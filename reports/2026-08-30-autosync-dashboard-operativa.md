# Dashboard operativa AutoSync — implementazione, test e deploy

**Data:** 2026-08-30
**Repository:** `/home/cbo/CursorProjects/GAIA`
**Ambito:** Elaborazioni / Visure / AutoSync

## Obiettivo

Aggiungere sopra la configurazione AutoSync una vista operativa equivalente al dettaglio batch, con stato corrente, statistiche, andamento orario, batch recenti, visure scaricate, blocchi ed eventi strutturati.

## Implementazione

### Backend

- Esteso `GET /elaborazioni/ruolo-autosync/status` con il campo strutturato `dashboard`.
- Creato `backend/app/services/elaborazioni_autosync_dashboard.py`.
- Aggregazioni filtrate per utente e per batch `ruolo_autosync`/`perpetual_sync`.
- Documenti conteggiati tramite `CatastoDocument -> CatastoVisuraRequest -> CatastoBatch`.
- Eventi derivati da record persistiti; nessuno scraping dei log Docker.
- Preservato il guard AutoSync OFF prima di refresh e materializzazione.

### Frontend

- Creato `AutoSyncActivityDashboard` e montato prima di `Configurazione AutoSync`.
- KPI: batch, richieste, visure scaricate da SISTER, velocità oraria, blocchi e durata media.
- Sezioni: stato operativo, andamento 24 ore, ultimi batch, blocchi/errori ed eventi.
- Link batch: `/elaborazioni/batches/<ID_JOB>`.
- Gestiti stati vuoto, OFF/idle, attivo, info/warning/error e valori nulli.

## Test e gate

- Backend correlato: **78 PASS**.
- Coverage backend runtime modificato: **100% statement e branch** su:
  - `app/schemas/catasto.py`;
  - `app/services/elaborazioni_autosync_dashboard.py`;
  - `app/services/elaborazioni_ruolo_autosync.py`.
- Frontend completo: **184 file / 1.663 test PASS**.
- Test dashboard mirato: **14 PASS**.
- Coverage frontend dashboard/pannello: **100% statement, branch, funzioni e linee** (`166/166`, `172/172`, `72/72`, `119/119`).
- TypeScript typecheck Node 20: **PASS**.
- Next.js production build Node 20: **PASS**; restano warning lint legacy non introdotti dalla dashboard.
- Quality tooling: **46 PASS**.
- Complexity ratchet su baseline autorevole `840c010001e0aa45434539c4cf96065de61bdc41`: **PASS**, `findings: []`.
- `git diff --check`: **PASS**.

## Graphify

- Aggiornati i grafi backend, frontend e documentazione.
- Ultimo grafo frontend: **5.531 nodi, 13.680 archi, 201 comunità**.
- `graph.html` non generato perché il grafo supera il limite di 5.000 nodi; `graph.json` e `GRAPH_REPORT.md` sono stati aggiornati.

## Documentazione

Aggiornato:

- `domain-docs/elaborazioni/docs/CATASTO_CONTINUOUS_SYNC.md`

con contratto API, semantica KPI, sorgenti autorevoli, layout UI, polling e verifiche richieste.

## Deploy CED

Stato: **COMPLETATO E VERIFICATO**.

- Commit sorgente usato per il deploy runtime: `1fc3e9320d3652241beea3a6c9b77062b2200033`.
- Backup CED: `/opt/gaia/backups/autosync-dashboard/20260830-032335`.
- File runtime distribuiti: 5 backend e 5 frontend.
- Tutti i file sono stati confrontati con `cmp` dopo la copia e registrati in `deployed.sha256`.
- Controllo `py_compile` backend: **PASS**.
- Riavviati soltanto i servizi compose `backend` e `frontend`.

### Verifica post-deploy

- `gaia-backend`: **healthy**.
- `gaia-frontend`: **healthy**.
- `GET /health`: **HTTP 200**.
- `GET /openapi.json`: **HTTP 200**.
- `/elaborazioni/visure`: **HTTP 200**.
- OpenAPI: endpoint `/elaborazioni/ruolo-autosync/status` presente.
- Schema `CatastoRuoloAutoSyncStatusResponse`: proprietà `dashboard` presente.
- Sorgente live frontend: etichetta `Attività AutoSync` presente.
- Sorgente live backend: `build_autosync_dashboard` presente.
- Log backend/frontend successivi al riavvio: **0** righe critiche (`Traceback`, `ERROR`, `Error:`, `FATAL`).

### Rollback

In caso di regressione:

1. ripristinare i file esistenti da `/opt/gaia/backups/autosync-dashboard/20260830-032335`, preservando i percorsi relativi;
2. rimuovere i file elencati in `new-files.txt`;
3. riavviare esclusivamente `backend` e `frontend` con Docker Compose;
4. ripetere healthcheck, verifica HTTP e controllo log.

## Avvertenze

- Non sono state materializzate code né creati batch di produzione per verificare la UI.
- Le modifiche non correlate presenti nel working tree non appartengono al commit AutoSync.
- Nessun segreto o dato di connessione è incluso nel report.
