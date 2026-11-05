"""Auditoría de cambios ORM en la misma transacción que la operación."""
import json
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from app.models.audit import AuditEvent

_HIDDEN = {'hashed_password', 'password', 'token', 'stripe_payment_id', 'result_json',
           'payload_json', 'respuesta_servidor', 'detalle_json'}
_IGNORED = {'audit_events', 'notifications', 'chat_messages', 'chat_conversations'}


def identify_actor(db, user):
    db.info['audit_actor'] = {'id': user.id, 'name': user.full_name,
        'role': user.role_name, 'empresa_id': user.empresa_id}


def _value(value):
    if isinstance(value, (date, datetime)): return value.isoformat()
    if isinstance(value, Decimal): return str(value)
    if isinstance(value, str): return value[:1000]
    return value if isinstance(value, (int, float, bool, type(None))) else str(value)[:1000]


def log_action(db, action, entity, entity_id, description, changes=None, empresa_id=None):
    actor = db.info.get('audit_actor')
    if not actor: return
    db.add(AuditEvent(empresa_id=empresa_id if empresa_id is not None else actor['empresa_id'],
        actor_id=actor['id'], actor_name=actor['name'], actor_role=actor['role'],
        action=action, entity=entity, entity_id=str(entity_id) if entity_id is not None else None,
        description=description[:255], changes_json=json.dumps(changes or {}, ensure_ascii=False, default=str)))


@event.listens_for(Session, 'after_flush')
def capture_changes(db, context):
    if not db.info.get('audit_actor'): return
    for group, action in ((list(db.new), 'CREAR'), (list(db.dirty), 'ACTUALIZAR'), (list(db.deleted), 'ELIMINAR')):
        for obj in group:
            table = getattr(obj, '__tablename__', '')
            if not table or table in _IGNORED: continue
            state = inspect(obj)
            changes = {}
            if action == 'ACTUALIZAR' and 'hashed_password' in state.attrs and state.attrs.hashed_password.history.has_changes():
                changes['credenciales'] = {'antes': '[oculto]', 'despues': 'Contraseña actualizada'}
            for col in state.mapper.column_attrs:
                if col.key in _HIDDEN: continue
                history = state.attrs[col.key].history
                current = _value(getattr(obj, col.key, None))
                if action == 'ACTUALIZAR':
                    if not history.has_changes(): continue
                    previous = _value(history.deleted[0]) if history.deleted else None
                    changes[col.key] = {'antes': previous, 'despues': current}
                else:
                    changes[col.key] = {'antes': current if action == 'ELIMINAR' else None,
                                        'despues': current if action == 'CREAR' else None}
            if not changes: continue
            company = getattr(obj, 'empresa_id', None)
            # Las relaciones de objetos recién insertados aún pueden ser None en
            # after_flush. Sus FK ya están disponibles; no dependemos del lazy load.
            from app.models.branch import Branch
            if company is None and table in {'inventory', 'reservations'}:
                branch = db.get(Branch, obj.branch_id)
                if branch is not None: company = branch.empresa_id
            log_action(db, action, table, getattr(obj, 'id', None),
                f'{action.capitalize()} {table} #{getattr(obj, "id", "")}', changes, company)
