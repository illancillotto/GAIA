# R13 — Capacitas execution controls: distinct final verification

**ACCEPTED / IMPROVED for the bounded R13 slice.** Fresh actual-source focused,
complete coverage, whole frontend units, type/lint/smoke/clean build, immutable
55a ratchet, native Chromium and available E2E executions pass. Full E2E has
seven explicitly recorded historical skips, not seven passes. Global baseline
check remains FAIL30 with every complete finding object unchanged from R12.
Global campaign remains **ACTIVE / INCOMPLETE**, not globally certified.

## Ownership and snapshot

Distinct verifier `/root/r13_final`, allocated before activation in the CURRENT
integration R13 ownership registry. Independent source review9fae accepted;
author and reviewer released the heavy slot before this verifier received it.
Exclusive heavy window, no parallel heavy actor or competing runtime writer.
Only repository write: THIS new report. Source/tests/config/packages/baseline
and all previous reports remain immutable; no commit, staging, integration,
reset, stash, install, baseline generation/repair or threshold/scope change.

Actual worktree `GAIA-campaign-20261009-r13-capacitas-execution-controls-final`,
branch `verification/complexity-r13-capacitas-execution-controls`, HEAD
`7b5da8e44e14f6d0d2bdf4a4833e54761d40bf56`. Main and merge-base both
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Initial status and diff clean.
Author/reviewer evidence is provenance, never substituted for fresh executions.

| Frozen input | SHA256 |
| --- | --- |
| Actual full workspace | `8111c1a4658055f29a4c0b56fb1113f8b06677f9e1e622e33d596ae3d9514f48` |
| Original R12 Git workspace | `b69cbc44b3c219503c940304ce9c1b335faeb7f3703d7569267ba5104bac555d` |
| Source SLICE report | `ac55ce2a2123b0f56249d836d4f7f6111f301903794b42e5e2705b55918c448c` |
| Independent source review | `9fae887fa4f55c6c2329396781f428d1464c5675a6864c2d718fcc2db847f285` |
| Original public characterization spec | `7154256e379b911e72bcf2324cda9f6b6bf14de31c1f57b3eb36bfbecdea7983` |
| Original characterization report | `6d28e1e448d5d90641e066ea01da2999e44072531749e80df48380af713a89fc` |
| Baseline | `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95` |

Evidence root `E=/home/cbo/.cache/gaia-campaign/20261009-r13-capacitas/verifier`.
Fresh `source-before.json`/`source-after.json` protect ALL3520 tracked paths;
they are byte-exact at terminal, including every original test/report/config.
Shared dirty main binary/status pins remain respectively9f85e574…664b and
0d54d4eb…5e87, independently asserted by `main-integrity.json`.

## Fresh tests and full-file coverage

| Gate | Fresh result |
| --- | --- |
| R13 focused characterization | 16 PASS / 1 spec, zero skips |
| All complete Capacitas characterization | 492 PASS / 21 specs, zero skips |
| Whole frontend unit suite | 4671 PASS / 307 specs, zero skips, 209.89s |
| Actual project TypeScript | Exit0, no diagnostics |
| Explicit original R13 test + setup + actual project roots | Exit0, no diagnostics |
| Workspace + policy + ALL21 specs actual ESLint | Exit0, zero errors/warnings |
| Full frontend lint | Exit0, 35 complete legacy warning objects exact R12 |
| `npm test` smoke | 18 PASS, zero skips |
| Actual `npm run build:clean` | Exit0, fresh OWN ignored `.next` production build |

JUnit audits assert tests/files/failures/errors/skips. Coverage raw V8 JSON
membership is exactly the TWO COMPLETE runtime files, not changed-line scope;
every statement/function/branch counter positive, no skipped map entries.

| Full runtime file | Statements | Branches | Functions | Lines |
| --- | ---: | ---: | ---: | ---: |
| `capacitas-workspace.tsx` | 718/718 | 778/778 | 249/249 | 625/625 |
| `capacitas-fraction-resolution.ts` unchanged | 9/9 | 6/6 | 6/6 | 8/8 |
| Combined actual | 727/727 | 784/784 | 255/255 | 633/633 |

