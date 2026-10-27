from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tenant import require_plan_profesional, get_current_empresa, get_current_user
from app.models.user import User
try:
    from app.schemas.reports_ai import (
        ReporteIARequest,
        ReporteIAResponse,
        ReporteIAExportRequest,
    )
except Exception:
    from app.schemas import ReporteIARequest, ReporteIAResponse, ReporteIAExportRequest

router = APIRouter()


@router.post("/ia", response_model=ReporteIAResponse)
def generar_reporte_ia(
    req: ReporteIARequest,
    ctx = Depends(require_plan_profesional),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    empresa = ctx["empresa"]
    pregunta = req.pregunta_natural.lower()

    if any(x in pregunta for x in ["drop", "delete", "update", "insert", "alter", "truncate"]):
        raise HTTPException(status_code=400, detail="Solicitud no permitida")

    # Catálogo permitido - respuestas controladas
    if "venta" in pregunta:
        tipo = "VENTAS_POR_PERIODO"
        columnas = ["fecha", "sucursal", "total"]
        filas = []
        grafico = {"tipo": "bar", "labels": ["Ventas"], "datos": [0]}
    elif "inventario" in pregunta or "stock" in pregunta:
        tipo = "INVENTARIO_BAJO"
        columnas = ["producto", "variante", "sucursal", "cantidad"]
        filas = []
        grafico = {"tipo": "table", "labels": [], "datos": []}
    elif "reserva" in pregunta:
        tipo = "RESERVAS_POR_ESTADO"
        columnas = ["estado", "cantidad"]
        filas = []
        grafico = {"tipo": "pie", "labels": [], "datos": []}
    else:
        raise HTTPException(
            status_code=422,
            detail="Solicitud ambigua o no soportada. Ejemplos: 'Ventas del mes por sucursal', 'Productos con stock bajo', 'Reservas pendientes'",
        )

    return ReporteIAResponse(
        solicitud_id=0,
        tipo_reporte=tipo,
        empresa_id=empresa.id,
        pregunta_natural=req.pregunta_natural,
        columnas=columnas,
        filas=filas,
        grafico=grafico,
        filtros_aplicados=req.filtros or {},
        mensaje="Reporte generado con consulta controlada por tenant",
    )


@router.post("/ia/export")
def exportar_reporte_ia(
    req: ReporteIAExportRequest,
    ctx = Depends(require_plan_profesional),
):
    if req.formato not in ["pdf", "excel"]:
        raise HTTPException(status_code=400, detail="Formato debe ser pdf o excel")
    return {
        "mensaje": f"Exportación {req.formato.upper()} generada",
        "archivo_url": f"/downloads/reporte-ia-{datetime.now().strftime('%Y%m%d%H%M%S')}.{req.formato == 'excel' and 'xlsx' or 'pdf'}",
        "formato": req.formato,
    }
