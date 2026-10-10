# R18 — Independent ORIGINAL Comune characterization review

**ACCEPTED — NO_CHANGE / ORIGINAL_CHARACTERIZED (TEST_ONLY).** Independent
fresh final-spec replay: focused46 PASS, four-spec union196 PASS, coverage-run
196 PASS; zero failures/errors/skips. Project/spec type, scoped lint, fresh
original-page AST and actual full-context immutable55a Make ratchet PASS0.
Full actual page coverage remains **FAIL100**:522/643statements81.18%,
427/645branch arms66.20%,148/194functions76.28%,484/595lines81.34%.
Acceptance is exclusively of original test characterization; runtime remains
**NO_CHANGE / BLOCKED_COVERAGE**, global campaign **ACTIVE / INCOMPLETE**.
All native gate processes are terminal; exclusive heavy **RELEASED**.

## Allocation and protected identities

The integration R18 registry was read first for both initial static review and
its latest2026-10-10 independent ORIGINAL replay allocation. Reviewer task
`01a12214-b28c-72f3-ada5-5d64a6479af6` remains distinct from R18 author
`/root/r17_catasto_cf_original`. The Coordinator explicitly transferred exclusive
GAIA heavy after R19 terminal release. No other wizard or diagnostic allocation.
Only this existing NEW review report and private evidence may change.

Reviewer worktree is the existing
`/home/cbo/CursorProjects/GAIA-campaign-20261009-r16-capacitas-credential-defaults`,
branch `review/complexity-r18-catasto-comune`, HEAD
`218670c73b7abdcb0210e61ac04e15271c9ebc41`. Coordinator-imported R18 spec/CHAR
remain untracked frozen inputs, not reviewer-owned additions. Immutable main/
merge-base remains `55a1b1d35911451e018b662c2acc450bf5994ea2`.

| Frozen input | Independently verified SHA256 |
| --- | --- |
| Final spec executed by reviewer |63e29633a3733258395e8760739240b1e5c0ca3ce1fa40cf4b7e79a81359273b |
| Imported author CHAR |8415c5244e0147ec58ea24763c67f977177d9b0d9043f5ba458c0d838ba39b54 |
| Actual ORIGINAL page |855e3ef09296d8024f894118ef6e9c0d6bf13dc63b4f653c6ce6202407a732f7 |
| Existing baseline |38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95 |
|3,550-path reviewer post-import manifest |21cf9c0058b82c26c44e3aa4986c0300e8aa081952980105a2fb818194bcb4c1 |
| Author47-entry freeze |dd0fa747ffd300c4bb80a25ebbf48689efd9ae47730a7cc59f8b122fb5eae7e2 |
| Prior static review, preserved privately |a6ff6ea2985e3877149151e6b8f503b416abf84304308fc4cf038d0a4f4ca021 |

Checkpoint and current repository complexity skills remain active. AGENTS and
nine loaded quality/style/reference files were hash-verified unchanged; current
PROGRESS and R17 closed checkpoint were read. No nested frontend AGENTS. No
Graphify command, runtime/test/config/tooling/baseline/package change, cleanup,
installation, commit/import/merge or next responsibility. Initial static host
had139MiB free; independent replay preflight had12GiB after external state change.
Private replay evidence is on root disk `/tmp`, never `/dev/shm`.

## Independent source/assertion review

The initial static review read the entire frozen new spec and matched it to original
`loadComuneWizard` (page line 361), `handleApplyComune` (576),
`handleApplyComuneBatch` (604), selected-count/top/clear logic (738 onward),
Comune controls/rendering (1590 onward), local pagination/tab/context effects
and apply-triggered overview/wizard refresh dependencies.

