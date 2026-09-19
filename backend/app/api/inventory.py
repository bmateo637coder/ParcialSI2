from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.branch import Branch
from app.models.catalog import Product, ProductVariant
from app.models.inventory import Inventory, InventoryMovement
from app.models.user import Role, User
from app.schemas import (
    AvailabilityItem,
    InventoryCreate,
    InventoryMovementCreate,
    InventoryMovementResponse,
    InventoryResponse,
    InventoryUpdate,
)

router = APIRouter()

# Roles con acceso de operación de inventario
_STAFF_ROLES = {"Administrador", "Encargado de Sucursal", "Cajero"}


def _get_inventory_or_404(db: Session, inventory_id: int) -> Inventory:
    inv = db.get(Inventory, inventory_id)
    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro de inventario no encontrado")
    return inv


def _lock_inventory_row(db: Session, inventory: Inventory) -> Inventory:
    """Re-lee la fila con SELECT ... FOR UPDATE para serializar decrementos de stock."""
    locked = (
        db.query(Inventory)
        .filter(Inventory.id == inventory.id)
        .with_for_update()
        .first()
    )
    if locked is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro de inventario no encontrado")
    return locked


def _get_or_create_inventory(db: Session, variant_id: int, branch_id: int) -> Inventory:
    inv = (
        db.query(Inventory)
        .filter(Inventory.variant_id == variant_id, Inventory.branch_id == branch_id)
        .with_for_update()
        .first()
    )
    if inv is None:
        try:
            inv = Inventory(variant_id=variant_id, branch_id=branch_id, available=0)
            db.add(inv)
            db.flush()
        except IntegrityError:
            db.rollback()
            inv = (
                db.query(Inventory)
                .filter(Inventory.variant_id == variant_id, Inventory.branch_id == branch_id)
                .with_for_update()
                .first()
            )
            if inv is None:
                raise
    return inv


def apply_movement(db: Session, inventory: Inventory, movement_type: str, quantity: int,
                   reason: str | None, user_id: int | None, commit: bool = True) -> InventoryMovement:
    """Aplica un delta con signo al inventario y registra el movimiento (CU21)."""
    if quantity == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El movimiento debe ser distinto de 0")

    inventory = _lock_inventory_row(db, inventory)
    new_value = inventory.available + quantity
    if new_value < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stock insuficiente: disponible actual {inventory.available}",
        )

    inventory.available = new_value
    movement = InventoryMovement(
        inventory_id=inventory.id,
        movement_type=movement_type,
        quantity=quantity,
        reason=reason,
        user_id=user_id,
    )
    db.add(movement)
    if commit:
        db.commit()
        db.refresh(movement)
    return movement


# ======================================================================
# DISPONIBILIDAD PÚBLICA (CU11)
# ======================================================================


