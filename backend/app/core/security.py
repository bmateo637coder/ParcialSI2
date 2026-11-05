from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Genera un hash bcrypt ($2b$) compatible con passlib y bcrypt."""
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise HTTPException(status_code=422, detail="La contraseña no puede superar 72 bytes en UTF-8")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        return False


def create_access_token(subject: str, role: str, extra: dict | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {"sub": subject, "role": role, "exp": expire}
    if extra:
        to_encode.update(extra)
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Devuelve el usuario autenticado a partir del token Bearer."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise unauthorized

    email = payload.get("sub")
    if not email or payload.get("purpose") is not None:
        raise unauthorized

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise unauthorized
    from app.services.audit import identify_actor
    identify_actor(db, user)
    return user


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Devuelve el usuario autenticado o ``None`` si no hay token válido.

    Se usa en endpoints públicos que, cuando reciben un usuario de una empresa,
    deben limitar los resultados a ese tenant sin romper el acceso anónimo.
    """
    if credentials is None:
        return None

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        return None

    email = payload.get("sub")
    if not email or payload.get("purpose") is not None:
        return None

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        return None
    return user


def get_current_business_user(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> User:
    from app.core.tenant import validate_subscription

    if user.empresa_id is not None:
        validate_subscription(db, user.empresa_id)
    return user


def require_admin(user: User = Depends(get_current_business_user)) -> User:
    """Bloquea el acceso a operaciones de administración."""
    if user.role_name != "Administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere rol de administrador",
        )
    return user


def require_platform_admin(user: User = Depends(get_current_user)) -> User:
    """Bloquea el acceso a operaciones de la plataforma SaaS.

    Solo el rol ``Administrador de Plataforma`` puede gestionar planes,
    empresas y suscripciones de cualquier tenant.
    """
    if user.role_name != "Administrador de Plataforma":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere rol de Administrador de Plataforma",
        )
    return user