| Responsibility | Original source contract and meaningful frozen assertions |
| --- | --- |
| Query/activation | Mode and token guards precede load state. Literal requests assert open status, optional numeric year, raw district, independent page1/pageSize25; overview closed/severity/page3 do not alter Comune query. Manual/Comune URL/navigation cases exercise real tab/effect transitions. |
| Candidate initialization | First response candidate wins, not highest score: literal first score0.2 versus second0.9 distinguishes the rules. No-candidate rows have no preview/single action; current code0 is preserved by nullish before-preview precedence. |
| Draft updates | Real radio clicks independently select per row. Pending reload retains the latest truthy second choice and fills a cleared row from a changed first candidate. Clear removes drafts; top overwrites current candidate-bearing rows while leaving other retained entries. |
| Current-page selection | Off-page drafts are retained but omitted from current-page batch. Literal batch order com-3 then com-2 follows response order; falsey com-4 is absent. A stale truthy choice whose candidates disappear remains eligible for batch even though preview/single vanish; the test observes this existing behavior without repairing it. |
| Pagination/recovery | Local page2 does not modify overview URL. Year/district/reset return page1. Empty positive-total later page triggers page1 before replacing old rows; first-page positive-total empty result does not retry. |
| Single/batch payloads | Literal anomaly/candidate IDs and trimmed notes are asserted through real public apply controls. Whitespace/empty notes use distinct original single and batch fallbacks. Subset filtering, response counts including zero, and status text are meaningful independent oracles. |
| Pending mutation/refresh | Deferred API responses prove capture before pending radio/note edits, no early reload, parallel overview and active Comune refresh, and release only after awaited refresh completion. Inactive CF/Particella stay idle. Single leaves batch eligible; batch locks applies while draft controls initially remain usable. |
| Errors/token | Error/non-Error load/single/batch messages, no refresh after mutation failure, feedback preservation when token is lost, token loss during mutation, and success coexisting with reload error match source catch/finally/guard behavior. |
| Existing concurrency | Older response can overwrite newer rows; captured loaders retain old year/page/mode after context/tab edits. Single completion can clear the scalar busy ID while batch remains pending. These public cases preserve the current behavior and do not claim a race fix. |

The page/Suspense/state/effects/render/handlers are actual imports. Mocks are
API/auth/navigation, authorization shell and external modals. No hook/state
substitution, private handler call, runtime helper mock, copied implementation,
synthetic runtime filename, skip/ignore or disabled-DOM alteration was found.
Payload expectations are literal; source mappers do not generate the oracles.
Authorization shell props are checked, but actual server/role enforcement is
not certified by that mock. Real service normalization/API responses and native
browser behavior remain outside this static review.

The empty-selection batch validation at page lines 618–620 is publicly
unreachable through the current zero-selected disabled batch button. The frozen
spec asserts disabled control and absent mutation, and does not force the
private handler. Raw coverage confirms those three statements remain uncovered.
That honest limit is not a missing assertion that can be solved by fabricating
UI access or narrowing the denominator.

## Type-only repair and execution attribution

Author's original executed spec SHA442a41bc differs from final spec63e29633
by exactly one substitution:

```diff
- return screen.getByText(`Utenza ${id}`).closest("div.rounded-2xl")!;
+ return screen.getByText(`Utenza ${id}`).closest<HTMLDivElement>("div.rounded-2xl")!;
```

The actual rendered row is a div with the corresponding class. The generic
correctly states the DOM type required by Testing Library `within`; it changes
no selector, assertion, fixture, mock or runtime expression. No cast/ignore
was added. Independent text comparison confirms this is the sole diff.

Author's retained first spec-type attempt has ten TS2345 errors and exit2.
The stop note and current registry document a separate explicit allocation for
this generic only, followed by author type-attempt2 PASS0. Project type excludes
tests and is not used to replace the spec-type gate. The initial failure remains
in the ledger, not relabeled as a pass.

Both retained TypeScript-emitted JS artifacts are independently byte-equal,
SHA256 `8fe6fe1822e93614bc133a751bbb9ce0e1ad021fbbceae6231054b53c1928b9a`.
Their frozen source hashes and exact generic-only diff also match. These are
read-only author artifacts; reviewer did not transpile or typecheck again.
The author executed tests/coverage before the annotation and established emitted
runtime equivalence afterward. That attribution is coherent for static review;
the separately authorized fresh final-spec replay below now independently passes.

## Fresh independent execution and actual coverage

