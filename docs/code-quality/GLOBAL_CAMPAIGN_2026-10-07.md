# GAIA — Global Complexity Refactor Report

Latest authorized follow-up: `ANPR_E2E_FOLLOWUP_2026-10-07.md`. The legacy ANPR
test and disposable E2E environment are repaired; obsolete browser tests and a
separately authorized GIS CSS layout defect are corrected. Full backend now
6361 PASS/448 skipped; rebuilt E2E 52 PASS/7 skipped/zero failures. Earlier
failure tables below preserve the original verification checkpoint, not the
current outcome. Quantitative campaign targets remain unmet.

## Status

**INCOMPLETE / CURRENT RATCHET PASS.** This report consolidates the current slices;
it does not accept the global campaign. The user chose to complete coverage
and gates before expanding the swarm. All nine modified campaign runtime files
now have full-file 100% statement and branch coverage. The three campaign LOC
regressions have subsequently been corrected, one slice at a time, after user
authorization. Each now passes its ratchet against the current merge-base.
The residual worker-test factory wrapper was subsequently removed after user
authorization, retaining every assertion. Its LOC falls 19→17 (main18), and
the global ratchet against main now passes with zero findings. The historical
comparison retains its separate baseline discrepancies. Extended full-suite
verification is recorded separately in `VERIFICATION_2026-10-07.md`.

### Authorized LOC corrections

| Slice | Rejected trial LOC | Corrected LOC | Main LOC | Tests | Full-file coverage | Scoped main ratchet |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Ruolo | 3749 | 3692 | 3694 | 111 PASS | 1860 statements / 722 branches, 100% | PASS |
| Presenze | 533 | 528 | 528 | 83 PASS | 276 statements / 114 branches, 100% | PASS |
| Operazioni | 1909 | 1907 | 1907 | 57 PASS | 788 statements / 208 branches, 100% | PASS |

Ruolo removes fragmented status helpers and unifies duplicate parser paths.
One reused positive-amount predicate remains; the decision order stays visible.
Two legacy errors return relative to the rejected trial, but errors do not
exceed main; cognitive still improves from 1415 to 1403. This tradeoff is
explicit, not hidden as a greater reduction. Presenze separates the workweek
predicate from Saturday eligibility. Operazioni treats latitude/longitude as
one coordinate pair and removes an unnecessary negative guard/continue.
No code relocation, baseline change, new suppression or unrelated cleanup is
used to offset LOC. Existing characterization tests are retained.

Evidence: `/tmp/gaia-ruolo-loc-correction.md`,
`/tmp/gaia-presenze-loc-correction.md`,
`/tmp/gaia-operazioni-loc-final-tests.log`. Ruolo additionally verifies 28,812
status combinations and 1,107 parser values; Presenze 6,250 classifications;
Operazioni 169 coordinate combinations including duplicate IDs.

Earlier checkpoints that withdrew Network/Catasto, reported incomplete coverage,
or described Operazioni as an aggregate cognitive improvement are superseded.
The repeated restores were coordination errors, not Graphify failures. Final
Catasto and Network changes remain present with stable, exclusive ownership.

No commits, baseline updates, threshold changes, exclusions, migrations or
public API changes were made by this campaign. Concurrent unrelated MCP,
autosync, worker and documentation changes are preserved.

## Initial baseline

- Source audit: `/tmp/gaia-complexity-full-2026-10-07.json`.
- Source commit, current HEAD and merge-base with `main`:
  `703f8411871e88e10b1c45151ba035f6b1f35a8f`.
- Additional historical comparison: `6b61fd27d325459866259c4b7cba133e661ea38f`.
- Counts include callable and file-level findings; no exceptions were applied.

## Final baseline

This is a **measured working-tree checkpoint**, not a repaired baseline or a
completed campaign. Current audit after LOC corrections:
`/tmp/gaia-complete-audit.json`. The earlier
`/tmp/gaia-campaign-accepted-final.json` is a superseded checkpoint, not an
acceptance result.
An agent accidentally replaced the tracked JSON report with a two-file report.
It was regenerated globally to verify recovery, then restored to its unchanged
session-entry state to avoid unrelated generated-report churn. The previously
modified tracked Markdown report was preserved. Final global artifacts remain
in `/tmp/gaia-complete-audit.json` and
`/tmp/gaia-complete-audit.md`, not in the historical tracked
report pair.

