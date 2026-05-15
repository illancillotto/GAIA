from __future__ import annotations


class SisterServerError(RuntimeError):
    """SISTER ha restituito un errore 500 — logout, rotazione credenziale, attesa, retry."""


class DocumentNotYetProducedError(RuntimeError):
    """SISTER ha accettato la visura ma il documento non è ancora stato prodotto."""

    def __init__(self, richieste_url: str | None = None) -> None:
        super().__init__("IL DOCUMENTO NON E' STATO ANCORA PRODOTTO")
        self.richieste_url = richieste_url


class DocumentNonEvadibileError(RuntimeError):
    """La richiesta SISTER è finita tra i non evadibili — eliminare e ritentare."""
