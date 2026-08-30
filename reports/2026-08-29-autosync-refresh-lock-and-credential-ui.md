# GAIA — sblocco “Aggiorna sorgente” e UI credenziali

**Data:** 2026-08-29
**Stato:** PASS — implementato, verificato e distribuito sul CED

## Problema segnalato

Nel pannello **Sincronizzazione catastale continua**:

1. il pulsante **Aggiorna sorgente** rimaneva in caricamento e bloccava tutti i controlli;
2. la selezione delle credenziali SISTER era poco leggibile su mobile;
3. mancava un comando per selezionare tutte le credenziali.

## Diagnosi live

Il problema è stato verificato direttamente su PostgreSQL del CED.

Il refresh manuale usava un advisory lock PostgreSQL **session-level**:

```sql
pg_advisory_lock(namespace, user_id)
```

Il lock rimaneva associato alla connessione restituita al pool anche dopo `COMMIT`/`ROLLBACK`. Alle 21:53 risultavano:

- un PID `idle` ancora titolare del lock;
- tre POST in attesa dello stesso lock da circa **49–52 minuti**;
- query in attesa: `SELECT pg_advisory_lock(...)`.

Il frontend non aveva un timeout applicativo e manteneva `busy=true` fino al termine della POST; di conseguenza tutto il pannello rimaneva disabilitato.

## Correzione backend

File:

```text
backend/app/services/elaborazioni_ruolo_autosync.py
```

Interventi:

- sostituito il lock session-level con `pg_try_advisory_xact_lock`;
- lock mantenuto su una connessione dedicata e rilasciato con rollback della transazione;
- acquisizione non bloccante;
- se un’altra operazione possiede già il lock, risposta HTTP **409** immediata con messaggio:

```text
Un aggiornamento delle sorgenti è già in corso. Riprova tra poco.
```

Questo impedisce sia il leak nel pool sia l’accodamento indefinito delle richieste manuali.

## Correzione frontend/UI

File:

```text
frontend/src/components/elaborazioni/continuous-catasto-sync-panel.tsx
```

Interventi:

- timeout UI di 30 secondi sul refresh; allo scadere il pannello si riabilita e mostra un errore comprensibile;
- conteggio `N di M selezionate`;
- pulsanti **Seleziona tutte** e **Deseleziona tutte**;
- credenziali in card più grandi e adatte al touch;
- checkbox da 20 px e area cliccabile sull’intera card;
- username separato dall’etichetta;
- badge distinti **Disponibile** / **Non disponibile**;
- stato selezionato più evidente;
- fieldset disabilitato finché il draft completo non è disponibile.

## Test e gate

### Backend mirato

```text
60 test PASS
```

Comando:

```bash
cd backend
../.venv/bin/pytest tests/test_elaborazioni_ruolo_autosync_lock.py tests/test_elaborazioni_api.py -q
```

Copertura verificata:

- lock transazionale;
- rollback/rilascio anche in eccezione;
- mancata esecuzione quando il lock è occupato;
- risposta busy HTTP 409;
- regressioni API/autosync esistenti.

### Frontend mirato

```text
74/74 PASS
```

### Coverage pannello

```text
Statements  100% (121/121)
Branches    100% (116/116)
Functions   100% (50/50)
Lines       100% (84/84)
```

Artifact coverage:

```text
/tmp/gaia-autosync-coverage
```

### Suite frontend completa

```text
184 file PASS
1.658/1.658 test PASS
```

### Typecheck e build

- TypeScript `tsc --noEmit`: **PASS**;
- Next.js production build: **PASS**, 154 pagine generate;
- restano warning lint preesistenti in file non toccati.

### Complexity

Il gate differenziale contro `HEAD` è **PASS con 0 finding**:

```bash
.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref HEAD
```

Il comando aggregato `complexity_ci_gate.sh` prosegue poi con il controllo globale e fallisce per debito preesistente in GIS/Ruolo/Presenze e altri file non toccati; nessun finding riguarda questo intervento.

### Suite backend completa

La suite completa ha rilevato 4 failure non introdotte da questo intervento:

1. un test SISTER tenta di monkeypatchare un simbolo già assente in `elaborazioni_batches`;
2. tre test Wiki analytics ricevono liste vuote (`top_vehicles`, `top_operators`, `by_team`).

I 60 test del perimetro autosync/API sono tutti verdi.

## Checksum locali da distribuire

```text
ce8ab2248fd3901825b86422f456902458a4adfaffc4a048cb60869b0b8cb41b  backend/app/services/elaborazioni_ruolo_autosync.py
f9c0b5fd8e86db458bc2b330d0b8e7861d585b3c2a53da9325796c7b18622f94  frontend/src/components/elaborazioni/continuous-catasto-sync-panel.tsx
```

## Deploy CED eseguito

Distribuiti esclusivamente:

```text
/opt/gaia/backend/app/services/elaborazioni_ruolo_autosync.py
/opt/gaia/frontend/src/components/elaborazioni/continuous-catasto-sync-panel.tsx
```

Backup rollback:

```text
/opt/gaia/backups/hotfixes/20260829-224424-autosync-refresh-ui/
```

Servizi riavviati:

```text
gaia-backend
gaia-frontend
```

## Verifica produzione

- checksum locale/live: corrispondenti per entrambi i file;
- `gaia-backend`: **healthy**;
- `gaia-frontend`: **healthy**;
- frontend `/elaborazioni`: **HTTP 200**;
- backend `/openapi.json`: **HTTP 200**;
- backend `/health`: **HTTP 200**;
- import del nuovo lock autosync nel container: **OK**;
- advisory lock del namespace autosync dopo il riavvio: **0**;
- le tre richieste precedentemente in attesa non sono più presenti;
- log backend/frontend post-riavvio: nessun errore di import, compilazione o runtime rilevato.

## Rollback

In caso di anomalia:

1. ripristinare i due file da `/opt/gaia/backups/hotfixes/20260829-224424-autosync-refresh-ui/`;
2. riavviare `gaia-backend` e `gaia-frontend`;
3. verificare health, HTTP e log.
