# SISTER: verifica finale del ciclo di sviluppo

## Scope e progress

- [x] Percorso rapido Espletate/Prelevate con fallback storico completo.
- [x] Riconoscimento checkbox idElemento e stato da categoria verificata.
- [x] Non evadibili checkbox-only fermate per revisione senza eliminazione.
- [x] Test unitari, DOM Playwright, persistenza SQLite e fencing del claim.
- [x] Coverage statement/branch dei tre file runtime al 100%.
- [x] Lint, complessita, build Docker ufficiale, import smoke senza rete.
- [x] Regression gate generale worker: import dei due test bloccanti corretti.
- [ ] Rilascio sul CED e misura dell'efficienza reale dopo il rilascio.
- [ ] Verifica sorgente del subalterno del canary prima di eventuali recuperi.

Il ciclo comprende soltanto i tre runtime sister_request_rows.py,
sister_requests_navigation.py e sister_exceptions.py, i test pertinenti e questa
documentazione. Le modifiche concorrenti Wiki, Presenze e Ruolo sono escluse.
Nessuna modifica a frontend, API pubbliche, schema DB, account o calendari.
Nessuna nuova dipendenza: dataclasses, datetime e zoneinfo sono standard library.
Il worker esistente rimane in modules/elaborazioni/worker; nessun servizio
parallelo o nuova superficie del monolite modulare.

## Matrice funzionalita / comportamento / test

I nomi dei test sono quelli in modules/elaborazioni/worker/tests/.

| Funzionalita | Comportamento verificato | Test |
| --- | --- | --- |
| Percorso rapido | Espletate/Prelevate prima dello storico, date solo se esposte | test_ready_fast_path_searches_both_categories_before_history; test_fast_path_uses_only_exposed_dates_and_ready_correlated_rows |
| Fallback | Categoria assente o PDF mancante non impediscono ricerca completa | test_non_evadibili_retains_full_search_when_fast_path_misses; test_search_dates_is_finite_and_deduplicated |
| Identita checkbox | Match univoco sull'ID remoto, senza link download | test_checkbox_identity_correlates_without_download_links |
| Input invalidi | Campo estraneo, prefisso, valore vuoto o ID parziale rifiutati | test_checkbox_identity_does_not_guess_from_unrelated_values |
| Identita ambigue | Nessun fallback verso una richiesta diversa; duplicati rifiutati | test_correlate_prefers_remote_id_and_rejects_duplicates; test_global_counters_do_not_skip_backlog_or_authorize_foreign_downloads |
| Stato categoria | Stato unknown inferito solo con radio checked noto e univoco | test_verified_ready_category_supplies_state_when_row_has_no_status; test_unverified_category_does_not_manufacture_state |
| Non evadibili | Errore terminale di revisione, nessun click, delete o defer | test_non_evadibile_checkbox_row_requires_review_without_delete_or_retry; test_checkbox_only_row_uses_verified_category_without_remote_actions; test_review_error_stops_request_without_defer_or_false_deletion |
| Error handling | Timeout propagati; filtro non applicato rifiutato | test_fast_path_does_not_swallow_filter_timeouts; test_unapplied_filter_fails_closed |
| Persistenza/concorrenza | Commit su claim attivo; claim obsoleto/batch cancellato non modificati; proprietario e identita remota preservati | test_non_evadibile_review_persists_only_active_claim |
| Diagnostica | Snapshot limitati; errori I/O non fermano il recupero | test_search_diagnostics_are_bounded_and_do_not_log_row_contents; test_search_diagnostics_io_error_does_not_interrupt_recovery |

## Test e coverage finali

148 test mirati superati: request_rows, requests_navigation,
checkbox_category_html, browser_session_correlation_coverage, reused_menu_html,
requests_navigation_html, review_persistence e visura_flow.

| Runtime | Statement | Branch | Mancanti |
| --- | --- | --- | --- |
| sister_request_rows.py | 126/126 | 46/46 | nessuno |
| sister_requests_navigation.py | 124/124 | 52/52 | nessuno |
| sister_exceptions.py | 18/18 | 0/0 | nessuno |

Nessuna nuova esclusione coverage. Il pragma preesistente sull'eccezione
SisterDocumentNotReadyError resta invariato. Coverage finale in
/tmp/sister-final-coverage.json; log /tmp/sister-final-focused-rerun.log.

