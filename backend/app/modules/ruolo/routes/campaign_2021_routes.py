"""Analyze first, retain a snapshot explicitly, approve accounting, then request private previews."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile

from app.api.deps import require_module, require_section
from app.modules.ruolo.campaign_2021_schemas import CampaignApproval
from app.modules.ruolo.routes.notice_import_routes import transaction
from app.modules.ruolo.routes.notice_register_routes import Database, Editor
from app.modules.ruolo.services import campaign_2021 as service
from app.modules.ruolo.services.notice_import_excel import MAX_BYTES

router = APIRouter(
    prefix="/tributi/campagna-2021",
    tags=["ruolo-campagna-2021"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)


@router.get("")
def campaigns(db: Database):
    return service.list_campaigns(db)


@router.post("/analisi")
def analyze(db: Database, file: Annotated[UploadFile, File()]):
    with transaction(db):
        return service.analyze(db, file.file.read(MAX_BYTES + 1))


@router.post("/importazioni", status_code=201)
def stage(
    db: Database,
    user: Editor,
    file: Annotated[UploadFile, File()],
    report_sha256: Annotated[str, Form()],
):
    with transaction(db):
        return service.stage(
            db,
            file.file.read(MAX_BYTES + 1),
            file.filename or "avvisi-2021.xlsx",
            report_sha256,
            user.id,
        )


@router.get("/{campaign_id}")
def detail(campaign_id: UUID, db: Database):
    with transaction(db):
        return service.view(service.require(db, campaign_id, service.IMPORT))


@router.post("/{campaign_id}/approvazioni", status_code=201)
def approve(campaign_id: UUID, payload: CampaignApproval, db: Database, user: Editor):
    with transaction(db):
        return service.approve(db, campaign_id, payload, user.id)


@router.post("/approvazioni/{approval_id}/anteprima")
def preview(approval_id: UUID, db: Database, user: Editor):
    with transaction(db):
        content = service.preview(db, approval_id, user.id)
        return Response(
            content,
            media_type="application/pdf",
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": 'inline; filename="anteprima-campagna-2021.pdf"',
            },
        )
