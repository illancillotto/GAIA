> Verifica storica antecedente alle slice. Stato corrente: le19regressioni del
> ciclo sono risolte; restano8finding Wiki unrelated nel gate globale.
> Vedere [report slice](TURNISTI_COMPLEXITY_SLICES_2026-10-05.md) per test/coverage finali.

# Verifica coordinata turnisti GAIA / GaTe — 5 ottobre 2026

**FINAL QUALITY GATE — FAIL**

La verifica funzionale locale è completata; la chiusura coordinata non è
certificabile: il ratchet GAIA fallisce su19 regressioni del ciclo e GAIA live
espone ancora il contratto precedente. Nessuna nuova feature, baseline,
threshold, scanner, dipendenza o esclusione quality modificata. Nessun commit,
push, deploy, restart, backfill o sync reale eseguito da questa verifica.

## Scope e base

```text
GAIA branch: main
GAIA HEAD/base: 17242e81ee607ad9e0eeb09d3f60d7cd4964f972
GAIA working tree iniziale verifica originaria: 40 file dirty; staging vuoto
GAIA working tree iniziale test finali: 46 file dirty (42 ciclo + 4 unrelated); staging vuoto
GaTe branch: main
GaTe HEAD: 6d07f9d9c7c93e8dcbbdb0b6270b029ddbc4c627
GaTe working tree iniziale: baseline locale e report storico unrelated
scope: ciclo GAIA non committato turnisti/CCNL/API/frontend/migration e parità GATE
```

Il diff base…HEAD GAIA è vuoto; perimetro reale ricostruito dal diff locale e dai
nuovi file.17 Python runtime/migration,5 frontend runtime e1 file di tipi TS
senza codice eseguibile. Tutti i40 percorsi iniziali sono del ciclo turnisti;
nessun altro runtime è stato alterato. Inventario e copie iniziali in
`/tmp/gaia-gate-coordinated-20261005/initial.json` e `initial-files/`.
Il PASS GATE del report precedente rimane limitato a quel repository e commit.

## Comportamenti e matrice test

| Comportamento | File principali | Atteso | Test / evidenza | Stato |
| --- | --- | --- | --- | --- |
| Tipo e date | shift_worker_schemas; gate_daily_record_schemas | none/acquaiolo/telecontrollo; range ordinato nello stesso mese; timestamp aware, command ID obbligatorio, no comandi misti | test_presenze_shift_workers | PASS |
| Timbrature/assenze/riposi | shift_worker_rules; schedule_engine; operational_quality |420min configurati; coppie positive complete, split/mezzanotte, overlap respinti; assenze canoniche; riposi0 | test_presenze_shift_workers; shift_ccnl; suite Presenze | PASS |
| CCNL e calendario | shift_ccnl; daily_details | notte22–06,8bucket, calendario due giorni, TitoloII/avventizi candidati senza payroll; sabato non festivo automatico | test_presenze_shift_ccnl; fixturecmp; parità reale builder | PASS |
| Buoni e regressione legacy | meal_vouchers; gate_daily_record_patch |419/420min, decorrenza26/08; incompleto/assenza niente automatico; manuale OR automatico massimo1; no fallback extra per turno non qualificato | shift_workers; meal_vouchers; coordinated_regression | PASS |
| Scope globale e autorizzazioni | router/routes/shift_workers; pagina giornaliere | admin/super_admin/HR ammessi; viewer/operator anche proprietari403; no scritture;401/404/422 e conflitto409 | shift_workers; coordinated_regression; unit pagina; Chromium | PASS |
| Assegnazioni, precedenza e revoca | shift_assignments; gate_shift_assignment; modello | GATE precede GAIA/import, anche revoca; nuovi import ereditano range; ordine e retry command_id senza duplicare | shift_workers LAN/outbound; PG concorrente | PASS |
| Snapshot e contratto GATE | gate_mobile_sync builder; shared GATE; overlay | payload vero accettato Zod e bucket ricalcolati identici; doppie chiavi compatibili | snapshot sintetico builder→Zod→overlay;128 mirati iniziali; fixturecmp | PASS |
| Trasporti e failure path | job outbound, API LAN, connector | ACK/fail/errori e scope; nessun nuovo inbound connector; nessun accesso app diretto GAIA | suite gate_mobile_sync/mobile_sync_API; connector E2E | PASS locale |
| Persistenza/migration | shift_worker_models;20261003_1200 | FK/unique/check/index; lock collaboratore; retry concorrente singolo; downgrade conserva giornaliera | test_presenze_shift_workers_postgres; altri4suite PG | PASS |
| UI/browser |5runtime frontend e pagina | tipo/date/range mese, no doppio submit, loading/error/retry, lock GATE, reload mese; viewer disabilitato |3829unit coverage;3Chromium | PASS |
| Export e regressioni | schemi, daily_details, meal_vouchers | notturno/buoni/bucket conservati in dettaglio e XLSM, regola legacy diurni invariata | regression Presenze incluse export/schedule/operai/union-leave | PASS |
| Versione reale e ultimo run | API LAN GAIA; VPS GATE; stato outbound admin | nuova route/campi e ultimo run/mese/record GATE verificabili | sonde GET sanitizzate, nessuna scrittura | RESIDUAL BLOCKING |