Nuovi test: test_sister_checkbox_category_html.py e
test_sister_review_persistence.py. Modificati test_sister_request_rows.py,
test_sister_requests_navigation.py e test_sister_requests_navigation_html.py;
successivamente test_worker_reliability.py e test_worker_repository.py nella
slice di chiusura esplicitamente autorizzata dall'utente.
Il test DOM storico e stato aggiornato per il nuovo ordine di ricerca, mantenendo
le asserzioni su storico completo, assenza di download estranei e ID invariato.
La verifica finale restringe anche il riconoscimento del campo idElemento al
valore completo: non accetta il prefisso valido di un input malformato.

## Code quality e build

- Ruff sullo scope, formato dei due test nuovi, make lint-backend contro HEAD
  e git diff --check superati; il lint include la compilazione Python.
- Ratchet mirato contro merge-base origin/main senza finding, baseline immutata.
- extract_remote_id cog/cyc/LOC 13/7/14 invariato; nuovo helper categoria 4/5/20;
  fast path 3/3/10 e 7/7/23, orchestrazione 3/3/12, fallback storico 7/6/30.
- Nessun nuovo hotspot, dead code o duplicazione di servizi. Coupling resta sul
  callback esistente di correlazione. L'errore terminale e distinto da quello
  recuperabile: altrimenti avrebbe causato un nuovo cooldown e polling.
- Nessun download o cancellazione basati sui soli contatori globali. Diagnosi
  senza credenziali o contenuti personali nuovi nei log.
- Dockerfile ufficiale del worker costruito con contesto temporaneo senza env,
  venv, cache e graphify-out; immagine locale gaia-sister-final-verification:local.
- Import del worker e contratti verificati nel container con rete disabilitata;
  pip check senza dipendenze incompatibili. Warning pip root standard del
  Dockerfile preesistente, non errore della change.
- Type-check statico non configurato per questo worker: non e dichiarato eseguito.
  Test runtime e compilazione non sono presentati come type-check statico.
- Frontend test/build, API HTTP e autorizzazioni utente non applicabili: nessuna
  superficie modificata. Il fencing interno del worker e verificato su SQLite.
- Nessun E2E live sul portale: verificati DOM offline e persistenza SQLite,
  senza azioni su richieste reali. La migrazione storica e verificata anche
  su PostgreSQL 16 locale effimero nella riconferma finale sotto riportata.

## Regression gate e chiusura dei test bloccanti

La raccolta pytest aggregata dei test worker fallisce per contaminazione da
moduli stub/import wildcard. Il target make test-worker esegue ogni file in un
processo separato ed e il runner autorevole per questo modulo. La raccolta
aggregata non e dichiarata supportata o corretta da questa slice.

Le failure di test_worker_reliability.py (23 NameError) e la raccolta di
test_worker_repository.py (CatastoVisuraRequestStatus non definito) sono state
riprodotte anche su snapshot git archive HEAD, senza la change SISTER. Entrambi
i file erano invariati durante quella verifica. L'utente ha poi autorizzato
la slice di chiusura: sostituiti gli import wildcard con import espliciti,
pubblicata la fixture worker_db dal supporto esistente, importati status e
SisterCaptchaClaim mancanti. L'eccezione di correlazione proviene dal medesimo
supporto che inizializza il worker isolato, preservando l'identita della classe
usata dal coordinatore. Rimossa la raccolta duplicata dei test di test_worker.
Asserzioni applicative e codice runtime invariati. Ruff allinea import e UTC
e rinomina una variabile fixture inutilizzata, senza riformattazione massiva.

I due file ora superano rispettivamente 23 e 21 test. Il target make test-worker
completo termina con successo: 49 file, 677 test superati, incluse combinazione
coverage e generazione JSON/XML. Log finale /tmp/sister-slice-worker-full.log;
coverage completa /tmp/sister-slice-worker-coverage.json. Il perimetro runtime
modificato resta al 100%; il worker complessivo e al 99,85%, con cinque statement
legacy non coperti in file non modificati: sister_credential_pool.py alle linee
449, 450, 451, 523 e sister_retry_metadata.py alla linea 22. Non si dichiara
100% globale; nessuna esclusione nuova o indebolimento delle asserzioni.
Lint-backend, Ruff mirato e build Docker ufficiale rieseguiti e superati.
Le riproduzioni storiche baseline restano nei log
/tmp/sister-final-baseline-reliability.log e /tmp/sister-final-baseline-repository.log.

## Documentazione, Graphify e working tree

Documento tecnico aggiornato: SISTER_READY_SEARCH_2026-10-05.md. Questa pagina
consolida implementation plan, progress, matrice e validation report della slice.
PRD, README generale, API docs e programma code-quality non cambiano: nessun
nuovo requisito pubblico, programma o architettura. I residui sono marcati sopra.

