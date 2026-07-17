"""All SQLAlchemy models for the Riordino module."""

from app.modules.riordino.models.appeal import RiordinoAppeal
from app.modules.riordino.models.block import RiordinoBlock
from app.modules.riordino.models.block_assignment import RiordinoBlockAssignment
from app.modules.riordino.models.block_parcel_snapshot import RiordinoBlockParcelSnapshot
from app.modules.riordino.models.checklist import RiordinoChecklistItem
from app.modules.riordino.models.document import RiordinoDocument
from app.modules.riordino.models.document_type_config import RiordinoDocumentTypeConfig
from app.modules.riordino.models.event import RiordinoEvent
from app.modules.riordino.models.gis_link import RiordinoGisLink
from app.modules.riordino.models.issue import RiordinoIssue
from app.modules.riordino.models.issue_type_config import RiordinoIssueTypeConfig
from app.modules.riordino.models.notification import RiordinoNotification
from app.modules.riordino.models.parcel_link import RiordinoParcelLink
from app.modules.riordino.models.party_link import RiordinoPartyLink
from app.modules.riordino.models.phase import RiordinoPhase
from app.modules.riordino.models.practice import RiordinoPractice
from app.modules.riordino.models.step import RiordinoStep
from app.modules.riordino.models.step_template import RiordinoStepTemplate
from app.modules.riordino.models.task import RiordinoTask

__all__ = [
    "RiordinoAppeal",
    "RiordinoBlock",
    "RiordinoBlockAssignment",
    "RiordinoBlockParcelSnapshot",
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
]
