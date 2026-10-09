# R11 Capacitas — independent quality-gate design revision

## Decision and immutable scope

**APPROVED — EXTERNAL DESIGN REVISION ONLY**, for Coordinator's separate runtime
phase decision. No actual implementation, rendered candidate coverage, runtime
ratchet, source integration or final certification is authorized by this report.
Actual review runtime remains originala409e887; campaign ACTIVE / INCOMPLETE.

Reviewed exact Coordinator external candidate:
`/home/cbo/.cache/gaia-campaign/20261009-r11-capacitas/coordinator/candidate-inline-application-workspace.tsx`.
SHA256 `077d02284410dddfeb1ab46da3b63f6cb9c8d85d2d7e211747153e8f157fda75`.
Authority: `DESIGN_REVISION_APPROVAL.md` and updated integration R11 registry.
Existing review checkout HEAD `8a3cd89b8e78a500ac5046c81e95b25cfe46e3c0`;
only this new report is writable. Prior reports/source/tests/config/scanner/
baseline remain frozen. Context-checkpoint and project complexity rules apply.

Oracle original was obtained independently with git show from committed
`b5d82b2a7690bd69b04d56fed52fd1faa227d9ac`, then SHA-checked as
`a409e88725f0c251df7e93560c909b4464d487f382ce8ceb74787c23b2c60b59`.
It is stored externally as design-review/original-workspace.tsx. No harness
reads the live modified author runtime as original. Core ApiError/isAuthError
and history result guard come from unchanged original review source/snapshot.

## Rejected prior design and precise revision

Independent original-config ESLint.lintText reproduces the rejected2a2199cc
design's0errors/1NEWwarning: react-hooks/exhaustive-deps on the initial empty
effect dependencies, naming all four load-family functions. Original source has
0errors/0warnings; revised077d0228 has0errors/0warnings. Previous396/full100%/
actualratchet0 evidence cannot waive the introduced warning.

Revision embeds the identical four family snapshot bodies as closed typed
monitor.apply callbacks and the synchronous single-use inCASS list adapter as
monitor.list. Shared refresh/status helpers remain byte-identical to selected2a.
There is no effect dependency change, useCallback, ignore, suppression, export,
extra async wrapper, new state, hook reorder or unrelated source rewrite.

Callback allocation moves from component render to loader invocation. These
application functions are internal, neither exposed nor retained for equality
comparison; each dispatch receives its original render closure and stable refs/
setters. Ref contents are still read after API await. The inCASS arrow directly
returns the original query promise with limit300; loaders directly return the
shared async refresh promise. The revised location fixes dependency analysis
while preserving request, callback, exception and caller settlement behavior.

## Complete metrics and unchanged-engine comparator

Fresh whole-repository read-only AST report was generated from unchanged review
checkout, providing complete current context rather than borrowing baseline
entries for unaffected runtime. Unchanged scanner separately parsed the external
candidate and substituted only its logical workspace path. Every nested apply,
list/filter/map/find/some callback is retained in numerical totals and matching.

Immutable baseline comes from merge-base/main
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Genuine git diff --no-index --unified=0
between its workspace and exact candidate supplies added lines, with only diff
headers mapped to the intended repository path. Full current context and original
R10 policy remain present. External full-context compare returns **exit0,
findings[]**. This is a design comparator, not an actual source ratchet.

| Metric | Original actual | Revised external | Delta |
| --- | ---: | ---: | ---: |
|Principal cognitive |455 |391 |-64 |
|Principal cyclomatic |404 |360 |-44 |
|Principal effective LOC |2625 |2527 |-98 |
|Combined cognitive |1022 |926 |-96 |
|Combined decisions |872 |803 |-69 |
|Combined raw cyclomatic |1129 |1062 |-67 |
|Combined callable LOC |4789 |4677 |-112 |
|Combined effective file LOC |3140 |3131 |-9 |
|Combined callable count |257 |259 |+2 |
|Error findings |22 |17 |-5 |
|Warning findings |19 |16 |-3 |

Workspace alone:3105→3096fileLOC,251→253callables,1019→923cognitive,
1120→1053cyclomatic,869→800decisions,4776→4664callableLOC. Unchanged R10policy:
35fileLOC/6callables/3cognitive/9cyclomatic/3decisions/13callableLOC.
Workspace31useState/2useEffect/0useReducer unchanged. Principal nesting2/params1.

Earlier selected2a combined902cognitive/1047cyclomatic/788decisions becomes
926/1062/803 in this revision: inline callback bodies are also counted in their
enclosing loaders by the unchanged engine. This numerical cost is disclosed,
not omitted as nested debt. Original-relative reduction remains substantial;
five error and three warning findings disappear, no new violation or regression.

