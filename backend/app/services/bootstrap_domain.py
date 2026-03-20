from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.effective_permission import EffectivePermission
from app.models.nas_group import NasGroup
from app.models.nas_user import NasUser
from app.models.permission_entry import PermissionEntry
from app.models.review import Review
from app.models.share import Share
from app.models.snapshot import Snapshot


SEED_SNAPSHOT_CHECKSUM = "seed-domain-20260320"

SEED_USERS = [
    {
        "username": "mrossi",
        "full_name": "Mario Rossi",
        "email": "mrossi@example.local",
        "source_uid": "1001",
        "is_active": True,
    },
    {
        "username": "lbianchi",
        "full_name": "Laura Bianchi",
        "email": "lbianchi@example.local",
        "source_uid": "1002",
        "is_active": True,
    },
    {
        "username": "gverdi",
        "full_name": "Giulia Verdi",
        "email": "gverdi@example.local",
        "source_uid": "1003",
        "is_active": True,
    },
]

SEED_GROUPS = [
    {"name": "amministrazione", "description": "Settore amministrativo"},
    {"name": "direzione", "description": "Direzione consortile"},
    {"name": "tecnici", "description": "Area tecnica e territorio"},
]

SEED_SHARES = [
    {
        "name": "contabilita",
        "path": "/volume1/contabilita",
        "sector": "Amministrazione",
        "description": "Documentazione contabilita e fornitori",
    },
    {
        "name": "direzione",
        "path": "/volume1/direzione",
        "sector": "Direzione",
        "description": "Documentazione strategica e verbali",
    },
    {
        "name": "progetti",
        "path": "/volume1/progetti",
        "sector": "Area Tecnica",
        "description": "Pratiche tecniche e documenti di progetto",
    },
]

SEED_PERMISSION_ENTRIES = [
    {
        "share_name": "contabilita",
        "subject_type": "group",
        "subject_name": "amministrazione",
        "permission_level": "write",
        "is_deny": False,
        "raw_reference": "seed:group:amministrazione",
    },
    {
        "share_name": "contabilita",
        "subject_type": "user",
        "subject_name": "gverdi",
        "permission_level": "read",
        "is_deny": True,
        "raw_reference": "seed:user:gverdi",
    },
    {
        "share_name": "direzione",
        "subject_type": "group",
        "subject_name": "direzione",
        "permission_level": "write",
        "is_deny": False,
        "raw_reference": "seed:group:direzione",
    },
    {
        "share_name": "progetti",
        "subject_type": "group",
        "subject_name": "tecnici",
        "permission_level": "write",
        "is_deny": False,
        "raw_reference": "seed:group:tecnici",
    },
    {
        "share_name": "progetti",
        "subject_type": "user",
        "subject_name": "mrossi",
        "permission_level": "read",
        "is_deny": False,
        "raw_reference": "seed:user:mrossi",
    },
]

SEED_EFFECTIVE_PERMISSIONS = [
    {
        "username": "mrossi",
        "share_name": "contabilita",
        "can_read": True,
        "can_write": True,
        "is_denied": False,
        "source_summary": "group:amministrazione:write:allow",
        "details_json": '{"matched_rules":["group:amministrazione:write:allow"]}',
    },
    {
        "username": "lbianchi",
        "share_name": "direzione",
        "can_read": True,
        "can_write": True,
        "is_denied": False,
        "source_summary": "group:direzione:write:allow",
        "details_json": '{"matched_rules":["group:direzione:write:allow"]}',
    },
    {
        "username": "gverdi",
        "share_name": "contabilita",
        "can_read": False,
        "can_write": False,
        "is_denied": True,
        "source_summary": "user:gverdi:read:deny",
        "details_json": '{"matched_rules":["user:gverdi:read:deny"]}',
    },
    {
        "username": "gverdi",
        "share_name": "progetti",
        "can_read": True,
        "can_write": True,
        "is_denied": False,
        "source_summary": "group:tecnici:write:allow",
        "details_json": '{"matched_rules":["group:tecnici:write:allow"]}',
    },
]

SEED_REVIEWS = [
    {
        "username": "mrossi",
        "share_name": "contabilita",
        "decision": "approved",
        "note": "Accesso conforme al ruolo di settore.",
    },
    {
        "username": "gverdi",
        "share_name": "contabilita",
        "decision": "revoked",
        "note": "Accesso negato per riallineamento delle responsabilita.",
    },
]


def _get_or_create_snapshot(db: Session) -> tuple[Snapshot, bool]:
    snapshot = db.scalar(select(Snapshot).where(Snapshot.checksum == SEED_SNAPSHOT_CHECKSUM))
    if snapshot is not None:
        return snapshot, False

    snapshot = Snapshot(
        status="completed",
        checksum=SEED_SNAPSHOT_CHECKSUM,
        notes="Seed iniziale del dominio audit",
    )
    db.add(snapshot)
    db.flush()
    return snapshot, True


def _ensure_users(db: Session, snapshot_id: int) -> dict[str, NasUser]:
    users: dict[str, NasUser] = {}
    for item in SEED_USERS:
        user = db.scalar(select(NasUser).where(NasUser.username == item["username"]))
        if user is None:
            user = NasUser(**item, last_seen_snapshot_id=snapshot_id)
            db.add(user)
            db.flush()
        else:
            user.full_name = item["full_name"]
            user.email = item["email"]
            user.source_uid = item["source_uid"]
            user.is_active = item["is_active"]
            user.last_seen_snapshot_id = snapshot_id
        users[user.username] = user
    return users


