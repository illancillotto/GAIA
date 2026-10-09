# R5 orphan-session operators — Independent Integration Review

## Ownership and source boundary

Reviewer writes this report only. Dedicated worktree
`GAIA-campaign-20261009-r5-orphan-review`, branch
`review/complexity-r5-orphan-operators`, clean initial SHA
`e96277c200c16e3f2176a8d4d24de2e8cae6ac1b`; authoritative main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Main dirty concurrent work was not
edited, copied, reset or stashed. Author source may be applied in this worktree
only after explicit Coordinator freeze authorization. No integration, push,
PR or main merge is authorized to the reviewer.

Durable independent evidence:
`/home/cbo/.cache/gaia-campaign/20261009-r5-orphan/reviewer`.
Dependency symlinks are read-only; database, coverage and pytest cache isolated.

## Preventive design review

Conditionally safe single responsibility: truthy-part joined operator names,
ordered requested-name indexes and linked-first orphan identity resolution.
`join(filter(None, (first, last))).strip()` preserves nullable/empty names and
internal whitespace; it must not strip individual parts or collapse spaces.
Ordered `(forward, reverse)` names with `setdefault` preserve first-wins name
collisions. GAIA dictionary comprehension preserves last-wins duplicates and
zero keys. Single-part requested-name join is equivalent to `strip().lower()`
for the declared nullable-string domain.

Linked driver lookup must use `is not None`, with name fallback only when no
linked operator is found. Unmatched raw label stays `session.operator_name or
None`; a matched operator with empty parts retains the empty joined label.
The identity boundary must be narrowly typed, not a generic context/dictionary.
General session-attribution normalization is deliberately not reused.

All query expressions, conditions, execution order and binds remain in the
route, including the missing orphan upper-date bound and `last_name IS NOT
NULL` candidate filter. Severity, hours, IDs, timestamps, labels and stable
sorting are unchanged. Remaining anomaly phases are outside this review slice.
Helpers below warning thresholds and real aggregate reduction are mandatory;
conditional design safety is not final approval or permission to edit runtime.

Preventively reviewed the bounded follow-up shared
`normalize_orphan_session_name(str | None) -> str`, `(name or "").strip().lower()`.
Requested set-comprehension excluding `""` is equivalent to the old raw/strip
predicates on nullable strings. The resolver's old `None` versus new `""`
internal sentinel remains false for the name-lookup guard; unmatched output must
still use the original raw label. This is actual deduplication within the same
identity responsibility. Final metrics and source review remain required.

## Independent source-before baseline

Fresh scoped AST report `before.json`, `before.md`, `before-metrics.log`:

| Scope | Cognitive | Cyclomatic | LOC | Callables |
| --- | ---: | ---: | ---: | ---: |
| `anomalies_analytics` | 361 | 159 | 387 | 1 |
| Entire `analytics.py` | 943 | 578 | 1265 | 28 |

Principal nesting 4, parameters 5. Scoped findings: 19 error, 13 warning,
32 total. These are the current source, not historical global counters.
Complete independent report `before-global.json`/`.md`/`.log`/`.exit` passes
with 1668 files, 20282 callables, 1938 error, 2749 warning and 4687 findings.

Fresh five existing focused suites independently pass **110 tests, zero skips**,
exit 0: `before-tests.log`, `before-tests.exit`, `before-coverage.json`.
Analytics has **673/673 statements, 302/302 branches, 100%**; unchanged vehicle
helper has **20/20 statements, 8/8 branches, 100%**. Four preexisting defensive
analytics exclusions remain unchanged. Existing short synthetic JWT warnings
remain visible. Source-before copy is saved as `before-analytics.py` for AST
and independent differential verification.

Command, from `backend/`, uses the evidence directory as `E`:

