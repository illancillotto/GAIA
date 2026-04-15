"""GAIA Operazioni SQLAlchemy models."""

from app.modules.operazioni.models.activities import (
    ActivityApproval,
    ActivityCatalog,
    OperatorActivity,
    OperatorActivityAttachment,
    OperatorActivityEvent,
)
from app.modules.operazioni.models.attachments import (
    Attachment,
    StorageQuotaAlert,
    StorageQuotaMetric,
)
from app.modules.operazioni.models.fuel_cards import FuelCard, FuelCardAssignmentHistory
from app.modules.operazioni.models.gps import GpsTrackSummary
from app.modules.operazioni.models.organizational import (
    OperatorProfile,
    Team,
    TeamMembership,
)
from app.modules.operazioni.models.reports import (
    FieldReport,
    FieldReportAttachment,
    FieldReportCategory,
    FieldReportSeverity,
    InternalCase,
    InternalCaseAssignmentHistory,
    InternalCaseAttachment,
    InternalCaseEvent,
)
from app.modules.operazioni.models.vehicles import (
    Vehicle,
    VehicleAssignment,
    VehicleDocument,
    VehicleFuelLog,
    VehicleMaintenance,
    VehicleMaintenanceType,
    VehicleOdometerReading,
    VehicleUsageSession,
)
from app.modules.operazioni.models.wc_area import WCArea
from app.modules.operazioni.models.wc_operator import WCOperator

__all__ = [
    "ActivityApproval",
    "ActivityCatalog",
    "Attachment",
    "FieldReport",
    "FieldReportAttachment",
    "FieldReportCategory",
    "FieldReportSeverity",
    "FuelCard",
    "FuelCardAssignmentHistory",
    "GpsTrackSummary",
    "InternalCase",
    "InternalCaseAssignmentHistory",
    "InternalCaseAttachment",
    "InternalCaseEvent",
    "OperatorActivity",
    "OperatorActivityAttachment",
    "OperatorActivityEvent",
    "OperatorProfile",
    "StorageQuotaAlert",
    "StorageQuotaMetric",
    "Team",
    "TeamMembership",
    "Vehicle",
    "VehicleAssignment",
    "VehicleDocument",
    "VehicleFuelLog",
    "VehicleMaintenance",
    "VehicleMaintenanceType",
    "VehicleOdometerReading",
    "VehicleUsageSession",
    "WCArea",
    "WCOperator",
]
