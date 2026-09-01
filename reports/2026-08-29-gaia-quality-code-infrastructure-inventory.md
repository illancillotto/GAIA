# Inventario dell’imbracatura Quality Code di GAIA

**Data:** 2026-08-29

**Repository:** `/home/cbo/CursorProjects/GAIA`

**Branch verificato:** `main`

**HEAD verificato:** `6207624abad738e683bb3cb9310d68dd3f30ff76`

**Tracking:** `main...origin/main [avanti 28]`

**Stato inventario:** COMPLETO CON ATTENZIONE — harness testato, baseline corrente non riproducibile sul checkout attuale

## 1. Sintesi

L’imbracatura GAIA non è un singolo tool. È composta da sei livelli:

1. **governance e regole di repository**;
2. **scanner AST di complessità e quality ratchet**;
3. **baseline, eccezioni, report e backlog hotspot**;
4. **coverage differenziale al 100% per backend, frontend e worker**;
5. **test, lint, typecheck, build e CI GitHub Actions**;
6. **skill operative, Graphify e harness di deploy/smoke**.

La suite specifica del quality tooling è stata rieseguita durante questo inventario:

```text
make quality-test QUALITY_PYTHON=.venv/bin/python
46 passed in 8.61s
exit code 0
```

Le eccezioni sono valide e attualmente vuote:

```text
.venv/bin/python tools/code_quality/complexity.py validate-exceptions
{"errors": []}
exit code 0
```

La baseline versionata è schema `2` e contiene:

- `1.004` file;
- `15.435` callable;
- `4.328` violation;
- `2.122` error;
- `2.206` warning;
- engine Python `python-ast`;
- engine JavaScript/TypeScript `babel-parser-ast`.

Attenzione: sul checkout corrente il comando

```text
.venv/bin/python tools/code_quality/complexity.py baseline-verify
```

restituisce:

```json
{"baseline_reproducible_ignoring_timestamp_commit": false}
```

con exit code `1`. La baseline versionata ha `source_commit=b1d4a988e3a8bd987f463cb62614592740be7595`, mentre il checkout verificato è a `6207624...` e contiene numerose modifiche runtime non committate. Quindi l’harness esiste ed è coperto dai propri test, ma **il gate complessivo non deve essere dichiarato interamente verde sullo stato corrente**.

---

## 2. Governance e responsabilità

### 2.1 Regole autorevoli del repository

#### `AGENTS.md`

Responsabilità:

- rende obbligatoria la coverage al `100%` dei file runtime nuovi o modificati;
- impone il quality ratchet per modifiche sotto:
  - `backend/app`;
  - `frontend/src`;
  - `modules/elaborazioni/worker`;
- vieta regressioni di complessità nel perimetro toccato;
- impone il confronto con la baseline del merge-base;
- vieta aggiornamenti baseline usati per assorbire regressioni;
- vieta esclusioni larghe, wrapper artificiali e spostamento del debito;
- richiede di preservare modifiche non correlate;
- richiede Graphify quando cambia struttura o documentazione;
- vieta commit, push, PR e merge senza richiesta esplicita.

#### `docs/AGENTS.md`

Responsabilità:

- governa la documentazione tecnica;
- richiede aggiornamento di `docs/TEST_COVERAGE_100_PLAN.md` quando cambia la policy coverage;
- disciplina gli aggiornamenti Graphify della documentazione.

### 2.2 Documenti normativi quality

Directory: `docs/code-quality/`

| File | Responsabilità |
|---|---|
| `README.md` | indice del programma, comandi e principi non negoziabili |
| `QUALITY_RATCHET.md` | decisione di usare il ratchet come modalità ordinaria e rollout a fasi |
| `METRICS_AND_BASELINE.md` | metriche, soglie, schema baseline, matching, eccezioni e anti-laundering |
| `VALIDATION.md` | matrice dei gate, definition of done e classificazione delle failure |
| `PROGRESS.md` | fonte di verità persistente, checkpoint, iterazioni e metriche prima/dopo |
| `HOTSPOTS.md` | backlog evidence-based degli hotspot; non è una coda automatica |
| `PLAN.md` | fasi, checkpoint e dipendenze del programma |
| `PROMPT.md` | brief tecnico della fondazione |
| `INSTRUCTIONS.md` | regole operative e stop condition |
| `HERMES_GOAL_PHASE_1.md` | goal Hermes per audit/tooling/baseline |
| `HERMES_GOAL_REFACTOR_ONE_HOTSPOT.md` | goal per una sola slice di refactoring |
| `HERMES_LOOP_MONITORING.md` | monitoraggio opzionale, non esecuzione di refactoring a timer |
| `AGENTS_ADDENDUM.md` | copia di riferimento delle regole già integrate in `AGENTS.md` |

