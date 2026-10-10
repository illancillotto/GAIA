# R20 author — Capacitas credential-default Complexity Slice Report

## Ownership

Dedicated worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261010-r20-capacitas-credentials`.
Branch: `refactor/complexity-r20-capacitas-credentials`.
Allocation: `docs/code-quality/MULTI_AGENT_OWNERSHIP_R20_CAPACITAS_CREDENTIALS_2026-10-10.md`
in the integration worktree, read before work. Runtime ownership is exclusively
`frontend/src/components/elaborazioni/capacitas-workspace.tsx`; this NEW report is
the only other repository write. The optional new R20 test was unnecessary.
Author held the exclusive heavy window; reviewer was STATIC ONLY. No install,
cleanup, main modification, commit, import, Graphify or global baseline check.

## Baseline

Initial clean HEAD: `438df8e83ba5a0ee7f328deb565be460d7932c59`.
Authoritative merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Initial owned-path diff was empty. Latest owned-path commits were `9e9e5421`,
`673026e7`, `01a9ada4` and `b12780e2`; no concurrent source edit was observed.

Initial workspace SHA256:
`8111c1a4658055f29a4c0b56fb1113f8b06677f9e1e622e33d596ae3d9514f48`.
Exact frozen candidate, now the actual author runtime:
`34afe117a828dca307e90f72f1318ac17b4597e14f0e80a897601c8911fe8913`.
Immutable candidate origin:
`/home/cbo/.cache/gaia-campaign/20261009-r16-capacitas-credential-defaults/readiness/selected-workspace.tsx`.
Application used `apply_patch`, then native `cmp` exit0 against those bytes.
No positional padding, source overlay or projected candidate gate is used.

Baseline SHA256 remains
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
Main concurrent binary-diff/status custody hashes remain respectively
`9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`
and `0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`.
No baseline generation/repair, threshold, exclusion, ignore or coverage-policy
change was performed. Prior historical global30 are a separate provenance issue;
the global check was not rerun by this author and is not declared PASS.

Evidence root, abbreviated below as `E`:
`/home/cbo/.cache/gaia-campaign/20261010-r20-capacitas-author`.
`E/preflight.log` records initial Git state, source/base custody and all22 old
campaign-spec hashes. Frozen original bytes are `E/original-workspace.tsx`.
Final custody is recorded separately in `E/freeze-audit-v2.json` and `E/frozen.sha256`.

## Target callable

One responsibility: the default credential selection policy used by the four
Terreni, particelle, history and inCass functional form updaters in
`loadCredentials`. Consolidate the repeated algorithm, not the whole workspace
or its JSX. Stop after behavioral equivalence, real full-file100%, measurement,
native immutable-base ratchet and author freeze; independent acceptance remains
required before integration.

## Behavioral invariants

- No-token guard, API call/token, response order, error handling/text and all
  unrelated job-loading effects remain byte-identical outside the allocated diff.
- The successful response first updates the credential list, then enqueues the
  same four setters in the same order. Each callback still receives React's
  latest `current` state and reads the captured response array when that updater
  executes; nothing is computed eagerly before scheduling.
- Each invocation spreads the complete current form into a new object before
  evaluating the exact original credential ternary. Nonempty selected IDs survive
  empty, multiple, inactive and absent replacement pools. Empty IDs choose only
  a singleton, including inactive singletons; otherwise they remain empty.
- Other pending form edits survive; requests already created before credentials
  resolve keep their captured payloads. User clearing after completion is not
  automatically defaulted again. Harvest/refetch forms are not added to this policy.
- StrictMode replay preserves the latest selection and independent form fields.
  Hook count, dependency arrays, cleanup/lifecycle and public props are unchanged.
- No backend, external portal, authentication, schema, permission, transaction,
  retry or endpoint contract is modified.

### TypeScript and React reasoning

The helper is private and accepts the concrete form states already inferred with
`credential_id: string`. Its constrained generic retains each form's other field
types; the readonly array parameter permits no mutation and accepts the same
actual API array. It is not exported as a general literal-subtype API. All four
current callers pass plain React state objects, exactly as before. The helper
does not retain, mutate or independently read state; it returns the same fresh
spread shape. Calling it inside the functional updater preserves evaluation
timing, list-reference capture and StrictMode purity. Project types and explicit
frozen-spec types use the actual modified worktree source, not a virtual overlay.

## Characterization tests

Unchanged `frontend/tests/unit/campaign-capacitas-credential-defaults-r16.test.tsx`
contains13 expanded public-UI cases; all22 frozen campaign specs contain505.
They were rerun first on the actual ORIGINAL workspace, then identically on the
actual modified workspace. No existing spec, assertion, skip or mock was changed;
no new test or copied implementation was needed to cover the new helper.

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Deferred empty/multiple/active and inactive singleton; all four literal create payloads | R16 four delayed-initial cases | None | None | Before4PASS / after4PASS |
| Missing selected IDs retained; only empty forms default under StrictMode | R16 two mixed-singleton cases | None | None | Before2PASS / after2PASS |
| Empty/multiple replacement preserves selected state despite absent options | R16 two absent-replacement cases | None | None | Before2PASS / after2PASS |
| Latest selection/clear during replay; post-completion clear remains automatic | R16 latest-selection case | None | None | BeforePASS / afterPASS |
| Already captured requests unchanged; subsequent creates use resolved singleton | R16 pending-creates case | None | None | BeforePASS / afterPASS |
| Error and non-Error rejection preserve unrelated edits and payloads | R16 two failure cases | None | None | Before2PASS / after2PASS |
| No token skips credential loading and all four public creates | R16 no-token case | None | None | BeforePASS / afterPASS |
| Every runtime statement/branch/function/line, navigation, jobs and mutation flows | Frozen22-spec union | None for measured coverage | None | Before505PASS / after505PASS; full100% |

Full-file coverage is a structural execution check, not proof of every possible
browser interleaving. Static timing invariants and the delayed/StrictMode UI
assertions provide the relevant behavioral evidence for this bounded policy.

## Changes

Added private domain-local `withCapacitasDefaultCredential` with the exact common
spread/ternary policy. Replaced the four duplicated callback bodies with calls
inside the same lazy functional setters. No other responsibility was extracted;
no new hook, component, file boundary, import or external dependency was added.

## Metric before / Metric after / Delta

Native complete reports: `E/original-complexity.json/.md/.log/.exit` and
`E/candidate-complexity.json/.md/.log/.exit`, both exit0.
`E/metrics-audit.json` records the full target tuples and physical AST census.

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive | 347 | 339 | -8 (-2.31%) |
| Principal cyclomatic | 324 | 316 | -8 (-2.47%) |
| Principal callable LOC | 2455 | 2439 | -16 |
| Principal nesting / params | 2 / 1 | 2 / 1 | 0 / 0 |
| loadCredentials cognitive | 12 | 4 | -8 (-66.67%) |
| loadCredentials cyclomatic | 12 | 4 | -8 |
| loadCredentials LOC | 30 | 14 | -16 |
| loadCredentials nesting / params | 1 / 0 | 1 / 0 | 0 / 0 |
| File aggregate cognitive | 858 | 836 | -22 (-2.56%) |
| File aggregate cyclomatic | 998 | 977 | -21 |
| Attributed sum(cyclomatic-1) | 749 | 727 | -22 |
| Physical AST decision nodes | 429 | 423 | -6 |
| File effective LOC | 3091 | 3085 | -6 |
| Sum callable LOC / max callable LOC | 4587 / 2455 | 4549 / 2439 | -38 / -16 |
| File callable count | 249 | 250 | +1 |
| File max nesting / max params | 2 / 3 | 2 / 3 | 0 / 0 |
| useState / useEffect / useReducer | 31 / 2 / 0 | 31 / 2 / 0 | 0 / 0 / 0 |
| Imports / dependency count | 21 / 21 | 21 / 21 | 0 / 0 |
| Local Error / Warning finding records | 17 / 16 | 17 / 15 | 0 / -1 |

New helper metrics: cognitive2, cyclomatic3, LOC10, nesting0, params2, no finding.
Its two ternaries replace eight physical ternaries: the actual file census has
218→212 ConditionalExpression nodes, all other decision-kind counts unchanged.
The native scanner attributes nested decisions to containing callables too;
its aggregate22-decision decline is NOT22 distinct decisions eliminated. The
physical six-decision reduction and the four identical policies becoming one
prove genuine deduplication rather than relocation. No mega-callable is moved.

| Complete application report metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Files | 1673 | 1673 | 0 |
| Callables | 20320 | 20321 | +1 |
| Errors | 1926 | 1926 | 0 |
| Warnings | 2742 | 2741 | -1 |
| Finding records | 4668 | 4667 | -1 |

All other file objects, callable records and finding records are exact between
the two native reports (`unchangedOtherFiles/Callables/Violations=true`). Findings
are metric records, not a count of independent engineering problems.

## Tests

| Native command / evidence | Result |
| --- | --- |
| Original focused, `E/original-focused.log/.exit/.json` | Exit0;13PASS;0failure/skip/todo |
| Original union, `E/original-union.log/.exit/.json` | Exit0;505PASS across22files;0failure/skip/todo |
| Candidate focused, `E/candidate-focused.log/.exit/.json` | Exit0;13PASS;0failure/skip/todo |
| Candidate union, `E/candidate-union.log/.exit/.json` | Exit0;505PASS across22files;0failure/skip/todo |
| Raw JSON assertion-status audit, `E/test-audit.jsonl/.exit` | Exit0; every assertion passed |
| Project tsc, `E/project-type.log/.exit` | Exit0; no diagnostics; incremental output disabled |
| Explicit frozen R16 spec types, `E/frozen-spec-type.log/.exit` | Exit0;135 imported runtime sources;0diagnostics |
| Existing-config scoped ESLint, `E/scoped-lint.log/.exit` | Exit0; workspace, fraction policy and all22 campaign specs; max-warnings0 |
| Native Make full before/after reports | Exit0 each; outputs above |
| Native Make immutable55a ratchet, `E/actual55a-ratchet.log/.exit` | Exit0;findings=[] |

The existing Vitest JSON counts nested describe suites (59 in the union);
`testResults.length` is22 actual spec files, not59 files. Audit retains both.
No native test, type, coverage, lint, report or ratchet attempt failed or was
retried. A preliminary targeted rg search included a nonexistent filename glob;
that search diagnostic is not a test/gate failure and did not alter source.
Complete frontend/backend/worker suites, clean build, E2E and global check were
not allocated/run here; no broad PASS claim is made from these focused checks.

Final private custody bookkeeping attempt1 failed: Node's default1MiB
execFileSync maxBuffer could not capture the8.45MB immutable Git baseline,
raising ENOBUFS/SIGTERM; its subsequent summary printer encountered the empty
JSON. `E/freeze-audit.exit=1`, empty `E/freeze-audit.json`, failed utility and
`E/FREEZE_ATTEMPT1_FAILURE.md` are preserved byte-exact. Author stopped and
notified Coordinator before correction. Coordinator authorized ONLY a NEW
`freeze-audit-v2.cjs` utility/result with bounded16MiB capture and this disclosure;
no successful native gate was rerun and no runtime/test/config/baseline changed.
Heavy was explicitly released before the corrected static custody audit; root
now owns heavy. The V2 audit distinguishes this explained bookkeeping failure
from all successful native gate exits rather than silently overwriting it.

## Coverage

V8 measures the actual complete worktree files; raw map has exactly the two
absolute author paths ending in `capacitas-workspace.tsx` and
`capacitas-fraction-resolution.ts`. No synthetic filenames or candidate overlay.
Native thresholds remain100 in all four dimensions. Counter source is
`E/{original,candidate}-coverage/coverage-final.json`; independent Istanbul raw
summary/map audit is `E/{original,candidate}-coverage-audit.json/.exit`.

| Actual full runtime file | Statements before→after | Branches before→after | Functions before→after | Lines before→after |
| --- | --- | --- | --- | --- |
| Workspace | 718/718→719/719 | 778/778→766/766 | 249/249→250/250 | 625/625→626/626 |
| Fraction policy, unchanged | 9/9→9/9 | 6/6→6/6 | 6/6→6/6 | 8/8→8/8 |
| Combined | 727/727→728/728 | 784/784→772/772 | 255/255→256/256 | 633/633→634/634 |

Every dimension100%; zero skipped map entries, missing statements/functions or
uncovered branch arms. V8 branch-arm reduction12 is a different denominator
from six physical conditional-expression nodes. Original and candidate focused
tests alone are not represented as full-file coverage; only the complete union is.

### Reproducible commands

From the dedicated frontend worktree, `E` set to the evidence root:

```bash
./node_modules/.bin/vitest run tests/unit/campaign-capacitas-credential-defaults-r16.test.tsx \
  --maxWorkers=1 --reporter=default --reporter=json --outputFile.json="$E/original-focused.json"
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts \
  ./node_modules/.bin/vitest run tests/unit/campaign-capacitas- --coverage --maxWorkers=1 \
  --coverage.reportsDirectory="$E/original-coverage" --reporter=default --reporter=json \
  --outputFile.json="$E/original-union.json"
