from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, require_admin
from app.models.user import Role, User
from app.schemas import RoleResponse, UserAdminCreate, UserAdminUpdate, UserResponse

router = APIRouter()


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return user


@router.get("/roles", response_model=list[RoleResponse], summary="Listar roles (admin)")
def list_roles(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(Role).order_by(Role.name).all()


@router.get("/", response_model=list[UserResponse], summary="Listar usuarios (admin)")
def list_users(
    q: Optional[str] = None,
    role_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            User.first_name.ilike(like) | User.last_name.ilike(like) | User.email.ilike(like)
        )
    if role_id:
        query = query.filter(User.role_id == role_id)
    if is_active is not None:
        query = query.filter(User.is_active.is_(is_active))
    return query.order_by(User.created_at.desc()).all()


@router.get("/{user_id}", response_model=UserResponse, summary="Obtener un usuario (admin)")
def get_user(user_id: int, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    return _get_user_or_404(db, user_id)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario con rol (admin)",
)
def create_user(
    payload: UserAdminCreate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not db.get(Role, payload.role_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rol inválido")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El correo ya está registrado"
        )

    user = User(
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        email=payload.email,
        phone=payload.phone.strip() if payload.phone else None,
        hashed_password=hash_password(payload.password),
        role_id=payload.role_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Actualizar usuario y rol (admin)",
)
def update_user(
    user_id: int,
    payload: UserAdminUpdate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(db, user_id)

    data = payload.model_dump(exclude_unset=True)

    if user.id == _admin.id:
        if data.get("role_id") is not None and data["role_id"] != user.role_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes cambiarte tu propio rol")
        if data.get("is_active") is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes desactivarte a ti mismo")
    if data.get("email"):
        email = data["email"]
        if email != user.email:
            other = db.query(User).filter(User.email == email).first()
            if other:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="El correo ya está registrado"
                )

    password = data.pop("password", None)
    if data.get("role_id") and not db.get(Role, data["role_id"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rol inválido")

    for field, value in data.items():
        setattr(user, field, value.strip() if isinstance(value, str) else value)
    if password:
        user.hashed_password = hash_password(password)

    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desactivar usuario (admin)",
)
def deactivate_user(user_id: int, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    if user.id == _admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes desactivarte a ti mismo")
    user.is_active = False
    db.commit()