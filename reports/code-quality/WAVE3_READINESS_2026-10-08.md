# GAIA — Wave 3 readiness Catasto backend 2026-10-08

## Esito

**C1 ADE WFS: BLOCKED_COVERAGE nel contesto isolato misurato.** La suite
assegnata richiede PostgreSQL/PostGIS: tutti gli otto scenari risultano skipped
con `DATABASE_URL` SQLite. Non ci sono test funzionali PASS in questa esecuzione.
Il processo pytest esce0, ma il gate coverage100% fallisce con exit2. Nessun
refactor runtime è avviato o integrato. Questo audit non blocca automaticamente
gli altri file Wave3, sui quali non sono state eseguite misure di readiness.

Le metriche giustificano una futura responsabilità delimitata nel servizio,
ma la copertura reale e l'equivalenza sul database GIS devono precedere le
modifiche. Il runtime integration finale resta congelato durante questa verifica.

## Ownership e snapshot

- Agent C1, modalità read-only readiness.
- Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261008-catasto-backend`.
- Branch `refactor/complexity-catasto-ade-readiness`.
- HEAD iniziale e merge-base main:
  `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Registro ownership C1 predisposto prima dell'assegnazione nella branch
  integration, `docs/code-quality/MULTI_AGENT_OWNERSHIP_2026-10-08.md`.
- Runtime esclusivo in lettura: `backend/app/modules/catasto/services/ade_wfs.py`.
- Suite esclusivamente eseguita: `backend/tests/test_catasto_ade_wfs_integration.py`.
- Scrittura consentita: questo report e artefatti temporanei di misura.
- Preflight working tree pulito. Nessun runtime, test, configurazione, baseline,
  soglia o tooling modificato; nessuna modifica al checkout main.

Skill progetto complessità e contesto checkpoint applicate; policy/soglie del
commit8/10 autorevoli. Nessun numero del7/10 usato per la baseline operativa.

## Graphify — Orientamento

Target dedicato eseguito prima dell'esplorazione dettagliata:

```bash
make graphify-catasto-query \
  Q='ade_wfs apply_ade_alignment preview_ade_alignment_apply audit transactions'
```

Nella worktree nuova il grafo Catasto non esiste: target exit2 con
`graph file not found`. Query ripetuta in sola lettura sul corpus Catasto
esistente del checkout principale tramite lo stesso target Make: **PASS**.
Nessuna estrazione dalla root grezza né rigenerazione del grafo condiviso.

Il risultato orienta su `apply_ade_alignment`, normalizzazione categorie,
raccolta/risoluzione candidati audit e creazione audit run. Gli edge EXTRACTED
sono distinti dagli INFERRED, che non costituiscono prova di comportamento.
La query non sostituisce la lettura delle sorgenti o i test e non è una misura
della complessità. Runtime e dipendenze invariati, nessun refresh Graphify richiesto.

Log `/tmp/c1-catasto-graphify-query.log` e
`/tmp/c1-catasto-graphify-main-query.log`.

## Metriche AST autorevoli del file

Scanner Python del checkout base, JSON `/tmp/c1-ade-wfs-before.json` e Markdown
`/tmp/c1-ade-wfs-before.md`. Nessun parse error.

| Metrica file | Valore |
| --- | ---: |
| Callable | 41 |
| Cognitive sum / max | 362 / 58 |
| Cyclomatic sum / max | 311 / 39 |
| Effective LOC | 2002 |
| Import / dipendenze | 14 / 14 |
| Error / warning finding | 21 / 9 |
| Total finding | 30 |

Il file contiene grandi query SQL multiline: LOC elevate segnalano dimensione
della responsabilità ma non equivalgono da sole a branching applicativo.
Una funzione può produrre più finding; il totale30 non misura problemi indipendenti.

| Callable | Cognitive | Cyclomatic | LOC | Nesting | Params |
| --- | ---: | ---: | ---: | ---: | ---: |
| execute_ade_sync_run | 58 | 30 | 114 | 5 | 3 |
| apply_ade_alignment | 58 | 39 | 370 | 2 | 8 |
| preview_ade_alignment_apply | 31 | 30 | 255 | 2 | 4 |
| get_ade_alignment_report | 23 | 22 | 289 | 2 | 3 |
| _geometry_to_wkt_6706 | 19 | 12 | 20 | 3 | 1 |
| get_ade_sync_run_status | 18 | 18 | 24 | 2 | 2 |
| get_latest_ade_sync_run_status | 15 | 16 | 24 | 1 | 1 |
| get_ade_alignment_audit_run_detail | 14 | 14 | 54 | 2 | 2 |

