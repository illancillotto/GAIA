import shlex
from hashlib import sha256

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.effective_permission import EffectivePermission
from app.models.nas_group import NasGroup
from app.models.nas_user import NasUser
from app.models.permission_entry import PermissionEntry
from app.models.share import Share
from app.models.snapshot import Snapshot
from app.schemas.permissions import PermissionCalculationRequest, PermissionEntryInput, PermissionUserInput
from app.schemas.sync import (
    ParsedAclEntry,
    ParsedNasGroup,
    ParsedNasUser,
    ParsedShare,
    SyncApplyResponse,
    SyncPreviewRequest,
    SyncPreviewResponse,
)
from app.services.nas_connector import NasSSHClient, get_nas_client
from app.services.nas_parsers import (
    parse_acl_output,
    parse_group_output,
    parse_passwd_output,
    parse_share_listing,
)
from app.services.permissions import calculate_effective_permissions


def build_sync_preview(payload: SyncPreviewRequest) -> SyncPreviewResponse:
    return SyncPreviewResponse(
        users=parse_passwd_output(payload.passwd_text or ""),
        groups=parse_group_output(payload.group_text or ""),
        shares=parse_share_listing(payload.shares_text or ""),
        acl_entries=[
            entry
            for acl_text in payload.acl_texts
            for entry in parse_acl_output(acl_text)
        ],
    )


def build_live_sync_payload(client: NasSSHClient | None = None) -> SyncPreviewRequest:
    active_client = client or get_nas_client()
    passwd_text = active_client.run_command(settings.nas_passwd_command)
    group_text = active_client.run_command(settings.nas_group_command)
    shares_text = active_client.run_command(settings.nas_shares_command)
    parsed_shares = parse_share_listing(shares_text)
    acl_texts = [
        active_client.run_command(
            settings.nas_acl_command_template.format(share=shlex.quote(share.name))
        )
        for share in parsed_shares
    ]
    return SyncPreviewRequest(
        passwd_text=passwd_text,
        group_text=group_text,
        shares_text=shares_text,
        acl_texts=acl_texts,
    )


def _build_snapshot_checksum(payload: SyncPreviewRequest) -> str:
    raw_payload = "\n---\n".join(
        [
            payload.passwd_text or "",
            payload.group_text or "",
            payload.shares_text or "",
            *payload.acl_texts,
        ]
    )
    return sha256(raw_payload.encode("utf-8")).hexdigest()


def _normalize_subject(raw_subject: str) -> tuple[str, str] | None:
    lowered = raw_subject.strip().lower()
    if lowered.startswith("group:"):
        return "group", raw_subject.split(":", maxsplit=1)[1].strip()
    if lowered.startswith("user:"):
        return "user", raw_subject.split(":", maxsplit=1)[1].strip()
    if not raw_subject.strip():
        return None
    return "user", raw_subject.strip()


def _normalize_permission_level(raw_permissions: str) -> str | None:
    values = {item.strip().lower() for item in raw_permissions.split(",") if item.strip()}
    if "write" in values:
        return "write"
    if "read" in values:
        return "read"
    lowered = raw_permissions.strip().lower()
    if "w" in lowered:
        return "write"
    if "r" in lowered:
        return "read"
    return None


def _upsert_user(db: Session, parsed_user: ParsedNasUser, snapshot_id: int) -> NasUser:
    existing = db.query(NasUser).filter(NasUser.username == parsed_user.username).one_or_none()
    if existing is None:
        existing = NasUser(
            username=parsed_user.username,
            full_name=parsed_user.full_name,
            email=None,
            source_uid=parsed_user.source_uid,
            is_active=True,
            last_seen_snapshot_id=snapshot_id,
        )
        db.add(existing)
        db.flush()
        return existing

    existing.full_name = parsed_user.full_name
    existing.source_uid = parsed_user.source_uid
    existing.is_active = True
    existing.last_seen_snapshot_id = snapshot_id
    return existing


def _upsert_group(db: Session, parsed_group: ParsedNasGroup, snapshot_id: int) -> NasGroup:
    existing = db.query(NasGroup).filter(NasGroup.name == parsed_group.name).one_or_none()
    description = f"GID {parsed_group.gid}"
    if existing is None:
        existing = NasGroup(
            name=parsed_group.name,
            description=description,
            last_seen_snapshot_id=snapshot_id,
        )
        db.add(existing)
        db.flush()
        return existing

    existing.description = description
    existing.last_seen_snapshot_id = snapshot_id
    return existing


def _upsert_share(db: Session, parsed_share: ParsedShare, snapshot_id: int) -> Share:
    existing = db.query(Share).filter(Share.name == parsed_share.name).one_or_none()
    if existing is None:
        existing = Share(
            name=parsed_share.name,
            path=f"/volume1/{parsed_share.name}",
            sector=None,
            description="Importata da sync NAS",
            last_seen_snapshot_id=snapshot_id,
        )
        db.add(existing)
        db.flush()
        return existing

    existing.last_seen_snapshot_id = snapshot_id
    if not existing.description:
        existing.description = "Importata da sync NAS"
    return existing


