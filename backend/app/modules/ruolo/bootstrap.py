"""Bootstrap sections per il modulo Ruolo."""

RUOLO_SECTIONS = [
    {"key": "ruolo.dashboard", "label": "Ruolo — Dashboard", "module": "ruolo", "min_role": "viewer"},
    {"key": "ruolo.avvisi", "label": "Ruolo — Avvisi", "module": "ruolo", "min_role": "viewer"},
    {"key": "ruolo.import", "label": "Ruolo — Import", "module": "ruolo", "min_role": "admin"},
    {"key": "ruolo.stats", "label": "Ruolo — Statistiche", "module": "ruolo", "min_role": "viewer"},
]
