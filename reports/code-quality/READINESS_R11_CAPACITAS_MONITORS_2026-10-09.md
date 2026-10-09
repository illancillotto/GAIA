# R11 Capacitas Monitors — Readiness Slice Report

## Decision and ownership

**READINESS ONLY. Recommend the selected inline domain-specific lifecycle
deduplication, conditionally on independent review and original characterization.**
No runtime/test/config/tooling/baseline modification or commit is authorized or
performed. Global campaign remains ACTIVE/INCOMPLETE; principal391 projected
below still exceeds300 and this is not campaign completion.

Author worktree `GAIA-campaign-20261009-r11-capacitas-monitors`, branch
`refactor/complexity-r11-capacitas-monitors`, initial HEAD
`d2f222f9b48a2e8b728ad2801a240f2d9bdd0ba5`. Main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Initial status clean; main and
historical worktrees untouched. Exclusive owned repository artifact: this report.
Registry is `MULTI_AGENT_OWNERSHIP_R11_CAPACITAS_MONITORS_2026-10-09.md` in
the integration checkout. Readiness source and tests remain read-only.

Evidence directory `~/.cache/gaia-campaign/20261009-r11-capacitas/author/`.
Original goal attachment, checkpoint skill, project AGENTS, complexity skill,
metrics/validation/ratchet/style/workflow constraints applied. Current PROGRESS
is555454bytes; bounded current campaign/closure entries were inspected rather
than dumping8131lines into context. Existing ignored main node_modules symlink
only; no install, generated source copy or baseline synchronization.

## Fresh baseline and original gates

Runtime SHA256:
- workspace `a409e88725f0c251df7e93560c909b4464d487f382ce8ceb74787c23b2c60b59`.
- R10 fraction policy `0d635381b311c18477aeef375713cf336114329350bd74791a4d6da447c574eb`.

Original fresh focused union: **338PASS,18spec,0failure/skip**,40.51seconds.
Full-file V8: workspace857/857statements,873/873branch arms,251/251functions;
fraction policy9/9statements,6/6arms,6/6functions. Combined756/756lines,
866/866statements,879/879arms,257/257functions: **100%**, zero missing arms.
Raw `original-coverage/coverage-final.json`, JUnit `original-junit.xml`, actual
start/end/PID/exit in `original-focused.process`, log `original-focused.log`.
Heavy focused session47129 finished exit0; explicitly released to reviewer.
Fresh project typecheck and original both-runtime/eighteen-spec ESLint exit0
in `original-typecheck.log` and `original-lint.log`; no broad build/browser run.

Installed versions freshly inspected: Node24.14.0, Vitest4.1.6, TypeScript5.8.3,
SheetJS0.20.3, Next15.5.25; packages/lock/config hashes unchanged. Dependency
symlink may write ordinary shared Vitest result cache; cache is not test evidence.

Reproduction:

```bash
cd frontend
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts \
  npm run test:coverage -- tests/unit/campaign-capacitas- --maxWorkers=1 \
  --coverage.reportsDirectory="$E/original-coverage" \
  --reporter=default --reporter=junit --outputFile.junit="$E/original-junit.xml"
npm run typecheck
node_modules/.bin/eslint src/components/elaborazioni/capacitas-workspace.tsx \
  src/components/elaborazioni/capacitas-fraction-resolution.ts tests/unit/campaign-capacitas-*.test.*
cd ..
python3 tools/code_quality/complexity.py report \
  frontend/src/components/elaborazioni/capacitas-workspace.tsx \
  frontend/src/components/elaborazioni/capacitas-fraction-resolution.ts \
  --json "$E/original-metrics.json" --markdown "$E/original-metrics.md"
```

Original unchanged AST scanner: workspace3105LOC251callables1019cognitive/
1120cyclomatic; R10policy35LOC6callables3cognitive/9cyclomatic. Combined3140LOC,
257callables,1022cognitive,1129cyclomatic,872decisions,4789callableLOC,
22error19warning. Workspace31useState2useEffect0useReducer.

