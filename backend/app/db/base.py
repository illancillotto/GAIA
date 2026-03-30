from app.core.database import Base
from app.models.application_user import ApplicationUser
from app.modules.anagrafica.models import (
    AnagraficaAuditLog,
    AnagraficaCompany,
    AnagraficaDocument,
    AnagraficaImportJob,
    AnagraficaImportJobItem,
    AnagraficaPerson,
    AnagraficaSubject,
)
from app.models.catasto import (
    CatastoBatch,
    CatastoCaptchaLog,
    CatastoComune,
    CatastoConnectionTest,
    CatastoCredential,
    CatastoDocument,
    CatastoVisuraRequest,
)
from app.models.effective_permission import EffectivePermission
from app.models.nas_group import NasGroup
from app.models.nas_user import NasUser
from app.models.permission_entry import PermissionEntry
from app.models.review import Review
from app.models.section_permission import RoleSectionPermission, Section, UserSectionPermission
from app.models.share import Share
from app.models.snapshot import Snapshot
from app.models.sync_run import SyncRun
from app.modules.network.models import (
    DeviceInventoryLink,
    DevicePosition,
    FloorPlan,
    NetworkAlert,
    NetworkDevice,
    NetworkScan,
    NetworkScanDevice,
)

__all__ = [
    "ApplicationUser",
    "AnagraficaAuditLog",
    "AnagraficaCompany",
    "AnagraficaDocument",
    "AnagraficaImportJob",
    "AnagraficaImportJobItem",
    "AnagraficaPerson",
    "AnagraficaSubject",
    "Base",
    "CatastoBatch",
    "CatastoCaptchaLog",
    "CatastoComune",
    "CatastoConnectionTest",
    "CatastoCredential",
    "CatastoDocument",
    "CatastoVisuraRequest",
    "DeviceInventoryLink",
    "DevicePosition",
    "EffectivePermission",
    "FloorPlan",
    "NasGroup",
    "NasUser",
    "NetworkAlert",
    "NetworkDevice",
    "NetworkScan",
    "NetworkScanDevice",
    "PermissionEntry",
    "Review",
    "RoleSectionPermission",
    "Section",
    "UserSectionPermission",
    "Share",
    "Snapshot",
    "SyncRun",
]
