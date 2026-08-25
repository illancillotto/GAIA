# Progress - GAIA Code Complexity Program

Questo file e la fonte di verita persistente. Hermes deve aggiornarlo dopo ogni
blocco verificato e prima di chiudere un goal.

## Stato generale

- Program status: `RATCHET_ACTIVE_ON_LOCAL_MAIN`
- Current phase: `3 - ordinary ratchet applied to feature recovery`
- Last verified commit: `31f875d4`
- Reference branch: `main`
- Working branch: `gaia/presenze-gate-canonical-export`
- Last update: `2026-08-20`
- Current owner: `GAIA maintainers`
- Active goal: `selective Presenze recovery with quality ratchet`
- Blocking CI enabled: `local_main_not_pushed`

> Il branch applicativo `gaia/code-complexity-refactor` e congelato come
> esperimento. Questa fondazione parte da `main` e non contiene i refactoring
> Catasto o Presenze del branch archiviato.

## Checkpoint

| Checkpoint | Stato | Evidenza | Approvazione |
| --- | --- | --- | --- |
| 0 - audit reale | pass | review branch/report 2026-08-20 | completed |
| 1 - tooling e baseline | pass | `df4ad919` integrato su `main` locale | completed |
| 2 - gate differenziale CI | pass on local main | `31f875d4`, workflow e gate locale verdi | push/review required |
| 3 - ratchet ordinario | technical pass | recupero Presenze verificato sul branch dedicato | review required |
| 4 - hotspot dedicato | on demand | solo per impedimento concreto | explicit decision |

## Decision log

| Data | Decisione | Motivo | Impatto |
| --- | --- | --- | --- |
| 2026-08-17 | Local-first in Fase 1 | Evitare dipendenza operativa dalla CI | Nessun gate bloccante prima del Checkpoint 1 |
| 2026-08-17 | Un hotspot per goal | Ridurre rischio e facilitare review/revert | Niente batch refactor |
| 2026-08-17 | `/goal` per modifiche, `/loop` per monitoraggio | Goal e verificabile; loop e temporizzato | Refactoring non eseguiti a timer |
| 2026-08-20 | Congelare `gaia/code-complexity-refactor` a `52798f96` | Catasto ha prodotto riduzione reale; Presenze H2-I1 ha spostato debito senza ridurre il callable obiettivo | Nessun altro hotspot sul branch; recupero selettivo del tooling |
| 2026-08-20 | Quality ratchet come modalita predefinita | Integrare la non-regressione nelle feature senza campagne massive | Hotspot dedicati solo quando bloccano sviluppo, test o manutenzione |
| 2026-08-20 | Baseline autorevole dal merge-base | La baseline della stessa change puo mascherare una regressione coordinata | Nuovo comando `complexity-ratchet`; CI in una change successiva alla fondazione |
| 2026-08-20 | Coverage invariata | Non abbassare implicitamente la policy esistente durante il redesign della complessita | Resta `100%` sui file runtime nuovi o modificati |
| 2026-08-20 | Workflow code-quality dedicato | Evitare duplicazione e divergenza tra CI backend/frontend | Un solo job autorevole per test tooling e ratchet |

## Esperimento archiviato

- Snapshot: `gaia/code-complexity-refactor` a `52798f964301a382bba37a794e4d5892ff06807d`.
- Catasto GIS: `IMPROVED`; riduzione cumulativa del callable principale circa
  cognitive `-23%`, cyclomatic `-26%`, con stop per rendimento marginale.
- Presenze H2-I1: `REORGANIZED_AND_CHARACTERIZED`; callable principale
  cognitive `577 -> 577`, cyclomatic `482 -> 482`, LOC `2314 -> 2314`, violation
  globali invariate e `6` violation trasferite al nuovo helper.
- Decisione: non integrare il branch in blocco e non iniziare H2-I2. Estrarre
  soltanto rules, skill, scanner e test dopo hardening.

## Audit corrente

- Branch/commit: `gaia/complexity-quality-ratchet` da `main@9562c9e6`.
- Working tree preesistente: pulito nel worktree dedicato; il working tree
  originale con modifiche Catasto/SISTER non e stato toccato.
- Tool estratti: scanner AST Python/JS, baseline, eccezioni, report e gate.
- Test tooling: suite completa `tests/code_quality`, non solo il file storico
  `test_complexity_tool.py`.
- Workflow CI: invariati in questa fase; attivazione rinviata finche la baseline
  non esiste nel branch di destinazione.
