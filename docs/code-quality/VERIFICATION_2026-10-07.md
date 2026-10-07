# GAIA — Complexity campaign verification and counterchecks

Follow-up results supersede the ANPR/E2E blockers recorded in this checkpoint:
`ANPR_E2E_FOLLOWUP_2026-10-07.md` documents 6361 backend passes/448 skips,
52 rebuilt E2E passes/7 skips, CSS regression counterchecks and unchanged
complexity baseline. Historical failures below remain as execution evidence.

## Scope

Requested after correction of the three campaign LOC regressions and the
residual worker-test gate. HEAD/main merge-base is `703f8411`; historical
reference is `6b61fd27`. Verification is read-only except removal of the
worker test's redundant factory wrapper and these reports. No runtime,
baseline, threshold or exclusion changes are made during this pass.

The nine campaign runtime files are revalidated with fresh coverage data,
separate temporary databases where applicable, and before/after source hashes.
Concurrent unrelated working-tree changes remain outside campaign ownership.
Raw evidence is under `/tmp/gaia-complete-*`; local artifacts are ephemeral.

## Residual gate correction

In `modules/elaborazioni/worker/tests/test_sister_observability.py`, pass the
`FakeDb` constructor directly instead of a local function returning `FakeDb()`.
The identity assertion compares the received callable with `FakeDb`; recorder
enablement, retention values and purge callback assertions remain unchanged.
No test is removed, weakened or skipped.

- 34 tests pass before and after.
- Callable LOC 19→17 versus main18; cognitive/cyclomatic remain 0/1.
- Ruff and diff-check pass; worker Graphify force pruning passes.
- No worker runtime file is edited by this correction.

## Fresh focused tests and full-file coverage

| Domain | Tests | Statements covered | Branches covered | Result |
| --- | ---: | ---: | ---: | --- |
| Ruolo | 111 | 1860/1860 | 722/722 | 100% |
| inCASS | 209 | 624/624 | 216/216 | 100% |
| Presenze XLSM | 83 | 276/276 | 114/114 | 100% |
| Operazioni mobile sync | 57 | 788/788 | 208/208 | 100% |
| GIS | 88 | 1041/1041 | 312/312 | 100% |
| Organigramma controller | 33 | 100/100 | 56/56 | 100% |
| Network | 253 | 807/807 | 290/290 | 100% |
| Catasto route | 305 shared | 337/337 | 124/124 | 100% |
| Catasto helper | same suite | 34/34 | 18/18 | 100% |

No missing or partial branches. Existing exclusions remain: Ruolo two lines,
inCASS three lines; none is added. Organigramma also covers 22/22 functions and
86/86 lines. Source hashes are unchanged during each measurement.

Specialist evidence and exact commands:

- `/tmp/gaia-complete-network-operazioni-review.md`
- `/tmp/gaia-complete-presenze-gis-org-review.md`
- `/tmp/gaia-complete-domain-review.md`
- `/tmp/gaia-complete-{ruolo,incass,catasto}-command.txt`
- `/tmp/gaia-complete-<domain>-tests.log` and `-coverage.json`

## Behavioral counterchecks

Independent comparisons load original HEAD implementations without replacing
working-tree files. Equality includes outputs and the relevant side effects
or exceptions, not merely execution counts.

| Responsibility | Cases | Result |
| --- | ---: | --- |
| Ruolo status precedence / Decimal exceptions | 28812 | PASS |
| Ruolo amount formats / rounding / failures | 1107 | PASS |
| inCASS receipt merge / ordering / query binds | 384 | PASS |
| Catasto matching / normalized empty names | 4320 | PASS |
| Presenze classifications / Saturday thresholds | 15690 | PASS |
| GIS persisted Boolean permissions | 33825 | PASS |
| Organigramma effects / failures / animation scheduling | 256 | PASS |
| Network SNMP profiles / duplicate and default ordering | 390 | PASS |
| Mobile-sync coordinate boundaries / exceptions / duplicate IDs | 515 | PASS |
| SQLite/PostgreSQL compiled Boolean SQL predicates | 32 | PASS |

