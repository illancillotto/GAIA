# Wave 3 — GIS readiness

## Scope and snapshot

Read-only readiness assegnata dal Coordinator dopo checkpoint B5 GREEN.
Branch `refactor/complexity-gis-readiness`, worktree
`/home/cbo/CursorProjects/GAIA-campaign-20261008-gis-readiness`.
Preflight: working tree inizialmente clean, HEAD e merge-base con main
`55a1b1d35911451e018b662c2acc450bf5994ea2`.

Runtime frozen, nessuna modifica ai test. Unico file scritto: questo report.
Perimetro delimitato:

- `frontend/src/app/catasto/gis/page.tsx`.
- `backend/app/modules/gis/services.py` (GIS condiviso, **non** Catasto backend).

Nessuna baseline, soglia, ignore, exclusion, dipendenza o configurazione
modificata. Nessuna integrazione, suite globale o refactoring eseguito.
L'audit del 7 ottobre non è una baseline operativa.

## Orientation

Graphify interrogato tramite i target Make, sui corpus corretti del checkout
principale; grafi usati per orientamento, non come prova di complessità:

```bash
make graphify-frontend-query Q='CatastoGisPage'
make graphify-backend-query Q='app/modules/gis/services.py'
make graphify-backend-query Q='get_catalog_health'
make graphify-backend-query Q='get_catalog_dashboard'
```

La query frontend collega pagina, `useGisSelection` e `useGisArchive`.
Le prime due query backend non trovano nodi; la query per simbolo reale
`get_catalog_dashboard` trova services, catalog routes, permissions,
shapefile import/publish/export, QGIS access e health checks.
Output limitato dal budget Graphify; il grafo backend mostra anche route
legacy e modulari. L'identità e le metriche authoritative vengono dalla
scansione AST del worktree base, non da eventuali edge stale.
Nessun refresh necessario: runtime e relazioni non cambiano.

## Current AST metrics

Scansione:

```bash
python3 tools/code_quality/complexity.py report \
  frontend/src/app/catasto/gis/page.tsx backend/app/modules/gis/services.py \
  --json /tmp/c2-gis-readiness-metrics.json \
  --markdown /tmp/c2-gis-readiness-metrics.md
```

| File | Callable | Effective LOC | Cognitive sum/max | Cyclomatic sum/max | Error | Warning |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Frontend Catasto GIS page | 176 | 2167 | 621 / 334 | 712 / 298 | 13 | 8 |
| Backend GIS shared services | 109 | 2169 | 458 / 27 | 480 / 20 | 14 | 20 |

Totale perimetro: due file, 285 callable, 27 error e 28 warning.
Sono finding per metrica, non 55 problemi indipendenti.
Scanner frontend: useState28, useEffect8, useReducer0; hook invariati.

| Callable | Cognitive | Cyclomatic | LOC | Nesting | Params |
| --- | ---: | ---: | ---: | ---: | ---: |
| CatastoGisPage | 334 | 298 | 1896 | 4 | 0 |
| handleImportXlsx callback | 43 | 31 | 81 | 4 | 1 |
| Excel row map callback | 17 | 18 | 8 | 0 | 2 |
| popupToMatch | 14 | 15 | 30 | 1 | 1 |
| AdE polling effect callback | 14 | 9 | 30 | 2 | 0 |
| create_change_requests_from_shapefile_import | 27 | 19 | 111 | 2 | 4 |
| update_annotation | 23 | 17 | 49 | 2 | 5 |
| _layer_health_issues | 22 | 14 | 63 | 2 | 2 |
| get_catalog_dashboard | 19 | 20 | 51 | 1 | 2 |

Metric before = metric after: runtime non toccato. Delta complessità **zero**.
La presenza di coverage rende una futura slice possibile, non riduce da sola
il debito e non autorizza automaticamente un refactor.

## Frontend existing-suite readiness

Comando dalla directory `frontend`:

```bash
VITEST_COVERAGE_INCLUDE=src/app/catasto/gis/page.tsx \
  npm run test:unit -- tests/unit/catasto-gis-page.test.tsx \
  tests/unit/catasto-gis-coordinate-page.test.tsx --maxWorkers=2 \
  --coverage --coverage.reportsDirectory=/tmp/c2-gis-frontend-coverage
```

**34 PASS**, due test file; zero skipped. Run 16,74 secondi.
Pagina completa verificata nel JSON, non soltanto riepilogo globale:

| Coverage | Covered / total | Missing |
| --- | ---: | ---: |
| Statement | 592/592 = 100% | 0 |
| Branch | 639/639 = 100% | 0 |
| Function | 176/176 = 100% | 0 |
| Line | 526/526 = 100% | 0 |

Nessuna suppression coverage trovata nella pagina, nessuna nuova exclusion.
Map adapter, pannelli, API e hook condivisi sono mockati al confine della
pagina: questa misura non certifica i loro runtime o l'integrazione reale.
La suite coordinate esercita la propria pagina separata; il coverage include
esplicitamente solo il file Catasto GIS richiesto.

## Backend existing-suite readiness

Comandi dalla directory `backend`:

```bash
COVERAGE_FILE=/tmp/c2-gis-backend.coverage APP_ENV=test \
  DATABASE_URL=sqlite:////tmp/gaia-campaign-gis-readiness.db \
  .venv/bin/python -m coverage run --branch --source=app/modules/gis \
  -m pytest tests/test_gis_services_contracts.py tests/test_gis_platform_api.py -q
COVERAGE_FILE=/tmp/c2-gis-backend.coverage .venv/bin/python -m coverage json \
  --include='*/services.py' -o /tmp/c2-gis-backend-coverage.json
COVERAGE_FILE=/tmp/c2-gis-backend.coverage .venv/bin/python -m coverage report \
  --include='*/services.py' --fail-under=100
```