### 2.3 Policy coverage

#### `docs/TEST_COVERAGE_100_PLAN.md`

Responsabilità:

- definisce l’obiettivo di piattaforma del `100%` sul runtime versionato;
- mantiene come gate immediato il `100%` per ogni file runtime modificato;
- vieta compensazioni tramite media globale;
- distingue obiettivo repository-wide e gate changed-file già attivi;
- mantiene il debito legacy visibile fino alla convergenza totale;
- registra verifiche e comandi affidabili per i singoli domini.

Perimetro dichiarato:

- `backend/app/**`;
- `frontend/src/**`;
- `modules/elaborazioni/worker/**`;
- script runtime versionati coinvolti nei flussi operativi.

---

## 3. Scanner AST e quality ratchet

### 3.1 Motore principale

#### `tools/code_quality/complexity.py`

È il cuore dell’harness. Responsabilità:

- scansione Python tramite AST nativo;
- orchestrazione della scansione JS/TS/JSX/TSX;
- normalizzazione delle metriche di callable e file;
- calcolo delle violation warning/error;
- generazione report JSON e Markdown;
- lettura/scrittura baseline schema `2`;
- matching per path, qualified name, rename Git e fingerprint AST;
- rilevazione di identità ambigue;
- confronto differenziale con merge-base;
- blocco delle regressioni legacy;
- blocco delle nuove violation error-level;
- verifica delle eccezioni;
- protezione delle migrazioni del motore metriche;
- blocco del debt laundering tramite baseline, rename, wrapper o ampliamento scope.

CLI verificata:

```text
report
check
changed
ratchet
baseline
baseline-verify
validate-exceptions
```

Contratto exit code:

- `0`: controllo superato;
- `1`: regressione o violation rilevata;
- `2`: errore di configurazione/integrità, merge-base mancante o identità ambigua.

Perimetro scanner:

```text
backend/app/**/*.py
frontend/src/**/*.js
frontend/src/**/*.jsx
frontend/src/**/*.ts
frontend/src/**/*.tsx
modules/elaborazioni/worker/**/*.py
```

Esclusioni tecniche strette:

- cache Python/pytest/ruff;
- `.next`, `node_modules`;
- output coverage/htmlcov/graphify;
- migration Alembic;
- file minificati, `.d.ts`, fixture e snapshot.

### 3.2 Parser JavaScript/TypeScript

#### `tools/code_quality/js_ast_metrics.mjs`

Responsabilità:

- parsing reale con `@babel/parser`, non regex/token scanning;
- supporto TypeScript, JSX, decorator, class properties, optional chaining, dynamic import e top-level await;
- estrazione di function, method, arrow function, callback e React component;
- identità strutturale delle callback anonime tramite owner, callee e indice argomento;
- fingerprint SHA-256 strutturale;
- metriche cyclomatic, cognitive, nesting, effective LOC e parametri;
- metriche file per import, LOC, `useState`, `useEffect` e `useReducer`;
- exit code `2` se manca il parser o il file non è parsabile.

### 3.3 Soglie callable

| Metrica | Warning | Error |
|---|---:|---:|
| Cyclomatic complexity | 10 | 15 |
| Cognitive complexity | 15 | 25 |
| Effective LOC | 50 | 80 |
| Nesting | 4 | 5 |
| Parametri | 5 | 7 |

### 3.4 Soglie file/componente

| Metrica | Warning | Error |
|---|---:|---:|
| Effective file LOC | 500 | 800 |
| `useState` | 10 | 20 |
| `useEffect` | 5 | 8 |

### 3.5 Regole del ratchet

