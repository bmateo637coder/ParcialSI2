from pydantic import BaseModel
from typing import List, Optional, Any


class ReporteIARequest(BaseModel):
    pregunta_natural: str
    filtros: Optional[dict] = None


class ReporteIAResponse(BaseModel):
    solicitud_id: int
    tipo_reporte: str
    empresa_id: int
    pregunta_natural: str
    columnas: List[str]
    filas: List[Any]
    grafico: dict
    filtros_aplicados: dict
    mensaje: str


class ReporteIAExportRequest(BaseModel):
    solicitud_id: int
    formato: str  # pdf | excel
