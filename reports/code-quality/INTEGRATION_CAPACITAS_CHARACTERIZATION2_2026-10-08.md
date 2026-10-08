# Capacitas — Independent characterization integration 2

## Ownership and snapshot

Integration2 ownership `characterization_integration` authorized before work in
registry commit `f0822f159ac7570c449e202f91b0791fca8dbb8d`. Own only this report
and approved sequential test-only cherry-picks. Dedicated integration worktree
`GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`; preflight clean. Merge-base main remains
`55a1b1d35911451e018b662c2acc450bf5994ea2`; frozen runtime remains R3
`0b1a0d37`. Coordinator may commit its separately owned documents concurrently.
No runtime/config/shared/protected file or old test is owned by this agent.

## Sequential review and integration

| Slice | Approved source tree | Integrated commit | Independent source tests | Integrated cumulative tests | Ratchet |
|---|---|---|---:|---:|---|
| C8 downloads | `473f021ba1ea6187d1f2ef00eb79cd2d684ea8a0` | `b994dcf1` | 26 PASS | 74 PASS | PASS, 0 findings |
| C1 Terreni | `da52a03810751a46bd589fdb5040e1cdec42dd2c` | `8862d20d` | 47 PASS | 102 PASS | PASS, 0 findings |
| C2a Particelle | `28dfb7c5b37876f8560109f6594bea83e531aac3` | `edba523c` | 43 PASS | 126 PASS | PASS, 0 findings |
| C3 Storico input | `f70017eac72ff891a9983b8ad4a9b5f8b2179995` | `cfc5025f` | 48 PASS | 155 PASS | PASS, 0 findings |

Closed test-only integration checkpoint: C8 adds 7 cases, C1 adds 28,
corrected C2a adds 24 and C3 adds 29 to the previously integrated 67.
Actual final cumulative run has 155 cases over eight specs, zero skips.
Counts in sequential rows are cumulative and must not be summed as unique tests.

Source worktrees were clean at independent preflight and all runtime hashes
match. Source specs and reports are the only two paths in each source change.
After every coherent integration, focused tests precede
`make complexity-ratchet BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python`.
Each completed ratchet uses the authoritative main55a baseline and has empty
findings. No overlap or merge conflict, runtime layering change, circular
dependency or component boundary is introduced by these test-only files.

## Rejected fixture and corrected source

Independent review rejected two initial C2a cases in `8eec9bc2`: speed/stop
request targeted job31 but a successful response returned job99. Backend
`capacitas_routes.py` speed/stop routes fetch the requested ID and serialize
that same job; these success mocks are impossible under that contract.
The original source was not integrated as a reviewed runtime/API scenario.

Source owner removed those two cases in `28dfb7c5`, retained valid multi-row
preservation cases, corrected its report and reran tests/coverage. Coordinator
explicitly authorized the final corrected tree in `0161cdfe`. The two source
commits were applied together with `git cherry-pick --no-commit` and committed
as one coherent test-only `edba523c`; no rejected intermediate tree was
committed on integration. Git diff against the approved final source is empty
for both owned files. Result is 24 new cases, not the rejected 26.
Observed command-band coverage is unchanged; this was a validity correction,
not assertion weakening for green tests or manufactured coverage.

## Behavioral review matrix

| Responsibility | Verified public behavior | Outcome |
|---|---|---|
| C8 CSV | Exact headers/examples, filename, real Blob bytes/text, MIME and normal anchor attributes | PASS |
| C8 XLSX | Actual SheetJS serializes workspace export; tests parse the real bytes and assert sheets/examples/instructions | PASS |
| C8 lifecycle | URL revocation not before 1000ms, once thereafter, independent staggered downloads, navigation/mode switch/unmount | PASS |
| C1 monitor | Pending/processing transition to terminal status opens once; manual versus silent loading/error semantics | PASS |
| C1 polling | Token/auth failure stops polling, explicit recovery restarts, hidden-tab suppression, visible recovery, slow-call dedup and cleanup | PASS |
| C1 commands | Exact rerun/delete ID, ordering and busy through refresh, row preservation/deletion, failure/token loss/retry | PASS |
| C1 reports | Counters/error items, current result while target exists, fallback snapshot after deletion, empty/invalid persisted result handling | PASS |
| C2a commands | Default/chosen payload, flags/limit/workers, create/rerun refresh ordering, delete/speed/stop matching row only | PASS |
| C2a async/errors | Per-row busy states, exact token/ID/payload, token loss guard, Error/non-Error failure and successful-create/failed-refresh feedback | PASS |
| C3 input/parser | Manual delimiters/order/duplicates, credentials/flags, actual CSV/XLS/XLSX first-sheet parsing, aliases/null pairs/skipped rows, invalid and empty inputs | PASS |
| C3 file/async | Public file reads reject/defer, stale prepared input clears, mode/reset retains independent manual input, exact create payload/busy through refresh, failures/retry/token guard | PASS |

