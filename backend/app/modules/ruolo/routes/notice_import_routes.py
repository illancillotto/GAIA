"""Protected staging and explicit confirmation, separate from outgoing workflows."""

from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.exc import IntegrityError

from app.api.deps import require_module, require_section
from app.modules.ruolo.notice_import_schemas import (
    ConflictDecision,
    ImportBatchView,
    ImportConfirmation,
    ImportRowFilters,
    ImportRowView,
    ImportSnapshot,
)
from app.modules.ruolo.notice_register_api_schemas import Mutation, MutationResult, Page, Pagination
from app.modules.ruolo.routes.notice_register_routes import Database, Editor, _command, _result
from app.modules.ruolo.services import notice_import as service
from app.modules.ruolo.services.notice_import_conflicts import resolve_conflict
from app.modules.ruolo.services.notice_import_excel import MAX_BYTES, parse_excel
from app.modules.ruolo.services.notice_import_poste import snapshot_poste
from app.modules.ruolo.services.notice_register import RegisterConflict, RegisterNotFound

router = APIRouter(
    prefix="/tributi/registro-avvisi/importazioni",
    tags=["ruolo-registro-import"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)


@contextmanager
def transaction(db):
    try:
        yield
        db.commit()
    except RegisterNotFound as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc
    except (RegisterConflict, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(
            409, "Import concorrente o anteprima non valida: ricaricare e riprovare"
        ) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc


def batch_or_404(db, batch_id):
    try:
        return service.require_batch(db, batch_id)
    except RegisterNotFound as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("", response_model=Page[ImportBatchView])
def imports(db: Database, pagination: Annotated[Pagination, Query()]):
    return service.list_imports(db, pagination)


@router.post("/excel", response_model=ImportBatchView, status_code=201)
def preview_excel(db: Database, user: Editor, file: Annotated[UploadFile, File()]):
    with transaction(db):
        content = file.file.read(MAX_BYTES + 1)
        rows, summary = parse_excel(content)
        snapshot = ImportSnapshot(
            "excel_2022_2023", file.filename or "avvisi.xlsx", content, rows, summary
        )
        return ImportBatchView.model_validate(service.stage_import(db, snapshot, user.id))


@router.post("/poste", response_model=ImportBatchView, status_code=201)
def preview_poste(db: Database, user: Editor):
    with transaction(db):
        content, rows, summary = snapshot_poste(db)
        snapshot = ImportSnapshot("poste_db", "poste-snapshot.json", content, rows, summary)
        return ImportBatchView.model_validate(service.stage_import(db, snapshot, user.id))


@router.get("/{batch_id}", response_model=ImportBatchView)
def detail(batch_id: UUID, db: Database):
    return batch_or_404(db, batch_id)


@router.get("/{batch_id}/righe", response_model=Page[ImportRowView])
def rows(batch_id: UUID, db: Database, pagination: Annotated[ImportRowFilters, Query()]):
    batch_or_404(db, batch_id)
    return service.list_imports(db, pagination, batch_id)


@router.post("/{batch_id}/righe/{row_id}/risoluzione", response_model=MutationResult)
def resolve(
    batch_id: UUID, row_id: UUID, payload: Mutation[ConflictDecision], db: Database, user: Editor
):
    with _command(db, user, payload) as change:
        document = resolve_conflict(db, batch_id, row_id, payload.data, change)
        return _result(db, document.id, row_id)


@router.get("/{batch_id}/originale")
def original(batch_id: UUID, db: Database):
    batch = batch_or_404(db, batch_id)
    return Response(
        batch.content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": 'attachment; filename="registro-originale.bin"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/{batch_id}/conferma", response_model=ImportBatchView)
def confirm(batch_id: UUID, payload: ImportConfirmation, db: Database, user: Editor):
    with transaction(db):
        batch = service.confirm_import(db, batch_id, payload.digest, user.id, payload.reason)
        return ImportBatchView.model_validate(batch)