Nessuna misura dopo refactor: runtime invariato, delta metrica0.
`useState`/`useEffect` non pertinenti al runtime Python.

## Responsabilità candidata, non implementata

Una sola futura slice proposta: **aggregazione/deduplicazione delle feature
durante download tile in `execute_ade_sync_run`**, preservando progress e
confini di persistenza. Non include riallineamento geometrie, matching,
pruning/soppressioni, interfacce HTTP o riorganizzazione dell'intero servizio.
Target iniziale: diminuire cognitive58/nesting5 del callable e gli aggregati,
senza trasferire branching a un mega-helper.

Invarianti da caratterizzare prima di autorizzare runtime:

- Validazione UUID/run/bbox e limite tile prima dell'avvio.
- WFS params/count/startIndex, timeout60s di default e stop alla pagina corta.
- Stesso ordine tile/feature; ultima feature per riferimento prevale, mentre
  il set dei riferimenti con geometria mantiene la presenza storica osservata.
- Stato processing e commit iniziale; commit progress dopo ogni tile;
  stato persisting e relativo commit prima dell'upsert.
- Riletture DB del run e relativi errori se sparisce durante progress,
  pre-persistenza o post-upsert.
- Stato completed, contatori e timestamp finali; eccezioni provocano rollback,
  reread del run, marcatura failed/commit se ancora presente e propagazione.
- Nessun retry aggiunto o riordino di richieste esterne e commit per semplificare
  la metrica. Nessun cambiamento delle semantiche di recupero o progress.

La suite assegnata copre invece principalmente alignment PostGIS; readiness
full-file non può essere dedotta dalla sola presenza di quei test.
Stop condition della futura slice: responsabilità isolata, equivalenza dei
side effect dimostrata, full-file100%, ratchet0, metriche aggregate migliorate.
Tali prerequisiti **non sono raggiunti** da questa verifica.

## Test matrix della suite assegnata

| Comportamento | Test esistente | Esito corrente | Gap |
| --- | --- | --- | --- |
| WFS geometry typed binds | test_upsert_ade_parcels_persists_wfs_geometry_with_psycopg_typed_binds | SKIPPED | PostgreSQL/PostGIS |
| Update in-place con FK preservate | test_apply_ade_alignment_updates_geometry_in_place_and_preserves_fk | SKIPPED | PostgreSQL/PostGIS |
| Matching sezione GAIA assente | test_apply_ade_alignment_matches_when_gaia_section_is_missing_and_ade_has_value | SKIPPED | PostgreSQL/PostGIS |
| Dedup chiavi AdE e base reference | test_ade_alignment_report_dedupes_duplicate_ade_keys_preferring_base_reference | SKIPPED | PostgreSQL/PostGIS |
| Soppressione solo con flag esplicito | test_apply_ade_alignment_suppresses_missing_only_with_explicit_flag | SKIPPED | PostgreSQL/PostGIS |
| Split padre/figli | test_apply_ade_alignment_handles_split_as_parent_suppressed_and_new_children | SKIPPED | PostgreSQL/PostGIS |
| Comune non mappato | test_apply_ade_alignment_skips_new_parcels_when_comune_is_unmapped | SKIPPED | PostgreSQL/PostGIS |
| Nessuna soppressione nel percorso standard | test_apply_ade_alignment_standard_does_not_suppress_missing_gaia | SKIPPED | PostgreSQL/PostGIS |
| Download/progress/failure tile | Non assegnato in questo audit | NOT_RUN | Caratterizzazione dedicata |

Nessun test aggiunto o modificato. Skipped non è PASS; non si dichiara che tutte
le altre suite del repository siano incapaci di caratterizzare il servizio.
Sono stati individuati riferimenti in phase1 e autosync scheduler, senza eseguirli
o usarli come falsa evidenza di copertura.

## Coverage full-file e cause

Suite eseguita con ambiente isolato SQLite esplicito. La fixture richiede URL
PostgreSQL, verifica `PostGIS_version()` e tabelle `cat_ade_sync_runs`/
`cat_ade_particelle`; con SQLite fa skip prima dei test funzionali. Non è stata
eseguita su un database deployment, né predisposto un server PostGIS in questo
audit read-only. Lo skip non dimostra che nessun server PostgreSQL esista nel
computer: identifica la mancanza del requisito nel contesto di prova utilizzato.

| Full-file ade_wfs.py | Coperto / totale | Percentuale |
| --- | ---: | ---: |
| Statement | 107 / 531 | 20,15% |
| Branch | 0 / 162 | 0% |
| Statement+branch | 107 / 693 | 15,44% |
| Esclusioni | 0 | n/a |

I107 statement coperti sono principalmente import/definizioni: non dimostrano
comportamento del servizio. Missing424 statement e162 branch. Coverage JSON
include il **file completo**, senza filtri di righe, suppressioni o threshold
ridotti: `/tmp/c1-ade-wfs-coverage.json`.

Esiti:

- Pytest: **0 PASS, 8 SKIPPED**, exit0; log `/tmp/c1-ade-wfs-tests.log` con le
  otto ragioni PostgreSQL riportate per linea.
- `coverage report --fail-under=100`: **FAIL, exit2**.
- Complexity report: PASS per scansione AST, non gate di non-regressione.
- Ratchet non rieseguito per questo audit docs-only senza runtime/test change;
  i gate della campagna integration restano evidenze separate.

## Priorità Wave3 considerate

| Percorso | Stato readiness in questa assegnazione | Prossima verifica proposta |
| --- | --- | --- |
| services/ade_wfs.py | BLOCKED_COVERAGE misurato sul contesto SQLite | DB PostGIS isolato e caratterizzazione download/progress; full-file100% |
| routes/anagrafica/matching.py | NOT_MEASURED | Test matching, normalizzazione e ambiguità prima di assegnare una slice |
| services/gis_service.py | NOT_MEASURED | Geometrie/SRID, query e persistenza con fixture GIS |
| routes/anomalie.py | NOT_MEASURED | Contratti query/mutation e permessi della singola responsabilità |
| routes/import_routes.py | NOT_MEASURED | Parsing, staging, failure parziali e transazioni import |

I percorsi della tabella sono relativi a `backend/app/modules/catasto/`.
Nessuna dichiarazione di tutti BLOCKED o READY senza misure. Ownership Catasto
backend resta separata da frontend GIS e GIS condiviso. Nessun hotspot successivo
iniziato; il Coordinator decide l'ordine dopo i gate della campagna corrente.

## Riproduzione

```bash
git status --short
git rev-parse HEAD
git merge-base HEAD main
python3 tools/code_quality/complexity.py report \
  backend/app/modules/catasto/services/ade_wfs.py \
  --json /tmp/c1-ade-wfs-before.json --markdown /tmp/c1-ade-wfs-before.md
cd backend
APP_ENV=test DATABASE_URL=sqlite:////tmp/c1-ade-wfs-readiness.db \
  COVERAGE_FILE=/tmp/c1-ade-wfs-readiness.coverage \
  .venv/bin/python -m coverage run --branch --source=app/modules/catasto/services \
  -m pytest -q tests/test_catasto_ade_wfs_integration.py \
  -o cache_dir=/tmp/c1-ade-wfs-cache -rs
.venv/bin/python -m coverage json --data-file=/tmp/c1-ade-wfs-readiness.coverage \
  --include='*/ade_wfs.py' -o /tmp/c1-ade-wfs-coverage.json
.venv/bin/python -m coverage report --data-file=/tmp/c1-ade-wfs-readiness.coverage \
  --include='*/ade_wfs.py' --fail-under=100
```

Le failure/skipped sono intenzionalmente riproducibili con lo stesso contesto;
per una futura verifica funzionale occorre un DATABASE_URL **isolato** PostGIS
con migrazioni richieste, seguito da misura completa e non dal semplice exit0.

## Integrità e stop

SHA-256 runtime:
`9a64354c3e8412b0c0f6a33fd2bb71a910a03cb300d6a4d4345026b9531d5f16`.
Suite:
`576d3d4045a8aee2da385aa6e993b71f1b61a56c71db9706a9ce1708ace7decb`.
Baseline:
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.

Nessun diff runtime/test/baseline/tooling; diff-check PASS. Commit esclusivamente
documentale sulla branch assegnata, nessun cherry-pick/merge della readiness
nell'integration corrente. **STOP dopo readiness**, come richiesto: nessun
refactor, nuovo test o ulteriore funzione modificata.