- Perimetro runtime: `backend/app`, `frontend/src`,
  `modules/elaborazioni/worker`.
- Coverage: policy corrente invariata.
- Rischio principale corretto: baseline della stessa change non autorevole.

## Fase 1

- [x] Audit completato
- [x] Architettura del motore disponibile nel diff per review
- [x] Adapter Python implementato
- [x] Adapter JS/TS implementato
- [x] Schema comune `2` implementato
- [x] Baseline generata da `main@9562c9e6`
- [x] Eccezioni validate
- [x] Ratchet contro baseline del merge-base implementato
- [x] Test dello strumento verdi
- [x] Target Make verificati
- [x] Documentazione completata
- [x] Report Checkpoint 1 prodotto
- [x] Nessun refactoring applicativo incluso

## Checkpoint 1 - fondazione quality ratchet (2026-08-20)

- Base: `main@9562c9e6711bb8384f889a8b9667a7a5a86eef55`.
- Branch/worktree: `gaia/complexity-quality-ratchet` in
  `/home/cbo/CursorProjects/GAIA-complexity-ratchet`.
- Perimetro: solo rules, skill, documentazione, scanner, test, baseline, report e
  script gate; nessun file runtime applicativo modificato.
- Baseline schema `2`: `1003` file, `15432` callable, `4328` violation (`2123`
  error, `2205` warning). I conteggi includono le soglie file-level, prima
  definite ma non applicate, e non sono confrontabili direttamente con i
  `4122` del prototipo.
- `make quality-test QUALITY_PYTHON=...` -> `33 passed`; la suite include tutti i
  file sotto `tests/code_quality`.
- `make complexity-check QUALITY_PYTHON=...` -> pass, findings vuoti.
- `make complexity-baseline-verify QUALITY_PYTHON=...` -> pass, baseline
  riproducibile ignorando timestamp, commit e metadati runtime.
- `complexity.py validate-exceptions` -> pass, nessuna eccezione.
- Test nuovi: soglia file su codice nuovo, peggioramento file legacy, regressione
  coordinata con baseline, scope change senza engine migration e merge-base
  mancante.
- `make complexity-ratchet BASE_REF=main` -> exit `2` atteso: la baseline non e
  ancora presente nel merge-base. Questo impedisce di attivare prematuramente
  la CI e prova la sequenza di rollout a due change.
- `make graphify-platform-docs` -> pass: `321` nodi, `376` archi, `41`
  community nel corpus `docs`; nessun grafo applicativo richiesto.
- Workflow CI: non modificati; Checkpoint 2 resta separato.

## Checkpoint 2 - attivazione CI (2026-08-20)

- Prerequisito: fondazione `df4ad919` integrata con fast-forward su `main`
  locale; la baseline esiste quindi al merge-base.
- Branch: `gaia/complexity-ratchet-ci`.
- Workflow: `.github/workflows/code-quality.yml`, separato dai workflow
  applicativi backend/frontend.
- Trigger PR: runtime backend/frontend/worker e infrastruttura code-quality.
- Trigger push: solo `main`, usando `github.event.before` come base autorevole.
- Checkout: `fetch-depth: 0`; Python `3.11`, Node `20`, `pytest` e dependency
  graph frontend installati esplicitamente.
- `make quality-test QUALITY_PYTHON=...` -> `33 passed`.
- Workflow YAML caricato con PyYAML -> pass.
- `make complexity-ci-gate BASE_REF=main QUALITY_PYTHON=...` -> pass:
  merge-base/baseline `df4ad919`, findings vuoti, baseline riproducibile ed
  eccezioni valide.
- `make graphify-platform-docs` -> pass: `346` nodi, `432` archi, `40`
  community; `104` file da cache e `3` riestratti.
- File runtime applicativi modificati: nessuno.

## Iterazione attiva

- ID: `none`
- Hotspot:
- Modulo:
- Motivazione:
- Invarianti:
- Test di caratterizzazione:
- Metriche prima:
- Slice pianificata:
- File previsti:
- Stato: `not_started`
- Metriche dopo:
- Verifiche:
- Coverage:
- Baseline diff:
- Esito:
- Debito residuo:

## Iterazioni concluse

| ID | Data | Hotspot | Prima | Dopo | Test/coverage | Commit/PR |
| --- | --- | --- | --- | --- | --- | --- |
| - | - | - | - | - | - | - |

## Modifiche funzionali verificate fuori dal programma hotspot

### 2026-08-19 - Export completo riepiloghi eventi INAZ

