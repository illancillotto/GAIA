# R7 Presenze anomaly-panel ordering/grouping — ownership

Initial integration `ef322424ff54e829daee5e4bd5bd01a7aab1ebb7`, clean.
Authoritative main/merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Dirty main is preserved and is not an input. R6 source/review/verifier are
terminal; all previous ownership closed. Goal remains ACTIVE/INCOMPLETE.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
|---|---|---|---|---|---|---|
| Coordinator | Governance | This registry; docs/code-quality/PROGRESS.md; reports/code-quality/MULTI_AGENT_COMPLEXITY_CAMPAIGN_2026-10-08.md | Approve one bounded responsibility and integration gates | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | ACTIVE |
| R7 author | Presenze UI | frontend/src/app/presenze/giornaliere/page.tsx; frontend/src/app/presenze/giornaliere/anomaly-panel-model.ts; frontend/tests/unit/presenze-giornaliere-r7.test.tsx; reports/code-quality/SLICE_R7_PRESENZE_ANOMALY_2026-10-09.md; domain-docs/presenze/docs/ANOMALY_PANEL_REFACTOR_2026-10-09.md | Shared anomaly grouping/counting/comparator policy, no JSX/lifecycle changes | GAIA-campaign-20261009-r7-presenze-anomaly | refactor/complexity-r7-presenze-anomaly | MERGED |
| R7 reviewer | Independent integration | reports/code-quality/REVIEW_R7_PRESENZE_ANOMALY_2026-10-09.md only, all source read-only | Independent design/source review, original differential oracle, before/after full-file coverage | GAIA-campaign-20261009-r7-presenze-review | review/complexity-r7-presenze-anomaly | MERGED |
| R7 verifier | Independent final verification | reports/code-quality/VERIFICATION_R7_PRESENZE_ANOMALY_2026-10-09.md only, all source read-only | Frozen source full frontend/build/browser/ratchet after review | GAIA-campaign-20261009-r7-presenze-verification | verify/complexity-r7-presenze-anomaly | ACTIVE |

## Scope and stop condition

Continue the extreme frontend queue. Provisional principal420cognitive/
371cyclomatic/2076LOC; do not claim original50%/under250 target achieved.
Single responsibility: anomaly-panel ordering/grouping preparation, not its
entire component, editor, effects, state machine or API. Author must present a
typed design, exact original invariants and current metrics before runtime
edits. Characterization on original first; all modified complete runtime
files100% statement/branch coverage, real aggregate cognitive/cyclomatic
reduction, no helper violation, ratchet/mainPASS0 and independent approval
before integration. Stop after this responsibility, reject laundering.

Preserve priority/date/name precedence, stable sorting, fallback labels,
duplicate entries, grouping/counts, selected first record, filter semantics,
immutability and every UI action/result. Classification, identity, permissions,
auth, lifecycle/effect dependencies and commands are out of scope. No shared
lib/hooks/UI/config, backend/worker, baseline/threshold/scope/ignore changes.
No main commit/merge, push or PR. Reviewed campaign-only commits/cherry-picks.

Main and relevant Presenze/R3/R6 worktrees have no dirty owned frontend paths;
committed older work on other branches is not an observed active edit. Inspect
again before modification; concurrent edits block ownership. Graphifyfrontend
query used for orientation; metrics proof is AST report, not graph.
Durable evidence `~/.cache/gaia-campaign/20261009-r7-presenze/`.

## Pre-design critical invariant

Priority uses `base * 100000 - operational_missing_minutes`. The original
comparator tests `priorityOrder !== 0`: NaN is returned rather than falling
through to date/name. Infinity differences can also becomeNaN. An `||` chain,
defaulting or data sanitization would change stable order; explicitly preserve
this behavior and characterize it. No functional cleanup is authorized.

## Bounded design approval

Reviewer conditionally approves domain-specific comparator factory with lazy
strict `!==0` chain, insertion-ordered shared grouping/count collector and
distinct day/collaborator builders. Root inspected fresh author413PASS and
page1094/1094statement1217/1217branch100%; beforeAST exactR6confirmed. Root
approves original-source characterization tests first, then runtime changes
only after those pass. Source replacement limited to month ordering and two
panel grouping preparation callbacks/types, same dependency arrays. No other
model/helper/hook edits. Newly extracted helpers must be genuinely small and
typed, no generic framework or error-level new callable. All final gates still
pending. Principal420 is still extreme, not50% target success.

## Reviewed integration

Author source `d879d2681841f2bbab6b885648ed6cfa8e847c1c` frozen clean; final424
focusedPASS/page1048s1189b/model39s16b100%,ratchetmain0/typecheck/lintPASS.
Independent reviewer report-only `a7341048` APPROVED/IMPROVED,424PASS/fullfile
100%, originaloracle180fixtures2917entries59593comparatorpairs720filteredgroups
and3NaNtrapsPASS/protectedASTexact. Source integrated `bee3fd53` and review
`1699e790`, all5sourcefiles exact. Source duplicate7307d091 not integrated.
Coordinator approves verifier exactsource application/full frontend/build/
browser gates in durable plaintext `coordinator/VERIFY_APPROVAL.txt`.
Author/reviewer terminal; verifier gates pending, notPASS. No main merge.