All dimensions100%. Original union724/804/254/630 from accepted ORIGINAL
characterization, not a new original-runtime run attributed to this verifier.
No test removed/weakened, no denominator/policy/gate/config/ignore change.
Explicit typecheck covers the new spec, not a claim of explicit typing ALL tests.

## Metrics and no laundering

Fresh complete `make complexity-report`:1672files/20316callables/1926errors/
2741warnings/4667findings; parse/exception errors empty. ALL actual file,
callable, violation, summary, scope and engine objects match approved source.
1671 unaffected file records and20067 unaffected callable records exact R12.

| Workspace + unchanged policy | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Cognitive sum / maximum | 871 / 359 | 861 / 347 | -10 / -12 |
| Decisions `sum(cyclomatic-1)` | 762 | 752 | -10 |
| Raw cyclomatic sum / maximum | 1016 / 336 | 1007 / 324 | -9 / -12 |
| Callable LOC sum / maximum | 4615 / 2487 | 4600 / 2455 | -15 / -32 |
| Effective file LOC | 3131 | 3126 | -5 |
| Callables / nesting maximum | 254 / 2 | 255 / 2 | +1 / 0 |
| Error / warning findings | 17 / 16 | 17 / 16 | 0 / 0 |

Principal359→347cognitive (-3.34%),336→324cyclomatic,2487→2455LOC;
new private helper2cognitive/3cyclomatic/17LOC/nesting0/1parameter, no violations.
Aggregate cognitive -1.15%; remaining debt explicitly retained, not closure.
Fresh source AST proof: fourteen distinct allocated decisions become FOUR,
whole combined source census440→430. All four original functional callbacks
and every nonblank source line outside allocated nodes/declarations exact.
Native button/two spans/type/title/description/class/siblings unchanged, direct
`props.onClick`, no wrapper/event layer/hook/state/API/feature/worker coercion.

Important existing scanner limitation:70 ACTUAL AST `useState` calls, not the
31 regex calls in the scanner, unchanged before/after;39 generic calls omitted
by existing tooling. `useEffect`2 and `useReducer`0 unchanged. No scanner,
baseline or metric rule repaired here; no state-concentration reduction claim.

## Native browser and behavior matrix

FRESH final native attempt5, actual production browser/source, BOTH family
orders. Genuine native login and real backend `/auth/me`200. TWO independent
family-order flows,17 assertion groups each;44 trusted native keyboard click
activations,28 Enter/16 Space; keydown-to-click text/order bijection, detail0,
eleven uniquely classified exact-description activations per family per flow.
These are instrumentation/assertion counts, not34 independent tests.

| Behavior | Existing characterization | Fresh native evidence | Result |
| --- | --- | --- | --- |
| Exact four-control button/two-span DOM, title/description/classes and sibling grids | Original R13 16 cases / 1 spec | Exact current DOM snapshots at every transition | PASS |
| All four controls Enter AND Space, focus retained, no synthetic dispatch | Native gap explicitly identified by reviewer | Trusted Chromium events, Tab/ShiftTab adjacent focus order, exact native accessible names | PASS |
| All four Boolean configurations in BOTH families | Original R13 payload cases | Full JSON objects and genuine token, no extra fields | PASS |
| Pending create captures old options while current UI is edited | Original R13 deferred cases | Response explicitly held; old payload immutable, no early reload; native edits; captured confirmation then current next payload | PASS |
| Family selection isolation/persistence and unrelated prepared values | Original R13 cross-family cases | Both starting orders, family return/credentials/checkbox state, exact prepared payload fields | PASS |
| Batched updater composition before rerender | Original R13 same-act cases | Fresh unchanged focused/whole union tests; not claimed as simultaneous native keyboard events | PASS |

Twenty-four complete public create payloads audited, six per family per order:
four configurations, captured pending request, subsequent current-form request.
Pending assertions verify list reload occurs AFTER create completion; no early
reload while held; submit disabled while controls remain editable. Zero page
errors. Native time is REAL; no virtual clock, private React state, callback
replacement, fake getter or keyboard `dispatchEvent` used.