## Fix e test della verifica

- Difetto riprodotto prima del fix: viewer/operator proprietari ricevevano200
  sul comando range/persona, potendo modificare anche giornate fuori scope.
  Route usa `_can_view_all_inaz_data` e controllo edit esistenti; frontend usa
  `accessContext.can_view_all_data`. Nessun nuovo resolver o bypass.
- Due regressioni403/no writes, una unit UI e una Chromium per proprietario
  senza scope globale; tre casi positivi admin/super_admin/hr_manager per una
  persona di altro proprietario.
- Due regressioni LAN/outbound sul buono manuale: grant/retry/revoke con
  due soli eventi audit e zero buoni finali. Coprono un failure di coverage reale.
- Copy UI corretto: soglia7ore ordinarie effettive e decorrenza, senza promettere
  un buono a prescindere dalla durata.
- Ruff: variabile inutilizzata `day`→`_day`, ordinamento import test e formatter
  della sola nuova route. Nessuna suppression nuova.

Nuovo file: `backend/tests/test_presenze_coordinated_regression.py`.
Altri test modificati: shift_workers, unit pagina, smoke operational-controls.

## Esecuzioni originarie (storiche; risultati correnti nella sezione finale)

Evidenze locali temporanee sotto `/tmp/gaia-gate-coordinated-20261005/`.
Comando completo della suite backend in `backend-command.json`; config coverage
`backend.coveragerc`: source directory app/alembic, report limitato ai17 file
runtime/migration iniziali; nessuna esclusione né neutralizzazione pragma.
L’elenco report è quello dello scope, non una misura differenziale su sole righe.

| Comando | Esito / conteggio |
| --- | --- |
| backend pytest shift_workers,shift_ccnl,gate_mobile_sync,mobile_sync_API | PASS128 iniziali prima del fix; esito storico della stessa sessione |
| pytest owner_cannot prima del fix | FAIL2,200 invece di403 |
| pytest owner_cannot/route_enforces dopo il fix | PASS3 |
| pytest regression Presenze/GATE con PG e coverage su directory app/alembic |1078PASS,zero skip; coverage99.80% iniziale su codice finale |
| pytest coordinated_regression --cov-append --cov-branch --cov-fail-under=100 | PASS5; coverage aggregata100% |
| pytest5suite PostgreSQL con GAIA_TEST_POSTGRES_URL e TEST_WHATSAPP_POSTGRES_URL | PASS11,zero skip |
| frontend npm run test:coverage -- --maxWorkers=2, include esplicito5runtime | PASS3829test/271suite;100% tutte4metriche |
| frontend npm run lint | PASS, warning legacy fuori delta |
| frontend npm run typecheck | PASS |
| frontend npm run build | PASS, Next build163pagine; warning legacy |
| make lint-backend QUALITY_PYTHON=backend/.venv/bin/python BASE_REF=17242e81 | PASS |
| make quality-test | PASS169 |
| make complexity-report | PASS, report emesso |
| make complexity-ci-gate BASE_REF=17242e81 | FAIL19finding, arresto al ratchet |
| GATE shared test:coverage | PASS32,100% tutte4metriche |
| GATE test:e2e con DATABASE_URL su PG isolato | PASS3 |
| frontend Playwright operational-controls su Next locale | PASS3Chromium |
| alembic heads dalla directory backend | PASS, unico head20261003_1200 |
| cmp fixture CCNL GATE/GAIA | PASS |
| builder GAIA sintetico→GATE Zod→overlay notturno | PASS |

