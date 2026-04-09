"""Schema exports for the Riordino module."""

from app.modules.riordino.schemas.appeal import (
    AppealCreate,
    AppealResolveRequest,
    AppealResponse,
    AppealUpdate,
)
from app.modules.riordino.schemas.config import (
    DocumentTypeConfigCreate,
    DocumentTypeConfigResponse,
    DocumentTypeConfigUpdate,
    IssueTypeConfigCreate,
    IssueTypeConfigResponse,
    IssueTypeConfigUpdate,
    StepTemplateResponse,
    StepTemplateUpdate,
)
from app.modules.riordino.schemas.dashboard import DashboardResponse
from app.modules.riordino.schemas.document import DocumentListResponse, DocumentResponse
from app.modules.riordino.schemas.event import EventResponse
from app.modules.riordino.schemas.gis import GisLinkCreate, GisLinkResponse, GisLinkUpdate
from app.modules.riordino.schemas.issue import IssueCloseRequest, IssueCreate, IssueResponse
from app.modules.riordino.schemas.notification import NotificationResponse
from app.modules.riordino.schemas.links import (
    ParcelLinkCreate,
    ParcelLinkResponse,
    PartyLinkCreate,
    PartyLinkResponse,
)
from app.modules.riordino.schemas.practice import (
    ChecklistItemResponse,
    PhaseResponse,
    PracticeCreate,
    PracticeDetailResponse,
    PracticeListResponse,
    PracticeResponse,
    PracticeUpdate,
    StepResponse,
)
from app.modules.riordino.schemas.workflow import (
    PhaseCompleteRequest,
    StepAdvanceRequest,
    StepSkipRequest,
)

__all__ = [
    "AppealCreate",
    "AppealResolveRequest",
    "AppealResponse",
    "AppealUpdate",
    "ChecklistItemResponse",
    "DashboardResponse",
    "DocumentTypeConfigCreate",
    "DocumentTypeConfigResponse",
    "DocumentTypeConfigUpdate",
    "DocumentListResponse",
    "DocumentResponse",
    "EventResponse",
    "GisLinkCreate",
    "GisLinkResponse",
    "GisLinkUpdate",
    "IssueCloseRequest",
    "IssueCreate",
    "IssueResponse",
    "IssueTypeConfigCreate",
    "IssueTypeConfigResponse",
    "IssueTypeConfigUpdate",
    "NotificationResponse",
    "ParcelLinkCreate",
    "ParcelLinkResponse",
    "PhaseCompleteRequest",
    "PhaseResponse",
    "PartyLinkCreate",
    "PartyLinkResponse",
    "PracticeCreate",
    "PracticeDetailResponse",
    "PracticeListResponse",
    "PracticeResponse",
    "PracticeUpdate",
    "StepAdvanceRequest",
    "StepResponse",
    "StepSkipRequest",
    "StepTemplateResponse",
    "StepTemplateUpdate",
]
