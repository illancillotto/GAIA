# R4 Fuel Related Mapping — Complexity Slice Report

## Ownership

Author `r4_fuel_related`, exclusive runtime `analytics.py` and new
`test_operazioni_fuel_related_r4.py`, domain note and this report.
Registry `MULTI_AGENT_OWNERSHIP_R4_FUEL_RELATED_2026-10-09.md` precedes edits.
Worktree `GAIA-campaign-20261009-r4-fuel-related`, branch
`refactor/complexity-r4-fuel-related`; initial clean HEAD `ecf15a1e`,
main/merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Main dirty concurrent work is not copied, reset, committed or merged.

After validated runtime/tests/measurements, the author suffered two terminal
upstream session-bridge/503 errors before source freeze. Coordinator explicitly
takes closure ownership for this report/domain note/commit only; no runtime
rework. Independent reviewer/verifier remain mandatory. No simultaneous owner.

## Baseline and target callable

`fuel_analytics`: cognitive322, cyclomatic183, callableLOC348, nesting4,
params5. Analytics file:26callables, cognitive978, cyclomatic585, LOC1250.
One responsibility: shared nullable average fields and related-usage response
mapping, not operator attribution, query redesign or anomalies_analytics.

## Behavioral invariants

- Raw `_metrics_for_logs` stays byte-identical and evaluated at the original
  four orchestration points. Price/cost/liter response precision remains4/2/2.
  Explicit zero/negative values remain distinct from None.
- Related count, liters and cost sums retain traversal order and separate
  left-to-right additions. Positive-only means do not become net means.
- Queries and parameters, call order, top-five related limit, stable net-liter
  ranking/ties, UUID/name/unknown identity and plate/name/id labels unchanged.
- No extra consolidation of vehicle-related operator names; no DB writes,
  transaction, exception, authorization, schema, external-service or UI change.
- Non-fuel functions and the R3 vehicle-consumption helper unchanged.

## Characterization tests

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Positive-only means vs net/storno totals | Analytics/R2/R3 suites | Four response levels together | Five persisted nullable/zero/negative/mixed cases | PASS before/after |
| Related net ranking, stable ties and top5 | Existing general fuel cases | Symmetric focused assertions | Two persisted vehicle/operator ranking cases | PASS before/after |
| Related vehicle label fallback | Existing vehicle coverage | Explicit precedence matrix | Plate/name/id cases | PASS before/after |
| UUID/name/unknown and unconsolidated related keys | Existing consolidation case | Explicit symmetry | Persisted identity assertions | PASS before/after |
| Exact SELECT order/parameters and read-only | Existing query coverage | Exact related-path sequence | SQLAlchemy listener/compiled bind comparison | PASS before/after |

Existing suite98tests independently PASS before edits (reviewer). Author new
characterization brings combined total110tests; 12final cases pass on original
runtime before edits. No existing tests removed, rewritten or skipped.

## Changes

Exact-key `FuelAverageFields` TypedDict defines the three response fields.
Pure `_fuel_average_fields` normalizes them once in a common implementation;
top vehicle/operator and both related responses share it. Nested four-argument
`_related_usage_item` owns common count/net totals/response construction and
receives already-computed raw means to preserve evaluation position. Queries,
identities, ranking and metric calculations remain in their existing phases.
No new runtime file, generic context, manager, exclusion or wrapper mega-helper.

## Metric before / after / delta

Complete author AST reports include all affected callables, not only main.

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Fuel main cognitive | 322 | 282 | -40 (-12.42%) |
| Fuel main cyclomatic | 183 | 169 | -14 |
| Fuel main callableLOC | 348 | 350 | +2 |
| Main nesting / params | 4 / 5 | 4 / 5 | 0 |
| Analytics cognitive sum | 978 | 943 | -35 (-3.58%) |
| Analytics cyclomatic sum | 585 | 578 | -7 |
| Analytics fileLOC | 1250 | 1265 | +15 |
| Analytics callable count | 26 | 28 | +2 |
| Global errors / warnings / findings | 1938 / 2749 / 4687 | 1938 / 2749 / 4687 | 0 |
| Global callable count | 20280 | 20282 | +2 |

New average helper: cognitive3/cyclomatic4/LOC9/nesting0/params1.
New related builder: cognitive2/cyclomatic3/LOC14/nesting0/params4.
Both have zero findings. Removing repeated nullable decisions lowers aggregate
debt rather than transferring it. LOC growth is explicit and bounded, not
classified as a LOC improvement. Global finding counts do not fall and are
not a proxy for independent problems. Main moves below300, not below error.

## Tests and commands

Durable evidence:
`/home/cbo/.cache/gaia-campaign/20261009-r4-fuel/author`.
From backend, isolated SQLite database, coverage and pytest cache in that folder:

```bash
APP_ENV=test DATABASE_URL=sqlite:////home/cbo/.cache/gaia-campaign/20261009-r4-fuel/author/test.db \
  COVERAGE_FILE=/home/cbo/.cache/gaia-campaign/20261009-r4-fuel/author/after.coverage \
  .venv/bin/python -m pytest tests/test_operazioni_analytics.py \
  tests/test_operazioni_analytics_characterization.py tests/test_operazioni_analytics_r2.py \
  tests/test_operazioni_fuel_vehicle_r3.py tests/test_operazioni_fuel_related_r4.py \
  -q -o cache_dir=/home/cbo/.cache/gaia-campaign/20261009-r4-fuel/author/pytest-cache \
  --cov=app.modules.operazioni.routes.analytics --cov-branch --cov-fail-under=100 \
  --cov-report=json:/home/cbo/.cache/gaia-campaign/20261009-r4-fuel/author/after-coverage.json
```

Before/after combined110PASS/zero skip, exit0; logs `before-tests.log` and
`after-tests.log`. Final SQL-parameter characterization12PASS on original
runtime (`before-sql-final.log`, exit0) before runtime changes.
Complete AST before/after via `complexity.py report`: `before.json`/`after.json`,
exit0. `make lint-backend BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python`
PASS; new test Ruff/format checked. `git diff --check` PASS.

Retained `differential.py` runs old callable AST and new callable on40seeded
real-database fixtures with7vehicles,3operators and mixed signed/null/zero
records. Entire response models, SQL strings/parameters/order, identity-map
column snapshots and no pending writes compare equal. Final corrected run
PASS40/exit0 (`differential-final.log`/`.exit`). This is controlled equivalence
evidence, not a PostgreSQL production or nonfinite-persistence claim.

## All attempts, including failures

- Adding exact SQL parameters to the new characterization initially failed
  before runtime edits: test used boolean `or` on a SQLAlchemy bind expression.
  Corrected to explicit None check. Next attempt failed date parameter-format
  comparison: dialect type, not dialect implementation, had been used.
  Final uses `dialect_impl(...).bind_processor(...)`, asserts SQL+parameters
  rather than dropping them, and passes12/12 on unchanged runtime.
- Differential first setup failed import app; subsequent setup failed missing
  test JWT settings. Final script initializes conftest and runs with required
  backend path/test environment; forty comparisons PASS. Original failures
  retained in `differential.log` and `differential-corrected.log`; not PASS.
- Author upstream stream/503 failure occurred after tests/metrics, not a
  behavioral gate. Coordinator closure transfer documented in registry.
- No new test skip, ignore, coverage pragma or baseline change introduced.

## Coverage

Only runtime changed: analytics.py. Before664/664statements,302/302branches;
after673/673statements,302/302branches, both full-file100%, missing lines/
branches empty. Four existing defensive excluded lines move with the source
but remain structurally unchanged; no new exemptions/config/scope changes.
Unchanged R3 fuel helper independently verifies20/20statements8/8branches.
Coverage counters are from whole-file JSON, not percentages averaged by suite.

## Ratchet

`make complexity-ratchet BASE_REF=main`: PASS0/exit0, authoritative merge-base55a.
`ratchet.log`/`.exit` retained. No baseline generation/repair, threshold,
exclusion, coverage configuration or tooling edit. Global30divergences remain
separate; not newly classified PASS here. Independent post-freeze rerun pending.

## Classification

Candidate **IMPROVED**: genuine aggregate cognitive decrease35 with duplicated
mapping removed, not a neutral relocation. Independent acceptance pending;
no integration or global completion claim. FileLOC and callableLOC increase,
and global findings unchanged, explicitly recorded.

## Files changed / commit

- `backend/app/modules/operazioni/routes/analytics.py`
- `backend/tests/test_operazioni_fuel_related_r4.py`
- `domain-docs/operazioni/docs/FUEL_RELATED_REFACTOR_2026-10-09.md`
- This report.

One source commit, retrieve exact SHA via `git log -1 --format=%H --
reports/code-quality/SLICE_R4_FUEL_RELATED_2026-10-09.md`. Runtime SHA256
`7e21f0f8decae49a795c8cd5ecbfd2df0ada48692fd113a905a9d4f50fda2aff`;
test SHA256 `713a4e9b009b3dc3dbafd02e800c59142b00001fe37940d049eb79dadac6bd47`.

## Residual risks / recommended next slice

SQLite tests do not certify PostgreSQL numeric storage/external production.
Full backend/integration suites belong to independent verifier; not run or
claimed PASS by this source report. Graphify code/domain/docs updates belong
to Coordinator after exact integration. No other fuel phase or anomaly work
started. Candidate ends at this responsibility; further reduction needs new
ownership and checkpoint, not extrapolation from this one green focused gate.
