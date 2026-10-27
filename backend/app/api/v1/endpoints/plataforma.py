from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tenant import Empresa, Plan, Suscripcion
from app.models.user import Role, User
from app.schemas import EmpresaCreate, EmpresaResponse, PlanCreate, PlanResponse, SuscripcionResponse

router = APIRouter()


@router.post("/planes", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def crear_plan(plan: PlanCreate, db: Session = Depends(get_db)):
    nuevo_plan = Plan(**plan.model_dump())
    db.add(nuevo_plan)
    db.commit()
    db.refresh(nuevo_plan)
    return nuevo_plan


@router.get("/planes", response_model=List[PlanResponse])
def listar_planes(db: Session = Depends(get_db), solo_activos: bool = True):
    query = db.query(Plan)
    if solo_activos:
        query = query.filter(Plan.is_active == True)
    return query.all()


@router.post("/empresas", response_model=EmpresaResponse, status_code=status.HTTP_201_CREATED)
def registrar_empresa(data: EmpresaCreate, db: Session = Depends(get_db)):
    if db.query(Empresa).filter(Empresa.nit == data.nit).first():
        raise HTTPException(status_code=400, detail="Ya existe una empresa con ese NIT")

    plan = db.query(Plan).filter(Plan.id == data.plan_id, Plan.is_active == True).first()
    if not plan:
        raise HTTPException(status_code=400, detail="Plan no válido o inactivo")

    empresa = Empresa(
        razon_social=data.razon_social,
        nit=data.nit,
        logo_url=data.logo_url,
        email_contacto=data.email_contacto,
        telefono=data.telefono,
        direccion=data.direccion,
        is_active=data.is_active,
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)

    suscripcion = Suscripcion(
        empresa_id=empresa.id,
        plan_id=plan.id,
        fecha_inicio=date.today(),
        fecha_vencimiento=date.today() + timedelta(days=30),
        estado="ACTIVA",
    )
    db.add(suscripcion)
    db.commit()

    return empresa


@router.get("/empresas", response_model=List[EmpresaResponse])
def listar_empresas(db: Session = Depends(get_db)):
    return db.query(Empresa).all()


@router.get("/empresas/{empresa_id}/suscripcion", response_model=SuscripcionResponse)
def obtener_suscripcion_empresa(empresa_id: int, db: Session = Depends(get_db)):
    suscripcion = db.query(Suscripcion).filter(Suscripcion.empresa_id == empresa_id).first()
    if not suscripcion:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")
    return suscripcion
