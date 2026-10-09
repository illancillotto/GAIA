# R17 — Original Catasto CF wizard characterization

Status: **TERMINAL / FROZEN — HEAVY RELEASED**. Global campaign **ACTIVE / INCOMPLETE**.
Classification: **NO_CHANGE — ORIGINAL_CHARACTERIZED**. No runtime
change, reduction, full-page coverage claim or runtime authorization.

## Ownership and exact original

Author: `/root/r17_catasto_cf_original`, independently allocated by Coordinator.
Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261008-catasto-ui`; existing
branch `refactor/complexity-catasto-anomalie-ui`; clean initial HEAD
`3b120c3ecfcb8e8b3544a4361ac35a1543a83590`. The tracked content diff against
certified `ca203378` is empty. Original main/merge-base is immutable
`55a1b1d35911451e018b662c2acc450bf5994ea2`.

Only the two new files below are writable:

- `frontend/tests/unit/campaign-catasto-cf-wizard-r17.test.tsx`.
- `reports/code-quality/CHARACTERIZATION_R17_CATASTO_CF_WIZARD_2026-10-09.md`.

Runtime, prior tests/reports, shared sources, packages/config/tooling and
baseline remain read-only. No Comune, Particella or AdE/batch characterization
is allocated. Those inactive loader guards and unrelated initial requests are
observed only as dependencies of CF apply/refresh. No candidate matching
diagnosis, runtime extraction, dependency installation, commit or integration.

Original page SHA256:
`855e3ef09296d8024f894118ef6e9c0d6bf13dc63b4f653c6ce6202407a732f7`.
The fresh post-import protected manifest covers **3541 tracked paths**, including
the tracked `tsconfig.tsbuildinfo`; SHA256
`1e8ee1c87a1e5f4e1213599b23010ea24b538d006205cedb3d546bcdfb99b0a1`.
Private evidence directory:
`/home/cbo/.cache/gaia-campaign/20261009-r17-catasto-cf-original/`.
`protected-before.sha256` and `protected-static-check.log` verify all original
tracked bytes after the test draft. Dependencies are linked to installed
`/home/cbo/CursorProjects/GAIA/frontend/node_modules`, used read-only.

## Read inputs and identity

The author read the R17 ownership registry, root AGENTS, checkpoint/complexity
skills, required policy/workflow/constraints and relevant current/historical
PROGRESS entries. No nested AGENTS exists under the owned frontend/report paths.
PROGRESS is an 8674-line historical ledger; exploration was bounded to current
campaign state and relevant Catasto/P4 entries under checkpoint hygiene.

| Read-only input | SHA256 |
| --- | --- |
| `frontend/src/types/catasto.ts` | `465e28541cb08da065db3f4c466607fe718fe0eb23e89f805e62173ac7bb947c` |
| `frontend/src/lib/api/catasto.ts` | `9c3dabfb8244860bef1f29ecf51a40cd40134aac2fdfbe38deace502742c8938` |
| `frontend/src/components/table/pagination.tsx` | `771d58dbdcd7b111aee9f2e2bb2b7f0a531357cdab9d02b79f35746fc2c550b0` |
| `frontend/src/components/catasto/catasto-page.tsx` | `54ef43ad10f6c0352604d4465ec0cd5d362acb0b9fb7cbc9c96132c7cae26d56` |
| `frontend/src/lib/auth.ts` | `114ed819fc57d0d6bbfb9f242994ce0f0cc6ce4c247a9d84ac91e37258240b1b` |
| Original P4 manual spec | `7f2ae75982efaec902bc584fe6435034d426e0ac231b7fab5b7f13aa0137de23` |
| Original utility spec `catasto-anomalie.test.ts` | `99ab392a3bf6955514b41a2185b85017b9d5e4d01028bce4c0d6b7c34c6b0947` |
| Original P4 report `SLICE_P4_2026-10-08.md` | `49b7b84df6044707b874f97112b1f2b6b2c2bdae052727f37d787d61b22b4918` |
| `frontend/vitest.config.ts` | `01e2dab469c1a961df5d2aa70efcb79e2e6a732be47808f5640a80d77ad61c68` |
| `frontend/package.json` | `f31817e80812eeedb368d6532244609d9fe377a7b5ee1a2e286ec5838d855574` |
| `frontend/package-lock.json` | `99529c27e1d52a92d4f87823b73e7877964fa660ee091d52c4c140581a50ab82` |
| `frontend/tsconfig.json` | `0bee88220b09305239129d1f473ededb1f034c950eaf08933f1a26ebbc86077e` |
| `config/code-quality/complexity-baseline.json` | `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95` |

Local dedicated `make graphify-frontend-query` returned Make exit2 because its
worktree has no `frontend/src/graphify-out/graph.json`. No graph was generated.
Coordinator explicitly allowed the existing integration graph; its dedicated
query evidence in
`/home/cbo/.cache/gaia-campaign/20261009-suites-coordinator/catasto-frontend-query.log`
finds the page, `CatastoAnomaliePageContent()` and `getPageCount()`. It is
orientation only, not metric or behavior proof. This test-only slice changes
no runtime structure, route, service, workflow or module surface; no graph
refresh has run or is claimed.

## Original metrics, fresh source verification

Coordinator permitted reading the exact page objects from its existing
`/home/cbo/.cache/gaia-campaign/20261009-suites-coordinator/complexity.json` after
checking the original source hash. That report records source commit
`429a8a1ebd81e76d5edcc423aab149b27c108200`; no new scanner was executed by the
author during static allocation. After explicit transfer, the fresh scoped
`page-after.json` report and `metric-comparison.json` prove every original
page file/callable/violation object exactly equal, with no parse/exception error.

| Metric | Original | Validated runtime delta |
| --- | ---: | ---: |
| Principal cognitive / cyclomatic | 390 / 342 | 0 / 0 |
| Principal effective LOC / nesting / parameters | 2109 / 2 / 0 | 0 / 0 / 0 |
| Principal AST fingerprint | `9933ead4497cdffc` | unchanged source |
| File cognitive / cyclomatic sum | 794 / 868 | 0 / 0 |
| File cyclomatic minus callable count | 671 | 0 |
| File effective LOC / AST callable count | 2267 / 197 | 0 / 0 |
| Scanner useState / useEffect / imports | 24 / 10 / 25 | 0 / 0 / 0 |
| Error / warning findings | 11 / 16 | 0 / 0 |

## Static behavioral derivation

`loadCfWizard` runs only for active CF mode and a stored token. It requests
`status: "aperta"`, optional numeric year and untrimmed district, local page
and fixed pageSize25. Overview query status/type/severity and URL overview page
do not alter that request. Year/district changes and tab selection reset CF
page; CF pagination does not write the overview URL page. Empty later pages
with positive total reset to page1 before updating items/total/drafts. An empty
first page with positive total is displayed as empty without another request.

Successful loads preserve every existing truthy draft by anomaly ID, including
off-page drafts. Only falsey drafts are filled from nullish suggestion, then
current CF, then empty string. An empty-string suggestion overrides a current
CF. Functional draft updates read edits made while the request is pending.
Typing uppercases immediately without trimming; the suggestion button restores
the raw suggestion. Apply trims and uppercases the captured draft; it checks
only non-emptiness, with no client CF/P.IVA format validation.

`handleApplyCf` rechecks the token before validation or feedback changes. Empty
draft reports the literal validation error and clears success before any API
side effect. Nonempty apply sets the current anomaly ID, clears both feedback
fields and sends one item with the anomaly-specific operator note. A mutation
success publishes counts before parallel overview/CF/inactive loader refresh.
The row stays busy until all refresh promises settle. Loader errors are caught
inside their loaders, so a successful mutation can retain its success message
beside a reload error. Mutation failure skips refresh, preserves drafts and
releases busy. Error objects expose their message; other values use the literal
CF load/apply fallback.

Current asynchronous behavior is deliberately characterized as it is: no
latest-request guard or abort means an older CF response can replace newer
rows, and either load can clear the boolean busy while another is pending.
An apply suspended before a year/tab change retains its original loader
closures, including the original year and active-CF mode on refresh. Inputs
and other row apply buttons remain available while one mutation is pending.
The single applying ID can be replaced by another row; either completion clears
that scalar and can enable the other still-pending row. These are observations
to validate, not fixes or new behavior.

## Validated public-UI matrix

All **34 cases PASS** on first focused execution. They import the actual
original page/Suspense and exercise
real state, effects, handlers, CF inputs, badges, empty state and pagination.
Mocks are API/auth/navigation boundaries, the authorization page container
(props contract only), and external workspace modals. No private handler/hook
access, runtime instrumentation, synthetic source copy, snapshot oracle,
coverage fabrication, skipped tests, ignore or threshold override.

| Responsibility | Cases | Independently derived literal oracle | Status |
| --- | ---: | --- | --- |
| Default load and inactive loaders/auth props | 1 | token/open/undefined context/page1/pageSize25; original roles | PASS |
| Public CF URL initialization/fallback | 4 | default/workspace/explicit CF/unknown-tab fallback select CF | PASS |
| Explicit manual tab then CF entry | 1 | no CF call until CF public tab selected | PASS |
| Query context and overview page independence | 1 | open CF/year2025/district09/page1 versus overview page3/closed | PASS |
| Initial pending load and empty result | 1 | loading text then empty queue/zero count/no pagination | PASS |
| Default draft precedence and metadata rendering | 1 | suggestion/current/empty/null; district0 and absent metadata | PASS |
| Typed edit, raw suggestion, normalized apply | 1 | uppercase edit/raw hint then HINT-LOW and exact note/count text | PASS |
| Pending edit retention and empty-draft refill | 1 | latest PENDING EDIT survives; empty second draft gets new hint | PASS |
| Off-page draft persistence | 1 | same ID restores RETAINED rather than replacement suggestion | PASS |
| Pagination/context reset/URL separation | 1 | CF page2 then year/district/reset page1; no CF URL page update | PASS |
| Later page recovery | 1 | page2 empty positive total then page1 before row replacement | PASS |
| Empty first page with positive total | 1 | 0 rows/total5 and exactly one request | PASS |
| Load Error/non-Error and recovery | 2 | original message/fallback; successful context reload clears error | PASS |
| Failed reload retains draft/rows | 1 | KEPT and original count remain after reload error | PASS |
| Initial missing token | 1 | no authenticated CF/overview/AdE/user call; lookup remains | PASS |
| Empty/whitespace apply validation | 2 | literal validation; no mutation or refresh; enabled button | PASS |
| Token lost before apply | 1 | existing validation unchanged; latest draft/no mutation | PASS |
| Mutation, captured draft, parallel refresh/busy lifecycle | 1 | exact CAPTURED VALUE note; counts precede all refresh completion | PASS |
| Apply Error/non-Error and retry | 2 | message/fallback; preserved RETRY ME; no failure refresh | PASS |
| Success/validation/next-apply feedback transitions | 1 | prior success/error cleared; zero response counts shown literally | PASS |
| CF reload failure after success | 1 | mutation success and CF reload error coexist | PASS |
| Overview reload failure after success | 1 | separate overview error; CF success not relabeled | PASS |
| Missing-CF note and refreshed disappearance | 1 | VAL-03-specific note/12345678901 then empty queue | PASS |
| Token lost while apply pending | 1 | success retained; no new authenticated refresh | PASS |
| Overlapping load completion order | 1 | newer response clears busy; older later replaces newer rows | PASS |
| Year change while apply pending | 1 | request2025 then captured undefined year refresh; field remains2025 | PASS |
| Leaving CF while apply pending | 1 | old captured CF refresh still runs; reentry clears feedback | PASS |
| Concurrent row apply scalar lifecycle | 1 | second row payload; either completion clears scalar busy | PASS |

## Validation allocation and executed commands

At drafting time R16 independent ORIGINAL review owned heavy. Coordinator
later reported its terminal acceptance/release but retained the static hold
while performing sequential integrations and root ratchets. R17 ran no heavy
check during that allocation. Coordinator then explicitly transferred heavy
after integration HEAD `08e85360c581c1005426524d27055af8d4236a51` actual postcommit
ratchet PASS0. Its registry and private `HEAVY_TRANSFER.md` were read before
launch. Every verification below is against the unchanged actual original.

Executed commands from `frontend/` (full stdout/stderr retained privately):

```bash
npm run test:unit -- tests/unit/campaign-catasto-cf-wizard-r17.test.tsx --maxWorkers=2
npm run test:unit -- tests/unit/campaign-catasto-cf-wizard-r17.test.tsx tests/unit/campaign-catasto-anomalie-page.test.tsx tests/unit/catasto-anomalie.test.ts --maxWorkers=2
VITEST_COVERAGE_INCLUDE=src/app/catasto/anomalie/page.tsx npm run test:coverage -- tests/unit/campaign-catasto-cf-wizard-r17.test.tsx tests/unit/campaign-catasto-anomalie-page.test.tsx tests/unit/catasto-anomalie.test.ts --maxWorkers=2 --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261009-r17-catasto-cf-original/coverage
npm run lint -- --file tests/unit/campaign-catasto-cf-wizard-r17.test.tsx
npm run typecheck -- --incremental false
```

Union and coverage runs also used `--reporter=default --reporter=junit` and
`--outputFile` pointing respectively to private `union.junit.xml` and
`coverage.junit.xml`. Project typecheck excludes tests; the separate private
`tsconfig.new-spec.json` extends the original config, includes only the new
spec, original setup and next-env declarations and their runtime imports,
and disables incremental/noEmit output. It was executed with
`node_modules/.bin/tsc -p <private-config> --noEmit --incremental false`: PASS0.
No tracked config or TS build artifact changed.

Fresh page report command from the worktree root:

```bash
PYTHONDONTWRITEBYTECODE=1 NODE_PATH=/home/cbo/CursorProjects/GAIA/frontend/node_modules python3 tools/code_quality/complexity.py report frontend/src/app/catasto/anomalie/page.tsx --json /home/cbo/.cache/gaia-campaign/20261009-r17-catasto-cf-original/page-after.json --markdown /home/cbo/.cache/gaia-campaign/20261009-r17-catasto-cf-original/page-after.md
```

Actual authoritative Make ratchet executed with the same bytecode/dependency
environment and immutable
`BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2`: **PASS0 / findings[]** and
that exact baseline_commit. All command logs, raw
reports/JUnit, private config and metric comparison are retained in the private
directory. No unexpected test/type/lint/scanner failure occurred, no retry,
test fix, source edit or cleanup was needed. Build/E2E and complete frontend
suite were not run for this allocated test-only slice and are not claimed PASS.

## Coverage and remaining limits

Fresh full-file original page coverage run is **FAIL1** against the unchanged
100% thresholds in all four dimensions, while all 150 tests PASS. Raw
`coverage/coverage-final.json` contains exactly one source key:
`/home/cbo/CursorProjects/GAIA-campaign-20261008-catasto-ui/frontend/src/app/catasto/anomalie/page.tsx`.
No source clone, restricted line denominator, skipped counters or threshold
override. `coverage-analysis.json` enumerates every missing statement ID and
location, branch ID/arm/type/location, function ID/name/location and line.

| Actual full-file dimension | Covered / total | Percent | Missing | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Statements | 449 / 643 | 69.82% | 194 | 0 |
| Branch arms | 342 / 645 | 53.02% | 303 | 0 |
| Functions | 125 / 194 | 64.43% | 69 | 0 |
| Lines | 416 / 595 | 69.91% | 179 | 0 |

P4 historical figures were 380/643 statements,261/645 branches,109/194
functions,352/595 lines. The fresh union adds observed coverage, but no fresh
standalone P4 coverage was rerun and no runtime complexity changed. The only
failing verification is the anticipated insufficient-coverage gate; it remains
FAIL, and **runtime refactoring remains BLOCKED_COVERAGE**.

The CF-only matrix leaves Comune/Particella single and batch commands,
candidate selectors, AdE scan/batch workflows and unrelated render/error
branches outside allocation. Uncovered source lines begin at124/127
(other wizard routing),366–441(other loaders),577–748(other mutation/batch
commands), with separate lookup/manual fallbacks and render callbacks from
1323 onward. The complete179line list and all194statement/303branch/69function
locations are archived, rather than inferred from a short terminal summary.
Full-page 100% remains mandatory before runtime permission. Public URL/input races are
unit characterization, not browser/E2E, live API, server normalization or
authorization enforcement certification.

## Validation terminal ledger

| Check | Native handle / launch chunk | Exit / result | Private evidence |
| --- | --- | --- | --- |
| Focused new spec | session43512 / e9c1d4 | 0;34PASS/0skip/failure;2.13s | `focused-attempt1.log` |
| Three-spec union | session75527 / bcc12a | 0;150PASS/3specs/0skip/failure;3.57s | `union-attempt1.log`, `union.junit.xml` |
| Actual full-page coverage union | session56882 / 7ec503 | 1;150PASS;100% threshold FAIL;5.86s | `coverage-attempt1.log`, `coverage.junit.xml`, raw coverage and analysis |
| Project TypeScript | session56308 / c7d8d8 | 0 | `type-project-attempt1.log` |
| New-spec TypeScript | session16002 / d36cad | 0 | `type-new-spec-attempt1.log`, private config |
| Scoped new-spec lint | session15512 / 948633 | 0;no ESLint warnings/errors | `lint-attempt1.log` |
| Fresh original page AST | chunk679fe3; synchronous terminal | 0;all original metric objects equal | `page-report-attempt1.log`, `page-after.json/md`, `metric-comparison.json` |
| Actual immutable55a Make ratchet | session5559 / cda22c | 0;findings[];baseline_commit55a1b1d35911451e018b662c2acc450bf5994ea2 | `ratchet-attempt1.log`, `ratchet-result.json` |

Raw union/coverage logs retain an `act(...)` warning in the unchanged P4
DataTable `unworked view` case; no R17 focused warning or test failure. Scoped
lint retains the installed Next15 `next lint` deprecation; no ESLint finding.
Neither old test nor runtime was changed to suppress those messages.

Post-gates all **3541 protected tracked paths verify exact**, including the
original source855e, prior P4/manual utility tests, package/config/baseline38e6
and tracked TS buildinfo. HEAD/branch unchanged. Only the two allocated new
files are untracked additions; no tracked diff, cleanup, commits or imports.
The final new spec SHA256 is
`e4b97fcc3460641482b01f8d6b55b804b1c7f1d374f11b6cb0f60417e98840a2`.
The report hash is delivered in the separate immutable freeze manifest, avoiding
a self-hash cycle. Raw logs/JUnit/coverage/metrics and private verification
configuration are frozen alongside exact terminal handles/results. No owned
test/type/lint/scanner/ratchet session remains running, no external browser,
backend, container or credential resource was created. **Heavy RELEASED**.

Final classification **NO_CHANGE — ORIGINAL_CHARACTERIZED**; runtime remains
**BLOCKED_COVERAGE**. The anticipated full-page100% gate failure is retained,
not waived or relabeled. The next decision belongs to Coordinator: independent
original characterization review/replay, without runtime permission or expansion
to another wizard in this allocation. No IMPROVED or full-campaign completion
is claimed.
