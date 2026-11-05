from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Si usamos SQLite, necesitamos este argumento adicional para evitar errores de hilos
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
if settings.sqlalchemy_database_url.startswith("postgresql"):
    connect_args["connect_timeout"] = 10

# Neon proporciona el pool externo. No mantener conexiones inactivas en
# instancias serverless que pueden congelarse o multiplicarse.
pool_options = {"poolclass": NullPool} if settings.VERCEL else {}

engine = create_engine(
    settings.sqlalchemy_database_url, connect_args=connect_args,
    pool_pre_ping=True, pool_recycle=300,
    **pool_options,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependencia para inyectar la sesión de DB en los endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