Domain credentials/lists/create responses intentionally intercepted with
synthetic data and deferred create completion. Auth/login remain real; this is
UI/HTTP-contract certification, NOT external Capacitas portal/session validation
or a real domain job write. Other synthetic API responses and closed websocket
are disclosed in `native-controls.cjs`; foreign browser origins blocked.

## E2E and skipped cases

Fresh pertinent dashboard/detail4PASS/zero skip/4.990s. Complete existing
frontend E2E61cases:54PASS,7SKIP,0unexpected/0flaky/0retry,72.641s. One worker,
retries0, original90000ms timeout; no timeout/selector/config repository edit.
Every skipped object (file/title/line/reason/annotation), normalized only for
worktree absolute prefix, exact R12. Full raw objects in `e2e-audit.json`.

| Skipped existing scenario | Reason |
| --- | --- |
| `catasto-anagrafica.spec.ts:14` single search | Removed legacy single-search workflow |
| `catasto-drilldown.spec.ts:14` district/parcel detail | No seeded district/shapefile data |
| `catasto-drilldown.spec.ts:52` district/anomaly navigation | No seeded district/shapefile data |
| `gis-territorio.spec.ts:381` console/mobile fit | Optional GIS explicit opt-in absent |
| `gis-territorio.spec.ts:439` map/sheets/print/QGIS | Optional GIS explicit opt-in absent |
| `wiki-mcp-console.spec.ts:3` synthetic console/tool history | Dedicated isolated gateway fixture required |
| `wiki-mcp-preview.spec.ts:3` live synthetic gateway/MCP/model | Explicit synthetic provider fixture required |

These seven scenarios are NOT certified/pass and remain global residual work.
Global backend and worker complete suites are NOT run in this bounded frontend
certification; their final global campaign gates remain due at global closure.

## Ratchet and provenance

Actual `make complexity-ratchet BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2`
PASS0, baseline_commit55a/findings[]. Full actual context, not overlay/scoped
comparator or changed BASE_REF to hide a failure. `make complexity-check`
FAIL30, makeexit2/scannerexit1. Every complete object exactly matches frozen
R12 verifier `global-check.json`, not merely the count/path list. None belongs
to this changed workspace; historic MCP/Ruolo/worker-test provenance remains
separate. Baseline byte-exact main55a; no baseline generation/sync/repair,
threshold inflation, broad scope exclusion or ignore.

Dedicated author `make graphify-frontend` source refresh already evidenced
AST650/650 and updated graph; verifier reads its frozen log, NOT claiming a
new verifier graph execution. No source boundary changed during certification,
no raw-root Graphify or graph commit. Coordinator owns closure docs/Graphify.

## Retained attempts and environment

All failures retained, not silently rewritten or declared PASS:

| Attempt | Failure / cause / correction / impact |
| --- | --- |
| Initial focused runner | Exit127 BEFORE collection: dedicated worktree lacked Vitest/node_modules. Explicit Coordinator authorization adds ONLY ignored existing dependency symlink; fresh attempt2 passes. No source failure inferred. |
| Native1 | Exact accessible-name oracle copied from no-layout jsdom concatenation. Compiled block spans produce one separating space in Chromium. Coordinator-authorized external exact-name correction; original title/description/classes/source unchanged. Keyboard not executed. |
| Native2 | Playwright exact `getByLabel` includes option text in wrapping label. Fresh actual ariaSnapshot proves exact combobox name `Credenziale`, original exact-label count0. Coordinator-authorized stronger exact role/name locator, no application fix. Keyboard not executed. |
| Native3 | External instrumentation expected24 rather than actual22. Derivation is11 per family:4 initial+3 configuration+1 preparation+2 pending edit+1 persistence. First-order behavioral assertions ran, whole certificate FAILED; second order not run. Coordinator-authorized exact22 plus trusted keydown/click bijection. |
| Native4 | New broad instrumentation regex `job.` incorrectly classifies Particelle descriptions as Terreni (14 vs11). Exact frozen full-description suffixes independently prove unique11/11; bounded external classifier corrected, no action padding/source change. First-order assertions/bijection ran, whole certificate FAILED. |
| Native5 | FRESH complete BOTH orders PASS with exact unique-description classifier, all invariants and trusted event bijection; this is the native certification result. |
| External capsule collector1 | FileNotFoundError from reading nonexistent `source-proof.json`; fresh source proof actually emits JSON to retained `source-proof.log`. Original direct failure and wrapper-reproduced failure retained; collector filename corrected without rerunning or changing successful source proof/gates. No runtime/test failure. |

