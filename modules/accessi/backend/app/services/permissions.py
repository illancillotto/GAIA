from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories.permissions import list_effective_permissions
from app.schemas.permissions import (
    EffectivePermissionPreviewResponse,
    PermissionCalculationRequest,
)


@dataclass
class _PermissionAccumulator:
    share_name: str
    username: str
    can_read: bool = False
    can_write: bool = False
    is_denied: bool = False
    matched_rules: list[str] | None = None

    def __post_init__(self) -> None:
        if self.matched_rules is None:
            self.matched_rules = []


def _entry_applies_to_user(subject_type: str, subject_name: str, username: str, groups: list[str]) -> bool:
    if subject_type == "user":
        return subject_name == username
    if subject_type == "group":
        return subject_name in groups
    return False


def _apply_permission_level(acc: _PermissionAccumulator, permission_level: str, is_deny: bool, source: str) -> None:
    level = permission_level.lower()
    acc.matched_rules.append(source)

    if is_deny:
        acc.is_denied = True
        acc.can_read = False
        acc.can_write = False
        return

    if acc.is_denied:
        return

    if level == "write":
        acc.can_write = True
        acc.can_read = True
    elif level == "read":
        acc.can_read = True


def calculate_effective_permissions(
    payload: PermissionCalculationRequest,
) -> list[EffectivePermissionPreviewResponse]:
    share_names = sorted({entry.share_name for entry in payload.permission_entries})
    results: list[EffectivePermissionPreviewResponse] = []

    for user in payload.users:
        for share_name in share_names:
            accumulator = _PermissionAccumulator(share_name=share_name, username=user.username)
            matching_entries = [
                entry
                for entry in payload.permission_entries
                if entry.share_name == share_name
                and _entry_applies_to_user(
                    entry.subject_type,
                    entry.subject_name,
                    user.username,
                    user.groups,
                )
            ]

            deny_entries = [entry for entry in matching_entries if entry.is_deny]
            allow_entries = [entry for entry in matching_entries if not entry.is_deny]

            for entry in deny_entries + allow_entries:
                source = (
                    f"{entry.subject_type}:{entry.subject_name}:{entry.permission_level}:"
                    f"{'deny' if entry.is_deny else 'allow'}"
                )
                _apply_permission_level(accumulator, entry.permission_level, entry.is_deny, source)

            results.append(
                EffectivePermissionPreviewResponse(
                    username=user.username,
                    share_name=share_name,
                    can_read=accumulator.can_read,
                    can_write=accumulator.can_write,
                    is_denied=accumulator.is_denied,
                    source_summary=", ".join(accumulator.matched_rules) if accumulator.matched_rules else "no-match",
                )
            )

    return results


def get_effective_permissions(db: Session):
    return list_effective_permissions(db)
