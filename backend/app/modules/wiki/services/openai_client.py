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
    "Sei l'assistente operativo GAIA per operatori del Consorzio. "
    "Rispondi usando il contesto recuperato in tono diretto, sintetico e pratico. "
    "Per overview di modulo o pagina usa: scopo, cosa puo fare l'operatore, dati o input tipici, prossimi passi. "
    "Se mancano dati minimi, chiedili in modo operativo indicando solo cio che serve. "
    "Se il contesto non basta, dillo chiaramente senza inventare e indica quale informazione manca. "
    "Non usare meta-frasi (es. verifico nel workspace, nel documento fornito, non ho abbastanza contesto tecnico). "
    "Non citare workspace, file, prompt, tool, retrieval o dettagli implementativi interni. "
    "Non descrivere il tuo processo di ragionamento."
)

_client = None

_DEGRADED_PROVIDER_MARKERS = (
    "no available accounts",
    "all upstream accounts are unavailable",
    "service is operating in degraded mode",
    "\"code\":\"no_accounts\"",
    "'code': 'no_accounts'",
)
_AVAILABILITY_PROBE_ATTEMPTS = 2
_AVAILABILITY_PROBE_TIMEOUT_SECONDS = 2


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
    for attempt in range(1, _AVAILABILITY_PROBE_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=_AVAILABILITY_PROBE_TIMEOUT_SECONDS):
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
            if attempt < _AVAILABILITY_PROBE_ATTEMPTS:
                logger.info(
                    "Wiki availability probe retry %s/%s after HTTP %s on %s",
                    attempt + 1,
                    _AVAILABILITY_PROBE_ATTEMPTS,
                    exc.code,
                    _models_url(),
                )
                continue
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
            if attempt < _AVAILABILITY_PROBE_ATTEMPTS:
                logger.info(
                    "Wiki availability probe retry %s/%s after transport error on %s",
                    attempt + 1,
                    _AVAILABILITY_PROBE_ATTEMPTS,
                    _models_url(),
                    exc_info=True,
                )
                continue
            if is_agent_fallback_enabled():
                logger.warning("Wiki availability probe falling back to local agent after transport error", exc_info=True)
                return True
            return False
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
