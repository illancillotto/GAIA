# R18 — Original Catasto Comune wizard characterization

Status **TERMINAL / FROZEN — HEAVY RELEASED**. Global campaign **ACTIVE / INCOMPLETE**.
Classification **NO_CHANGE — ORIGINAL_CHARACTERIZED**.
No runtime modification, reduced-complexity claim or full-page100% permission.

## Exclusive ownership and original checkpoint

Author `/root/r17_catasto_cf_original`, now explicitly allocated R18.
Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261008-catasto-ui`, existing
branch `refactor/complexity-catasto-anomalie-ui`; initially clean HEAD
`e885d249d8b54edea33d94f0a04c665db0a52643`. Tracked content is exactly the
certified root `218670c73b7abdcb0210e61ac04e15271c9ebc41` (empty content diff).
Canonical original main/merge-base remains immutable
`55a1b1d35911451e018b662c2acc450bf5994ea2`. R17 author/reviewer/root gates are
terminal, accepted and integrated before this new responsibility was allocated.

The only writable repository files are NEW:

- `frontend/tests/unit/campaign-catasto-comune-wizard-r18.test.tsx`.
- `reports/code-quality/CHARACTERIZATION_R18_CATASTO_COMUNE_WIZARD_2026-10-09.md`.

Runtime, every existing spec/report, config/package/tooling/baseline and tracked
build artifact remain frozen. No CF, Particella, AdE, manual-register expansion
or candidate-matching diagnosis. Those loaders and accepted tests are inputs
only. No author commit/import/merge, cleanup, install or source extraction.

Read-first inputs: R18 integration ownership registry, Coordinator
`CHECKPOINT_R17_CLOSED.md`, checkpoint skill and active project AGENTS/complexity
skill/reference rules already read in this author session. The policy, skill,
README/metrics/validation/ratchet/workflow/constraints/style inputs are unchanged
from that reading; current PROGRESS R17 closure was read afresh. No nested
AGENTS governs the owned frontend/report paths. Root-provided dedicated
`r18-orientation.log` finds the original page/component/getPageCount and is
orientation only; no extraction/refresh ran here.

Fresh post-import protected manifest: **3550 tracked paths**, including
`tsconfig.tsbuildinfo`; `protected-before.sha256` SHA256
`21cf9c0058b82c26c44e3aa4986c0300e8aa081952980105a2fb818194bcb4c1`.
Durable private evidence:
`/home/cbo/.cache/gaia-campaign/20261009-r18-catasto-comune-original/`.
Installed dependencies remain the read-only link to
`/home/cbo/CursorProjects/GAIA/frontend/node_modules`. Low disk capacity
(Coordinator preflight130MiB) forbids cleanup or large new worktrees; stop on
ENOSPC rather than masking any failed command.

## Frozen identities and metric inputs

| Input | SHA256 |
| --- | --- |
| Actual `frontend/src/app/catasto/anomalie/page.tsx` | `855e3ef09296d8024f894118ef6e9c0d6bf13dc63b4f653c6ce6202407a732f7` |
| `config/code-quality/complexity-baseline.json` | `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95` |
| Accepted R17 CF spec | `e4b97fcc3460641482b01f8d6b55b804b1c7f1d374f11b6cb0f60417e98840a2` |
| Accepted R17 CHAR | `b882beec4f3bd094f84f4fa2c973e69e8bdef623d1b61aa8d1ca48b13dca3545` |
| `frontend/src/types/catasto.ts` | `465e28541cb08da065db3f4c466607fe718fe0eb23e89f805e62173ac7bb947c` |
| `frontend/src/lib/api/catasto.ts` | `9c3dabfb8244860bef1f29ecf51a40cd40134aac2fdfbe38deace502742c8938` |
| `frontend/vitest.config.ts` | `01e2dab469c1a961df5d2aa70efcb79e2e6a732be47808f5640a80d77ad61c68` |
| `frontend/tsconfig.json` | `0bee88220b09305239129d1f473ededb1f034c950eaf08933f1a26ebbc86077e` |

The accepted original R17 report/fresh `page-after.json` objects were source-hash
matched preflight inputs. R18 fresh scoped original page AST subsequently
passed; `metric-comparison.json` proves every original file/callable/violation
object exactly equal, no parse/exception errors. Source hash remains855e.

| Metric | Original input | R18 measured runtime delta |
| --- | ---: | ---: |
| Principal cognitive / cyclomatic / callableLOC | 390 / 342 / 2109 | 0 / 0 / 0 |
| Principal nesting / parameters | 2 / 0 | 0 / 0 |
| Principal fingerprint | `9933ead4497cdffc` | unchanged source |
| File cognitive / cyclomatic / weighted decisions | 794 / 868 / 671 | 0 / 0 / 0 |
| File effective LOC / AST callable count | 2267 / 197 | 0 / 0 |
| Scanner useState / useEffect | 24 / 10 | 0 / 0 |
| Error / warning findings | 11 / 16 | 0 / 0 |

## Independently derived Comune contract

`loadComuneWizard` exits before token retrieval when another mode is active,
and before busy/error changes when token is missing. Its public input is open
status, optional numeric year, raw district string, independent local page1
and pageSize25. Overview status/severity/type/page do not select the Comune
query. Context/year/district/tab changes reset local page; page navigation does
not serialize Comune page into the overview URL. Empty later pages with positive
total reset page1 before replacing prior rows/total/drafts. First-page empty
positive-total results do not retry.

Every newly loaded row receives its first response candidate only when its
existing draft is falsey and that first candidate exists; no score sorting.
Radio choices are per anomaly, preserve truthy selections through pending
loads and off-page absence, and affect the literal before/after preview.
Before code uses current/source/nullish-dash precedence, preserving current0.
`Pulisci selezioni` clears the entire draft map; `Seleziona top candidate`
overwrites each current candidate-bearing row with the first candidate and
does not delete drafts for rows without candidates or off-page rows.

Selected count and batch eligibility use truthy draft values for **current
items**, rather than verifying membership in current candidates. Therefore a
retained draft whose candidate disappears has no preview/single button yet
can still enter batch. This original behavior needs explicit observation; the
test does not repair or infer a safer selection rule.

Single apply sends exactly the public preview candidate ID and anomaly ID.
Batch maps current response items in their original order, filters falsey
drafts, and excludes off-page drafts. Both notes derive from the same editable
batch-note field, trimmed on invocation. Default field value is
`Correzione comune batch da console anomalie`; an empty/whitespace field uses
single fallback `Correzione comune da console anomalie` or batch fallback
`Correzione comune batch da console anomalie`. No ID/name inference or candidate
matching diagnosis is involved in these literal request assertions.

Both apply paths recheck token before feedback/state changes, clear prior
success/error before side effect, await mutation, publish literal count text
and then await parallel overview/active- Comune refresh (other wizard guards
stay idle). Loaders catch errors internally, so mutation success can coexist
with a reload error. Mutation failure skips refresh and releases applying ID,
preserving drafts/note. Error objects expose their message; non-Error values
use the distinct existing single/batch/load fallback strings.

During initial load the batch/selection controls are disabled, but note input
is editable. During reload, displayed radio candidates and single apply are
still present; batch and clear/top depend on load busy. Pending single disables
only that row, leaving batch eligible. Pending batch sets scalar `__batch__`,
disabling all single/batch apply controls while clear/top/radio/note stay usable
until reload busy starts. Functional drafts preserve edits during async work.
Original loader closures captured by an apply retain old year/page/mode across
context/tab changes. No response guard/cancellation prevents an older response
overwriting newer rows or an earlier load clearing busy. Single then batch
can overlap; either completion clears the shared scalar applying ID. Tests
photograph these existing transitions; they are not concurrency fixes.

## Original public-UI matrix

**46 cases PASS** on the first focused run and as part of the fresh196-case
union/full-page coverage run; zero skipped/failed cases. Real page, Suspense, state/effects/handlers,
Comune candidates/radios/previews/counts/notes/pagination and messages. Mocked
boundaries are API/auth/navigation, authorization container (props contract
only), and external workspace modals. Literal requests/results/ordering are
derived from the original Comune contract. No wholesale renamed CF spec,
private hook/handler access, exported test controls, synthetic runtime copy,
skip/ignore or fabricated coverage.

| Public responsibility | Cases | Literal oracle | Status |
| --- | ---: | --- | --- |
| Initial request/default candidate/auth shell | 1 | open/undefined context/page1/25; first0.2-score candidate over second0.9; default note | PASS |
| Comune URL entry and explicit manual mode | 3 | workspace/explicit Comune; no load before public tab; VAL-04 URL type | PASS |
| Overview query independence | 1 | open Comune/year2025/district09/page1 versus closed overview/page3 | PASS |
| Initial pending/empty controls | 1 | loading then empty/no pagination; clear/top versus note enablement | PASS |
| No-candidate rows and disabled empty batch | 1 | no preview/single; count0; no mutation | PASS |
| Before-preview nullish code | 3 | null/source91, current0/source91, bothnull/dash | PASS |
| Per-row radio/after preview | 1 | second candidate202; independent second row remains first | PASS |
| Clear/top choice replacement | 1 | empty map/no previews then first candidates overwrite prior second | PASS |
| Pending edits/falsey refill | 1 | latest second retained; cleared row receives new first | PASS |
| Off-page retention/current batch ordering | 1 | page2 com-3 then com-2; com-4 falsey excluded; page1 draft restored | PASS |
| Stale truthy draft/no candidates | 1 | no preview, batchcount1 and old candidate ID still sent; clear removes | PASS |
| Pagination/context/URL separation | 1 | page2 independent URL; year/district/reset return page1 | PASS |
| Later-page recovery and first-page positive empty | 2 | page2→page1 before row replacement; firstpageempty no retry | PASS |
| Load Error/non-Error recovery | 2 | literal error or workspace-comuni fallback; next load clears | PASS |
| Failed reload draft preservation | 1 | second choice/old total remain enabled after error | PASS |
| Initial absent token | 1 | no authenticated request; lookup still runs; Comune empty | PASS |
| Single trim/default-note contract | 3 | selected second ID; custom trim or distinct single fallback | PASS |
| Batch trim/default-note contract | 3 | selected first ID; custom trim or batch fallback | PASS |
| Explicit subset after clear | 1 | only chosen com-2/second sent; count1 | PASS |
| Single captured payload/parallel refresh/busy | 1 | captured first ID/note; pending second choice retained; waits both refreshes | PASS |
| Batch captured payload/controls/refresh | 1 | two first IDs captured; batch locks applies; edits retained/refilled | PASS |
| Single Error/non-Error/retry | 2 | distinct single fallback; no failure refresh; draft/note persist | PASS |
| Batch Error/non-Error/retry | 2 | distinct batch fallback; no failure refresh; successful retry clears | PASS |
| Token lost before single/batch | 2 | existing feedback preserved; no second mutation/busy change | PASS |
| Next apply feedback/zero counts | 1 | prior single success clears before pending batch; zero text literal | PASS |
| Single/batch success plus load failure | 2 | success and Comune reload error coexist, applies released | PASS |
| Overview reload failure and queue removal | 1 | separate overview error plus batch success/empty Comune | PASS |
| Token lost during batch | 1 | success retained; no authenticated refresh | PASS |
| Overlapping response ordering | 1 | newer clears busy; older overwrites while year remains latest | PASS |
| Context changed during batch | 1 | request2025 then captured undefined-year refresh; latest draft/note preserved | PASS |
| Tab exit during single | 1 | captured page2/Comune refresh still runs; reentry page1 clears messages | PASS |
| Single then batch shared busy | 1 | batch allowed during single; single completion enables outstanding batch | PASS |

The handler's zero-selected batch validation is not reachable through the
current public UI: zero selected count disables its only button. Characterize
that disabled control and absence of side effects; do not access the private
handler or manipulate disabled DOM/state to manufacture branch coverage.

## Execution allocation and explained type repair

The initial static allocation executed no heavy check. Coordinator then
explicitly transferred exclusive ORIGINAL heavy after root218 actual postcommit
immutable55a ratchet terminalPASS0, with R19 STATIC ONLY. The current registry
and private `HEAVY_TRANSFER.md` were read before launch. Every executed gate
below is fresh R18; no prior R17 PASS is reused. No build/E2E/full frontend or
global suite, graph refresh, external process/resource or cleanup was allocated.

Focused46, four-spec union196 (P4manual27+utility89+R17CF34+R18Comune46), actual
full-page coverage196 and project type all completed on their first runs.
New-spec type-attempt1 **FAIL2** with ten TS2345 errors because owned `row()`
inferred `Element` from `closest`, whereas Testing Library `within` accepts
`HTMLElement`. The chain stopped before lint/AST/ratchet and preserved raw
`type-new-spec-attempt1.log` plus `STOP_NEW_SPEC_TYPE_ATTEMPT1.md`.

Coordinator inspected the helper/errors and issued a separate explicit registry
allocation for ONLY `closest<HTMLDivElement>("div.rounded-2xl")`. No selector,
assertion, mock, test behavior, cast, ignore, runtime/config/old test changed.
The tiny diff is exactly that type generic. TypeScript5.8.3 transpilation of
original/final spec yields byte-identical JavaScript SHA256
`8fe6fe1822e93614bc133a751bbb9ce0e1ad021fbbceae6231054b53c1928b9a`;
`type-only-runtime-equivalence.json` and both emitted artifacts are retained.
Original tests/coverage remain attributed to spec442a41bc before annotation;
runtime equivalence is proved, not inferred, and no unnecessary test rerun
occurred. New-spec type-attempt2 **PASS0**; initial FAIL2 is not relabeled PASS.
Scoped lint and original AST then passed under that same explicit allocation.

Final spec SHA256:
`63e29633a3733258395e8760739240b1e5c0ca3ce1fa40cf4b7e79a81359273b`.
Frozen initial spec442a41bc is privately retained as
`type-attempt1-original-spec.tsx`; static readiness retains its initial hashes.

Executed command families (working directory frontend unless stated):

```bash
npm run test:unit -- tests/unit/campaign-catasto-comune-wizard-r18.test.tsx --maxWorkers=2 --reporter=default --reporter=junit --outputFile=<private>/focused.junit.xml
npm run test:unit -- tests/unit/campaign-catasto-comune-wizard-r18.test.tsx tests/unit/campaign-catasto-cf-wizard-r17.test.tsx tests/unit/campaign-catasto-anomalie-page.test.tsx tests/unit/catasto-anomalie.test.ts --maxWorkers=2 --reporter=default --reporter=junit --outputFile=<private>/union.junit.xml
VITEST_COVERAGE_INCLUDE=src/app/catasto/anomalie/page.tsx npm run test:coverage -- tests/unit/campaign-catasto-comune-wizard-r18.test.tsx tests/unit/campaign-catasto-cf-wizard-r17.test.tsx tests/unit/campaign-catasto-anomalie-page.test.tsx tests/unit/catasto-anomalie.test.ts --maxWorkers=2 --coverage.reportsDirectory=<private>/coverage --reporter=default --reporter=junit --outputFile=<private>/coverage.junit.xml
npm run typecheck -- --incremental false
node_modules/.bin/tsc -p <private>/tsconfig.new-spec.json --noEmit --incremental false
npm run lint -- --file tests/unit/campaign-catasto-comune-wizard-r18.test.tsx
```

Here `<private>` is the exact durable R18 private directory stated above, not a
repository config/path. Full actual invocations/stdout/stderr remain in logs.
The private new-spec config extends the original project config, includes only
new spec/setup/next-env plus imports, and disables incremental output. Project
type excludes tests, so its PASS0 never substitutes for the separately checked
new spec. Tracked tsbuildinfo/config remain exact.

From worktree root, original page report and authoritative Make ratchet use
`PYTHONDONTWRITEBYTECODE=1 NODE_PATH=/home/cbo/CursorProjects/GAIA/frontend/node_modules`.
Page command is `python3 tools/code_quality/complexity.py report
frontend/src/app/catasto/anomalie/page.tsx --json <private>/page-after.json
--markdown <private>/page-after.md`; Make command is
`make complexity-ratchet BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2`.

## Actual full-file coverage and remaining limits

R18 actual coverage command is **FAIL1** solely because the four unchanged
100% thresholds are unmet; all196 tests PASS. Raw `coverage/coverage-final.json`
contains exactly one source key:
`/home/cbo/CursorProjects/GAIA-campaign-20261008-catasto-ui/frontend/src/app/catasto/anomalie/page.tsx`.
No synthetic source, narrowed-line denominator or threshold override. Skipped
counters are0 in every dimension. `coverage-analysis.json` enumerates all missing
statement IDs/locations, branch ID/arm/type/locations, function IDs/names/locations
and111uncovered lines exactly.

| Actual dimension | Covered / total | Percent | Missing | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Statements | 522 / 643 | 81.18% | 121 | 0 |
| Branch arms | 427 / 645 | 66.20% | 218 | 0 |
| Functions | 148 / 194 | 76.28% | 46 | 0 |
| Lines | 484 / 595 | 81.34% | 111 | 0 |

Source-matched prior R17 union was449/643statement69.82%,342/645arms53.02%,
125/194functions64.43%,416/595lines69.91%; it is historical input, not a fresh
R18 prechange rerun. Remaining page branches include Particella/AdE/batch and
manual/lookup/render fallbacks outside this responsibility. The zero-selection
batch validation lines618/619/620 are explicitly uncovered, along with their
branch arm; a disabled public batch button cannot invoke them. No private
handler call or disabled-control alteration fabricated that missing coverage.
Partial full-page gate remains FAIL and runtime **BLOCKED_COVERAGE**; no waiver.
This static matrix does not certify live API responses, server normalization,
authorization enforcement or browser/E2E behavior.

## Terminal ledger and integrity

| Check | Native session / launch chunk | Exit/result | Raw private evidence |
| --- | --- | --- | --- |
| Focused original Comune | 15109 / c17533 | 0;46PASS/0skip/failure;3.22s | `focused-attempt1.log`, `focused.junit.xml` |
| Four-spec union | 59991 / d42e53 | 0;196PASS/4specs/0skip/failure;5.23s | `union-attempt1.log`, `union.junit.xml` |
| Actual full-page coverage | 23112 / 715ab6 | 1;196PASS;unchanged100%gateFAIL;7.96s | `coverage-attempt1.log`, `coverage.junit.xml`, rawcoverage/analysis |
| Project type | 40253 / 57e7e9 | 0;incrementalfalse | `type-project-attempt1.log` |
| New spec type attempt1 | 11845 / 6739fa | 2;tenTS2345;STOP | `type-new-spec-attempt1.log`, stop note |
| New spec type attempt2, explicit type-only allocation | 58904 / fb5557 | 0;runtime emitted exact | `type-new-spec-attempt2.log`, equivalence/artifacts |
| Scoped final spec lint | 32128 / 1441c9 | 0;no ESLint finding | `lint-attempt1.log` |
| Fresh original page AST | synchronous96747e | 0;every original metric object exact | `page-report-attempt1.log`, page report/comparison |
| Actual immutable55a Make ratchet | 76432 / 7aafd8 | 0;findings[];exact55a baseline_commit | `ratchet-attempt1.log`, `ratchet-result.json` |

Unchanged P4manual `unworked view` DataTable act-warning remains in union/coverage
raw logs; no R18 focused warning/failure. Scoped lint retains Next15 next-lint
deprecation but has no ESLint warning/error. No prior test/runtime was modified
to suppress either message. All **3550 protected tracked paths verify exact**
after terminal gates, including actual source855e, baseline38e6, accepted
P4/R17 tests/reports, packages/config/thresholds and tracked TS buildinfo.
HEAD e885d249/branch unchanged; tracked contents still exactly root218670c7.
Only the two allocated new files are additions, with the explicitly authorized
type annotation as the only spec change after original test execution.
Read-only final main audit preserves HEAD55a, binarydiff SHA256
`9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`
and status SHA256
`0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`,
matching Coordinator's protected concurrent-main checkpoint. No main edit.

All nine gate executions are terminal, including the retained first typeFAIL2
and separate repaired typePASS0. No browser/server/container/credential resource
was created, no dependency install/cleanup/commit/import occurred. Raw failure,
stop/allocation/equivalence and terminal artifacts remain durable. Spec final63e2
and report exact hashes are delivered in the separate private freeze manifest,
avoiding a report self-hash cycle. **Heavy RELEASED**. Independent original
review/replay is a Coordinator decision; no other wizard follow-on here.

Final classification **NO_CHANGE — ORIGINAL_CHARACTERIZED**; partial actual
full-page coverage remains **FAIL100 / runtime BLOCKED_COVERAGE**. No IMPROVED,
runtime permission or strategic campaign completion is claimed.
