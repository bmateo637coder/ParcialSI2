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
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True, index=True)
    request_id = Column(String(36), unique=True, nullable=True)
    request_fingerprint = Column(String(64), nullable=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    order_type = Column(String(20), nullable=False, default="DIGITAL")
    status = Column(String(20), nullable=False, default="PENDIENTE")
    total = Column(Float, nullable=False, default=0.0)
    stock_deducted = Column(Boolean, nullable=False, default=False)
    subtotal = Column(Float, nullable=True)
    shipping_address = Column(String(255), nullable=True)
    es_offline = Column(Boolean, default=False)
    origen = Column(String(20), default="ONLINE")
    order_number = Column(String(30), nullable=True)
    payment_method = Column(String(30), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    empresa = relationship("Empresa")
    client = relationship("User", backref="orders", foreign_keys=[client_id])
    user = relationship("User", backref="orders_sync", foreign_keys=[user_id])
    branch = relationship("Branch", backref="orders")
    items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payment = relationship("Payment", back_populates="order", uselist=False)
    refunds = relationship('Refund', back_populates='order', order_by='Refund.id')


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
    cash_received = Column(Float, nullable=True)
    change_amount = Column(Float, nullable=False, default=0)
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


class Refund(Base):
    __tablename__ = 'refunds'
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False, index=True)
    payment_id = Column(Integer, ForeignKey('payments.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    request_id = Column(String(36), nullable=False, unique=True)
    fingerprint = Column(String(64), nullable=False)
    amount = Column(Float, nullable=False)
    reason = Column(String(500), nullable=False)
    source = Column(String(30), nullable=False, default='MANUAL')
    status = Column(String(30), nullable=False, default='PENDIENTE')
    reference = Column(String(100))
    error = Column(String(255))
    payouts_json = Column(Text, nullable=False, default='[]')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    order = relationship('Order', back_populates='refunds')
    items = relationship('RefundItem', back_populates='refund', cascade='all, delete-orphan')


class RefundItem(Base):
    __tablename__ = 'refund_items'
    id = Column(Integer, primary_key=True)
    refund_id = Column(Integer, ForeignKey('refunds.id'), nullable=False, index=True)
    order_item_id = Column(Integer, ForeignKey('order_items.id'), nullable=False)
    lot_key = Column(String(60), nullable=False)
    variant_id = Column(Integer, ForeignKey('product_variants.id'), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    amount = Column(Float, nullable=False)
    restock = Column(Boolean, nullable=False, default=False)
    restocked_quantity = Column(Integer, nullable=False, default=0)
    refund = relationship('Refund', back_populates='items')


class RefundStockReturn(Base):
    __tablename__ = 'refund_stock_returns'
    id = Column(Integer, primary_key=True)
    request_id = Column(String(36), nullable=False, unique=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    refund_item_id = Column(Integer, ForeignKey('refund_items.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
