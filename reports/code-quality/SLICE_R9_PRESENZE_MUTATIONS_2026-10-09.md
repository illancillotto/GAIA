# R9 Presenze — Complexity Slice Report

## Ownership

Registry: `docs/code-quality/MULTI_AGENT_OWNERSHIP_R9_PRESENZE_MUTATIONS_2026-10-09.md`.
Dedicated worktree `GAIA-campaign-20261009-r9-presenze-mutations`, branch
`refactor/complexity-r9-presenze-mutations`. Original characterization is
integrated; the actual runtime candidate is independently source-reviewed,
frozen for source commit/final verification and not integrated. Coordinator owns implementation sequentially
after the original author/reviewer phases ended.

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

Original phase added `frontend/tests/unit/presenze-giornaliere-r9.test.tsx`:19
meaningful rendered tests. Existing tests and original runtime unchanged.
Initial test-harness
selector mistakes (KM label and `dateFrom` query key) were corrected using the
existing public UI/API; failed logs retained. No runtime workaround, skip,
timeout change, ignore or weakened assertion.

Actual candidate adds a private pure editor payload mapper, named local mutation
type and bounded factory returning one named async handler. Four preparations
retain their original guards/start-state order; one request/cache/apply/error/
finally lifecycle replaces four copies. Inline no-op success and two distinct
finish callbacks are shared. No new runtime file/hook/state/JSX/API change.

## Metric before

Page aggregate1109cognitive/1230cyclomatic/296callables/2788effectiveLOC;
21useState/13useEffect. Four target flows47cognitive/38cyclomatic/86callableLOC.

## Metric after

Actual named candidate: page1093cognitive/1231cyclomatic/308callables/
2812effectiveLOC, callableLOC4364; principal385cognitive/341cyclomatic/2023LOC.
21useState/13useEffect unchanged. All other complete runtime AST metric objects
are identical to before; no new helper/callback finding, one warning removed.

## Delta

Page cognitive−16 (−1.44%), principal cognitive−14 (−3.51%) and cyclomatic−11.
Raw aggregate cyclomatic+1, callable count+12; aggregate decisions934→923 (−11).
FileLOC+24, callableLOC+45 and principalLOC+3 are disclosed. Coordinator accepted
the raw-cyclomatic tradeoff in principle because real duplicated lifecycle
decisions are removed and the payload boundary is independently understandable.
No reduction attributed to tests alone or fabricated helper to force raw sum down.

## Tests

Author original six focused UI suites:472PASS,0skip/failure. New tests19PASS;
previous five suites453PASS. New-test ESLint and TypeScript check exit0.
Commands and failures retained under
`~/.cache/gaia-campaign/20261009-r9-presenze/author/`.
Coordinator raw coverage/runtime hash inspection confirms the stated counters.
Reviewer independently reviewed all19 new test behaviors and original oracle.
Independent original replay also472PASS/fullpage100%, typecheck/lint exit0.
Coordinator separately replayed original and actual named candidate:472PASS
each,0skip/failure. Actual typecheck/owned lint exit0, three unchanged legacy
page warnings. Actual frozen differential:101cases,64overlaps,73timingcases/
365microticks and2352payload variants; protected91helpers75hooks103other
principal statements482JSX identical. Source SHA256:
`d362df3199fbf65dc4566b56d4029fe72135c910f3e39e691b3e3535516fa940`.

Actual-source reviewer task `01a12041-d4a7-7431-a864-0c3fd0b21c5b` completed
APPROVED/IMPROVED for exact frozen source; report-only38c27eff2a8d55578ff6ed0433b307471800e364
inspected by Coordinator. Independently472PASS/fullpage100%, exact original
oracles/protectedAST/typecheck/lint/ratchet0 reproduced; 53legacyanonymous
metric/fingerprint entries identical, no hidden rename. Fullfrontend is live
Coordinator process14852; no PASS claim until terminal. Build/E2E/final verifier
remain outstanding, not certified by this source review.

## Coverage

Complete original page:1033/1033statements,1143/1143branches,294/294functions,
846/846lines,100%. Raw `characterization-coverage/coverage-final.json`, not
an aggregate percentage or a changed-lines-only claim.