Every gate below ran against the reviewer's actual imported ORIGINAL page and
frozen final spec63e29633. No author PASS substitutes for an independent gate.
Project type excludes tests; a separate private tests-inclusive configuration
extends this reviewer's unchanged project config and points imports/aliases to
this reviewer tree. Existing installed dependencies are linked read-only.
ESLint uses actual existing config, max warnings0, no cache/ignore change.

| Fresh reviewer gate | Native session/chunk | Terminal result |
| --- | --- | --- |
| Focused final Comune spec |14385 /3fa2b5 |0;46PASS0skip/error/failure |
| Accepted four-spec union |6534 /99c9d5 |0;196PASS0skip/error/failure |
| Actual full-page coverage, same four specs |52665 /f9c2bd |1;196PASS, unchanged100%thresholdsFAIL |
| Project type, incrementalfalse |82371 /901a7f |0 |
| Final spec private type, incrementalfalse |88000 /f19b1c |0 |
| Scoped final-spec ESLint maxwarnings0 |76496 /819751 |0 |
| Fresh complete original-page AST |synchronousaf0272 |0;every page metric object equal |
| Actual full-context Make immutable55a ratchet |90297 /5fafd3 |0;baseline_commit55a, findings[] |

Focused and union each execute once; coverage is its own required run. No
native gate retry/restart or timeout kill. P4's preexisting DataTable act-warning
is retained in union/coverage logs; focused R18 has no warning/failure.
No skip/ignore, test weakening, private handler invocation or runtime clone.

| Full actual ORIGINAL page coverage | Covered / total | Percent | Missing | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Statements |522/643 |81.18% |121 |0 |
| Branch arms |427/645 |66.20% |218 |0 |
| Functions |148/194 |76.28% |46 |0 |
| Lines |484/595 |81.34% |111 |0 |

Raw fresh coverage has exactly one source key in this reviewer worktree:
`frontend/src/app/catasto/anomalie/page.tsx`. All raw counters and complete
missing statement ID/location, function ID/name/location, branch ID/arm/type/
location and111line-key maps reproduce author evidence exactly. No narrowed-line
or synthetic-source denominator. The disabled zero-selected batch UI cannot
invoke handler validation statements618–620; these remain explicitly uncovered.
All four100% thresholds remain unchanged and each fails. No runtime permission.

Fresh AST objects for files/callables/violations/errors/engines/scope/summary
match the author original-page report completely despite different provenance
commits. Principal remains390cognitive/342cyclomatic/2109LOC/fingerprint
9933ead4497cdffc; file794cognitive/868cyclomatic/671weighted decisions/2267LOC,
197ASTcallables,24state/10effect,11errors16warnings. Delta0; no complexity
reduction claimed. V8's194functions and AST197callables are separate denominators.
Actual Make ratchet used the entire ordinary scope, no scoped substitute or
candidate overlay; immutable55a baseline and findings[] were audited from its
unchanged native terminal log. No baseline synchronization/repair/verify claim.

## Retained bookkeeping failures and explicit correction

The previous static phase's two private read-only audit errors (percentage
rounding versus Istanbul truncation; string versus integer line keys) remain
preserved in static evidence. They are not fresh application gate failures.
Author's first spec-type FAIL2 also remains preserved; reviewer instead executes
and typechecks the final frozen generic-only repaired spec fresh, first try.

After all native reviewer gates were terminal, the private closure audit
`c40884` exited1 with `AttributeError: 'int' object has no attribute 'strip'`.
Failed expression treated the second `JSONDecoder.raw_decode` result as remainder
text. Actual return is `(decoded_object,end_index)`. The chain stopped; the
existing native ratchet90297 was not restarted. Coordinator inspected its exit0/
log and protected3550/no mismatches, then explicitly allocated only private
parser representation correction in the latest R18 registry. The authorized
audit uses the decoded object and remaining text at `start+end_index`; exact
failed expression/trace/attribution are retained. Initial failure is not relabeled
PASS; corrected evidence analysis does not replace or rerun native results.

