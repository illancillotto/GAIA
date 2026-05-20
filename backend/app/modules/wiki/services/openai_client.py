"""Client codex-lb — proxy OpenAI-compatibile locale su porta 2455."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# URL del proxy codex-lb.
# Da Docker: host.docker.internal:2455  |  Da host: 127.0.0.1:2455
CODEX_LB_URL = os.environ.get("CODEX_LB_URL", "http://host.docker.internal:2455/v1")

# Chiave API: codex-lb disabilita l'auth per richieste locali,
# quindi qualsiasi stringa non vuota va bene.
CODEX_LB_API_KEY = os.environ.get("CODEX_LB_API_KEY", "sk-codex-lb-local")

CHAT_MODEL = os.environ.get("WIKI_CHAT_MODEL", "gpt-5.4-mini")
TOP_K = int(os.environ.get("WIKI_TOP_K", "5"))

SYSTEM_PROMPT = """Sei l'assistente tecnico di GAIA, la piattaforma IT governance del Consorzio di Bonifica dell'Oristanese.

Il tuo compito è rispondere alle domande degli utenti basandoti esclusivamente sui documenti forniti come contesto.
Rispondi in italiano, in modo chiaro e conciso. Se la risposta non è nei documenti forniti, dillo esplicitamente.

Quando citi informazioni, indica il documento di origine (es. "Secondo ARCHITECTURE.md...").
Non inventare funzionalità non documentate.
Se ti viene chiesta una funzionalità non ancora implementata, indicalo chiaramente e suggerisci all'utente di registrare una richiesta."""

_client = None


def get_openai_client():
    """Restituisce il client puntato a codex-lb, inizializzandolo al primo accesso."""
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(base_url=CODEX_LB_URL, api_key=CODEX_LB_API_KEY)
        logger.info("Wiki client inizializzato → %s (model: %s)", CODEX_LB_URL, CHAT_MODEL)
    return _client


def is_wiki_available() -> bool:
    """
    True se codex-lb è raggiungibile.
    Non richiede OPENAI_API_KEY — usa il proxy locale.
    """
    import urllib.request
    try:
        urllib.request.urlopen(CODEX_LB_URL.replace("/v1", "/v1/models"), timeout=2)
        return True
    except Exception:
        return False
