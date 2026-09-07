"""Esito strutturato di un singolo tentativo di risoluzione CAPTCHA.

Ogni risposta possibile di un provider (Agent CLI, codex-lb, Anti-Captcha) ha un
``reason`` distinto, così il messaggio d'errore finale della visura dice
esattamente perché il CAPTCHA non è stato risolto invece di un generico
"exhausted".
"""

from __future__ import annotations

from dataclasses import dataclass

# Un'etichetta leggibile per ogni codice di esito. Il codice resta stabile per
# log/telemetria; l'etichetta è quella mostrata nel messaggio d'errore visura.
REASON_LABELS_IT: dict[str, str] = {
    "solved": "risolto",
    "disabled": "provider disattivato",
    "no_answer": "nessuna risposta",
    "solver_exception": "eccezione del solver",
    # Agent CLI (Cursor)
    "agent_unavailable": "Agent non avviabile",
    "agent_exit_error": "Agent terminato con errore",
    "agent_provider_error": "Agent quota/autenticazione esaurita",
    "agent_no_candidate": "Agent senza trascrizione utile",
    # codex-lb
    "codex_lb_disabled": "codex-lb disattivato o senza API key",
    "codex_lb_connect_error": "codex-lb non raggiungibile",
    "codex_lb_timeout": "codex-lb timeout",
    "codex_lb_http_error": "codex-lb errore HTTP",
    "codex_lb_api_error": "codex-lb errore API",
    "codex_lb_refusal": "codex-lb rifiuto del modello",
    "codex_lb_no_answer": "codex-lb nessun testo restituito",
    "codex_lb_unparseable": "codex-lb trascrizione non valida",
    "codex_lb_error": "codex-lb errore imprevisto",
    # Anti-Captcha
    "external_no_answer": "Anti-Captcha nessuna risposta",
    "external_error": "Anti-Captcha errore",
    # portale
    "sister_rejected": "trascrizione rifiutata da SISTER",
}


@dataclass(slots=True)
class CaptchaSolveResult:
    """Testo trascritto (``None`` se fallito) + motivo dell'esito."""

    text: str | None
    reason: str = "no_answer"
    provider: str = "unknown"
    detail: str = ""

    @property
    def solved(self) -> bool:
        return bool(self.text)

    def label(self) -> str:
        """Etichetta leggibile, con il dettaglio tra parentesi se presente."""
        base = REASON_LABELS_IT.get(self.reason, self.reason)
        return f"{base} ({self.detail})" if self.detail else base


def as_result(value: object) -> CaptchaSolveResult:
    """Normalizza il ritorno di un callback solver.

    Accetta un ``CaptchaSolveResult`` già pronto oppure il vecchio contratto
    ``str | None`` (usato dai test e da eventuali solver esterni).
    """
    if isinstance(value, CaptchaSolveResult):
        return value
    if value is None:
        return CaptchaSolveResult(None, "no_answer")
    text = str(value).strip()
    return CaptchaSolveResult(text or None, "solved" if text else "no_answer")
