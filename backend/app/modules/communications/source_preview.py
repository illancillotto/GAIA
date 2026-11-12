"""Read-only definitive PDF preview before sender/template selection.

The browser retains these exact bytes until draft creation. The draft command
compares the supplied digest before taking its immutable transport snapshot.
This endpoint grants no document-review authorization and creates no message.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db

from . import ruolo_source
from .policy import Conflict, Missing, pdf_pages, sha256
from .schemas import Channel
from .source_repair_routes import router as repair_router
from .template_composition import preview_composition

router = APIRouter(
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))]
)
router.include_router(repair_router)


@router.get("/ruolo/candidates/{identity}/preview")
def preview(identity: UUID, db: Session = Depends(get_db)):
    try:
        item = ruolo_source.source_item(db, identity)
        if item.status != "generated" or item.years_json != [2021]:
            raise Conflict("Anteprima disponibile solo per PDF definitivi 2021")
        content = ruolo_source.read_pdf(item)
        pages = pdf_pages(content)
    except Missing as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except Conflict as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'inline; filename="avviso-{identity}.pdf"',
            "X-Content-SHA256": sha256(content),
            "X-PDF-Pages": str(pages),
            "Access-Control-Expose-Headers": "X-Content-SHA256, X-PDF-Pages",
        },
    )


def verify_preview(content, expected_sha256) -> int:
    """Validate the PDF and the exact document observed before draft creation."""
    if expected_sha256 is not None and sha256(content) != expected_sha256:
        raise Conflict(
            "PDF modificato dopo l'anteprima: riaprire Componi e verificare il documento"
        )
    return pdf_pages(content)


@router.get(
    "/ruolo/candidates/{identity}/template-preview",
    dependencies=[Depends(require_section("ruolo.tributi.manage_status"))],
)
def template_preview(
    identity: UUID,
    template_id: UUID,
    channel: Channel,
    response: Response,
    db: Session = Depends(get_db),
):
    """Render approved text from the canonical source without creating a draft."""
    try:
        result = preview_composition(db, identity, template_id, channel)
    except Missing as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except Conflict as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return result