```bash
APP_ENV=test DATABASE_URL="sqlite:///$E/before.db" COVERAGE_FILE="$E/before.coverage" \
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
  tests/test_operazioni_analytics.py tests/test_operazioni_analytics_characterization.py \
  tests/test_operazioni_analytics_r2.py tests/test_operazioni_fuel_vehicle_r3.py \
  tests/test_operazioni_fuel_related_r4.py -o cache_dir="$E/before-cache" \
  --cov=app.modules.operazioni.routes.analytics \
  --cov=app.modules.operazioni.routes._fuel_vehicle_metrics --cov-branch \
  --cov-fail-under=100 --cov-report="json:$E/before-coverage.json" \
  --cov-report=term-missing
```

## Independent persisted characterization

Independent persisted oracle `independent_oracle.py` records 20 combinations
of date windows and anomaly filters, with 81 persisted sessions spanning 15
names, nullable/zero/missing/duplicate links, ordered forward/reverse/name
collisions, internal spaces/tabs and candidate last-name null/empty distinctions.
It compares entire responses, SQL statements/binds/order and persisted column
snapshots, asserts read-only statements and no new/dirty/deleted ORM state.
Initial successful source-before: `oracle-before-final.log`/`.exit` **0**.
Final enriched source-before success: `oracle-before-mixed-final.log`,
`oracle-before-mixed-final.exit` **0**, `oracle-before.json` and `oracle.db`.
Persisted assignment and excessive-fuel rows exercise real mixed anomaly phases
and stable severity sorting alongside the orphan data.
First harness attempts failed before route execution because the standalone
environment lacked `JWT_SECRET_KEY`, then seeding lacked required
`start_odometer_km`; failures retained as `oracle-before.log`/`.exit` and
`oracle-before-corrected.log`/`.exit`, both **1**. These were reviewer harness
setup issues, not application failures or passed checks.
An intermediate mixed-fixture attempt used the wrong fuel recorder field;
`oracle-before-mixed.log`/`.exit` **1** retains that harness failure before route
execution, corrected before the final mixed-fixture run.

Independent expected-value assertions also pass (`oracle-before-assertions.log`
and `.exit` **0**): first-wins aliases, last-wins GAIA link, zero IDs, whitespace
preservation, raw label fallback, empty matched label, candidate null last-name
exclusion, lower/cutoff/no-upper bounds, raw timestamps and mixed severity order.
These assertions supplement the differential oracle rather than relying solely
on comparison to the original implementation.

Independent source-before wider selection passes **36 tests, 14 skips**, exit 0:
`before-wide.log`, `before-wide.exit`. All 14 skips explicitly require absent
PostgreSQL `TEST_DATABASE_URL`; they are not counted as PASS. This establishes
the environmental skip baseline before source changes.

## Frozen source and independent review

Coordinator explicitly authorized certification of source
`cd4b11457f2cb3848b87a5c41d110657d8d11d27`, applied by Coordinator in the reviewer
worktree as `912dc84660dd8aa29404689ba78841e19f333f61`. The reviewer did not
reapply or edit application/test source. All five source files independently
match the frozen source byte-for-byte (`source-equality.json`):

- `backend/app/modules/operazioni/routes/analytics.py`
- `backend/app/modules/operazioni/routes/_orphan_session_operators.py`
- `backend/tests/test_operazioni_orphan_operator_r5.py`
- `domain-docs/operazioni/docs/ORPHAN_OPERATOR_REFACTOR_2026-10-09.md`
- `reports/code-quality/SLICE_R5_ORPHAN_OPERATORS_2026-10-09.md`

Reviewed all five files. The four pure helpers share actual orphan identity
work: repeated normalization, truthy-part display joining, ordered name
indexing and linked/name annotation. A two-field `NamedTuple` represents the
returned identity. No generic context, untyped aggregate dictionary, moved
mega-function, phase relocation or artificial wrapper is introduced.

The original 25 database-call AST expressions remain exact in source order.
All seven other anomaly phases, route signature/decorators and final response
constructor are identical. Twelve other top-level functions are AST-identical,
including their nested functions; all 27 other callable metric/fingerprint
records are independently identical (`after-contracts.json`,
`after-metric-audit.json`). Existing tests, protected configuration, baseline,
thresholds, exclusions, tooling and coverage/style gate paths have no diff.
The two defensive pragma expressions/four excluded analytics lines remain
identical; positions shift 386/387/889/890 to 391/392/894/895. No new exclusion,
skip, pragma or ignore is introduced.

The independent persisted after oracle passes all 20 cases against both the
saved original callable and the source-before recorded full results:
`oracle-after.log`/`.exit` **0**, `oracle-after.json`. Exact whole responses,
SQL/binds/order, persisted columns and no writes hold. All 35 independent
expected-value assertion sites pass after as before:
`oracle-after-assertions.log`/`.exit` **0**. This verifies collisions,
normalization, IDs/raw labels and mixed phase/severity ordering in persisted
records rather than inferring them from helper coverage.

## Independent final gates

| Gate | Result | Durable evidence |
| --- | --- | --- |
| Six focused suites | 148 PASS, zero skip/failure/error, exit 0 | `after-tests.log`, `.exit`, `.xml` |
| Entire analytics statements | 661/661, 100% | `after-coverage.json` |
| Entire analytics branches | 290/290, 100%, zero missing/partial | `after-coverage.json` |
| New helper statements / branches | 27/27 and 10/10, 100%, zero exclusions | `after-coverage.json` |
| Unchanged vehicle helper | 20/20 statements, 8/8 branches, 100% | `after-coverage.json` |
| Independent persisted differential | 20/20 full response/SQL/binds/order/state equal | `oracle-after.log`, `.exit`, `.json` |
| Independent semantic assertions | All 35 assertion sites PASS before/after | `oracle-*-assertions.log`, `.exit` |
| Wider API/fuel-card/integration selection | 36 PASS, 14 existing PostgreSQL skips, exit 0 | `after-wide.log`, `.exit`, `.xml` |
| Entire Operazioni suite | 236 PASS, 14 existing PostgreSQL skips, zero failure/error, exit 0 | `after-operazioni-all.log`, `.exit`, `.xml` |
| New persisted source characterization on original callable | 38 PASS, zero skip/failure/error, exit 0 | `original-characterization.log`, `.exit`, `.xml` |
| Fresh scoped and complete AST reports | PASS, exit 0 | `after.json`, `after-global.json`, logs/exits |
| Authoritative merge-base complexity ratchet | PASS, zero findings, exit 0 | `ratchet.log`, `.exit` |
| Backend compile/style ratchet | PASS, exit 0 | `lint.log`, `.exit` |
| Direct Ruff and new-file format check | PASS, exit 0 | `ruff.log`, `.exit`, `format.log`, `.exit` |
| Source equality / AST / protected paths | All checks PASS | `source-equality.json`, `after-contracts.json` |
| Source whitespace | PASS, exit 0 | `diff-check.log`, `.exit` |

Focused after command extends the source-before command with
`tests/test_operazioni_orphan_operator_r5.py` and
`--cov=app.modules.operazioni.routes._orphan_session_operators`, using independent
`after.*` database/coverage/cache/JUnit artifacts. JUnit confirms 148 tests with
zero skipped/error/failure, 100.239 seconds. Whole-file coverage is certified
individually for both modified runtime files, not just their combined percentage.

Wider command uses `tests/test_operazioni.py`, `tests/test_operazioni_api.py`,
`tests/test_operazioni_integration.py`, `tests/test_import_fuel_cards.py`; full
Operazioni command uses `tests/test_operazioni*.py`. Both use separate durable
SQLite databases/cache and `-rs`/JUnit to record skip identities and reasons.
No author results substitute for these independent executions.

