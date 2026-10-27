from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class OperacionSync(Base):
    __tablename__ = "operaciones_sync"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    sucursal_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tipo_operacion = Column(String(20), nullable=False)  # RESERVA | VENTA_CONTADO
    payload_json = Column(Text, nullable=False)
    estado = Column(String(20), default="REGISTRADA_LOCAL", nullable=False)  # REGISTRADA_LOCAL | ENVIADA | CONFIRMADA | RECHAZADA | EN_CONFLICTO
    intentos = Column(Integer, default=0)
    fecha_local = Column(DateTime(timezone=True))
    fecha_sync = Column(DateTime(timezone=True))
    respuesta_servidor = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa")
    sucursal = relationship("Branch")
    usuario = relationship("User")
    conflicto = relationship("ConflictoSync", back_populates="operacion", uselist=False)


class ConflictoSync(Base):
    __tablename__ = "conflictos_sync"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    operacion_sync_id = Column(Integer, ForeignKey("operaciones_sync.id"), nullable=False, unique=True)
    motivo = Column(Text, nullable=False)
    stock_disponible = Column(Integer, default=0)
    cantidad_solicitada = Column(Integer, default=0)
    resuelto = Column(Boolean, default=False)
    resuelto_por = Column(Integer, ForeignKey("users.id"))
    fecha_resolucion = Column(DateTime(timezone=True))
    accion_tomada = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    empresa = relationship("Empresa")
    operacion = relationship("OperacionSync", back_populates="conflicto")
    resuelto_por_user = relationship("User")


class CambioPrenda(Base):
    __tablename__ = "cambios_prenda"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    venta_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fecha_solicitud = Column(DateTime(timezone=True), server_default=func.now())
    fecha_limite = Column(DateTime(timezone=True))
    estado = Column(String(20), default="PENDIENTE")  # PENDIENTE | APROBADO | RECHAZADO
    observaciones = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    empresa = relationship("Empresa")
    venta = relationship("Order")
    usuario = relationship("User")
