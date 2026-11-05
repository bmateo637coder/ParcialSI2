import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.audit import AuditEvent

router = APIRouter()


@router.get('')
def list_audit(user=Depends(get_current_user), db: Session=Depends(get_db),
    q: str=Query('', max_length=120), action: str|None=None, entity: str|None=None,
    actor_id: int|None=None, desde: datetime|None=None, hasta: datetime|None=None,
    page: int=Query(1, ge=1), page_size: int=Query(25, ge=1, le=100)):
    if user.role_name not in {'Administrador', 'Encargado de Sucursal', 'Administrador de Plataforma'}:
        raise HTTPException(403, 'Solo los responsables pueden consultar la bitácora')
    query = db.query(AuditEvent)
    if user.role_name != 'Administrador de Plataforma':
        query = query.filter(AuditEvent.empresa_id == user.empresa_id)
    if desde: desde = desde.replace(tzinfo=timezone.utc) if desde.tzinfo is None else desde.astimezone(timezone.utc)
    if hasta: hasta = hasta.replace(tzinfo=timezone.utc) if hasta.tzinfo is None else hasta.astimezone(timezone.utc)
    if desde and hasta and desde > hasta: raise HTTPException(422, 'El inicio debe ser anterior al fin')
    if q.strip():
        term = f'%{q.strip()}%'
        query = query.filter(or_(AuditEvent.actor_name.ilike(term), AuditEvent.description.ilike(term), AuditEvent.entity.ilike(term)))
    if action: query = query.filter(AuditEvent.action == action)
    if entity: query = query.filter(AuditEvent.entity == entity)
    if actor_id is not None: query = query.filter(AuditEvent.actor_id == actor_id)
    if desde: query = query.filter(AuditEvent.created_at >= desde)
    if hasta: query = query.filter(AuditEvent.created_at <= hasta)
    total = query.count()
    rows = query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).offset((page-1)*page_size).limit(page_size).all()
    return {'total': total, 'page': page, 'page_size': page_size, 'items': [
        {**{key: getattr(row, key) for key in ('id','empresa_id','actor_id','actor_name','actor_role','action','entity','entity_id','description','created_at')},
         'changes': json.loads(row.changes_json)} for row in rows]}