**108 PASS**, zero skipped; 102 warning JWT legati alla chiave corta delle
fixture, nessuna failure. Il source-directory evita l'eager import doppio
SQLAlchemy del source dotted senza cambiare tooling o scoping CI.

Full-file `services.py`: **1041/1041 statement**, **312/312 branch**, 100%.
Zero statement excluded, zero missing line/branch e zero partial branch nel JSON.
Il filtro di report seleziona l'intero file runtime di ownership: non righe,
funzioni o branch specifici. I servizi importati di altri file non sono
certificati da questa misura e non vengono modificati.

Anche il backend è coverage-ready per una sola futura responsabilità coesa,
non autorizza relocation massiva o modifica di auth/transazioni.

## Characterization matrix

| Responsibility | Existing evidence | Remaining prerequisite |
| --- | --- | --- |
| Bootstrap/sessione mancante/errori azioni | primary map workflows, missing session, degraded bootstrap | integrazione autentica sullo stack fuori readiness |
| Import Excel varianti header, esiti resolver, geometrie mancanti | imports workspace layers; alternate headings; import failures Error/non-Error | assertion completa payload/header precedence e cap5000 per candidata |
| Persistenza archivi, aggiornamento colore, cancellazione, autoload | workspace-layer workflows e archive-failure tests | race fra due richieste concorrenti non provata dalla percentuale |
| Selezione, popup parcella, titolari, Capacitas, WhiteCompany/DUI | rich/sparse/inferred record tests, ambigui/unmatched identifiers | map adapter/pannelli reali richiedono suite proprie/E2E |
| AdE polling queued/processing/completed/failed | polling cases, preview geometry variants, active completion | test dedicato risposta tardiva dopo unmount/nuovo run prima di toccare lifecycle |
| Permessi GIS, annotazioni e audit DB | services contracts e platform API | transazioni ed auth devono rimanere invarianti nella futura slice backend |
| Shapefile→change requests | API idempotency, pagination, skips, invalid target/state | verifica ordine side effect e rollback se si modifica orchestrazione |

Full-file100% non equivale alla prova di tutti gli interleaving async.
Non si propone di modificare il polling nella prima slice.

## One coherent candidate

**Frontend: normalizzazione delle righe Excel in riferimenti particella**,
dentro `handleImportXlsx`. È la candidata primaria del prossimo checkpoint,
per priorità della coda estrema (pagina cognitive334) e comportamento
pure/data già in gran parte caratterizzato.

Limiti dell'ownership proposta: pagina, nuovo helper locale GIS e test
esclusivi; nessun hook/lib/UI condiviso e nessuna route/backend Catasto.

Invarianti da fissare con test meaningful prima del runtime:

- solo primo foglio, stesso `sheet_to_json({defval:null})`;
- massimo5000 righe, `row_index=index+2`, ordine di input invariato;
- precedenza esatta header lowercase → titlecase → uppercase;
- sub: sub/Sub/SUB prima di subalterno/Subalterno;
- fallback **nullish**, non truthy: 0, false e stringa vuota non saltano
  automaticamente al successivo alias;
- String/trim identici; whitespace vuota diventa null dopo scelta;
- stessa chiamata resolver con `includeGeometry:true`;
- nessun cambio stato busy, catch/finally, layer id/color, API o feedback.

Tecnica possibile: mapping tipizzato e lookup degli alias coerente, eliminando
duplicazione di coalescenze/parsing. Non estrarre l'intero handler di81LOC,
né spostare il JSX in un megacomponente. Misurare aggregati inclusivo del
nuovo helper; classificare IMPROVED solo se la somma realmente cala.

Stop condition futura: tutti i nuovi helper sotto soglie error, zero nuovi
finding ratchet, full-file100% pagina e helper, invarianti del payload
dimostrati. Se migliora soltanto la posizione del codice,
REORGANIZED_AND_CHARACTERIZED; nessun refactor autorizzato in readiness.

Il backend GIS shared non ha coda cognitiva estrema (max27): pur con
file2169LOC e numerosi finding, non si propone una decomposizione massiva
come scorciatoia. Nessuna seconda candidata avviata.

## Limits and classification

**NO_CHANGE / READINESS_ONLY**. Pagina frontend e services backend sono coverage-ready per una
piccola slice pura, non per qualunque refactor. Runtime e test congelati.
Non eseguiti build, E2E, suite repository completa, ratchet o baseline check:
questo audit non introduce runtime e non sostituisce il gate integration.
Non dichiarare campagna migliorata o wave3 refactor completata da questo report.

## Evidence

- `/tmp/c2-gis-readiness-metrics.json`, `/tmp/c2-gis-readiness-metrics.md`.
- `/tmp/c2-gis-frontend-query.log`, `/tmp/c2-gis-backend-query{,2,3}.log`.
- `/tmp/c2-gis-frontend-tests.log`.
- `/tmp/c2-gis-frontend-coverage/coverage-final.json`.
- `/tmp/c2-gis-backend-tests.log`, `/tmp/c2-gis-backend-coverage.json`.
- Commit report esclusivo: reperibile con
  `git log -1 --format=%H -- reports/code-quality/WAVE3_GIS_READINESS_2026-10-08.md`.