Tentativi non verdi preservati: interprete di sistema senza Ruff; primo
coverage con source a nomi modulo importava troppo presto e ha causato44errori
collection SQLAlchemy; sostituito con sorgenti directory, senza cambiare file
quality. PG iniziale nominava un file inesistente, corretto. Primo run1076PASS
aveva2skip WhatsApp per variabile mancante, poi entrambi eseguiti. Coverage
route iniziale inattendibile dopo formatter concorrente: rigenerata da zero
sul codice finale. Connector senza DATABASE_URL falliva connection refused;
rilancio su database dedicato PASS. Nessuno di questi tentativi è dichiarato PASS.

## Coverage finale

Backend: **1239/1239 statements,264/264 branches**,17file; nessuna riga esclusa.
Frontend: **1228/1228 statements,1385/1385 branches,319/319 functions,1010/1010 lines**.

| File runtime/migration misurato | Coverage |
| --- | --- |
| `backend/alembic/versions/20261003_1200_presenze_shift_assignments.py` |100% statements /100% branches |
| `backend/app/modules/presenze/daily_record_schemas.py` |100% statements /100% branches |
| `backend/app/modules/presenze/gate_daily_record_schemas.py` |100% statements /100% branches |
| `backend/app/modules/presenze/models.py` |100% statements /100% branches |
| `backend/app/modules/presenze/router/__init__.py` |100% statements /100% branches |
| `backend/app/modules/presenze/router/routes/shift_workers.py` |100% statements /100% branches |
| `backend/app/modules/presenze/services/daily_details.py` |100% statements /100% branches |
| `backend/app/modules/presenze/services/gate_daily_record_patch.py` |100% statements /100% branches |
| `backend/app/modules/presenze/services/gate_shift_assignment.py` |100% statements /100% branches |
| `backend/app/modules/presenze/services/meal_vouchers.py` |100% statements /100% branches |
| `backend/app/modules/presenze/services/operational_quality.py` |100% statements /100% branches |
| `backend/app/modules/presenze/services/schedule_engine.py` |100% statements /100% branches |
| `backend/app/modules/presenze/services/shift_assignments.py` |100% statements /100% branches |
| `backend/app/modules/presenze/services/shift_ccnl.py` |100% statements /100% branches |
| `backend/app/modules/presenze/services/shift_worker_rules.py` |100% statements /100% branches |
| `backend/app/modules/presenze/shift_worker_models.py` |100% statements /100% branches |
| `backend/app/modules/presenze/shift_worker_schemas.py` |100% statements /100% branches |
| `frontend/src/app/presenze/giornaliere/page.tsx` |100% statements /branches /functions /lines |
| `frontend/src/components/presenze/shift-worker-badge.tsx` |100% statements /branches /functions /lines |
| `frontend/src/components/presenze/shift-worker-control.tsx` |100% statements /branches /functions /lines |
| `frontend/src/components/presenze/use-shift-worker-assignment.ts` |100% statements /branches /functions /lines |
| `frontend/src/lib/api/presenze-shift-workers.ts` |100% statements /branches /functions /lines |

Python verifica statements/branches; frontend V8 verifica anche functions/lines.
JSON completi con righe/archi in `backend-coverage.json` e
`frontend-coverage/coverage-final.json`. File tipi `presenze-base.ts` privo di
runtime, escluso dalla policy V8 esistente; non introdotta nuova esclusione.
Il rerun finale unico esegue1083test, inclusi i5nuovi, tutti PASS;
non richiede append alla coverage.
Hash dei23 percorsi runtime/schema in `final-runtime-hashes.json`.

## Complessità: blocco attribuito al ciclo

