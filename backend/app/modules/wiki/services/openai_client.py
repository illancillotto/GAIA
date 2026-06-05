"""Client codex-lb per il Wiki Agent."""

from __future__ import annotations

import logging
import urllib.request

from app.core.config import settings

logger = logging.getLogger(__name__)

CHAT_MODEL = settings.wiki_chat_model
TOP_K = settings.wiki_top_k
SYSTEM_PROMPT = (
    "Sei l'assistente documentale di GAIA. Rispondi usando prima il contesto recuperato, "
    "mantieni un tono operativo e sintetico, e segnala quando il contesto non basta."
)

_client = None


def _models_url() -> str:
    return settings.codex_lb_url.rstrip("/").replace("/v1", "/v1/models")


def get_openai_client():
    """Restituisce il client OpenAI-compatibile puntato al servizio wiki configurato."""
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI(
            base_url=settings.codex_lb_url,
            api_key=settings.codex_lb_api_key,
        )
        logger.info("Wiki client inizializzato → %s (model: %s)", settings.codex_lb_url, CHAT_MODEL)
    return _client


def is_wiki_available() -> bool:
    """True se il servizio wiki risponde al probe modelli con la API key configurata."""
    request = urllib.request.Request(
        _models_url(),
        headers={"Authorization": f"Bearer {settings.codex_lb_api_key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=2):
            return True
    except Exception:
        return False
