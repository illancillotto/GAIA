# R15 Capacitas — Independent Static Readiness Review

## Disposition

**ACCEPTED: bounded NO_CHANGE disposition; all three measured designs rejected.**
No runtime candidate is accepted, no implementation or heavy-gate permission is
implied, and no reduction is credited to R15. This conclusion applies to the
three frozen designs, not to every possible safe design of this responsibility.
Global campaign remains **ACTIVE / INCOMPLETE**.

## Ownership and provenance

- Reviewer: `/root/r15_static_review`, distinct from the readiness author.
- Authoritative registry read first: integration
  `docs/code-quality/MULTI_AGENT_OWNERSHIP_R15_CAPACITAS_CREATE_JOBS_2026-10-09.md`;
  Coordinator allocation follows registry commit `711f2b9f`.
- Review worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261009-r15-capacitas-create-jobs-review`.
- Branch: `review/complexity-r15-capacitas-create-jobs`.
- Review HEAD: `9bbb937f0d010bb5244d2d284cfc836a27a7dba4`;
  authoritative merge-base/main: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Sole writable tracked-tree artifact is this new report. Runtime, all21 specs,
  source policy, author report/evidence, baseline, tooling and configuration
  remain read-only. No commit, import, merge, reset, stash or branch creation.
- Initial review status/diff were clean. Author HEAD observed after publication:
  `995e3778cc6e71e6ca13780ba7b511a2dd4733f0`, also clean. The author's frozen
  `68996649`/untracked-report preflight describes its earlier readiness snapshot,
  not these subsequently published states.

Frozen readiness SHA256:
`aec8f39c5bceaa05a97499012fb91e838913bd4a125f8953cf2593257ca1d516`.
Frozen28-artifact manifest SHA256:
`127bc6656b317000a10b216d2092fa7e1d3307b1684a11c050abdab48741e63d`.
Fresh reviewer assertions verify both hashes, every manifest artifact, all3525
protected paths in BOTH author/review trees, and all21 spec hashes/bodies.

Workspace remains SHA256
`8111c1a4658055f29a4c0b56fb1113f8b06677f9e1e622e33d596ae3d9514f48`;
policy remains `0d635381b311c18477aeef375713cf336114329350bd74791a4d6da447c574eb`;
scanner remains `faf340a36a2a3730d313be34b17a89e1c96c6310084d3b63739e0a3fbf446b8d`.
Concurrent main binary diff/status freshly reproduce
`9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b` and
`0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`.

Checkpoint skill, Graphify skill, root AGENTS, repository complexity skill and
its workflow/constraints/quality references were read. Current R13/R14 progress
entries and relevant historical verification entries were inspected; no other
historical campaign is recertified by this review.

## Fresh bounded metric verification

Five one-file scanner invocations used the existing unchanged integration
`tools/code_quality/js_ast_metrics.mjs`: review workspace, three exterior full
workspace projections, and unchanged fraction policy. All completed exit0.
Every workspace callable record, not just aggregates/principal, equals the
corresponding frozen author output. Independent AST accounting reproduces the
source census and confirms that non-target AST is unchanged: only the four
create handlers plus the projected helper differ. Extracted handlers AND helper
exactly match the snippets exercised by the timing harness.

| Scope | Cognitive | Cyclomatic | Sum(cyclomatic-1) | Callables | Effective LOC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Actual workspace | 858 | 998 | 749 | 249 | 3091 |
| Actual policy | 3 | 9 | 3 | 6 | 35 |
| Actual combined | 861 | 1007 | 752 | 255 | 3126 |
| Direct-request projection combined | 860 | 1031 | 759 | 272 | 3144 |
| Async-operation projection combined | 850 | 1008 | 748 | 260 | 3144 |
| Error-formatter projection combined | 846 | 1001 | 745 | 256 | 3129 |

| Target actual callable | Cognitive | Cyclomatic | LOC | Nesting | Params |
| --- | ---: | ---: | ---: | ---: | ---: |
| ElaborazioniCapacitasWorkspace | 347 | 324 | 2455 | 2 | 1 |
| handleCreateParticelleSyncJob | 7 | 7 | 26 | 1 | 0 |
| handleCreateTerreniBatchJob | 11 | 10 | 28 | 1 | 0 |
| handleImportAnagraficaHistory | 6 | 6 | 23 | 1 | 0 |
| handleCreateIncassJob | 4 | 4 | 18 | 1 | 0 |

Inclusive callable sums count a nested decision again in its enclosing callable.
The independent whole-AST census instead counts unique source nodes. Original
scanner-style census is432 combined; R13-compatible census is430, excluding the
workspace SwitchStatement/default SwitchCase. The three projections have combined
R13-compatible census427/424/427, respectively. Thus direct-source decisions
really decrease by3 even though inclusive decisions increase by7; neither
observation may be substituted for the other. Both identical perimeter definitions
were preserved. Actual useState70/useEffect2 versus regex-scanner31/2 remains an
explicit unchanged tooling limitation, not a reason to adjust baseline.

Raw AST scanner records contain placeholder `violations: []`: these are NOT a
threshold evaluation, full-context matcher, authoritative ratchet or fresh global
finding count. Prior R13 local17error/16warning and its gates are attributed only.

## Why the three designs remain rejected

| Design | Principal cog/cyclomatic/LOC | Concrete blocker |
| --- | --- | --- |
| Direct request/accepted callbacks | 339/320/2458 | Combined LOC+18, principal LOC+3; inclusive decisions+7 and17 additional callables despite3 fewer source decisions |
| Async-operation wrapper | 335/316/2459 | Combined LOC+18, principal LOC+4; an extra awaited operation delays actual busy-release setter calls |
| Shared error formatter | 339/320/2455 | Combined LOC+3 in already excessive file debt; also only error formatting, not the allocated full lifecycle |

The first two share recognizable phases, but extracting request/accept callbacks
is not sufficient evidence of an acceptable debt reduction. The formatter does
remove duplicated source ternaries; its rejection follows explicit non-growth
and bounded-scope rules, not a claim that its cognitive reduction is fictitious.
None was installed in the checkout. No packing, unrelated trimming, relocation,
baseline inflation or matcher workaround was used to make a projection acceptable.

## Original behavior and supplementary timing evidence

Actual four handlers/parser and monitor/loaders were inspected. Guard/token read,
outside-try error clearing for Terreni/history, payload construction, inCASS
spread, unbound imported API calls, expiry/notice/error ordering, awaited reload,
and finally release remain untouched. Terreni batch error and monitor error are
different channels. Real reload rereads token and swallows ordinary load errors;
its auth-expiry path may overwrite success status. No race/cancellation fix is
authorized. Render-captured form values and completion-order semantics remain
invariants rather than opportunities for behavioral cleanup.

Fresh replay of the frozen, statically inspected pure harness completed exit0
using review-tree original source; only paths/output location were adapted in a
NEW private script. Complete41-case trace objects equal the frozen author objects,
not merely flags/counts. Independent assertions rederive41 direct equivalences,
41 formatter equivalences,36 async differences and strict unbound API receivers
for every projection. Four missing-token cases and empty-Terreni are the five
no-op cases without the async difference.

Concrete extracted Particelle happy-path observation: creation resolves tick2;
success effects and reload dispatch occur tick2; reload resolves tick5; original
busy false occurs tick5 versus async wrapper tick6. This reproducible setter-order
counterexample alone is enough to reject that wrapper under the stated invariant.

These are supplementary port observations, NOT real React scheduling/UI proof,
coverage, production API/monitor behavior, type validation or promise-return
identity. The harness substitutes reload and inCASS payload builder, serializes
payload observations (omitting undefined fields/reference identity), uses only
manual-history mode, and replaces only Particelle/Terreni form objects. It does
not establish actual file-array identity, token-loss/auth monitor transitions,
same-act overlapping creates, cross-family races, payload-builder exceptions,
returned-ID accessor exceptions or exhaustive stale-capture behavior. Its
reload-rejection case propagates a rejected port unlike normal swallowed real
monitor errors. These limitations do not weaken the LOC or busy-release rejection;
they do prevent promoting41 matches into implementation permission.

## Existing-test gap matrix review

Fresh Babel extraction verified all21 files and206 static callback bodies against
the frozen inventory. Static bodies are NOT206 executed cases; previous492/21
R13 results are attributed only. Relevant public-UI assertions were read, notably
Particelle exact payload/pending refresh, Terreni creation+refresh/retry/token
guard, history captured input/create401/no direct auth handling, inCASS actual
builder/pending refresh/load-error and expiry status replacement, R13 execution
captures, R11 monitor transitions and R12 command-only concurrency.

| Contract | Existing static evidence | Remaining gap | Added/run here |
| --- | --- | --- | --- |
| Exact payload/guard and busy through reload | Particelle commands130; batch227; history326; inCASS221 | Full cross-family phase/error matrix and microtask checkpoints | None |
| Real load errors/auth status overwrite | history374; inCASS269/283; R11 monitor cases | Create-to-reload token rotation/loss/auth variants for all four | None |
| Captured forms/arrays | history326; Terreni residual140; R13 captures | File/manual switch, reference identity, history/inCASS stale capture | None |
| Errors and exceptions | batch244; history352 includes real ApiError401 and no auth handler; inCASS249 | Sync imported throw, builder/spread exceptions, defensive mapping failure | None |
| Create overlap/completion order | R12 addresses rerun/delete only | Same-act create overlap, reversed completion, cross-family isolation | None |

The author's missing-case matrix is appropriately conservative: an existing
history401 example does not cover all families/403 or establish monitor behavior.
No missing case was added or executed. Full-file coverage cannot substitute for
these ordering/race assertions. No future slice is implicitly allocated.

## Commands actually executed and results

Private evidence: `/home/cbo/.cache/gaia-campaign/20261009-r15-static-review/`.

- `git status --short`, `git rev-parse HEAD`, `git branch --show-current`,
  `git merge-base HEAD main`, `git diff --stat`, owned-path log/worktree inventory:
  fresh preflight; initial review clean, expected branch/merge-base.
- `node /home/cbo/.cache/gaia-campaign/20261009-r15-static-review/verify.cjs`:
  attempt1 exit1 was a REVIEW HARNESS ordering assumption, not application failure:
  author candidate snippets are reverse source-order after range replacement.
  Failure retained in `verify-attempt1.log`; compare exact handler-string multisets
  instead. Attempt2 exit0; attempt3 exit0 additionally checks helper extraction.
  Both logs retained. No author script/log/candidate was modified.
- Child commands actually executed by `verify.cjs`:
  `node /home/cbo/CursorProjects/GAIA-campaign-20261008-integration/tools/code_quality/js_ast_metrics.mjs <file>`
  for the five paths listed above; bounded one-file scans only, fresh outputs stored.
  Integrity checks use `git diff --binary`/`git status --short` read-only on main.
- `node /home/cbo/.cache/gaia-campaign/20261009-r15-static-review/timing-replay.cjs`:
  exit0,41 bounded supplementary cases,36 retained counterexamples.
- `node /home/cbo/.cache/gaia-campaign/20261009-r15-static-review/verify-traces.cjs`:
  exit0, complete trace equality, independently rederived counts/ticks/receivers.
- Targeted `cat`, `sed`, `rg`, `wc`, `sha256sum` and AST inventory reads:
  static review only. Earlier author Graphify query/failures were inspected,
  not freshly executed or relabeled PASS.
- `git diff --check` and `git diff --no-index --check /dev/null <new-report>`:
  no whitespace errors. Final status/HEAD/merge-base/diff captured privately.
- `node /home/cbo/.cache/gaia-campaign/20261009-r15-static-review/freeze.cjs`:
  exit0, terminal integrity recheck and private `FROZEN_REVIEW.json` publication;
  author28artifacts, both3525-path manifests and concurrent main remain exact.

Tests/type/lint/coverage/build/fullscan/complexity-report/ratchet/global-check/
Graphify refresh: **NOT RUN** by this reviewer. R14 owns exclusive heavy window;
no heavy slot was acquired, and no planned R15 heavy execution remains. No
threshold/exclusion/ignore/baseline changes or fresh gate claims. No runtime or
domain-document boundary changed; no graph refresh is required for this report.

## Terminal result and residual risk

Actual metric after equals before: principal347/324/2455 and combined861cognitive/
752decisions/3126LOC, delta0, delta%0. **NO_CHANGE**, not IMPROVED or a runtime
REGRESSED slice. Source/test/config/protected author artifacts remain exact.
All reviewer Node processes are terminal; no server or shared dependency/cache
was created. This report awaits Coordinator publication; reviewer creates no commit.

Accept the rejection of these three projections and stop this allocation. A new
design or differently scoped hotspot requires explicit Coordinator ownership and
new characterization gates. No claim is made that a safe alternative is impossible,
that global suite obligations are satisfied, or that the campaign is complete.
