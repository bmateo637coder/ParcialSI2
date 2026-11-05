"""Contexto de lectura del catálogo público de una tienda concreta."""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_optional_current_user
from app.core.tenant import validate_subscription


@dataclass(frozen=True)
class PublicStorefront:
    empresa_id: int
    role_name: str = "Visitante"


def get_catalog_context(
    empresa_id: int | None = Query(default=None, gt=0),
    current_user=Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    if current_user is not None:
        if empresa_id is not None and empresa_id != current_user.empresa_id:
            raise HTTPException(404, "Tienda no disponible para esta sesión")
        return current_user
    if empresa_id is None:
        return None
    try:
        validate_subscription(db, empresa_id)
    except HTTPException:
        raise HTTPException(404, "Tienda no disponible") from None
    return PublicStorefront(empresa_id)
