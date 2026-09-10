from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, branches, products
from app.core.config import settings
from app.core.database import Base, engine
from app.models import branch, catalog, user

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


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Autenticación"])
app.include_router(branches.router, prefix=f"{settings.API_PREFIX}/branches", tags=["Sucursales"])
app.include_router(products.router, prefix=f"{settings.API_PREFIX}/products", tags=["Productos"])


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