| Metric | Initial | Current | Delta | Delta % |
| --- | ---: | ---: | ---: | ---: |
| Files | 1645 | 1656 | +11 | +0.67% |
| Callables | 20150 | 20210 | +60 | +0.30% |
| Errors | 1968 | 1961 | -7 | -0.36% |
| Warnings | 2742 | 2747 | +5 | +0.18% |
| Total findings | 4710 | 4708 | -2 | -0.04% |
| Parse errors | 0 | 0 | 0 | — |

## Delta

Whole-tree changes include concurrent work. Campaign-only runtime findings are
**153→146 errors (-4.58%)**, **166→158 warnings (-4.82%)**, total
**319→304 (-4.70%)**. Other changes contribute 13 additional warnings; those
are not campaign achievements or silently accepted campaign regressions.

| Area | Errors before/after | Warnings before/after | Total delta | Total delta % |
| --- | ---: | ---: | ---: | ---: |
| Backend | 1047 / 1040 | 1673 / 1677 | -3 | -0.11% |
| Frontend | 878 / 878 | 882 / 881 | -1 | -0.06% |
| Worker | 43 / 43 | 187 / 189 | +2 | +0.87% |

The next table counts findings by metric, not sums of metric values.

| Metric | Errors before/after | Warnings before/after | Total delta | Total delta % |
| --- | ---: | ---: | ---: | ---: |
| cyclomatic | 709 / 706 | 934 / 935 | -2 | -0.12% |
| cognitive | 512 / 509 | 588 / 588 | -3 | -0.27% |
| loc | 510 / 510 | 577 / 578 | +1 | +0.09% |
| params | 182 / 182 | 516 / 519 | +3 | +0.43% |
| nesting | 36 / 35 | 102 / 102 | -1 | -0.72% |
| useEffect | 10 / 10 | 11 / 11 | 0 | 0% |
| useState | 9 / 9 | 14 / 14 | 0 | 0% |

## Result by module

These are whole-scope counts using the requested ownership prefixes, not only
the edited files. Elaborazioni/Wiki/Worker include unrelated concurrent work.
Prefixes do not partition all runtime; other legacy/frontend paths remain in
the global totals rather than being assigned to Core as a catch-all.

| Module | Error before | Error after | Warning before | Warning after |
| --- | ---: | ---: | ---: | ---: |
| Ruolo | 181 | 181 | 268 | 267 |
| Elaborazioni | 222 | 220 | 299 | 303 |
| Presenze | 173 | 173 | 335 | 333 |
| Operazioni | 201 | 201 | 157 | 155 |
| Catasto | 332 | 329 | 390 | 390 |
| GIS | 16 | 16 | 73 | 71 |
| Organigramma | 53 | 53 | 64 | 63 |
| Utenze | 99 | 99 | 126 | 126 |
| Network | 133 | 131 | 94 | 94 |
| Wiki | 176 | 176 | 248 | 255 |
| Worker | 43 | 43 | 187 | 189 |
| Riordino | 37 | 37 | 51 | 51 |
| Inventory / Dotazioni | 1 | 1 | 9 | 9 |
| Accessi | 23 | 23 | 30 | 30 |
| Core / Shared / Search / ME | 21 | 21 | 58 | 58 |

## Ownership and dependencies

The available concurrency limit is coordinator plus three specialists. Work
used exclusive ownership in the existing dirty checkout, not separate branches
or worktrees. Agent roles were reused between batches. Shared configuration,
baseline and unrelated working-tree changes were not assigned to specialists.