- codice nuovo warning-level: visibile, non bloccante;
- codice nuovo error-level: gate fallisce;
- legacy invariato: può restare baselined;
- legacy modificato: nessuna metrica primaria può peggiorare;
- nessuna nuova violation, anche se un massimo di file diminuisce;
- debito aggregato del perimetro toccato non può aumentare;
- il confronto autorevole usa la baseline al merge-base;
- una baseline modificata nella stessa change non autorizza la change;
- matching ambiguo: exit `2`, mai scelta silenziosa;
- cross-path fingerprint matching solo se la sorgente originaria non esiste più;
- migrazione engine esplicita non può autorizzare regressioni o nuove esclusioni.

---

## 4. Baseline, eccezioni e report

### 4.1 Baseline

#### `config/code-quality/complexity-baseline.json`

Responsabilità:

- fotografia versionata del debito legacy;
- provenance, commit sorgente, engine e scope;
- identità strutturale e metriche dei callable;
- metriche aggregate di file;
- violation attive.

Stato verificato:

- schema: `2`;
- source commit: `b1d4a988e3a8bd987f463cb62614592740be7595`;
- file: `1.004`;
- callable: `15.435`;
- violation: `4.328`;
- error: `2.122`;
- warning: `2.206`.

### 4.2 Eccezioni

#### `config/code-quality/complexity-exceptions.json`

Stato corrente:

```json
{
  "schema_version": 1,
  "exceptions": []
}
```

Le eccezioni, quando necessarie, devono avere path/pattern stretto, metrica, motivazione, owner, data e scadenza. Sono vietati wildcard di intere directory runtime e ignore permanenti di codice imperativo.

### 4.3 Report versionati

- `reports/code-quality/complexity-report.json` — output machine-readable;
- `reports/code-quality/complexity-report.md` — top hotspot e riepilogo umano.

Per verifiche read-only è preferibile sovrascrivere i default con output sotto `/tmp`.

---

## 5. Test dell’harness

Directory: `tests/code_quality/`

### 5.1 `test_complexity_tool.py`

Copre:

- codice nuovo sotto/sopra soglia;
- soglia LOC file;
- legacy invariato, migliorato e peggiorato;
- debito file-level;
- Python async/nested/match;
- TSX, arrow, callback, componenti e hook;
- eccezioni valide/scadute/troppo larghe;
- baseline mancante o corrotta;
- baseline update che tenta di assorbire regressioni;
- regressione coordinata source + baseline;
- file cancellati e rename;
- riuso fingerprint non interpretabile come rename;
- identità ambigua;
- merge-base non disponibile;
- migrazione engine valida e non valida;
- regressioni/esclusioni durante engine migration;
- cancellazione manuale di entry baseline.

### 5.2 `test_complexity_js_identity.py`

Copre:

- stabilità delle callback anonime dopo line shift;
- regressione legacy delle callback;
- callback indistinguibili con exit `2`;
- sibling identity reservation;
- callback aggiunte parzialmente o integralmente;
- nuove violation nelle callback ambigue;
- parsing degli hunk aggiunti;
- debt laundering tramite wrapper o rename.

### 5.3 `test_complexity_baseline_reproducibility.py`

Copre:

- normalizzazione di timestamp/commit/provenance;
- rilevazione di veri cambi sorgente dopo la normalizzazione.

### 5.4 `test_worker_coverage_gate.py`

Copre:

- scope dei runtime worker;
- risoluzione delle chiavi coverage;
- parsing argomenti e diff Git;
- percentuali invalide;
- nessun file runtime modificato;
- file mancanti o sotto soglia;
- tutti i file al 100%;
- esecuzione dello script come entrypoint.

**Totale verificato:** `46 passed`.

---

## 6. Coverage differenziale al 100%

### 6.1 Backend

#### `scripts/check_changed_backend_coverage.py`

Responsabilità:

- ricava i file da `git diff BASE...HEAD`;
- considera runtime Python sotto `backend/app` esclusi `__init__.py`;
- legge il JSON di `coverage.py`;
- fallisce se un file modificato manca dal report o è sotto `100%`.

### 6.2 Frontend

