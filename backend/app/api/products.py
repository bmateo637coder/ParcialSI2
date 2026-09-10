from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.catalog import (
    Category,
    Color,
    Product,
    ProductVariant,
    Provider,
    Season,
    Size,
)
from app.schemas import (
    CategoryCreate,
    CategoryResponse,
    ColorCreate,
    ColorResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    ProviderCreate,
    ProviderResponse,
    SeasonCreate,
    SeasonResponse,
    SizeCreate,
    SizeResponse,
    VariantCreate,
    VariantResponse,
    VariantUpdate,
)

router = APIRouter()


def _get_product_or_404(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return product


# ======================================================================
# PRODUCTS
# ======================================================================


@router.get("/", response_model=list[ProductResponse], summary="Listar productos del catálogo")
def get_products(
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    season_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(Product.name.ilike(like) | Product.description.ilike(like))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if season_id:
        query = query.filter(Product.season_id == season_id)
    return query.order_by(Product.created_at.desc()).all()


@router.get("/{product_id}", response_model=ProductResponse, summary="Obtener un producto")
def get_product(product_id: int, db: Session = Depends(get_db)):
    return _get_product_or_404(db, product_id)


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear producto (admin)",
)
def create_product(
    payload: ProductCreate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Actualizar producto (admin)",
)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = _get_product_or_404(db, product_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar producto (admin)",
)
def delete_product(product_id: int, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    product = _get_product_or_404(db, product_id)
    db.delete(product)
    db.commit()


# ======================================================================
# PRODUCT VARIANTS
# ======================================================================


@router.get(
    "/{product_id}/variants",
    response_model=list[VariantResponse],
    summary="Listar variantes de un producto",
)
def get_variants(product_id: int, db: Session = Depends(get_db)):
    _get_product_or_404(db, product_id)
    return (
        db.query(ProductVariant)
        .filter(ProductVariant.product_id == product_id)
        .order_by(ProductVariant.id)
        .all()
    )


@router.post(
    "/{product_id}/variants",
    response_model=VariantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear variante del producto (admin)",
)
def create_variant(
    product_id: int,
    payload: VariantCreate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = _get_product_or_404(db, product_id)

    if not db.get(Size, payload.size_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Talla inválida")
    if not db.get(Color, payload.color_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Color inválido")

    variant = ProductVariant(product_id=product.id, **payload.model_dump())
    db.add(variant)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SKU duplicado. Usa un código de inventario único.",
        )
    db.refresh(variant)
    return variant


@router.patch(
    "/variants/{variant_id}",
    response_model=VariantResponse,
    summary="Actualizar variante (admin)",
)
def update_variant(
    variant_id: int,
    payload: VariantUpdate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variante no encontrada")
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(variant, field, value)
    db.commit()
    db.refresh(variant)
    return variant


@router.delete(
    "/variants/{variant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar variante (admin)",
)
def delete_variant(variant_id: int, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variante no encontrada")
    db.delete(variant)
    db.commit()


# ======================================================================
# CATALOG REFERENCE DATA
# ======================================================================


@router.get("/metadata/categories", response_model=list[CategoryResponse], summary="Categorías")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    for category in categories:
        category.products_count = len(category.products)
    return categories


@router.get("/metadata/seasons", response_model=list[SeasonResponse], summary="Temporadas")
def get_seasons(db: Session = Depends(get_db)):
    return db.query(Season).order_by(Season.name).all()


@router.get("/metadata/sizes", response_model=list[SizeResponse], summary="Tallas")
def get_sizes(db: Session = Depends(get_db)):
    return db.query(Size).order_by(Size.name).all()


@router.get("/metadata/colors", response_model=list[ColorResponse], summary="Colores")
def get_colors(db: Session = Depends(get_db)):
    return db.query(Color).order_by(Color.name).all()


@router.get("/metadata/providers", response_model=list[ProviderResponse], summary="Proveedores")
def get_providers(db: Session = Depends(get_db)):
    return db.query(Provider).order_by(Provider.name).all()


# ======================================================================
# CATALOG REFERENCE CREATE (admin)
# ======================================================================


@router.post(
    "/catalog/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear categoría (admin)",
)
def create_category(payload: CategoryCreate, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.post(
    "/catalog/seasons",
    response_model=SeasonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear temporada (admin)",
)
def create_season(payload: SeasonCreate, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    season = Season(**payload.model_dump())
    db.add(season)
    db.commit()
    db.refresh(season)
    return season


@router.post(
    "/catalog/sizes",
    response_model=SizeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear talla (admin)",
)
def create_size(payload: SizeCreate, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    size = Size(**payload.model_dump())
    db.add(size)
    db.commit()
    db.refresh(size)
    return size


@router.post(
    "/catalog/colors",
    response_model=ColorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear color (admin)",
)
def create_color(payload: ColorCreate, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    color = Color(**payload.model_dump())
    db.add(color)
    db.commit()
    db.refresh(color)
    return color


@router.post(
    "/catalog/providers",
    response_model=ProviderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear proveedor (admin)",
)
def create_provider(payload: ProviderCreate, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    provider = Provider(**payload.model_dump())
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider