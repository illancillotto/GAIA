# R5 orphan operator identity — independent final verification

## Ownership and frozen source

Verifier `r5_orphan_verifier` owns only this report in dedicated worktree
`/home/cbo/CursorProjects/GAIA-campaign-20261009-r5-orphan-verification`, branch
`verify/complexity-r5-orphan-operators`. Coordinator applied frozen author source
`cd4b11457f2cb3848b87a5c41d110657d8d11d27` as verifier HEAD
`fba9c2cc651dd393705a65be51151fbb9f4ad4a1` before verification started.
Independent reviewer approved exactly that source in report-only commit
`8730228ff3aa3edbd1d907967dd2a9d6a156742b`, following applied reviewer source
`912dc84660dd8aa29404689ba78841e19f333f61`.

Authoritative main/merge-base is `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Pre-slice AST is read directly from Git
`55a91d42fa1d6a4286a2c98578f61352e8c089db`; runtime diff to author/reviewer
pre-slice `e96277c2` is empty. No runtime, tests, configuration, baseline,
threshold, exception, exclusion, tooling or shared file was changed by this
verifier. Dirty main was neither edited, copied, stashed nor reset.

All five source-commit blobs are independently equal across author, reviewer
and verifier; complete `backend/app` Git trees are equal. Runtime identities:

| File | Git blob | SHA256 |
| --- | --- | --- |
| `analytics.py` | `097557c8773316e0b5e73b982255bc83fe9594aa` | `cbe829a0c31166288f2774a03b92f70351705612586745f0dac1564e89304dc7` |
| `_orphan_session_operators.py` | `937b73acad8b96611c5e2bad4bb812891737a69a` | `423027d461a368c54d0c0fa9497d11fb2efbe473b551b73d787d29c512be967a` |
| `test_operazioni_orphan_operator_r5.py` | `c41b8b47fffb332dc3ae9af9d3bcb7b30a57bd59` | `d84749110595bad57027a8809f2211f99530e4fcc72f111f4717d190cc82e339` |

## Independently executed gates

Durable evidence directory:
`/home/cbo/.cache/gaia-campaign/20261009-r5-orphan/verifier/`.
Raw logs, commands, exit files, JUnit, coverage, isolated SQLite databases,
cache, AST reports and executable audit/oracle runners are retained there.
Every PASS below is executed independently in this verifier worktree; another
agent's test log is not credited as verifier execution.

| Gate | Independent result | Durable evidence |
| --- | --- | --- |
| Six focused analytics suites | 148 PASS, zero skip/failure/error, 60 warnings, exit0/101.53s | `focused.log`, `focused-junit.xml`, `focused.exit` |
| Entire analytics statements/branches | 661/661 statements, 290/290 branches, 100%, zero missing/partial | `focused-coverage.json`, `coverage-summary.json` |
| Entire new helper statements/branches | 27/27 statements, 10/10 branches, 100%, zero exclusions/missing/partial | `focused-coverage.json` |
| Wider Operazioni | 236 PASS, 14 existing PostgreSQL skips, 86 warnings, exit0/80.95s | `operazioni.log`, `operazioni-junit.xml`, `operazioni-summary.json` |
| Complete backend suite | 6658 PASS, 449 existing skips, 2272 warnings, zero failure/error, exit0/1210.23s | `backend-full.log`, `backend-full-junit.xml`, `backend-full-summary.json`, `backend-full.exit` |
| Persisted differential oracle | 20 before/after cases plus 35 explicit semantic assertions per run, exit0 | `oracle-with-assertions.log`, `oracle-before.json`, `oracle-after.json` |
| Complete AST report | 1669 files, 20286 callable, zero parser/exception errors, exit0 | `after.json`, `after.md`, `report.exit` |
| Independent before/after AST audit | All affected callable records; unchanged-function fingerprints; exact aggregate reduction, exit0 | `metric-audit.json`, `independent-audit.log` |
| Frozen source/protected scope | All source blobs and runtime trees equal; protected diff empty | `contracts-and-objects.json` |
| Complexity ratchet against main55a | PASS, zero findings, exit0 | `ratchet.log`, `ratchet.exit` |
| Global baseline check | FAIL30, Make exit2/scanner1; exact historical objects | `global-findings.json`, `global-check.log`, `global-check.exit` |
| Compile/backend Ruff ratchet | PASS, exit0 | `style.log`, `style.exit` |
| New helper/test formatter | PASS, two files already formatted, exit0 | `format.log`, `format.exit` |
| Whitespace | PASS, exit0 | `diff-check.log`, `diff-check.exit` |

Focused selection is precisely `test_operazioni_analytics.py`,
`test_operazioni_analytics_characterization.py`, `test_operazioni_analytics_r2.py`,
`test_operazioni_fuel_vehicle_r3.py`, `test_operazioni_fuel_related_r4.py` and
`test_operazioni_orphan_operator_r5.py`. Coverage measures both complete modified
runtime files with `--cov-branch --cov-fail-under=100`, not just extracted code.
The two existing defensive `pragma: no cover` markers still exclude four
analytics lines; their exact text and covered exception AST are unchanged.
No marker or exclusion was introduced. Existing JWT short-key warnings remain
visible; no new warning/skip filter was applied.

## Behavioral and structural invariants

The reviewer-authored persisted differential harness was inspected and rerun
independently on the verifier's own database against a callable compiled from
frozen pre-slice Git AST and the actual frozen after route. It seeds81 usage
sessions,12 operators, one assignment and one fuel log. Four date windows and
five anomaly filters give20 whole-response/query/state comparisons. Both runs
also independently execute35 explicit semantic assertions. This is an
independently executed shared harness, not a verifier-authored oracle.

The comparison includes exact complete serialized responses, SQL strings,
bound parameters and execution order; identity-map/persisted snapshots remain
equal, with only SELECTs and no new/dirty/deleted objects. Cases cover nullable,
empty and whitespace-only names; lowercase/outer strip without collapsing
internal spaces or tabs; forward/reverse first-wins collisions; last-wins GAIA
collisions; linked-driver precedence including0; absent linked match falling
back by name; original raw-label fallback; None versus empty string; missing
vehicles; open-status/date boundaries; severity and stable mixed-phase order.
The orphan query intentionally has a lower date bound and no upper date bound,
and the name-candidate SQL still requires `last_name IS NOT NULL`.

Independent AST assertions show all25 ordered `db` calls identical, all seven
other anomaly phases identical, all12 other top-level functions identical,
route signature/decorators and final response constructor identical. Every
unaffected original callable has the same fingerprint and metric tuple. There
is no query, authorization, schema, transaction, rounding or sorting change.
The extraction is confined to one responsibility: orphan operator name indexes
and identity annotations. SQLite equivalence does not certify unavailable
PostgreSQL integration contracts or external services.

## Metrics and residual debt

Before metrics use the current AST engine directly on frozen Git source, with
all28 original and32 final affected callable records retained in
`metric-audit.json`. The affected file records and callable objects exactly
match the author's scoped report. All complete after-report file, callable,
violation, scope, engine, summary and error objects exactly match the reviewer's
independently generated complete report.

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| `anomalies_analytics` cognitive | 361 | 298 | -63 (-17.45%) |
| `anomalies_analytics` cyclomatic | 159 | 137 | -22 |
| `anomalies_analytics` callable LOC | 387 | 372 | -15 |
| `anomalies_analytics` nesting/params | 4/5 | 4/5 | 0 |
| Analytics plus helper cognitive | 943 | 897 | -46 (-4.88%) |
| Analytics plus helper cyclomatic | 578 | 572 | -6 |
| Analytics plus helper callable LOC sum | 1335 | 1355 | +20 |
| Analytics file LOC | 1265 | 1255 | -10 |
| New helper file LOC | 0 | 43 | +43 |
| Total affected file LOC | 1265 | 1298 | +33 |
| Affected callable count | 28 | 32 | +4 |
| Affected callable errors/warnings | 18/13 | 18/13 | 0 |
| Global cognitive | 81365 | 81319 | -46 |
| Global cyclomatic | 83370 | 83364 | -6 |
| Global file LOC | 332248 | 332281 | +33 |
| Global errors/warnings/findings | 1938/2749/4687 | 1938/2749/4687 | 0 |
| Global callable cognitive>300 | 6 | 5 | -1 |
| Global callable cognitive>200 | 17 | 17 | 0 |

Callable LOC sums include nested callables and are reported separately from
file LOC. LOC growth is explicit and is not represented as a LOC improvement.
The net cognitive reduction is46, not the principal's63;17 cognitive points
reside in genuinely small identity helpers:

| New helper | Cognitive | Cyclomatic | LOC | Nesting | Params | Findings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `normalize_orphan_session_name` | 2 | 3 | 2 | 0 | 1 | 0 |
| `_orphan_operator_name` | 0 | 1 | 2 | 0 | 2 | 0 |
| `index_orphan_operator_names` | 6 | 4 | 13 | 3 | 2 | 0 |
| `orphan_operator_identity` | 9 | 8 | 18 | 1 | 3 | 0 |

All helpers remain below warning thresholds. Ordered candidate indexing and
identity resolution are real, separately understandable responsibilities;
there is no relocated mega-function, wrapper laundering or copied phase.
Principal and affected cognitive totals both decrease. Classification:
`IMPROVED`. The principal remains substantially above ordinary error thresholds,
the analytics file remains above LOC threshold and finding counts do not fall.

## Provenance, skips and harness attempts

The global FAIL30 is independently compared as exact finding objects against
`/home/cbo/.cache/gaia-campaign/20261009-r4-fuel/coordinator/final-global-check.json`.
All30 path/symbol/metric/baseline/current tuples also exactly match versioned
`BASELINE_PROVENANCE_2026-10-08.md`:15 `REAL_REGRESSION` and15
`TEST_ONLY_DIVERGENCE`. No baseline update/repair was run. These historical
failures remain separate and are neither absorbed nor reclassified PASS.

All14 wider Operazioni skips require absent `TEST_DATABASE_URL` for disposable
PostgreSQL. Their exact IDs/causes are retained in `operazioni-skips.json` and
JUnit; no skip was added by the slice and skipped contracts are not PASS.
Complete backend JUnit independently confirms7107 collected cases,6658PASS,
449SKIP, zero failures/errors and saved shell exit0. The single original
PID259095/session28090 ran from07:33:58 to07:54:20UTC, with observation waits
and no restart. All exact test IDs/causes are retained in
`backend-full-skips.json`; counts and raw reasons in `backend-full-summary.json`.
Skip groups are447 PostgreSQL contracts, one unavailable OSGeo shapefile fixture
and one unavailable pyproj fallback fixture. The exact PostgreSQL breakdown:

| Missing-service / PostgreSQL contract reason | Count |
| --- | ---: |
| `GAIA_TEST_POSTGRES_URL non configurato` | 161 |
| `GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race` | 120 |
| `Concorrenza verificata su PostgreSQL, non simulata da SQLite` | 2 |
| `Concorrenza reale verificata su PostgreSQL` | 6 |
| `Concorrenza e row lock richiedono PostgreSQL` | 1 |
| `GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza` | 111 |
| `PostgreSQL integration tests require a PostgreSQL DATABASE_URL` | 18 |
| `PostgreSQL integration tests require TEST_DATABASE_URL to be configured` | 14 |
| `GAIA_TEST_POSTGRES_URL not configured` | 12 |
| `TEST_WHATSAPP_POSTGRES_URL requires a disposable PostgreSQL` | 2 |

These447 unavailable PostgreSQL contracts and the two GIS dependency skips
are not treated as exercised behavior. The full run uses `APP_ENV=test`, its
own durable SQLite database/cache and the unchanged repository skip policy:
`pytest -q -rs -o addopts='' --tb=short --junitxml=...` from `backend/`.

Three explained verifier harness attempts are retained in `harness-attempts.md`:
an assertion initially counted four pragma markers instead of two markers/four
excluded lines; global file findings required default `<file>` because they
omit `symbol`; a supplemental SQLite count guessed plural table names.
Corrected audit and count checks pass without changing product source/tests.
Both failed audit tracebacks/exits remain durable. No application test, oracle
or functional failure is hidden by those harness corrections.

Graphify integration refresh and campaign governance remain Coordinator-owned.
No campaign integration, main merge, push or PR is performed by this verifier.
The global goal remains ACTIVE/INCOMPLETE. Separate Capacitas97.52%/FAIL100 and
historical30 issues remain open. All verifier-owned terminal gates are complete;
the available backend suite passes with the explicit service/dependency limits
above. This certifies only the frozen R5 responsibility, not the global campaign.
