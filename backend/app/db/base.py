from app.core.database import Base
from app.models.application_user import ApplicationUser
from app.models.operator_invitation import OperatorInvitation
from app.models.bonifica_oristanese import BonificaOristaneseCredential
from app.models.capacitas import (
    CapacitasAnagraficaHistoryImportJob,
    CapacitasCredential,
    CapacitasParticelleSyncJob,
    CapacitasTerreniSyncJob,
)
from app.models.wc_sync_job import WCSyncJob
from app.modules.catasto.models import (
    CatAdeParticella,
    CatAdeSyncRun,
    CatCapacitasCertificato,
    CatCapacitasIntestatario,
    CatCapacitasTerrenoDetail,
    CatCapacitasTerrenoRow,
    CatConsorzioOccupancy,
    CatConsorzioUnit,
    CatConsorzioUnitSegment,
    CatGisSavedSelection,
    CatGisSavedSelectionItem,
    CatUtenzaIntestatario,
)
from app.modules.accessi.wc_org_charts import WCOrgChart, WCOrgChartEntry
from app.modules.inventory.models import WarehouseRequest
from app.modules.operazioni.models.wc_area import WCArea
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.models.vehicles import WCRefuelEvent
from app.modules.riordino.models import (
    RiordinoAppeal,
    RiordinoChecklistItem,
    RiordinoDocument,
    RiordinoDocumentTypeConfig,
    RiordinoEvent,
    RiordinoGisLink,
    RiordinoIssue,
    RiordinoIssueTypeConfig,
    RiordinoNotification,
    RiordinoParcelLink,
    RiordinoPartyLink,
    RiordinoPhase,
    RiordinoPractice,
    RiordinoStep,
    RiordinoStepTemplate,
    RiordinoTask,
)
from app.modules.utenze.models import (
    AnagraficaAuditLog,
    AnagraficaCompany,
    AnagraficaDocument,
    AnagraficaImportJob,
    AnagraficaImportJobItem,
    AnagraficaPerson,
    AnagraficaPersonSnapshot,
    AnagraficaSubject,
    BonificaUserStaging,
)
from app.modules.utenze.anpr.models import AnprCheckLog, AnprSyncConfig
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
    "AnagraficaPersonSnapshot",
    "AnagraficaSubject",
    "AnprCheckLog",
    "AnprSyncConfig",
    "BonificaUserStaging",
    "Base",
    "BonificaOristaneseCredential",
    "CapacitasCredential",
    "CapacitasAnagraficaHistoryImportJob",
    "CapacitasParticelleSyncJob",
    "CapacitasTerreniSyncJob",
    "CatAdeParticella",
    "CatAdeSyncRun",
    "CatCapacitasCertificato",
    "CatCapacitasIntestatario",
    "CatCapacitasTerrenoDetail",
    "CatCapacitasTerrenoRow",
    "CatastoBatch",
    "CatastoCaptchaLog",
    "CatastoComune",
    "CatastoConnectionTest",
    "CatastoCredential",
    "CatastoDocument",
    "CatastoVisuraRequest",
    "CatConsorzioOccupancy",
    "CatConsorzioUnit",
    "CatConsorzioUnitSegment",
    "CatGisSavedSelection",
    "CatGisSavedSelectionItem",
    "CatUtenzaIntestatario",
    "DeviceInventoryLink",
    "DevicePosition",
    "EffectivePermission",
    "FloorPlan",
    "NasGroup",
    "OperatorInvitation",
    "NasUser",
    "NetworkAlert",
    "NetworkDevice",
    "NetworkScan",
    "NetworkScanDevice",
    "PermissionEntry",
    "Review",
    "RiordinoAppeal",
    "RiordinoChecklistItem",
    "RiordinoDocument",
    "RiordinoDocumentTypeConfig",
    "RiordinoEvent",
    "RiordinoGisLink",
    "RiordinoIssue",
    "RiordinoIssueTypeConfig",
    "RiordinoNotification",
    "RiordinoParcelLink",
    "RiordinoPartyLink",
    "RiordinoPhase",
    "RiordinoPractice",
    "RiordinoStep",
    "RiordinoStepTemplate",
    "RiordinoTask",
    "RoleSectionPermission",
    "Section",
    "UserSectionPermission",
    "WarehouseRequest",
    "WCArea",
    "WCRefuelEvent",
    "WCOrgChart",
    "WCOrgChartEntry",
    "WCOperator",
    "WCSyncJob",
    "Share",
    "Snapshot",
    "SyncRun",
]
