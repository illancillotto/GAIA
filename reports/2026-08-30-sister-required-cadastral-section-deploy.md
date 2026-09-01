# GAIA — recovery sezione catastale SISTER con flusso batch autorevole

**Data:** 2026-08-30/31  
**Repository:** `/home/cbo/CursorProjects/GAIA`  
**CED:** `/opt/gaia` via `serverCed`  
**Stato report:** chiuso — deploy verificato; percorso positivo non esercitabile sui casi reali disponibili

## Obiettivo

Correggere il caso in cui SISTER rifiuta una ricerca per immobile con il messaggio `La sezione è obbligatoria per il comune specificato.`, senza duplicare o alterare la logica batch già validata per comune, foglio e particella.

## Analisi rispetto al batch esistente

Il percorso autorevole resta `BrowserSession.fill_visura_form`:

1. compila catasto, comune, eventuale sezione esplicita, foglio, particella e subalterno;
2. invia il form;
3. esegue integralmente `BrowserSession._wait_for_visura_submission_state`;
4. conserva classificazione, server error, not-found, CAPTCHA, download e selezione tipo visura esistenti.

La prima versione della recovery controllava il marker della sezione prima che il wait batch avesse concluso l'attesa. Un test differenziale ha dimostrato il rischio di race e l'inversione della gerarchia. La versione finale:

1. chiama prima il metodo batch originale;
2. intercetta esclusivamente l'errore con prefisso esatto `Submit visura non avanzato per richiesta <id>:`;
3. verifica il marker esplicito della sezione obbligatoria;
4. carica le opzioni tramite `_ensure_sezione_options_loaded`, già presente nel batch;
5. seleziona soltanto se il DOM contiene esattamente un elemento `<option>` valido e non vuoto;
6. considera opzioni duplicate come opzioni multiple e quindi non selezionabili automaticamente;
7. ripete una sola volta il click `Visura`;
8. rientra nello stesso metodo batch originale.

Qualsiasi altro errore viene ripropagato senza modifiche. Con zero o più sezioni valide non viene effettuata alcuna scelta. Un errore Playwright durante l'ispezione conserva l'errore batch originale e collega l'errore DOM come causa diagnostica.

La sottoclasse recovery test-only è stata rimossa: resta un solo meccanismo, l'installer idempotente usato in produzione. Questo elimina la possibilità futura di doppio wrapping e doppio resubmit.

I file legacy autorevoli `browser_session.py`, `worker.py` e i relativi test storici non hanno delta rispetto a `HEAD` per questo fix.

## Review indipendente

Una code review read-only indipendente ha confermato che il flusso batch resta al comando e non ha rilevato finding bloccanti. Ha segnalato tre hardening, tutti recepiti:

- opzioni duplicate non devono diventare univoche tramite deduplicazione;
- rimozione della sottoclasse per evitare doppio wrapping futuro;
- conservazione dell'errore batch quando l'ispezione DOM fallisce.

## File runtime

- Nuovo: `modules/elaborazioni/worker/sister_cadastral_browser_session.py`
- Wiring: `modules/elaborazioni/worker/sister_worker_reliability.py`
- Planner: `backend/app/services/elaborazioni_perpetual_sync.py`
- Test worker: `modules/elaborazioni/worker/tests/test_sister_cadastral_browser_session.py`
- Test backend: `backend/tests/test_elaborazioni_api.py`
- Docs: `domain-docs/elaborazioni/docs/CATASTO_CONTINUOUS_SYNC.md`

## TDD recovery

Sono stati osservati RED reali per:

- wait batch eseguito prima della recovery;
- errore batch autorevole diverso da `submit non avanzato` non mascherabile;
- due opzioni duplicate erroneamente accettate come univoche;
- errore DOM che sostituiva l'errore batch.

La suite specifica finale contiene **14 test PASS**, inclusi:

- race primo submit / marker disponibile soltanto dopo il wait;
- unica sezione valida;
- opzioni duplicate rifiutate;
- più sezioni rifiutate;
- zero sezioni rifiutate;
- submit normale invariato;
- errore `submit non avanzato` senza marker preservato;
- errore server/altro con marker preservato;
- errori lettura marker/opzioni preservano l'errore batch;
- seconda attesa fallita: un solo resubmit;
- wiring dal reliability;
- installer idempotente;
- installer no-op senza metodo target.

## Correzione deadline retry AutoSync

La verifica live ha individuato un difetto separato: `_retry_item` ricalcolava `retry_after = now + delay` a ogni riconciliazione di una richiesta già fallita. La deadline scorreva in avanti e il retry naturale poteva non diventare mai dovuto.

È stato osservato un test RED che esegue due riconciliazioni e pretende una deadline invariata. Il fix minimo preserva `retry_after` quando l'item è già `pending` e possiede una deadline. Il backoff viene quindi calcolato una sola volta.

Verifica backend:

- `backend/tests/test_elaborazioni_api.py`: **76 PASS**;
- `elaborazioni_perpetual_sync.py`: 268 statement, 0 mancanti, **100%**;
- complexity ratchet: PASS, `findings: []`.

## Worker test e quality gate

`make test-worker` finale:

- 30 file di test: PASS;
- `sister_cadastral_browser_session.py`: 48 statement, 10 branch, 0 mancanti, **100%**;
- totale worker: 5.139 statement, 1.326 branch, 0 mancanti, **100%**.

Ulteriori gate:

- `compileall`: PASS;
- `git diff --check`: PASS;
- assenza di delta nei file legacy batch: PASS;
- complexity ratchet su `HEAD`: PASS, `findings: []`.

## Documentazione e Graphify

