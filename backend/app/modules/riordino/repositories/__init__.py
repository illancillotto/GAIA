"""Repository exports for Riordino."""

from app.modules.riordino.repositories.appeal_repository import AppealRepository
from app.modules.riordino.repositories.document_repository import DocumentRepository
from app.modules.riordino.repositories.issue_repository import IssueRepository
from app.modules.riordino.repositories.practice_repository import PracticeRepository
from app.modules.riordino.repositories.workflow_repository import WorkflowRepository

__all__ = [
    "AppealRepository",
    "DocumentRepository",
    "IssueRepository",
    "PracticeRepository",
    "WorkflowRepository",
]