| Callable | Cognitive | Cyclomatic | LOC | Nesting | Params |
| --- | ---: | ---: | ---: | ---: | ---: |
| ElaborazioniCapacitasWorkspace |455 |404 |2625 |2 |1 |
| loadTerreniJobs |21 |15 |47 |2 |1 |
| loadParticelleJobs |21 |15 |42 |2 |1 |
| loadHistoryJobs |25 |18 |46 |2 |1 |
| loadIncassJobs |21 |15 |42 |2 |1 |

## Behavioral invariants and exact lifecycle

Public action or actual polling tick → synchronous fresh token read → optional
loading → same API → expiry clearing → family snapshot/ref effects → optional
manual error clearing → finally loading release. Preserve no-generation races.

1. Missing/falsy token: expirytrue/error/resume status in that order, no API,
   no loading write or finally; applies also silent request and initial mount.
2. Normal refresh: loadingtrue before API. Silent never changes loading or
   ordinary error, including success; prior manual/auth messages persist.
3. Successful API resolution: expiryfalse BEFORE reading prior in-flight ref.
   Read current ref after await, not request-start snapshot. Original list order
   and IDs preserved. No cancellation, freshness counter or last-request filter.
4. Terreni: only silent with nonempty prior ref searches first prior-ID terminal
   job in list order; modalsetter precedes refreplacement and jobsetter. Manual
   refresh does not notify. Replace ref with pending/processing/queued_resume IDs.
5. Particelle/inCASS: read priorref → replace ref → setjobs → only manual and
   nonemptypriorref run short-circuit `.some` → completionstatus → clearerror.
   Keep `.some`, not `.find`, including evaluation order and silent suppression.
6. History: priorref → refreplacement → setjobs → `.find` first terminal with
   validresult → REPEAT original resultguard → setresult → manualcompletion
   notification → clearerror. Do not cache/remove second guard or reorder it.
7. Terminal set is succeeded/completed_with_errors/failed; in-flight exactly
   pending/processing/queued_resume. Cancelling/cancelled/unknown unchanged.
8. Auth classification uses authentic ApiError401/403, BEFORE `instanceofError`
   and message reading. Auth expiry follows same3setter order, returns while
   finally still releases normal loading. Plain `{status:401}` is nonauth.
9. Ordinary rejection: only normal refresh reads Error.message or familyfallback;
   silent does neither. Exceptions in family application remain inside original
   try/catch. Preserve all exact Italian expiry/resume/fallback strings.
10. Late older results replace newer rows and current refs. Success clears expiry
    but not status; silent success keeps any visible manual/autherror. Earlier
    auth failure can stop polling after later success; opposite order can restart
    polling while keeping expiry message. Do not repair these races.
11. APIs unchanged; inCASS receives `{limit:300}` on every call. Token captured
    at dispatch remains used if session changes while request pending.
12. Existing4polling callbacks/options, actual usePolling single-flight/visibility/
    cleanup,15s versus20/45s threshold100,2effect bodies/order/dependencies,
    commands' awaits and busy state, authorization and R10readers unchanged.

No database/transaction/API/server behavior modified. Module-level private
helpers have no exports or independent React state; typed closed4family monitor
contract is not a generic megaContext. Family snapshot callbacks preserve old
render closure but read shared refs only after the response resolves.

## Original characterization matrix

| Behavior | Existing test | Missing | Proposed added | Original result |
| --- | --- | --- | --- | --- |
| Each family mount/manual/silent loading, ordinary/fallback/auth failure, token loss/recovery |terreni, particelle-monitor, storico-monitor, incass-monitor |Authentic cross-family401/403 rendered parity rather than some mocked classification |4family ×401/403 original APIerror matrix |Existing PASS |
| Actual interval, active/terminal status, hidden/visible, single-flight, unmount |Same4specs with actual usePolling |No replacement polling mock allowed |Retain all original checks |PASS |
| inCASS limit300 and100/101 interval change |incass-monitor |None |Retain APIassertions |PASS |
| TrackedID versus unrelated completion; manual/silent family differences |Same4specs |Terreni first of2tracked completions in reversed APIorder |Rendered real modal first-ID assertions |Existing PASS |
| First valid historyterminal and stored/current result precedence |storico-monitor |No extra coverage branch gap |Retain repeated runtime guard; no fabricated getters |PASS |
| Late manual overwrites newer silentrows |incass-monitor manual/poll overlap |Parity Terreni/Particelle/History, opposite completion order |Public-refresh/real-tick deferred responses both orders |One family PASS |
| Crossed manual ordinary/auth failure versus silent success/failure |None fully covers4families and bothorders |Ordering/race/error/loading/status/expiry interactions |Bounded rendered deferred matrix below |Not yet implemented |
| Token changes between overlapping dispatches |Tokenloss tests and existing inCASSrace separately |Captured old/new token per overlap and completion |Same deferred matrix with tokenA/tokenB/tokenloss |Not yet implemented |

