# Stato sync INAZ negli snapshot GaTe Mobile

**Data:** 2026-08-31 08:37 CEST
**Stato:** PASS - implementazione distribuita e verificata su `serverCed`

## Risultato

Gli snapshot `months`, `giornaliere` e `anomalie` espongono il nuovo oggetto
globale additivo `inaz_sync`, mantenendo `schema_version: 1` e senza cambiare la
semantica di `synced_from_gaia_at`.

Il resolver usa esclusivamente i job live persistiti in
`presenze_sync_jobs`. Non usa `updated_at` delle giornaliere e non genera un
timestamp INAZ al momento della risposta. Lo stato supporta `success`,
`running`, `degraded`, `error` e `never`; un fallimento successivo non cancella
`last_success_at`.

## Verifiche locali

- Suite mirata: `90 passed`.
- Coverage runtime modificato: `1028/1028`, `100%`.
- Complexity ratchet sul merge-base `840c010001e0aa45434539c4cf96065de61bdc41`: PASS, nessun finding.
- `git diff --check`: PASS.
- Graphify codice Presenze: `836` nodi, `2760` archi, `28` community.

## Deploy CED

Non erano presenti job Presenze `queued` o `running` prima del restart. Sono
stati aggiornati i tre componenti runtime del resolver, ricostruita l'immagine
`gaia-backend:latest` e ricreati soltanto `backend` e `presenze-worker`.
Entrambi usano l'immagine `sha256:08023c6727c0748b9620ce659d82e167de3f60cd1a4e089e11733379b7292a6c`.

Backup rollback:

```text
/opt/gaia/backups/hotfixes/inaz-sync-status-20260831T063228Z
```

Nessuna migrazione o variazione di configurazione e stata necessaria.

## Verifica produzione

- `backend`: running e healthy.
- `presenze-worker`: running.
- `/health`: HTTP 200.
- OpenAPI: cinque route Presenze Mobile Sync presenti.
- `months`: HTTP 200, stato INAZ `degraded`, 8 mesi.
- `giornaliere?month=2026-08`: HTTP 200, stato INAZ `degraded`, 5859 righe.
- `anomalie?month=2026-08`: HTTP 200, stato INAZ `degraded`, 954 righe.
- Ciclo connector end-to-end: completato senza failure; push `months`, due
  snapshot `giornaliere`, due snapshot `anomalie` e lettura pending-actions
  tutti con HTTP 200.
- Log recenti backend/worker: nessun traceback, exception o error.

Ogni risposta verificata esponeva `status`, `last_attempt_at`,
`last_success_at`, `data_updated_at`, `error_code` ed `error_message`. Token,
payload personali e dettagli errore grezzi non sono stati registrati nel report.

## Stato Git

Le modifiche non correlate gia presenti nel working tree sono state preservate.
Il deploy non ha richiesto push dal checkout locale.
