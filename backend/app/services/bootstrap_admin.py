from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.repositories.application_user import get_application_user_by_username


def ensure_bootstrap_admin(db: Session) -> tuple[ApplicationUser, bool]:
    user = get_application_user_by_username(db, settings.bootstrap_admin_username)
    created = user is None
    if user is None:
        user = ApplicationUser(username=settings.bootstrap_admin_username)
    user.email = settings.bootstrap_admin_email
    user.password_hash = hash_password(settings.bootstrap_admin_password)
    user.role = ApplicationUserRole.SUPER_ADMIN.value
    user.is_active = True
    user.module_accessi = True
    user.module_rete = True
    user.module_inventario = True
    user.module_dotazioni = True
    user.module_gis = True
    user.module_catasto = True
    user.module_utenze = True
    user.module_operazioni = True
    user.module_riordino = True
    user.module_ruolo = True
    user.module_presenze = True
    user.module_organigramma = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, created
