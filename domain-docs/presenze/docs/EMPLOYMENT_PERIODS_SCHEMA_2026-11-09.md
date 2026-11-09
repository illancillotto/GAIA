# Schema dei periodi contrattuali — 9 novembre 2026

La migrazione additiva `20261106_1000`, successiva a `20261104_1400`, crea
`presenze_employment_periods`: collaboratore canonico, intervallo di validita,
tipo di rapporto e provenienza documentale con hash, nota e operatore.

Vincoli su date, rapporto ammesso, unicita dell’inizio periodo e chiavi esterne
sono verificati su PostgreSQL in `test_presenze_employment_periods_postgres.py`.
Il downgrade rifiuta la cancellazione di attestazioni presenti.

Questo commit introduce soltanto schema e modello; la presentazione delle
assenze Avventizi resta un intervento separato. La migrazione e anche il
predecessore di `20261107_0900`, relativo al collegamento squadre/organigramma.
Nessun backfill o modifica alle identita viene eseguito dalla migrazione.
