from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.tenant import Suscripcion, Plan, Empresa
from datetime import date

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        )
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no autenticado"
        )
    return user


def get_current_empresa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Empresa:
    if not current_user.empresa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Usuario sin empresa asignada"
        )
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa or not empresa.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Empresa inactiva o no encontrada"
        )
    return empresa


def require_plan_profesional(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    empresa = get_current_empresa(current_user, db)
    suscripcion = (
        db.query(Suscripcion)
        .filter(Suscripcion.empresa_id == empresa.id, Suscripcion.estado == "ACTIVA")
        .first()
    )
    if not suscripcion:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin suscripción activa")
    plan = db.query(Plan).filter(Plan.id == suscripcion.plan_id).first()
    if not plan or not plan.permite_reportes_ia:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta funcionalidad requiere plan Profesional",
        )
    if suscripcion.fecha_vencimiento < date.today():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Suscripción vencida")
    return {"empresa": empresa, "suscripcion": suscripcion, "plan": plan}


def require_suscripcion_activa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    empresa = get_current_empresa(current_user, db)
    suscripcion = (
        db.query(Suscripcion)
        .filter(Suscripcion.empresa_id == empresa.id, Suscripcion.estado == "ACTIVA")
        .first()
    )
    if not suscripcion:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin suscripción activa")
    if suscripcion.fecha_vencimiento < date.today():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Suscripción vencida")
    return {"empresa": empresa, "suscripcion": suscripcion}