- Branch/worktree: `main` nel worktree dedicato `/home/cbo/CursorProjects/gaia-inaz-ferie-main`, base `2ded321cd99aeb59c02865e5e7f2bc158804e4b9`.
- Scope runtime: `backend/app/modules/presenze/services/parser.py` e nuovo `event_summary_export.py`.
- Invarianti: nessuna modifica a route, schema DB, autenticazione, autorizzazione, transazioni o sync; i campi legacy `*_minutes` persistiti restano compatibili.
- Correzione: segno delle durate negative `-HH:MM`; nuovo export unit-aware che conserva i valori grezzi e non filtra le descrizioni.
- Coverage: `pytest tests/test_presenze_event_summary_export.py tests/test_presenze_parser.py --cov=... --cov-fail-under=100` -> `17 passed`, `100%` sui due file runtime e sull'entrypoint CLI.
- Verifiche aggiuntive: compileall completato; suite mirate import/summary `16 passed`; suite backend completa senza failure; export read-only su produzione `6563` righe; Graphify code/docs aggiornato.
- Metriche complessita: tooling/target `complexity-*` non presente sul commit `main` di base; nessuna baseline modificata o rigenerata. Il nuovo servizio usa funzioni piccole e isolate, senza nuove esclusioni o eccezioni.
- Baseline diff: nessuno.
- Commit previsto: `fix(presenze): export complete INAZ event summaries`; PR: nessuna.

### 2026-08-20 - Versionamento hotfix live GATE Presenze

- Branch/worktree: `main` nel worktree dedicato `/home/cbo/CursorProjects/gaia-inaz-ferie-main`; nessuna integrazione dal branch `gaia/code-complexity-refactor`.
- Scope runtime: `backend/app/services/gate_mobile_sync.py`; diff live acquisito dal CED pari a `23` righe aggiunte e `2` rimosse.
- Invarianti: route, schema DB, autenticazione, autorizzazione e transazioni invariati; `_get_gate_record_or_404` continua a essere il gate autorizzativo finale.
- Comportamento: propagazione KM/reperibilita negli snapshot GATE e fallback del record giornaliero rigenerato tramite `collaborator_id/work_date`.
- Provenienza: il file modificato coincide byte per byte con il runtime CED, SHA256 `bb1aad87b1c05884d08afd5a33495a0887e1d081bde7ee2da9747127753ed30e`.
- Coverage: `pytest tests/test_gate_mobile_sync.py --cov=app.services.gate_mobile_sync --cov-fail-under=100` -> `28 passed`, `100%` (`655/655` statement).
- Metriche complessita: i target `complexity-*` non sono presenti sulla base `main`; nessuna baseline, eccezione o esclusione e stata importata dal branch di refactoring.
- Baseline diff: nessuno.

### 2026-08-20 - Recupero selettivo export canonico GATE Presenze

- Provenienza: cherry-pick del solo commit funzionale `f98b6495` dal branch
  archiviato; refactoring Catasto e Presenze H2-I1 esclusi. Il fix successivo
  `66feb26c` non e stato duplicato perche gia presente semanticamente su `main`.
- Invarianti: API, schema DB, auth, autorizzazioni, transazioni e fallback delle
  pending action invariati; il contratto aggiunge versione e valori canonici
  XLSM e collega i supervisori ai collaboratori quando disponibili.
- Primo ratchet: blocco atteso su `gate_mobile_sync.py`, con LOC file
  `1182 -> 1239` e `_gate_record_feature_values` LOC `6 -> 23`, params `1 -> 3`.
  La baseline non e stata aggiornata per assorbire la regressione.
- Slice locale: serializzazione snapshot estratta nel boundary di dominio
  `gate_mobile_payloads.py`; il sync resta orchestratore. Metriche mirate:
  `99 -> 100` callable e `53 -> 53` violation; LOC sync `1239 -> 1146`, nuovo
  servizio `118` LOC senza violation file-level.
- Coverage: `test_gate_mobile_sync.py` -> `28 passed`, `100%` su sync
  (`640/640`) e payload (`36/36`); test GATE di `test_presenze_api.py` ->
  `13 passed`, `100%` sul router (`343/343`); Vitest Presenze -> `60 passed`.
- Typecheck globale: non verde per failure preesistenti nei test TypeScript non
  toccati; `presenze-pages.test.tsx` non compare tra le failure.