| Module | Path / hotspot | Owner role | Dependencies / shared files | State |
| --- | --- | --- | --- | --- |
| Ruolo | `backend/app/modules/ruolo/tributi_repositories.py` | 01 | Utenze read-only | LOC corrected; coverage/main ratchet PASS |
| Elaborazioni | `backend/app/services/elaborazioni_capacitas_incass.py` | 02 | Catasto read-only; worker excluded | inCASS tested; Terreni deferred |
| Presenze | `backend/app/modules/presenze/services/xlsm_export.py` | 03 | Organigramma read-only | LOC corrected; coverage/main ratchet PASS |
| Operazioni | `backend/app/modules/operazioni/routes/mobile_sync.py` | 04 | GATE contract; shared sync untouched | LOC corrected; coverage/main ratchet PASS |
| Catasto | `backend/app/modules/catasto/routes/anomalie.py`, matching helper | 05 | Shared GIS read-only | 305 tests; scoped ratchet passes |
| GIS | `backend/app/modules/gis/services.py` | 06 | Catasto-specific components excluded | 74 tests; scoped ratchet passes |
| Organigramma | `frontend/src/features/organigramma/organigramma-layout-controller.ts` | 07 | Recent workspace slices preserved | 33 tests; controller slice only |
| Utenze | `backend/app/modules/utenze/anpr/service.py` | 08 | Historical namespace compatibility | No runtime edit; baseline test failure |
| Network | `backend/app/modules/network/services.py` | 09 | No Catasto/GIS writes | 253 tests; scoped ratchet passes |
| Wiki | `backend/app/modules/wiki`, `frontend/src/features/wiki` | 10 planned | Core read-only; concurrent MCP work excluded | Deferred |
| Riordino | `backend/app/modules/riordino` | 11 planned | No shared edits | Deferred |
| Worker | `modules/elaborazioni/worker` | 12 planned | Elaborazioni interfaces unchanged | Campaign edits deferred |
| Inventory / Dotazioni | Canonical backend modules; inventory frontend | 13 planned | No shared edits | Deferred |
| Accessi / NAS | Canonical backend module; nas-control frontend | 14 planned | Stable module | Deferred |
| Core / Shared / Search / ME | Canonical modules; frontend lib/hooks/services/types | 15 planned | Explicit per-file lock required | Deferred |

Final read-only review: `/root/presenze_refactor`. Final Catasto owner:
`/root/elaborazioni_refactor`; final Network owner: `/root/operazioni_refactor`.
The LOC correction reuses the Ruolo specialist role and Presenze reviewer as
exclusive owners, sequentially. The Operazioni specialist supplies a read-only
proposal; the coordinator applies its two-line integration correction and
reruns coverage, differential equivalence and ratchets. No ownership overlaps.
All planned specialist roles have not yet been executed; this is not a claim
that the minimum complete swarm campaign has finished.

## Hotspot resolved

No whole mandatory hotspot file is claimed debt-free. The following are measured
local results, separate from overall gate acceptance. File aggregates include
the new Catasto helper, avoiding credit for merely moving complexity.

| Slice | Errors before/after | Warnings before/after | Cognitive sum | Cyclomatic sum | Effective LOC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ruolo tributi | 59 / 59 | 59 / 58 | 1415→1403 | 1203→1195 | 3694→3692 |
| inCASS | 16 / 14 | 21 / 21 | 467→460 | 353→354 | 1116→1126 |
| XLSM | 6 / 6 | 9 / 7 | 213→207 | 161→161 | 528→528 |
| Mobile sync | 22 / 22 | 23 / 21 | 521→521 | 391→392 | 1907→1907 |
| GIS | 14 / 14 | 22 / 20 | 472→458 | 489→480 | 2173→2169 |
| Organigramma controller | 0 / 0 | 4 / 3 | 47→44 | 57→57 | 160→172 |
| Network | 20 / 18 | 14 / 14 | 660→644 | 482→482 | 1454→1451 |
| Catasto route + helper | 16 / 13 | 14 / 14 | 280→226 | 183→173 | 772→795 |
| Campaign total | 153 / 146 | 166 / 158 | 4075→3963 | 3319→3294 | 11804→11840 |

Aggregate cognitive improvement is 112 (-2.75%); cyclomatic improvement is 25
(-0.75%). LOC grows 36 (+0.30%); this is disclosed, not claimed as an
improvement. Operazioni is `REORGANIZED_AND_CHARACTERIZED`, not `IMPROVED`.
The other slices reduce cognitive complexity, but this classification does
not waive the strict no-worsening requirement or the failed gates below.

## Characterization

