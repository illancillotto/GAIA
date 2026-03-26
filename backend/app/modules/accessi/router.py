from fastapi import APIRouter

from app.modules.accessi.routes.admin_users import router as admin_users_router
from app.modules.accessi.routes.audit import router as audit_router
from app.modules.accessi.routes.auth import router as auth_router
from app.modules.accessi.routes.permissions import router as permissions_router
from app.modules.accessi.routes.section_permissions import (
    admin_permissions_router,
    auth_permissions_router,
    sections_router,
)
from app.modules.accessi.routes.sync import router as sync_router

router = APIRouter()
router.include_router(audit_router)
router.include_router(auth_router)
router.include_router(permissions_router)
router.include_router(sync_router)
router.include_router(admin_users_router)
router.include_router(auth_permissions_router)
router.include_router(sections_router)
router.include_router(admin_permissions_router)
