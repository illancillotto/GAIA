"""Client codex-lb per il Wiki Agent."""

from __future__ import annotations

import logging
import urllib.error
import urllib.request

from app.core.config import settings
from app.modules.wiki.services.agent_fallback import is_agent_fallback_enabled

logger = logging.getLogger(__name__)

CHAT_MODEL = settings.wiki_chat_model
TOP_K = settings.wiki_top_k
SYSTEM_PROMPT = (
    "Sei l'assistente documentale di GAIA. Rispondi usando prima il contesto recuperato, "
    "mantieni un tono operativo e sintetico, e segnala quando il contesto non basta."
)

_client = None

_DEGRADED_PROVIDER_MARKERS = (
    "no available accounts",
    "all upstream accounts are unavailable",
    "service is operating in degraded mode",
    "\"code\":\"no_accounts\"",
    "'code': 'no_accounts'",
)


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
    except urllib.error.HTTPError as exc:
        # Una risposta HTTP dal codex-lb indica che il servizio e' raggiungibile
        # anche se la chiave non autorizza il listing dei modelli.
        if 400 <= exc.code < 500:
            logger.warning(
                "Wiki availability probe reached codex-lb but got HTTP %s on %s",
                exc.code,
                _models_url(),
            )
            return True
        logger.warning(
            "Wiki availability probe failed with HTTP %s on %s",
            exc.code,
            _models_url(),
        )
        if is_agent_fallback_enabled():
            logger.warning("Wiki availability probe falling back to local agent after HTTP %s", exc.code)
            return True
        return False
    except Exception:
        if is_agent_fallback_enabled():
            logger.warning("Wiki availability probe falling back to local agent after transport error", exc_info=True)
            return True
        return False


def is_wiki_provider_degraded_error(exc: Exception) -> bool:
    """True se codex-lb e' raggiungibile ma senza upstream account utilizzabili."""
    status_code = getattr(exc, "status_code", None)
    if status_code != 503:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
    message = str(exc).lower()
    has_degraded_marker = any(marker in message for marker in _DEGRADED_PROVIDER_MARKERS)
    if not has_degraded_marker:
        return False
    return status_code == 503 or "503" in message or "no_accounts" in message
