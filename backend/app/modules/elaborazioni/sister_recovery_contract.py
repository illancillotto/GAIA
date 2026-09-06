"""Recovery deadline shared by the API and the Python 3.10 SISTER worker."""

from datetime import datetime, timedelta, timezone

from app.models.catasto import CatastoVisuraRequest

REMOTE_STATES = frozenset({"submitted", "pending", "ready"})
RECOVERY_WINDOW = timedelta(hours=24)


def is_remote_recovery(request: CatastoVisuraRequest) -> bool:
    return request.sister_remote_state in REMOTE_STATES


def recovery_stop_reason(request: CatastoVisuraRequest, now: datetime) -> str | None:
    if not is_remote_recovery(request):
        return None
    submitted = request.sister_first_submitted_at
    if submitted is None:
        return "Data primo invio SISTER sconosciuta: verifica manuale necessaria"
    submitted = submitted.replace(tzinfo=submitted.tzinfo or timezone.utc)  # noqa: UP017 - Python 3.10.
    if submitted > now:
        return "Data primo invio SISTER futura: verifica manuale necessaria"
    if now >= submitted + RECOVERY_WINDOW:
        return "Finestra di recupero SISTER di 24 ore scaduta: verifica manuale necessaria"
    if not request.sister_remote_request_url:
        return "URL richiesta SISTER mancante: verifica manuale necessaria, nessun reinvio"
    return None