Complete Operazioni JUnit confirms 250 collected tests: 236 PASS, 14 skipped,
zero errors/failures, 83.935 seconds. The fourteen skip identities/reasons are
the same preexisting PostgreSQL integration cases as the source-before run.

Independently reran the 38 new persisted author tests against the saved original
`anomalies_analytics` AST via a durable external pytest plugin
`before_candidate_plugin.py`, without any runtime/test edits in the worktree.
The plugin replaces only the in-process callable after collection; the tests'
frozen clock patches the original globals as usual. All 38 cases pass, zero
skips/errors/failures, 20.045 seconds. This verifies that the added expected
response/SQL contracts characterize the original source as well as the candidate.

## Independent final metrics

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive | 361 | 298 | -63 (-17.45%) |
| Principal cyclomatic | 159 | 137 | -22 |
| Principal callable LOC | 387 | 372 | -15 |
| Principal nesting / parameters | 4 / 5 | 4 / 5 | 0 |
| Analytics cognitive / cyclomatic | 943 / 578 | 880 / 556 | -63 / -22 |
| Analytics file LOC | 1265 | 1255 | -10 |
| New helper cognitive / cyclomatic / file LOC | 0 / 0 / 0 | 17 / 16 / 43 | +17 / +16 / +43 |
| Affected cognitive sum | 943 | 897 | -46 (-4.88%) |
| Affected cyclomatic sum | 578 | 572 | -6 |
| Affected file LOC sum | 1265 | 1298 | +33 |
| Affected callable count | 28 | 32 | +4 |
| Affected errors / warnings / findings | 19 / 13 / 32 | 19 / 13 / 32 | 0 |

| New helper | Cognitive | Cyclomatic | LOC | Nesting | Parameters |
| --- | ---: | ---: | ---: | ---: | ---: |
| `normalize_orphan_session_name` | 2 | 3 | 2 | 0 | 1 |
| `_orphan_operator_name` | 0 | 1 | 2 | 0 | 2 |
| `index_orphan_operator_names` | 6 | 4 | 13 | 3 | 2 |
| `orphan_operator_identity` | 9 | 8 | 18 | 1 | 3 |

Every new helper is below every warning threshold and has zero findings.
The principal falls below the desired 300 checkpoint; both primary affected
aggregates decline, with unchanged remaining callable metrics. The real
reduction is not debt transfer. Aggregate LOC grows 33, an explicit cost of
typed shared identity boundaries; neither aggregate LOC nor finding-count
improvement is claimed.

Complete after report independently records 1669 files, 20286 callables,
1938 errors, 2749 warnings, 4687 findings. Before report records 1668 files,
20282 callables with the same finding counts. These are checkpoint counters;
they do not establish completion of strategic campaign targets.

## Decision and residual risk

**APPROVED** exact source `cd4b11457f2cb3848b87a5c41d110657d8d11d27`;
classification **IMPROVED**. All required independent gates are terminal PASS,
with explicit unchanged environmental skips. Principal and primary aggregate
reductions are real, all helpers remain below warnings, source and persisted
SQL/response/ordering/normalization invariants hold, and protected gates remain
unchanged. The only reviewer-owned change is this report; a report-only commit
is authorized. Campaign integration remains a separate Coordinator action.

SQLite fixtures prove bounded behavioral equivalence; the 14 unchanged
PostgreSQL cases remain skipped because `TEST_DATABASE_URL` is unavailable,
not counted as PASS. Full repository backend verification belongs to the final
verifier/Coordinator and is not certified by this focused review. Existing
synthetic JWT warnings remain visible. Principal 298 cognitive/137 cyclomatic
and analytics 1255 effective LOC remain substantial legacy debt.

Graphify refresh belongs to Coordinator after accepted integration. Historical
global 30 divergences and Capacitas 97.52% FAIL100 remain separate and open;
global campaign remains ACTIVE/INCOMPLETE. No baseline repair, coverage waiver,
second phase, integration, push, PR or main merge is performed by the reviewer.
