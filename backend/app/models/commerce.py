from datetime import timedelta

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CartItem(Base):
    """Item del carrito de un cliente (CU16). UNIQUE por (cliente, variante)."""

    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("client_id", "variant_id", name="uq_cart_item_per_client"),
    )

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    variant = relationship("ProductVariant", backref="cart_items")


class Reservation(Base):
    """
    Cabecera de reserva multi-prenda (CU13). El detalle vive en ReservationItem.
    Estados (según el enunciado): PENDIENTE, ATENDIDA, CANCELADA, VENCIDA.
    """

    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    status = Column(String(20), nullable=False, default="PENDIENTE")
    reservation_date = Column(DateTime(timezone=True), server_default=func.now())
    expiration_date = Column(DateTime(timezone=True), nullable=False)
    attend_date = Column(DateTime(timezone=True), nullable=True)

    client = relationship("User", backref="reservations")
    branch = relationship("Branch", backref="reservations")
    items = relationship(
        "ReservationItem",
        back_populates="reservation",
        cascade="all, delete-orphan",
    )

    @property
    def total(self) -> float:
        return round(sum(item.subtotal for item in self.items), 2)

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)


class ReservationItem(Base):
    """Prenda (variante) reservada dentro de una reserva."""

    __tablename__ = "reservation_items"

    id = Column(Integer, primary_key=True, index=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    reservation = relationship("Reservation", back_populates="items")
    variant = relationship("ProductVariant")

    @property
    def subtotal(self) -> float:
        return round(self.quantity * self.unit_price, 2)


class Order(Base):
    """
    Pedido de compra (CU16 y punto de venta). Tipos: DIGITAL, PRESENCIAL.
    Estados: PENDIENTE, PAGADO, ENVIADO, ENTREGADO, CANCELADO.
    """

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    order_type = Column(String(20), nullable=False, default="DIGITAL")
    status = Column(String(20), nullable=False, default="PENDIENTE")
    total = Column(Float, nullable=False, default=0.0)
    shipping_address = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("User", backref="orders")
    branch = relationship("Branch", backref="orders")
    items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payment = relationship("Payment", back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount = Column(Float, nullable=False, default=0.0)
    promotion_id = Column(Integer, nullable=True)

    order = relationship("Order", back_populates="items")
    variant = relationship("ProductVariant")

    @property
    def subtotal(self) -> float:
        return round(self.quantity * self.unit_price - float(self.discount or 0.0), 2)


class Payment(Base):
    """Pago de un pedido. Un pedido puede tener máximo un pago activo."""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(String(30), nullable=False)  # TARJETA, EFECTIVO, TRANSFERENCIA
    status = Column(String(20), nullable=False, default="PENDIENTE")
    stripe_payment_id = Column(String(80))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship("Order", back_populates="payment")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(120), nullable=False)
    message = Column(Text)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="notifications")