Scanner identico eseguito nel checkout pulito detached del base e in GAIA:
base1589file/19649callable/4738violation (2041error,2697warning);
corrente1600file/19685callable/4747violation (2041error,2706warning).
Il numero error-level invariato non rende verde il ratchet: vieta anche il
peggioramento delle metriche legacy. I19finding sono tutti differenti dal
codice reale del base, non soltanto da una baseline stale. Prova riproducibile:
`complexity-base.json`, `complexity-current.json`, `complexity-proof.json`.

| File / simbolo | Metrica | Base reale | Corrente |
| --- | --- | ---: | ---: |
| `backend/app/modules/presenze/services/daily_details.py` / `classification_breakdown_values` | cyclomatic | 2 | 3 |
| `backend/app/modules/presenze/services/daily_details.py` / `classification_breakdown_values` | cognitive | 1 | 2 |
| `backend/app/modules/presenze/services/daily_details.py` / `classification_breakdown_values` | loc | 13 | 18 |
| `backend/app/modules/presenze/services/daily_details.py` / `classification_breakdown_values` | nesting | 0 | 1 |
| `backend/app/modules/presenze/services/gate_daily_record_patch.py` / `apply_gate_daily_record_patch` | cyclomatic | 3 | 4 |
| `backend/app/modules/presenze/services/gate_daily_record_patch.py` / `apply_gate_daily_record_patch` | cognitive | 2 | 3 |
| `backend/app/modules/presenze/services/gate_daily_record_patch.py` / `apply_gate_daily_record_patch` | loc | 13 | 15 |
| `backend/app/modules/presenze/services/meal_vouchers.py` / `meal_voucher_values` | cyclomatic | 8 | 12 |
| `backend/app/modules/presenze/services/meal_vouchers.py` / `meal_voucher_values` | cognitive | 7 | 11 |
| `backend/app/modules/presenze/services/meal_vouchers.py` / `meal_voucher_values` | loc | 15 | 28 |
| `backend/app/modules/presenze/services/schedule_engine.py` / `classify_daily_record` | cyclomatic | 56 | 57 |
| `backend/app/modules/presenze/services/schedule_engine.py` / `classify_daily_record` | cognitive | 62 | 63 |
| `backend/app/modules/presenze/services/schedule_engine.py` / `classify_daily_record` | loc | 121 | 128 |
| `frontend/src/app/presenze/giornaliere/page.tsx` / `PresenzeGiornalierePage` | cyclomatic | 457 | 458 |
| `frontend/src/app/presenze/giornaliere/page.tsx` / `PresenzeGiornalierePage` | cognitive | 550 | 551 |
| `frontend/src/app/presenze/giornaliere/page.tsx` / `PresenzeGiornalierePage` | loc | 2275 | 2276 |
| `backend/app/modules/presenze/models.py` / `file` | loc | 514 | 517 |
| `backend/app/modules/presenze/services/schedule_engine.py` / `file` | loc | 578 | 588 |
| `frontend/src/app/presenze/giornaliere/page.tsx` / `file` | loc | 3009 | 3011 |

Baseline/scanner/soglie non modificati. Risolvere questo blocco richiede una
tranche di semplificazione pertinente e revisionabile; non un semplice
riallineamento del JSON. Nessun refactoring trasversale eseguito per nasconderlo.
Il ci-gate non ha raggiunto check/baseline-verify dopo il ratchet fallito:
questi ultimi **non sono dichiarati eseguiti** da quel comando.

## Migration, sicurezza e architettura

Nuova revision20261003_1200, parent20261002_1030; una sola testa. Tabella additiva
con PK, FK CASCADE collaboratore, FK actor, command_id UNIQUE,3CHECK e indice
persona/date. PostgreSQL16-alpine isolato: upgrade/downgrade/re-upgrade e retry
concorrente verificati; nessuna migration del database reale. Non dichiarato
eseguito l’intero storico Alembic da database vuoto: le suite preparano schemi
isolati e applicano le migration pertinenti.

Auth/modulo/visibilità, scope persona,409GATE authority,422contratto, parametro
SQLAlchemy e transazioni verificati dalle suite. HTML frontend usa escaping
React; nessun token o dato personale reale salvato/stampato. Mapping sintetico
esplicito nella prova builder; nessun backfill né inferenza di identità reale.
Business rule canonica GAIA e overlayGATE: fixture condivisa identica; trasporti
preservati. Connector rimane outbound-only; operator app invariata.
Ordine multi-processo dei timestamp GATE non certificato da questa verifica.

