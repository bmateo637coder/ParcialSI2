from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Date, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

from .promotion import Promotion  # noqa: F401  (registro de modelos en la metadata)


class Provider(Base):
    __tablename__ = "providers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    contact_email = Column(String(100))
    nit = Column(String(30), unique=True)
    phone = Column(String(30))
    address = Column(String(180))
    is_active = Column(Boolean, default=True, nullable=False)
    products = relationship("Product", back_populates="provider")


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    products = relationship("Product", back_populates="category")


class Season(Base):
    __tablename__ = "seasons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # ej. Primavera-Verano 2026
    year = Column(Integer)
    description = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    is_active = Column(Boolean, default=True, nullable=False)
    products = relationship("Product", back_populates="season")


class Collection(Base):
    __tablename__ = "collections"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    season_id = Column(Integer, ForeignKey("seasons.id"))
    is_active = Column(Boolean, default=True, nullable=False)
    products = relationship("Product", back_populates="collection")

class Size(Base):
    __tablename__ = "sizes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), unique=True, nullable=False) # S, M, L, XL, 38, 40

class Color(Base):
    __tablename__ = "colors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    base_price = Column(Float, nullable=False)
    image_url = Column(String(500), nullable=True)

    # Claves foráneas (Relaciones)
    category_id = Column(Integer, ForeignKey("categories.id"))
    season_id = Column(Integer, ForeignKey("seasons.id"))
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones ORM
    category = relationship("Category", back_populates="products")
    season = relationship("Season", back_populates="products")
    collection = relationship("Collection", back_populates="products")
    provider = relationship("Provider", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product")


class ProviderAccount(Base):
    """
    Cuenta de portal proveedor: vincula a un usuario (rol Proveedor, PK) con
    la empresa proveedora. Un usuario proveedor gestiona los productos de UNA
    empresa.
    """

    __tablename__ = "provider_accounts"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="provider_account")
    provider = relationship("Provider", backref="accounts")


class ProductProposal(Base):
    """
    Propuesta de producto enviada por un proveedor. El administrador la aprueba
    (creando el Product) o la rechaza con un comentario.
    Estados: PENDIENTE, APROBADA, RECHAZADA.
    """

    __tablename__ = "product_proposals"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    base_price = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default="PENDIENTE")
    admin_comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    provider = relationship("Provider", backref="proposals")

class ProductVariant(Base):
    """
    Esta tabla es clave para una tienda de ropa. 
    Representa una prenda específica en un color y talla específicos (Ej: Camiseta X, Talla M, Color Rojo)
    """
    __tablename__ = "product_variants"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    size_id = Column(Integer, ForeignKey("sizes.id"), nullable=False)
    color_id = Column(Integer, ForeignKey("colors.id"), nullable=False)
    sku = Column(String(100), unique=True, index=True) # Código de inventario único
    price = Column(Float, nullable=True)  # Precio específico (si difiere del base)
    stock = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True, nullable=False)

    product = relationship("Product", back_populates="variants")
    size = relationship("Size")
    color = relationship("Color")

    @property
    def effective_price(self) -> float:
        return self.price if self.price is not None else self.product.base_price

    @property
    def size_name(self) -> str | None:
        return self.size.name if self.size else None

    @property
    def color_name(self) -> str | None:
        return self.color.name if self.color else None