- `CATASTO_CONTINUOUS_SYNC.md` aggiornato con precedenza batch, singolo elemento `<option>`, fail-closed e deadline stabile.
- Graphify backend: **7.795 nodi, 19.678 archi, 441 comunità**.
- Graphify docs finale: **1.413 nodi, 2.431 archi, 122 comunità**.

## Deploy CED

### Backup

1. Worker iniziale:
   `/opt/gaia/backups/hotfixes/2026-08-30-sister-required-section-batch-authoritative/`
2. Backend deadline retry:
   `/opt/gaia/backups/hotfixes/2026-08-30-autosync-stable-retry-deadline/`
3. Hardening post-review:
   `/opt/gaia/backups/hotfixes/2026-08-30-sister-section-review-hardening/`

### File live finali

- `sister_cadastral_browser_session.py` — SHA-256 `b9da22b16b427dac3227a816aa8690fc51b633c79069e320029a7f3773c401eb`;
- `sister_worker_reliability.py` — SHA-256 `c9350a0a11037d724aed0b2fd0a1a5ab9d8d84e41e5171e53c42738c20fca0c5`;
- `elaborazioni_perpetual_sync.py` — SHA-256 `fab2f8c27e0cedf744dfa448a37742bacd59d5676bd661b103d70c8b5bf3c7ee`.

Compilazione nei container prima del restart: PASS.

Sono stati riavviati soltanto:

- `backend`;
- `elaborazioni-worker-visure`.

Post-restart:

- backend: healthy, restart count 0, `/health` HTTP 200;
- worker: running, restart count 0;
- recovery installata nel processo: sì;
- traceback/import error: 0;
- frontend non riavviato.

Una richiesta ordinaria Solarussa ripresa dopo il primo restart è terminata `completed` con PDF scaricato, confermando la non regressione del flusso normale.

## Verifica live Arborea

### Deadline retry

La deadline iniziale controllata era:

`2026-08-30 22:24:27.837934+00`

È rimasta invariata durante più cicli planner ed è diventata regolarmente dovuta. Questo dimostra live che la correzione backend non sposta più continuamente `retry_after`.

### Caso ambiguo: fail-closed verificato

È stata elaborata una nuova richiesta reale per Arborea, foglio 23, particella 1495. Il DOM finale conteneva due opzioni valide:

- `A — MARRUBIU`;
- `B — SANTA GIUSTA`.

Il worker non ha scelto alcuna sezione, non ha eseguito il secondo submit e ha preservato l'errore batch originale. La richiesta è terminata `failed`; worker `running`, restart count 0. Questo è il comportamento fail-closed atteso e valida anche l'hardening post-review sulle opzioni multiple.

### Secondo caso controllato e correzione della diagnosi iniziale

È stato rieseguito il caso Arborea, foglio 12, particella 10, inizialmente ritenuto univoco perché la prima ispezione aveva letto soltanto la prima option `A — MARRUBIU`. Prima dello smoke è stata salvata la riga completa dell'item con permessi 0600 in:

`/opt/gaia/backups/hotfixes/2026-08-30-sister-section-review-hardening/arborea-single-section-item-before-smoke.txt`

È stato anticipato esclusivamente `next_due_at` del singolo item, lasciando invariati stato, `attempt_count=1`, `retry_after` e collegamento precedente. Nessuna campagna o insieme di fallimenti è stato riaccodato.

La nuova richiesta reale è stata correlata ed elaborata. Il DOM completo del `select[name="sezione"]` ha mostrato tre option valide:

- `A — MARRUBIU`;
- `B — SANTA GIUSTA`;
- `C — TERRALBA`.

Anche questo caso era quindi ambiguo. Il worker ha correttamente evitato selezione e resubmit, ha preservato l'errore batch originale ed è rimasto `running` con restart count 0.

### Disponibilità di un caso positivo

È stata eseguita una scansione read-only di tutti gli artefatti `final-failed.html` presenti nel volume worker, limitata alle pagine contenenti il messaggio di sezione obbligatoria e contando esclusivamente le option non vuote del `select[name="sezione"]`:

- pagine analizzate: **602**;
- esattamente una option valida: **0**;
- più option valide: **602**;
- zero option valide: **0**.

Non esiste quindi, negli artefatti reali oggi disponibili sul CED, un caso che soddisfi la precondizione per la selezione automatica. Il ramo positivo resta provato automaticamente al 100% da test statement/branch, ma non può essere dichiarato esercitato sul portale reale senza inventare o forzare una sezione, operazione vietata dal guardrail. La verifica live dimostra invece in modo ripetibile il comportamento fail-closed sui casi reali disponibili.

### Controllo runtime conclusivo

- backend `/health`: HTTP 200, container healthy, restart count 0;
- frontend `/elaborazioni/autosync`: HTTP 200, container healthy, restart count 0;
- worker Visure: running, restart count 0;
- richiesta controllata: `failed`, nessun `document_id`, errore batch originale preservato;
- item AutoSync: tornato `pending` con `attempt_count=1` e nuova deadline ordinaria `2026-08-30 23:10:48.755885+00`;
- il `next_due_at=1970` usato per lo smoke non è rimasto persistito: la riconciliazione lo ha sostituito con la normale deadline di backoff;
- nessun processo di monitoraggio ancora attivo;
- `git diff --check`: PASS.

Un nuovo batch permanente era regolarmente `processing` al controllo finale; questo conferma la prosecuzione del planner e non costituisce un blocco dello smoke concluso.

## Stato Git

- branch locale: `main`, avanti rispetto a `origin/main` per modifiche già presenti nel workspace;
- working tree condiviso e sporco: preservate tutte le modifiche concorrenti;
- nessun commit o push eseguito.