@router.get(
    "/availability",
    response_model=list[AvailabilityItem],
    summary="Disponibilidad por variante y sucursal (CU11)",
)
def get_availability(
    product_id: Optional[int] = None,
    branch_id: Optional[int] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Inventory, ProductVariant, Product, Branch)
        .join(ProductVariant, Inventory.variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .join(Branch, Inventory.branch_id == Branch.id)
        .filter(Product.is_active.is_(True), ProductVariant.is_active.is_(True))
        .filter(Inventory.available > 0)
    )

    if product_id:
        query = query.filter(Product.id == product_id)
    if branch_id:
        query = query.filter(Inventory.branch_id == branch_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(Product.name.ilike(like) | ProductVariant.sku.ilike(like))

    results: list[AvailabilityItem] = []
    for inv, variant, product, branch in query.all():
        results.append(
            AvailabilityItem(
                variant_id=variant.id,
                product_id=product.id,
                product_name=product.name,
                image_url=product.image_url,
                size_name=variant.size_name,
                color_name=variant.color_name,
                sku=variant.sku,
                branch_id=inv.branch_id,
                branch_name=branch.name if branch else None,
                city=branch.city if branch else None,
                available=inv.available,
                price=variant.effective_price,
            )
        )
    return results


# ======================================================================
# ADMIN: GESTIÓN DE INVENTARIO
# ======================================================================


@router.get(
    "/",
    response_model=list[InventoryResponse],
    summary="Listar inventario (admin / encargado)",
)
def list_inventory(
    branch_id: Optional[int] = None,
    product_id: Optional[int] = None,
    low_stock_only: bool = False,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Inventory, ProductVariant, Product, Branch)
        .join(ProductVariant, Inventory.variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .join(Branch, Inventory.branch_id == Branch.id)
    )
    if branch_id:
        query = query.filter(Inventory.branch_id == branch_id)
    if product_id:
        query = query.filter(Product.id == product_id)
    if low_stock_only:
        query = query.filter(Inventory.available <= 5)

    rows = query.order_by(Product.name, ProductVariant.id).all()

    def _to_response(inv: Inventory, variant: ProductVariant, product: Product, branch: Branch):
        return InventoryResponse(
            id=inv.id,
            variant_id=inv.variant_id,
            branch_id=inv.branch_id,
            available=inv.available,
            product_id=product.id,
            product_name=product.name,
            image_url=product.image_url,
            sku=variant.sku,
            size_name=variant.size_name,
            color_name=variant.color_name,
            branch_name=branch.name if branch else None,
            city=branch.city if branch else None,
            effective_price=variant.effective_price,
        )

    return [_to_response(inv, variant, product, branch) for inv, variant, product, branch in rows]


@router.post(
    "/",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar stock inicial de una variante en una sucursal (admin)",
)
def create_inventory(
    payload: InventoryCreate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not db.get(ProductVariant, payload.variant_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Variante inválida")
    if not db.get(Branch, payload.branch_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sucursal inválida")

    existing = (
        db.query(Inventory)
        .filter(Inventory.variant_id == payload.variant_id, Inventory.branch_id == payload.branch_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un registro de inventario para esa variante y sucursal",
        )

    inventory = Inventory(variant_id=payload.variant_id, branch_id=payload.branch_id, available=payload.available)
    db.add(inventory)
    db.flush()
    if payload.available > 0:
        db.add(
            InventoryMovement(
                inventory_id=inventory.id,
                movement_type="INGRESO",
                quantity=payload.available,
                reason="Stock inicial",
                user_id=_admin.id,
            )
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un registro de inventario para esa variante y sucursal",
        )
    db.refresh(inventory)
    return _inventory_response(db, inventory)


@router.patch(
    "/{inventory_id}",
    response_model=InventoryResponse,
    summary="Ajustar stock absoluto de un registro (admin)",
)
def update_inventory(
    inventory_id: int,
    payload: InventoryUpdate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    inventory = _get_inventory_or_404(db, inventory_id)
    delta = payload.available - inventory.available
    if delta != 0:
        apply_movement(
            db, inventory, "AJUSTE", delta,
            reason=f"Ajuste de stock a {payload.available}", user_id=_admin.id, commit=False,
        )
    db.commit()
    db.refresh(inventory)
    return _inventory_response(db, inventory)


def _inventory_response(db: Session, inventory: Inventory) -> InventoryResponse:
    variant = db.get(ProductVariant, inventory.variant_id)
    product = db.get(Product, variant.product_id) if variant else None
    branch = db.get(Branch, inventory.branch_id)
    return InventoryResponse(
        id=inventory.id,
        variant_id=inventory.variant_id,
        branch_id=inventory.branch_id,
        available=inventory.available,
        product_id=product.id if product else None,
        product_name=product.name if product else None,
        image_url=product.image_url if product else None,
        sku=variant.sku if variant else None,
        size_name=variant.size_name if variant else None,
        color_name=variant.color_name if variant else None,
        branch_name=branch.name if branch else None,
        city=branch.city if branch else None,
        effective_price=variant.effective_price if variant else None,
    )


# ======================================================================
# MOVIMIENTOS DE INVENTARIO (CU21)
# ======================================================================


@router.get(
    "/movements",
    response_model=list[InventoryMovementResponse],
    summary="Listar movimientos de inventario (admin / encargado)",
)
def list_movements(
    inventory_id: Optional[int] = None,
    movement_type: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role_name not in _STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere rol de administrador o de sucursal")

    query = db.query(InventoryMovement)
    if inventory_id:
        query = query.filter(InventoryMovement.inventory_id == inventory_id)
    if movement_type:
        query = query.filter(InventoryMovement.movement_type == movement_type)

    rows = query.order_by(InventoryMovement.created_at.desc()).all()
    resp = []
    for mov in rows:
        user_name = None
        if mov.user_id:
            u = db.get(User, mov.user_id)
            user_name = u.full_name if u else None
        resp.append(
            InventoryMovementResponse(
                id=mov.id,
                inventory_id=mov.inventory_id,
                movement_type=mov.movement_type,
                quantity=mov.quantity,
                reason=mov.reason,
                user_id=mov.user_id,
                user_name=user_name,
                created_at=mov.created_at,
            )
        )
    return resp


@router.post(
    "/movements",
    response_model=InventoryMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar movimiento manual (CU21) — admin / encargado",
)
def create_movement(
    payload: InventoryMovementCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role_name not in _STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere rol de administrador o de sucursal")

    inventory = _get_inventory_or_404(db, payload.inventory_id)
    movement_type = payload.movement_type
    quantity = payload.quantity

    if movement_type in ("INGRESO", "DEVOLUCION") and quantity < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{movement_type} debe incrementar stock (delta positivo)")
    if movement_type in ("SALIDA", "RESERVA") and quantity > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{movement_type} debe decrementar stock (delta negativo)")

    movement = apply_movement(db, inventory, movement_type, quantity, payload.reason, user.id, commit=True)
    return InventoryMovementResponse(
        id=movement.id,
        inventory_id=movement.inventory_id,
        movement_type=movement.movement_type,
        quantity=movement.quantity,
        reason=movement.reason,
        user_id=movement.user_id,
        user_name=user.full_name,
        created_at=movement.created_at,
    )