import json
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tenant import require_plan_profesional
from app.models.report import GeneratedReport
from app.schemas import ReporteIARequest, ReporteIAResponse, ReporteIAExportRequest
from app.services.report_builder import build_report

DOWNLOADS_DIR = Path(__file__).resolve().parents[2] / "static" / "downloads"
router = APIRouter()


@router.post("/ia", response_model=ReporteIAResponse)
def generar_reporte_ia(req: ReporteIARequest, ctx=Depends(require_plan_profesional), db: Session = Depends(get_db)):
    result = build_report(db, ctx["empresa"].id, req.pregunta_natural, req.filtros)
    report = GeneratedReport(empresa_id=ctx["empresa"].id, user_id=ctx["user"].id,
        result_json=json.dumps(result, ensure_ascii=False))
    db.add(report)
    db.flush()
    result["solicitud_id"] = report.id
    report.result_json = json.dumps(result, ensure_ascii=False)
    db.commit()
    return result


def _load_report(db, report_id, ctx):
    record = db.query(GeneratedReport).filter(GeneratedReport.id == report_id,
        GeneratedReport.empresa_id == ctx["empresa"].id).first()
    if record is None:
        raise HTTPException(404, "Reporte no encontrado")
    return json.loads(record.result_json)


@router.post("/ia/export")
def exportar_reporte_ia(req: ReporteIAExportRequest, ctx=Depends(require_plan_profesional), db: Session = Depends(get_db)):
    if req.formato not in {"pdf", "excel"}:
        raise HTTPException(422, "Formato debe ser pdf o excel")
    _load_report(db, req.solicitud_id, ctx)
    return {"mensaje": "Reporte preparado", "formato": req.formato,
        "archivo_url": f"/api/reportes/ia/{req.solicitud_id}/archivo?formato={req.formato}"}


@router.get("/ia/{report_id}/archivo")
def descargar_reporte(report_id: int, formato: str = "excel", ctx=Depends(require_plan_profesional), db: Session = Depends(get_db)):
    data = _load_report(db, report_id, ctx)
    stream = BytesIO()
    title = data["tipo_reporte"].replace("_", " ")
    metadata = [ctx["empresa"].razon_social, data["pregunta_natural"],
        ", ".join(f"{k}: {v}" for k, v in data["filtros_aplicados"].items())]
    columns, rows = data["columnas"], data["filas"]
    if formato == "excel":
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        from openpyxl.utils import get_column_letter

        def safe(value):
            return "'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@")) else value

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Reporte"
        for value in [title, *metadata]:
            sheet.append([safe(value)])
        sheet.append([])
        sheet.append(columns)
        for row in rows:
            sheet.append([safe(row.get(key)) for key in columns])
        for cell in sheet[6]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="5B2333")
        for index, key in enumerate(columns, 1):
            sheet.column_dimensions[get_column_letter(index)].width = min(50, max(18, len(key) + 3))
        sheet.freeze_panes = "A7"
        sheet.auto_filter.ref = f"A6:{get_column_letter(len(columns))}{sheet.max_row}"
        workbook.save(stream)
        content_type, extension = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
    elif formato == "pdf":
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle

        styles = getSampleStyleSheet()
        def paragraph(value):
            return Paragraph(escape(str(value)), styles["BodyText"])
        content = [Paragraph(escape(title), styles["Title"]), *[paragraph(v) for v in metadata], Spacer(1, 16)]
        table = LongTable([[paragraph(c) for c in columns], *[[paragraph(row.get(k, "")) for k in columns] for row in rows]],
            repeatRows=1, colWidths=[740 / len(columns)] * len(columns))
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eadfe3")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        content.append(table)
        SimpleDocTemplate(stream, pagesize=landscape(A4), leftMargin=40, rightMargin=40).build(content)
        content_type, extension = "application/pdf", "pdf"
    else:
        raise HTTPException(422, "Formato debe ser pdf o excel")
    stream.seek(0)
    return StreamingResponse(stream, media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="reporte-{report_id}.{extension}"'})
