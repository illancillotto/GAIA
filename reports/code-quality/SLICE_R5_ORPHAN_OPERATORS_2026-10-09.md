# R5 Orphan Operator Identity — Complexity Slice Report

## Ownership and authorization

Author `r5_orphan_operators`, worktree
`/home/cbo/CursorProjects/GAIA-campaign-20261009-r5-orphan-operators`, branch
`refactor/complexity-r5-orphan-operators`; clean starting HEAD
`e96277c200c16e3f2176a8d4d24de2e8cae6ac1b`, runtime-equivalent to R4 `b4cfd5cd`.
Authoritative main/merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
The ownership registry was read before changes. Main dirty concurrent work
was not edited, reset, stashed, copied or committed.

Exclusive files are analytics, the new adjacent `_orphan_session_operators.py`,
new `test_operazioni_orphan_operator_r5.py`, the assigned domain note and this
report. No shared documentation, runtime dependency, baseline, threshold,
exclusion, tooling, Makefile or coverage configuration changed.

Coordinator approved the concrete helper/index/identity design before runtime
edits, subject to passing persisted tests on unchanged source. Reviewer
independently accepted the safety conditions. Coordinator separately approved
the bounded shared nullable session-name normalizer after the first candidate.
One coherent campaign source commit is authorized after gates; no source
integration, main merge, push or PR is authorized to this author.

## Baseline and responsibility

Principal `anomalies_analytics`: cognitive361, cyclomatic159, callableLOC387,
nesting4, params5. Whole analytics:28callables, cognitive943, cyclomatic578,
fileLOC1265,19error/13warning findings. The single responsibility is orphan
operator indexing, normalized name matching and identity annotations. All
seven other anomaly phases and all27other analytics callable metrics and AST
fingerprints remain exact.

## Behavioral invariants

- Original25query AST expressions, SQL/binds, conditional query execution and
  phase order remain unchanged. Orphan sessions have no upper date bound;
  name candidates still require SQL `last_name IS NOT NULL`.
- Truthy-part joins preserve lower/strip/join behavior, internal whitespace,
  nullable/empty/whitespace-only parts and original-case matched display.
  No username matching or normalization from generic attribution is added.
- Forward then reverse variants retain first-wins name collisions; linked
  operator indexing retains last-wins GAIA collisions, including integer zero.
  Linked `is not None` precedence and missing-link name fallback remain exact.
- Matched empty names produce an empty label. Unmatched names use the raw
  `session.operator_name or None`; labels, string operator UUIDs, WC IDs,
  timestamps, descriptions,24/48hour boundaries and severity sorting stay exact.
- No writes, identity reconciliation, schema, authentication, transaction,
  threshold, API or UI change. Existing four defensive excluded lines retain
  the same two pragma expressions and are not broadened.

## Persisted characterization

| Contract | Added cases | Exact assertions | Before / after |
| --- | ---: | --- | --- |
| Nullable/empty names, case, raw whitespace, internal spaces/tab, reverse names, last-name SQL filter | 17 | Entire response, SQL/binds/order, record snapshots/no writes | PASS / PASS |
| Forward/reverse name collisions and first candidate | 2 | Both names resolve to earliest candidate | PASS / PASS |
| None/driver/zero/missing links, duplicate GAIA links, nullable/empty matched labels | 16 | Last linked match, linked precedence, fallback, zero retained | PASS / PASS |
|24/48hour boundaries, no upper date bound, closed/fresh/pre-from exclusion, stable ties | 1 | Entire sorted response and query bounds | PASS / PASS |
| Empty orphan population | 1 | Only session SELECT, empty entire response | PASS / PASS |
| Mixed orphan/fuel/unmatched response, label fallback and phase query order | 1 | Entire mixed response and all conditional SELECTs | PASS / PASS |

New38cases PASS on unchanged runtime before edits, exit0. Existing110focused
cases remain unchanged; combined148PASS with no failure/error/skip before and
after. SQLite real persisted ORM records are used, not fake database results.
The frozen clock makes cutoff/boundary assertions exact and deterministic.
All added cases compare the whole response model, compiled SQL with dialect
bind processors, execution order, mapped-column snapshots and no pending writes.

## Implementation

`OrphanOperatorIdentity` is a narrow typed name/string-ID pair. Four small
pure helpers own nullable session-name normalization, candidate truthy-part
display, ordered requested-name indexing and linked/name resolution.
`setdefault` expresses first-wins name collisions without repeated membership
branches. The GAIA dict comprehension expresses the existing last-wins index.
The shared normalizer replaces duplicated route/resolver normalization; the
requested set removes its empty sentinel while unmatched output remains raw.
Queries stay in the route at their original positions. No mega-context,
generic manager, untyped aggregate dictionary or unchanged mega-helper is added.

