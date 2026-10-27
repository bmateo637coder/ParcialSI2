from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.tenant import require_plan_profesional

router = APIRouter()


@router.post("/entrenar")
def entrenar_modelos(ctx = Depends(require_plan_profesional), db: Session = Depends(get_db)):
    return {
        "mensaje": "Entrenamiento con datos sintéticos iniciado",
        "tipo": ["SUPERVISADO", "NO_SUPERVISADO"],
        "algoritmos": ["LINEAR_REGRESSION", "RANDOM_FOREST", "KMEANS"],
        "metricas": {"mae": 0.0, "r2": 0.0, "silhouette": 0.0},
        "estado": "ENTRENADO"
    }


@router.get("/dashboard")
def dashboard_analitico(ctx = Depends(require_plan_profesional)):
    return {
        "kpi": {"ventas_mes": 0, "productos_vendidos": 0, "ticket_promedio": 0},
        "prediccion_demanda": [],
        "segmentacion": [],
        "anomalias": [],
        "recomendaciones": []
    }