def _build_permission_entries_by_share(
    preview: SyncPreviewResponse,
    payload: SyncPreviewRequest,
) -> tuple[list[PermissionEntryInput], int]:
    permission_entries: list[PermissionEntryInput] = []
    share_acl_pairs_used = min(len(preview.shares), len(payload.acl_texts))

    for index in range(share_acl_pairs_used):
        share_name = preview.shares[index].name
        parsed_acl_entries = parse_acl_output(payload.acl_texts[index])

        for acl_entry in parsed_acl_entries:
            normalized_subject = _normalize_subject(acl_entry.subject)
            permission_level = _normalize_permission_level(acl_entry.permissions)
            if normalized_subject is None or permission_level is None:
                continue

            subject_type, subject_name = normalized_subject
            permission_entries.append(
                PermissionEntryInput(
                    share_name=share_name,
                    subject_type=subject_type,
                    subject_name=subject_name,
                    permission_level=permission_level,
                    is_deny=acl_entry.effect == "deny",
                )
            )

    return permission_entries, share_acl_pairs_used


def _build_permission_users(users: list[ParsedNasUser], groups: list[ParsedNasGroup]) -> list[PermissionUserInput]:
    memberships: dict[str, list[str]] = {user.username: [] for user in users}

    for group in groups:
        for member in group.members:
            if member in memberships and group.name not in memberships[member]:
                memberships[member].append(group.name)

    return [
        PermissionUserInput(username=user.username, groups=sorted(memberships[user.username]))
        for user in users
    ]


def _serialize_acl_reference(share_name: str, acl_entry: ParsedAclEntry) -> str:
    return (
        f"share={share_name};subject={acl_entry.subject};"
        f"permissions={acl_entry.permissions};effect={acl_entry.effect}"
    )


def apply_sync_payload(db: Session, payload: SyncPreviewRequest) -> SyncApplyResponse:
    preview = build_sync_preview(payload)
    snapshot = Snapshot(
        status="completed",
        checksum=_build_snapshot_checksum(payload),
        notes="Manual sync apply from preview payload",
    )
    db.add(snapshot)
    db.flush()

    users_by_name = {
        parsed_user.username: _upsert_user(db, parsed_user, snapshot.id)
        for parsed_user in preview.users
    }
    for parsed_group in preview.groups:
        _upsert_group(db, parsed_group, snapshot.id)
    shares_by_name = {
        parsed_share.name: _upsert_share(db, parsed_share, snapshot.id)
        for parsed_share in preview.shares
    }

    permission_entries_input, share_acl_pairs_used = _build_permission_entries_by_share(preview, payload)

    for index in range(share_acl_pairs_used):
        share_name = preview.shares[index].name
        share = shares_by_name[share_name]
        for acl_entry in parse_acl_output(payload.acl_texts[index]):
            normalized_subject = _normalize_subject(acl_entry.subject)
            permission_level = _normalize_permission_level(acl_entry.permissions)
            if normalized_subject is None or permission_level is None:
                continue

            subject_type, subject_name = normalized_subject
            db.add(
                PermissionEntry(
                    snapshot_id=snapshot.id,
                    share_id=share.id,
                    subject_type=subject_type,
                    subject_name=subject_name,
                    permission_level=permission_level,
                    is_deny=acl_entry.effect == "deny",
                    source_system="sync_apply",
                    raw_reference=_serialize_acl_reference(share_name, acl_entry),
                )
            )

    permission_users = _build_permission_users(preview.users, preview.groups)
    effective_permissions_preview = calculate_effective_permissions(
        PermissionCalculationRequest(
            users=permission_users,
            permission_entries=permission_entries_input,
        )
    )

    for item in effective_permissions_preview:
        user = users_by_name.get(item.username)
        share = shares_by_name.get(item.share_name)
        if user is None or share is None:
            continue

        db.add(
            EffectivePermission(
                snapshot_id=snapshot.id,
                nas_user_id=user.id,
                share_id=share.id,
                can_read=item.can_read,
                can_write=item.can_write,
                is_denied=item.is_denied,
                source_summary=item.source_summary,
                details_json=None,
            )
        )

    db.commit()

    return SyncApplyResponse(
        snapshot_id=snapshot.id,
        snapshot_checksum=snapshot.checksum or "",
        persisted_users=len(preview.users),
        persisted_groups=len(preview.groups),
        persisted_shares=len(preview.shares),
        persisted_permission_entries=len(permission_entries_input),
        persisted_effective_permissions=len(effective_permissions_preview),
        share_acl_pairs_used=share_acl_pairs_used,
    )


def apply_live_sync(db: Session, client: NasSSHClient | None = None) -> SyncApplyResponse:
    return apply_sync_payload(db, build_live_sync_payload(client))