## Metrics before / after / delta

Complete AST reports in durable author artifacts cover every affected file
and callable, including nested callables. No baseline update was performed.

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Main cognitive | 361 | 298 | -63 (-17.45%) |
| Main cyclomatic | 159 | 137 | -22 |
| Main callableLOC | 387 | 372 | -15 |
| Main nesting / params | 4 / 5 | 4 / 5 | 0 |
| Analytics cognitive sum | 943 | 880 | -63 |
| Analytics cyclomatic sum | 578 | 556 | -22 |
| Analytics fileLOC | 1265 | 1255 | -10 |
| New identity file cognitive / cyclomatic / LOC | 0 / 0 / 0 | 17 / 16 / 43 | +17 / +16 / +43 |
| Affected-file cognitive sum | 943 | 897 | -46 (-4.88%) |
| Affected-file cyclomatic sum | 578 | 572 | -6 |
| Affected-file LOC sum | 1265 | 1298 | +33 |
| Affected-file callable count | 28 | 32 | +4 |
| Affected errors / warnings / findings | 19 / 13 / 32 | 19 / 13 / 32 | 0 |

The LOC tradeoff is explicit: the principal and analytics LOC decline, while
typed helpers and imports add33aggregate effective lines. No LOC improvement
is claimed for the affected set. Both primary aggregates decline; no callable
debt transfers to new helpers, and no new findings are introduced.

### Complete callable metric set

Columns are cognitive/cyclomatic/LOC/nesting/params. All unchanged rows retain
exact metrics and fingerprints; only the principal row differs.

| Analytics callable | Before | After |
| --- | --- | --- |
| `_parse_date` |6/4/7/3/2|same|
| `_period_key` |2/3/6/1/2|same|
| `_user_display_name` |8/9/5/1/1|same|
| `_fuel_average_fields` |3/4/9/0/1|same|
| `_wc_operator_display_name` |7/8/2/0/1|same|
| `_build_session_attribution_context` |10/9/19/2/2|same|
| `_resolve_session_attribution` |3/4/23/1/2|same|
| `available_periods` |9/10/56/1/2|same|
| `analytics_summary` |33/31/95/1/4|same|
| `fuel_analytics` |282/169/350/4/5|same|
| `fuel_analytics._safe_float` |6/5/5/2/1|same|
| `fuel_analytics._avg` |1/2/4/1/1|same|
| `fuel_analytics._metrics_for_logs` |4/5/10/0/1|same|
| `fuel_analytics._related_usage_item` |2/3/14/0/4|same|
| `fuel_analytics._top_stations_for_logs` |13/10/19/1/2|same|
| `fuel_analytics._top_stations_for_logs._score` |1/2/3/0/1|same|
| `fuel_analytics._session_km` |5/5/7/1/1|same|
| `fuel_analytics._target_consumption_l_per_100km` |20/16/17/1/1|same|
| `fuel_analytics._op_display` |17/11/11/2/1|same|
| `fuel_analytics._op_km` |54/24/20/4/1|same|
| `km_analytics` |44/37/137/2/5|same|
| `km_analytics._session_km` |5/5/7/1/1|same|
| `km_analytics._operator_label_for_session` |0/1/2/0/1|same|
| `km_analytics._vehicle_label_for_session` |3/4/3/0/1|same|
| `km_analytics._duration_minutes` |5/5/10/2/1|same|
| `work_hours_analytics` |36/29/105/3/5|same|
| `work_hours_analytics._activity_minutes` |3/4/2/0/1|same|
| `anomalies_analytics` |361/159/387/4/5|298/137/372/4/5|

| New identity helper | After | Findings |
| --- | --- | --- |
| `normalize_orphan_session_name` |2/3/2/0/1|0|
| `_orphan_operator_name` |0/1/2/0/2|0|
| `index_orphan_operator_names` |6/4/13/3/2|0|
| `orphan_operator_identity` |9/8/18/1/3|0|

All new helpers are below warning thresholds, including nesting and params.
Principal298 is below the desired300 checkpoint but remains legacy error debt.

## Tests, coverage and commands

Artifact root:
`/home/cbo/.cache/gaia-campaign/20261009-r5-orphan/author`.
Tests use its isolated SQLite `test.db`, pytest cache and coverage data; shared
`.venv`/`node_modules` symlinks are read-only dependencies, not installation
targets. Logs, JSON, JUnit and exit files are durable, outside volatile `/tmp`.

```bash
DATABASE_URL=sqlite:////home/cbo/.cache/gaia-campaign/20261009-r5-orphan/author/test.db \
PYTHONDONTWRITEBYTECODE=1 \
COVERAGE_FILE=/home/cbo/.cache/gaia-campaign/20261009-r5-orphan/author/.coverage-after \
backend/.venv/bin/python -m pytest -q \
backend/tests/test_operazioni_analytics.py \
backend/tests/test_operazioni_analytics_characterization.py \
backend/tests/test_operazioni_analytics_r2.py \
backend/tests/test_operazioni_fuel_vehicle_r3.py \
backend/tests/test_operazioni_fuel_related_r4.py \
backend/tests/test_operazioni_orphan_operator_r5.py \
-o cache_dir=/home/cbo/.cache/gaia-campaign/20261009-r5-orphan/author/pytest-cache \
--cov=app.modules.operazioni.routes.analytics \
--cov=app.modules.operazioni.routes._orphan_session_operators \
--cov-branch --cov-fail-under=100 \
--cov-report=json:/home/cbo/.cache/gaia-campaign/20261009-r5-orphan/author/coverage-after.json
```

- Before:148PASS,0skip, exit0,95.158s; analytics673/673statements,
  302/302branches100%, four existing excluded lines.
- Final after:148PASS,0skip, exit0,96.489s; analytics661/661statements,
  290/290branches100%, the same four excluded lines; new helper27/27statements,
  10/10branches100%, zero exclusions. Neither file has missing/partial branches.
- Wider Operazioni suite:236PASS,14existing PostgreSQL skips,0failure/error,
  exit0,77.799s;250JUnit cases. Command uses the same isolated database/cache
  and `backend/.venv/bin/python -m pytest -q backend/tests/test_operazioni*.py`.
  All14skips are from unchanged `test_operazioni_integration.py`, explicitly
  requiring unavailable `TEST_DATABASE_URL`; names/reasons are retained in
  `wider.xml`. Skips are not counted as PASS. Existing JWT-key warnings remain.
- `make complexity-ratchet BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python`:
  PASSexit0, `findings=[]`, authoritative merge-base55a. Full report context
  used; no scoped matching shortcut or baseline mutation.
- `make lint-backend BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python`:
  PASSexit0. Direct Ruff check PASS; new runtime/test Ruff format-check PASS.
  `git diff --check` and frozen source SHA256 checks PASS.
- AST invariant audit `source_invariants.py`: PASSexit0,27othercallable metric/
  fingerprint records identical, all7otherphases identical,25queryAST identical,
  signature/decorators and existing defensive pragma expressions identical.
- AST reports `before.json`, `first-after.json`, `after.json`, Markdown/logs
  and `.exit` files all retain executed results, not inferred gate outcomes.

## Attempts and intermediate candidate

1. New38characterizations PASS on original runtime, then combined148and100%
   original analytics coverage PASS before runtime edits. No characterization
   failure, skip or setup retry occurred.
2. First candidate principal301/139/373; combined899cognitive/572cyclomatic/
   1296LOC. New38PASS after, combined148PASS and full-file100% independently
   per runtime: analytics661statements290branches, helper25statements10branches.
   Retained `first-after.json`, `first-source.diff`, coverage and JUnit/logs.
3. Coordinator approved shared nullable-name normalization to remove actual
   duplicated normalization within the same responsibility. Final principal
   298 and aggregate897cognitive are measured, not assumed from that prospect.
4. Some collaboration messages arrived as unreadable encrypted payloads;
   explicit plaintext approval was requested and received before this bounded
   follow-up. Direct collaboration messaging resolved delivery. No failed
   behavioral gate was hidden or bypassed.

No runtime/test/config gate failures occurred in these author attempts. The
wider-suite14existing PostgreSQL skips are recorded explicitly above; no
unexecuted full backend test claim is made by this author.

## Review, classification and residual risk

Classification `IMPROVED`: meaningful principal and affected-file aggregate
cognitive reduction, cyclomatic aggregate decline, zero new helper findings
and full runtime coverage. Added LOC and unchanged legacy finding counts are
explicit tradeoffs, not debt hidden in another module. SQLite characterization
is not a production PostgreSQL validation claim.

Independent reviewer and final verifier remain separate owners; their findings
and source certification determine acceptance. Coordinator owns Graphify module
code/docs and platform docs refresh after integration. No generated graph is
committed by this author.

The principal remains298cognitive/137cyclomatic and the analytics file remains
1255LOC. No second anomaly phase is started. Global goal stays ACTIVE/INCOMPLETE;
historical30global divergences and separate Capacitas97.52%FAIL100remain open
without waiver, attribution change or baseline repair.

Next action: Coordinator accepts or rejects the exact frozen source after
independent review and verification, then integrates only the authorized source
and report commits. The author does not integrate, push or merge main.
