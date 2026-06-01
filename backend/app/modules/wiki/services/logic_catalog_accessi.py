from __future__ import annotations

ACCESSI_PERMISSION_SOURCE_EXPLANATIONS: dict[str, str] = {
    "super_admin": "abilitazione completa per ruolo super_admin",
    "user_override": "override esplicito assegnato all'utente",
    "role_default": "permesso derivato dalla configurazione del ruolo",
    "min_role": "permesso concesso dalla soglia minima del ruolo della sezione",
    "denied": "nessuna regola applicativa ha concesso l'accesso",
}