#### `scripts/check_changed_frontend_coverage.py`

Responsabilità:

- considera `.ts/.tsx/.js/.jsx` sotto `frontend/src`;
- esclude `src/types`, `.d.ts` e test;
- legge `coverage-final.json` V8/Istanbul;
- applica il minimo `100%` per file modificato.

#### `frontend/vitest.config.ts`

Responsabilità:

- usa ambiente `jsdom` e setup condiviso;
- calcola il perimetro coverage da `VITEST_COVERAGE_INCLUDE` oppure dal diff contro `VITEST_COVERAGE_BASE_REF`/`origin/main`;
- applica `100%` a linee, funzioni, statement e branch quando esistono file runtime modificati;
- produce report text, JSON, HTML e Cobertura.

### 6.3 Worker

#### `scripts/check_changed_worker_coverage.py`

Responsabilità:

- considera i runtime Python sotto `modules/elaborazioni/worker`;
- esclude test e `__init__.py`;
- legge il JSON combinato statement+branch;
- fallisce per report mancante o file sotto `100%`.

#### Target `make test-worker`

Responsabilità:

- esegue i file `test_*.py` worker in processi isolati;
- evita contaminazione fra stub globali;
- combina i dati coverage;
- produce:
  - `backend/coverage-worker.json`;
  - `backend/coverage-worker.xml`.

### 6.4 Configurazione backend

- `backend/pytest.ini` — discovery, output breve e marker `postgres`;
- `backend/.coveragerc` — source, omit test/cache/init, report missing e path normalization.

Nota: la `.coveragerc` non impone da sola `fail_under=100`; il requisito changed-file è applicato dagli script CI.

---

## 7. Makefile: superficie operativa

### Quality e complexity

```text
make quality-test
make complexity-report
make complexity-check
make complexity-changed BASE_REF=...
make complexity-ratchet BASE_REF=...
make complexity-baseline
make complexity-baseline-verify
make complexity-ci-gate BASE_REF=...
```

Responsabilità:

- `quality-test`: tutta `tests/code_quality`, senza lista manuale parziale;
- `report`: JSON + Markdown;
- `check`: confronto con baseline del working tree;
- `changed`: analisi differenziale dei file cambiati;
- `ratchet`: confronto autorevole con baseline al merge-base;
- `baseline`: aggiornamento esplicito e protetto;
- `baseline-verify`: riproducibilità;
- `ci-gate`: sequenza CI completa.

### Test/lint/build

```text
make lint
make lint-backend
make lint-frontend
make test
make test-worker
make test-ruolo-postgres
make test-presenze-postgres
make test-wiki
make coverage-wiki
```

- `lint-backend` usa `compileall` su backend, test e worker;
- `lint-frontend` richiama il lint Next;
- i test PostgreSQL hanno marker e database reale isolato;
- il worker ha runner coverage dedicato.

### Graphify / impact analysis

I target `graphify-*-code`, `graphify-*-docs`, `graphify-frontend`, `graphify-backend` e `graphify-platform-docs` mantengono il grafo di conoscenza di codice e documentazione.

Graphify non è un gate di complessità, ma fa parte dell’imbracatura di manutenzione perché supporta orientamento, impact analysis e aggiornamento della conoscenza dopo cambi strutturali.

---

## 8. CI GitHub Actions

### 8.1 `.github/workflows/code-quality.yml`

Workflow autorevole del quality ratchet.

Caratteristiche:

- trigger su runtime e infrastruttura quality;
- checkout `fetch-depth: 0`;
- Python `3.11`;
- Node `20`;
- installazione `pytest` e dependency graph frontend;
- `make quality-test`;
- `scripts/complexity_ci_gate.sh` con SHA base della PR o commit precedente del push.

### 8.2 `scripts/complexity_ci_gate.sh`

Sequenza:

1. determina `BASE_REF`;
2. verifica/fetch base branch;
3. calcola merge-base;
4. genera report in `/tmp`;
5. esegue `ratchet` contro merge-base;
6. esegue `check`;
7. esegue `baseline-verify`;
8. esegue `validate-exceptions`;
9. pubblica un GitHub step summary.

Fallisce con exit `2` se il merge-base non è disponibile.

