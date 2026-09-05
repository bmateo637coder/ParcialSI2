from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Provider(Base):
    __tablename__ = "providers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    contact_email = Column(String(100))
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
    products = relationship("Product", back_populates="season")

class Collection(Base):
    __tablename__ = "collections"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    season_id = Column(Integer, ForeignKey("seasons.id"))
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
    
    # Claves foráneas (Relaciones)
    category_id = Column(Integer, ForeignKey("categories.id"))
    season_id = Column(Integer, ForeignKey("seasons.id"))
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones ORM
    category = relationship("Category", back_populates="products")
    season = relationship("Season", back_populates="products")
    collection = relationship("Collection", back_populates="products")
    provider = relationship("Provider", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product")

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

    product = relationship("Product", back_populates="variants")
    size = relationship("Size")
    color = relationship("Color")