| Behavior | Preserved contract | Pertinent tests / status |
| --- | --- | --- |
| Ruolo parsing/status | Currency separators, cancellation/payment precedence, repository filtering and persistence | `backend/tests/ruolo/test_tributi_api.py`, added gap characterization; PASS |
| inCASS serialization | Receipt ordering/merge, fallbacks, list filtering and pagination | `test_incass_job_list_serialization.py` plus Capacitas/recovery suites; PASS |
| XLSM paid rest | Contract profile, Saturday presence, five weekdays, inclusive 2280-minute threshold, no carry credit | XLSM-related tests including 11 focused cases; PASS |
| Mobile sync | Coordinate fallback, SQL predicates, attachment errors, status/permissions and side effects | `test_operazioni_mobile_sync_api.py`, `test_operazioni_mobile_sync_unit.py`; PASS |
| GIS permissions | Empty rows and aggregation of persisted non-null Boolean permissions | GIS suite; 1025 baseline/current combinations; PASS |
| Organigramma | Orientation notice, permission guards, layout persistence, refresh and viewport scheduling | `organigramma-layout-controller.test.ts`; horizontal guided case added; PASS |
| Network | SNMP profile order/duplicates, deduplicated defaults, retries/fallbacks, scan/snapshot/alert/device states | New boundaries/persistence tests plus complete Network suite; 176 differential combinations; PASS |
| Catasto | Comune normalization/scoring, empty normalized names, ranking/order, admin guards, wizard queries/side effects | New characterization plus phase1/payload suites; 4320 differential combinations; PASS |

External systems are mocked at transport boundaries. SQLite characterization
does not replace deployment testing with PostgreSQL/PostGIS or live devices.
GIS equivalence assumes the enforced non-null Boolean database invariant;
synthetic permission rows containing `None` are not claimed equivalent.

Operazioni Ruff cleanup adds explicit exception chaining (`raise ... from exc`):
HTTP error contracts are unchanged, but internal tracebacks are not claimed
byte-for-byte identical.

## Tests

| Command / scope | Result | Evidence / limitation |
| --- | --- | --- |
| Ruolo `pytest tests/ruolo/test_tributi_api.py` | 111 PASS | `/tmp/gaia-ruolo-loc-final-tests.log` |
| inCASS Capacitas/list/recovery suites | 209 PASS | `/tmp/gaia-campaign-incass-tests-final.log` |
| Presenze XLSM hours/minutes and schedule engine | 83 PASS | `/tmp/gaia-presenze-loc-after-tests.log` |
| Mobile-sync API/unit suites | 57 PASS | `/tmp/gaia-operazioni-loc-final-tests.log` |
| GIS suite | 74 PASS; independent rerun 88 PASS | `/tmp/gaia-integration-gis-tests.log`; final reviewer report |
| Organigramma controller | 33 PASS | `/tmp/gaia-campaign-organigramma.md` |
| Network `pytest tests/test_network*.py` | 253 PASS | `/tmp/gaia-network-all-tests.log` |
| Catasto phase1/payload/characterization | 305 PASS | `/tmp/gaia-catasto-final-full-tests.log` |
| `cd frontend && npm test` | PASS | `/tmp/gaia-campaign-frontend-smoke.log` |
| `cd frontend && npm run test:unit` | 3986 PASS / 277 files | `/tmp/gaia-campaign-frontend-unit.log` |
| `cd frontend && npm run build:clean` | PASS | Production build completed |
| `make quality-test QUALITY_PYTHON=backend/.venv/bin/python` | 169 PASS | `/tmp/gaia-campaign-quality-tests.log` |
| `BASE_REF=main make lint-backend QUALITY_PYTHON=backend/.venv/bin/python` | PASS | `/tmp/gaia-loc-final-lint.log` |
| `git diff --check` | PASS | No whitespace errors |
| Full backend pytest, final `timeout 2400` run | 6360 PASS, 1 FAIL, 448 skipped | Completes in 21m08s; ANPR legacy failure; `/tmp/gaia-complete-backend-tests.log` |
| Full Playwright suite on temporary local Next | 32 PASS, 19 FAIL, 7 skipped | All failures blocked at login without local backend; `/tmp/gaia-complete-e2e-final.json` |

