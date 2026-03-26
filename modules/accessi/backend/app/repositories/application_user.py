from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.application_user import ApplicationUser
from app.schemas.users import ApplicationUserCreate, ApplicationUserUpdate


def get_application_user_by_username(db: Session, username: str) -> ApplicationUser | None:
    statement = select(ApplicationUser).where(ApplicationUser.username == username)
    return db.execute(statement).scalar_one_or_none()


def get_application_user_by_email(db: Session, email: str) -> ApplicationUser | None:
    statement = select(ApplicationUser).where(ApplicationUser.email == email)
    return db.execute(statement).scalar_one_or_none()


def get_application_user_by_id(db: Session, user_id: int) -> ApplicationUser | None:
    statement = select(ApplicationUser).where(ApplicationUser.id == user_id)
    return db.execute(statement).scalar_one_or_none()


def list_application_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    role: str | None = None,
    is_active: bool | None = None,
) -> tuple[list[ApplicationUser], int]:
    query = select(ApplicationUser)
    count_query = select(func.count(ApplicationUser.id))
    if role is not None:
        query = query.where(ApplicationUser.role == role)
        count_query = count_query.where(ApplicationUser.role == role)
    if is_active is not None:
        query = query.where(ApplicationUser.is_active == is_active)
        count_query = count_query.where(ApplicationUser.is_active == is_active)

    items = db.execute(query.order_by(ApplicationUser.id).offset(skip).limit(limit)).scalars().all()
    total = db.execute(count_query).scalar_one()
    return items, total


def create_application_user(db: Session, payload: ApplicationUserCreate) -> ApplicationUser:
    user = ApplicationUser(
        username=payload.username,
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
        module_accessi=payload.module_accessi,
        module_rete=payload.module_rete,
        module_inventario=payload.module_inventario,
        module_catasto=payload.module_catasto,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_application_user(db: Session, user: ApplicationUser, payload: ApplicationUserUpdate) -> ApplicationUser:
    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    for key, value in data.items():
        setattr(user, key, value)
    if password:
        user.password_hash = hash_password(password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_application_user(db: Session, user: ApplicationUser) -> None:
    db.delete(user)
    db.commit()
