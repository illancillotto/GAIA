# R31 Session Distance — Complexity Slice Report

## Ownership

- Author `/root/r31_session_distance_author`, one exclusive policy responsibility.
- Worktree `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r31-session-distance/author-worktree`.
- Branch `refactor/complexity-r31-session-distance`; HEAD
  `6089b05e1c047f388badf8f9b53caa18a1babf6e`; actual main/merge-base
  `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Registry R31 established before activation. Initial tree clean; ownership ONLY
  analytics runtime, NEW R31 test, this report and isolated private SSD evidence.
- Heavy gates serial and author-only until release. No commit/import/push/merge.

## Baseline and concurrency provenance

Fresh native whole report before edits:1673files20323callables1924errors2740warnings
4664overlapping findings. Original analytics SHA256
`49b9ffeef7851e12aa4e8a309fb63356d226a6526cffbdaef052d4c9d3fde0d7`.

Six historical dirty analytics snapshots independently hashed before runtime
mutation; exact hashes match rejected/frozen R19V1 author/reviewer, accepted R19V2,
R24 reviewer and R28 author/final snapshots. Their terminal dispositions are in
REJECTION_R19_DRIVER_MISMATCH, INTEGRATION_R19_V2_R16_DIAGNOSIS,
INTEGRATION_R24_FUEL_TARGETS and INTEGRATION_R28_FUEL_OPERATOR_KEYS. R19V1 review
freeze was historically incomplete after ENOSPC; no complete V1 manifest is
invented. Its surviving input hashes and explicit rejection/freeze are verified.
None of those worktrees modified or treated as a fresh active source owner.

Custody before/after checks2073tracked runtime/test/shared/tooling/config paths;
ONLY owned analytics changes. All old12specs and other runtime exact. Main binary
diff9f85e574/status0d54d4eb and baseline38e6b794 exact. No baseline, threshold,
scope, exclusion, pragma, ignore, dependency or shared-file modification.

## Target callable

Two identical nested `_session_km` implementations inside fuel_analytics and
km_analytics: each cognitive5/cyclomatic5/LOC7/params1/nesting1, fingerprint
ea35810e8539a288. Eliminate this one duplication, not either endpoint as a whole.

## Behavioral invariants

- Truthy route distance wins, including negative truthy values. Zero/None route
  fall back to odometers; do not replace truthiness with positivity or None check.
- Route is read twice on the taken branch; odometers are not read there.
- Falsey route checks end first, then start only if end is not None. If either
  is None, return0.0 without coercing the other value.
- When both odometers exist, read/convert end again BEFORE read/convert start,
  subtract in that order and clamp only the odometer difference with max(0.0,diff).
- Float errors propagate; no caching, parameter pre-evaluation or default rescue.
- Keep every call site and execution position, iteration/SQL/query order,
  session/ORM strong references, authorization, dates/status filters, ranking,
  response schema, rounding, operator attribution and duration extremes unchanged.
- Session policy is pure: no mutation, DB operation, service call or lifecycle change.

## Characterization tests

NEW spec contains32genuine public HTTP cases with actual login. Twenty persisted
distance cases, four real-auth/module permission cases and eight expressly
unflushed ORM supplemental edge cases. The latter are NOT persisted-domain proof
and are excluded from the separately measured persisted-only coverage gates.
No fake auth, source copy, private route-handler invocation or synthetic coverage.

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Truthy route precedence, negative route, zero fallback | Original km and R14 distances | Both endpoints with contradictory odometers | Persisted public matrix | PASS before/after |
| None route/end, zero odometers, negative/fractional delta | Existing partial distance cases | Exact public projections and rounding | Persisted public matrix | PASS before/after |
| Period/vehicle/operator/total/extreme projections | Original km/fuel contracts | Single-session exact km payload and fuel distance fields | Included in20persisted cases | PASS before/after |
| Attribute order/read count/short circuit | Prior source policy only | Real persisted HTTP trace |2fuel/6km calls with exact ordered reads | PASS before/after |
| Actual login/module authorization | Original fuel/km auth | Both endpoints with/without permission |4cases401/403/200 | PASS before/after |
| Start None / float coercion failures | Start column NONNULL, malformed Numeric not persistable | Supplemental behavior only |8unflushed HTTP cases | PASS before/after, not coverage proof |
| Queries/status/date/order/attribution/lifetime/other analytics | Immutable old12spec342 genuine union | No new responsibility | Retained exact old specs + complete AST proof | PASS before/after |
| Entire runtime coverage | Historical R28 union100 | Fresh genuine full-file before/after |366persisted-only and374complete union |100statement/branch both |

## Changes

Single typed `_session_distance_km(session: VehicleUsageSession) -> float` in the
SAME analytics.py file; remove both original bodies and replace seven original
call names. Rename only new helper parameter/local s→session/diff→distance to
follow no-one-letter style. No new import, context abstraction, wrapper or file.

Private static-proof0 normalizes those two identifiers and proves helper body
AND signature identical to BOTH originals. After only removing the two nested
definitions, removing the new shared definition and normalizing call names,
the COMPLETE module AST is identical, including every query and call position.

## Metric before / after / delta

Both measurements are fresh native full-project reports, not imported metrics.

| Scope | Before | After | Delta |
| --- | ---: | ---: | ---: |
| fuel_analytics cognitive / cyclomatic / LOC |240 /158 /344 |235 /154 /337 |-5 /-4 /-7 |
| km_analytics cognitive / cyclomatic / LOC |44 /37 /137 |39 /33 /130 |-5 /-4 /-7 |
| Physical policy implementations |2 |1 |-1 |
| Policy cognitive / cyclomatic / LOC sum |10 /10 /14 |5 /5 /7 |-5 /-5 /-7 |
| Whole file cognitive sum / max |749 /240 |734 /239 |-15 /-1 |
| Whole file cyclomatic sum / max |514 /158 |501 /154 |-13 /-4 |
| Normalized decision sum(cyclomatic-1) |485 |473 |-12 |
| File effective LOC / callable LOC |1200 /1266 |1193 /1245 |-7 /-21 |
| File callable count |29 |28 |-1 |
| Native file statements / branch outcomes |632 /260 |625 /256 |-7 /-4 |
| Imports / dependencies |21 /21 |21 /21 |0 |
| Global file / callable count |1673 /20323 |1673 /20322 |0 /-1 |
| Global error / warning / overlapping findings |1924 /2740 /4664 |1924 /2740 /4664 |0 |

Main routes keep nesting4/2 and params5; new helper5cognitive/5cyclomatic/7LOC,
nesting1/params1, no violation. File cognitive sum falls2.00%, cyclomatic sum2.53%,
file LOC0.58%, callable LOC1.66%. Native density1.0525→1.035205.

Scanner recursively counts nested decisions in parent AND nested callable:
aggregate -15 cognition/-12 normalized decisions is NOT15independent domain rules
or12physical branches removed. Physical policy deletion and native branch-outcome
reduction4 are reported separately. All1672other file objects and their callable
objects exactly identical before/after, scope/engines unchanged, no parse errors.
Extreme tail remains5>300/17>200/55>100; this slice does not resolve it.

## Tests and coverage

| Native gate | Result |
| --- | --- |
| Original NEWspec focus |32PASS,0failure/error/skip |
| Original complete union |374PASS/native0; outer wrapper2 process deviation below |
| Original persisted-only union |366PASS/native0/wrapper0,18deselected |
| Candidate persisted-only union |366PASS/native0/wrapper0,18deselected |
| Candidate complete union |374PASS/native0/wrapper0,10historic synthetic diagnostics deselected |
| Scoped Ruff runtime/NEWspec |PASS0 |
| NEWspec Ruff format-check |PASS0 |
| make lint-backend / style-ratchet actualmain55a |PASS0 /PASS0 |
| Raw JSON/XML/whole metrics/ratchet audit |PASS0 |
| Whole before/after report |PASS0 /PASS0 |
| Custody / diff-check |PASS0 |

Persisted-only before/after analytics statement632/632→625/625 and branch
260/260→256/256,100% each. Complete unions have identical coverage counters:
the eight supplemental cases add NO coverage. Existing helper files unchanged,
driver49statement/16branch100 and orphan27statement/10branch100.
Zero missing lines/branches/partial branches. Four existing analytics pragma
exclusions unchanged by AST proof; no new exclusions. JWT21-byte-key warnings
retained, not suppressed. Zero skipped; deselected cases explicitly accounted.

Commands/argv/cwd/log/native exits/wrapper exits/JUnit/coverage/report/custody
stored under isolated SSD `../evidence/`; shared original coverage.ini and old12
spec command remain read-only. New TMPDIR/bytecode/Ruff cache/basetemp on SSD;
root minimum100MiB checked before every gate, no cleanup/install/build/browser.

## Process deviation and recovery

Original native374 union completed0 with real100 coverage. Its outer bash
observer exited2 because author edited LIVE union.sh to accept Coordinator's
additional persisted-only selection while pytest was running. Bash resumed an
old read offset and reported unmatched quote. This was a process error, not a
pytest failure, and outer2 is NOT declared PASS. Input/log/JUnit/coverage/native0
and wrapper2 preserved; author STOPPED before any runtime mutation or retry.

Coordinator separately admitted bounded recovery: NEW byte-frozen wrapper,
syntax0, distinct persisted-before366 gate before runtime edit. All subsequent
wrappers immutable while live and native/wrapper0 independently retained.
Read-only scratch JSON schema and installed Graphify path observation mistakes
also recorded in OBSERVATION_ERRORS.md; neither is a passing native gate.

## Ratchet

`make complexity-ratchet BASE_REF=main`: native0, findings[], baseline_commit
55a1b1d35911451e018b662c2acc450bf5994ea2. No BASE_REF substitution or baseline
synchronization. Global historical30finding check separate, NOT rerun/certified
by this slice and not absorbed into baseline.

## Graphify

`make graphify-operazioni-code`: native0, fresh module AST graph535nodes1534edges,
26communities. Parseable graph audit verifies shared distance node and extracted
calls from BOTH public route nodes. Fresh isolated corpus had no stale graph;
no pruning patch/shared tooling edit or root graph run required. Ignored outputs
not committed/imported; graph is impact evidence, not complexity/coverage proof.

## Classification

**IMPROVED / READY_FOR_REVIEW**: genuine duplicate policy removal and lower
whole-file cognition/decisions/LOC with real full100 and ratchet0. No laundering.
Independent reviewer/root gates remain required before integration.

## Files changed

- `backend/app/modules/operazioni/routes/analytics.py` only runtime;
  SHA256 `dd7a8bcd259efc1ef9853bef07a69b2123eb1cedfbcf78aa1eb0a8b645b48a2e`.
- NEW `backend/tests/test_operazioni_session_distance_r31.py`;
  SHA256 `51ce977a2da5059c75493bf7f05550f7788265a3e8dc7c6980759f4a807ae174`.
- NEW this report. Private raw evidence/freeze retained outside checkout.

## Commit

NONE. Author does not commit/push/import/merge. Source/spec/report/raws frozen
for independent review; native heavy token RELEASED after freeze publication.

## Residual risks and recommended next slice

- Fuel235/anomalies239 and other extreme/UI hotspots remain; full-project final
  backend/frontend/worker/build/E2E suites not certified by these pertinent gates.
- Persisted proof uses genuine SQLite ORM/auth; PostgreSQL concurrency or external
  integrations are not certified. None of their boundaries was modified.
- Missing-start/malformed Numeric cases are unflushed supplementation, never
  claimed valid stored records or used to reach full100.
- Review exact frozen diff and rerun independent366persisted/374complete gates.
  Do not continue on another responsibility without Coordinator ownership.
- Global original backend/frontend/worker campaign remains ACTIVE / INCOMPLETE.
