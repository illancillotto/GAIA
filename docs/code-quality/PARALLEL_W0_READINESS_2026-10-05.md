# W0 — readiness della campagna parallela

Data: 2026-10-05. **Audit W0 eseguito; W1 non avviata.**
Tre agenti hanno misurato i candidati in parallelo, senza modificare runtime,
test, fixture o configurazioni. Il coordinatore aggiorna solo questi documenti.
Il piano di riferimento e `PARALLEL_REDUCTION_PLAN_2026-10-05.md`.

## Snapshot e baseline

- Branch `main`, HEAD e merge-base del controllo locale:
  `bfc8e68fd6d4acf373b23b7cc15693c80bd75f18`.
- Baseline autorevole letta dal merge-base, non rigenerata nella change:
  `config/code-quality/complexity-baseline.json`.
- `source_commit` della baseline: `11ed944a46ebdeb32ad50c14e7fca90b2c55f1fd`.
- SHA256 baseline corrente:
  `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
- Report AST W0: `2026-10-05T11:39:22.942109+00:00`, 1604 file,
  19714 callable, 4742 violation, 2041 error e 2701 warning.
  Il precedente piano riportava 1603/19713/4741: il checkout concorrente
  e cambiato; il delta non e attribuito a W0 o a una riduzione.
- Confronto integrale baseline: 26 finding su 11 file, exit 1.
  Ratchet del working tree contro HEAD: otto finding Wiki, exit 1.
  Ratchet dei tre runtime candidati: exit 0, nessun finding.

HEAD e rimasto invariato durante le misure; il working tree e non pulito.
Wiki/Ruolo, Presenze/GaTe e SISTER hanno change runtime/test concorrenti;
sono **fuori assegnazione W1**. Anche i loro documenti e test untracked
vanno preservati. I sei file runtime/test proposti qui risultano puliti.
Le misure sono locali, non una validazione del futuro contenuto integrato.

## Gate riprodotti

| Verifica | Risultato |
| --- | --- |
| `make quality-test` | 169 passed, 6,30 s |
| `BASE_REF=bfc8e68f… make lint-backend QUALITY_PYTHON=backend/.venv/bin/python` | PASS, compileall e style ratchet su 26 file Python cambiati |
| Confronto complexity globale / ratchet working tree | FAIL noto: 26 / 8 finding descritti sotto |
| Ratchet scoped tre candidati con baseline del merge-base | PASS, zero finding |
| ESLint scoped Organigramma runtime/test | PASS, zero warning/error |
| Typecheck frontend con build-info separato in `/tmp` | PASS |

Il ratchet scoped e ottenuto dal report fresco con `baseline_at_merge_base`,
`compare(changed_only=...)` e `added_lines_since`. Prima di implementare,
ripetere il comando CLI sullo snapshot approvato:

```bash
python3 tools/code_quality/complexity.py ratchet --base-ref bfc8e68fd6d4acf373b23b7cc15693c80bd75f18 \
  backend/app/modules/catasto/services/anomalie_payloads.py \
  backend/app/modules/utenze/services/parser_service.py \
  frontend/src/features/organigramma/organigramma-selection-controller.ts
