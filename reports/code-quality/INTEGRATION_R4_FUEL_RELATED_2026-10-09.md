# R4 fuel related usage — Independent Integration Review

## Ownership and snapshot

- Reviewer owns this report only; application and characterization edits belong
  exclusively to the author. No overlapping edits or main integration.
- Clean reviewer branch `review/complexity-r4-fuel-related` initially at
  `ecf15a1ec9840924ee3222daa9cee05e4de5040f`; merge-base/main
  `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Dedicated worktree `GAIA-campaign-20261009-r4-fuel-review`; dirty concurrent
  main remains excluded. Source integration awaits exact-SHA authorization.
- Durable evidence directory:
  `/home/cbo/.cache/gaia-campaign/20261009-r4-fuel/reviewer`.

## Preventive design review

Conditionally approved the coherent shared response responsibility: a narrow
three-key `TypedDict` for nullable rounded averages, consumed by all four
response constructors, plus one shared related-usage constructor replacing the
two identical related schema/totals constructions. Not a generic context or a
relocation of the mega-callable. Helpers must remain below warning thresholds
and aggregate complexity must decrease before an `IMPROVED` classification.

The raw `_metrics_for_logs` arithmetic must remain byte-identical. In related
construction compute raw averages before the original ordered liters/cost sums.
Preserve explicit `None` tests, price precision 4 and cost/liters precision 2,
positive-log metrics versus net-log totals, stable net-liter ranking, top-five
selection, labels and operator identity. Query statements, parameters and their
order remain owned by the original orchestration. No changes to authorization,
route contracts, mutations, schema, baseline, thresholds or coverage config.

## Independent baseline

Fresh complete report: `before.json`, `before.md`, `before.log`, `before.exit`.

| Scope | Cognitive | Cyclomatic | LOC |
| --- | ---: | ---: | ---: |
| `fuel_analytics` | 322 | 183 | 348 |
| Entire `analytics.py` | 978 | 585 | 1250 |

Principal nesting 4 and parameters 5. Global report: 1668 files, 20280
callables, 1938 error, 2749 warning, 4687 findings. Findings are not independent
problem counts; these are a current checkpoint, not the original audit totals.

Fresh existing focused suites before runtime edits: **98 PASS, zero skips**,
exit 0. Full-file analytics coverage **664/664 statements, 302/302 branches,
100%**; existing vehicle helper **20/20 statements, 8/8 branches, 100%**. Zero
missing or partial branches. Four preexisting defensive analytics excluded
lines 369/370/869/870; helper has none. No exclusion was added. Existing short
synthetic JWT warnings were not hidden.

Command from `backend/` (all artifacts under the evidence directory above):

```bash
APP_ENV=test DATABASE_URL=sqlite:////home/cbo/.cache/gaia-campaign/20261009-r4-fuel/reviewer/before.db \
  COVERAGE_FILE=/home/cbo/.cache/gaia-campaign/20261009-r4-fuel/reviewer/before.coverage \
  .venv/bin/python -m pytest -q \
  tests/test_operazioni_analytics.py \
  tests/test_operazioni_analytics_characterization.py \
  tests/test_operazioni_analytics_r2.py \
  tests/test_operazioni_fuel_vehicle_r3.py \
  -o cache_dir=/home/cbo/.cache/gaia-campaign/20261009-r4-fuel/reviewer/before-cache \
  --cov=app.modules.operazioni.routes.analytics \
  --cov=app.modules.operazioni.routes._fuel_vehicle_metrics \
  --cov-branch --cov-fail-under=100 \
  --cov-report=json:/home/cbo/.cache/gaia-campaign/20261009-r4-fuel/reviewer/before-coverage.json \
  --cov-report=term-missing
