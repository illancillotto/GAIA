import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatRequest, WikiChatResponse, WikiChatStreamChunk
from app.modules.wiki.services.orchestrator import answer_with_orchestration

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Wiki"])


def _chunk_answer(answer: str, *, chunk_words: int = 40) -> list[str]:
    words = answer.split()
    if not words:
        return [""]
    return [" ".join(words[index:index + chunk_words]) for index in range(0, len(words), chunk_words)]


def _serialize_sse(chunk: WikiChatStreamChunk) -> str:
    return f"event: {chunk.event}\ndata: {chunk.model_dump_json()}\n\n"


@router.post("/chat", response_model=WikiChatResponse)
def wiki_chat(
    payload: WikiChatRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiChatResponse:
    """
    Risponde a una domanda usando il pipeline RAG sui documenti GAIA.
    Usa codex-lb come LLM backend (proxy OpenAI-compatibile locale su porta 2455).
    Retrieval: PostgreSQL full-text search (nessuna chiamata API per gli embedding).
    """
    try:
        return answer_with_orchestration(
            db,
            current_user,
            payload.question,
            payload.context_article,
            payload.conversation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Errore wiki chat: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno durante l'elaborazione della risposta.",
        ) from exc


@router.post("/chat/stream")
def wiki_chat_stream(
    payload: WikiChatRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> StreamingResponse:
    def event_generator():
        try:
            response = answer_with_orchestration(
                db,
                current_user,
                payload.question,
                payload.context_article,
                payload.conversation_id,
            )
            meta = WikiChatStreamChunk(
                event="meta",
                data={
                    "mode": response.mode,
                    "found": response.found,
                    "conversation_id": response.conversation_id,
                    "tool_calls": [item.model_dump(mode="json") for item in response.tool_calls],
                    "sources": [item.model_dump(mode="json") for item in response.sources],
                    "evidences": [item.model_dump(mode="json") for item in response.evidences],
                },
            )
            yield _serialize_sse(meta)
            for piece in _chunk_answer(response.answer):
                yield _serialize_sse(WikiChatStreamChunk(event="delta", data={"text": piece}))
            yield _serialize_sse(
                WikiChatStreamChunk(
                    event="done",
                    data={"answer": response.answer, "conversation_id": response.conversation_id},
                )
            )
        except ValueError as exc:
            yield _serialize_sse(
                WikiChatStreamChunk(
                    event="error",
                    data={"status_code": status.HTTP_404_NOT_FOUND, "detail": str(exc)},
                )
            )
        except RuntimeError as exc:
            yield _serialize_sse(
                WikiChatStreamChunk(
                    event="error",
                    data={"status_code": status.HTTP_503_SERVICE_UNAVAILABLE, "detail": str(exc)},
                )
            )
        except Exception as exc:
            logger.error("Errore wiki chat stream: %s", exc, exc_info=True)
            yield _serialize_sse(
                WikiChatStreamChunk(
                    event="error",
                    data={"status_code": status.HTTP_500_INTERNAL_SERVER_ERROR, "detail": "Errore interno durante l'elaborazione della risposta."},
                )
            )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
