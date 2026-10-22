# STEP riscossione: sync e collegamento al ruolo

Aggiornamento: 2026-10-21.

Integrazione in sola lettura del portale STEP (Prunesenti/servizienti,
ente `14215`, sezione Contribuenti) per la riscossione coattiva delle
annualita 2018-2021 affidate a STEP. Il connettore e il port Python del
`step-scraper` Node.js usato per la prima estrazione completa del
2026-10-20 (3.354 contribuenti, 3.410 documenti/PDF, 21.265 tributi).

## Architettura

| Livello | File |
| --- | --- |
| Modelli e migration | `backend/app/modules/elaborazioni/step/models.py`, `backend/alembic/versions/20261021_1200_elaborazioni_step_archive.py` |
| Credenziali e coda job | `step/credentials.py`, `step/jobs.py` |
| Persistenza e storico | `step/persistence.py`, `step/parsing.py`, `step/storage.py` |
| Import archivio scraper | `step/archive.py` |
| Collegamento ruolo | `step/ruolo_link.py` |
| API | `backend/app/modules/elaborazioni/step_routes.py` (`/elaborazioni/step`) |
| Autosync opzionale | `step/scheduler.py`, controllato dal worker STEP quando e inattivo |
| Worker | `modules/elaborazioni/worker/step_worker.py`, `step_sync.py`, `step_client.py`, `step_rules.py`, `step_browser_scripts.py` |
| UI | `/elaborazioni/step` (`frontend/src/components/elaborazioni/step/`) |

Il worker STEP e un processo dedicato (`elaborazioni-worker-step` in
`docker-compose.yml`), separato da `worker.py`: un sync completo tiene il
browser per decine di minuti e non deve rallentare le altre famiglie. Un solo
job STEP alla volta: l'API rifiuta con `409` un nuovo job finche un altro e
`pending` o `processing`.

## Job

| Modalita | Effetto |
| --- | --- |
| `credential_test` | solo login |
| `list_only` | legge tutte le pagine Contribuenti e aggiorna le righe elenco |
| `sync` | elenco completo, poi scheda (documenti, tributi, PDF, pagamenti, procedure) dei contribuenti nuovi o la cui riga elenco e cambiata; `force_details` le rilegge tutte, `max_details` limita il lotto |
| `archive_import` | importa un `raccolta-completa.zip` del vecchio scraper dalla cartella `STEP_IMPORT_ROOT` |
| `relink` | ricalcola tutti i collegamenti al ruolo (dopo nuovi import `ruolo_avvisi` o correzioni del parser) |

Stati: `pending -> processing -> succeeded | completed_with_errors | failed`,
`cancelled` per i job annullati in coda. Al riavvio del worker i job
`processing` tornano `pending`.

Regole del connettore (dal checkpoint dello scraper verificato):

- il portale sovrascrive `window.Set`: si legge solo con `page.evaluate`, mai
  `locator.evaluate_all` o `page.wait_for_function`;
- SmartClient ignora click ravvicinati: pausa minima 600 ms;
- ogni pagina elenco, tabella della scheda e pagina tributi e validata
  (totali, righe attese, colonne, duplicati, pagine ripetute): un dato parziale
  interrompe la scheda, non viene salvato;
- una scheda puo avere documenti in piu griglie (Emessi, Presi in carico) e
  piu documenti dell'elenco: la differenza e registrata in
  `document_reconciliation_json`;
- tre schede fallite consecutive fermano il lotto (`completed_with_errors`);
  dopo ogni errore il browser viene riaperto;
- solo un rifiuto del login conta per la disattivazione della credenziale
  (3 tentativi); errori di rete o del portale non penalizzano l'account.

### Rilevamento cambiamenti

`RESIDUO` e `IMPORTO_AGGIORNATO` dell'elenco crescono ogni giorno per gli
interessi: vengono aggiornati dall'elenco ma **non** fanno riscaricare la
scheda. La verifica live del 2026-10-21 ha trovato 570 righe cambiate solo per
interessi e una sola modifica reale (pagamento); il `sync` riapre quindi solo
la scheda effettivamente cambiata. Una variazione che non tocca le colonne
dell'elenco (es. solo una procedura) richiede `force_details`.

## Dati

- `step_contribuenti`: riga elenco (importi correnti), anagrafica e situazione
  contabile per etichetta (gli ID SmartClient `isc_*` sono instabili e
  scartati), sezioni della scheda (pagamenti, procedure esecutive/cautelari e
  propedeutiche) e impronte;
- `step_documenti`, `step_tributi`, `step_pagamenti`: snapshot corrente,
  riscritto quando la scheda cambia; `raw_json` conserva il record originale;
- `step_observations`: storico append-only di ogni versione osservata della
  scheda;
