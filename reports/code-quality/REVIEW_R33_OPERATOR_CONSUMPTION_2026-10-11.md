# R33 Independent Review — Operator weighted fuel target

## Ownership

Reviewer owns this NEW report only; runtime, tests and author evidence are read-only.
Dedicated SSD review-worktree, branch review/complexity-r33-operator-consumption,
HEAD1613f2b56f0c8ef2dcf253dd1ee9bcee8299b380; main/merge-base
55a1b1d35911451e018b662c2acc450bf5994ea2. Coordinator imported exact frozen
candidate after author termination; no reviewer native test/gate or commit.

## Baseline and frozen candidate

Original analytics SHA dd7a8bcd259efc1ef9853bef07a69b2123eb1cedfbcf78aa1eb0a8b645b48a2e.
Candidate source SHA3f0032a3cf3783a6af5771fd89d7edaa58d9c9fe28fcd3d1c0ebcfd44d5bf32d;
NEW test SHA81ece2837059a17ac7596256fb61e261c89ecf1b3083b29872c0dea3c9058949;
author report SHAc26adb9abbd29a3dfdc86502c38b18c7f66f9a1f2001cd99341bd5206ecfa425.
Author manifest SHA1d91736438aee1e260b1ca549c7f9d8b4fb7c5ce0de2be190af55004442e4309:
all114 members independently rehashed, zero mismatch. Imported candidate bytes exact.

## Target callable

Only weighted target aggregation for fuel operators. Neither consumption,
coefficient, judgement, query phases, authorization, target classifier, _op_km,
anomalies_analytics nor unrelated metrics change. Entire module AST equals the
original plus exactly one Iterable import, one helper and one weighted-block
replacement. All original nested function ASTs and non-target callable metrics/
fingerprints remain exact. This is not a full fuel_analytics cleanup.

## Behavioral invariants

- The generator remains lazy: each original vehicle target lookup occurs before
  its distance exclusion and before advancing to the next pair. Map insertion
  order and original fuel-log-only vehicles_map are retained.
- Positive total operator km still gates the whole calculation. The omitted
  empty-map guard is safe because _op_km returns a builtin dict; consuming its
  empty items iterator has no target reads or side effects and returns None.
- `not (target is None or kilometers <= 0)` is the exact complement of the old
  skip predicate, including short-circuit and NaN behavior. It is not the subtly
  different `kilometers > 0`. Unknown target bypasses distance comparison.
- Numerator then denominator accumulate in original order; float(km) is still
  called twice, float(target) once. Final denominator comparison remains >0.
- Operator consumption rounds2 BEFORE coefficient; coefficient display rounds3
  AFTER judgement on the unrounded ratio. Vehicle helper semantics are not reused.
- Public response ordering, all other calculations, ORM identity/entity state,
  query SQL/parameters/order and transaction behavior are unchanged.

## Characterization tests

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Unequal weights and missing-target denominator | R14/R24 direct routes | Persisted authenticated HTTP | Seven cases including zero/negative km | Before/after PASS |
| Target reads before rejecting km; query/entity invariants | R14/R24 SQL contracts | Public property reads and exact domain SQL | Same seven cases | Before/after PASS |
| Operator/vehicle rounding difference and threshold judgement | Legacy vehicle tests | Operator boundary behavior | Five cases | Before/after PASS |
| Nonpositive total skips all operator target reads | R31 distance contracts | Observable public lookup suppression | Two cases | Before/after PASS |
| Actual login/module denial | Existing HTTP tests | Dedicated operator route | Two cases | Before/after PASS |
| Session-only vehicle absent fuel lookup map | Existing map semantics | Persisted public missing-map scenario | One case | Before/after PASS |

All17 NEW cases genuinely invoke TestClient with real login/token and persisted
SQLAlchemy entities. Dependency override supplies the real Session, not mocked
runtime/query/auth. Property instrumentation observes rather than changes values.
Original13 test modules are byte-exact. Existing full-response contracts cover
unmodified sections; NEW seven-case responses assert complete top-operator shape.
NaN/throwing exotic numeric objects are not claimed reachable ORM/API cases:
predicate/order equivalence is static, not synthetic coverage credit.

## Changes

