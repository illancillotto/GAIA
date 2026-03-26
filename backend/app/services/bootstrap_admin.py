from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.repositories.application_user import get_application_user_by_username


def ensure_bootstrap_admin(db: Session) -> tuple[ApplicationUser, bool]:
    existing_user = get_application_user_by_username(db, settings.bootstrap_admin_username)
    if existing_user is not None:
        existing_user.email = settings.bootstrap_admin_email
        existing_user.password_hash = hash_password(settings.bootstrap_admin_password)
        existing_user.role = ApplicationUserRole.SUPER_ADMIN.value
        existing_user.is_active = True
        existing_user.module_accessi = True
        existing_user.module_rete = True
        existing_user.module_inventario = True
        existing_user.module_catasto = True
        db.add(existing_user)
        db.commit()
        db.refresh(existing_user)
        return existing_user, False

    user = ApplicationUser(
        username=settings.bootstrap_admin_username,
        email=settings.bootstrap_admin_email,
        password_hash=hash_password(settings.bootstrap_admin_password),
        role=ApplicationUserRole.SUPER_ADMIN.value,
        is_active=True,
        module_accessi=True,
        module_rete=True,
        module_inventario=True,
        module_catasto=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, True