Failed native variants1–4 have separate frozen script snapshots, JSON, log,
exit and screenshot. Final results are never substituted into old attempts.
No source/test/config/timeout fixes, waived gate or unexplained runtime failure.
Fresh label-probe and every external script/log are retained in NEW verifier
cache; R12 scaffolding adapted through apply_patch, never old result reuse.

Coordinator-authorized ignored `frontend/node_modules` symlink resolves to
existing main frontend dependencies; NO root symlink/install/dependency source
mutation. Scanner uses `NODE_PATH=/home/cbo/CursorProjects/GAIA/node_modules`.
Installed Vitest4.1.6/coverage4.1.6/TS5.8.3/Next15.5.25/React18.3.1/Playwright1.59.1.
Complete32122 dependency membership/hash inventory differs ONLY in ordinary
Vitest timing-results cache; raw before/after digest recorded. Initial complete
inventory collected after successful focused replay while union running,
not misrepresented as before the first attempted command.

## Isolation, cleanup and reproducibility

Own production Next loopback13044; own loopback proxy18134; unique internal
Docker network `gaia-r13-capacitas-20261009`. Actual backend bind read-only,
SQLite/tmpfs `/e2e`, storage/tmpfs `/data`, no volume, random synthetic secrets
0600, NO production database/portal/shared compose resource. Setup retains
exact image/container/network/mount IDs and commands; backend internal network
blocks portal egress. Before/after shared container/network/volume identities
exact;43 pre-existing containers untouched.

Cleanup verifies Next PID+startTicks+cwd+command and exact created Docker
container/network IDs BEFORE removal. Next terminalexit0, both own containers
and network removed, tmpfs gone, no own volumes, ports13044/18134 free, secret
file deleted. Source3520 hashes exact; only THIS report untracked. Terminal
resource/process audit and final report digest are delivered separately.

Actual command/args/cwd/PID/startTicks/start/end/exit ledger retained in
`*-process.json`/`*-exit.json`, plus gates/audit/metrics/native/E2E/raw coverage/
JUnit/build/lint/cleanup logs, original Git snapshot, pins, capsule and final
resource inventory. `gates.py` serializes actual commands; `run.cjs` refuses
overwriting old logs. Reproduction requires a NEW evidence directory and NEW
owned names/ports, never overwriting these immutable attempts.

```bash
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts \
  npm run test:coverage -- tests/unit/campaign-capacitas- --maxWorkers=1
npm run test:unit -- --maxWorkers=2
npm run typecheck
node "$E/explicit-type.cjs"
./node_modules/.bin/eslint --max-warnings=0 src/components/elaborazioni/capacitas-workspace.tsx \
  src/components/elaborazioni/capacitas-fraction-resolution.ts tests/unit/campaign-capacitas-*.test.ts*
npm run lint && npm test && npm run build:clean
NODE_PATH=/home/cbo/CursorProjects/GAIA/node_modules make complexity-report REPORT_JSON="$E/complexity.json" REPORT_MD="$E/complexity.md"
NODE_PATH=/home/cbo/CursorProjects/GAIA/node_modules make complexity-ratchet BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2
NODE_PATH=/home/cbo/CursorProjects/GAIA/node_modules make complexity-check
node "$E/native-controls.cjs" native-controls-attempt5
PLAYWRIGHT_BASE_URL=http://127.0.0.1:18134 npm run test:e2e -- --config "$E/playwright.config.ts"
```

## Decision and residual risks

Bounded R13 **ACCEPTED / IMPROVED**, ready for Coordinator's sequential exact
source/certificate integration and post-integration ratchet. No integration or
commit delegated here. Principal347 remains extreme,70 actual states remain,
historical30 baseline finding objects and seven skipped E2E cases remain.
Do NOT infer global campaign completion, full external portal equivalence,
all-domain coverage, final global backend/worker suite completion or readiness
of R14 from this certificate. Stop; heavy window released after terminal audit.
