import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.modules.wiki.schemas import WikiChatRequest, WikiChatResponse
from app.modules.wiki.services.openai_client import is_wiki_available
from app.modules.wiki.services.rag import answer_question

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Wiki"])


@router.post("/chat", response_model=WikiChatResponse)
def wiki_chat(
    payload: WikiChatRequest,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> WikiChatResponse:
    """
    Risponde a una domanda usando il pipeline RAG sui documenti GAIA.
    Usa codex-lb come LLM backend (proxy OpenAI-compatibile locale su porta 2455).
    Retrieval: PostgreSQL full-text search (nessuna chiamata API per gli embedding).

    TODO(Codex): aggiungere streaming SSE con StreamingResponse e stream=True
    su client.chat.completions.create. Vedere services/rag.py per il TODO inline.
    """
    if not is_wiki_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wiki Agent non disponibile: codex-lb non raggiungibile su CODEX_LB_URL.",
        )

    try:
        return answer_question(db, payload.question, payload.context_article)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Errore wiki chat: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno durante l'elaborazione della risposta.",
        ) from exc