## Sonde read-only live e rilascio residuo

GAIA LAN handshake200 e capabilities Presenze; snapshot ottobre200,5704record,
zero con `shift_worker_type`; OpenAPI live senza route `/turnista`.
Il codice verificato localmente non è quindi attestato nel rilascio reale.
VPS operations200 con token configurato per outbound GAIA: snapshot recente
`2026-10-05T07:58:32.063Z`, ricevuto `07:58:49.684Z`; connector GAIA offline
(ultimo heartbeat `07:56:34.207Z`). È un massimo aggregato, non la prova di
una giornata o di un run outbound concluso. Status outbound GAIA401 con token
connector: richiede sessione amministrativa. Il token del file GATE.vps ha
restituito401, riportato senza esporlo; non è stato sostituito o modificato.

Manca evidenza completa canale attivo/ultimo run/mese specifico/record GATE.
Prima della chiusura reale: gate locale verde, rilascio autorizzato GAIA/GATE,
migration e verifica versione, stato ultimo run e almeno un record turnista
ricevuto in GATE con identità e valori coerenti. Nessun deploy è autorizzato
implicitamente da questo report.

## Docs, Graphify e stato della verifica originaria

Report corrente, progress Presenze e prefisso del report storico aggiornati.
La mappa codice è aggiornata con `make graphify-presenze-code` (1372nodi,
4210archi,57comunità) e `make graphify-frontend` (update PASS, nessun delta topologico
nell’ultimo refresh;6483nodi/15529archi). Artefatti ignorati; nessun output Graphify committato.
Mappa semantica dominio: `make graphify-presenze-docs` PASS, chunk1/1 done,
967nodi/1846archi/71comunità;19203token input/4984output, costo stimato0.0157USD.
Nessuna degradazione partial/failed. Refresh finale sui documenti consolidati
nel log `graphify-presenze-docs-final.log`: PASS, chunk1/1 done,
974nodi/1867archi/73comunità;5582token input/4518output, costo stimato0.0095USD. Query/JSON confermano schema, servizi e controlli
turnisti nei corpus codice.

DONE: verifica funzionale locale e fix sicurezza, parità payload, PG/browser/build.
PARTIAL: consolidamento GAIA non committato, quality gate non verde.
RESIDUAL BLOCKING:19regressioni metriche; rilascio e prova end-to-end reale.
PRE-EXISTING/NON-BLOCKING:2041error-level scanner, warning lint legacy e chiave
JWT sintetica breve nei test. Non equivalgono a finding security produttivi.
OUT OF SCOPE: nuove feature, payroll/HR/rotazione non attestati, backfill,
refactor generici, Android nativo e modifiche a baseline/tooling.

Working tree:40file iniziali preservati, modificati solo file del ciclo;
aggiunti regression test e report corrente. Nessun segreto, dump, screenshot,
coverage, build o grafo selezionato nello staging. Staging vuoto.
Final commit: nessuno; non si consolida con gate bloccante.
Cleanup effettuato: container PG dedicato e Next locale arrestati/rimossi;
schemi test residui0; worktree base di sola lettura rimosso dopo lo scanner.
Cache Python creata incidentalmente dal probe GATE eliminata; nessun servizio
preesistente fermato. GAIA finale42path dirty (40iniziali+2nuovi), staging vuoto.
GATE finale2unrelated byte-identici+il solo nuovo report coordinato.
Nessun output Graphify/coverage/log/build nello staging.


## Riproduzione coverage backend completa

Eseguire dalla root GAIA con database PostgreSQL dedicato e variabili
`GAIA_TEST_POSTGRES_URL` e `TEST_WHATSAPP_POSTGRES_URL` puntate a quel database.
Le fixture creano e cancellano schemi isolati. Usare il seguente filtro temporaneo
per misurare gli interi17file, anche `__init__.py` e migration:

```ini
[run]
branch = True
[report]
include =
    */backend/app/modules/presenze/daily_record_schemas.py
    */backend/app/modules/presenze/gate_daily_record_schemas.py
    */backend/app/modules/presenze/models.py
    */backend/app/modules/presenze/router/__init__.py
    */backend/app/modules/presenze/services/daily_details.py
    */backend/app/modules/presenze/services/gate_daily_record_patch.py
    */backend/app/modules/presenze/services/meal_vouchers.py
    */backend/app/modules/presenze/services/operational_quality.py
    */backend/app/modules/presenze/services/schedule_engine.py
    */backend/alembic/versions/20261003_1200_presenze_shift_assignments.py
    */backend/app/modules/presenze/router/routes/shift_workers.py
    */backend/app/modules/presenze/services/gate_shift_assignment.py
    */backend/app/modules/presenze/services/shift_assignments.py
    */backend/app/modules/presenze/services/shift_ccnl.py
    */backend/app/modules/presenze/services/shift_worker_rules.py
    */backend/app/modules/presenze/shift_worker_models.py
    */backend/app/modules/presenze/shift_worker_schemas.py
```

Salvare come `/tmp/gaia-turnisti.coveragerc`, quindi:

```bash
COVERAGE_FILE=/tmp/gaia-turnisti.coverage backend/.venv/bin/python -m pytest \
  backend/tests/test_presenze*.py backend/tests/test_gate_mobile_sync.py \
  backend/tests/test_operazioni_mobile_sync_api.py \
  --cov=backend/app --cov=backend/alembic --cov-config=/tmp/gaia-turnisti.coveragerc \
  --cov-branch --cov-fail-under=100 --cov-report=term-missing \
  --cov-report=json:/tmp/gaia-turnisti-coverage.json
```

Il rerun finale include i5nuovi casi nella stessa esecuzione dei1083test.
Nessun pragma nuovo, branch ignorato o test fittizio.

### Inventario iniziale della verifica originaria

