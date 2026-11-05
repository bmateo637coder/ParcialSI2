from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.sql import func
from app.core.database import Base


class AnalyticsRun(Base):
    __tablename__ = "analytics_runs"
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    model_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