- Quality gate: `complexity-ratchet BASE_REF=main` -> pass, findings vuoti;
  baseline `1003 -> 1004` file, `15432 -> 15435` callable e `4328 -> 4328`
  violation, scope/esclusioni invariati; `baseline-verify` -> pass.

## Failure preesistenti

| Data | Comando | Failure | Riproducibile | Relazione con il lavoro |
| --- | --- | --- | --- | --- |
| - | - | - | - | - |

## Blocker e domande aperte

- Revisionare e pubblicare i commit locali del workflow CI e del recupero
  Presenze; nessun push e stato eseguito.
- Dopo l'integrazione, osservare le prime PR per falsi positivi operativi.
- Calibrare soglie ed eccezioni solo su falsi positivi osservati, non prima.
- Il controllo semantico contro split/wrapper artificiali e lo spostamento
  neutro del debito resta una review obbligatoria degli aggregati; non viene
  sostituito da un euristico CI inaffidabile.
- La policy coverage resta invariata; un eventuale ratchet per righe legacy e
  una decisione separata.

## Prossima azione

Revisionare e integrare il recupero Presenze su `main`, poi applicare il ratchet
alle feature in corso senza avviare automaticamente hotspot applicativi.

## Functional maintenance - SISTER visure reliability and Profilo A (2026-08-20)

- Scope: worker visure, stato persistito `CatastoVisuraRequest`, documenti, migration e contratti API; nessun nuovo hotspot del programma Fase 3.
- Profilo richiesto: `idConv=1050380`, label completa `CONSORZIO DI BONIFICA DELL'ORISTANESE (CONSULTAZIONI - PROFILO A)`, verificati anche sull'HTML multi-convenzione fornito.
- Decisione doppio ruolo: nessun flag sulle credenziali; selezione dinamica ID+label nella sessione SISTER, probe fino all'area visure e comportamento fail-closed.
- Affidabilita: baseline remota obbligatoria, correlazione deterministica, polling/download/delete limitati alla riga correlata, stato remoto persistito, affinità credenziale dopo restart, errore esplicito se la credenziale proprietaria non e disponibile.
- Concorrenza/retry: `execution_token` come fencing, `retry_not_before` e `last_error_code` persistiti, backoff e massimo tentativi, reset coerente su cancel/release/retry.
- Documenti: path univoco per utente/batch/request/execution, download `.part`, firma `%PDF-`, rename atomico, SHA-256 e upsert idempotente del documento.
- Stati: `completed`, `not_found`, `failed` e `non_evadibile` distinti; i non evadibili correlati vengono eliminati prima del retry.

### Complexity evidence

- Slice comparabile prima: `6` file, `276` callable, `112` violation (`43` error, `69` warning).
- Slice comparabile dopo: `6` file, `307` callable, `92` violation (`29` error, `63` warning).
- `worker.py`: LOC `1534 -> 1194`, cognitive sum `678 -> 470`, cyclomatic sum `431 -> 308`, max cognitive `120 -> 119`, max cyclomatic `52 -> 51`.
- `browser_session.py`: max cognitive `44 -> 25`, max cyclomatic `19 -> 14`, density `0.737548 -> 0.663941`; LOC aumenta `1044 -> 1223` per le nuove garanzie browser/correlazione.
- `visura_flow.py`: max cognitive `121 -> 63`, max cyclomatic `50 -> 26`, cognitive sum `130 -> 107`, density `0.732558 -> 0.513736`.
- Nuovi moduli affidabilita: nessuna violation error-level; `sister_worker_reliability.py` resta a `790` LOC, sotto la soglia error file di `800`.
- Baseline delta: `NONE`; nessuna eccezione o esclusione aggiunta.

### Tests and gates

- Worker browser/flow: `92 passed`; repository/orchestrazione worker: `67 passed`; client worker aggiuntivi: `30 passed`; CAPTCHA Pillow isolato: `4 passed`.
- Coverage nucleo SISTER: `1092/1092` statement e `274/274` branch, `100%` sui sette moduli misurati.
- Backend elaborazioni API/integration: `47 passed`; tutte le righe introdotte in `elaborazioni_batches.py` sono esercitate, mentre il file completo conserva debito coverage legacy.
- `make lint-backend`: `PASS`; `npm run typecheck:from-root`: `PASS`; `make quality-test`: `22 passed`; `make complexity-check`: `PASS`; `git diff --check`: `PASS`.
- Alembic: singolo head `20260820_0900`; SQL offline del range upgrade/downgrade della nuova revisione: `PASS`.
- Limite test: i test worker restano eseguiti in processi separati perche `test_worker.py` installa stub globali in `sys.modules`; `test_captcha_solver.py` usa il Python di sistema con Pillow, mentre i test Playwright usano `backend/.venv`.
- Failure nuove: `NONE`; commit/push/PR: `NO`.

