# R10 Capacitas — bounded fraction-resolution policy and reader invariants

## Ownership, phase and frozen originals

**IMPROVED — ACTUAL RUNTIME, UNCOMMITTED FOR INDEPENDENT REVIEW.** One bounded
slice attacks the campaign's highest cognitive hotspot. Global objective remains
ACTIVE/INCOMPLETE: this is not campaign completion or elimination of the extreme
tail. Coordinator's updated integration ownership registry and external
`coordinator/RUNTIME_APPROVAL.md` authorize exactly these four paths:

- `frontend/src/components/elaborazioni/capacitas-workspace.tsx`;
- `frontend/src/components/elaborazioni/capacitas-fraction-resolution.ts`;
- `frontend/tests/unit/campaign-capacitas-fraction-resolution-r10.test.ts`;
- `reports/code-quality/SLICE_R10_CAPACITAS_2026-10-09.md`.

Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261009-r10-capacitas`, branch
`refactor/complexity-r10-capacitas`, HEAD
`fd26c39594d438e271ad885d725f1e182920a1e2`, main merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Initial runtime/test working tree was
clean. No runtime source commit is authorized; no files are staged.

Original runtime SHA256
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935` is preserved
inGit. All seventeen frozen original specs, including characterization commit's
new rendered spec, remain byte-identical. Frozen readiness SHA256
`163feb3d31d16e5d47f6b7808dc3af585c62013051dd14d6394a532c57be970d` remains
unchanged. Main and concurrent worktrees were not edited, merged or copied.

Checkpoint/project complexity instructions remain active. Governance progress
updates and integration are Coordinator-owned. Durable private author evidence:
`/home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/`.
Before evidence is `original-complexity.json` and
`characterization-original-coverage/coverage-final.json`: actual original
324tests/17specsPASS,906/929branches97.52% **FAIL100**,857statements/251functions/
748lines100%. This original failure is retained, not reclassified as a pass.

## Actual bounded change and invariants

The adjacent module owns a closed typed five-event fraction-resolution policy
and one null-first transition. Five original functional updater sites invoke
that domain policy at their original locations. The module imports only API
types; it has noReact/API/service dependency, request orchestration or effects.
The workspace adds exactly one value import and one type import while retaining
all original imports. It keeps opening/closing, token acquisition, request
arguments, awaiting, branching on result.ok and anomaly filtering verbatim.

| Event | Exact change to existing state; all other fields retained |
| --- | --- |
|selected|selectedFrazioneId becomes candidate.frazione_id |
|started|busytrue,errornull |
|synchronized|busyfalse,successtrue |
|unsuccessful|busyfalse,error=result.error??`Errore sync` |
|rejected|busyfalse,error=originalinstanceofError/message/`Errore` semantics |

The transition returns null unchanged before calling any event factory or
reading candidate.frazione_id/result.error/Error.message. Passing the candidate
object, rather than an eagerly evaluated ID, preserves selection laziness.
Functional updater evaluation timing, old closures and current-state semantics
remain intact. UNKNOWN original3166/3206 null behavior and reachable original
3214/3217/3220 races are preserved by the shared guard, not deleted as dead code.

The old request's captured rowID/fraction remains itsAPI payload/filter identity,
while completion still patches the currently displayed modal. Replacement,
close/reopen, overlapping requests and mixed success/error states behave exactly
as before. Success does not clear an earlier error; failure/rejection does not
clear success. No request generation/ownership/cancellation, busy normalization,
race correction, state substitution, effect change or additional dispatch occurs.

The exact independently proved twenty-one fallback alternatives are separately
removed, with meaningful guards and reader behavior preserved:

| Original source locations | Arms | Proof and retained behavior |
| --- | ---: | --- |
|258|1|Private normalizer receives onlyObject.keys strings; normalize/trim/case/regex sequence unchanged |
|281,378|2|Nonempty string separator always yields a nonempty split array; final item string, encoded by nonnull assertion |
|291,293,313,388,390,403|6|ActualSheetJS0.20.3/headeromitted/defvalnull/rawfalse produces dense nonnull object rows; bounded synchronous iteration unchanged |
|314,315,316,317,318,404,405|7|Chosen aliases belong to normalized keys that populate the sameMap; raw values strings; meaningful optional-key guards remain |
|2056|1|PlainAPI-JSON array synchronously reread afterArray.isArray; length defined; nonarray branch remains |
|2482twice,2483,2484|4|Local preview list populated exclusively by reader's validated/normalized string constructions; optionalsub stillstring includingempty |

Full per-arm original coordinates, installed library hashes and fresh source
proof remain in frozen readiness and original ledgers. Reader options, first
sheet, genuine empty/no-sheet guards, normalized collision/alias precedence,
cell stringification, compressed row indices/error messages, optional values,
preview count andAPI item order remain unchanged. No invented sparseSheetJS
return, builtin monkeypatch, parser substitute or accessorAPI fixture is used.
The library-dependent proof must be revalidated on dependency/options changes.

## Tests and actual full-file coverage