Full-backend failure independently reproduced with:
`cd backend && timeout 90 .venv/bin/python -m pytest tests/test_anpr_service.py::test_get_stats_reports_deceased_kpis -x -vv -o addopts='' --tb=short`.
It raises `AttributeError: app.modules.utenze.router has no attribute settings`.
The test and router are byte-identical at historical base, HEAD and working
tree; no out-of-scope repair was attempted. The final full-suite rerun finishes
with this as its only failure; earlier timed-out runs are superseded. Skipped
checks remain unvalidated. See `VERIFICATION_2026-10-07.md` for complete commands
and fresh coverage/countercheck evidence.

Worker validation command:
`PYTHONPATH="$PWD" timeout --signal=TERM 600 make test-worker WORKER_PYTHON=backend/.venv/bin/python WORKER_COVERAGE_JSON=/tmp/gaia-campaign-worker-coverage.json WORKER_COVERAGE_XML=/tmp/gaia-campaign-worker-coverage.xml`.
It passes; final rerun has 774 passing tests and one skip across 52 files,
`/tmp/gaia-complete-worker-tests.log`. Initial raw pytest
collection failed due to shared test-module stubs; the first Make attempt
without root PYTHONPATH also failed. These attempts are not passes. Worker
coverage remains approximately 99% (6063 statements, five missing, four partial
branches); there are no campaign worker runtime edits.

## Coverage

All figures are full-file measurements, not changed-line coverage. Existing
coverage exclusions are retained, not expanded. In particular inCASS reports
three pre-existing excluded lines and Ruolo two, disclosed separately from
their 100% results. No new exclusion is introduced by the LOC corrections.

| Runtime file | Statements | Branches | Result | JSON evidence under `/tmp/` |
| --- | ---: | ---: | --- | --- |
| `backend/app/modules/ruolo/tributi_repositories.py` | 1860/1860 | 722/722 | 100% | `gaia-ruolo-loc-final-coverage.json` |
| `backend/app/services/elaborazioni_capacitas_incass.py` | 624/624 | 216/216 | 100% | `gaia-campaign-incass-coverage-final.json` |
| `backend/app/modules/presenze/services/xlsm_export.py` | 276/276 | 114/114 | 100% | `gaia-presenze-loc-after-coverage.json` |
| `backend/app/modules/operazioni/routes/mobile_sync.py` | 788/788 | 208/208 | 100% | `gaia-operazioni-loc-final-coverage.json` |
| `backend/app/modules/gis/services.py` | 1041/1041 | 312/312 | 100% | `gaia-integration-gis-coverage.json` |
| `frontend/src/features/organigramma/organigramma-layout-controller.ts` | 100/100 | 56/56 | 100% | See Organigramma specialist evidence |
| `backend/app/modules/network/services.py` | 807/807 | 290/290 | 100% | `gaia-network-final-coverage.json` |
| `backend/app/modules/catasto/routes/anomalie.py` | 337/337 | 124/124 | 100% | `gaia-catasto-final-full-coverage.json` |
| `backend/app/modules/catasto/services/anomalie_matching.py` | 34/34 | 18/18 | 100% | `gaia-catasto-final-full-coverage.json` |

Older Catasto `accepted-coverage` and intermediate inCASS measurements taken
while sources changed are invalid and superseded by these stable final runs.
Meaningful assertions characterize behavior; percentage alone is not proof
of functional equivalence or complete deployment compatibility.

## Ratchet

**The current global ratchet is PASS; the historical comparison is FAIL.**
Separate references give different results:

1. `BASE_REF=6b61fd27 make complexity-ratchet`: **FAIL**, 21 historical
   mismatches. Actual source at that same commit already has the current
   values for all 21. Nineteen concern registered-mail Ruolo; two concern
   XLSM/inCASS parameter metadata. Detailed evidence:
   `/tmp/gaia-campaign-ratchet-diagnosis.md` and
   `/tmp/gaia-complete-historical-ratchet.log`.
2. `BASE_REF=main make complexity-ratchet`: **PASS**, `findings=[]`, against
   merge-base `703f8411`. Evidence: `/tmp/gaia-complete-main-ratchet.log`.
   The three campaign LOC regressions and the worker test regression are
   eliminated. Separate scoped ratchets for Ruolo, Presenze and Operazioni
   also pass against this same merge-base.