- `README.md` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/daily_record_schemas.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/gate_daily_record_schemas.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/models.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/router/__init__.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/services/daily_details.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/services/gate_daily_record_patch.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/services/meal_vouchers.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/services/operational_quality.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/services/schedule_engine.py` — CURRENT CYCLE, presente all’avvio.
- `backend/tests/test_gate_mobile_sync.py` — CURRENT CYCLE, presente all’avvio.
- `docs/ARCHITECTURE.md` — CURRENT CYCLE, presente all’avvio.
- `docs/IMPLEMENTATION_PLAN.md` — CURRENT CYCLE, presente all’avvio.
- `docs/PRD.md` — CURRENT CYCLE, presente all’avvio.
- `domain-docs/presenze/docs/PROGRESS_PRESENZE.md` — CURRENT CYCLE, presente all’avvio.
- `frontend/src/app/presenze/giornaliere/page.tsx` — CURRENT CYCLE, presente all’avvio.
- `frontend/src/types/api/presenze-base.ts` — CURRENT CYCLE, presente all’avvio.
- `frontend/tests/e2e/presenze-operational-controls.spec.ts` — CURRENT CYCLE, presente all’avvio.
- `frontend/tests/unit/presenze-giornaliere-page.test.tsx` — CURRENT CYCLE, presente all’avvio.
- `skills/gate-mobile-sync-contract/SKILL.md` — CURRENT CYCLE, presente all’avvio.
- `backend/alembic/versions/20261003_1200_presenze_shift_assignments.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/router/routes/shift_workers.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/services/gate_shift_assignment.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/services/shift_assignments.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/services/shift_ccnl.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/services/shift_worker_rules.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/shift_worker_models.py` — CURRENT CYCLE, presente all’avvio.
- `backend/app/modules/presenze/shift_worker_schemas.py` — CURRENT CYCLE, presente all’avvio.
- `backend/tests/fixtures/shift-ccnl.json` — CURRENT CYCLE, presente all’avvio.
- `backend/tests/test_presenze_shift_ccnl.py` — CURRENT CYCLE, presente all’avvio.
- `backend/tests/test_presenze_shift_workers.py` — CURRENT CYCLE, presente all’avvio.
- `backend/tests/test_presenze_shift_workers_postgres.py` — CURRENT CYCLE, presente all’avvio.
- `domain-docs/presenze/docs/TURNISTI_CCNL_2026.md` — CURRENT CYCLE, presente all’avvio.
- `domain-docs/presenze/docs/TURNISTI_FINAL_REPORT.md` — CURRENT CYCLE, presente all’avvio.
- `domain-docs/presenze/docs/TURNISTI_GAIA_GATE.md` — CURRENT CYCLE, presente all’avvio.
- `frontend/src/components/presenze/shift-worker-badge.tsx` — CURRENT CYCLE, presente all’avvio.
- `frontend/src/components/presenze/shift-worker-control.tsx` — CURRENT CYCLE, presente all’avvio.
- `frontend/src/components/presenze/use-shift-worker-assignment.ts` — CURRENT CYCLE, presente all’avvio.
- `frontend/src/lib/api/presenze-shift-workers.ts` — CURRENT CYCLE, presente all’avvio.
- `frontend/tests/unit/presenze-shift-workers.test.tsx` — CURRENT CYCLE, presente all’avvio.


## Test finali richiesti — esecuzione corrente

Questa sezione sostituisce gli esiti storici come evidenza della verifica finale.
Evidenze: `/tmp/gaia-gate-final-tests-20261005-_6bwuhsb/`; nessun runtime o test
modificato durante questo rerun. La matrice precedente copre i comportamenti:
non aggiunti test che eseguono righe senza verificare risultati.

| Comando effettivo | Risultato corrente |
| --- | --- |
| pytest Presenze + gate_mobile_sync + operazioni_mobile_sync_API, `--cov=backend/app --cov=backend/alembic --cov-branch --cov-fail-under=100` | PASS1083, nessuno skip,17file100% |
| frontend `npm run test:coverage`, perimetro5runtime | PASS3829test /271suite;100% statements/branches/functions/lines |
| frontend `npm run lint`, `npm run typecheck`, `npm run build` | PASS, warning legacy documentati |
| `make lint-backend QUALITY_PYTHON=backend/.venv/bin/python BASE_REF=17242e81` | PASS |
| `make quality-test` | PASS169 |
| `make complexity-ci-gate BASE_REF=17242e81` | FAIL26finding nel rerun finale:19del ciclo +7Wiki unrelated (prima23=19+4) |
| GATE `npm run quality:test`, `npm run lint` | PASS36 / PASS |
| GATE `npm run test:coverage:ci` | PASS954test (626gateway,97connector,199operator,32shared); typecheck/build4workspace PASS |
| GATE `npm run test:integration` su PostgreSQL16 isolato | PASS53test /8suite |
| GATE `npm run test:e2e` | PASS3connector |
| Chromium GAIA operational-controls / GATE console smoke | PASS3 / PASS16 |
| GATE `npm run openapi:test`, `npm run openapi:verify` | PASS1 / PASS |
| GATE `npm run complexity:ci-gate -- --base-ref e691a663ab196f19f47e2ec4b5b174006d2bc4c7` | PASS, baseline autorevole del base |
| `make graphify-presenze-code`, `make graphify-frontend` | PASS, AST invariato |
| GATE `npm run graphify:code-map` | PASS5840nodi /9857archi /337comunità; HTML omesso dal limite5000nodi |
| `make graphify-platform-docs` | PASS chunk1/1,2454nodi /5667archi /166comunità; nessun partial/failed |

Coverage rigenerata da zero: Python1239/1239statements,264/264branches,
0righe escluse; frontend1228/1228statements,1385/1385branches,
319/319functions,1010/1010lines. Tutti i22file runtime/migration della tabella
coverage precedente sono coperti integralmente. Il JSON coverage.py misura
statements/lines e branches; non fornisce una percentuale functions distinta.
GATE100% su tutte4metriche per ogni workspace nel perimetro coverage versionato;
nessun runtime GATE modificato da questa verifica.

### Residui e classificazione

- BLOCKING:19regressioni ciclo elencate sopra, immutate rispetto al codice
  reale del base. Non si modifica baseline/scanner/soglie per assorbirle.
- PRE-EXISTING / UNRELATED:4ulteriori finding `wiki/mcps/http.py::create_http_app`
  (cyclomatic1→2,cognitive0→1,LOC44→50,nesting0→1); lavoro già presente all’avvio.
  Preservati anche test Wiki e due documenti `docs/code-quality`.
- PARTIAL: consolidamento e commit non eseguiti perché il ratchet resta rosso.
- OUT OF SCOPE rispetto al gate locale: deploy, sync/backfill, migration
  produttiva e certificazione del rilascio coordinato. Le sonde live precedenti
  non sono state rieseguite e non provano un rilascio successivo.

Non applicato refactoring trasversale: la skill
`skills/gaia-complexity-reduction/SKILL.md` impone di fermarsi se «la slice supera
una singola unita revisionabile»; i finding attraversano più responsabilità.
La fase finale richiesta non autorizza una riprogettazione generica.
Nessun commit con un controllo bloccante, come richiesto dall’utente.

### Ulteriori comandi e working tree finale

- GATE `npm ci`: PASS; `npm run test`: PASS954test /123suite.
- GATE `npm run complexity:report`: report269runtime/361violation/134error;
  `npm run complexity:check`: FAIL134error legacy, distinta dal ratchet PASS.
  Il confronto base già documentato nel report GATE mostra134error al base.
- `npm audit --json`:53finding (2low,13moderate,37high,1critical shell-quote).
  Lockfile SHA256 identico al base e HEAD: debito preesistente, nessun audit fix.
- `make graphify-presenze-docs`: PASS chunk1/1,987nodi/1902archi/73comunità,
  15345token input/5379output,costo stimato0.0147USD; nessun partial/failed.
  Ulteriore refresh sui report finali registrato nel log `graphify-presenze-docs-final.log`.
- `make graphify-platform-docs` finale: PASS,126cache hit/0miss,
  2455nodi/5670archi/153comunità. Nessuna nuova estrazione semantica necessaria.
- Cleanup: Next locale dedicato arrestato, container PostgreSQL dedicato rimosso;
  nessun servizio preesistente fermato.

Alla verifica di igiene: GAIA49percorsi dirty,42ciclo +7unrelated. I3percorsi
Wiki aggiuntivi sono `backend/app/modules/wiki/mcps/cli.py`,
`backend/app/modules/wiki/mcps/data/cli.py`, `backend/tests/test_wiki_mcp_console.py`.
Sono comparsi durante il rerun e non sono stati modificati da questa verifica.
I due documenti `docs/code-quality/{HOTSPOTS,PROGRESS}.md` sono cambiati anch’essi
esternamente; non ripristinati né sovrascritti. Wiki HTTP e test HTTP restano
byte-identici all’inizio. I23runtime/schema del ciclo e tutti i test del ciclo
sono byte-identici all’inizio del rerun: la coverage finale è pertinente.
Il ratchet finale è rieseguito sul working tree corrente:26finding,
19del ciclo e7Wiki unrelated (4iniziali,3ulteriori nei CLI).
Il blocco del ciclo resta distinto dal lavoro Wiki. Il codice Wiki concorrente non è certificato
dalle suite del ciclo turnisti.

GATE3percorsi dirty: report coordinato CURRENT CYCLE, baseline locale e report
storico PRE-EXISTING / UNRELATED; nessuno dei due toccato da questa verifica.
`git diff --check` PASS entrambi; `git ls-files --others --exclude-standard`
contiene solo sorgenti/test/documenti del ciclo e il report storico unrelated.
Nessun env/segreto/dump/log/screenshot/coverage/build/grafo nello staging;
staging vuoto entrambi. Inventario finale in `gaia-final-hygiene.json` e
`gate-final-hygiene.json` nella directory evidenze locale.

```text
Final commit: nessuno (gate bloccante)
GAIA HEAD finale: 17242e81ee607ad9e0eeb09d3f60d7cd4964f972
GATE HEAD finale: 6d07f9d9c7c93e8dcbbdb0b6270b029ddbc4c627
Working tree after commit: non applicabile; modifiche lasciate non committate
```

FINAL QUALITY GATE — FAIL


## Correzione slice successiva

Il 2026-10-05 sono state rimosse le19regressioni del ciclo, senza cambiare
baseline/soglie. Risultati e stato corrente: [report slice](TURNISTI_COMPLEXITY_SLICES_2026-10-05.md).
Gli esiti precedenti restano storici; il gate globale include lavoro Wiki unrelated.
