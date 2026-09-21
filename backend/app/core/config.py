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

    # Narrativa generativa de los reportes por voz. Si GENAI_API_KEY está vacío
    # se usa la plantilla local en español (fallback determinista).
    GENAI_API_KEY: str = ""
    GENAI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    GENAI_MODEL: str = "gemini-1.5-flash"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def sqlalchemy_database_url(self) -> str:
        """URL de base de datos lista para SQLAlchemy.

        Railway inyecta ``DATABASE_URL`` con el esquema ``postgres://``
        (sin driver). SQLAlchemy lo acepta, pero se normaliza a
        ``postgresql+psycopg2://`` para fijar el driver explícitamente y
        evitar sorpresas entre proveedores.
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://"):]
        return url

    @property
    def cors_allow_credentials(self) -> bool:
        """No se pueden combinar credenciales con un origen comodín ``*``."""
        return "*" not in self.BACKEND_CORS_ORIGINS


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()