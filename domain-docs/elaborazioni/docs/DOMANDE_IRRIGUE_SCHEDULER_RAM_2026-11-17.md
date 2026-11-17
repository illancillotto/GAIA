# Scheduler Domande irrigue: memoria ed executor — 17 novembre 2026

Il planner Sister era bloccato dai riavvii OOM dello scheduler condiviso.
La scansione anomalie Domande irrigue materializzava tutte le entita ORM,
inclusi JSON sorgente e geometrie. Il limite di memoria resta 2 GiB; aumentarlo
temporaneamente a 4 GiB non aveva risolto la causa.

## Correzioni

- `domande_irrigue_anomaly_queries.py` seleziona soltanto i campi scalari
  necessari, tramite Bundle SQLAlchemy, un anno alla volta.
- La scansione conserva regole, transazione unica e chiusura globale finale
  delle anomalie obsolete. I dati sorgente restano conservati.
- Il job APScheduler registra una funzione sincrona che esegue il wrapper
  asincrono nel proprio executor. Creazione, uso e chiusura della sessione DB
  restano nello stesso thread; `max_instances=1` e `coalesce=True` invariati.
  Gli altri job possono avanzare durante la scansione.

## Verifica e rilascio

La verifica RAM comprende 62 test, coverage statement/branch 100% dei due
runtime, assenza di JSON/geometrie nelle query e nessuna entita sorgente ORM
caricata. La verifica executor comprende 47 test e coverage 100%; due prove
con APScheduler reale passano sul candidato server e falliscono sull'originale.
Lint e ratchet mirati contro il merge-base di main passano. I grafi codice
Catasto e backend sono stati aggiornati tramite i target Make dedicati.

Il calcolo in sola lettura su 108.118 domande e 429.881 dettagli ha prodotto
40.039 anomalie in 17,9 secondi, con picco RSS 281,76 MiB. Il ciclo completo
con persistenza e terminato alle 08:12 UTC, consentendo al planner Sister
di aggiungere 17 richieste. Questo non attesta un nuovo download PDF.

La release finale `gaia-scheduler:executor-20261117`, avviata alle 09:05 UTC,
include entrambe le correzioni; prima esecuzione riuscita alle 09:06 UTC,
circa 229 MiB e zero riavvii al controllo. Solo lo scheduler e stato ricreato.
Script di applicazione e rollback sul CED:
`/opt/gaia/releases/scheduler-executor-20261117/`.

Il modulo scheduler gia installato differiva dal checkout nelle politiche
di refresh e di completamento: sul server e stata applicata esclusivamente
la piccola modifica executor, preservando tali differenze. Il commit locale
non implica che l'intero modulo del checkout sia stato distribuito.

Artefatti di verifica locali: `/tmp/gaia-scheduler-ram-20261117/`,
`/tmp/gaia-scheduler-executor-20261117/` e log/coverage associati.
Nessuna credenziale, payload privato o configurazione del container e inclusa.
