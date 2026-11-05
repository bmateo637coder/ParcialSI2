from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api import (
    assistant,
    auth,
    branches,
    commerce,
    inventory,
    products,
    promotions,
    providers,
    reports,
    users,
)
from app.api.v1.endpoints import plataforma, sync
from app.api import ia_reportes, analitica_ml
from app.api import audit
from app.services import audit as audit_service
from app.core.config import settings
from app.core.database import Base, engine
from app.models import (
    assistant as assistant_model,
    branch,
    catalog,
    commerce as commerce_model,
    inventory as inventory_model,
    promotion as promotion_model,
    user,
)

if settings.auto_init_db:
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.API_DESCRIPTION,
)


def _ensure_roles():
    """Garantiza que los roles base existan al arrancar."""
    from app.core.database import SessionLocal
    from app.models.user import Role
    from app.core.migrations import migrate_compatible_schema

    migrate_compatible_schema(engine)
    _migrate_order_items_columns()
    _migrate_orders_columns()
    _migrate_promotions_columns()
    _migrate_products_columns()

    db = SessionLocal()
    try:
        for name, desc in {
            "Administrador de Plataforma": "Gestiona empresas, planes y suscripciones SaaS",
            "Administrador": "Control total de la empresa contratante",
            "Cliente": "Usuario regular de la tienda",
            "Cajero": "Gestión de ventas en sucursal",
            "Encargado de Sucursal": "Administración de una sucursal",
            "Proveedor": "Suministra productos a la tienda",
        }.items():
            if not db.query(Role).filter(Role.name == name).first():
                db.add(Role(name=name, description=desc))
        _ensure_plans(db)
        db.commit()
        from app.services.refunds import register_legacy_cancellations
        register_legacy_cancellations(db)
    finally:
        db.close()


def _ensure_plans(db):
    """Crea los planes SaaS base si la tabla está vacía."""
    from app.models.tenant import Plan

    for name, old_limit, old_description, new_limit, description in (
        ("Básico", 1, "Una sucursal, sin módulos de IA.", 2, "Hasta dos sucursales, sin reportes generativos."),
        ("Profesional", 3, "Hasta tres sucursales y reportes con IA.", 10, "Hasta diez sucursales y reportes con IA."),
    ):
        legacy = db.query(Plan).filter_by(nombre=name, max_sucursales=old_limit, descripcion=old_description).first()
        if legacy:
            legacy.max_sucursales, legacy.descripcion = new_limit, description
    if db.query(Plan).count() > 0:
        return
    db.add_all(
        [
            Plan(
                nombre="Básico",
                max_sucursales=2,
                permite_reportes_ia=False,
                permite_analitica_ml=False,
                precio_mensual=0.0,
                descripcion="Hasta dos sucursales, sin reportes generativos.",
            ),
            Plan(
                nombre="Profesional",
                max_sucursales=10,
                permite_reportes_ia=True,
                permite_analitica_ml=True,
                precio_mensual=99.0,
                descripcion="Hasta diez sucursales y reportes con IA.",
            ),
            Plan(
                nombre="Empresarial",
                max_sucursales=10,
                permite_reportes_ia=True,
                permite_analitica_ml=True,
                precio_mensual=299.0,
                descripcion="Sucursales ampliadas, reportes IA y analítica ML.",
            ),
        ]
    )


@app.on_event("startup")
def _initialize_local_database():
    if settings.auto_init_db:
        _ensure_roles()


@app.on_event("startup")
def _seed_initial_data():
    """Datos demo opcionales en desarrollo; nunca en instancias serverless."""
    import os

    if settings.VERCEL or not settings.auto_init_db or os.getenv("AUTO_SEED", "").strip().lower() not in {"1", "true", "yes"}:
        return
    from seed import seed_db

    seed_db()


def _migrate_order_items_columns():
    """SQLite: create_all no altera tablas existentes; añade las columnas de
    promociones a order_items si faltan (BD de desarrollo ya creada)."""
    import sqlalchemy as sa
    from app.models.commerce import OrderItem

    inspection = sa.inspect(engine)
    if "order_items" not in inspection.get_table_names():
        return
    existing = {column["name"] for column in inspection.get_columns("order_items")}
    with engine.connect() as connection:
        if "discount" not in existing:
            connection.execute(sa.text(
                "ALTER TABLE order_items ADD COLUMN discount FLOAT NOT NULL DEFAULT 0"))
        if "promotion_id" not in existing:
            connection.execute(sa.text(
                "ALTER TABLE order_items ADD COLUMN promotion_id INTEGER"))
        connection.commit()