Historical source comparison proves provenance, not a waiver. For example
`count_operai_paid_rest_days(export_row, schedule_context=None)` already has
two parameters at `6b61fd27`, while its stored baseline records one;
`list_incass_sync_jobs(db, *, limit=..., statuses=None)` has three versus one.
Removing parameters or hiding them in kwargs would break or obscure contracts.
All six implicated Ruolo registered-mail callables have identical ASTs at
historical base, HEAD and working tree; chasing their stale numbers is not
legitimate evidence of campaign regression repair.

The current merge-base result cannot be substituted by a scoped historical
PASS. Follow-up reconciliation confirms that all 21 corrected values were
already committed in ancestor `dc669728` and retained in current main; no new
baseline repair is necessary. See
`HISTORICAL_MISMATCH_RECONCILIATION_2026-10-07.md` for the complete provenance
table and counterchecks. No reference change or code compression conceals the
historical failure. The user authorized bounded structural correction
of the three campaign slices; this correction is complete and no other
runtime scope is opened. The user subsequently authorized resolving the worker
finding; only its redundant test factory wrapper was removed, not runtime.

## Architectural changes

Only one new campaign domain runtime file is introduced:
`backend/app/modules/catasto/services/anomalie_matching.py`. It separates
matching/scoring from route orchestration; the existing private normalization
alias remains compatible. No domain is moved to top-level `modules/`.
The inCASS legacy service stays in place to avoid unrelated relocation churn.
No new backend, route, payload, permission model or schema is introduced.

Module code Graphify targets were refreshed (Catasto/Network force-pruned).
GIS uses the backend corpus because no dedicated GIS target exists. The final
backend refresh passes: `/tmp/gaia-campaign-accepted-backend-graph.log`.
Ruolo, Presenze and Operazioni code graphs were force-pruned after the LOC
corrections. Platform documentation refresh evidence is maintained separately
from runtime gates; no graph result substitutes for a test or ratchet.
No generated Graphify output is committed.

## Regression analysis

Characterization, differential checks and focused suites support preservation
of the exercised behavior; they do not justify an unconditional no-regression
claim. The three campaign current-base LOC regressions are corrected; the
worker test regression is also corrected and the current global gate passes.
Full backend and E2E validation is tracked in the verification report.
Reviewer findings and prior superseded
measurements are retained in `/tmp/gaia-campaign-integration.md` and specialist
reports. Final independent review is
`/tmp/gaia-campaign-integration-final.md`; it confirms nine fully covered runtime
files and the three former campaign LOC regressions. Its LOC/coverage numbers
for those three files are superseded by this report's authorized corrections.

## Remaining hotspot

Unresolved mandatory hotspots include Ruolo repositories/tributi page, Capacitas
Terreni/workspace, Presenze giornaliere/gate router, Operazioni analytics/analisi,
Catasto ADE WFS/GIS/MapContainer, Utenze ANPR/detail page, Wiki orchestrator and
frontend. Organigramma workspace was already sliced recently; this campaign
only changed its controller. Existing errors remain in all modified large
backend files. No module-wide zero-error claim is made.

## Open risks

- The three targeted current-base LOC regressions are resolved. Other slices
  still have disclosed aggregate LOC growth or extra base cyclomatic counts;
  this continuation does not claim every campaign metric is reduced.
- Historical mismatch provenance is resolved: the existing `dc669728` repair
  already covers all 21 values. The immutable older comparison remains FAIL;
  this does not justify another baseline regeneration.
- Backend legacy test drift, 448 skipped backend checks and 19 E2E cases
  blocked by missing backend login prevent unconditional functional acceptance;
  both full suite runs finish and their results are recorded.
- Concurrent unrelated changes affect global metrics/gates and require their
  own owners; they must not be overwritten or attributed to this campaign.
- `/tmp` artifacts are local and ephemeral; this document preserves principal
  measured results, commands and limitations but not every raw finding/test log.
- The requested -50% errors / -25% warnings targets are not achieved.

## Recommended next wave

The authorized point 1 and residual current-ratchet correction are complete.
Do not expand the swarm yet: extended validation has finished with disclosed
failures; address ANPR test drift and a disposable E2E backend separately.
Historical mismatch provenance is now reconciled without a new baseline write.
No baseline repair, threshold change or worker
runtime edit is included. See `VERIFICATION_2026-10-07.md` for fresh test and
countertest evidence, including environmental and legacy failures.