```

## Exact-source review

Coordinator acknowledges the final design variation: a module-level exact-key
average adapter and a nested four-argument related constructor, with the raw
tuple passed from the original evaluation position. This preserves means
calculation before label lookup and totals, and does not change log traversal.
Preliminary source checks confirm all five DB-call AST expressions, raw metrics
AST and all eleven non-fuel top-level functions are unchanged. These checks are
preliminary until repeated on the frozen source.

Preliminary measured delta is cognitive 322→282 for the main callable and
978→943 across the complete file; cyclomatic 183→169 and 585→578 respectively.
Two small helpers replace duplicated decision/schema logic. LOC grows 348→350
for the main callable and 1250→1265 for the file; callable count grows 26→28.
This is **not** LOC or finding reduction: finding counts remain unchanged.
The extra typed response boundary is an explicit tradeoff for actual cognitive
deduplication, not an undisclosed metric improvement in every dimension.

Source frozen `6b1bec8d98571240c809fdf39f82c65af1c8c04f` was applied only to the
reviewer's dedicated branch as `f14301fdd14e0e407f3f61d66fe5969cc04e54f6`, on
explicit Coordinator authorization. All four source files match the source SHA
byte-for-byte. No application edits were made by the reviewer. Working tree
contains only this owned report. Integration into the campaign branch requires
a separate Coordinator decision; main remains untouched.

Fresh AST checks in `after-contracts.json` confirm the five DB-call expressions,
raw metrics function, and eleven non-fuel top-level functions are unchanged.
Protected config/tooling paths have no diff. Characterization retains exact SQL
statements **and bound parameters**, their order, and read-only identity state.
Stable ranking, top-five truncation, identity, label fallback and four response
levels are tested rather than inferred from helper coverage alone. No existing
test was modified or removed; no skip, pragma or ignore added.

The frozen diff genuinely deduplicates four copies of the three nullable
rounding decisions and two related schema/totals constructions. Related raw
metrics stay at their original caller locations; constructor argument evaluation
keeps labels before length, liters sum, cost sum and average normalization.
Top-entity normalization stays before stations preparation. Both helpers are
small, responsibility-specific, and below every warning threshold; no generic
context, new runtime file, component layering or artificial wrapper.

## Independent final gates

| Gate | Result | Durable evidence |
| --- | --- | --- |
| Five focused characterization suites | 110 PASS, zero skip, exit 0 | `after-tests.log`, `after-tests.exit` |
| Modified analytics full-file statements | 673/673, 100% | `after-coverage.json` |
| Modified analytics full-file branches | 302/302, 100%, zero partial/missing | `after-coverage.json` |
| Unchanged R3 helper | 20/20 statements, 8/8 branches, 100% | `after-coverage.json` |
| Persisted differential comparison | 40/40 entire response + SQL/parameters/order + input snapshots equal | `differential.log`, `differential.exit` |
| Wider Operazioni/API/fuel-card/integration selection | 36 PASS, 14 existing PostgreSQL skips, zero failure, exit 0 | `operazioni.log`, `operazioni.exit` |
| Explicit integration skip rerun | 14 skipped: no `TEST_DATABASE_URL`, exit 0 | `integration-skips.log`, `integration-skips.exit` |
| Complete complexity report | PASS, exit 0 | `after.json`, `after.md`, `after-metrics.log` |
| Main merge-base complexity ratchet | PASS, zero findings, exit 0 | `ratchet.log`, `ratchet.exit` |
| Backend compile/style ratchet | PASS, exit 0 | `lint.log`, `lint.exit` |
| Direct runtime/test Ruff and new-test format | PASS | Independent tool output |
| Frozen source equality and AST contracts | All checks true | `after-contracts.json` |
| Whitespace check | PASS | `git diff --check ecf15a1e HEAD` |

The differential script is the inspected author artifact `author/differential.py`,
executed independently from reviewer backend with `PYTHONPATH=.` and isolated
durable SQLite database. It compiles the original fuel AST from `ecf15a1e`,
without decorators, against identical analytics globals; for forty seeded
persisted fixtures it compares entire Pydantic model dumps, executed SQL/binds,
identity-map columns, and absence of dirty/new/deleted objects. This proves
bounded fixture equivalence, not all PostgreSQL or external production behavior.

Focused after command is the baseline command above using `after.*` artifact
paths and adding `tests/test_operazioni_fuel_related_r4.py`. All commands were
rerun on the exact frozen source, not credited from the author's previous runs.
Wider command uses `tests/test_operazioni.py`, `tests/test_operazioni_api.py`,
`tests/test_operazioni_integration.py`, `tests/test_import_fuel_cards.py` with
its own database/cache. Full repository backend execution belongs to the final
verifier and is not certified by this narrower selection.

Four preexisting defensive analytics excluded lines are unchanged AST with
positions shifted to 386/387/889/890. No exclusions added. Existing synthetic
JWT warnings remain visible. The fourteen PostgreSQL integration cases are
**not PASS**, and this review does not conceal missing environment verification.

## Final measurements

Frozen-source complete reports independently reproduce the preliminary delta:

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Fuel cognitive | 322 | 282 | -40 (-12.42%) |
| Fuel cyclomatic | 183 | 169 | -14 |
| Fuel callable LOC | 348 | 350 | +2 |
| Fuel nesting / parameters | 4 / 5 | 4 / 5 | 0 |
| Entire analytics cognitive | 978 | 943 | -35 (-3.58%) |
| Entire analytics cyclomatic | 585 | 578 | -7 |
| Entire analytics file LOC | 1250 | 1265 | +15 |
| Analytics callables | 26 | 28 | +2 |
| Global error / warning / findings | 1938 / 2749 / 4687 | 1938 / 2749 / 4687 | 0 |

New `_fuel_average_fields`: cognitive 3, cyclomatic 4, LOC 9, nesting 0,
parameters 1. New `fuel_analytics._related_usage_item`: cognitive 2, cyclomatic
3, LOC 14, nesting 0, parameters 4. All other existing callable primary metrics
remain unchanged. `metric-delta.json` records complete affected-callable metrics,
not only the principal. No finding-count or LOC improvement is claimed.

## Decision and residual scope

**APPROVED — IMPROVED**, specifically for cognitive deduplication of the
assigned responsibility, on exact source `6b1bec8d98571240c809fdf39f82c65af1c8c04f`.
The positive LOC tradeoff is bounded, explicitly acknowledged by Coordinator,
and compensated by genuine aggregate cognitive reduction rather than debt
transfer. Main drops below 300 but remains an error-level hotspot at 282;
`anomalies_analytics` and all other phases are untouched.

Graphify refresh and exact campaign integration belong to Coordinator after
acceptance. Global historical 30-finding baseline divergence and Capacitas
97.52% coverage remain separate unresolved items, not exemptions from this
slice's gates. The global campaign remains ACTIVE/INCOMPLETE.