```

Non e stato eseguito un build frontend o un test applicativo globale.
Il verde scoped non rende verde il gate cumulativo. Non sono cambiate policy,
esclusioni, baseline, soglie o configurazioni coverage/CI.

## Classificazione completa dei 26 finding

Tutti sono `legacy_metric_regression`, non 26 nuove violation error-level.
I delta confrontano il checkout con la baseline corrente; gli otto indicati
con WT appartengono anche al ratchet working tree. Le cause funzionali
richiedono review dell'owner: l'audit non autorizza a rimuovere contratti.

| File / simbolo | Delta metriche | Finding | Decisione W0 |
| --- | --- | ---: | --- |
| Wiki `auth.py::verify_token` | LOC +1 | 1 WT | Review owner Wiki; preservare verifica scope |
| Wiki `cli.py::main` | cyc +1, LOC +6 | 2 WT | Review lifecycle/audit; niente wrapper cosmetici |
| Wiki `data/cli.py::main` | LOC +3 | 1 WT | Review owner; preservare lifecycle |
| Wiki `data/server.py::create_server` | LOC +3 | 1 | Change gia committed: review separata |
| Wiki `data/service.py::DataService.__init__` | LOC +1, parametri +1 | 2 | Contratto costruttore: nessuna riduzione automatica |
| Wiki `experiment_runner.py::experiment_manifest` | LOC +1 | 1 | Review manifest separata |
| Wiki `http.py::create_http_app` | cyc +1, cog +1, LOC +6, nesting +1 | 4 WT | Review lifecycle HTTP; preservare cleanup |
| Wiki frontend `WikiMCPPreview` | LOC +1 | 1 | Review feature, no split per LOC |
| Ruolo frontend `RegisteredMailRow` | LOC +1 | 1 | Review feature/owner, fuori pilota |
| Worker `test_sister_browser_reliability.py::_Page.__init__` | LOC +1 | 1 | Goal test-only separato |
| Stesso file `_Page.locator` | cyc +1, cog +1, LOC +2 | 3 | Fake browser: conservare tutti gli scenari |
| Worker `test_sister_reused_menu_html.py::test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice` | cyc +1, cog +5, LOC +11, nesting +1 | 4 | Goal test-only con owner SISTER |
| Stesso test, callable annidato `scenario` | cyc +1, cog +5, LOC +11, nesting +1 | 4 | Stessa responsabilita; niente esclusione dei test |

Totali: Wiki backend 12, frontend Wiki/Ruolo 2, test worker 12.
Nessun finding viene sanato riscrivendo la baseline. Il recupero globale
resta una dipendenza aperta, distinta dal pilota; la sua chiusura richiede
goal autorizzati e gate verdi, oppure una decisione separata fail-closed.

## Metriche prima e coverage full-file

Le tuple callable sono cognitive/cyclomatic/LOC/nesting.
Le aggregazioni riguardano l'intero file, non solo il callable scelto.

| Candidato | Callable prima | LOC file / numero callable | Cog sum/max | Cyc sum/max | Import |
| --- | --- | --- | --- | --- | ---: |
| Catasto `build_anomalia_payload` | 30/24/31/2 | 105 / 7 | 65/30 | 56/24 | 4 |
| Utenze `parse_folder_name` | 30/21/79/2 | 110 / 5 | 31/30 | 26/21 | 4 |
| Organigramma `handleSchemaCardSelect` | 23/12/19/2 | 95 / 13 | 59/23 | 50/12 | 2 |

| Suite mirata | Test | Statement | Branch | Funzioni / linee | Durata | Readiness runtime |
| --- | ---: | --- | --- | --- | --- | --- |
| Catasto anomalie payload | 5 passed | 99/99, 100% | 50/52, 96,15% | n/a | pytest 3,38 s; wall 5,97 s | BLOCKED_COVERAGE |
| Utenze parser | 5 passed | 52/58, 89,66% | 12/16, 75% | n/a | wall 1,70 s | BLOCKED_COVERAGE_AND_INVARIANT |
| Organigramma selection | 35 passed | 62/62, 100% | 57/57, 100% | 13/13 e 50/50, 100% | Vitest 1,33 s | READY_SCOPED |

Backend misurato con config temporanea branch coverage senza omit;
zero righe escluse nei report. Catasto exit 1 soltanto per fail-under 100, non test falliti.
Utenze e un audit senza enforcement fail-under: exit 0 dei test **non**
significa coverage conforme. Frontend JSON contiene solo il file assegnato.
Le durate sono osservazioni, non stime SLA; non e stato profilato il picco RAM.
In W1 limitare i test costosi e l'integrazione cumulativa a un processo
alla volta; aumentare concorrenza solo dopo misura risorse.

### Prerequisiti Catasto

Branch mancanti `120→123` e `126→131`: superfici e indice presenti, ma
`imponibile_sf=None`. Aggiungere caratterizzazione reale dell'atteso senza
delta, possibilmente coprendo entrambe le superfici nel medesimo scenario.
Il primo goal deve essere test-only e verificare nuovamente full-file 100%.
Nessuna modifica runtime fino alla chiusura del prerequisito.

### Prerequisiti Utenze

Gap: property `is_person`/`is_company` (30/34), input vuoto (50), persona
incompleta (62), `missing_nome` (77–78), classificazione non speciale
(`125→128`). Le property e gli input reali ammettono caratterizzazione.
La guardia `missing_nome` sembra irraggiungibile: `_split_tokens` elimina
token vuoti e il percorso persona completo richiede almeno tre token.
Prima serve dimostrare l'invariante con l'owner; non fabbricare un risultato
impossibile del tokenizer via monkeypatch per raggiungere il numero.
Nessuna esclusione coverage o rimozione della guardia viene autorizzata da W0.

## Registry ownership proposto

Ownership proposta, non lock acquisito: confermare assenza di owner esterni
e congelare gli hash all'avvio di ciascun goal.

| Slice / owner futuro | Runtime esclusivo | Test esclusivo | Artefatti |
| --- | --- | --- | --- |
| W1-A / agente A | `backend/app/modules/catasto/services/anomalie_payloads.py` | `backend/tests/test_catasto_anomalie_payloads.py` | `/tmp/gaia-w1-catasto-*` |
| W1-B / agente B | `backend/app/modules/utenze/services/parser_service.py` | `backend/tests/test_anagrafica_parser.py` | `/tmp/gaia-w1-utenze-*` |
| W1-C / agente C | `frontend/src/features/organigramma/organigramma-selection-controller.ts` | `frontend/tests/unit/organigramma-selection-controller.test.ts` | `/tmp/gaia-w1-organigramma-*` |

Per W1-A/B test-only il runtime e read-only. Nessun nuovo file/helper/fixture
e implicitamente ammesso: aggiungerlo al manifest prima della change.
`backend/tests/conftest.py`, modelli Catasto/Utenze, consumer route/GIS,
hook Organigramma e API condivise sono dipendenze read-only, fuori ownership.
Non servono DB operativo o rete per le tre suite misurate.

Matrice conflitti: A/B condividono ambiente Python/conftest ma non file
scrivibili; A/C e B/C non condividono file assegnati. Config, lockfile,
baseline, coverage policy, docs programma e grafi appartengono soltanto
al coordinatore. Se occorre modificarli, sospendere la slice e rivedere scope.
I processi di misura W0 hanno usato report/cache/coverage separati in `/tmp`.

## Isolamento proposto, non predisposto

Non sono stati creati branch, commit o worktree. Per implementazioni parallele
proporre tre worktree detached al medesimo SHA approvato, previa autorizzazione
esplicita. Un checkout da HEAD non include il dirty tree: non trasferire
Wiki/Presenze/SISTER o test untracked senza manifest approvato.
Prima confermare se usare il solo committed HEAD oppure uno snapshot
autorizzato con patch selezionate. Le misure W0 includono l'ambiente corrente:
riprodurle negli isolati prima di dichiarare readiness trasferibile.

Registrare SHA base/merge-base, hash runtime/test/config, baseline SHA,
allowlist, comandi, invarianti e metrica obiettivo per ogni goal. Se HEAD
o dipendenze cambiano, rieseguire preflight; niente reset/stash/clean.
Agenti consegnano patch, non commit. Coordinatore integra una patch alla
volta, verifica aggregati/invarianti e gate cumulativi, poi aggiorna Graphify
con target dedicati (Catasto/Utenze code o frontend; docs piattaforma).

## Decisione richiesta per il checkpoint successivo

W0 e conclusa come audit, **non come via libera a tre refactoring runtime**.
Proposta del prossimo checkpoint, da autorizzare esplicitamente:

1. W1-A: singolo goal test-only Catasto per chiudere i due branch reali.
2. W1-B: singolo goal di audit/caratterizzazione parser Utenze; fermarsi
   sulla guardia irraggiungibile senza modifiche funzionali o policy.
3. W1-C: singolo hotspot Organigramma, obiettivo riduzione cognitiva reale
   della selezione senza alterare Ctrl/Meta/Shift, drag, capture o permessi.
   Ammissibile dopo conferma ownership e isolamento/riproduzione dei gate.

Nessuna sostituzione automatica del candidato bloccato. Il recupero globale
Wiki/worker rimane separato. Stop a fine goal e review prima della prossima
ondata. In W0 metriche runtime prima/dopo invariate: nessun `IMPROVED` dichiarato.

## Evidenze locali e riproduzione

Artefatti non versionati, da rigenerare se `/tmp` non e piu disponibile:

- `/tmp/gaia-w0-global.{json,md}`, `/tmp/gaia-w0-comparison.json`:
  scan globale e confronto con baseline/merge-base.
- `/tmp/gaia-w0-quality-tests.log`, `/tmp/gaia-w0-lint-backend.log`.
- `/tmp/gaia-w0-catasto-coverage.json`, `-test.log`, `-time.txt`, `-coverage.ini`.
- `/tmp/gaia-w0-utenze-coverage.json`, `/tmp/gaia-w0-utenze-coveragerc`.
- `/tmp/gaia-w0-organigramma-coverage/coverage-final.json` e
  `/tmp/gaia-w0-organigramma.tsbuildinfo`.

Backend: dalla directory `backend`, usare `.venv/bin/python -m pytest` sul
test assegnato, `--cov=app.modules.<dominio>.services.<modulo>`,
`--cov-branch`, config temporanea senza esclusioni, report JSON isolato e
`COVERAGE_FILE` dedicato; per il gate aggiungere `--cov-fail-under=100`.
Verificare nel JSON statement e branch, non soltanto la percentuale combinata.
Frontend, dalla directory `frontend`:

```bash
VITEST_COVERAGE_INCLUDE=src/features/organigramma/organigramma-selection-controller.ts \
  npm run test:unit -- tests/unit/organigramma-selection-controller.test.ts \
  --coverage --coverage.reportsDirectory=/tmp/gaia-w0-organigramma-coverage --cache=false
```

Graphify piattaforma aggiornato con `make graphify-platform-docs`:
`chunk 1/1 done`, nessun warning semantico, exit 0; 2507 nodi, 5804 edge.
Log `/tmp/gaia-w0-graph-docs.log`; costo stimato dal tool $0,0108.
Verificare sempre chunk e warning, non soltanto l'exit code.
