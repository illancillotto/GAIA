# R8 Presenze daily-record presentation — ownership and design gate

Initial integration `c9216c5a`, clean; main/authoritative merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. R7 owners and processes terminal,
full-file coverage100%, fullfrontend4428PASS/buildPASS/fullE2E54PASS7oldSKIP,
post-report ratchetmainPASS0. Global campaign remains ACTIVE/INCOMPLETE.
Main dirty backend/Presenze/Ruolo/docs work is not copied or modified.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
|---|---|---|---|---|---|---|
| Coordinator | Governance | This registry; docs/code-quality/PROGRESS.md; reports/code-quality/MULTI_AGENT_COMPLEXITY_CAMPAIGN_2026-10-08.md | Scope/design approval and integration gates | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | ACTIVE |
| R8 author | Presenze UI | frontend/src/app/presenze/giornaliere/page.tsx; frontend/src/app/presenze/giornaliere/record-presentation-model.ts; frontend/tests/unit/presenze-giornaliere-r8.test.tsx; reports/code-quality/SLICE_R8_PRESENZE_PRESENTATION_2026-10-09.md; domain-docs/presenze/docs/RECORD_PRESENTATION_REFACTOR_2026-10-09.md | Shared daily-record display projection, design only until approved | GAIA-campaign-20261009-r8-presenze-presentation | refactor/complexity-r8-presenze-presentation | ACTIVE |
| R8 reviewer | Independent review | reports/code-quality/REVIEW_R8_PRESENZE_PRESENTATION_2026-10-09.md only; all source read-only | Original characterization/differential oracle and exact candidate review | GAIA-campaign-20261009-r8-presenze-review | review/complexity-r8-presenze-presentation | ACTIVE |
| R8 verifier | Independent certification | reports/code-quality/VERIFICATION_R8_PRESENZE_PRESENTATION_2026-10-09.md only; all source read-only | Frozen-source coverage/fullfrontend/build/browser/ratchet | GAIA-campaign-20261009-r8-presenze-verification | verify/complexity-r8-presenze-presentation | PLANNED |

## Design-only initial assignment

Inspect the still-extreme principal403cognitive/356cyclomatic/2020LOC, identify
one coherent shared daily-record presentation responsibility across matrix,
collaborator modal and detail rendering, and propose concrete simplification
before editing runtime. Avoid another nominal JSX move or giant hook. Prefer
removing repeated branching/conditions through typed pure domain projections.
Original formatting, null/zero/NaN behavior, icon precedence, DOM/accessibility,
input controlledness, permissions, commands, API, identity and all React hook
order/dependencies/cleanup must remain equivalent. Parent retains lifecycle
and mutation flows. New projections must be genuinely small and below error
thresholds; no complexity laundering or component explosion.

Desired direction: substantially lower the extreme tail, ideally principal
below300 within this responsibility; report feasibility honestly rather than
force metric tricks. Aggregate cognitive/cyclomatic of every affected callable
must actually fall. Design must state precise original branches/call sites,
invariants, expected aggregate benefit and full-file test matrix. Coordinator
must explicitly approve design and original characterization before runtime.
If this scope is not coherent, report a bounded alternative without editing.

## Gates and stop condition

Analyze current worktrees/status/log and metrics before edits. First execute
original characterization; then100% statement/branch on every complete runtime
file modified, focused tests/typecheck/lint, measured before/after including
all helpers, ratchetmainPASS0, independent source review, and final integration
gates. Stop after assigned responsibility. No shared lib/hooks/UI/layout,
backend/worker, package/config/tooling/baseline/threshold/exclusion/ignore changes.
No main commits/merge/push/PR; exact reviewed campaign commits/cherry-picks only.
Unknown equivalence, active concurrent source edits or unexplained failures
stop the slice. CoverageCapacitasFAIL and historical30 remain separate.
Durable evidence `~/.cache/gaia-campaign/20261009-r8-presenze/`.

## Original characterization approval

Author exact design and reviewer assessment inspected. Scope narrowed to finite
cell primary/secondary/detail badge policies and FormulaGAIA status variant/text
pair, implemented locally rather than unnecessary model file. Technical absence,
header, tooltip/classification, all hooks/DOM/lifecycle/commands excluded.
Author may add original-source rendered characterization only; runtime approval
requires baseline full-file100% and these tests passing first. Preserve inherited
key rejection for unknown causes, ordered substrings, nullish/NaN/holiday/auth
precedence. Expected aggregate40-60 cognitive decrease, principalabout8, not<300.
Reviewer original-AST2800adversarial fixtures frozen before candidate. Every77
existing worktree inspected, no dirty owned page;15historical/tmp paths absent,
not cleaned. Ignored established dependency symlinks authorized, no installs.
Plaintext `coordinator/CHARACTERIZATION_APPROVAL.txt` is authoritative.

## Runtime approval after original gates

Author/reviewer independently424focusedPASS/fullpage1048statements1189branches
100%,44newrendered originalUI PASS; root confirms whole beforeAST identicalR7.
Original pageSHA06d0bec0 unchanged. Earlier smokecommand error and whitespace
normalizer selector failure retained/explained, corrected exact text assertion
does not modify runtime. Author now authorized accepted exact local labelpolicy
whitelist only, not lifecycle/JSX moves/unrelated cleanup. Final completepage100%,
aggregate actual improvement/no helpererror, ratchetmain0/review mandatory.
Plaintext `coordinator/RUNTIME_APPROVAL.txt`; all original processes terminal.