### Final review addendum

- Corretto un race residuo nell'attesa CAPTCHA manuale: ingresso e letture sono ora transazionali e verificano batch, stato richiesta ed `execution_token`; cancel/release prima o durante l'attesa restituiscono subito `skip` senza riattivare il claim.
- Nuovo componente delimitato: `sister_captcha_wait.py`, coperto al `100%` statement/branch; suite repository/worker aggiornata a `70 passed`.
- `make complexity-check`: `PASS`, findings vuoti dopo la riduzione della firma `_wait_for_manual_captcha`; nessuna eccezione o esclusione aggiunta.
- Baseline aggiornata con il comando ufficiale della CLI usando Python `3.11.15`, cioe lo stesso motore registrato nella baseline. Il tentativo con il Python `3.12.3` del target `make` e stato correttamente rifiutato come engine migration non autorizzata; `/home/cbo/.local/bin/python3.11 tools/code_quality/complexity.py baseline-verify` restituisce `true`.
- Delta baseline limitato a `backend/app/services/elaborazioni_batches.py`, runtime/test SISTER e nuovi helper SISTER; nessun file applicativo di altri domini e nessuna engine migration.
- Graphify finale: `make graphify-backend` `7186` nodi, `make graphify-frontend` `4904` nodi; dopo l'ultima modifica docs, `make graphify-docs` `1129` nodi, `1691` archi, `99` community.
- Limite coverage policy: i moduli estratti di affidabilita sono al `100%`, ma i file legacy runtime modificati non raggiungono ancora il `100%` full-file (`browser_session.py` `41%` e `worker.py` `35%` nelle suite mirate; `elaborazioni_batches.py` conserva debito legacy). La change non va dichiarata pienamente conforme alla policy coverage integrale finche questo debito non viene colmato o il perimetro non viene ridisegnato in una iterazione separata.

### Full-file coverage closure

- Il limite coverage precedente e superato: tutti i file runtime SISTER modificati sono ora al `100%` statement e branch, senza pragma, esclusioni, abbassamenti gate o refactoring runtime finalizzati alla metrica.
- Worker SISTER: `2857/2857` statement e `784/784` branch su `browser_session.py`, `worker.py`, `visura_flow.py`, `sister_exceptions.py`, `sister_selectors.py`, `sister_browser_reliability.py`, `sister_captcha_wait.py`, `sister_request_rows.py`, `sister_worker_files.py` e `sister_worker_reliability.py`.
- Backend SISTER: `1081/1081` statement e `216/216` branch su `app/models/catasto.py`, `app/schemas/catasto.py` e `app/services/elaborazioni_batches.py`.
- Suite worker isolate: browser/flow/helper `158 passed`; repository/orchestrazione `116 passed`. L'isolamento resta obbligatorio perche `test_worker.py` installa stub globali in `sys.modules`.
- Suite backend isolate: API `38 passed`, integrazione visure `9 passed`, nuovi test full-file `18 passed`; totale `65 passed`. Le coverage dei processi sono combinate soltanto dopo il completamento delle suite.
- Nuovi test di caratterizzazione: lifecycle/form/correlazione browser, dispatch/recovery/claim/fencing/retry/cooldown worker, validator Pydantic, fallback `StrEnum` Python 3.10, parsing upload, transizioni batch e metriche runtime.
- Complexity: firma del locator browser finto ridotta da `8` a `6` parametri; `/home/cbo/.local/bin/python3.11 tools/code_quality/complexity.py check` restituisce `findings: []`.
- Baseline aggiornata esclusivamente con il comando ufficiale Python `3.11`; `baseline-verify` restituisce `true`. Nessuna esclusione, eccezione o engine migration aggiunta.
- Snapshot complessita dopo i test: `1021` file, `15916` callable, `4134` violation (`2001` error, `2133` warning); nessuna nuova finding rispetto alla baseline aggiornata.
- Gate eseguiti: `make lint-backend` `PASS`; `make quality-test`: `22 passed`; `npm run typecheck:from-root`: `PASS`; `git diff --check`: `PASS`.
- Graphify: `make graphify-backend` `PASS`, nessuna variazione topologica; `make graphify-platform-docs` `PASS`, refresh incrementale del corpus completato.