Added **fourteen direct domain tests**. All five events check null and nonnull
states. Frozen state/candidate/response fixtures and row-reference checks protect
retention and immutability. Response errors cover provided/null/empty values;
rejections cover realError/nonError/null/plainmessage objects and emptyError
messages. Three supplementary accessor probes verify lazy candidateID,
unsuccessfulerror and rejectedError.message reads:zero reads on null, exactly
one per nonnull evaluation. These pure probes are notAPI fixtures, UI coverage
or witnesses for the two UNKNOWN synchronous original events.

The unchanged324 rendered tests continue to execute the real workspace, public
handlers, React state/hooks, polling hook and presentation with coherentAPI/auth
boundaries. C12 retains its six replacement/null/late-response cases, and frozen
R10 rendered characterization retains its twelve two-request/state-retention
cases. RealSheetJS upload fixtures remain unchanged. No old test is weakened,
removed or skipped; no privateReact setter or fake unreachable branch is added.

Actual union **338PASS/18specs/zero skip,52.94s,exit0**:324 unchanged rendered
cases plus14directpolicy cases. Both runtime files are explicitly included in
the unchanged100% full-file coverage gate. RawJSON independently verified every
statement/function/branch positive and every summary line100%, zero skipped.

| Runtime | Statements | Branch arms | Functions | Lines |
| --- | ---: | ---: | ---: | ---: |
|capacitas-workspace.tsx|857/857|873/873|251/251|748/748|
|capacitas-fraction-resolution.ts|9/9|6/6|6/6|8/8|
|Combined|866/866|879/879|257/257|756/756|

Actual final coverage SHA256
`7c8b07b5906a6d5f015be16658a1f4751f75567eec1982ffd61bf335b38fbae3`.
The branch map changes intentionally because redundant decisions are removed
and shared policy branches live in the new module. The original23missingarms
are not claimed artificially hit in their former expressions:21 alternatives
were proven impossible, while five nullable guards and lazy formatting are
deduplicated into preserved domain behavior covered by originalUI races and
direct policy tests. No changed gate/config/threshold/coverage ignore is used.

## Actual metrics and debt accounting

The unchanged production AST scanner measured both actual runtime files and
every nested callback. Independent actual `scanner.scan_js` remeasurement
confirms workspace3105effectiveLOC, policy35effectiveLOC, total3140. These are
actual source measurements, not the earlier prototype or physical line counts.

| Metric | Original single file | Actual workspace | Actual policy | Actual combined |
| --- | ---: | ---: | ---: | ---: |
|Cognitive sum|1099|1019|3|1022,−77(7.01%)|
|Cyclomatic sum|1174|1120|9|1129,−45|
|Decision count=sum(cyclomatic−1)|923|869|3|872,−51(5.53%)|
|Callables|251|251|6|257,+6|
|Effective fileLOC|3109|3105|35|3140,+31(1.00%)|
|Error findings|24|22|0|22,−2|
|Warning findings|20|19|0|19,−1|
|Total findings|44|41|0|41,−3|

Main `ElaborazioniCapacitasWorkspace`: cognitive472→455,cyclomatic416→404,
effectiveLOC2631→2625; nesting2/params1 unchanged. Its31useState/2useEffect remain.
Terreni reader51→35cognitive,28→19cyclomatic,53LOCunchanged. Storico reader
31→21cognitive,20→14cyclomatic,35LOCunchanged; its twoerror findings become two
warnings. No new error or transferred violation enters the domain module.

| New policy callable | Cognitive | Cyclomatic | LOC | Nesting | Params |
| --- | ---: | ---: | ---: | ---: | ---: |
|selected|0|1|1|0|1|
|started|0|1|1|0|0|
|synchronized|0|1|1|0|0|
|unsuccessful|1|2|1|0|1|
|rejected|1|2|1|0|1|
|transitionFractionResolution|1|2|8|1|3|

The policy is domain-specific decision deduplication and a testable state
contract, not a generic null-wrapper or relocation of five unchanged guarded
branches. Earlier isolated policy-only measurement demonstrated cognitive
1099→1059 and decisions923→898 before the independent fallback cleanup. Actual
combined metrics decrease even after counting the new module and every factory.
The extra31effectiveLOC/sixcallables are an explicit structural cost, not hidden
by formatting compression. Main455cognitive remains extreme and still requires
future bounded work; no second hotspot or additional slice starts here.

## Executed gates and preservation

All artifacts below are beneath the durable author evidence prefix.

