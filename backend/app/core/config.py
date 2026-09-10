from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FashionStore API"
    PROJECT_VERSION: str = "2.0.0"
    API_PREFIX: str = "/api"
    API_DESCRIPTION: str = "API de la tienda de ropa FashionStore."

    # Por defecto usamos SQLite para que funcione sin configuración extra.
    # Para producción se puede sobrescribir con una URL de PostgreSQL.
    DATABASE_URL: str = "sqlite:///./fashionstore.db"

    # Seguridad: leer el secreto desde el entorno SIEMPRE en producción.
    SECRET_KEY: str = "dev-secret-key-no-usar-en-produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 600

    # Orígenes permitidos para CORS (frontend de desarrollo).
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()