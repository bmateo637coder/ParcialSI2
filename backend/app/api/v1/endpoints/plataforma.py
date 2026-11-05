from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import hash_password, require_platform_admin, get_current_user
from app.models.branch import Branch
from app.models.tenant import Empresa, Plan, Suscripcion
from app.models.user import Role, User
from app.schemas import (
    EmpresaCreate,
    EmpresaResponse,
    PlanCreate,
    PlanResponse,
    SuscripcionResponse,
    SuscripcionUpdate,
)

router = APIRouter()

_ESTADOS_SUSCRIPCION = {"ACTIVA", "VENCIDA", "SUSPENDIDA", "CANCELADA"}


@router.get("/tiendas")
def tiendas_publicas(db: Session = Depends(get_db)):
    today = date.today()
    stores = db.query(Empresa).join(Suscripcion, Suscripcion.empresa_id == Empresa.id).join(Plan, Plan.id == Suscripcion.plan_id).filter(
        Empresa.is_active.is_(True), Plan.is_active.is_(True), Suscripcion.estado == "ACTIVA",
        Suscripcion.fecha_inicio <= today, Suscripcion.fecha_vencimiento >= today,
    ).order_by(Empresa.razon_social).all()
    return [{"id": company.id, "nombre": company.razon_social} for company in stores]


@router.get("/mi-suscripcion")
def mi_suscripcion(user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.empresa_id is None:
        raise HTTPException(404, "Usuario sin empresa asignada")
    subscription = db.query(Suscripcion).filter(Suscripcion.empresa_id == user.empresa_id).first()
    if not subscription:
        raise HTTPException(404, "Suscripción no encontrada")
    company, plan = db.get(Empresa, user.empresa_id), db.get(Plan, subscription.plan_id)
    return {"empresa_id": company.id, "empresa": company.razon_social, "plan": plan.nombre,
        "estado": subscription.estado, "fecha_inicio": subscription.fecha_inicio,
        "fecha_vencimiento": subscription.fecha_vencimiento, "max_sucursales": plan.max_sucursales,
        "permite_reportes_ia": plan.permite_reportes_ia, "permite_analitica_ml": plan.permite_analitica_ml}


def _get_plan_activo(db: Session, plan_id: int) -> Plan:
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.is_active.is_(True)).first()
    if not plan:
        raise HTTPException(status_code=400, detail="Plan no válido o inactivo")
    return plan


@router.post("/planes", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def crear_plan(
    plan: PlanCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    nuevo_plan = Plan(**plan.model_dump())
    db.add(nuevo_plan)
    db.commit()
    db.refresh(nuevo_plan)
    return nuevo_plan


@router.put("/planes/{plan_id}", response_model=PlanResponse)
def actualizar_plan(plan_id: int, payload: PlanCreate, db: Session = Depends(get_db), _admin=Depends(require_platform_admin)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan no encontrado")
    counts = (db.query(Branch.empresa_id, func.count(Branch.id)).join(Suscripcion, Suscripcion.empresa_id == Branch.empresa_id)
        .filter(Suscripcion.plan_id == plan.id, Branch.is_active.is_(True)).group_by(Branch.empresa_id).all())
    if any(count > payload.max_sucursales for _, count in counts):
        raise HTTPException(409, "Hay empresas que superan el nuevo límite de sucursales")
    for field, value in payload.model_dump().items():
        setattr(plan, field, value)
    db.commit(); db.refresh(plan)
    return plan


@router.get("/planes", response_model=List[PlanResponse])
def listar_planes(db: Session = Depends(get_db), solo_activos: bool = True):
    query = db.query(Plan)
    if solo_activos:
        query = query.filter(Plan.is_active.is_(True))
    return query.all()


@router.post("/empresas", response_model=EmpresaResponse, status_code=status.HTTP_201_CREATED)
def registrar_empresa(
    data: EmpresaCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    if db.query(Empresa).filter(Empresa.nit == data.nit).first():
        raise HTTPException(status_code=400, detail="Ya existe una empresa con ese NIT")

    plan = _get_plan_activo(db, data.plan_id)

    if db.query(User).filter(User.email == data.admin_email).first():
        raise HTTPException(
            status_code=400, detail="Ya existe un usuario con ese correo electrónico"
        )

    admin_role = db.query(Role).filter(Role.name == "Administrador").first()
    if admin_role is None:
        admin_role = Role(
            name="Administrador", description="Control total de la empresa contratante"
        )
        db.add(admin_role)
        db.flush()

    try:
        empresa = Empresa(
            razon_social=data.razon_social,
            nit=data.nit,
            logo_url=data.logo_url,
            email_contacto=data.email_contacto,
            telefono=data.telefono,
            direccion=data.direccion,
            is_active=data.is_active,
        )
        db.add(empresa)
        db.flush()

        db.add(
            User(
                empresa_id=empresa.id,
                first_name=data.admin_first_name.strip(),
                last_name=data.admin_last_name.strip(),
                email=data.admin_email,
                hashed_password=hash_password(data.admin_password),
                role_id=admin_role.id,
                is_active=True,
            )
        )

        db.add(
            Suscripcion(
                empresa_id=empresa.id,
                plan_id=plan.id,
                fecha_inicio=date.today(),
                fecha_vencimiento=date.today() + timedelta(days=30),
                estado="ACTIVA",
            )
        )
        db.commit()
        db.refresh(empresa)
    except Exception:
        db.rollback()
        raise

    return empresa


@router.get("/empresas", response_model=List[EmpresaResponse])
def listar_empresas(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    return db.query(Empresa).order_by(Empresa.razon_social).all()


@router.get("/empresas/{empresa_id}/suscripcion", response_model=SuscripcionResponse)
def obtener_suscripcion_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    if not db.get(Empresa, empresa_id):
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    suscripcion = db.query(Suscripcion).filter(Suscripcion.empresa_id == empresa_id).first()
    if not suscripcion:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")
    return suscripcion


@router.patch("/empresas/{empresa_id}/suscripcion", response_model=SuscripcionResponse)
def actualizar_suscripcion(
    empresa_id: int,
    payload: SuscripcionUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    if not db.get(Empresa, empresa_id):
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    suscripcion = db.query(Suscripcion).filter(Suscripcion.empresa_id == empresa_id).first()
    if not suscripcion:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")

    data = payload.model_dump(exclude_unset=True)
    if data.get("plan_id") is not None:
        plan = _get_plan_activo(db, data["plan_id"])
        count = db.query(Branch).filter(Branch.empresa_id == empresa_id, Branch.is_active.is_(True)).count()
        if count > plan.max_sucursales:
            raise HTTPException(409, "La empresa supera las sucursales permitidas por el nuevo plan")
    if data.get("estado") is not None:
        estado = data["estado"].strip().upper()
        if estado not in _ESTADOS_SUSCRIPCION:
            raise HTTPException(status_code=400, detail="Estado de suscripción no válido")
        data["estado"] = estado

    for field, value in data.items():
        setattr(suscripcion, field, value)

    if suscripcion.fecha_vencimiento < suscripcion.fecha_inicio:
        raise HTTPException(
            status_code=400,
            detail="La fecha de vencimiento no puede ser anterior a la de inicio",
        )

    db.commit()
    db.refresh(suscripcion)
    return suscripcion
