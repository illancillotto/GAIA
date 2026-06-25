import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiIndexResult
from app.modules.wiki.services.indexer import index_documents
from app.modules.wiki.services.openai_client import is_wiki_available

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Wiki"])


def _run_indexing(force: bool) -> None:
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        result = index_documents(db, force=force)
        logger.info(
            "Indicizzazione completata: %d file, %d chunk",
            len(result["indexed_files"]),
            result["total_chunks"],
        )
    except Exception as exc:
        logger.error("Errore indicizzazione: %s", exc, exc_info=True)
    finally:
        db.close()


@router.post("/index", response_model=WikiIndexResult)
def trigger_index(
    force: bool = False,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiIndexResult:
    """
    Avvia la re-indicizzazione dei documenti in background.
    Solo admin e super_admin. Richiede Wiki Agent raggiungibile.
    """
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso negato.")

    if not is_wiki_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wiki Agent non disponibile: codex-lb non raggiungibile su CODEX_LB_URL.",
        )

    background_tasks.add_task(_run_indexing, force)
    return WikiIndexResult(
        indexed_files=[],
        total_chunks=0,
        message="Indicizzazione avviata in background. Controlla i log del backend.",
    )