## Functional maintenance - SISTER settings credential pool UI (2026-08-20)

- Scope: `/elaborazioni/settings`, presentazione del pool credenziali SISTER e orchestrazione frontend dei test; nessuna modifica API, DB, autenticazione, autorizzazione o selezione Profilo A.
- UI: la precedente tabella orizzontale e sostituita da card responsive con stato attivo/default, convenzione, codice richiesta, ufficio, ultima verifica e azioni contestuali.
- Bulk test: `Testa tutte` include credenziali attive e disattivate, ma esegue sempre una sola verifica per volta; ogni POST viene seguito dal polling fino allo stato terminale prima di passare all'account successivo.
- Resilienza: un errore o timeout resta associato al singolo account e non ferma gli altri; sono disponibili avanzamento, riepilogo, cancellazione e refresh finale del pool. Il worker continua a usare soltanto credenziali attive.
- Correzione: l'errore di un test singolo non viene piu cancellato da un refresh nel `finally`; il refresh immediato viene eseguito solo per credenziali persistite e risultati terminali.

### Complexity evidence

- Before, baseline `settings-workspace.tsx`: LOC `2106`, callable `132`, cyclomatic sum/max `783/386`, cognitive sum/max `835/467`, density `0.768281`.
- After, `settings-workspace.tsx`: LOC `1977`, callable `128`, cyclomatic sum/max `717/352`, cognitive sum/max `755/425`, density `0.744562`.
- Delta workspace: LOC `-129`, callable `-4`, cyclomatic sum/max `-66/-34`, cognitive sum/max `-80/-42`, density `-0.023719`.
- Nuovi runtime estratti: controller LOC `125`, view LOC `147`, facade LOC `45`, orchestratore puro LOC `146`, diagnostica LOC `32`; nessuna violation error-level e `8` warning non bloccanti complessivi.
- La prima bozza monolitica del pool aveva `5` violation error-level ed e stata scartata; la separazione finale mantiene controller, view e orchestrazione sotto le soglie error-level.
- `make complexity-check`: `PASS`, findings vuoti; snapshot globale `1026` file, `15962` callable, `4137` violation (`2000` error, `2137` warning).
- Baseline delta di questa slice: `NONE`; nessuna eccezione o esclusione aggiunta. `make complexity-baseline-verify` non e stato dichiarato verde: restituisce `false` sul checkout funzionale non assorbito nella baseline, che non e stata ampliata per registrare nuovo debito warning-level.

### Tests and gates

- Coverage mirata sui sei runtime frontend: `660/660` statement, `910/910` branch, `175/175` funzioni e `591/591` righe, tutte al `100%`; `69 passed`.
- `npm run typecheck:from-root`: `PASS`.
- `npm run lint`: `PASS` con soli warning preesistenti fuori dal perimetro Elaborazioni modificato.
- `make quality-test`: `22 passed`.
- `git diff --check`: `PASS`.
- Verifica HTTP: `GET http://gaia.lan/elaborazioni/settings` risponde `200`; validazione visuale browser non eseguita per assenza di una sessione Chrome DevTools disponibile.
- Graphify: `make graphify-frontend` `PASS` (`4904` nodi, `12233` archi); `make graphify-docs` `PASS` (`1134` nodi, `1708` archi); `make graphify-platform-docs` `PASS` (`821` nodi, `1529` archi).

## Functional maintenance - SISTER portal telemetry and DEMANIO R9 batch (2026-08-20)

- Telemetria completa distribuita su backend, frontend e worker: eventi strutturati SISTER, dashboard `/elaborazioni/portal-health`, retention eventi/artifact e rotazione log Docker.
- Alembic verificato con singolo head `20260820_1100`; backend e frontend healthy, worker visure stabile su Python `3.10.12`; la route protetta `GET /elaborazioni/portal-health` risponde `401` senza token.
- Compatibilita worker corretta sostituendo `datetime.UTC` con `timezone.utc` nei moduli retention e telemetry; import dei moduli verificato nel container Python 3.10.
- Safeguard login: `Credenziali SISTER rifiutate` e `Autenticazione fallita` sono errori recuperabili, quindi attivano differimento, cooldown e telemetria invece di fallire in sequenza tutte le richieste della batch.
- Retention iniziale completata nel solo perimetro debug/report consentito: `76358` file, `22951` directory e `4691290206` byte rimossi; purge eventi scaduti `0`.

### DEMANIO R9 deployment evidence

