from pathlib import Path
import sys

from sqlalchemy import delete, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.models.catasto import CatastoComune
from app.models.effective_permission import EffectivePermission
from app.models.nas_group import NasGroup
from app.models.nas_user import NasUser
from app.models.permission_entry import PermissionEntry
from app.models.review import Review
from app.models.share import Share
from app.models.snapshot import Snapshot
from app.services.bootstrap_domain import SEED_SNAPSHOT_CHECKSUM
from app.services.catasto_comuni import SEED_COMUNI


def main() -> None:
    db = SessionLocal()
    try:
        snapshot = db.scalar(select(Snapshot).where(Snapshot.checksum == SEED_SNAPSHOT_CHECKSUM))
        if snapshot is None:
            print("purge_seed_data=skipped reason=no_seed_snapshot")
            return

        snapshot_id = snapshot.id

        deleted_reviews = db.execute(delete(Review).where(Review.snapshot_id == snapshot_id)).rowcount or 0
        deleted_effective_permissions = (
            db.execute(delete(EffectivePermission).where(EffectivePermission.snapshot_id == snapshot_id)).rowcount or 0
        )
        deleted_permission_entries = (
            db.execute(delete(PermissionEntry).where(PermissionEntry.snapshot_id == snapshot_id)).rowcount or 0
        )
        deleted_users = (
            db.execute(delete(NasUser).where(NasUser.last_seen_snapshot_id == snapshot_id)).rowcount or 0
        )
        deleted_groups = (
            db.execute(delete(NasGroup).where(NasGroup.last_seen_snapshot_id == snapshot_id)).rowcount or 0
        )
        deleted_shares = (
            db.execute(delete(Share).where(Share.last_seen_snapshot_id == snapshot_id)).rowcount or 0
        )
        deleted_catasto_comuni = 0
        for item in SEED_COMUNI:
            deleted_catasto_comuni += (
                db.execute(
                    delete(CatastoComune).where(
                        CatastoComune.nome == item["nome"],
                        CatastoComune.ufficio == item["ufficio"],
                    )
                ).rowcount
                or 0
            )
        deleted_snapshots = db.execute(delete(Snapshot).where(Snapshot.id == snapshot_id)).rowcount or 0

        db.commit()
    finally:
        db.close()

    print(
        "purge_seed_data=completed "
        f"snapshot_id={snapshot_id} snapshots={deleted_snapshots} users={deleted_users} "
        f"groups={deleted_groups} shares={deleted_shares} permission_entries={deleted_permission_entries} "
        f"effective_permissions={deleted_effective_permissions} reviews={deleted_reviews} "
        f"catasto_comuni={deleted_catasto_comuni}"
    )


if __name__ == "__main__":
    main()
