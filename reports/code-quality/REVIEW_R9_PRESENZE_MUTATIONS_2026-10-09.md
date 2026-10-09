# R9 independent review — actual frozen daily-record mutation candidate

Date: 2026-10-09. Result: **APPROVED for this exact source candidate**.
Classification: **IMPROVED**, with the aggregate/LOC compensation below explicitly
reviewed. Global campaign remains **ACTIVE/INCOMPLETE**. This report does not
authorize integration or replace independent final certification.

## Scope and provenance

Authority: `~/.cache/gaia-campaign/20261009-r9-presenze/coordinator/CANDIDATE_REVIEW_APPROVAL.md`.
Applied root AGENTS, checkpoint skill, repository complexity skill and quality
references. Review owns this report only, in
`/home/cbo/CursorProjects/GAIA-campaign-20261009-r9-presenze-review`, branch
`review/complexity-r9-presenze-mutations`, starting HEAD
`9afd3bc57d042dc38e72d87ea43212a62e8a1c18`. Runtime/tests in that worktree were
not changed or replaced with the candidate.

Actual source examined and executed read-only:
`/home/cbo/CursorProjects/GAIA-campaign-20261009-r9-presenze-mutations`, HEAD
`8833a587707f9ac0e2da6389dda5757d63da9457` plus the frozen page delta.
Exact SHA256 values verified:

| Input | SHA256 |
| --- | --- |
| Candidate `frontend/src/app/presenze/giornaliere/page.tsx`, before/after | `d362df3199fbf65dc4566b56d4029fe72135c910f3e39e691b3e3535516fa940` |
| Original page in clean review worktree | `134a8b04c1dcd28ac8dd73b4e3a94bc24fe927f863256dfd4e28da8a3a1162f4` |
| Frozen `presenze-giornaliere-r9.test.tsx`, before/after | `c337873289d2fd58736477a969f94f8f4c3fbcc1f2ce6328d3ff9bc651266f30` |

Fresh evidence is under
`~/.cache/gaia-campaign/20261009-r9-presenze/reviewer-source/`; original goldens
and prior evidence were not overwritten. A new untracked domain documentation
file appeared in the source worktree during review:
`domain-docs/presenze/docs/DAILY_RECORD_MUTATIONS_REFACTOR_2026-10-09.md`.
The status comparison therefore differs; runtime/test hashes remain identical.
Coordinator explicitly confirmed this documentation addition and the concurrent
`SLICE_R9` report update are coordinator-owned, with runtime/tests still frozen.
They are outside source review approval. No claim of an entirely unchanged
source worktree status is made.

## Findings and behavioral review

No blocking correctness, permission, payload, timing or debt-laundering finding
was identified in the actual diff. Only the four approved daily-record handlers,
their narrow local lifecycle helpers, editor payload helper and type import are
changed. API transport, refresh/polling, collaborator profile save, meal voucher
callback, record application and cache helper remain untouched. No INAZ identity
mapping or GaTe sync change is involved.

- Preflight remains synchronous inside the returned async handler, before its
  `try`. Missing token and other no-op guards still resolve an async Promise
  without resets, requests, eviction or finalization. Throws from token lookup,
  guards or preflight setters reject without entering catch/finally, as before.
  KM still has its original distinct authorization boundary, trim/finite check,
  nonnegative rounded value and equality guard. Reperibilita retains token,
  operational permission and ferie checks in the original short-circuit order.
- Editor/validation retain distinct guards, saving flags, error/success resets,
  payloads and messages. Editor number conversion deliberately differs from KM;
  minute parsing, note trimming, reperibilita values and conditional validation
  note are unchanged. Payload construction stays inside the request invoked
  within `try`, so parse/getter/transport synchronous failures are caught.
  `buildDailyRecordEditorUpdate` preserves property evaluation order and does
  not read `validationNote` when validation permission is absent.
- The factory performs no request/state mutation during render; it only creates
  the handler. The handler synchronously prepares and invokes the request, then
  has exactly one await. There is no awaited wrapper or additional Promise
  scheduling. The no-op inline success callback adds no state reset or microtask.