- Origine: `/home/cbo/Desktop/DEMANIO_R9.xlsx`, `3503` righe complete; rimossi `144` duplicati esatti.
- Template: `/home/cbo/Desktop/DEMANIO_R9_visure_template.xlsx`, SHA-256 `ab2db1d8eb296b6544e33dcc4047427b357ea3c6913bb349e9ac77a34043ac78`, `3359/3359` righe validate dal parser applicativo.
- Mapping creato: Marrubiu `2168`, Terralba sezione `A` `124`, Uras `1067`; catasto `Terreni`, tipo visura `Sintetica`.
- Batch server: `32f88227-962f-4751-9efe-2d5a6c178689`, nome `DEMANIO R9 - Visure terreni`, utente `admin`, `3359` richieste.
- Il collaudo live ha rilevato `Credenziali errate / Autenticazione fallita` sulla credenziale predefinita. La batch e stata rilasciata e normalizzata in stato resumibile: `cancelled`, `3359` richieste `skipped` con operazione di release, nessun fallimento catastale persistito.
- Condizione di ripresa: aggiornare e testare positivamente la password SISTER in `/elaborazioni/settings`, quindi riavviare la batch esistente; non crearne una nuova.

### Tests and gates

- Retention e telemetry: `215/215` statement e `36/36` branch, `100%`, `6 passed`.
- Worker e reliability: `1333/1333` statement e `364/364` branch, `100%`, `116 passed`.
- Test completi precedenti della slice: worker regressioni `122 passed`, browser/reliability `146 passed`, backend Elaborazioni `67 passed`, frontend telemetria/navigazione `19 passed` con runtime modificato al `100%`; typecheck frontend `PASS`.
- Baseline complexity: nessun aggiornamento eseguito in questa slice; le modifiche preesistenti al file baseline sono state preservate.
- `make complexity-check`: `PASS`, `findings: []`; snapshot `1039` file, `16133` callable, `4141` violation (`1999` error, `2142` warning). `git diff --check` e `docker compose config --quiet`: `PASS`.
- Graphify finale: backend `7219` nodi, `17418` archi e `423` community; frontend `4938` nodi, `12305` archi e `177` community; docs `1147` nodi, `1737` archi e `115` community.
- Verifica live finale: `GET /health` `200`, `GET /elaborazioni/portal-health` senza token `401`; `20` eventi della batch registrati, inclusi login error, logout e chiusura sessione.

### Revalidation 2026-08-21

- Backend telemetria/router/base: `280/280` statement e `30/30` branch, `100%`, `3 passed`.
- Worker osservabilita/retention/telemetry: `511/511` statement e `82/82` branch, `100%`, `23 passed`.
- Worker orchestrazione/reliability: `1333/1333` statement e `364/364` branch, `100%`, `116 passed`.
- Frontend Portal Health/navigazione: `170/170` statement, `179/179` branch, `58/58` funzioni e `141/141` righe, `100%`, `19 passed`.
- Regressioni: backend Elaborazioni `68 passed`; browser/flow worker `158 passed`; client/osservabilita worker `53 passed`; CAPTCHA Pillow isolato `4 passed`.
- Corretto il test backend dipendente dal giorno fisso: la finestra usa ora `datetime.now(UTC)` e verifica il totale dei bucket giornalieri senza assumere che le ultime sette ore cadano nello stesso giorno UTC.
- Gate: typecheck frontend, compile backend, `make quality-test` (`22 passed`), `make complexity-check` (`findings: []`), `git diff --check`, compose e Alembic head/current `20260820_1100`: `PASS`.
- Lint frontend: exit `0`, con soli warning legacy fuori dal perimetro Portal Health; nessun warning nuovo attribuito alla slice.
- Graphify: backend e frontend senza variazioni topologiche; domain docs `1151` nodi, `1756` archi e `109` community; refresh platform docs `PASS`.

## Hotspot Presenze - visibility router characterization (2026-08-25)

