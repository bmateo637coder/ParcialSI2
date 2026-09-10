from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ======================================================================
# AUTH & USERS
# ======================================================================


class UserBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)


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
# BRANCHES
# ======================================================================


class BranchBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    address: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    is_active: bool = True


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    city: Optional[str] = Field(default=None, min_length=1, max_length=100)
    address: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None


class BranchResponse(BranchBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ======================================================================
# CATALOG (categories, seasons, sizes, colors, providers)
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


class SeasonCreate(SeasonBase):
    pass


class SeasonResponse(SeasonBase):
    id: int

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


class ProviderCreate(ProviderBase):
    pass


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


class CategoryBrief(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class SeasonBrief(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class ProductResponse(ProductBase):
    id: int
    category: Optional[CategoryBrief] = None
    season: Optional[SeasonBrief] = None

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


class VariantUpdate(BaseModel):
    size_id: Optional[int] = None
    color_id: Optional[int] = None
    sku: Optional[str] = Field(default=None, max_length=100, pattern=r"^[A-Za-z0-9\-]+$")
    price: Optional[float] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)


class VariantResponse(BaseModel):
    id: int
    product_id: int
    size_id: int
    color_id: int
    sku: Optional[str] = None
    price: Optional[float] = None
    stock: int
    effective_price: float
    size_name: Optional[str] = None
    color_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)