./node_modules/.bin/vitest run tests/unit/campaign-capacitas-credential-defaults-r16.test.tsx \
  --maxWorkers=1 --reporter=default --reporter=json --outputFile.json="$E/candidate-focused.json"
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts \
  ./node_modules/.bin/vitest run tests/unit/campaign-capacitas- --coverage --maxWorkers=1 \
  --coverage.reportsDirectory="$E/candidate-coverage" --reporter=default --reporter=json \
  --outputFile.json="$E/candidate-union.json"
./node_modules/.bin/tsc --noEmit --incremental false
node "$E/type-frozen-spec.cjs"
./node_modules/.bin/eslint --max-warnings=0 src/components/elaborazioni/capacitas-workspace.tsx \
  src/components/elaborazioni/capacitas-fraction-resolution.ts tests/unit/campaign-capacitas-*.test.ts*
```

Native report before patch, report after patch and ratchet from the worktree root:

```bash
PYTHONPYCACHEPREFIX="$E/pycache" make complexity-report QUALITY_PYTHON=backend/.venv/bin/python \
  REPORT_JSON="$E/original-complexity.json" REPORT_MD="$E/original-complexity.md"
PYTHONPYCACHEPREFIX="$E/pycache" make complexity-report QUALITY_PYTHON=backend/.venv/bin/python \
  REPORT_JSON="$E/candidate-complexity.json" REPORT_MD="$E/candidate-complexity.md"
