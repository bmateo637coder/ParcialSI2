from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    razon_social = Column(String, nullable=False)
    nit = Column(String, unique=True, nullable=False, index=True)
    logo_url = Column(String)
    email_contacto = Column(String)
    telefono = Column(String)
    direccion = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    sucursales = relationship("Branch", back_populates="empresa")
    usuarios = relationship("User", back_populates="empresa")
    suscripcion = relationship("Suscripcion", back_populates="empresa", uselist=False)


class Plan(Base):
    __tablename__ = "planes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)  # BASICO | PROFESIONAL
    max_sucursales = Column(Integer, default=2)
    permite_reportes_ia = Column(Boolean, default=False)
    permite_analitica_ml = Column(Boolean, default=False)
    precio_mensual = Column(Float, default=0.0)
    descripcion = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    suscripciones = relationship("Suscripcion", back_populates="plan")


class Suscripcion(Base):
    __tablename__ = "suscripciones"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, unique=True)
    plan_id = Column(Integer, ForeignKey("planes.id"), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    estado = Column(String, default="ACTIVA")  # ACTIVA | VENCIDA | SUSPENDIDA | CANCELADA
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="suscripcion")
    plan = relationship("Plan", back_populates="suscripciones")
