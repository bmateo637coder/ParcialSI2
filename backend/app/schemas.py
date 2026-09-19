from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ======================================================================
# AUTH & USERS
# ======================================================================


class UserBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=30)


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=128)


class ResetPasswordResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    full_name: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: EmailStr
    user_id: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


# ======================================================================
# ADMIN USERS & ROLES (CU4)
# ======================================================================


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserAdminCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    phone: Optional[str] = Field(default=None, max_length=30)
    role_id: int


class UserAdminUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
    role_id: Optional[int] = None
    is_active: Optional[bool] = None


# ======================================================================
# BRANCHES
# ======================================================================


class BranchBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    address: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    latitude: Optional[Decimal] = Field(default=None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(default=None, ge=-180, le=180)
    is_active: bool = True


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    city: Optional[str] = Field(default=None, min_length=1, max_length=100)
    address: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    latitude: Optional[Decimal] = Field(default=None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(default=None, ge=-180, le=180)
    is_active: Optional[bool] = None


class BranchResponse(BranchBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ======================================================================
# CATALOG (categories, seasons, collections, sizes, colors, providers)
# ======================================================================


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: int
    products_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SeasonBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    year: Optional[int] = Field(default=None, ge=2000, le=2100)
    description: Optional[str] = Field(default=None, max_length=1000)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool = True


class SeasonCreate(SeasonBase):
    pass


class SeasonUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    year: Optional[int] = Field(default=None, ge=2000, le=2100)
    description: Optional[str] = Field(default=None, max_length=1000)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class SeasonResponse(SeasonBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CollectionBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    season_id: Optional[int] = None
    is_active: bool = True


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    season_id: Optional[int] = None
    is_active: Optional[bool] = None


class CollectionResponse(CollectionBase):
    id: int
    season: Optional["SeasonBrief"] = None

    model_config = ConfigDict(from_attributes=True)


class SizeBase(BaseModel):
    name: str = Field(min_length=1, max_length=20)


class SizeCreate(SizeBase):
    pass


class SizeResponse(SizeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ColorBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class ColorCreate(ColorBase):
    pass


class ColorResponse(ColorBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ProviderBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    contact_email: Optional[EmailStr] = None
    nit: Optional[str] = Field(default=None, max_length=30)
    phone: Optional[str] = Field(default=None, max_length=30)
    address: Optional[str] = Field(default=None, max_length=180)
    is_active: bool = True


class ProviderCreate(ProviderBase):
    pass


class ProviderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    contact_email: Optional[EmailStr] = None
    nit: Optional[str] = Field(default=None, max_length=30)
    phone: Optional[str] = Field(default=None, max_length=30)
    address: Optional[str] = Field(default=None, max_length=180)
    is_active: Optional[bool] = None


class ProviderResponse(ProviderBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ======================================================================
# PRODUCTS
# ======================================================================


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    base_price: float = Field(ge=0)
    image_url: Optional[str] = Field(default=None, max_length=500)
    category_id: Optional[int] = None
    season_id: Optional[int] = None
    collection_id: Optional[int] = None
    provider_id: Optional[int] = None
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    base_price: Optional[float] = Field(default=None, ge=0)
    image_url: Optional[str] = Field(default=None, max_length=500)
    category_id: Optional[int] = None
    season_id: Optional[int] = None
    collection_id: Optional[int] = None
    provider_id: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryBrief(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class SeasonBrief(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class CollectionBrief(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class ProductResponse(ProductBase):
    id: int
    category: Optional[CategoryBrief] = None
    season: Optional[SeasonBrief] = None
    collection: Optional[CollectionBrief] = None
    provider: Optional[ProviderResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ======================================================================
# PRODUCT VARIANTS
# ======================================================================


class VariantCreate(BaseModel):
    size_id: int
    color_id: int
    sku: Optional[str] = Field(default=None, max_length=100, pattern=r"^[A-Za-z0-9\-]+$")
    price: Optional[float] = Field(default=None, ge=0)
    stock: int = Field(default=0, ge=0)
    is_active: bool = True


class VariantUpdate(BaseModel):
    size_id: Optional[int] = None
    color_id: Optional[int] = None
    sku: Optional[str] = Field(default=None, max_length=100, pattern=r"^[A-Za-z0-9\-]+$")
    price: Optional[float] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class VariantResponse(BaseModel):
    id: int
    product_id: int
    size_id: int
    color_id: int
    sku: Optional[str] = None
    price: Optional[float] = None
    stock: int
    is_active: bool
    effective_price: float
    size_name: Optional[str] = None
    color_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ======================================================================
# INVENTORY (CU11, CU21)
# ======================================================================


class InventoryBase(BaseModel):
    variant_id: int
    branch_id: int


class InventoryCreate(InventoryBase):
    available: int = Field(default=0, ge=0)


class InventoryUpdate(BaseModel):
    available: Optional[int] = Field(default=None, ge=0)


class InventoryResponse(InventoryBase):
    id: int
    available: int
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    image_url: Optional[str] = None
    sku: Optional[str] = None
    size_name: Optional[str] = None
    color_name: Optional[str] = None
    branch_name: Optional[str] = None
    city: Optional[str] = None
    effective_price: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class AvailabilityItem(BaseModel):
    """Disponibilidad por variante y sucursal para el cliente (CU11)."""

    variant_id: int
    product_id: int
    product_name: str
    image_url: Optional[str] = None
    size_name: Optional[str] = None
    color_name: Optional[str] = None
    sku: Optional[str] = None
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    city: Optional[str] = None
    available: int
    price: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryMovementCreate(BaseModel):
    inventory_id: int
    movement_type: str = Field(pattern=r"^(INGRESO|SALIDA|AJUSTE|RESERVA|DEVOLUCION)$")
    quantity: int = Field(
        ...,
        description="Delta con signo: positivo incrementa inventario (INGRESO/DEVOLUCION), "
        "negativo lo decrementa (SALIDA/RESERVA). AJUSTE acepta ambos.",
    )
    reason: Optional[str] = Field(default=None, max_length=255)


class InventoryMovementResponse(BaseModel):
    id: int
    inventory_id: int
    movement_type: str
    quantity: int
    reason: Optional[str] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ======================================================================
# CART (CU16)
# ======================================================================


class CartItemCreate(BaseModel):
    variant_id: int
    quantity: int = Field(default=1, ge=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1)


class CartItemResponse(BaseModel):
    id: int
    variant_id: int
    quantity: int
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    image_url: Optional[str] = None
    size_name: Optional[str] = None
    color_name: Optional[str] = None
    sku: Optional[str] = None
    unit_price: float = 0
    discount: float = 0
    subtotal: float = 0
    added_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CartSummary(BaseModel):
    items: list[CartItemResponse] = []
    total_items: int = 0
    total_amount: float = 0
    total_discount: float = 0

    model_config = ConfigDict(from_attributes=True)


# ======================================================================
# RESERVATIONS (CU13, CU14, CU15)
# ======================================================================


class ReservationItemInput(BaseModel):
    variant_id: int
    quantity: int = Field(ge=1)


class ReservationCreate(BaseModel):
    branch_id: int
    items: list[ReservationItemInput] = Field(min_length=1)
    expiration_hours: int = Field(default=48, ge=1, le=720)


class ReservationItemResponse(BaseModel):
    id: int
    variant_id: int
    quantity: int
    unit_price: float
    subtotal: float
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    image_url: Optional[str] = None
    size_name: Optional[str] = None
    color_name: Optional[str] = None
    sku: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReservationResponse(BaseModel):
    id: int
    code: str
    client_id: int
    client_name: Optional[str] = None
    branch_id: int
    branch_name: Optional[str] = None
    status: str
    reservation_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    attend_date: Optional[datetime] = None
    items: list[ReservationItemResponse] = []
    total: float = 0
    item_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ======================================================================
# ORDERS & PAYMENTS (CU16)
# ======================================================================


class OrderItemInput(BaseModel):
    variant_id: int
    quantity: int = Field(ge=1)


class OrderCreate(BaseModel):
    order_type: str = Field(pattern=r"^(DIGITAL|PRESENCIAL)$", default="DIGITAL")
    branch_id: Optional[int] = None
    items: Optional[list[OrderItemInput]] = None
    payment_method: Optional[str] = Field(
        default="TARJETA", pattern=r"^(TARJETA|EFECTIVO|TRANSFERENCIA)$"
    )
    shipping_address: Optional[str] = Field(default=None, max_length=255)
    card_number: Optional[str] = Field(default=None, max_length=30)


class PosSaleCreate(BaseModel):
    """Venta presencial registrada por cajero (CU18)."""

    branch_id: int
    items: list[OrderItemInput] = Field(min_length=1)
    client_id: Optional[int] = None
    payment_method: str = Field(default="EFECTIVO", pattern=r"^(TARJETA|EFECTIVO|TRANSFERENCIA)$")
    card_number: Optional[str] = Field(default=None, max_length=30)


class PayRequest(BaseModel):
    """Completar o reintentar el pago de un pedido pendiente (CU19)."""

    payment_method: str = Field(default="TARJETA", pattern=r"^(TARJETA|EFECTIVO|TRANSFERENCIA)$")
    card_number: Optional[str] = Field(default=None, max_length=30)


class OrderStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(PENDIENTE|PAGADO|ENVIADO|ENTREGADO|CANCELADO)$")


class OrderItemResponse(BaseModel):
    id: int
    variant_id: int
    quantity: int
    unit_price: float
    discount: float = 0
    subtotal: float
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    image_url: Optional[str] = None
    size_name: Optional[str] = None
    color_name: Optional[str] = None
    sku: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentBrief(BaseModel):
    id: int
    method: str
    amount: float
    status: str
    stripe_payment_id: Optional[str] = None
    created_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    client_id: int
    client_name: Optional[str] = None
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    order_type: str
    status: str
    total: float
    shipping_address: Optional[str] = None
    receipt_number: Optional[str] = None
    created_at: Optional[datetime] = None
    items: list[OrderItemResponse] = []
    payment: Optional[PaymentBrief] = None

    model_config = ConfigDict(from_attributes=True)


# ======================================================================
# RECOMMENDATIONS (CU22)
# ======================================================================


class RecommendedItem(BaseModel):
    product_id: int
    name: str
    category: str
    base_price: float
    in_stock: bool
    reason: str
    score: float


class RecommendationResponse(BaseModel):
    source: str  # "featured" (sin historial) | "ai" (basado en historial)
    items: list[RecommendedItem] = []


# ======================================================================
# ASSISTANT (CU23)
# ======================================================================


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    conversation_id: int
    reply: str


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ChatConversationResponse(BaseModel):
    id: int
    created_at: Optional[datetime] = None
    messages: list[ChatMessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ======================================================================
# NOTIFICATIONS
# ======================================================================


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: Optional[str] = None
    is_read: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


CollectionResponse.model_rebuild()


# ======================================================================
# REPORTS (CU25) & VOICE COMMAND (CU24)
# ======================================================================


class ReportKpis(BaseModel):
    """Indicadores operativos: ventas, inventario y reservas."""

    total_sales: float
    total_orders: int
    avg_order: float
    reservations: int
    total_units_available: int
    low_stock_variants: int
    active_promotions: int = 0
    discount_amount: float = 0


class SalesPoint(BaseModel):
    date: str
    amount: float
    orders: int


class CategoryReport(BaseModel):
    category_id: Optional[int] = None
    category_name: str
    sales: float
    units: int


class TopProductReport(BaseModel):
    product_id: int
    name: str
    units: int
    revenue: float


class DashboardReport(BaseModel):
    empty: bool
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    kpis: ReportKpis
    sales_series: list[SalesPoint] = []
    by_category: list[CategoryReport] = []
    top_products: list[TopProductReport] = []
    narrative: Optional[str] = None


# ======================================================================
# PROMOTIONS
# ======================================================================


class PromotionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=1000)
    discount_type: str = Field(pattern=r"^(PERCENTAGE|FIXED)$")
    value: float = Field(gt=0)
    target_type: str = Field(pattern=r"^(GLOBAL|CATEGORY|PRODUCT)$")
    target_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool = True


class PromotionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=1000)
    discount_type: Optional[str] = Field(default=None, pattern=r"^(PERCENTAGE|FIXED)$")
    value: Optional[float] = Field(default=None, gt=0)
    target_type: Optional[str] = Field(default=None, pattern=r"^(GLOBAL|CATEGORY|PRODUCT)$")
    target_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class PromotionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    discount_type: str
    value: float
    target_type: str
    target_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ======================================================================
# PROVIDER PORTAL
# ======================================================================


class ProviderAccountCreate(BaseModel):
    user_id: int
    provider_id: int


class ProviderAccountResponse(BaseModel):
    user_id: int
    provider_id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProviderMeResponse(BaseModel):
    user: UserResponse
    role: str
    provider: Optional[ProviderResponse] = None


class ProposalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    base_price: float = Field(ge=0)


class ProposalReview(BaseModel):
    admin_comment: Optional[str] = Field(default=None, max_length=1000)


class ProposalResponse(BaseModel):
    id: int
    provider_id: int
    provider_name: Optional[str] = None
    name: str
    description: Optional[str] = None
    base_price: float
    status: str
    admin_comment: Optional[str] = None
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VoiceCommand(BaseModel):
    """Comando de voz transcrito por el navegador (CU24)."""

    command: str = Field(min_length=1, max_length=500)


class VoiceReportIntent(BaseModel):
    recognized: bool
    report_type: Optional[str] = None  # VENTAS | INVENTARIO | RESERVAS
    message: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    branch_id: Optional[int] = None
    category_id: Optional[int] = None


class VoiceReportResponse(BaseModel):
    recognized: bool
    message: Optional[str] = None
    intent: VoiceReportIntent
    data: Optional[DashboardReport] = None