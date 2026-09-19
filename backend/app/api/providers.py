"""Portal del Proveedor.

Un usuario con rol Proveedor (vinculado a una empresa mediante ProviderAccount):
- consulta su perfil y su empresa (/me),
- gestiona la disponibilidad de SOLO los productos de su empresa,
- envía propuestas de nuevos productos.

El administrador:
- vincula usuarios a empresas (provider_accounts),
- aprueba o rechaza las propuestas; al aprobarlas se crea el Producto.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.catalog import Product, ProductProposal, Provider, ProviderAccount
from app.models.user import User
from app.schemas import (
    ProductResponse,
    ProposalCreate,
    ProposalResponse,
    ProposalReview,
    ProviderAccountCreate,
    ProviderAccountResponse,
    ProviderMeResponse,
    UserResponse,
)

router = APIRouter()


def _require_provider(user: User) -> User:
    if user.role_name != "Proveedor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Requiere rol de proveedor")
    return user


def _account(db: Session, user: User) -> ProviderAccount | None:
    return db.query(ProviderAccount).filter(ProviderAccount.user_id == user.id).first()


def _get_account_or_404(db: Session, user: User) -> ProviderAccount:
    account = _account(db, user)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Tu usuario no está vinculado a ninguna empresa proveedora")
    return account


def _get_provider_product_or_404(db: Session, account: ProviderAccount, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    if product.provider_id != account.provider_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Este producto no pertenece a tu empresa")
    return product


@router.get("/me", response_model=ProviderMeResponse, summary="Mi perfil de proveedor")
def provider_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_provider(user)
    provider = None
    account = _account(db, user)
    if account is not None:
        provider = db.get(Provider, account.provider_id)
    return ProviderMeResponse(
        user=UserResponse(
            id=user.id, first_name=user.first_name, last_name=user.last_name,
            email=user.email, phone=user.phone, is_active=user.is_active,
            role_id=user.role_id, role_name=user.role_name, full_name=user.full_name,
            created_at=user.created_at,
        ),
        role=user.role_name,
        provider=provider if (provider and provider.is_active) else None,
    )


@router.get("/products", response_model=list[ProductResponse],
            summary="Productos de mi empresa")
def provider_products(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_provider(user)
    account = _get_account_or_404(db, user)
    return (
        db.query(Product)
        .filter(Product.provider_id == account.provider_id)
        .order_by(Product.id.desc())
        .all()
    )


@router.patch("/products/{product_id}", response_model=ProductResponse,
              summary="Cambiar disponibilidad de un producto propio")
def update_provider_product(product_id: int, payload: dict,
                            user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    _require_provider(user)
    account = _get_account_or_404(db, user)
    product = _get_provider_product_or_404(db, account, product_id)

    is_active = payload.get("is_active")
    if not isinstance(is_active, bool):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Se requiere el campo booleano is_active")
    product.is_active = is_active
    db.commit()
    db.refresh(product)
    return product


@router.post("/products", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED,
             summary="Proponer un nuevo producto")
def propose_product(payload: ProposalCreate, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    _require_provider(user)
    account = _get_account_or_404(db, user)
    proposal = ProductProposal(
        provider_id=account.provider_id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        base_price=payload.base_price,
        status="PENDIENTE",
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return _proposal_response(db, proposal)


@router.get("/proposals", response_model=list[ProposalResponse],
            summary="Ver propuestas (proveedor: solo las suyas; admin: todas)")
def list_proposals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role_name == "Administrador":
        rows = db.query(ProductProposal).order_by(ProductProposal.id.desc()).all()
    else:
        _require_provider(user)
        account = _get_account_or_404(db, user)
        rows = (db.query(ProductProposal)
                .filter(ProductProposal.provider_id == account.provider_id)
                .order_by(ProductProposal.id.desc()).all())
    return [_proposal_response(db, p) for p in rows]


def _proposal_response(db: Session, proposal: ProductProposal) -> ProposalResponse:
    provider = db.get(Provider, proposal.provider_id)
    return ProposalResponse(
        id=proposal.id,
        provider_id=proposal.provider_id,
        provider_name=provider.name if provider else None,
        name=proposal.name,
        description=proposal.description,
        base_price=proposal.base_price,
        status=proposal.status,
        admin_comment=proposal.admin_comment,
        created_at=proposal.created_at,
        processed_at=proposal.processed_at,
    )


def _get_proposal_or_404(db: Session, proposal_id: int) -> ProductProposal:
    proposal = db.get(ProductProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Propuesta no encontrada")
    return proposal


def _resolve_proposal(db: Session, proposal: ProductProposal, new_status: str,
                      admin_comment: str | None, create_product: bool) -> ProposalResponse:
    if proposal.status != "PENDIENTE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"La propuesta ya fue procesada (estado: {proposal.status})")
    proposal.status = new_status
    proposal.admin_comment = admin_comment
    proposal.processed_at = datetime.now(timezone.utc)
    if create_product:
        db.add(Product(
            name=proposal.name,
            description=proposal.description,
            base_price=proposal.base_price,
            provider_id=proposal.provider_id,
            is_active=True,
        ))
    db.commit()
    db.refresh(proposal)
    return _proposal_response(db, proposal)


@router.patch("/proposals/{proposal_id}/approve", response_model=ProposalResponse,
              summary="Aprobar propuesta (admin): crea el producto")
def approve_proposal(proposal_id: int, payload: ProposalReview,
                     _admin=Depends(require_admin), db: Session = Depends(get_db)):
    proposal = _get_proposal_or_404(db, proposal_id)
    return _resolve_proposal(db, proposal, "APROBADA", payload.admin_comment, create_product=True)


@router.patch("/proposals/{proposal_id}/reject", response_model=ProposalResponse,
              summary="Rechazar propuesta (admin)")
def reject_proposal(proposal_id: int, payload: ProposalReview,
                    _admin=Depends(require_admin), db: Session = Depends(get_db)):
    proposal = _get_proposal_or_404(db, proposal_id)
    return _resolve_proposal(db, proposal, "RECHAZADA", payload.admin_comment, create_product=False)


@router.post("/accounts", response_model=ProviderAccountResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Vincular un usuario proveedor a una empresa (admin)")
def link_account(payload: ProviderAccountCreate, _admin=Depends(require_admin),
                 db: Session = Depends(get_db)):
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if user.role_name != "Proveedor":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="El usuario debe tener rol Proveedor")
    provider = db.get(Provider, payload.provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    account = ProviderAccount(user_id=user.id, provider_id=provider.id)
    db.add(account)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="El usuario ya está vinculado a una empresa")
    db.refresh(account)
    return account