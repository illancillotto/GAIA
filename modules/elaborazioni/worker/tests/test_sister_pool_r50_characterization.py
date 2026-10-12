from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.application_user import ApplicationUser
from app.models.catasto import (
    CatastoBatch,
    CatastoBatchKind,
    CatastoBatchStatus,
    CatastoCredential,
    CatastoRuoloAutoSyncConfig,
)
from sister_credential_pool import (
    ActiveSisterCredentialPool,
    load_active_credential_pool,
    load_configured_credential_ids,
    refresh_shared_credential_pool,
    run_dynamic_credential_pool,
)


def _credential(user_id: int, username: str, *, active: bool = True) -> CatastoCredential:
    return CatastoCredential(
        id=uuid4(),
        user_id=user_id,
        label=username,
        sister_username=username,
        sister_password_encrypted=b"synthetic-test-only",
        active=active,
        schedule_enabled=username == "scheduled",
        availability_schedule={"timezone": "UTC", "weekly": {}},
    )


@pytest.fixture
def pool_db() -> Iterator[tuple[sessionmaker[Session], CatastoBatch, dict[str, CatastoCredential]]]:
    engine = create_engine("sqlite://")
    for model in (ApplicationUser, CatastoCredential, CatastoBatch, CatastoRuoloAutoSyncConfig):
        model.__table__.create(bind=engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with factory() as db:
            owner = ApplicationUser(
                username="r50-owner", email="r50-owner@example.local", password_hash="synthetic"
            )
            other = ApplicationUser(
                username="r50-other", email="r50-other@example.local", password_hash="synthetic"
            )
            db.add_all([owner, other])
            db.flush()
            credentials = {
                username: _credential(owner.id, username, active=username != "inactive")
                for username in ("scheduled", "disabled", "unconfigured", "inactive", "unlisted")
            }
            credentials["foreign"] = _credential(other.id, "foreign")
            db.add_all(credentials.values())
            db.flush()
            batch = CatastoBatch(
                user_id=owner.id,
                name="r50-private-pool",
                total_items=1,
                status=CatastoBatchStatus.PROCESSING.value,
                batch_kind=CatastoBatchKind.MANUAL_BATCH.value,
                credential_ids=[
                    str(selected.id)
                    for username, selected in credentials.items()
                    if username != "unlisted"
                ],
            )
            db.add(batch)
            db.commit()
        yield factory, batch, credentials
    finally:
        engine.dispose()


def test_configured_manual_credentials_ignore_profiles_and_current_time_window(pool_db) -> None:
    factory, batch, credentials = pool_db
    with factory() as db:
        db.add(
            CatastoRuoloAutoSyncConfig(
                user_id=batch.user_id,
                credential_profiles={
                    str(selected.id): {"enabled": False} for selected in credentials.values()
                },
            )
        )
        db.commit()
        configured = load_configured_credential_ids(db, batch)
        available = load_active_credential_pool(db, batch, datetime(2026, 10, 11, tzinfo=UTC))

    assert configured == {
        credentials[username].id for username in ("scheduled", "disabled", "unconfigured")
    }
    assert available.available_ids == {
        credentials[username].id for username in ("disabled", "unconfigured")
    }
    assert credentials["scheduled"].id in configured - available.available_ids


def test_configured_perpetual_credentials_require_enabled_profile_but_not_open_schedule(
    pool_db,
) -> None:
    factory, batch, credentials = pool_db
    batch.batch_kind = CatastoBatchKind.PERPETUAL_SYNC.value
    with factory() as db:
        db.merge(batch)
        db.add(
            CatastoRuoloAutoSyncConfig(
                user_id=batch.user_id,
                credential_profiles={
                    str(credentials["scheduled"].id): {
                        "enabled": True,
                        "schedule_enabled": True,
                        "availability_schedule": {"timezone": "UTC", "weekly": {}},
                    },
                    str(credentials["disabled"].id): {"enabled": False},
                    str(credentials["inactive"].id): {"enabled": True},
                    str(credentials["unlisted"].id): {"enabled": True},
                    str(credentials["foreign"].id): {"enabled": True},
                },
            )
        )
        db.commit()
        configured = load_configured_credential_ids(db, batch)
        available = load_active_credential_pool(db, batch, datetime(2026, 10, 11, tzinfo=UTC))

    assert configured == {credentials["scheduled"].id}
    assert available.credentials == ()
    assert available.active_credential_count == 3
    assert available.next_availability is None


def test_pool_merge_preserves_original_identity_and_quarantine_without_new_members() -> None:
    original = _credential(1, "original")
    rejected = _credential(1, "rejected")
    replacement = _credential(1, "same-id-new-instance")
    replacement.id = original.id
    pool = ActiveSisterCredentialPool((original,), 1)
    assert pool.reject(rejected.id) == 1
    existing_members = pool.credentials
    opening = datetime(2026, 10, 12, tzinfo=UTC)

    assert pool.merge(ActiveSisterCredentialPool((replacement, rejected), 2, opening)) == ()
    assert pool.credentials is existing_members
    assert pool.credentials[0] is original
    assert pool.available_ids == {original.id}
    assert pool.rejected_ids == {rejected.id}
    assert pool.active_credential_count == 2
    assert pool.next_availability == opening

    new_member = _credential(1, "new")
    assert pool.merge(ActiveSisterCredentialPool((replacement, rejected, new_member), 3)) == (
        new_member,
    )
    assert pool.credentials == (original, new_member)
    assert pool.available_ids == {original.id, new_member.id}
    assert pool.rejected_ids == {rejected.id}
    assert pool.active_credential_count == 3
    assert pool.next_availability is None


def test_dynamic_pool_refresh_completes_real_runners_after_synchronous_announcement(
    pool_db,
) -> None:
    factory, batch, credentials = pool_db
    first = credentials["disabled"]
    batch.credential_ids = [str(first.id)]
    with factory() as db:
        db.merge(batch)
        db.commit()
    pool = ActiveSisterCredentialPool((first,), 1)
    late = _credential(batch.user_id, "late")
    observed: list[tuple[str, UUID | None]] = []
    snapshots: list[set[UUID]] = []

    async def scenario() -> None:
        release = asyncio.Event()

        async def run_credential(selected: CatastoCredential) -> None:
            observed.append(("started", selected.id))
            await release.wait()
            observed.append(("finished", selected.id))

        def refresh(started_ids: set[UUID]) -> tuple[CatastoCredential, ...]:
            snapshots.append(set(started_ids))
            observed.append(("refresh", None))
            with factory() as db:
                db.add(late)
                current_batch = db.get(CatastoBatch, batch.id)
                assert current_batch is not None
                current_batch.credential_ids = [str(first.id), str(late.id)]
                db.commit()
            return refresh_shared_credential_pool(factory, batch.id, pool, started_ids)

        def announce() -> None:
            observed.append(("announced", None))
            release.set()

        await asyncio.wait_for(
            run_dynamic_credential_pool(
                (first,), run_credential, refresh, lambda: True, announce, 1
            ),
            timeout=5,
        )

    asyncio.run(scenario())
    assert snapshots == [{first.id}]
    assert observed[:3] == [("started", first.id), ("refresh", None), ("announced", None)]
    assert {identity for event, identity in observed if event == "started"} == {first.id, late.id}
    assert {identity for event, identity in observed if event == "finished"} == {first.id, late.id}
    assert pool.available_ids == {first.id, late.id}
    assert pool.active_credential_count == 2
