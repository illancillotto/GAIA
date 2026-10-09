# R9 Presenze — Complexity Slice Report

## Ownership

Registry: `docs/code-quality/MULTI_AGENT_OWNERSHIP_R9_PRESENZE_MUTATIONS_2026-10-09.md`.
Dedicated worktree `GAIA-campaign-20261009-r9-presenze-mutations`, branch
`refactor/complexity-r9-presenze-mutations`. This checkpoint records original
characterization, not an implemented or integrated runtime refactor.

## Baseline

Original source HEAD `1fe4a15b265b78bc45e21111e9c2aca32f6fc486`;
authoritative main/merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Main concurrent changes excluded. Runtime SHA256 before characterization:
`134a8b04c1dcd28ac8dd73b4e3a94bc24fe927f863256dfd4e28da8a3a1162f4`.

## Target callable

One responsibility: the daily-record persistence lifecycle of `persistKm`,
`persistReperibilita`, `handleSaveEditor`, `handleValidation`. Current principal
`PresenzeGiornalierePage` remains399cognitive/352cyclomatic/2020callableLOC.
No INAZ refresh, profile, meal voucher, identity, hook, JSX or API change.

## Behavioral invariants

- Token fetched once before original guards; distinct KM/reperibilita/editor/
  validation permission behavior remains intentional.
- Inline commands set saving ID and error only; editor/validation also clear
  success. Preflight/setter exceptions remain outside the request catch.
- Original payload evaluation happens inside try, after start-state writes.
- One async boundary preserves returned Promise and microtask ordering.
- Captured token and response date determine cache eviction; response apply
  precedes success. Partial failures and unconditional finally reset preserved.
- Overlap, stale selection, out-of-order completion and unmount behavior are
  characterized, not fixed or serialized.

## Characterization tests

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Distinct operational/validation permissions and ferie | Page/regressions | Cross-role mutation comparison | Three rendered cases | PASS original |
| Complete editor payload, trims and overrides | Page/regressions | Exact command payload | One rendered case | PASS original |
| Invocation token, synchronous API failure, expiry | Regressions | Four-flow synchronous/expiry matrix | Eight rendered cases | PASS original |
| Inline success retention versus editor reset | Regressions | Pending transition comparison | One rendered case | PASS original |
| Overlapping requests/scalar saving/late failure | Partial existing | Both completion orders and late error | Three rendered cases | PASS original |
| Changed response ID and stale detail selection | Partial existing | Tuple replacement plus retained current detail | One rendered case | PASS original |
| Captured token/response month after unmount | Partial existing | Same/other-month cache invalidation | Two rendered cases | PASS original |

## Changes

Added only `frontend/tests/unit/presenze-giornaliere-r9.test.tsx`:19 meaningful
rendered tests. Existing tests and runtime unchanged. Initial test-harness
selector mistakes (KM label and `dateFrom` query key) were corrected using the
existing public UI/API; failed logs retained. No runtime workaround, skip,
timeout change, ignore or weakened assertion.

## Metric before

Page aggregate1109cognitive/1230cyclomatic/296callables/2788effectiveLOC;
21useState/13useEffect. Four target flows47cognitive/38cyclomatic/86callableLOC.

## Metric after

Original runtime unchanged; all runtime metrics identical at this checkpoint.

## Delta

Runtime delta0. No complexity improvement attributed to tests alone.

## Tests

Author original six focused UI suites:472PASS,0skip/failure. New tests19PASS;
previous five suites453PASS. New-test ESLint and TypeScript check exit0.
Commands and failures retained under
`~/.cache/gaia-campaign/20261009-r9-presenze/author/`.
Coordinator raw coverage/runtime hash inspection confirms the stated counters.
Reviewer independently reviewed all19 new test behaviors and original oracle.
Independent replay of the new six-suite snapshot remains a separate gate.

## Coverage

Complete original page:1033/1033statements,1143/1143branches,294/294functions,
846/846lines,100%. Raw `characterization-coverage/coverage-final.json`, not
an aggregate percentage or a changed-lines-only claim.

## Ratchet

No runtime changed at this checkpoint; no new slice ratchet run attributed here.
Campaign integration ratchet was freshly PASS0 before this test checkpoint.
Authoritative future source gate remains `make complexity-ratchet BASE_REF=main`.
No baseline, threshold, exclusion, scope or tooling modification.

## Classification

**NO_CHANGE — ORIGINAL_CHARACTERIZATION**. Runtime refactor pending explicit
approval after exact original replay and design/equivalence review.

## Files changed

- `frontend/tests/unit/presenze-giornaliere-r9.test.tsx`
- This phase report.

## Commit

One characterization-only commit; retrieve exact SHA using `git log -1
--format=%H -- frontend/tests/unit/presenze-giornaliere-r9.test.tsx`.
No main merge, push or PR.

## Residual risks

Two external prototypes rejected before source changes: wrapper A aggregate
cognitive+27/cyclomatic+41; simple factory cognitive−4/cyclomatic+15 and
decision count+1. Neither regression was applied or absorbed into baseline.

Refined external design has genuine shared persistence lifecycle, pure editor
payload mapping inside try and shared finish callbacks. Independent frozen
oracle:101cases/64overlaps/73timingcases365microticks/2352payload combinations,
protected AST unchanged; four negative controls detect intentional regressions.
Measured cognitive−16, principal399→385; raw cyclomatic+1, callable+12,
aggregate decision count−11, fileLOC+22/principalLOC+9. This explicit tradeoff
needs Coordinator approval and exact source coverage/ratchet/review; external
prototype metrics are not runtime after metrics or integration proof.

## Recommended next slice

Finish this same responsibility: independent original replay, approved bounded
implementation, after coverage/metrics/ratchet, source review and final gates.
Do not open another hotspot. Global campaign ACTIVE/INCOMPLETE; Capacitas
coverage97.52%, thirty historical baseline divergences and extreme tail remain
separate unresolved work, not repaired or declared green by this test slice.
