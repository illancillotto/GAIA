# Capacitas — Coverage Closure Plan

## Scope and evidence

**PLANNING ONLY** under Coordinator registry authorization `c0a03abd`.
Worktree `GAIA-campaign-20261008-capacitas`, clean preflight HEAD
`60d44529d9746e392150a7d5636df93b430f7291`; merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`.
Own only this untracked report. No runtime/test/config modification, new suite,
commit, integration, ignore, export, instrumentation or baseline update.

Runtime `frontend/src/components/elaborazioni/capacitas-workspace.tsx` is
identical to the authoritative snapshot. Existing AST artifact
`/tmp/p2-capacitas-before.json`: main cognitive472/cyclomatic416/callable LOC2631;
file effective LOC3109, physical lines3270, cognitive sum1099, 251 callables.
These are existing measurements, not a fresh scan or reduction.

Existing V8 evidence `/tmp/p2-capacitas-coverage-final/coverage-final.json`:

| Counter | Covered / total | Missing | Percent |
| --- | ---: | ---: | ---: |
| Statements | 305 / 857 | 552 | 35.58% |
| Branch arms | 263 / 929 | 666 | 28.31% |
| Functions | 46 / 251 | 205 | 18.32% |
| Lines | 288 / 748 | 460 | 38.50% |

Existing execution log `/tmp/p2-capacitas-coverage-final.log`: 19 tests PASS,
but **coverage gate FAIL** on all four100% thresholds. This is not overall
coverage compliance. The file's only direct behavioral suite is
`frontend/tests/unit/campaign-capacitas-batch.test.tsx`; inCASS payload and job
visibility helper tests do not cover its workspace orchestration. Source-text
smoke checks and a parent test mocking the entire workspace are not substitutes.

SHA256 runtime `d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`;
existing suite `4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`;
coverage JSON `57ab4476ec19a7f9f6b6e515e559d5d4036a8f1244035e75de6ac3792c031ff1`.

## Exact uncovered responsibilities

Counters below are **missing / total**, partitioned by source start line.
Implicit branch locations without a line use their containing branch's line;
this preserves all929 arms rather than dropping unlocated else arms.

| Responsibility / physical line band | Statements | Functions | Branch arms |
| --- | ---: | ---: | ---: |
| Date/status display, Terreni completion/errors modals, download:1–255 | 26/40 | 8/10 | 35/39 |
| Terreni/history file readers and CSV/XLSX templates:256–435 | 49/94 | 3/7 | 49/90 |
| Four result shape guards:436–527 | 10/12 | 3/4 | 34/36 |
| Credentials, derived jobs, effects, four monitors:528–946 | 69/253 | 18/36 | 89/166 |
| Mutating commands/manual-history preparation:947–1294 | 193/218 | 32/34 | 76/96 |
| Shell/navigation and Particelle UI:1295–1707 | 42/46 | 31/33 | 96/127 |
| Storico controls/job/result UI:1708–2216 | 61/61 | 46/46 | 92/93 |
| Terreni controls/job UI:2217–2621 | 9/38 | 9/26 | 27/107 |
| inCASS controls/job/result UI:2622–2916 | 30/30 | 25/25 | 94/95 |
| Certificati re-fetch:2917–3034 | 21/21 | 9/9 | 17/18 |
| Anomalie/list/resolve dialog and final shell:3035–3270 | 42/44 | 21/21 | 57/62 |

## Proposed coherent test-only slices

Run sequentially after fresh ownership approval; these are not implementation
assignments. Keep the existing19 cases unchanged. Each slice gets a small
domain-specific spec under `frontend/tests/unit/campaign-capacitas-*`; reserve
any reusable fixture file explicitly before creation. Shared runtime remains
read-only. Never combine all sections into one assertion-free render matrix.

| Priority / slice | Missing behavior and meaningful assertions | Boundaries / fixtures |
| --- | --- | --- |
| C0: credentials and workspace shell | Zero/one/multiple active/inactive credentials; selection preservation across refresh; `initialSection` rerender; embedded/non-embedded shell; six navigable panels; settings open/close | Typed credential factories, actual labels/controls; child modal double exposes its real `open/onClose` contract; ProtectedPage prop contract is not an authorization proof |
| C1: Terreni monitor/actions/reports | Pending→terminal polling opens completion once; manual refresh messages differ from silent refresh; report→failed-item details→close; rerun/delete ordering and matching-row removal; dates absent/invalid/valid; statuses and empty/mixed results | `list/rerun/deleteCapacitasTerreni*`; deferred API promises; terminal/processing/queued_resume fixtures; valid batch `items` with successes and failures; real polling with fake timers |
| C2: Particelle workflow | Create exact numeric/optional flags; rerun refresh; delete removes only target; speed/stop map returned job by ID; busy states; active/done partition, progress/recent items, malformed/null result fallback | `create/list/rerun/delete/patch-speed/stopCapacitasParticelle*`; multiple typed jobs including unmatched IDs; observable labels/payloads rather than snapshots only |
| C3: Storico input/import | Manual delimiters and subject/idxana ordering; real CSV and XLSX first-sheet selection; aliases, optional columns, blank/empty/invalid rows; reset/mode switching; credential/continue-on-error/auto_resume payload; create then refresh order | `createCapacitasAnagraficaHistoryJob`; real XLSX library and generated files; File text/arrayBuffer rejection is a legitimate I/O boundary; deferred create/refresh |
| C4: Storico monitor/results | Active→terminal latest valid result selection; invalid/null result fallback; rerun/delete; item outcome rows/progress; last-job versus stored-result precedence | `list/rerun/deleteCapacitasAnagraficaHistory*`; ordered distinct jobs and results containing processed/imported/skipped/failed plus item outcomes |
| C5: inCASS workflow/queue | Exact sync/harvest integration payloads; zero/nonzero harvest totals; rerun/delete; collapsed/expanded ordering; active-status queue; payment counters, truncated/malformed results;20s versus45s polling at100/101 jobs | `create/list/rerun/deleteCapacitasInCass*`, harvest API; real already-tested payload/visibility helpers; coherent typed job fixtures and deferred calls |
| C6: Certificati re-fetch | Credential null/selected, limit/throttle, clears old result on next run, busy state, remaining_empty tone, auth failure versus ordinary Error/non-Error, retry | `refetchCapacitasCertificatiEmpty`, token getter, error classifier; deferred result and rejection; assert exact payload and UI |
| C7: Anomalie resolution | Load empty/single/plural list; candidates and empty CCO/stati fallback; select→exact resolve payload; success removes only target; false result with/without error; thrown errors; close versus busy state | `listCapacitasParticelleAnomalie`, `resolveCapacitasParticellaFrazione`; typed candidates, multiple anomalies and deferred resolution; do not expose setters |
| C8: Templates/download I/O | Terreni/history CSV and XLSX filenames, MIME/content/header/example data; anchor download; object URL revoked after1000ms, not earlier | Actual template buttons; spy only on browser URL/anchor I/O, inspect Blob/workbook; real XLSX serialization, fake timer for revoke |

Each monitor's own domain slice also covers token missing at mount or vanishing
after mount, authenticated API rejection, Error/non-Error failures, explicit
versus silent refresh, recovery after legitimate token restoration, pending
request ordering, hidden-document polling and unmount cleanup. The existing
Terreni cleanup test does not prove the other three monitor lifecycles.

Use `getStoredAccessToken` and API-module mocks only at their real boundary.
Current mock exports cover only list calls, Terreni creation and error
classification: add explicit mocks for the assigned actions, otherwise Vitest's
missing-export exception can masquerade as a tested business error. No mocked
success may return undefined where the real contract returns a job/result.
Do not mock `usePolling` wholesale, replace JSX implementation, invoke private
closures, extract/export helpers or manufacture React state for coverage.

## Reachable versus defensive branches — critical blocker

Most missing branches are reachable through genuine UI actions, endpoint
failure/unknown `result_json`, token changes and asynchronous ordering. Type
guards at437/449/474/489 can be exercised through supplied API results: null,
array/non-object, individually wrong required field types, valid complete
results, optional values absent/present. Use coherent valid fixtures after a
guard accepts a result; do not cause a downstream crash just to hit a line.

**Do not promise full-file100% branch closure using test-only changes.**
The artifact already has15 missing defensive arms worth separate provenance:

- **9 construction/language-unreachable fallback arms:** branch IDs19/41 at
  lines281/378 (`string.split('.').pop() ?? ''`: split is never an empty array);
  IDs28/29/30/32/34/51/53 at314/315/316/317/318/404/405
  (`headerMap.get(selectedKey) ?? selectedKey`: selected aliases come from the
  same normalized headers that populated the map with string values).
- **6 library-contract-dependent arms:** IDs23/24/45/46 at291/293/388/390
  (`data[0] ?? {}` after nonzero length), IDs27/49 at313/403
  (`data[index] ?? {}` while iterating sheet_to_json output). Validate the
  actual library contract/real supported files before declaring these dead;
  sparse mocked parser arrays are not evidence of reachable user behavior.

These15 are a candidate ledger, not the entire irreducible residue and not new
exclusions. Missing-sheet guards285/382 require a real supported corrupt/empty
workbook example or documented parser behavior, not impossible fabricated
`XLSX.read` output. Resolve-modal `prev ? ... : null` arms at3166/3203/3213/3217/3220
also need real race evidence; unmount/close cannot be assumed to execute every
updater, particularly while closing is disabled during an active request.

No monkeypatch of String/Array/Map, sparse impossible records, fake state,
new ignore, coverage scope change or baseline inflation is acceptable. If
these arms remain unhit after legitimate characterization, **STOP and obtain
a separate Coordinator decision** with proof before any minimal removal of
redundant runtime defenses. That would be a new authorized runtime slice, not
this test-only plan. Until then the largest cognitive472 refactor remains
**BLOCKED_BY_FULL_FILE_COVERAGE**; a strategic target does not override policy.

## Future validation and stop conditions

Only after implementation is separately authorized, run each relevant spec,
then their combined full-file report using the existing include mechanism:

```bash
cd frontend
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-*.test.tsx \
  --maxWorkers=2 --coverage.reportsDirectory=/tmp/capacitas-closure-coverage
```

Ensure include patterns match all newly assigned specs; this command is
**proposed, not executed**. Keep all four thresholds100 and show raw denominator,
missing locations, cumulative delta and per-behavior matrix after each slice.
Test-only slices preserve runtime metrics exactly; run the authoritative
ratchet against merge-base55a1b1, never repair the baseline. Before authorizing
runtime refactoring require genuine full-file statement/branch/function/line
100%, relevant tests/typecheck/smoke and no unexplained new failure. Do not
classify characterization as a complexity improvement.

Graphify orientation attempted through `make graphify-frontend-query`:
exit2, worktree-local frontend graph absent. Prior `/tmp/p2-graphify-orientation.log`
exists but its broad keyword match is not coverage proof. No graph regeneration
or API extraction was needed/authorized for this read-only plan.

Planning stops here: only this report added untracked; runtime/tests unchanged,
no suites rerun, no commit or integration, no fresh coverage/PASS claim.