The GIS checks apply to persisted non-null Boolean columns, not arbitrary
invalid objects. External transport mocks and SQLite do not replace live
PostGIS, SISTER, device or connector deployment validation. Existing explicit
exception chaining in the mobile-sync diff preserves HTTP errors, not identical
internal traceback text.

An AST countercheck confirms all 161 public function signatures, return
annotations and decorators in the seven existing modified Python runtime files
are identical to HEAD. No migration, threshold or baseline file is changed.

## Global gates

| Command | Result | Evidence |
| --- | --- | --- |
| `BASE_REF=main make complexity-ratchet` | PASS, zero findings | `gaia-complete-main-ratchet.log` |
| `BASE_REF=6b61fd27 make complexity-ratchet` | FAIL, 21 historical mismatches | `gaia-complete-historical-ratchet.log` |
| `make quality-test QUALITY_PYTHON=backend/.venv/bin/python` | 169 PASS | `gaia-complete-quality-tests.log` |
| `BASE_REF=main make lint-backend QUALITY_PYTHON=backend/.venv/bin/python` | PASS | `gaia-complete-backend-lint.log` |
| `cd frontend && npm test` | PASS | `gaia-complete-frontend-smoke.log` |
| `cd frontend && npm run test:unit` | 3986 PASS, 277 files | `gaia-complete-frontend-unit.log` |
| `cd frontend && npm run build:clean` | PASS | `gaia-complete-frontend-build.log` |
| `cd frontend && npm run typecheck:from-root` | PASS | `gaia-complete-frontend-typecheck.log` |
| `cd frontend && npm run lint` | PASS with existing warnings | `gaia-complete-frontend-lint.log` |
| Root Python tests with required PYTHONPATH | 256 PASS | `gaia-complete-root-tests-final.log` |
| Complete worker target | 774 PASS, 1 skipped, 52 files | `gaia-complete-worker-tests.log` |
| Full backend suite | 6360 PASS, 1 FAIL, 448 skipped | `gaia-complete-backend-tests.log` |
| Full Playwright suite on local Next | 32 PASS, 19 FAIL, 7 skipped | `gaia-complete-e2e-final.log` / `.json` |
| Isolated mocked E2E countertest | 15 PASS, 2 skipped | `gaia-complete-e2e-mocked-isolated.log` |

Root tests require
`PYTHONPATH="$PWD/backend:$PWD/modules/elaborazioni/worker:$PWD" backend/.venv/bin/python -m pytest tests -q --tb=short`.
First attempts without all import roots fail collection (`app`, then
`posta_online_client` missing); they are not reported as passing.

Worker command:
`PYTHONPATH="$PWD" timeout --signal=TERM 900 make test-worker WORKER_PYTHON=backend/.venv/bin/python WORKER_COVERAGE_JSON=/tmp/gaia-complete-worker-coverage.json WORKER_COVERAGE_XML=/tmp/gaia-complete-worker-coverage.xml`.
Worker-wide coverage is approximately 99%, not 100%: five missing statements
in unchanged `sister_credential_pool.py` / `sister_retry_metadata.py`, and four
partial branches. Campaign worker runtime is not changed. A trial attempt to
measure the worker test itself with a file path passed to pytest-cov produced
no data and is invalid; a subsequent coverage-run measurement records the
changed test executed, with one unrelated test-helper line unexecuted. This is
not a runtime coverage exclusion or a hidden passing gate.

The complete backend command is
`cd backend && timeout --signal=TERM 2400 .venv/bin/python -m pytest -q -o addopts='' --tb=short`.
It finishes naturally in 1268.58 seconds (21m08s), exit1, with 6360 passed,
448 skipped and one failure: `test_get_stats_reports_deceased_kpis` at
`backend/tests/test_anpr_service.py:1935`, accessing absent
`utenze_router.settings`. This is the previously identified test drift, not a
new campaign failure. The same single test fails independently in 2.08s with
an isolated SQLite URL; test and router are unchanged from HEAD and the
historical reference. Evidence: `/tmp/gaia-complete-anpr-countertest.log` and
`/tmp/gaia-complete-anpr-source-diff.log`. No unrelated ANPR repair is included.
Skipped tests are not passes; environment-dependent PostgreSQL checks remain
unvalidated where skipped. The full suite is NOT classified PASS.

