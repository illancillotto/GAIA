from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser


def get_application_user_by_username(db: Session, username: str) -> ApplicationUser | None:
    statement = select(ApplicationUser).where(ApplicationUser.username == username)
    return db.execute(statement).scalar_one_or_none()


def get_application_user_by_id(db: Session, user_id: int) -> ApplicationUser | None:
    statement = select(ApplicationUser).where(ApplicationUser.id == user_id)
    return db.execute(statement).scalar_one_or_none()