PYTHONPYCACHEPREFIX="$E/pycache" make complexity-ratchet \
  BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2 QUALITY_PYTHON=backend/.venv/bin/python
```

Native command stdout/stderr are retained in matching logs; each `.exit` stores
the actual process result, not a piped tail result. Node audit/type scripts are
private evidence utilities, not repository/configuration changes. Dependency
links were supplied by Coordinator; no install or provider call was made.

## Ratchet

Actual native Make gate against immutable55a: PASS0, findings empty. This uses
the integration ancestry plus actual candidate working-tree diff; it is not a
local self-baseline or exterior projection. Source-provenance matcher fix is
already committed in the inherited HEAD. No baseline matching assumption is
substituted for this run. A post-publication/integration gate belongs to root.

## Classification

**IMPROVED**, bounded credential-default policy only: real duplicate conditional
decisions disappear, both main and file aggregate cognitive decrease, helper is
under all thresholds, complete runtime100% and relevant behavior gates pass.
NOT an extreme-hotspot completion: principal339 remains above300, all17 local
Error records remain and useState31 remains. The full campaign is ACTIVE /
INCOMPLETE; its five>300, seventeen>200 and fifty-five>100 tail is not eliminated.
Independent review and integration certification remain required.

## Files changed

- `frontend/src/components/elaborazioni/capacitas-workspace.tsx`.
- NEW `reports/code-quality/SLICE_R20_CAPACITAS_CREDENTIALS_2026-10-10.md`.

No existing test, fraction-policy, shared runtime, tooling, baseline, config,
threshold, documentation governance or graph output was edited by the author.

## Commit

None created: publication/import were not delegated. HEAD remains438df8e8.
Root may authorize publication only after independent exact-source acceptance.

## Residual risks

The monolithic workspace still concentrates state, render decisions and job
controllers. This safe frozen slice removes only six distinct decision nodes
and one warning; it cannot satisfy the global reduction target. Mocked UI tests
do not establish live-provider/E2E behavior or certify untested final suites.
Independent reviewer must rerun actual runtime gates after custody transfer;
Graphify refresh and final campaign integration gates remain root obligations.
Historical baseline divergences remain separate, never absorbed here.

Before author freeze, Coordinator reports the independent reviewer terminal
ERRORED because of its account usage limit (reset quoted October11 00:20 local).
No reviewer restart or transfer is allocated. This is not a native author gate
failure; independent acceptance is unavailable, therefore this source is NOT
accepted for integration. Root may preserve independent-tree controls but may
not integrate the unreviewed slice. Author source/tests and completed native
evidence remain frozen; no review result is inferred from author PASS.

## Recommended next slice

ANALYZE ONLY before allocation: the duplicated job-action presentation policy
in Terreni/history/inCass, including busy captions, deletion eligibility for
pending/processing/queued_resume and response/error presentation, is a coherent
monitor responsibility. Existing repeated branches appear around the history,
Terreni and inCass cards; shared command lifecycle is already consolidated.
Consider a typed local action model and one genuinely reused action cluster,
not three moved JSX wrappers or a mega context. Preserve each family's styling,
labels, busy IDs, public buttons, handlers and ordering; do not silently give
Particelle stop/cancelling semantics to other families or conflate backend status
vocabularies. Keep model evaluation at render time and preserve captured IDs.

Proposed bounded acceptance target after fresh AST census: at least10 distinct
duplicated decisions removed and at least20 principal cognitive points reduced,
with aggregate reduction and no new finding; reaching below300 is a stretch
target only if this one responsibility justifies it. Characterize every status,
family, busy/missing-result/error case, independent IDs and deferred completion;
retain full-file100% and native55a gate. Reject the proposal if measurement shows
mere relocation or if the response/error surfaces require a separate slice.
Do not implement this or another hotspot under the present R20 allocation.