Precise proposed new original-rendered spec:
`frontend/tests/unit/campaign-capacitas-monitor-order-r11.test.tsx`, only after
separate approval; no existing specs edited. Render public workspace with actual
usePolling and real ApiError classifier, synthetic API list/deferred boundary,
plain JSON jobs/results, real public refresh/tab/modal controls. Fake timers
drive actual15s/20s/45s hook, not callback capture/privateReact. Eight authentic
authcases above plus2Terreni completion-order cases, then4families ×6outcome
pairs ×2resolveorders (48cases):

- manual active success versus silent terminalsuccess;
- manual ordinary Error versus silent active success;
- manual ApiError401 versus silent active success;
- manual active success versus silent ordinary Error;
- manual active success versus silent ApiError403;
- manual fallback rejection versus silent terminalsuccess.

Each mounts2tracked activeIDs, starts deferred manualrequest through button,
changes token then triggers one real polling tick, loses token after dispatch,
resolves chosen order and checks intermediate + final public loading/refresh
enablement, row/status/list identity, ordinary/autherror retention/clearing,
statusguidance, historyresult, Terreni completionmodal, APIcount/token/limit.
After restoring token, real nexttick checks whether original expiry permits
polling; do not infer private state. Reverse ordering must retain original late
replacement, not force latest-wins. Proposed58tests are behavior protection,
not coverage filler; original full-file100% already exists.

## Design comparison and rejected variants

External only; `make-prototypes.cjs`, candidate source and complete owned AST
files make every nested callback measurable. No report uses only parent delta.

| Design | Combined cognitive | Decisions | Cyclomatic | Callable LOC | File LOC | Errors/warnings | Comparator |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Original |1022 |872 |1129 |4789 |3140 |22/19 |Original |
| Adjacent monitorpolicy |902 |788 |1048 |4654 |3150 |17/16 |FAIL4 historical anonymous matcher findings |
| Inline firstprototype with trivial terminalwrapper |902 |788 |1048 |4654 |3141 |17/16 |PASS0 vs55a; rejected fileLOC+1 |
| **Selected inline, required silent argument** |**902** |**788** |**1047** |**4651** |**3138** |**17/16** |**PASS0 vs55a external design comparator** |

Selected workspaceLOC3105→3103; R10policy35 unchanged. Parent455→391cognitive
(-64,-14.07%),404→360cyclomatic(-44,-10.89%),2625→2534LOC(-91,-3.47%). Combined
cognitive1022→902(-120,-11.74%), decisions872→788(-84,-9.63%), rawcyclomatic
1129→1047(-82,-7.26%), callableLOC4789→4651(-138,-2.88%), fileLOC3140→3138(-2).
Callable count257→259(+2): wrappers alone are not credited as reduction;
repeated orchestration/status policies actually collapse and all nested debt
is included. Fiveerror and3warning projected eliminated, no new violations.
useState31/useEffect2 unchanged. No principal/file regression selected.

The adjacent version has4matching findings on the unchanged R10anonymous
fraction-resolution body due to line-based tie-break against55a; no scanner,
identity, baseline or padding change attempted to hide them. It also costs+10
combinedLOC. Reject it for this slice. Initial inline trivial terminalwrapper
adds1legacy workspaceLOC; reject as unnecessary indirection/file regression.
Selected uses private shared TERMINAL_STATUSES directly in history guard;
shared refresh requires `silent:boolean` because all4real callers always pass
it. Public internal loaders retain existing optional defaultfalse. No unreachable
default is introduced merely to demand tests for a non-callable private API.