Real workspace React effects and public UI handlers run; doubles remain at
API/auth/protected/modal boundaries. C8 stubs browser download URL/anchor APIs,
restores descriptors and inspects actual generated content; XLSX is not mocked.
C1 nullable/list/dict `result_json` and string status fixtures match the public
persisted-job output schema, including diagnostic legacy payloads. They are not
constructed as impossible parser values. C3 mocks only File read boundaries
with genuinely serialized SheetJS workbook bytes or real CSV text; actual
parser is unchanged and unmocked. No private closures, runtime exports,
setter captures, directly invoked disabled handlers, sparse parser outputs or
ignore additions. Endpoint failure exports are explicit, so missing-export
exceptions cannot impersonate domain failures. Existing agent test-construction
iterations remain recorded in individual reports, not hidden as first-run PASS.

## Genuine full-file cumulative coverage

Fresh before run on integration reproduces previous checkpoint with only
batch+C6+C7+C0: 67 tests PASS, unchanged raw 401/857 statements, 371/929 arms,
89/251 functions, 365/748 lines. After executions use all actual integrated
`campaign-capacitas-*.test.tsx` specs, not a sum of independent percentages.
Existing V8 whole-file include and all four 100% thresholds stay unchanged.

| Counter | Previous checkpoint | After C8+C1 | After corrected C2a | Final with C3 | Final delta |
|---|---:|---:|---:|---:|---:|
| Statements | 401/857 | 496/857 | 599/857 | 678/857 | +277 |
| Branch arms | 371/929 | 475/929 | 587/929 | 640/929 | +269 |
| Functions | 89/251 | 119/251 | 158/251 | 172/251 | +83 |
| Lines | 365/748 | 454/748 | 536/748 | 609/748 | +244 |

After C3: statement79.11%, branch68.89%, function68.52%, line81.41%.
Tests155 PASS, but coverage gate **FAIL**, exit1 for unmet 100% thresholds.
Remaining179 statements,289 branch arms,79 functions,139 lines.
No full-file100% compliance or runtime refactor permission is implied.

Raw V8 evidence `/tmp/gaia-capacitas-integration2-{before,c8-c1,c2a,final}-coverage/coverage-final.json`;
logs with the same stem and `.log`. Read-only Istanbul extraction stored
`/tmp/gaia-capacitas-integration2-final-counters.json`; line counts use
`getLineCoverage`, not sum of overlapping statement locations. Coverage exit1
is explicitly distinct from passing test cases.

Reproduction from integration frontend:

```bash
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/gaia-capacitas-integration2-final-coverage
```

At later integration this filter includes later committed matching specs too;
the exact eight-spec snapshot recorded above is `cfc5025f` plus concurrent
coordinator documentation only. Do not reuse its counters for an unexecuted
larger future suite. Before coverage JSON SHA256 is
`80e14ac94fdd5e2b33a4c0c955cab45f25259bd33b3ea52611244144d2535d65`;
final coverage JSON SHA256 is
`328964985a62d67cf7947efc9b4069ac26a7a99af03f23803e326466cfca225e`.

## Preservation, metrics and other checks

Runtime SHA256 stays
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`;
existing batch SHA256 stays
`4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`;
baseline SHA256 stays
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
Git diff versus preflight is empty for all runtime trees, config/code-quality,
tooling, Makefile, frontend package/lock and Vitest config.

Fresh final scoped AST `/tmp/gaia-capacitas-integration2-final-complexity.json`:
principal472 cognitive/416 cyclomatic/2631LOC/2nesting/1param;
file1099 cognitive/1174 cyclomatic/3109 effectiveLOC/251callables,
24error/20warning/44finding,31useState/2useEffect. Runtime byte-identical,
all metric deltas0; no reduction claim or complexity laundering.

Explicit temporary test-inclusive TypeScript configuration
`/tmp/gaia-capacitas-integration2-test-tsconfig.json` passes for integrated
C8/C1/C2a/C3. Repository default excludes tests, so this check includes the new
specs explicitly without committed config edits. Scoped new-test ESLint PASS;
existing Next16 deprecation notice only. `git diff --check` PASS.
Validation logs `/tmp/gaia-capacitas-integration2-*` record each source/integrated
focused run, ratchet, typecheck, lint and coverage invocation.

Dedicated Graphify frontend query for `ElaborazioniCapacitasWorkspace` PASS,
82 related nodes, `/tmp/gaia-capacitas-integration2-graph-query.log`;
orientation only, not a complexity or coverage proof. No runtime relationships
changed, so no code-graph refresh is needed. Coordinator owns documentation
Graphify maintenance. No full suite/build/E2E or live portal verification
is claimed by this micro-slice checkpoint.

## Classification and hold

All integrated slices: **NO_CHANGE — CHARACTERIZATION_ONLY**.
All four assigned sources independently reviewed/integrated with actual gates.
Stop this ownership after C3; C5 is not integrated by this agent.
Capacitas runtime remains **BLOCKED_BY_FULL_FILE_COVERAGE**. Other
sections and defensive/library-sensitive arms require legitimate characterization
or separately owned provenance, never impossible fixtures. Future runtimewave
holds and GIS residual-risk decision remain Coordinator-owned. This evidence
does not accept that risk or complete the global complexity campaign.
