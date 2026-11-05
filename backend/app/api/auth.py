from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import hashlib
import hmac
import smtplib

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, decode_token, get_current_user, hash_password, verify_password
from app.core.tenant import validate_subscription
from app.core.config import settings
from app.models.user import Role, User
from app.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    Token,
    UserCreate,
    UserResponse,
    UserUpdate,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo cliente",
)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if user.empresa_id is not None:
        validate_subscription(db, user.empresa_id)
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El correo ya está registrado"
        )

    cliente_role = db.query(Role).filter(Role.name == "Cliente").first()
    if not cliente_role:
        cliente_role = Role(name="Cliente", description="Rol de Cliente")
        db.add(cliente_role)
        db.flush()

    new_user = User(
        empresa_id=user.empresa_id,
        first_name=user.first_name.strip(),
        last_name=user.last_name.strip(),
        email=user.email,
        phone=user.phone.strip() if user.phone else None,
        hashed_password=hash_password(user.password),
        role_id=cliente_role.id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token, summary="Iniciar sesión")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")

    token = create_access_token(subject=user.email, role=user.role_name or "Cliente")
    from app.services.audit import identify_actor, log_action
    identify_actor(db, user)
    log_action(db, 'ACCESO', 'users', user.id, 'Inicio de sesión correcto')
    db.commit()
    return Token(
        access_token=token,
        role=user.role_name or "Cliente",
        email=user.email,
        user_id=user.id,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Perfil del usuario autenticado",
)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Actualizar el perfil del usuario autenticado",
)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    new_email = data.get("email")
    if new_email is not None and new_email != current_user.email:
        other = db.query(User).filter(User.email == new_email).first()
        if other:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo ya está registrado",
            )
    password = data.pop("password", None)
    for field, value in data.items():
        setattr(current_user, field, value.strip() if isinstance(value, str) else value)
    if password:
        current_user.hashed_password = hash_password(password)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post(
    "/forgot-password",
    response_model=ResetPasswordResponse,
    summary="Solicitar restablecimiento de contraseña",
)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    if not settings.ALLOW_DEMO_PASSWORD_RESET and not settings.SMTP_HOST:
        raise HTTPException(503, "La recuperación por correo no está configurada. Contacta al administrador.")
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not user.is_active:
        if not settings.ALLOW_DEMO_PASSWORD_RESET:
            return ResetPasswordResponse(message="Si existe una cuenta activa, recibirá instrucciones por correo.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una cuenta activa con ese correo",
        )

    # Token de corto plazo (30 min), con propósito explícito para no reutilizar
    # tokens de acceso como token de reseteo.
    reset_token = create_access_token(
        subject=user.email,
        role=user.role_name or "Cliente",
        extra={"purpose": "reset_password", "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "password_version": hashlib.sha256(user.hashed_password.encode()).hexdigest()},
    )
    # Sin servidor de correo configurado se devuelve el token en la respuesta
    # (modo demo). En producción se enviaría por email y no se retornaría.
    if not settings.ALLOW_DEMO_PASSWORD_RESET:
        message = EmailMessage()
        message["Subject"] = "Restablecer contraseña de FashionStore"
        message["From"] = settings.SMTP_FROM or settings.SMTP_USER
        message["To"] = user.email
        message.set_content(f"Abre este enlace para restablecer tu contraseña dentro de 30 minutos:\n{settings.FRONTEND_URL.rstrip('/')}/auth?reset_token={reset_token}")
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_STARTTLS:
                    server.starttls()
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(message)
        except Exception:
            raise HTTPException(503, "No se pudo enviar el correo de recuperación. Intenta más tarde.")
        return ResetPasswordResponse(message="Si existe una cuenta activa, recibirá instrucciones por correo.")
    return ResetPasswordResponse(
        message="Se generó un enlace de restablecimiento de contraseña.",
        reset_token=reset_token,
    )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    summary="Restablecer contraseña con token",
)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        claims = decode_token(payload.token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de restablecimiento no es válido o expiró",
        )
    if claims.get("purpose") != "reset_password":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de restablecimiento no es válido o expiró",
        )

    exp = claims.get("exp")
    if exp is not None:
        expired_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        if expired_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El enlace de restablecimiento no es válido o expiró",
            )

    email = claims.get("sub")
    user = db.query(User).filter(User.email == email).first() if email else None
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de restablecimiento no es válido o expiró",
        )
    fingerprint = hashlib.sha256(user.hashed_password.encode()).hexdigest()
    if not hmac.compare_digest(claims.get("password_version", ""), fingerprint):
        raise HTTPException(400, "El enlace ya fue utilizado o dejó de ser válido")

    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return ResetPasswordResponse(message="Contraseña restablecida. Ya puedes iniciar sesión.")
