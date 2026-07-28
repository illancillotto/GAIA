# WhiteCompany Operazioni Live Sync Fix

Data: `2026-07-28`

## Contesto

Il job scheduler `whitecompany_operazioni_live_sync` risultava configurato e attivo, ma le
entity operative:

- `reports`
- `refuels`
- `taken_charge`
- `warehouse_requests`

non venivano piu riallineate con continuita.

## Root cause

Nel runtime `backend/app/services/elaborazioni_bonifica_sync.py` la funzione
`_has_active_jobs()` considerava bloccanti i job con stato `queued` o `running` e
`finished_at IS NULL`.

La funzione di cleanup `_expire_stale_running_jobs()` marcava pero come scaduti solo i job
`running`. Se un job restava orfano in stato `queued` dopo restart backend o interruzione del
task originale, il live sync orario continuava a essere saltato con log:

`WhiteCompany Operazioni live job skipped: pending/running jobs already exist`

## Fix applicata

Modifica runtime:

- `_expire_stale_running_jobs()` ora scade sia i job `queued` sia i job `running`;
- il messaggio di errore persistito riporta lo stato reale del job orfano (`queued` o
  `running`), utile per diagnosi successive.

File runtime aggiornato:

- `backend/app/services/elaborazioni_bonifica_sync.py`

## Test e coverage

Test backend eseguiti nel container `gaia-backend`:

```bash
pytest tests/test_elaborazioni_bonifica_oristanese.py tests/test_elaborazioni_bonifica_sync_live_unit.py --cov=app.services.elaborazioni_bonifica_sync --cov-report=term-missing -q
```

Esito:

- test: `35 passed`
- coverage `app/services/elaborazioni_bonifica_sync.py`: `100%`

Branch coperti dalla regressione:

- scadenza job `queued` stale;
- scadenza job `running` stale/orfani dopo restart backend;
- fallback utente attivo per job daily/live;
- errore esplicito se nessun utente Operazioni e disponibile;
- bootstrap failure prima dell'esecuzione entity;
- bootstrap failure dopo `pick_credential()`;
- gestione job id mancanti o non piu presenti;
- generazione search code refuel con skip di candidati vuoti o duplicati.

## Verifica operativa

Prima della fix erano presenti job orfani:

- `users` `queued` dal `2026-05-20`
- `warehouse_requests` `queued` dal `2026-05-20`

Dopo il deploy locale della patch:

- i job orfani sono stati marcati `failed`;
- non risultano piu job `queued/running` aperti bloccanti in `wc_sync_job`;
- e stata lanciata una run manuale del live sync WhiteCompany.

Esito run manuale `2026-07-28 09:51 UTC`:

- `reports`: `completed`, `162` sincronizzati
- `refuels`: `completed`, `22` sincronizzati
- `taken_charge`: `completed`, `159` sincronizzati, `4` errori dati
- `warehouse_requests`: `completed`, `42` sincronizzati

Errori dati residui osservati su `taken_charge`:

- `vehicle HC514PV non trovato`
- `vehicle HC513PV non trovato`

## Nota operativa

La patch e stata applicata anche nel container runtime locale `gaia-backend` per sbloccare
subito lo scheduler. Al prossimo rebuild/recreate del servizio backend l'immagine deve
includere questa versione del sorgente per mantenere il fix persistente.