- PDF: archiviati per contenuto in `STEP_DOCUMENT_STORAGE_PATH`
  (`<ente>/<sha[:2]>/<sha>.pdf`), verificati per firma PDF e SHA-256,
  scaricabili da `GET /elaborazioni/step/documenti/{id}/pdf`.

Importi: formati italiani (`1.405,12`) e numerici (`258.27`) convertiti in
`Decimal`; un valore ambiguo (`1.405`) o malformato resta `NULL` con
l'originale in `raw_json`, mai `0`.

## Collegamento al ruolo

`step_ruolo_links` collega ogni riferimento avviso di un documento STEP a
`ruolo_avvisi`, nel rispetto di
`domain-docs/ruolo/docs/STEP_IMPORT_IMPLEMENTAZIONE.md`:

- unico identificatore: il `codice_cnc` di 15 cifre stampato da STEP nel
  tributo (`Avv. N. 020190006018040 ...`, oppure `Bollettazione n. ...` per le
  bollettazioni 2022/2023);
- un documento multi-annualita produce un collegamento per ciascun avviso;
- `linked` solo per corrispondenza univoca; con piu avvisi stesso codice si usa
  l'annualita del tributo come seconda meta della chiave
  `(codice_cnc, anno_tributario)`;
- `not_found`, `ambiguous` (con candidati) e `unrecognized` (codici troncati,
  16 cifre, protocolli `PG...`) restano anomalie visibili in UI;
- codice fiscale, nome e importi non sono mai usati per collegare;
- gli incassi STEP non creano pagamenti GAIA.

## Proiezione nel registro avvisi

Dopo ogni `sync`, `archive_import` e `relink` il worker aggiorna la
valutazione STEP (`ruolo_notice_recoveries`) delle posizioni del registro
collegate agli avvisi `linked` (`step/register_projection.py`):

| Evidenza STEP sui documenti collegati all'avviso | Stato registro |
| --- | --- |
| almeno un carico non coperto da pagamenti/discarichi | `affidato` |
| carico interamente discaricato (sgravio) | `revocato` |
| carico coperto da pagamenti (ed eventuali discarichi) | `chiuso` |

- scrittura tramite `assess_recovery` del registro: lock del documento,
  controllo versione e riga `ruolo_notice_audit` con motivazione
  `Pubblicazione automatica stato STEP (job N)`;
- `case_reference` = numeri documento STEP, `evidence_reference` =
  `STEP sync job N del AAAA-MM-GG: documenti STEP ...`, `amount` = carico;
- una decisione dell'operatore non viene mai sovrascritta: si aggiorna solo una
  posizione `da_verificare` o con evidenza scritta dalla proiezione; le altre
  sono contate in `register.operator_decision`;
- documenti del registro gia riconciliati, posizioni senza avviso e avvisi
  senza posizioni (`without_position`) non vengono toccati; un conflitto di
  versione e contato e ritentato al job successivo;
- l'assenza da STEP non prova nulla: `non_affidato_verificato` non viene mai
  impostato; `affidato` e `chiuso` bloccano la generazione come previsto da
  `notice_eligibility`, `revocato` la libera;
- autore audit: l'utente che ha accodato il job; per l'autosync notturno
  `STEP_REGISTER_ACTOR_USER_ID` (id di `application_users`); senza autore la
  proiezione e saltata e il job riporta `register.skipped`.

Sul dataset del 2026-10-20 i riferimenti sono 7.355 gruppi documento/avviso;
36 non riconoscibili. Il tasso di `linked` dipende dagli avvisi presenti in
`ruolo_avvisi` dell'ambiente: dopo un nuovo import del ruolo eseguire `relink`.

## Messa in produzione

1. `alembic upgrade head` (revisione `20261021_1200`).
2. `docker compose up -d --build backend elaborazioni-worker-step`.
3. Copiare l'archivio verificato nel volume:
   `docker compose exec elaborazioni-worker-step mkdir -p /data/catasto/step/import`
   e `docker compose cp raccolta-completa.zip elaborazioni-worker-step:/data/catasto/step/import/`.
4. Da `/elaborazioni/step` (super admin) avviare **Importa archivio** su
   `raccolta-completa.zip`. Il job verifica i totali con `verification.json`
   prima di scrivere e ogni PDF con lo SHA-256 della scheda; reimportare lo
   stesso archivio non duplica nulla. Tempo misurato in locale: circa 50 s.
5. Inserire la credenziale STEP, eseguire **Test login**, poi un `sync`.
   Misurato il 2026-10-21: elenco completo 336 pagine in circa 6 minuti.
6. Facoltativo: autosync notturno con `STEP_AUTOSYNC_ENABLED=true` nel `.env`
   del worker STEP (`STEP_AUTOSYNC_TIME`, default `02:15`,
   `STEP_AUTOSYNC_TIMEZONE`, default `Europe/Rome`). Come l'auto import
   registry del worker principale, il controllo gira nel loop inattivo del
   worker: un solo job `sync` al giorno dopo l'orario configurato, saltato se
   un job STEP e attivo o se non c'e una credenziale attiva.

