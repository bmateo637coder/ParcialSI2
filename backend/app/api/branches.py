from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.core.tenant import enforce_branch_limit, ensure_tenant_owns, scope_to_empresa
from app.core.storefront import get_catalog_context
from app.models.branch import Branch
from app.schemas import BranchCreate, BranchResponse, BranchUpdate

router = APIRouter()


@router.get("/", response_model=list[BranchResponse], summary="Listar sucursales activas")
def get_branches(
    city: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_catalog_context),
):
    query = db.query(Branch).filter(Branch.is_active.is_(True))
    query = scope_to_empresa(query, Branch, current_user, include_global=False)
    if city:
        query = query.filter(Branch.city.ilike(f"%{city.strip()}%"))
    return query.order_by(Branch.city, Branch.name).all()


@router.get("/{branch_id}", response_model=BranchResponse, summary="Obtener una sucursal")
def get_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_catalog_context),
):
    branch = db.get(Branch, branch_id)
    if branch is None or not branch.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
    if current_user is None:
        if branch.empresa_id is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
    else:
        ensure_tenant_owns(branch, current_user, label="Sucursal")
    return branch


@router.post(
    "/",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear sucursal (admin)",
)
def create_branch(
    payload: BranchCreate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    enforce_branch_limit(db, _admin.empresa_id)
    branch = Branch(**payload.model_dump(), empresa_id=_admin.empresa_id)
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


@router.patch(
    "/{branch_id}",
    response_model=BranchResponse,
    summary="Actualizar sucursal (admin)",
)
def update_branch(
    branch_id: int,
    payload: BranchUpdate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
    ensure_tenant_owns(branch, _admin, include_global=False, label="Sucursal")

    data = payload.model_dump(exclude_unset=True)
    if data.get("is_active") is True and not branch.is_active:
        enforce_branch_limit(db, _admin.empresa_id)
    for field, value in data.items():
        setattr(branch, field, value)
    db.commit()
    db.refresh(branch)
    return branch


@router.delete(
    "/{branch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desactivar sucursal (admin)",
)
def delete_branch(branch_id: int, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
    ensure_tenant_owns(branch, _admin, include_global=False, label="Sucursal")
    branch.is_active = False
    db.commit()