- Scope: singolo hotspot `backend/app/modules/presenze/router.py`; nessun secondo hotspot avviato. La policy estratta in `services/visibility_policy.py` conserva il dual-read tra Organigramma canonico e assegnazioni supervisore legacy.
- Invarianti: `admin`, `hr_manager` e `super_admin` vedono tutti i dati Presenze; dirigenti e capi leggono il proprio sottoalbero; approvazione gerarchica distinta dagli override `read`; route, payload, schema DB e transazioni Presenze invariati.
- Coverage router prima: `1603/1988` statement, `80,63%`. Dopo i test di caratterizzazione: `1988/1988`, `100%`, `0` righe mancanti e `0` esclusioni. La nuova policy di visibilita e a sua volta al `100%` (`56/56`, `0` mancanti).
- Coverage runtime completo Organigramma/Presenze: `3350/3350`, `100%`, `0` righe mancanti e `0` esclusioni sui `13` file modificati. Il conteggio include modelli, posizioni, repository, import/export, bozze, servizi di organigramma/visibilita, sync WhiteCompany, router e policy Presenze.
- Metriche prima, router: LOC `4668`, cognitive sum/max `1372/111`, cyclomatic sum/max `1156/64`, `1` violation file-level.
- Metriche dopo, aggregato router + policy: LOC `4670`, cognitive sum/max `1366/111`, cyclomatic sum/max `1157/64`, `1` violation file-level. Il debito non e ridotto in modo univoco e non viene classificato come miglioramento.
- Test: suite strumentata Organigramma/Presenze `PASS`; `pytest -q tests/organigramma tests/test_presenze_*.py` `PASS`; `compileall` e `git diff --check` `PASS`; `make quality-test` `34 passed` dopo l'aggiunta della regressione sul matching cross-file. `test_modified_runtime_coverage.py` caratterizza errori import, fallback bozze/dettagli, cicli di visibilita e rami di mapping WhiteCompany.
- Ratchet autorevole isolato: checkout temporaneo della base `8e2008d24bac2f19c9403416fb06681a34952161` con i soli runtime Presenze modificati; `make complexity-ratchet BASE_REF=8e2008d24bac2f19c9403416fb06681a34952161` `PASS`, `findings: []`.
- Ratchet globale: il falso rename di un file nuovo e stato corretto limitando il matching cross-file ai percorsi baseline realmente assenti. Il gate completo resta in exit `2` per una distinta `ambiguous_identity` nel file concorrente `frontend/src/app/gis/catalogo/page.tsx`, ampiamente riorganizzato; baseline globale non aggiornata.
- Esito: `REORGANIZED_AND_CHARACTERIZED`. Debito residuo: router legacy sopra soglia LOC; una futura riduzione richiede una nuova autorizzazione hotspot separata.

## Functional maintenance - GIS coordinates and overtime months (2026-08-21)

- Scope GIS: ricerca globale, parser coordinate e nuova route `/catasto/gis/coordinate`; la pagina `/catasto/gis` e `MapContainer` sono identici a `main`, senza modifiche API, DB o auth.
- Scope Straordinari: nuovo router periodico, selettore mese self-service e query dei mesi con extra effettivi positivi; endpoint legacy, template XLSX e mapping collaboratore invariati.
- Coverage backend: `34 passed`, `342/342` statement e `84/84` branch, `100%` su router API, router periodico e service export.
- Coverage frontend: Straordinari `106/106` statement e `74/74` branch; route/parser GIS `101/101` statement e `78/78` branch; search box `143/143` statement e `129/129` branch. Tutti i file runtime nuovi o modificati sono al `100%` anche per funzioni e righe.
- Regressione frontend: `149` file e `1447` test verdi. Typecheck globale: `149` diagnostiche legacy, stesso insieme di `main` dopo normalizzazione e nessuna nei file modificati.
- Regressione backend: suite globale con due failure preesistenti riprodotte su `main`, entrambe fixture SISTER incomplete in `test_coverage_small_runtime.py`; test della change verdi.
- Quality ratchet: `make quality-test` -> `33 passed`; `make complexity-ratchet BASE_REF=main` -> `PASS`, `findings: []`; baseline, eccezioni ed esclusioni non modificate.
- Build production: il primo `npm run build` ha rilevato l'export helper non ammesso dalla route Next; il builder overlay e stato spostato nel helper GIS senza variazioni funzionali. Build finale `PASS`, con `/catasto/gis/coordinate` e `/me/straordinari` generate.
- Verifica finale del fix GIS: `15 passed`; `101/101` statement, `78/78` branch, `23/23` funzioni e `83/83` righe, `100%`; regressione frontend completa confermata a `149` file e `1447` test verdi.
- Graphify: Presenze code `643` nodi e `1989` archi; Catasto code `871` nodi e `2097` archi; frontend finale `4521` nodi, `11051` archi e `185` community; refresh Catasto docs, Presenze docs e platform docs `PASS`.
- Verifiche residue: backend `compileall` `PASS`; `git diff --check` `PASS`.
