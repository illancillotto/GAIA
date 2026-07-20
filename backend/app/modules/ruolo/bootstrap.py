"""Bootstrap sections per il modulo Ruolo."""

RUOLO_SECTIONS = [
    {"key": "ruolo.dashboard", "label": "Ruolo — Dashboard", "module": "ruolo", "min_role": "viewer"},
    {"key": "ruolo.avvisi", "label": "Ruolo — Avvisi", "module": "ruolo", "min_role": "viewer"},
    {"key": "ruolo.import", "label": "Ruolo — Import", "module": "ruolo", "min_role": "admin"},
    {"key": "ruolo.stats", "label": "Ruolo — Statistiche", "module": "ruolo", "min_role": "viewer"},
    {"key": "ruolo.tributi.view", "label": "Ruolo Tributi — Consultazione", "module": "ruolo", "min_role": "viewer"},
    {
        "key": "ruolo.tributi.manage_payments",
        "label": "Ruolo Tributi — Gestione pagamenti",
        "module": "ruolo",
        "min_role": "admin",
    },
    {
        "key": "ruolo.tributi.manage_status",
        "label": "Ruolo Tributi — Gestione stati",
        "module": "ruolo",
        "min_role": "admin",
    },
    {
        "key": "ruolo.tributi.manage_notes",
        "label": "Ruolo Tributi — Gestione note",
        "module": "ruolo",
        "min_role": "reviewer",
    },
    {
        "key": "ruolo.tributi.generate_reminders",
        "label": "Ruolo Tributi — Generazione solleciti",
        "module": "ruolo",
        "min_role": "reviewer",
    },
    {
        "key": "ruolo.tributi.import_payments",
        "label": "Ruolo Tributi — Import pagamenti",
        "module": "ruolo",
        "min_role": "admin",
    },
    {"key": "ruolo.tributi.admin", "label": "Ruolo Tributi — Amministrazione", "module": "ruolo", "min_role": "admin"},
]
