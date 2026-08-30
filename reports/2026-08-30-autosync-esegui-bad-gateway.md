# AutoSync “Esegui adesso” — Bad Gateway

Data: 2026-08-30

## Segnalazione

Premendo **Esegui adesso** nel pannello di sincronizzazione catastale continua, la UI mostrava:

```text
Errore sincronizzazione
Bad Gateway
```

## Evidenze CED

- `gaia-backend` risultava healthy a livello container, ma nei log due worker Uvicorn sono morti durante i tentativi:
  - `Child process [27] died`;
  - `Child process [5160] died`.
- Nginx/frontend restavano disponibili; il 502 era quindi transitorio sulla chiamata backend.
- Tutte le configurazioni AutoSync risultavano `enabled=false`.
- La configurazione operativa usava il pool moderno di 9 credenziali, priorità primaria e secondaria abilitate.
- `catasto_perpetual_sync_items`: `0` righe.
- Nessun batch creato negli ultimi 30 minuti.

## Causa

`maintain_perpetual_sync()` eseguiva il refresh delle sorgenti prima di controllare `config.enabled`.

Di conseguenza, anche con AutoSync **OFF**, `POST /elaborazioni/ruolo-autosync/run-now` avviava il caricamento iniziale dell’intero universo delle sorgenti catastali/Ruolo. Questo percorso è molto oneroso e il worker che gestiva la richiesta veniva terminato; nginx restituiva `502 Bad Gateway`.

Il controllo `enabled` esisteva soltanto più avanti, in `ensure_perpetual_sync_batch()`, quindi arrivava troppo tardi.

## Correzione

File runtime:

```text
backend/app/services/elaborazioni_perpetual_sync.py
```

È stato aggiunto un ritorno immediato prima di qualsiasi refresh:

```python
if not config.enabled:
    return None
```

Con AutoSync OFF, “Esegui adesso” non carica più le sorgenti e non può abbattere il worker backend.

## TDD e qualità

- RED: il test mostrava le chiamate inattese `['refresh', 'ensure']` con configurazione disattivata.
- GREEN: nessuna chiamata eseguita e risultato `None`.
- Test mirati: `2/2 PASS`.
- Suite backend correlata: `65/65 PASS`.
- Coverage del file runtime:
  - statements: `189/189 — 100%`;
  - branches: `58/58 — 100%`.
- Complexity ratchet: `PASS`, `findings: []`.
- `git diff --check`: `PASS`.

## Deploy CED

Distribuito esclusivamente il file runtime backend e riavviato soltanto `gaia-backend`, dopo conferma esplicita dell’utente.

Backup rollback:

```text
/opt/gaia/backups/hotfixes/20260830-014336-autosync-run-bad-gateway/elaborazioni_perpetual_sync.py
```

Checksum:

```text
3ba6f1c91f741330462d8fbefee66c9ff215c3560d97a5355521208382e184f5  backup pre-deploy
7aff69aaed3cec1dcfa369d32017abe23a423f826a9456c60eab91a815936f18  runtime CED finale
```

## Verifica post-deploy

- `gaia-backend`: `healthy`;
- `/health`: HTTP `200`;
- `/openapi.json`: HTTP `200`;
- quattro worker Uvicorn avviati regolarmente;
- nessun nuovo `Child process ... died`, traceback o errore nei log post-riavvio;
- guardia `enabled` presente nella sorgente live;
- `catasto_perpetual_sync_items`: ancora `0`;
- batch creati negli ultimi 30 minuti: `0`.

## Stato operativo

Il 502 causato dal click con AutoSync OFF è corretto. Nessun job era stato creato dai tentativi falliti.

La configurazione sul CED è attualmente **OFF**. In tale stato il comando verifica correttamente che non vi sia nulla da avviare e non materializza la coda. L’attivazione reale dell’AutoSync è un’azione distinta e mutante, da effettuare consapevolmente tramite **Metti su ON**.

Nessun commit o push eseguito.
