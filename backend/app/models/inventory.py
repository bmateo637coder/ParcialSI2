from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Inventory(Base):
    """
    Existencia REAL de una variante en una sucursal concreta.
    Reemplaza el stock "global" como fuente de verdad para CU11/CU13/CU15/CU21.
    """

    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("variant_id", "branch_id", name="uq_inventory_variant_branch"),
    )

    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    available = Column(Integer, nullable=False, default=0)

    variant = relationship("ProductVariant", backref="inventory")
    branch = relationship("Branch", backref="inventory")
    movements = relationship(
        "InventoryMovement", back_populates="inventory", cascade="all, delete-orphan"
    )


class InventoryMovement(Base):
    """Registro de ingreso / salida / ajuste / reserva / devolución de stock (CU21)."""

    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=False)
    movement_type = Column(String(20), nullable=False)  # INGRESO, SALIDA, AJUSTE, RESERVA, DEVOLUCION
    quantity = Column(Integer, nullable=False)
    reason = Column(String(255))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    inventory = relationship("Inventory", back_populates="movements")
    user = relationship("User", backref="inventory_movements")