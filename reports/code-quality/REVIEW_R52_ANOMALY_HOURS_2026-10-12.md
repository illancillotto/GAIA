# R52 — Independent hours-anomaly guard review

## Ownership and snapshot

Review only: new review report and reviewer-evidence. Runtime, existing/new
tests, config, baseline, matcher and prior evidence remained read-only.
Review worktree HEAD `114fbf7196382c6446a7963c34bd89e4c9795ef5`, main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. No commit/push/Git merge.
Native-heavy token was never acquired by reviewer; native test/report/style/
ratchet receipts were independently audited from author's serial executions.
All reviewer verifiers use only stdlib and do not execute application coverage.

## Scope / source proof

The actual candidate changes only the hours-discrepancy emission guard.
Original source SHA256 `3f0032a3cf3783a6af5771fd89d7edaa58d9c9fe28fcd3d1c0ebcfd44d5bf32d`;
candidate `0aa1f19603ab12105d6f2a6d229152ecf342a39ab0079889f48150a1c53c834f`.

Independent full-module AST proof constructs the expected transformation of
the original and compares it to actual candidate: inverse `diff <= 60` guard
with continue, followed by exactly the same append. Every other callable,
query, literal, conversion and expression remains identical AST. Source before
and after the hours block is also byte-exact. No helpers or responsibilities
were relocated. This is a bounded local improvement, not decomposition of the
remaining extreme orchestrator.

## Behavioral reasoning

The two `int(... or 0)` conversions retain their left-to-right evaluation,
exception propagation and response-detail conversions. Successful `abs` of
their subtraction is always a nonnegative integer; `<= 60` is the exact
complement of the original `> 60`, without floating/NaN assumptions. The append
was the final loop statement, so continue skips no loop-tail side effect.
Exactly 60 still emits nothing; 61/119 are low, 120/121 medium. Stable severity
sorting, query/result ordering, date bounds/defaults, null SQL predicates,
authorization, response schema and transaction boundaries remain unchanged.

Operand layout is honestly disclosed: joining the same arithmetic operands
into a 95-column expression is ordinary layout below configured width100.
It offsets the physical continue line, but receives no complexity/LOC reduction
credit. Actual coverage counts the new executable continue statement.

## Characterization / test matrix review

New spec contains36 actual cases/10 test functions. Persisted direct-handler
cases do not claim auth coverage; two HTTP cases use real login and module
permission with only real database replacement. Nulls, signed/zero minutes,
strict emission/severity edges, SQL predicates/parameters/entity sequence,
complete ORM column state, adjacent date microseconds, invalid/absent/reversed
dates, type aliases/isolation, counts and stable ties are covered.

Some expected detail/severity arithmetic repeats production expressions, but
independent response membership, hard-coded mixed-severity order/counts and
unchanged R2 boundaries prevent a vacuous shared-helper oracle. No runtime
mapper/query result is mocked. Date-only seam removes the midnight race without
replacing parsing/default-window behavior.

Initial readiness defects were fixed before native execution: lifetime spec
omitted from draft union; incorrect zero-exclusion audit; selected-only inventory.
Draft evidence is retained separately. Final union preserves15 immutable specs,
including three genuine distinct-writer lifetime tests, and executes all457
cases in exact disjoint partitions. Supplemental synthetic/AST/unflushed tests
never contribute coverage credit.

## Tests and coverage

Both original and candidate:379 genuine PASS plus78 supplemental PASS, no
failure/error/skip. Independent raw JUnit identity multiset equals selected
nodeids exactly; full collected union/deselection complement is exact; all15
source hashes bind and remain identical before/after. Duplicate identities are
rejected. The36 new cases are included in the genuine partition.

Raw full-file analytics:623/623 statements,252/252 branches before;
624/624 statements,252/252 branches after. Zero missing/partial branches.
Four inherited defensive excluded lines413/414/883/884 remain exactly unchanged,
not added or presented as zero exclusions. Driver helper49/16 and orphan
helper27/10 retain full100. Native genuine runs retain152 warnings; those are
not hidden, classified as skipped, or attributed as regressions by this review.

## Metrics

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Anomalies cognitive |239|238|-1 (-0.42%)|
| Anomalies cyclomatic |112|112|0|
| Anomalies LOC |320|320|0|
| Anomalies nesting / params |4 / 5|4 / 5|0|
| File cognitive sum / max |724 / 239|723 / 238|-1 / -1|
| File cyclomatic sum |501|501|0|
| File LOC / callables |1193 / 29|1193 / 29|0|

All1672 other file objects and20322 other callable objects are exactly equal,
including fingerprints/multiplicity. File findings and total finding counts do
not change; no new violation or significant metric regression. The meaningful
gain is the removed nesting level around emission and its severity expression,
not layout compression or debt transfer.

Author original/candidate whole snapshots are1673files/20323callables/
1922errors/2739warnings/4661findings. They are NOT the current integration R50
snapshot; uncommitted integration overlays require separate Coordinator gates.
No global campaign delta is inferred from those author totals.

## Gates

Both stages have nine exact native gate receipts, each exit0: genuine tests,
coverage audit, supplemental tests, union audit, Ruff, new-spec format check,
whole complexity report, actual ratchet, diff-check. Both terminal markers
match. Actual ratchet JSON: main, baseline55a1b1d35911451e018b662c2acc450bf5994ea2,
findings[]. This review does not substitute these for current integration gates.
Baseline/scope/engines/exclusion configuration remain unchanged in local delta.

## Classification / decision

**ACCEPT_LOCAL_IMPROVEMENT — IMPROVED**, subject to Coordinator integration
custody and current whole-change gates. Cognitive gain is real but only one
point; no finding removed, extreme hotspot not eliminated, campaign not complete.

## Evidence / residual risks

Base: `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261012-r52-anomaly-hours`.
Reviewer proofs: candidate-ast-proof.json, candidate-custody.json,
original-identities.json, candidate-identities.json, coverage-proof.json,
metric-proof.json, gate-proof.json. Author raw logs/XML/coverage/metrics/exits
remain in author-evidence/original and candidate. Diagnostic reader mistakes
and their resolution are disclosed separately; no native gate was rerun.

SQLite tests do not establish PostgreSQL isolation equivalence, but the complete
AST/byte proof excludes any query/ORM/transaction change in this slice. Current
integration gates, aggregate campaign metrics, final suites and Graphify duties
remain Coordinator responsibilities. Stop this responsibility; no follow-on
anomaly-family or pending R51/R43/Bonifica/worker/E2E change is authorized by
this review.