### 8.3 `.github/workflows/backend.yml`

Gate:

- PostgreSQL 16 reale come service container;
- dependency guard tra backend e worker;
- syntax check `compileall`;
- suite pytest con coverage JSON/XML;
- upload artifact coverage backend;
- changed-file backend coverage `100%`;
- test worker isolati con coverage;
- upload artifact worker;
- changed-file worker coverage `100%`.

### 8.4 `.github/workflows/frontend.yml`

Gate:

- Node `20`;
- install dipendenze;
- lint;
- typecheck runtime;
- smoke test Node;
- Vitest unit con coverage;
- artifact JSON/Cobertura/HTML;
- changed-file frontend coverage `100%`;
- build Next.js production.

---

## 9. Skill create e skill operative

### 9.1 Skill GAIA versionata nel repository

#### `skills/gaia-complexity-reduction/SKILL.md`

È la skill specificamente creata per GAIA e fa parte del repository.

Modalità:

- ratchet ordinario, default;
- fondazione tooling-only;
- singolo hotspot, soltanto su richiesta.

Regole principali:

- metriche prima/dopo;
- test e coverage del perimetro;
- una sola semplificazione locale nella responsabilità toccata;
- nessuna baseline usata per assorbire regressioni;
- nessun trasferimento artificiale del debito;
- nessun commit/push/PR/merge senza richiesta;
- classificazione `IMPROVED`, `REORGANIZED_AND_CHARACTERIZED`, `NO_SAFE_CHANGE`, `BLOCKED`.

File di supporto:

- `skills/gaia-complexity-reduction/references/WORKFLOW.md`;
- `skills/gaia-complexity-reduction/references/GAIA_CONSTRAINTS.md`;
- `skills/gaia-complexity-reduction/INSTALL.md`.

### 9.2 Skill Hermes di supporto usate nel processo

Queste non sono copiate nel repository GAIA, ma compongono il processo operativo:

| Skill | Responsabilità |
|---|---|
| `repository-quality-tooling` | bootstrap e manutenzione dello scanner, baseline, gate e documentazione |
| `project-coverage-audits` | audit coverage separando gap, test falliti e caveat di configurazione |
| `test-driven-development` | ciclo RED → GREEN → REFACTOR, test prima del runtime |
| `systematic-debugging` | riproduzione stretta e root cause prima della correzione |
| `quality-gate-finalization` | gate finali, coverage letterale, diff/secret audit e confini Git |
| `checkpoint-quality-gates` | PASS solo dopo il rerun di tutti i gate successivi all’ultima modifica |
| `responsive-web-qa` | audit responsive mobile/desktop e verifica overflow/navigation |
| `gaia-operations` | verifiche runtime/DB/CED basate su evidenze e deploy sensibili |

Riferimenti GAIA persistenti dentro `gaia-operations`:

- `references/gaia-code-quality-complexity-checkpoint.md`;
- `references/gaia-code-quality-phase2-ci-gate.md`.

Questi documentano hardening, verifiche read-only, parser AST reale, migrazione engine, anti-laundering e wiring CI.

---

## 10. Harness di delivery e verifica produzione

### `scripts/deploy-ced-gaia.sh`

Non è parte dello scanner di complessità, ma completa la quality delivery.

Responsabilità:

- validazione di comandi e ambiente;
- blocco di deploy remoto con modifiche tracciate non committate;
- verifica che il commit richiesto sia stato pushato;
- validazione di variabili produzione senza stamparne i valori;
- modalità `remote` e `archive`;
- manifest release con SHA/branch/timestamp;
- build e archivio immagini;
- retention delle release;
- verifica SHA server dopo il pull;
- readiness dei container backend/frontend;
- smoke HTTP di `/api/health` e home;
- smoke del virtual host Nginx;
- modalità read-only `DEPLOY_ACTION=smoke`.

Modalità:

```text
DEPLOY_ACTION=deploy
DEPLOY_ACTION=nginx
DEPLOY_ACTION=smoke
```

Per hotfix chirurgici sul CED sono stati inoltre applicati, come procedura operativa:

- backup del file runtime;
- checksum locale/live;
- riavvio dei soli servizi coinvolti;
- healthcheck;
- verifica HTTP della route;
- controllo log;
- rollback documentato.