- Request token is captured once per call and reused for eviction. Eviction uses
  the response date, followed by existing `applyUpdatedRecord` and per-flow
  success. The original record replacement/detail map semantics survive. Error
  fallback distinguishes actual `Error` from string/null/non-Error rejection;
  eviction/application/success failures are caught with original partial effects.
  Finish executes in `finally`, using the correct saving flag, including when
  catch fails. Existing finalizer failure masking and overlap/stale-result races
  are preserved rather than repaired.
- Function declarations become local const handlers, initialized before every
  use. All product references are later JSX callbacks; no earlier invocation,
  dependency-array use, reflection or reliance on hoisting was found. Functions
  were already recreated per render. Names and reflective `.length` do change
  for returned rest-argument functions; product code does not observe them.
  This approval concerns the current product behavior, not reflective equivalence
  of JavaScript function objects. No use of `this`, `arguments`, `super` or
  `new.target` is introduced.

Protected AST independently rerun: 91 named helpers, 75 hook calls, 103 protected
principal statements and 482 JSX nodes unchanged, no differences. Protected hash
`c4a699ecfa0544312c3815a8452db5f80b97756aea3eb9ebc3354ead3e2d2c13`.

## Identity remedy

The added returned async function is explicitly named
`executeDailyRecordMutation`; it is genuinely new, cognitive/cyclomatic/LOC
4/4/14, with no violation. This fixes its accidental participation in the
legacy `Program<anonymous>` matching pool without renaming any legacy function
or modifying the matcher/baseline. Independently scanned original and actual
candidate retain exactly 53 legacy anonymous callable entries with the identical
multiset of name/kind/fingerprint/cognitive/cyclomatic/LOC/nesting/parameters.
This includes the duplicate legacy forms implicated by the earlier five matching
findings. The new executor's identity is therefore explicit; no existing debt
is concealed as a renamed new callable. Evidence: `identity-review.json` and
fresh original/candidate metric reports. Authoritative main ratchet passes.

## Metrics and compensation

Fresh AST reports from the clean original review worktree and actual source:

| Metric | Original | Actual | Delta |
| --- | ---: | ---: | ---: |
| Page aggregate cognitive | 1109 | 1093 | -16 |
| Page aggregate raw cyclomatic | 1230 | 1231 | +1 |
| Aggregate decisions, sum(cyclomatic - 1) | 934 | 923 | -11 |
| Callable count | 296 | 308 | +12 |
| Sum of callable LOC | 4319 | 4364 | +45 |
| File effective LOC | 2788 | 2812 | +24 |
| Principal cognitive | 399 | 385 | -14 |
| Principal cyclomatic | 352 | 341 | -11 |
| Principal LOC | 2020 | 2023 | +3 |
| Findings | 33 | 32 | -1 warning |
| Errors / warnings | 13 / 20 | 13 / 19 | 0 / -1 |
| useState / useEffect metrics | 21 / 13 | 21 / 13 | unchanged |
| Complexity density | 0.838953 | 0.826458 | -0.012495 |

Raw cyclomatic grows by one and LOC grows: neither is described as decreasing.
The explicit candidate approval discloses this tradeoff for independent review.
The compensation is substantive: four duplicated request/cache/apply/catch/
finally sequences become one domain-specific lifecycle; request, success and
finish hooks preserve the four real boundaries. The pure editor payload helper
has its own testable parsing responsibility. Added functions are below warning
thresholds, not relocated hotspots. Counts include nested callbacks and the new
executor, not merely named top-level helpers. Entry constants for 12 additional
callables explain the raw cyclomatic increase while decisions fall by 11.
Cognitive falls both in the principal and over the complete page; no adjacent
runtime file absorbs the debt. The empty inline success and two flag finalizers
are small adaptation points needed for the shared lifecycle, not four copied
wrappers concealing unchanged orchestration. No new error or warning is added.
On these specific facts the slice is **IMPROVED**, not a claim that every metric
improves or that the principal/file legacy violations are resolved.

## Independently executed gates

All commands below used actual frozen source except the explicitly original
metric command. Exit codes were collected, not inferred from log contents.