def _ensure_groups(db: Session, snapshot_id: int) -> dict[str, NasGroup]:
    groups: dict[str, NasGroup] = {}
    for item in SEED_GROUPS:
        group = db.scalar(select(NasGroup).where(NasGroup.name == item["name"]))
        if group is None:
            group = NasGroup(**item, last_seen_snapshot_id=snapshot_id)
            db.add(group)
            db.flush()
        else:
            group.description = item["description"]
            group.last_seen_snapshot_id = snapshot_id
        groups[group.name] = group
    return groups


def _ensure_shares(db: Session, snapshot_id: int) -> dict[str, Share]:
    shares: dict[str, Share] = {}
    for item in SEED_SHARES:
        share = db.scalar(select(Share).where(Share.name == item["name"]))
        if share is None:
            share = Share(**item, last_seen_snapshot_id=snapshot_id)
            db.add(share)
            db.flush()
        else:
            share.path = item["path"]
            share.sector = item["sector"]
            share.description = item["description"]
            share.last_seen_snapshot_id = snapshot_id
        shares[share.name] = share
    return shares


def _ensure_permission_entries(
    db: Session,
    snapshot_id: int,
    shares: dict[str, Share],
) -> None:
    for item in SEED_PERMISSION_ENTRIES:
        share = shares[item["share_name"]]
        permission_entry = db.scalar(
            select(PermissionEntry).where(
                PermissionEntry.snapshot_id == snapshot_id,
                PermissionEntry.share_id == share.id,
                PermissionEntry.subject_type == item["subject_type"],
                PermissionEntry.subject_name == item["subject_name"],
                PermissionEntry.permission_level == item["permission_level"],
                PermissionEntry.is_deny == item["is_deny"],
            )
        )
        if permission_entry is None:
            db.add(
                PermissionEntry(
                    snapshot_id=snapshot_id,
                    share_id=share.id,
                    subject_type=item["subject_type"],
                    subject_name=item["subject_name"],
                    permission_level=item["permission_level"],
                    is_deny=item["is_deny"],
                    source_system="seed",
                    raw_reference=item["raw_reference"],
                )
            )


def _ensure_effective_permissions(
    db: Session,
    snapshot_id: int,
    users: dict[str, NasUser],
    shares: dict[str, Share],
) -> None:
    for item in SEED_EFFECTIVE_PERMISSIONS:
        user = users[item["username"]]
        share = shares[item["share_name"]]
        effective_permission = db.scalar(
            select(EffectivePermission).where(
                EffectivePermission.snapshot_id == snapshot_id,
                EffectivePermission.nas_user_id == user.id,
                EffectivePermission.share_id == share.id,
            )
        )
        if effective_permission is None:
            effective_permission = EffectivePermission(
                snapshot_id=snapshot_id,
                nas_user_id=user.id,
                share_id=share.id,
                can_read=item["can_read"],
                can_write=item["can_write"],
                is_denied=item["is_denied"],
                source_summary=item["source_summary"],
                details_json=item["details_json"],
            )
            db.add(effective_permission)
        else:
            effective_permission.can_read = item["can_read"]
            effective_permission.can_write = item["can_write"]
            effective_permission.is_denied = item["is_denied"]
            effective_permission.source_summary = item["source_summary"]
            effective_permission.details_json = item["details_json"]


def _ensure_reviews(
    db: Session,
    snapshot_id: int,
    reviewer_user_id: int,
    users: dict[str, NasUser],
    shares: dict[str, Share],
) -> None:
    for item in SEED_REVIEWS:
        user = users[item["username"]]
        share = shares[item["share_name"]]
        review = db.scalar(
            select(Review).where(
                Review.snapshot_id == snapshot_id,
                Review.nas_user_id == user.id,
                Review.share_id == share.id,
            )
        )
        if review is None:
            review = Review(
                snapshot_id=snapshot_id,
                nas_user_id=user.id,
                share_id=share.id,
                reviewer_user_id=reviewer_user_id,
                decision=item["decision"],
                note=item["note"],
            )
            db.add(review)
        else:
            review.reviewer_user_id = reviewer_user_id
            review.decision = item["decision"]
            review.note = item["note"]


def ensure_bootstrap_domain(db: Session, reviewer_user_id: int) -> dict[str, int | bool]:
    snapshot, snapshot_created = _get_or_create_snapshot(db)
    users = _ensure_users(db, snapshot.id)
    _ensure_groups(db, snapshot.id)
    shares = _ensure_shares(db, snapshot.id)
    _ensure_permission_entries(db, snapshot.id, shares)
    _ensure_effective_permissions(db, snapshot.id, users, shares)
    _ensure_reviews(db, snapshot.id, reviewer_user_id, users, shares)
    db.commit()

    return {
        "snapshot_created": snapshot_created,
        "snapshot_id": snapshot.id,
        "nas_users": len(SEED_USERS),
        "nas_groups": len(SEED_GROUPS),
        "shares": len(SEED_SHARES),
        "permission_entries": len(SEED_PERMISSION_ENTRIES),
        "effective_permissions": len(SEED_EFFECTIVE_PERMISSIONS),
        "reviews": len(SEED_REVIEWS),
    }
