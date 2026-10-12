# R52 — Work-hours discrepancy guard Complexity Slice Report

## Ownership

Exclusive `backend/app/modules/operazioni/routes/analytics.py` work-hours
discrepancy loop only; new
`backend/tests/test_operazioni_hours_anomaly_r52.py`; this new report/private
evidence. No old tests, helpers, shared files or pending candidates changed.

## Baseline

Author worktree `refactor/complexity-r52-anomaly-hours`, HEAD
`114fbf7196382c6446a7963c34bd89e4c9795ef5`; main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`.
Fresh original native scan confirms inherited target baseline:
analytics cognitive724/cyclomatic501/LOC1193/29callables;
`anomalies_analytics` cognitive239/cyclomatic112/LOC320.

## Target callable

`anomalies_analytics`, single guarded work-hours emission responsibility.
Do not claim improvements until native original/candidate metrics prove them.

## Behavioral invariants

Preserve exact date defaults/parsing/day inclusivity; type-filter semantics;
SQL predicates/parameter values/query order; null exclusions; both integer
conversions and their left-to-right evaluation/exception propagation; absolute
delta; strict60 emission threshold and120 severity threshold; public login,
module permission and type alias; entity labeling; complete payload;
stable severity ties and summary mapping order; no ORM mutation or transaction
boundary change. Guard complement is justified only for successfully computed
integer `diff`; there is no loop-tail work after the original emission.

## Characterization tests

| Behavior | Existing test | Missing | Added | Result |
|---|---|---|---|---|
| Strict60 and120 severity boundaries | R2 hours threshold | Signed59/121/zero edges | R52 signed integer threshold cases | Original/candidate PASS |
| Negative/zero persisted minutes | Original hours fixture | Full signed response details | R52 negative/zero cases | Original/candidate PASS |
| Null query exclusion | Existing nullable activities | Both null/one null boundary | R52 nullable cases | Original/candidate PASS |
| Exact SQL and ORM/transaction state | Existing general analytics state probes | Hours-specific predicate/params/order | R52 actual query listener/state snapshot | Original/candidate PASS |
| Inclusive day window | Existing analytics date cases | Adjacent microsecond exclusion | R52 both boundaries | Original/candidate PASS |
| Default/invalid/reversed dates | Existing parse-date contracts | Hours response/default window | R52 date tests pinned to captured today | Original/candidate PASS |
| Type filtering | R2 unknown type | Hours empty/falsy/other family | R52 type cases | Original/candidate PASS |
| Severity stable ties | R2 threshold order | Two ties per severity/full response map | R52 fixed-ID tie case | Original/candidate PASS |
| HTTP auth/module/alias | Original analytics auth cases | Hours-specific real login | R52 public allowed/denied/anonymous cases | Original/candidate PASS |

New spec:36 statically enumerated cases/10 test functions, all genuine
persisted data or public HTTP. No internal result, scheduler or query stubs.
The response expectation builder is not a runtime helper; independent threshold
membership/literal counts/order and existing R2 tests remain additional oracles.

## Changes

Original full-file100 and gates passed before source grant. Applied source change: replace the nested
`diff > THRESHOLD_MIN` emission with equivalent `diff <= THRESHOLD_MIN:
continue`, dedent the unchanged emission, and optionally join only the two
integer operands inside that same expression to preserve effective file LOC.
Source applied only after separate candidate grant; candidate session51392
observed terminal exit0. No code layout change receives complexity credit.

## Metric before

Fresh original target metrics as above. Author whole snapshot1673files/
20323callables/1922error/2739warning/4661observations is not the current R50
integration global snapshot; current uncommitted integration overlays require
separate root gates. Only candidate versus author original supports local delta.

## Metric after

Fresh candidate anomalies238/112/320/nesting4/params5; analytics723cognitive/
501cyclomatic/1193LOC/29callables/imports22. All1672 other file records and20322
other callable records exactly unchanged, including multiplicity/fingerprints.
Author whole totals1673/20323/1922error/2739warning/4661observations unchanged.

## Delta

Target cognitive239→238 (-1, -0.42%); file sum724→723 (-1, -0.14%).
Cyclomatic/LOC/max nesting/params/callable/import/violation counts unchanged.
Normalized file decisions `sum(cyclomatic-1)`472→472. No helper or debt move.
The payload emission leaves one conditional indentation level; its nested
severity expression genuinely loses that cognitive level. Absolute operand
layout is AST-neutral and receives no LOC/complexity credit; effective LOC
stays1193 solely rather than claiming a denominator-driven improvement.

## Tests

Reviewed original launcher launched once with exclusive token, session5091,
observed terminal exit0. Original genuine379 PASS and supplemental78 PASS;
all36 new cases passed. All nine original gates exit0. Raw evidence lives under
SSD r52 `author-evidence/original`; candidate uses separate `candidate/`.
Pipeline stops at first nonzero result. Candidate51392 terminal0: genuine379
and supplemental78 PASS, all nine gates0. Original/candidate exact inventories
and15 test source hashes equal,457 cases each, no errors/failures/skips.
Author exact JUnit classname/name identity audit PASS0 on all four partitions;
root/reviewer independent candidate checks remain separate, not presumed PASS.
Fifteen-spec union preserves prior lifetime spec and new characterization.
`synthetic`, `nested_ast`, `unflushed` tests run separately without coverage
credit. Full original collected IDs, selected/deselected partitions, all source
hashes and JUnit are retained. Independent root/reviewer exact identity audit
PASS binds all457 cases and15 hashes. Synthetic JWT length warnings are
retained in logs; actual installed interpreter is Python3.12.3 despite style
target3.11. No dependency/config change.

## Coverage

Fresh original analytics623/623 statement and252/252 branch100 PASS. Existing
driver helper49statement/16branch and orphan helper27statement/10branch full100
also PASS. Raw original coverage and partition audits exit0.
Candidate analytics624/624statements and252/252branches100 PASS; additional
covered statement is the actual `continue`, not padding. Helper coverage and
four legacy exclusions remain exact. Candidate coverage and union audits exit0.
Exactly four preexisting defensive excluded lines413/414/883/884 remain;
no source exclusion or tracked coverage configuration is changed. Candidate
cannot proceed unless original coverage and all gates pass.

## Ratchet

Actual original `make complexity-ratchet BASE_REF=main` PASS, baseline commit55a
and findings[]. Scoped Ruff/new-spec format/whole report/diff-check PASS.
Candidate actual main55a ratchet PASS0/findings[]; source Ruff/new-test format/
whole report/diff-check PASS0. Baseline/scope/thresholds/matcher unchanged.

## Classification

IMPROVED — bounded local cognitive reduction demonstrated without transfer.
This is an author technical classification, NOT root integration admission,
strategic campaign completion or elimination of an extreme hotspot.

## Files changed

Owned hours block, new R52 test and report. All existing specs byte-unchanged.

## Commit

None. No commit, push or Git merge authorized/performed.

## Residual risks

Independent final source/raw review and current integration gates remain
required; this candidate is NOT_ADMITTED yet. Complete final campaign suites and historical
baseline provenance remain separate obligations. Guard metrics may be too
small or regress file LOC; no acceptance based solely on presumed simplification.

## Recommended next slice

Stop this responsibility; await independent review and root admission before
any next slice.