1. From actual `frontend/`:
   `VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx npm run test:coverage -- tests/unit/presenze-giornaliere-page.test.tsx tests/unit/presenze-giornaliere-regressions.test.tsx tests/unit/presenze-giornaliere-r6.test.tsx tests/unit/presenze-giornaliere-r7.test.tsx tests/unit/presenze-giornaliere-r8.test.tsx tests/unit/presenze-giornaliere-r9.test.tsx --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261009-r9-presenze/reviewer-source/coverage`
   — exit 0, 6 suites / 472 tests PASS. Full page statement 1035/1035,
   branch 1139/1139, function 306/306, line 847/847, all **100%**. JSON contains
   exactly the actual page path. Existing four 100% thresholds remained enabled;
   no exclusions, skips, config changes or weakened tests. See `coverage.log`
   and `coverage/coverage-final.json`.
2. From actual root:
   `node /home/cbo/.cache/gaia-campaign/20261009-r9-presenze/coordinator/run-candidate-oracles.cjs frontend/src/app/presenze/giornaliere/page.tsx ../reviewer-source`
   — exit 0. 101 cases, 64 overlap schedules, four microtask flows, 73 timing
   cases (365 microticks), 2352 original/candidate payload variants and protected
   AST PASS. Exact events/state/overlaps/timing compared against immutable
   `oracle-original-v2.json` and `timing-original.json`. The same-realm runner
   adapts entry points and redirects output only; assertions are unchanged.
   Earlier VM-realm and v1 null-rejection harness errors remain preserved in
   provenance; the erroneous oldest v1 oracle is not used as the golden.
3. From actual `frontend/`: `npm run typecheck -- --incremental false`
   — exit 0; disabled incremental output to avoid writing source-tree artifacts.
   `npm run lint -- --file src/app/presenze/giornaliere/page.tsx` — exit 0,
   three legacy warnings: unused `isLoadingRecordDetail`, hook dependencies
   `closeSelectedRecord` and `contractProfileEditor`. No new warning or ignore.
4. From actual root: `make complexity-ratchet BASE_REF=main` — exit 0,
   authoritative baseline commit `55a1b1d35911451e018b662c2acc450bf5994ea2`,
   zero findings. `ratchet.log` preserves the full changed-path scope. No
   baseline synchronization, verification claim or threshold/tooling edits.
5. From actual root and separately clean original review root:
   `python3 tools/code_quality/complexity.py report frontend/src/app/presenze/giornaliere/page.tsx --json <fresh reviewer-source metrics path> --markdown <fresh reviewer-source markdown path>`
   — both exit 0; `metrics.json`, `original-metrics.json` and identity comparison
   independently reproduce the table above. SHA comparisons before/after PASS;
   source `git diff --check` PASS. Tests/config/tooling have no working-tree diff.

Coordinator's `candidate-graphify-code.log` records dedicated
`make graphify-frontend GRAPHIFY_CODE_FLAGS=--force`: 649 source files extracted,
6029 nodes / 12619 edges, exit success. This is prior coordinator evidence,
not a reviewer-executed refresh. No report-only graph update is required here;
no runtime or general platform/domain documentation was modified by reviewer.

## Residual risk and handoff

The principal remains 385 cognitive / 341 cyclomatic / 2023 LOC, still above
300 and legacy thresholds. The page retains 13 errors and 19 warnings. Existing
overlap races, shared saving flags and stale completion behavior remain.
Reflective function-object metadata differs as disclosed. Targeted 100% page
coverage is not global frontend/repository coverage or a browser proof.
No full suite, build or E2E was run in this review slot; independent verifier
gates remain outstanding. Capacitas 97.52% coverage and thirty historical
baseline divergences remain separate. No source commit, integration, main
change, push, PR or new goal was performed.

Report-only commit is authorized by the exact review approval. Its final SHA
and terminal result are recorded outside git in `reviewer-source/REPORT_SHA.txt`
and `reviewer-source/REVIEW_RESULT.md` after commit. Coordinator may proceed
only with this exact reviewed source and the separately authorized next phase.
