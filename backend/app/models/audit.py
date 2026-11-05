from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func
from app.core.database import Base


class AuditEvent(Base):
    """Historial independiente: conserva autor y datos aunque se borre el recurso."""
    __tablename__ = 'audit_events'
    __table_args__ = (Index('ix_audit_tenant_date', 'empresa_id', 'created_at'),)

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, nullable=True, index=True)
    actor_id = Column(Integer, nullable=True, index=True)
    actor_name = Column(String(220), nullable=False)
    actor_role = Column(String(80), nullable=True)
    action = Column(String(30), nullable=False, index=True)
    entity = Column(String(80), nullable=False, index=True)
    entity_id = Column(String(80), nullable=True)
    description = Column(String(255), nullable=False)
    changes_json = Column(Text, nullable=False, default='{}')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
