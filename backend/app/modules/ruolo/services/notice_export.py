"""Versioned archives with a fresh commit fence immediately before delivery."""

import hashlib
import json
from dataclasses import dataclass
from io import BytesIO
from uuid import UUID
from zipfile import ZIP_STORED, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloTributiNoticeNumber
from app.modules.ruolo.notice_confirmation_models import (
    NoticeExportClaim,
    NoticeExportIdentity,
    NoticeGenerationConfirmation,
    NoticeGenerationExport,
)
from app.modules.ruolo.services import notice_draft_review as review
from app.modules.ruolo.services.notice_revision import lock_revision, read_revision


@dataclass(frozen=True)
class ExportSnapshot:
    confirmation_id: UUID
    manifest: dict
    files: tuple[tuple[str, bytes], ...]


def _identities(db, records, confirmation):
    identities, numbers = [], []
    for record in records:
        identity = review._confirmed_identity(record.payload_json)
        number = record.payload_json.get("notice_number")
        reservation = db.get(
            RuoloTributiNoticeNumber, record.notice_number_id, with_for_update=True
        )
        if (
            reservation is None
            or reservation.status != "confirmed"
            or reservation.identity_key != identity
            or reservation.notice_number != number
            or not number
        ):
            raise review.DraftReviewBlocked("Numerazione confermata non valida")
        identities.append(identity)
        numbers.append(number)
    if identities != confirmation.identity_keys or numbers != confirmation.notice_numbers:
        raise review.DraftReviewBlocked("Identita diverse dalla conferma")


def _snapshot(db, batch_id) -> ExportSnapshot:
    current = read_revision(db.connection())
    lock_revision(db.connection(), current)
    confirmation = db.scalar(
        select(NoticeGenerationConfirmation)
        .where(
            NoticeGenerationConfirmation.generation_id == batch_id,
            NoticeGenerationConfirmation.generation_kind == "batch",
        )
        .with_for_update()
    )
    if confirmation is None:
        raise review.DraftReviewBlocked("Confermare il lotto prima di esportare")
    records = review._records(db, batch_id, True, expected_status="confirmed")
    drafts = review._drafts(db, batch_id, records, True)
    review._check_review_size(db, drafts)
    basis = review._basis(drafts)
    lock_revision(db.connection(), basis)
    digest = review._integrity(records, drafts, expected_status="confirmed")
    if digest != confirmation.review_digest or drafts[0].input_basis != confirmation.input_basis:
        raise review.DraftReviewBlocked("Artefatti diversi dalla conferma: export bloccato")
    _identities(db, records, confirmation)
    files = tuple(
        (f"avvisi/{draft.id}.{draft.artifact_format}", draft.artifact) for draft in drafts
    )
    manifest = {
        "schema_version": 1,
        "batch_id": str(batch_id),
        "confirmation_id": str(confirmation.id),
        "confirmed_by": confirmation.confirmed_by,
        "confirmed_at": confirmation.confirmed_at.isoformat(),
        "review_digest": digest,
        "input_basis": confirmation.input_basis,
        "authorizes_dispatch": False,
        "documents": [
            {
                "path": name,
                "draft_id": str(draft.id),
                "source_id": str(draft.source_id),
                "sha256": draft.artifact_sha256,
                "format": draft.artifact_format,
                "payload": draft.manifest,
            }
            for (name, _), draft in zip(files, drafts, strict=True)
        ],
    }
    return ExportSnapshot(confirmation.id, manifest, files)


def build_archive(snapshot: ExportSnapshot) -> bytes:
    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_STORED) as archive:
        archive.writestr("manifest.json", json.dumps(snapshot.manifest, sort_keys=True, indent=2))
        for name, content in snapshot.files:
            archive.writestr(name, content)
    return stream.getvalue()


def _claim(db, snapshot, archive, actor_id):
    export = db.scalar(
        select(NoticeGenerationExport)
        .where(NoticeGenerationExport.confirmation_id == snapshot.confirmation_id)
        .with_for_update()
    )
    if export is None:
        export = NoticeGenerationExport(
            confirmation_id=snapshot.confirmation_id,
            manifest=snapshot.manifest,
            artifact=archive,
            artifact_sha256=hashlib.sha256(archive).hexdigest(),
            created_by=actor_id,
        )
        db.add(export)
        db.flush()
        _reserve_identities(db, export)
    if (
        export.manifest != snapshot.manifest
        or hashlib.sha256(export.artifact).hexdigest() != export.artifact_sha256
    ):
        raise review.DraftReviewBlocked("Archivio definitivo alterato: export bloccato")
    db.add(NoticeExportClaim(export_id=export.id, actor_id=actor_id))
    return export.artifact


def _reserve_identities(db, export):
    identities = [
        document["payload"]["notice_identity_key"] for document in export.manifest["documents"]
    ]
    existing = db.scalar(
        select(NoticeExportIdentity)
        .where(NoticeExportIdentity.identity_key.in_(identities))
        .limit(1)
    )
    if existing is not None:
        raise review.DraftReviewBlocked(
            "Avviso gia esportato in un altro lotto: necessaria una rettifica esplicita"
        )
    db.add_all(
        NoticeExportIdentity(identity_key=identity, export_id=export.id) for identity in identities
    )


def export_batch(engine, batch_id: UUID, actor_id: int) -> bytes:
    # Packaging happens outside database locks. A second check closes the race.
    with Session(engine) as db, db.begin():
        snapshot = _snapshot(db, batch_id)
    archive = build_archive(snapshot)
    with Session(engine) as db, db.begin():
        current = _snapshot(db, batch_id)
        if current != snapshot:
            raise review.DraftReviewBlocked("Lotto modificato durante l'export")
        result = _claim(db, current, archive, actor_id)
    # Commit must succeed before any bytes can reach the HTTP response.
    return result
