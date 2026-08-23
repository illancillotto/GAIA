from __future__ import annotations


class SisterServerError(RuntimeError):
    """SISTER ha restituito un errore 500 — logout, rotazione credenziale, attesa, retry."""


class SisterConventionSelectionError(RuntimeError):
    """Il profilo SISTER richiesto non e' disponibile o non e' identificabile in modo univoco."""


class SisterRequestCorrelationError(RuntimeError):
    """La richiesta remota non puo' essere correlata in modo sicuro alla richiesta locale."""


class SisterNotFoundError(RuntimeError):
    """SISTER non ha trovato il soggetto o l'immobile richiesto."""


class SisterInvalidDocumentError(RuntimeError):
    """Il file restituito da SISTER non e' un PDF valido."""


class DocumentNotYetProducedError(RuntimeError):
    """SISTER ha accettato la visura ma il documento non è ancora stato prodotto."""

    remote_id: str | None = None

    def __init__(self, richieste_url: str | None = None) -> None:
        super().__init__("IL DOCUMENTO NON E' STATO ANCORA PRODOTTO")
        self.richieste_url = richieste_url

    @classmethod
    def correlated(cls, richieste_url: str | None, remote_id: str | None) -> "DocumentNotYetProducedError":
        error = cls(richieste_url)
        error.remote_id = remote_id
        return error


class DocumentNonEvadibileError(RuntimeError):
    """La richiesta SISTER è finita tra i non evadibili — eliminare e ritentare."""


class SisterDocumentNotReadyError(TimeoutError):  # pragma: no cover
    """Il documento SISTER non è ancora disponibile dopo i poll iniziali.

    Viene sollevata da poll_richieste_for_download quando max_attempts è
    impostato a un valore ridotto e scade senza trovare il documento.
    La richiesta deve essere salvata come 'queued_sister' e ripresa più tardi.
    """