| Gate | Actual result | Artifact |
| --- | --- | --- |
|Focused direct+frozenR10rendered|26PASS/2spec,exit0,4.10s|`runtime-focused.log`/`.exit`|
|Actual full-file both-runtime union|338PASS/18spec;all four coverage dimensions100%,exit0|`runtime-coverage.log`/`.exit`, `runtime-coverage/coverage-final.json`|
|Explicit actualruntime/newdirect+frozenrenderedTypeScript|PASSexit0|`runtime-tsconfig.json`, `runtime-typecheck.log`/`.exit`|
|Scoped lint bothruntime/newdirect+frozenrendered|PASSexit0,noESLintwarning/error;Next16command deprecation only|`runtime-lint.log`/`.exit`|
|Actual production main ratchet|PASSexit0,zero findings,exact baseline55a1b1d3|`runtime-ratchet.log`/`.exit`, `runtime-ratchet-provenance.json`|
|Actual before/final AST|PASS,257actualcallables counted, metrics/table above|`original-complexity.json`, `runtime-complexity.json`/`.md`/`.log`|
|Independent actualLOCremeasure|3105+35=3140,matching exact source hashes|`runtime-loc-remeasurement.json`|
|Rawcoverage/test/config/hash audit|PASS,zero missing,17oldspec/readiness unchanged|`audit-runtime.mjs`, `runtime-preservation.json`/`.log`, `runtime-coverage-summary.json`|
|Whole protected source AST/import audit|PASS,actual matches reviewed candidate, originals/imports preserved|`audit-protected-source.mjs`, `runtime-protected-source.json`/`.log`|
|Whitespace/staging/diff scope|PASS,stagingempty,onlyfourauthorizedpaths|`git diff --check`, `git status --short`, protected source audit|
|Dedicated frontendGraphify|PASSexit0,freshASTgraph650sources|`runtime-graphify.log`/`.exit`|
|Dedicated frontendGraphify query|PASSexit0|`runtime-graphify-query.log`|

Authoritative ratchet JSON has `base_ref:main`,
`baseline_commit:55a1b1d35911451e018b662c2acc450bf5994ea2`, emptyfindings.
The first supplementary log extraction mistakenly parsedMake's shell
`${BASE_REF:-origin/main}` text asJSON; corrected extraction starts on the
actual line containing only `{`. This audit-script error did not fail or alter
the executed ratchet or change production tooling; raw output remains retained.
All first actual runtime focused/type/lint/coverage/ratchet commands pass.

Reproduction, frontend commands from `frontend/`:

```sh
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/runtime-coverage
node_modules/.bin/tsc -p /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/runtime-tsconfig.json --noEmit
node_modules/.bin/next lint \
  --file src/components/elaborazioni/capacitas-workspace.tsx \
  --file src/components/elaborazioni/capacitas-fraction-resolution.ts \
  --file tests/unit/campaign-capacitas-fraction-resolution-r10.test.ts \
  --file tests/unit/campaign-capacitas-resolution-state-r10.test.tsx
```

From the dedicated repository root:

```sh
make complexity-ratchet BASE_REF=main
python3 tools/code_quality/complexity.py report \
  frontend/src/components/elaborazioni/capacitas-workspace.tsx \
  frontend/src/components/elaborazioni/capacitas-fraction-resolution.ts \
  --json /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/runtime-complexity.json \
  --markdown /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/runtime-complexity.md
make graphify-frontend
node /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/audit-runtime.mjs
node /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/audit-protected-source.mjs
```

The protected-source audit compares the whole actual workspace/policyBabelAST
to the independently reviewed exact external candidates, allowing only actual
domain import paths/placement and normal indentation. It separately verifies
all original imports plus exactlytwo new domain imports. The new module's sole
dependency is type-onlyAPItypes. No unrelated source/comment/import/hook/service/
request/UI/layering change or dependency cycle appears outside the reviewed
candidate. Emitted behavior equality provides a second independent comparison.

DedicatedGraphify created the previously absent localfrontendgraph from650AST
files:6034nodes,12627edges,250communities. HTML visualization was skipped because
6034exceeds its existing5000limit; JSON/report update succeeds. Fresh extraction
has no prior stale edges to prune, so noforcedpruning or toolingpatch was needed.
Graph artifacts are ignored and never staged/committed. No rootsemantic scan or
externalLLM call was used; documentGraphify governance remainsCoordinator-owned.

## Frozen actual source and stop

| Path | SHA256 |
| --- | --- |
|capacitas-workspace.tsx|`a409e88725f0c251df7e93560c909b4464d487f382ce8ceb74787c23b2c60b59`|
|capacitas-fraction-resolution.ts|`0d635381b311c18477aeef375713cf336114329350bd74791a4d6da447c574eb`|
|campaign-capacitas-fraction-resolution-r10.test.ts|`c2d0bf12003c5d5718af7b0c6b02af4fcc2b2e39721c68a7d7712dddb6e8848c`|

BaselineSHA256`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`
unchanged; coverage config/scanner exact original hashes verified. No baseline
repair/synchronization, matcher change, threshold/scope/exclusion/package/test
configuration edit, existing-test change, skip or coverageignore occurs.

All author sessions84287focused,36451types,61564lint,65237coverage,79192ratchet,
43501Graphify completed. No background service/browser/test process remains;
heavy focused slot is free for Coordinator transfer to independent actual-source
review. No fullfrontend/build/E2E/globalcheck or final verifier phase was run by
this author, and no broad suite is claimed from the focused gates.

**Stop uncommitted with actual runtime gates green.** Independent exact-source
review/replay and separate Coordinator approval must precede any source commit
or integration. Residual extreme main455, other legacy findings, historical
global divergences and campaign targets remain open. No further functional
slice, hotspot, baseline update or main/worktree mutation is authorized here.