---

## 11. Responsabilità umane e automatiche

### Automatiche

- parsing e calcolo metriche;
- soglie callable/file;
- confronto merge-base;
- nuove violation e regressioni legacy;
- baseline integrity/reproducibility;
- validazione eccezioni;
- coverage changed-file;
- test, syntax, typecheck e build;
- smoke e health dei deploy standard.

### Umane / review

- confermare invarianti funzionali;
- stabilire se un’estrazione ha valore semantico;
- verificare che il debito non sia stato spostato;
- approvare una migrazione del motore metriche;
- approvare eccezioni strette;
- decidere l’apertura di un hotspot;
- controllare il diff della baseline;
- autorizzare commit, push, PR, merge e deploy impattanti.

Il tool può dimostrare non-regressione metrica, ma non può sostituire la review semantica.

---

## 12. Stato reale al momento dell’inventario

### PASS

- esistenza di scanner Python e parser AST Babel;
- CLI complexity verificata;
- `46/46` test dell’harness PASS;
- eccezioni valide e vuote;
- soglie e policy documentate;
- workflow CI backend/frontend/code-quality presenti;
- gate coverage changed-file `100%` presenti per tutti e tre i runtime;
- skill GAIA versionata nel repository;
- report e baseline versionati.

### ATTENZIONE / NON VERDE

- `baseline-verify` restituisce exit `1` sul checkout attuale;
- baseline source commit e HEAD corrente non coincidono;
- working tree contiene modifiche runtime concorrenti;
- non è stato eseguito in questo inventario l’intero `complexity-ci-gate`, perché la failure di riproducibilità rende già falsa una dichiarazione di PASS complessivo;
- il `100%` repository-wide resta un obiettivo progressivo: il gate immediato autorevole è changed-file per backend/frontend/worker.

### Nessuna azione mutante eseguita

- baseline non rigenerata;
- eccezioni non modificate;
- runtime non modificato;
- nessun commit, push, PR o merge;
- nessun servizio riavviato.

---

## 13. Mappa rapida dei file principali

```text
AGENTS.md
docs/AGENTS.md
docs/TEST_COVERAGE_100_PLAN.md
docs/code-quality/
skills/gaia-complexity-reduction/
tools/code_quality/complexity.py
tools/code_quality/js_ast_metrics.mjs
config/code-quality/complexity-baseline.json
config/code-quality/complexity-exceptions.json
reports/code-quality/complexity-report.json
reports/code-quality/complexity-report.md
tests/code_quality/
scripts/complexity_ci_gate.sh
scripts/check_changed_backend_coverage.py
scripts/check_changed_frontend_coverage.py
scripts/check_changed_worker_coverage.py
frontend/vitest.config.ts
frontend/package.json
backend/pytest.ini
backend/.coveragerc
Makefile
.github/workflows/code-quality.yml
.github/workflows/backend.yml
.github/workflows/frontend.yml
scripts/deploy-ced-gaia.sh
```

## 14. Comando autorevole consigliato prima di chiudere una change

Dopo aver risolto o sincronizzato legittimamente lo stato baseline, la sequenza è:

```bash
make quality-test QUALITY_PYTHON=.venv/bin/python
make complexity-report REPORT_JSON=/tmp/gaia-complexity.json REPORT_MD=/tmp/gaia-complexity.md QUALITY_PYTHON=.venv/bin/python
make complexity-ratchet BASE_REF=origin/main QUALITY_PYTHON=.venv/bin/python
make complexity-check QUALITY_PYTHON=.venv/bin/python
make complexity-baseline-verify QUALITY_PYTHON=.venv/bin/python
.venv/bin/python tools/code_quality/complexity.py validate-exceptions
```

A questi gate vanno aggiunti, secondo il perimetro:

- backend pytest + coverage changed-file;
- frontend unit/coverage/typecheck/build;
- worker `make test-worker` + coverage changed-file;
- smoke/integration PostgreSQL o Playwright quando richiesti;
- `git diff --check`;
- Graphify del modulo/documentazione coinvolti;
- smoke CED dopo un deploy autorizzato.
