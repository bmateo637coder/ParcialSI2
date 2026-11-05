from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FashionStore API"
    PROJECT_VERSION: str = "2.0.0"
    API_PREFIX: str = "/api"
    API_DESCRIPTION: str = "API de la tienda de ropa FashionStore."

    # Por defecto usamos SQLite para que funcione sin configuración extra.
    # Para producción se puede sobrescribir con una URL de PostgreSQL.
    DATABASE_URL: str = "sqlite:///./fashionstore.db"
    # Vercel inicia varias instancias: el esquema se prepara una sola vez,
    # desde la herramienta de despliegue, no durante peticiones o builds.
    VERCEL: bool = False
    AUTO_INIT_DB: bool | None = None

    # Seguridad: leer el secreto desde el entorno SIEMPRE en producción.
    SECRET_KEY: str = "dev-secret-key-no-usar-en-produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 600
    EXCHANGE_WINDOW_DAYS: int = 15
    ALLOW_DEMO_PASSWORD_RESET: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_STARTTLS: bool = True
    FRONTEND_URL: str = "http://localhost:4200"

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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    @model_validator(mode="after")
    def validate_hosted_settings(self):
        if self.VERCEL:
            if not self.DATABASE_URL.startswith(("postgres://", "postgresql://", "postgresql+psycopg2://")):
                raise ValueError("En Vercel configura DATABASE_URL con PostgreSQL externo.")
            if len(self.SECRET_KEY) < 32 or self.SECRET_KEY == "dev-secret-key-no-usar-en-produccion":
                raise ValueError("En Vercel configura SECRET_KEY con un secreto aleatorio de al menos 32 caracteres.")
            if self.auto_init_db:
                raise ValueError("En Vercel usa AUTO_INIT_DB=false y prepara la base antes de desplegar.")
        return self

    @property
    def auto_init_db(self) -> bool:
        return self.AUTO_INIT_DB if self.AUTO_INIT_DB is not None else not self.VERCEL

    @property
    def sqlalchemy_database_url(self) -> str:
        """URL de base de datos lista para SQLAlchemy.

        Normaliza las cadenas de PostgreSQL de los proveedores para usar
        explícitamente el driver instalado, psycopg2.
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        return url

    @property
    def cors_allow_credentials(self) -> bool:
        """No se pueden combinar credenciales con un origen comodín ``*``."""
        return "*" not in self.BACKEND_CORS_ORIGINS


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