def _migrate_promotions_columns():
    """SQLite: añade empresa_id a promotions en BD ya creadas."""
    if engine.dialect.name != "sqlite":
        return

    import sqlalchemy as sa

    inspection = sa.inspect(engine)
    if "promotions" not in inspection.get_table_names():
        return
    existing = {column["name"] for column in inspection.get_columns("promotions")}
    if "empresa_id" in existing:
        return
    with engine.connect() as connection:
        connection.execute(sa.text(
            "ALTER TABLE promotions ADD COLUMN empresa_id INTEGER"))
        connection.commit()


def _migrate_products_columns():
    """Añade empresa_id a products en BD ya creadas."""
    import sqlalchemy as sa

    inspection = sa.inspect(engine)
    if "products" not in inspection.get_table_names():
        return
    existing = {column["name"] for column in inspection.get_columns("products")}
    if "empresa_id" in existing:
        return
    with engine.connect() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(
                sa.text(
                    "ALTER TABLE products ADD COLUMN IF NOT EXISTS empresa_id INTEGER "
                    "REFERENCES empresas(id)"
                )
            )
        else:
            connection.execute(sa.text("ALTER TABLE products ADD COLUMN empresa_id INTEGER"))
        connection.commit()


def _migrate_orders_columns():
    """SQLite: añade columnas de tenant/offline a orders en BD ya creadas."""
    if engine.dialect.name != "sqlite":
        return

    import sqlalchemy as sa

    inspection = sa.inspect(engine)
    if "orders" not in inspection.get_table_names():
        return

    existing = {column["name"] for column in inspection.get_columns("orders")}
    columns = {
        "empresa_id": "INTEGER",
        "es_offline": "BOOLEAN NOT NULL DEFAULT 0",
        "origen": "VARCHAR(20) DEFAULT 'ONLINE'",
        "order_number": "VARCHAR(30)",
        "payment_method": "VARCHAR(30)",
        "subtotal": "FLOAT",
        "shipping_address": "VARCHAR(255)",
    }

    with engine.connect() as connection:
        for name, ddl in columns.items():
            if name not in existing:
                connection.execute(
                    sa.text(f"ALTER TABLE orders ADD COLUMN {name} {ddl}")
                )
        connection.commit()



app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Autenticación"])
app.include_router(users.router, prefix=f"{settings.API_PREFIX}/users", tags=["Usuarios y roles"])
app.include_router(audit.router, prefix=f"{settings.API_PREFIX}/bitacora", tags=["Bitácora"])
app.include_router(branches.router, prefix=f"{settings.API_PREFIX}/branches", tags=["Sucursales"])
app.include_router(products.router, prefix=f"{settings.API_PREFIX}/products", tags=["Productos"])
app.include_router(inventory.router, prefix=f"{settings.API_PREFIX}/inventory", tags=["Inventario"])
app.include_router(commerce.router, prefix=f"{settings.API_PREFIX}", tags=["Ventas y operaciones"])
app.include_router(assistant.router, prefix=f"{settings.API_PREFIX}", tags=["Asistente y recomendaciones"])
app.include_router(reports.router, prefix=f"{settings.API_PREFIX}/reports", tags=["Reportes y dashboards"])
app.include_router(promotions.router, prefix=f"{settings.API_PREFIX}/promotions", tags=["Promociones"])
app.include_router(providers.router, prefix=f"{settings.API_PREFIX}/providers", tags=["Portal proveedor"])
app.include_router(plataforma.router, prefix=f"{settings.API_PREFIX}/plataforma", tags=["Plataforma SaaS"])
app.include_router(sync.router, prefix=f"{settings.API_PREFIX}/sync", tags=["Sincronización Offline"])
app.include_router(ia_reportes.router, prefix=f"{settings.API_PREFIX}/reportes", tags=["Reportes IA"])
app.include_router(analitica_ml.router, prefix=f"{settings.API_PREFIX}/analitica", tags=["Analítica ML"])


@app.get("/", tags=["Info"])
def read_root():
    return {
        "message": f"Bienvenido a la API de {settings.PROJECT_NAME}",
        "version": settings.PROJECT_VERSION,
        "docs": "/docs",
    }


@app.get(f"{settings.API_PREFIX}/health", tags=["Info"])
def health_check():
    from sqlalchemy import text

    from app.core.database import SessionLocal

    db_status = "ok"
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - entorno caído
        db_status = f"error: {type(exc).__name__}"
    return {"status": "ok", "database": db_status}