Variabili: `STEP_DOCUMENT_STORAGE_PATH` (default
`/data/catasto/step/documents`), `STEP_IMPORT_ROOT` (default
`/data/catasto/step/import`), `STEP_BROWSER_PATH` (opzionale),
`STEP_AUTOSYNC_ENABLED`/`STEP_AUTOSYNC_TIME`/`STEP_AUTOSYNC_TIMEZONE`,
`STEP_REGISTER_ACTOR_USER_ID` (autore audit per l'autosync).

## Verifiche eseguite (2026-10-21)

- migration up/down/up su PostgreSQL 16 temporaneo;
- import reale dell'archivio completo su PostgreSQL: 3.354 contribuenti,
  3.410 documenti/PDF (SHA verificati), 21.265 tributi, 3.237 pagamenti, nessun
  importo/data non interpretato; reimport idempotente (0 schede cambiate);
- live sul portale: test login, `sync` con 3 schede (PDF salvati), `list_only`
  con rilevamento corretto delle sole modifiche reali;
- test backend (49) e worker (STEP 5 file) con coverage 100% statement/branch;
  frontend: 5294 test Vitest e smoke `npm test` verdi, `build:clean`, eslint e
  `tsc` puliti, coverage 100% sui file STEP/navigazione/dettaglio avviso;
- E2E Chromium (API simulate, 1440/390 px): nuova `elaborazioni-step.spec.ts`
  (workspace, dettaglio contribuente, link all'avviso, riquadro STEP sul
  dettaglio avviso, voce di menu) piu dashboard e specifiche ruolo pertinenti:
  24 PASS;
- complexity ratchet contro `main` senza finding sui file della change
  (verificato in un worktree isolato); la baseline condivisa non era
  riproducibile gia su `HEAD`: riparata a parte sul branch
  `chore/complexity-baseline-repair-20261021`.

## Stato in produzione (2026-10-22)

Rilascio parziale, solo backend, come overlay dell'immagine in esercizio
(`/opt/gaia/releases/step-archive-20261022/` e `step-linkfix-20261022/`):

- Completato: backup completo pre-rilascio, migration a `20261021_1200`
  (applicate anche `20261006_1200`, `20261007_1600/1800`, `20261019_1500`
  rimaste indietro), backend `gaia-backend:step-linkfix-20261022`.
- Completato: import di `raccolta-completa.zip` (job 1): 3.354 contribuenti,
  3.410 documenti e PDF, 21.265 tributi, 3.237 pagamenti.
- Corretto dopo l'import: STEP stampa il codice avviso senza il prefisso
  GAIA `01.` e con una cifra finale in piu, quindi il confronto esatto dava
  0 collegamenti; con `gaia_codice_cnc` il relink (job 2) ha prodotto 7.118
  `linked` (7.070 avvisi: 2018 584, 2019 1.437, 2020 1.916, 2021 2.997,
  2022 114, 2023 21, 2024 1), 201 `not_found`, 0 `ambiguous`,
  36 `unrecognized`.
- Proiezione nel registro: autore audit scelto `admin` (id 1). Anteprima del
  job 2: 0 posizioni interessate, perche il registro contiene solo avvisi
  2022-2023 (3.400 posizioni) e nessuno di quelli collegati a STEP. Non
  pubblicata; da eseguire quando nel registro entreranno avvisi collegati
  (`relink_publish.py publish 1` nella cartella del rilascio).
- Residuo: worker `elaborazioni-worker-step` (sync, autosync,
  `STEP_REGISTER_ACTOR_USER_ID`) e frontend `/elaborazioni/step` non
  rilasciati; credenziale STEP non inserita.

## Interfaccia

- menu Elaborazioni: voce **STEP riscossione** (sezioni del modulo in
  `frontend/src/components/layout/elaborazioni-navigation.ts`);
- dettaglio avviso ruolo `/ruolo/avvisi/{id}`: riquadro **Riscossione coattiva
  STEP** con i documenti collegati (`components/ruolo/step-avviso-card.tsx`,
  API `GET /elaborazioni/step/ruolo-avvisi/{id}`);
- dashboard `/elaborazioni` e ricerca operativa.

## Limiti noti

- una variazione STEP che non cambia le colonne dell'elenco richiede un `sync`
  con `force_details`;
- tasso di collegamento misurato in produzione il 2026-10-22 (vedi sotto):
  i 201 `not_found` residui (178 del 2018) sono avvisi assenti da
  `ruolo_avvisi`, i 36 `unrecognized` riferimenti non numerici (`PG...`) o
  codici accorciati;
- la proiezione non riapre posizioni gia decise da un operatore: eventuali
  discordanze sono visibili nel conteggio `operator_decision` del job.
