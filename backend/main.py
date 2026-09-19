from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.API_DESCRIPTION,
)


@app.on_event("startup")
def _ensure_roles():
    """Garantiza que los roles base existan al arrancar."""
    from app.core.database import SessionLocal
    from app.models.user import Role

    _migrate_order_items_columns()

    db = SessionLocal()
    try:
        for name, desc in {
            "Administrador": "Control total de la plataforma",
            "Cliente": "Usuario regular de la tienda",
            "Cajero": "Gestión de ventas en sucursal",
            "Encargado de Sucursal": "Administración de una sucursal",
            "Proveedor": "Suministra productos a la tienda",
        }.items():
            if not db.query(Role).filter(Role.name == name).first():
                db.add(Role(name=name, description=desc))
        db.commit()
    finally:
        db.close()


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


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Autenticación"])
app.include_router(users.router, prefix=f"{settings.API_PREFIX}/users", tags=["Usuarios y roles"])
app.include_router(branches.router, prefix=f"{settings.API_PREFIX}/branches", tags=["Sucursales"])
app.include_router(products.router, prefix=f"{settings.API_PREFIX}/products", tags=["Productos"])
app.include_router(inventory.router, prefix=f"{settings.API_PREFIX}/inventory", tags=["Inventario"])
app.include_router(commerce.router, prefix=f"{settings.API_PREFIX}", tags=["Ventas y operaciones"])
app.include_router(assistant.router, prefix=f"{settings.API_PREFIX}", tags=["Asistente y recomendaciones"])
app.include_router(reports.router, prefix=f"{settings.API_PREFIX}/reports", tags=["Reportes y dashboards"])
app.include_router(promotions.router, prefix=f"{settings.API_PREFIX}/promotions", tags=["Promociones"])
app.include_router(providers.router, prefix=f"{settings.API_PREFIX}/providers", tags=["Portal proveedor"])


@app.get("/", tags=["Info"])
def read_root():
    return {
        "message": f"Bienvenido a la API de {settings.PROJECT_NAME}",
        "version": settings.PROJECT_VERSION,
        "docs": "/docs",
    }


@app.get(f"{settings.API_PREFIX}/health", tags=["Info"])
def health_check():
    return {"status": "ok"}