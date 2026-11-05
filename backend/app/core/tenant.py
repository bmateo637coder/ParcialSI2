from datetime import date

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_business_user as _security_get_current_user
from app.models.branch import Branch
from app.models.user import User
from app.models.tenant import Suscripcion, Plan, Empresa


def get_current_user(
    current_user: User = Depends(_security_get_current_user),
) -> User:
    """Compatibility dependency: delegate JWT validation to core.security."""
    return current_user


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
    suscripcion, plan = validate_subscription(db, empresa.id)
    if current_user.role_name not in {"Administrador", "Encargado de Sucursal"}:
        raise HTTPException(status_code=403, detail="Requiere autorización para consultar reportes")
    if not plan.permite_reportes_ia:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta funcionalidad requiere plan Profesional",
        )
    return {"empresa": empresa, "suscripcion": suscripcion, "plan": plan, "user": current_user}


def validate_subscription(db: Session, empresa_id: int):
    empresa = db.get(Empresa, empresa_id)
    if not empresa or not empresa.is_active:
        raise HTTPException(status_code=403, detail="Empresa inactiva o no encontrada")
    subscription = db.query(Suscripcion).filter(Suscripcion.empresa_id == empresa_id).first()
    if not subscription or subscription.estado != "ACTIVA":
        raise HTTPException(status_code=403, detail="Sin suscripción activa")
    today = date.today()
    if not subscription.fecha_inicio <= today <= subscription.fecha_vencimiento:
        raise HTTPException(status_code=403, detail="Suscripción fuera de vigencia")
    plan = db.get(Plan, subscription.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=403, detail="Plan inactivo o no encontrado")
    return subscription, plan


def scope_to_empresa(query, model, user: User | None, *, include_global: bool = True):
    """Limita una consulta al tenant del usuario.

    Solo el administrador de plataforma tiene acceso transversal. Los usuarios
    sin empresa acceden únicamente a los registros del catálogo compartido.
    """
    if user is not None and user.role_name == "Administrador de Plataforma":
        return query
    if user is None or user.empresa_id is None:
        return query.filter(model.empresa_id.is_(None))

    clause = model.empresa_id == user.empresa_id
    if include_global:
        clause = or_(clause, model.empresa_id.is_(None))
    return query.filter(clause)


def ensure_tenant_owns(
    instance,
    user: User | None,
    *,
    include_global: bool = True,
    label: str = "Recurso",
):
    """Lanza 404 si el registro pertenece a otra empresa."""
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} no encontrado")
    if user is not None and user.role_name == "Administrador de Plataforma":
        return instance

    owner = getattr(instance, "empresa_id", None)
    empresa_id = user.empresa_id if user is not None else None
    if owner != empresa_id and not (include_global and owner is None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} no encontrado")
    return instance


def enforce_branch_limit(db: Session, empresa_id: int | None) -> None:
    """Valida el máximo de sucursales activas del plan contratado (CU5/CU30)."""
    if empresa_id is None:
        return

    # Bloquear la empresa serializa altas/reactivaciones concurrentes.
    db.query(Empresa).filter(Empresa.id == empresa_id).with_for_update().first()
    _, plan = validate_subscription(db, empresa_id)

    activas = (
        db.query(func.count(Branch.id))
        .filter(Branch.empresa_id == empresa_id, Branch.is_active.is_(True))
        .scalar()
        or 0
    )
    if activas >= plan.max_sucursales:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"El plan {plan.nombre} permite como máximo "
                f"{plan.max_sucursales} sucursal(es) activa(s)"
            ),
        )


def require_suscripcion_activa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    empresa = get_current_empresa(current_user, db)
    suscripcion, _ = validate_subscription(db, empresa.id)
    return {"empresa": empresa, "suscripcion": suscripcion}
