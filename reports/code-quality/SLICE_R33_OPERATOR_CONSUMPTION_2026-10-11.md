# R33 Author — Operator weighted fuel target

## Ownership

Exclusive analytics.py, NEW test_operazioni_operator_consumption_r33.py and this
report in SSD author-worktree, branch refactor/complexity-r33-operator-consumption.
Ownership registry preceded agents/worktrees; eight dirty historical analytics
snapshots were separately admitted terminal/frozen by Coordinator. No historical
worktree, main, baseline, shared tooling or original test was modified.

## Baseline

Author HEAD1613f2b56f0c8ef2dcf253dd1ee9bcee8299b380; main/merge-base
55a1b1d35911451e018b662c2acc450bf5994ea2. Initially clean. Original analytics
SHA dd7a8bcd259efc1ef9853bef07a69b2123eb1cedfbcf78aa1eb0a8b645b48a2e.
Fresh native whole report:1673files20322callables1924errors2740warnings4664findings.
These are current pre-slice metrics, not the 7 October or campaign-opening scope.

## Target callable

Only weighted vehicle target aggregation inside fuel_analytics. Consumption,
coefficient, judgement, response, _op_km, target classifier, queries/auth/filtering
and anomalies_analytics remain unchanged. The assigned responsibility is complete;
no second hotspot or wider analytics refactor is authorized by this report.

## Behavioral invariants

- Original classifier closure reads only original fuel-log vehicles_map; session-only
  vehicles remain absent. No extra database lookup, filtering or vehicle loading.
- Positive total operator distance gates target evaluation; zero/negative total
  distance causes no operator target lookups. Empty builtin dict naturally yields None.
- For each vehicle, target lookup precedes distance rejection, including zero and
  negative distances. Unknown targets never enter numerator or denominator.
- Lazy iteration and insertion order are preserved. float(distance) occurs twice
  in the same order as original accumulation; final denominator comparison stays >0.
- Negating the original skip predicate preserves short-circuit and NaN semantics;
  it does not replace km<=0 with km>0 or denominator>0 with denominator truthiness.
- Operator consumption rounds before coefficient; vehicle calculations remain
  different. Coefficient display rounds3, judgement evaluates unrounded coefficient.
- Query SQL/parameter/order and ORM entity state are unchanged; no mutation/transaction
  boundary or real login/module authorization contract changes.

## Characterization tests

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Weighted targets, unknown-target denominator, negative/zero km | R14/R24 direct-route contracts | Authenticated HTTP persisted response | Seven cases | Original/after PASS |
| Getter and SQL order, no entity mutation | R14/R24 direct-route contracts | Public route exact SQL and property reads | Same seven cases | Original/after PASS |
| Consumption-before-coefficient and judgement thresholds | Legacy vehicle/classifier tests | Actual differing operator/vehicle boundary results | Five cases | Original/after PASS |
| Nonpositive total km skips target lookup | R31 distance contracts | Public property-read order | Two cases | Original/after PASS |
| Real login and module permission | Original analytics and R31 | Focused operator-route contract | Two cases | Original/after PASS |
| Session-only vehicle absent original fuel target map | Direct-route prerequisites | Public persisted fuel map behavior | One case | Original/after PASS |

All17 new cases use real ORM persistence and real public HTTP/auth. No new synthetic
probe, copied/private runtime handler, fake auth, skip or unflushed coverage credit.
Original13 modules remain byte-exact. Before proof comprises original382/390 unions
(16 NEW cases) plus independently executed original session-only case1; appended
case was authorized after original unions terminated. Successful originals were
not rerun. Final unions383/391 include all17 NEW cases.

## Changes

One module-level typed pure _operator_weighted_target consumes lazily resolved
(target,distance) pairs. Redundant empty-map control disappears; accumulation uses
the exact negation of the original skip predicate instead of continue. The caller
keeps positive-distance gating and passes the original target closure through a
lazy generator. No lambda, context object, companion file or unrelated cleanup.
Analytics diff13added/12removed physical lines; effective fileLOC unchanged.

## Metric before

fuel_analytics cognitive235/cyclomatic154/LOC337/nesting4/params5. File effectiveLOC
1193,28callables,cognitiveSUM734,cyclomaticSUM501,cognitiveMAX239/cyclomaticMAX154.

## Metric after

fuel_analytics cognitive217/cyclomatic148/LOC329/nesting3/params5. New helper
cognitive8/cyclomatic6/LOC7/nesting2/params1, zero findings. File effectiveLOC1193,
29callables,cognitiveSUM724,cyclomaticSUM501,cognitiveMAX239/cyclomaticMAX148.
All original non-target callable metrics/fingerprints remain exact.