Complete actual named page:1035/1035statements,1139/1139branches,306/306functions,
847/847lines,100%; Coordinator inspected raw counters. Command uses the existing
supported `VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx` with
unmodified100% gate and the same six UI suites. Earlier Coordinator command
without that variable ran472PASS but default all-campaign coverage failed for
unrelated runtime whose suites were not requested. Failure retained, explained
as command/suite-scope mismatch, not erased or claimed global coverage PASS.

## Ratchet

Characterization-only integration ratchet/mainPASS0. Actual named source
`make complexity-ratchet BASE_REF=main`:PASS0,exit0. Initial anonymous returned
handler was incorrectly associated with existing Program<anonymous> debt and
failed five metrics. The genuinely new shared lifecycle function now has its
explicit semantic name executeDailyRecordMutation; no legacy function renamed,
algorithm unchanged, exact oracles rerun PASS. Initial failure retained.
No baseline, threshold, exclusion, scope or tooling modification.

Actual global `make complexity-check`:FAIL30,Makeexit2; all thirty complete
finding objects identical to R8,zero attribution to this slice. The gate is
reported separately, not repaired/ignored or treated as a new change regression.

## Classification

Original characterization:**NO_CHANGE**. Actual runtime candidate demonstrates
an **IMPROVED** metric result with disclosed tradeoffs; independent source
acceptance complete, integration pending final certification. Not a
completed wave or global campaign success.

## Files changed

- `frontend/tests/unit/presenze-giornaliere-r9.test.tsx`
- This phase report.
- Candidate `frontend/src/app/presenze/giornaliere/page.tsx`
- `domain-docs/presenze/docs/DAILY_RECORD_MUTATIONS_REFACTOR_2026-10-09.md`

## Commit

Characterization8833a587707f9ac0e2da6389dda5757d63da9457 integrated4e903a83.
Runtime/report/domain-doc source commit authorized only after actual source
review; retrieve exact SHA through this file's git log. Source integration waits
for final certification. No main merge, push or PR.

## Residual risks

Two external prototypes rejected before source changes: wrapper A aggregate
cognitive+27/cyclomatic+41; simple factory cognitive−4/cyclomatic+15 and
decision count+1. Neither regression was applied or absorbed into baseline.

Refined external design has genuine shared persistence lifecycle, pure editor
payload mapping inside try and shared finish callbacks. Independent frozen
oracle:101cases/64overlaps/73timingcases365microticks/2352payload combinations,
protected AST unchanged; four negative controls detect intentional regressions.
External prototype estimates were superseded by the actual formatted source
metrics above. Coordinator first oracle wrapper hit cross-realm strict-array
equality; standard Node compilation fixed the harness, not runtime. Initial
comparison used oldest v1 golden whose null case substituted Error. Current
independently frozen original-v2 golden exercises actual null rejection and
matches the candidate exactly. Both failures/goldens retained; no rewritten
candidate-generated expectations. Output redirection preserves reviewer goldens.
See Coordinator CANDIDATE_HARNESS_PROVENANCE.md and named-candidate artifacts.

Readability tradeoff: additional typed callbacks versus removed repeated
orchestration. Source review must verify this remains bounded and useful;
principal385 is still extreme. Dedicated frontend Graphify refresh:649/649
sources,6029nodes12619edges247communities; forced final refresh confirms no stale
topology difference. Domain docs target withgpt-reserve:chunk1/2and2/2done,
zero semantic failure,41nodes45edges13communities,exit0;101740input/7301output
tokens,estimated$0.0524. Graph artifacts not versioned; no domain-doc edit after
that refresh. Full-suite/build/browser/final certification still pending.

## Recommended next slice

Finish this same responsibility: reviewed source commit, frozen verification,
sequential integration and final gates. Source review already terminal approved.
Do not open another hotspot. Global campaign ACTIVE/INCOMPLETE; Capacitas
coverage97.52%, thirty historical baseline divergences and extreme tail remain
separate unresolved work, not repaired or declared green by this test slice.
