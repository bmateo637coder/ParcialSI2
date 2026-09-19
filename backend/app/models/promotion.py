from sqlalchemy import Column, Integer, String, Float, Boolean, Text, Date, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class Promotion(Base):
    """
    Promoción (CU Admin). Aplica un descuento porcentual o fijo sobre uno o más
    productos según su alcance:

    - GLOBAL  : todos los productos activos.
    - CATEGORY: productos de la categoría indicada en target_id.
    - PRODUCT : el producto indicado en target_id.

    La vigencia se controla con start_date/end_date (fechas inclusivas) e
    is_active (habilitado por el administrador).
    """

    __tablename__ = "promotions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    discount_type = Column(String(20), nullable=False)  # PERCENTAGE | FIXED
    value = Column(Float, nullable=False)
    target_type = Column(String(20), nullable=False)  # GLOBAL | CATEGORY | PRODUCT
    target_id = Column(Integer, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())