## Ratchet countercheck

The global main ratchet was rerun after the focused checks: PASS again,
`/tmp/gaia-complete-final-main-ratchet.log`, zero findings.

A scoped scan of only XLSM/GIS/Organigramma exits 2 on
`expandedNode:flatTree.find[0]<callback>`, unchanged at line26. The controller
has no entry in the versioned baseline; its simple fingerprint occurs in 121
callbacks elsewhere. The partial scan omits those still-existing paths, making
them appear eligible as removed-path candidates for cross-file matching.

The complete scan retains every such path and passes. All 22 controller
callable records are identical between partial and full scans. A separate
`compare()` run using the complete report and authoritative main baseline also
returns zero findings. Thus the partial command is a documented scope-context
limitation, not a new runtime regression or a reason to alter the callback.
It is not marked PASS. Prefer full scanning followed by report filtering.
Evidence: `/tmp/gaia-complete-matcher-context-review.md`.

Historical mismatches are not repaired in a dirty checkout or hidden by a
reference change. Actual source at `6b61fd27` already has all 21 current values;
the recorded historical baseline differs. No runtime signature changes can
legitimately repair that Git history. Follow-up verification locates all 21
corrected records in existing ancestor `dc669728` and current main; another
repair is unnecessary. See
`HISTORICAL_MISMATCH_RECONCILIATION_2026-10-07.md` for the provenance table,
169 tooling tests and 21 regression-rejection counterchecks. The old
comparison remains FAIL, distinct from the current passing gate.

## Audit

Fresh full audit `/tmp/gaia-complete-audit.json`: 1656 files, 20210 callables,
1961 errors, 2747 warnings, 4708 findings, zero parse errors. Relative to the
original audit: errors -7, warnings +5. Whole-tree warnings include unrelated
concurrent work; campaign-only deltas remain in the global report.

The audit covers all files; file LOC growth in inCASS and the combined Catasto
route/helper is disclosed even when their recorded-baseline ratchet passes.
A gate PASS is not a claim that every source metric decreased.

## Completion boundary

The first full browser run shared Playwright's default artifact directory with
an initial mocked countertest, causing artifact ENOENT errors in addition to
login failures. That was a validation-orchestration mistake, not a product
regression. A complete rerun uses dedicated `/tmp` output and JSON reporting;
only that run is authoritative for final E2E classification. The isolated
mocked countertest also passes independently (15 pass, two skipped).

Final full E2E command, from `frontend/`:
`PLAYWRIGHT_BASE_URL=http://127.0.0.1:8080 PLAYWRIGHT_JSON_OUTPUT_FILE=/tmp/gaia-complete-e2e-final.json timeout --signal=TERM 1000 npm run test:e2e -- --workers=6 --reporter=line,json --output=/tmp/gaia-complete-e2e-final-results`.
It completes in 475 seconds, exit1: 32 pass, 19 fail, seven skipped, no flaky
tests or global runner errors. All 19 failures time out in `page.waitForURL`
after login; `/api/auth/login` on the isolated Next server returns HTTP404
because no backend/proxy is provisioned. This is NOT an E2E PASS and does not
validate those workflows. No real deployment credentials or production writes
are used. The temporary Next process is stopped after validation.

The requested verification pass is finished: current ratchet, focused coverage,
behavioral counterchecks, lint, typecheck and build pass; complete backend and
E2E runs finish with the explicit legacy/environment failures above. No newly
introduced functional failure is identified by these checks, but unavailable
integration scenarios are not proven regression-free.

The larger campaign remains incomplete: quantitative targets and unstarted
domain waves are not achieved. ANPR test drift and a real disposable
backend/proxy for E2E require separate follow-up. Historical mismatch provenance
is now reconciled in the dedicated report; the immutable old gate remains FAIL.
No historical
baseline rewrite or global all-tests-PASS claim is made. No commits are created.
Graphify worker and platform documentation are refreshed using dedicated Make
targets; generated graph files are not committed.
