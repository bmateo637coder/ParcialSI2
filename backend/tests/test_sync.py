import uuid
from datetime import datetime, timezone

import pytest
from conftest import subscribe_empresa

from app.core.database import SessionLocal
from app.models.branch import Branch
from app.models.commerce import Order
from app.models.inventory import Inventory
from app.models.sync import OperacionSync
from app.models.tenant import Empresa
from app.models.user import User


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def sync_catalog(catalog):
    """Asigna empresa al cajero y a la sucursal del catálogo de pruebas."""
    uid = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        empresa = Empresa(
            razon_social=f"Empresa Sync {uid}",
            nit=f"SYNC-{uid}",
            is_active=True,
        )
        db.add(empresa)
        db.flush()
        subscribe_empresa(db, empresa.id)

        branch = db.query(Branch).filter(Branch.id == catalog["branch_id"]).first()
        branch.empresa_id = empresa.id

        cajero = db.query(User).filter(User.email == "cajero@test.com").first()
        cajero.empresa_id = empresa.id

        db.commit()
        context = {**catalog, "empresa_id": empresa.id, "cajero_id": cajero.id}
    yield context
    with SessionLocal() as db:
        db.get(User, context["cajero_id"]).empresa_id = None
        db.commit()


def _operation(sync_catalog, op_uuid, quantity):
    return {
        "uuid": op_uuid,
        "tipo_operacion": "VENTA_CONTADO",
        "sucursal_id": sync_catalog["branch_id"],
        "usuario_id": sync_catalog["cajero_id"],
        "fecha_local": datetime.now(timezone.utc).isoformat(),
        "items": [
            {
                "variante_id": sync_catalog["variant_id"],
                "cantidad": quantity,
                "precio": 120.0,
            }
        ],
        "total": 120.0 * quantity,
        "forma_pago": "EFECTIVO",
        "origen": "OFFLINE",
    }


def test_sync_sale_discounts_stock_and_is_idempotent(client, cajero_token, sync_catalog):
    op_uuid = str(uuid.uuid4())
    operation = _operation(sync_catalog, op_uuid, 2)

    res = client.post("/api/sync", json={"operaciones": [operation]}, headers=_headers(cajero_token))
    assert res.status_code == 200, res.text
    assert res.json()["resultados"][0]["estado"] == "CONFIRMADA"

    with SessionLocal() as db:
        inventory = db.query(Inventory).filter(
            Inventory.branch_id == sync_catalog["branch_id"],
            Inventory.variant_id == sync_catalog["variant_id"],
        ).first()
        assert inventory.available == 8

        order = db.query(Order).filter(Order.empresa_id == sync_catalog["empresa_id"]).first()
        assert order is not None
        assert order.total == 240.0
        assert order.es_offline is True

    res = client.post("/api/sync", json={"operaciones": [operation]}, headers=_headers(cajero_token))
    assert res.status_code == 200, res.text
    assert res.json()["resultados"][0]["estado"] == "CONFIRMADA"

    with SessionLocal() as db:
        inventory = db.query(Inventory).filter(
            Inventory.branch_id == sync_catalog["branch_id"],
            Inventory.variant_id == sync_catalog["variant_id"],
        ).first()
        assert inventory.available == 8


def test_sync_conflict_can_be_rejected_and_adjusted(client, cajero_token, sync_catalog):
    rejected_uuid = str(uuid.uuid4())
    rejected = _operation(sync_catalog, rejected_uuid, 99)

    res = client.post("/api/sync", json={"operaciones": [rejected]}, headers=_headers(cajero_token))
    assert res.status_code == 200, res.text
    assert res.json()["resultados"][0]["estado"] == "EN_CONFLICTO"

    conflictos = client.get(
        "/api/sync/conflictos?solo_pendientes=true", headers=_headers(cajero_token)
    )
    assert conflictos.status_code == 200, conflictos.text
    conflicto = next(
        c for c in conflictos.json() if c["operacion_sync_id"] == res.json()["resultados"][0]["operacion_sync_id"]
    )
    assert conflicto["stock_disponible"] == 10
    assert conflicto["cantidad_solicitada"] == 99

    rechazo = client.post(
        f"/api/sync/conflictos/{conflicto['id']}/resolver",
        json={"accion": "RECHAZAR"},
        headers=_headers(cajero_token),
    )
    assert rechazo.status_code == 200, rechazo.text
    assert rechazo.json()["accion_tomada"] == "RECHAZAR"

    with SessionLocal() as db:
        op = db.query(OperacionSync).filter(OperacionSync.uuid == rejected_uuid).first()
        assert op.estado == "RECHAZADA"

    adjusted_uuid = str(uuid.uuid4())
    adjusted = _operation(sync_catalog, adjusted_uuid, 50)
    res = client.post("/api/sync", json={"operaciones": [adjusted]}, headers=_headers(cajero_token))
    assert res.status_code == 200, res.text
    assert res.json()["resultados"][0]["estado"] == "EN_CONFLICTO"

    conflictos = client.get(
        "/api/sync/conflictos?solo_pendientes=true", headers=_headers(cajero_token)
    )
    conflicto = next(
        c for c in conflictos.json() if c["operacion_sync_id"] == res.json()["resultados"][0]["operacion_sync_id"]
    )

    ajuste = client.post(
        f"/api/sync/conflictos/{conflicto['id']}/resolver",
        json={"accion": "AJUSTAR_CANTIDAD", "cantidad_aceptada": 3},
        headers=_headers(cajero_token),
    )
    assert ajuste.status_code == 200, ajuste.text
    assert ajuste.json()["accion_tomada"] == "AJUSTAR_CANTIDAD"

    with SessionLocal() as db:
        op = db.query(OperacionSync).filter(OperacionSync.uuid == adjusted_uuid).first()
        assert op.estado == "CONFIRMADA"

        inventory = db.query(Inventory).filter(
            Inventory.branch_id == sync_catalog["branch_id"],
            Inventory.variant_id == sync_catalog["variant_id"],
        ).first()
        assert inventory.available == 7