Manutenzione Graphify tramite make graphify-elaborazioni-worker-code e
make graphify-elaborazioni-docs sullo stato finale. Evidenze nei log
/tmp/sister-final-graph-code.log e /tmp/sister-final-graph-docs.log:
la verifica docs richiede chunk completati e assenza di warning semantici,
non soltanto exit code. Nessun grafo committato.

Working tree con modifiche concorrenti preesistenti preservate. Nuovi test e
documenti della slice restano non tracciati; nessun commit, push o branch nuovo.
Log, coverage e contesti di verifica sotto /tmp, immagine soltanto locale;
nessun file di credenziali/configurazione modificato e nessun rilascio produttivo.

## Residui e decisione

La divergenza canary subalterno A in richiesta/item/ruolo contro null nel catasto
canonico resta da verificare: non dimostra da sola la causa del rifiuto. Nessun
dato normalizzato per supposizione. Recupero massivo subordinato al PDF verificato.
Il nuovo percorso rapido puo aggiungere costo ai poll negativi; il guadagno
prestazionale non e ancora misurato sul CED. Gli stati remoti storici vengono
preservati: una richiesta fermata per revisione non viene falsamente marcata deleted.

## Riconferma finale del 2026-10-05

Verifica rieseguita sullo scope SISTER con HEAD
bfc8e68fd6d4acf373b23b7cc15693c80bd75f18 e modifiche locali preservate.
Nessuna nuova funzionalita o modifica runtime introdotta nella riconferma.

- make test-worker: exit 0, 677 test superati in 49 file; log
  /tmp/sister-close-worker.log e report /tmp/sister-close-worker-coverage.json.
- Il runner senza GAIA_TEST_POSTGRES_URL salta una variante PostgreSQL della
  migrazione storica, non modificata. Eseguita poi separatamente con database
  PostgreSQL 16 effimero: entrambe le varianti SQLite/PostgreSQL superate,
  2 test, nessuno skip; /tmp/sister-close-postgres-final.log. Primo tentativo
  con URL psycopg2 fallito per driver assente; corretto l'URL temporaneo a
  psycopg, gia previsto da requirements.txt. Nessuna dipendenza aggiunta.
- Statement/branch di tutti e tre i runtime modificati riconfermati al 100%.
  Totale worker: 5835/5840 statement (99,9144%), 1554/1560 branch (99,6154%);
  combinato 99,8514%. Non si dichiara coverage globale al 100%.
- Gap legacy: sister_credential_pool.py linee 449-451 (caricamento credenziali
  configurate), 523 (notifica di espansione durante runner attivi), branch
  105->107, 448->449, 450->448, 450->451, 522->523;
  sister_retry_metadata.py linea 22 e branch 21->22 (clear_baseline=True).
  Sono casi reali che meritano test nel backlog coverage globale, non codice
  introdotto dalla slice. Nessuna esclusione aggiunta per nasconderli.
- Warning preesistenti del runner: runpy nel test dello script efficienza e
  no-data-collected nella migrazione, che non importa runtime worker. Non
  compromettono la coverage combinata dei file modificati.
- Ruff su runtime/test SISTER, formato dei due nuovi test, make lint-backend
  e git diff --check superati; /tmp/sister-close-lint.log.
- Ratchet read-only sui tre runtime contro merge-base origin/main: exit 0,
  findings vuoto, baseline invariata; /tmp/sister-close-ratchet.json.
- Build Dockerfile ufficiale sul contesto temporaneo sanificato riconfermata:
  /tmp/sister-close-build.log. Import worker e contratti SISTER nel container
  senza rete superati; pip check senza incompatibilita.
- Graphify codice riconfermato tramite target modulo con force pruning:
  /tmp/sister-close-graph-code.log; nessuna variazione topologica rispetto al
  grafo gia aggiornato. Documentazione aggiornata tramite target dominio:
  /tmp/sister-close-graph-docs.log; completamento semantico chunk 1/1
  verificato, nessun warning di estrazione parziale.
- Frontend, API pubbliche, schema e autorizzazioni utente invariati: relativi
  gate non applicabili alla slice. Nessun type-check statico worker configurato.
  La prova offline non certifica disponibilita, tempi o HTML attuale del CED;
  rollout e misura operativa rimangono attivita separate, non completate.
- Working tree: preservate le modifiche concorrenti Wiki/Presenze/Ruolo e
  code-quality; nessun artefatto temporaneo aggiunto al repository, nessuna
  configurazione o credenziale modificata, nessun commit o deploy.

FINAL QUALITY GATE — PASS

Gate riferito alla slice di sviluppo e al runner worker autorevole. Restano
fuori scope copertura globale legacy, raccolta pytest aggregata, rollout CED,
E2E live e verifica del dato canonico del canary.
