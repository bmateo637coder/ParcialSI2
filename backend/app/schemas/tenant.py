from pydantic import BaseModel
from typing import Optional
from datetime import date


class PlanBase(BaseModel):
    nombre: str
    max_sucursales: int = 2
    permite_reportes_ia: bool = False
    permite_analitica_ml: bool = False
    precio_mensual: float = 0.0
    descripcion: Optional[str] = None
    is_active: bool = True


class PlanCreate(PlanBase):
    pass


class PlanResponse(PlanBase):
    id: int

    class Config:
        from_attributes = True


class EmpresaBase(BaseModel):
    razon_social: str
    nit: str
    logo_url: Optional[str] = None
    email_contacto: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    is_active: bool = True


class EmpresaCreate(EmpresaBase):
    plan_id: int


class EmpresaResponse(EmpresaBase):
    id: int

    class Config:
        from_attributes = True


class SuscripcionResponse(BaseModel):
    id: int
    empresa_id: int
    plan_id: int
    fecha_inicio: date
    fecha_vencimiento: date
    estado: str

    class Config:
        from_attributes = True