Typed pure single-argument helper consumes Iterable[(target|None, distance)].
No companion file, duplication, mega context, generic processor, additional
query or shared hook. The helper is a real aggregation responsibility; lazy
resolution remains with the route which owns the map/classifier closure.
Physical diff13 additions/12 removals; no opportunistic cleanup.

## Metric before

fuel_analytics235 cognitive/154 cyclomatic/337LOC/nesting4/params5.
File1193effectiveLOC/28callables/cognitiveSUM734/cyclomaticSUM501.

## Metric after

fuel_analytics217 cognitive/148 cyclomatic/329LOC/nesting3/params5.
Helper8cognitive/6cyclomatic/7LOC/nesting2/params1, zero findings.
File1193effectiveLOC/29callables/cognitiveSUM724/cyclomaticSUM501.

## Delta

Main cognitive-18(-7.66%), cyclomatic-6(-3.90%), LOC-8(-2.37%).
Aggregate cognitive-10(-1.36%); cyclomatic sum unchanged501; decisions
sum(cyclomatic-1)473→472. FileLOC unchanged; nesting warning removed.
Whole native findings4664→4663, errors1924 unchanged, warnings2740→2739.
Helper stays below every warning threshold. No transferred violation or debt
laundering. Maximum cognitive239 remains in unrelated anomalies_analytics.
Imports/dependency count21→22 is the explicit stdlib Iterable typing dependency,
not a new service/layer relationship or hidden runtime coupling.

## Tests

Independent STATIC XML/exit audit: original persisted382/complete390 PASS plus
standalone original missing-map1 PASS; after persisted383/complete391 PASS.
All XML0failure/error/skip. Original unions contain NEW16; after contains NEW17.
Exact original9701byte NEW16 prefix SHAbf74b9cf4774f75b8615c122539b5a7daa91d8095e2b13f6a60ab4abf61d198c
is reconstructed and independently verified; author did not snapshot NEW16 at
launch and discloses this limit. No successful original union rerun.
Author native ratchet/lint-backend/owned Ruff/test format/diff-check exit0.
Reviewer independently runs static audit and diff-check only, not native gates.
Fresh independent unions and gates remain Final Verifier responsibility.

## Coverage

Author RAW JSON full-file analytics original625/625statements256/256branches,
after623/623statements252/252branches in BOTH persisted/complete scopes. Zero
missing/partial. Existing four defensive excluded source lines are unchanged
except shifted positions; no new pragma/config baseline/scope weakening.
Companions retain statement/branch100. Coverage is full-file, not a diff average.
The reused external coverage.ini is observed unchanged in content: branch=True,
source=app, report includes analytics/_driver_mismatch/_orphan_session_operators.
It was not independently snapshotted at author gate launch; this provenance
limit is not retroactively represented as proven custody. Final native gates
must freeze/bind their own exact config and inspect all full-file counters.

## Ratchet

Author actual make complexity-ratchet BASE_REF=main exit0/findings[], main55a
authoritative. Baseline/scope/threshold/shared tooling protected by tracked
custody;3639 other tracked files exact. Historical global30 are separate;
no global-check PASS is asserted here. Reviewer performs no baseline command.

## Classification

IMPROVED — ACCEPTED_STATIC_REVIEW. No concrete semantic or scope defect found.
Admission to fresh independent final verification, not unconditional integration
certification. Whole campaign remains ACTIVE / INCOMPLETE.

## Files changed

Reviewer report only. Source/test/author report were exact Coordinator imports.
Independent audit evidence: SSD r33/reviewer-evidence/static-review.py and
static-review.json; full original-to-approved AST transformation checks PASS.

## Commit

None by reviewer. No merge/push/import/runtime mutation performed by reviewer.

## Residual risks

Author disclosed static diagnostic typo/terminal-observation error are not
application failure; rejected nested alternative is not credited. Full backend,
frontend, worker and E2E campaign gates are not run by this slice. Graphify
code/docs updates remain Coordinator-owned. Fresh final gates must pass before
publication. Fuel still217cognitive; this is a bounded improvement, not a claim
that the extreme tail or original campaign mission is complete.

## Recommended next slice

Final Verifier must execute native gates on these exact frozen bytes first.
No additional hotspot work authorized by this report. Reviewer TERMINAL;
no heavy token acquired, all reviewer writes cease after freeze.