The same closure audit's main identity comparison then exposed another private
representation mismatch (`3653ae`, exit1): expanded `--untracked-files=all`
status was compared to the checkpoint's default-short status hash. Read-only
inspection verifies main HEAD55a, binarydiff9f85e574 and default-short0d54d4eb
exact; the expanded status has distinct hashb94eba47. No actual main change,
input/oracle/tooling change or application gate rerun. Both views and the failed
assertion attribution are retained. No unexplained runtime failure or ENOSPC.

A follow-up Coordinator-message tool attempt was rejected because it required
approval while policy was never. The Coordinator supplied the narrow allocation
through this same task thread; no escalation or input change bypassed that
rejection. Report saving uses ordinary filesystem access only; a sandbox write
denial, if encountered, must be retained and the completed report preserved
privately for Coordinator publication.

## Evidence, terminal integrity and stop

Fresh replay evidence:
`/tmp/gaia-r18-independent-original-replay-20261010/` on root disk.
Original compact static evidence remains at
`/home/cbo/.cache/gaia-campaign/20261009-r18-independent-static-review/`.
Retained exact commands/environments and `.log/.exit` pairs cover all eight
native gates; JUnit/rawcoverage/complete gaps/private type config/fresh AST/
metric object comparison/native ratchet JSON/protected manifests/main identity,
failed closure traces/allocation/corrected parser audit and report/freeze hashes
are exterior. Previous static reporta6ff is preserved as `previous-static-review.md`.

Relevant independent commands (frontend cwd unless noted):

```bash
./node_modules/.bin/vitest run tests/unit/campaign-catasto-comune-wizard-r18.test.tsx --maxWorkers=2
./node_modules/.bin/vitest run tests/unit/campaign-catasto-comune-wizard-r18.test.tsx tests/unit/campaign-catasto-cf-wizard-r17.test.tsx tests/unit/campaign-catasto-anomalie-page.test.tsx tests/unit/catasto-anomalie.test.ts --maxWorkers=2
VITEST_COVERAGE_INCLUDE=src/app/catasto/anomalie/page.tsx ./node_modules/.bin/vitest run <same four exact specs> --coverage --maxWorkers=2 --coverage.reportsDirectory=/tmp/gaia-r18-independent-original-replay-20261010/coverage
./node_modules/.bin/tsc --noEmit --incremental false
./node_modules/.bin/tsc --noEmit --incremental false -p /tmp/gaia-r18-independent-original-replay-20261010/tsconfig.new-spec.json
./node_modules/.bin/eslint --max-warnings=0 tests/unit/campaign-catasto-comune-wizard-r18.test.tsx
# Repository root; reports are exterior, bytecode writes disabled:
PYTHONDONTWRITEBYTECODE=1 NODE_PATH=/home/cbo/CursorProjects/GAIA/frontend/node_modules python3 tools/code_quality/complexity.py report frontend/src/app/catasto/anomalie/page.tsx --json /tmp/gaia-r18-independent-original-replay-20261010/page-after.json --markdown /tmp/gaia-r18-independent-original-replay-20261010/page-after.md
PYTHONDONTWRITEBYTECODE=1 NODE_PATH=/home/cbo/CursorProjects/GAIA/frontend/node_modules BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2 make complexity-ratchet
```

The `.command.json` artifacts retain full exact coverage argv plus reporters/
JUnit paths; the explanatory placeholder above is not a different test corpus.
All3550protected tracked files, originalpage855e/baseline38e6/spec63e29633/
CHAR8415c524 and author47frozen artifacts remain exact. Tracked buildinfo is
unchanged. Main concurrent HEAD/diff/defaultstatus are preserved. Only this
existing new review report is allocated to change; its former static version
is an explicitly retained historical snapshot, not a protected immutable input.

All native processes are terminal; exclusive heavy explicitly **RELEASED**.
No build/E2E/full frontend/other wizard or diagnostic work follows. Independent
acceptance is test-only **NO_CHANGE / ORIGINAL_CHARACTERIZED**. Actual runtime
remains **BLOCKED_COVERAGE** until genuine full-file100% is measured; no waiver,
metric reduction or global campaign completion is inferred.