## Delta

- Main callable cognitive -18 (-7.66%), cyclomatic -6 (-3.90%), LOC -8 (-2.37%).
- Aggregate cognitive -10 (-1.36%), aggregate cyclomatic0; actual decisions
  sum(cyclomatic-1)473→472. No transferred violation or increased fileLOC.
- Fuel nesting warning removed; current whole report1673files20323callables,
  1924errors2739warnings4663findings. One finding is not treated as one independent issue.
- File cognitiveMAX239 persists in unrelated anomalies_analytics; no claim it improves.

## Tests

Immutable original-gates.sh, original-session-only.sh and after-gates.sh preserve
argv/environment/log/exit/XML/rawcoverage/disk in private SSD author-evidence.
Original persisted382PASS/complete390PASS, standalone original1PASS; after
persisted383PASS/complete391PASS. Every XML has0errors/failures/skips.
Existing JWT insecure-key warnings are disclosed and not altered.
Owned Ruff check PASS0; NEW test format-check PASS0. Native make lint-backend
BASE_REF=main PASS0, preserving legacy formatting; git diff --check PASS.
No full backend/frontend/worker/E2E campaign certification is claimed here.

## Coverage

Real full-file statement and branch coverage100 in both original and after scopes:
analytics625/625statements256/256branches→623/623statements252/252branches.
Unchanged companions _driver_mismatch49/49statements16/16branches and
_orphan_session_operators27/27statements10/10branches retain100. No missing or
partial branch. Exact original four defensive excluded analytics lines retained;
no new exclusion/pragma/ignore, policy waiver or scope weakening.
Historic synthetic diagnostics excluded from both scopes; complete includes the
unchanged eight unflushed tests, persisted excludes them and remains independently100.

## Ratchet

Native make complexity-ratchet BASE_REF=main PASS0, findings[], authoritative
baseline_commit55a1b1d35911451e018b662c2acc450bf5994ea2. No baseline synchronization,
threshold change or exclusion expansion. Global historical30 divergence provenance
is separate and not rerun, ignored or absorbed by this slice.

## Classification

IMPROVED (author candidate; independent review/integration admission still required).
Aggregate cognitive truly falls, nesting and primary callable improve, helper is
below every warning threshold and fileLOC/aggregate cyclomatic do not increase.

## Files changed

backend/app/modules/operazioni/routes/analytics.py;
backend/tests/test_operazioni_operator_consumption_r33.py;
reports/code-quality/SLICE_R33_OPERATOR_CONSUMPTION_2026-10-11.md.
Custody final-audit PASS0: only owned runtime changes among3640tracked files;
all3639 other tracked bytes including original tests/tooling/shared/baseline exact.
Main HEAD/status/diff exact; approved planned source equals final SHA
3f0032a3cf3783a6af5771fd89d7edaa58d9c9fe28fcd3d1c0ebcfd44d5bf32d.

## Commit

None by author. No merge/push/commit or integration publication performed.

## Residual risks

First static in-memory diagnostic failed on nonexistent CallableMetric.qualname;
STOP preserved, distinct corrected diagnostic admitted using name. No application
failure or native gate retry followed. Nested alternative rejected for aggregate
cyclomatic+4; module alternatives with LOC growth1195/1194 never applied. Final
v5 alone was admitted after original full100 and missing-case proof.
One observation wait used an already consumed terminal PTY identifier; no-such-
process error was an observation defect only, no command/test restarted.
NEW16 file was not copied at launch: exact9701byte prefix hashbf74b9cf is observed
pre-mutation and reconstructable from NEW17; input-custody-binding.md states this.
NaN behavior preserved by exact predicate rather than claimed reachable ORM/API case.
Fuel remains217cognitive; the extreme tail and complete campaign are unfinished.
Graphify code/docs updates and independent/root gates remain Coordinator-owned.

## Recommended next slice

Review/final-verification this frozen candidate first. Only after green integration,
consider a separately owned fuel aggregation responsibility; no new slice here.

## Evidence

/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r33-operator-consumption/author-evidence:
original-report/report.json; after-report/report.json; original/after scopes'
tests.xml, .coverage and coverage.json; after-ratchet/output.log; after-style-ratchet;
custody-original/candidate/final.json; final-audit.json/log; input-custody-binding.md;
static-stop-v1.md; immutable static-plan-v2/v3/v4/v5 proposals and terminal-freeze.
