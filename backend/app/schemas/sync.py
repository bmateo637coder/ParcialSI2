from pydantic import BaseModel
from typing import Optional


class ResolverConflictoRequest(BaseModel):
    accion: str  # AJUSTAR_CANTIDAD | RECHAZAR
    cantidad_aceptada: Optional[int] = None
    observaciones: Optional[str] = None
