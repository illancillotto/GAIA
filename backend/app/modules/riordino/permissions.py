"""Permissions and role checks for the Riordino module."""

from fastapi import HTTPException, status

from app.modules.riordino.enums import (
    IssueCategory,
)

# Module permission keys
RIORDINO_PRACTICE_CREATE = "riordino.practice.create"
RIORDINO_PRACTICE_READ = "riordino.practice.read"
RIORDINO_PRACTICE_UPDATE = "riordino.practice.update"
RIORDINO_PRACTICE_DELETE = "riordino.practice.delete"
RIORDINO_PRACTICE_ARCHIVE = "riordino.practice.archive"
RIORDINO_STEP_ADVANCE = "riordino.step.advance"
RIORDINO_STEP_SKIP = "riordino.step.skip"
RIORDINO_STEP_REOPEN = "riordino.step.reopen"
RIORDINO_PHASE_TRANSITION = "riordino.phase.transition"
RIORDINO_APPEAL_CREATE = "riordino.appeal.create"
RIORDINO_APPEAL_RESOLVE = "riordino.appeal.resolve"
RIORDINO_ISSUE_CREATE = "riordino.issue.create"
RIORDINO_ISSUE_CLOSE = "riordino.issue.close"
RIORDINO_DOCUMENT_UPLOAD = "riordino.document.upload"
RIORDINO_DOCUMENT_DELETE = "riordino.document.delete"
RIORDINO_CONFIG_MANAGE = "riordino.config.manage"
RIORDINO_NOTIFICATION_READ = "riordino.notification.read"


def require_permission(user_permissions: list[str], required_permission: str) -> None:
    """Check if user has the required permission.

    Raises 403 Forbidden if permission is missing.
    """
    if required_permission not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{required_permission}' required.",
        )