| Revised callable, including nested entries | Cognitive | Cyclomatic | LOC | Nesting | Params |
| --- | ---: | ---: | ---: | ---: | ---: |
|refreshCapacitasJobMonitor |12 |9 |33 |2 |2 |
|expireCapacitasJobMonitor |0 |1 |5 |0 |1 |
|getCapacitasInFlightJobIds |2 |3 |5 |0 |1 |
|jobs.filter callback |2 |3 |1 |0 |1 |
|filter-result map callback |0 |1 |1 |0 |1 |
|findCapacitasCompletedJob |1 |2 |6 |0 |2 |
|helper jobs.find callback |1 |2 |1 |0 |1 |
|hasCapacitasCompletedJob |1 |2 |3 |0 |2 |
|helper jobs.some callback |1 |2 |1 |0 |1 |
|loadTerreniJobs / nested apply |5 /5 |4 /4 |21 /11 |2 /2 |1 /2 |
|loadParticelleJobs / nested apply |5 /5 |4 /4 |18 /8 |1 /1 |1 /2 |
|loadHistoryJobs / nested apply |9 /9 |7 /7 |22 /12 |1 /1 |1 /2 |
|history latestCompleted find callback |1 |2 |1 |0 |1 |
|loadIncassJobs / nested apply |5 /5 |4 /4 |18 /8 |1 /1 |1 /2 |
|inCASS list callback |0 |1 |1 |0 |1 |

All introduced/revised responsibility callables are below warning thresholds.
No matcher/baseline/threshold/scope modification or anonymous renaming. Reduction
is genuine orchestration/status decision deduplication, not debt transfer into
new warning/error callables. Actual principal remains455; projected391 still
exceeds300 and cannot constitute global campaign completion.

## Original behavior and timing evidence

Independent protected-source checks PASS:35original named functions unchanged;
component outside allocated loader region byte-identical; top-level source outside
new helper region identical; shared helper source identical to selected2a;
all4inline application bodies identical after indentation normalization. This
preserves actual effect arrays/order, hook declarations/options, JSX, commands,
auth/permissions, readers and R10 decisions. Only EOF/addition whitespace differs
outside the substantive allocated edits.

Adapted reviewer source-level oracle selects complete loaders, including inline
callbacks, and actual shared helpers. It uses genuine original ApiError/guard,
deferred API promises, request arguments, ref read/write traces, setter events
and caller fulfillment/rejection events at12microticks per settled outcome.
All original-versus-revised comparisons PASS:

-3920base traces: missing token, synchronous storage throw, normal/silent paths,
  previous sets, ordered terminal/nonterminal lists, ordinary/untyped/auth401/403/
  plain-status401 failures, all silent pairings and both overlapping orders.
-1120additional setter-throw scenarios: one-shot throws at family expiry/error/
  status/loading/jobs/modal/result boundaries across null/present token and
  success/failure branches, including naturally unvisited setter paths.
-3200token chronology overlaps: capture token-A then token-B, lose token before
  resolution; preserve current-ref consumption and both response orders.
-8synchronous list-API throw scenarios across4families ×normal/silent.

Total8248source-level comparisons in expanded oracle. No fabrication of API JSON
getters, private React access or rendered test replacement. Setter instrumentation
belongs solely to external source-level timing proof. This is supplementary
equivalence evidence; no DOM batching/native browser reachability or revised
rendered coverage claim. Prior original396/19/full100% remains original-only.

## Commands, provenance, attempts and terminal state

External evidence:
`/home/cbo/.cache/gaia-campaign/20261009-r11-capacitas/design-review/`.

Reproducible commands from review root/frontend as appropriate:

```text
python3 tools/code_quality/complexity.py report --json <E>/current-full-context.json --markdown <E>/current-full-context.md
python3 <E>/compare.py
node <E>/lint.cjs
node <E>/typecheck.cjs
node <E>/protected.cjs
node <E>/revision-expanded-oracle.cjs <E>/original-workspace.tsx <Coordinator>/candidate-inline-application-workspace.tsx
```

Original-project ESLint lintText/filePath PASS revision0errors0warnings, while
separate rejected-lint.log intentionally records the old2a warning. Compiler
overlay uses review project's actual tsconfig/fileNames/imports/declarations,
noEmit/incrementalfalse, overriding only readFile for intended workspace: zero
diagnostics. Scanner, full-context comparison, protected source and both base/
expanded oracle executions exit0. No failed harness attempts in this design
evaluation; initial base oracle3920+1120 was expanded to cover dispatch-token
changes and synchronous API throws, not rerun to hide a failure.

Process handles69553(full AST),1583(base oracle),60601(type overlay),21382(lint),
81279(expanded oracle) are terminal exit0. Complete owned callable metrics,
comparison.json, genuine-added-lines.diff and all logs remain external. Prior
author/runtime failed lint attempt is retained and independently reproduced;
it is not reclassified PASS merely because tests/ratchet passed.

Final protected manifest and18original-spec manifest PASS; allocated lifecycle
test85206faf, frozen author CHARACTERIZATION13014929 and prior reviewer reports
c74e515e/7f4a16b4 unchanged. No source/test/config/baseline edits, commit, actual
source copy, rendered replay, build/browser/backend/worker or Graphify batch.
Only this new DESIGN_REVISION report added untracked. Stop for Coordinator's
separate runtime decision, then eventual exact-source review/fresh certification.