| Selected callable | Cognitive | Cyclomatic | LOC | Nesting | Params |
| --- | ---: | ---: | ---: | ---: | ---: |
| refreshCapacitasJobMonitor |12 |9 |33 |2 |2 |
| expireCapacitasJobMonitor |0 |1 |5 |0 |1 |
| getCapacitasInFlightJobIds |2 |3 |5 |0 |1 |
| findCapacitasCompletedJob |1 |2 |6 |0 |2 |
| hasCapacitasCompletedJob |1 |2 |3 |0 |2 |
| jobs.filter[0] callback |2 |3 |1 |0 |1 |
| CallExpression.map[0] callback |0 |1 |1 |0 |1 |
| jobs.find[0] callback |1 |2 |1 |0 |1 |
| jobs.some[0] callback |1 |2 |1 |0 |1 |
| Each original loadFamilyJobs |0 |1 |11 |0 |1 |
| applyTerreniJobSnapshot |5 |4 |11 |2 |2 |
| applyParticelleJobSnapshot |5 |4 |8 |1 |2 |
| applyHistoryJobSnapshot |9 |7 |12 |1 |2 |
| applyIncassJobSnapshot |5 |4 |8 |1 |2 |
| listIncassMonitorJobs |0 |1 |3 |0 |1 |

Every new helper including nested callbacks below all warning/error thresholds.
Typed contract binds only family/list/application and4setter boundaries, not
workspace state or dependencies. New helpers stay private in existing domain
file; no export/test hook/dependency change. Real shared orchestration replaces
four21/25cognitive copies with one12cognitive lifecycle and small family phases.

## Supplementary exact behavior evidence

`loader-oracle.cjs` extracts actual original/selected function declarations with
TypeScript AST, uses original ApiError/isAuthError code, plain JSON fixtures,
deferred API promises, setter/ref event traces and original historyguard.
It compares synchronous dispatch, resolution and promise-completion ordering:
8064single complete state/trace comparisons,800two-request overlapping state/
ordering comparisons (all4families, allsilentpairs, success/Error/untyped/
auth401/403, both completionorders),8six-microtask timing comparisons,24lazy
Error.message probes. Authenticerrorconstructor fixed to original3arg signature
before final run; preliminary2arg harness results discarded. Errorgetter probes
are supplementary errorclassification timing checks, NOT fabricated APIJSON
coverage or rendered branch reachability. Silent/authpaths avoid message access.
All35protected named functions and whole component outside4loaderregion exact.
Hook/command/R10readers/JSX therefore unchanged byte-for-byte.

`typecheck-prototype.cjs` uses actual project compileroptions/imports/declarations
and read-only external source overlay; PASS zero diagnostics. First harness cwd
misresolved vitest/globals; rerun from frontend/compilerhostcwd corrected that
external setup issue, not application/config. No repository config edited.

`compare-prototypes.py` invokes unchanged scanner on external source, assigns
intended owned paths, merges into R10complete report only after proof current
runtime diff from its frozen source is empty, matches immutable55abaseline with
complete unaffected context and explicit source-added-line mapping. Actual
owned originals rescanned locally; nested allmetrics retained. It is **external
design comparison**, NOT actual implementation/mainratchet or new global audit.
Later source phase must execute actual full report/ratchet with real git diff.

## Graphify, integrity and risks

Dedicated `make graphify-frontend-query` in author checkout fails because fresh
worktree has no local graph, explicitly not called PASS. Same dedicated query
in integration succeeds with existing currentgraph and Capacitas/polling/API
relations. No rawroot graphify run. No structural source change yet; eventual
source phase needs dedicated frontendcode update/pruning before closure.

Frozen original18spec hashes in `original-specs.sha256`; protected runtime/R10/
config/scanner hashes in `protected.sha256`. All remain unchanged. Only report
untracked, no staged files or commits. Actual main and all other worktrees
unchanged. Old complete reports are contextual comparator data, not fresh gates.

## Classification, next authorized decision

Actual runtime result **NO_CHANGE** (readiness only). Candidate projects genuine
IMPROVED, but cannot claim implemented until original rendered characterization,
independent review, actual full-file100%, mainratchet0 and frozen certification.

Recommended next bounded action: Coordinator approve selected exact design and
58original-rendered characterization cases; run/review before runtime custody.
Do not broaden into UI/state/commands/refactor other loaders/R10policy. Preserve
semantic races, unknown guards and principal extreme debt. Runtime/test edits
and commits remain stopped awaiting approval.
