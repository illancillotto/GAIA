# R12 Capacitas — rerun/delete command lifecycle ownership

## Scope and authority

The previous goal turn was PROGRESS: R11 source, independent certificate and
closure integrated at clean `f0b6e00e4f41d2fe54f504d4fe700613ae4b2c83`, actual
post-commit main55a ratchet PASS0. Global campaign remains ACTIVE/INCOMPLETE.
Read the original goal attachment and campaign instructions; Capacitas priority
and complete-file100% policy remain confirmed. Do not redefine the global goal.

Main/base `55a1b1d35911451e018b662c2acc450bf5994ea2`; concurrent main binary diff
`9f85e574...114664b` and status `0d54d4eb...735e87` unchanged. All R11 agents are
terminal and release their ownership. Reuse their clean dedicated worktrees on
NEW R12 branches from the accepted integration snapshot; do not reuse old gate
results as fresh tests. No worktree deletion/pruning/reset/stash/source copying.

## Registry

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Coordinator | Governance | This registry; docs/code-quality/PROGRESS.md; private phase approvals/checkpoints; later global/integration/domain docs only with explicit allocation | Ownership, phase gates, exact-source publication/integration | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | ACTIVE |
| R12 author (01a120c5-d838-7251-b33b-52a5f9b03b48) | Capacitas command lifecycle | reports/code-quality/READINESS_R12_CAPACITAS_COMMANDS_2026-10-09.md only initially; runtime path read-only; external prototypes allowed | Analyze eight rerun/delete handlers, fresh original coverage/invariants, measured candidate design; no runtime implementation yet | GAIA-campaign-20261009-r11-capacitas-monitors (reused clean worktree) | refactor/complexity-r12-capacitas-commands | ACTIVE |
| R12 reviewer/integrator (01a120c7-5237-7f02-9fe7-352e65b9a6ed) | Independent original command behavior/design | reports/code-quality/REVIEW_READINESS_R12_CAPACITAS_COMMANDS_2026-10-09.md only initially; source/test/config read-only | Inspect original token/API/busy/refresh/error/updater ordering and microtasks, independently review candidate before implementation | GAIA-campaign-20261009-r11-capacitas-monitors-review (reused clean worktree) | review/complexity-r12-capacitas-commands | ACTIVE |
| R12 final verifier | Frozen-source certification | Future distinct VERIFICATION_R12 report only after explicit source freeze/phase allocation | No task active before candidate review and original characterization | Dedicated clean final worktree to be assigned | To be assigned | PLANNED |

No runtime file has two owners. Shared lib/hooks/UI/tooling/config/baseline and
all previous nineteen specs and policy files remain read-only. Coordinator
does not implement a competing source candidate in the owned runtime file.

## Bounded responsibility

Runtime target: `frontend/src/components/elaborazioni/capacitas-workspace.tsx`.
Exactly eight handlers: handleRerunJob, handleDeleteJob,
handleRerunParticelleJob, handleDeleteParticelleJob, handleRerunHistoryJob,
handleDeleteHistoryJob, handleRerunIncassJob, handleDeleteIncassJob.
Shared token/busy/API/error/finally lifecycle is genuinely duplicated. Rerun
refresh and delete functional filtering remain action-specific. Do not extend
to create/import/parse/speed/stop/render/polling or fix original races.

Accepted R11 planning snapshot (acquire fresh locally): principal391cognitive/
360cyclomatic/2527LOC; workspace3096effectiveLOC253callables923sumcognitive/
1053sumcyclomatic,31useState2useEffect. Each original rerun/delete handler
4cognitive/4cyclomatic,16/15LOC respectively. Combined unchanged-policy scope
926cognitive/803decisions/3131effectiveLOC/259callables. Include all nested
callbacks, raw cyclomatic and decision totals before/after; no debt laundering.

## Required original characterization and candidate evidence

Reconstruct user action → token/busy → exact API → expiry/status/error →
reload or functional row update → busy release; missing token, real Error,
non-Error rejection, auth failure, list failure and deferred overlaps. Preserve
exact strings, IDs, API signatures, getter laziness, closure capture, state
updater semantics and all old manual/polling/rerun/delete races.

Do not introduce an extra await or asynchronous success wrapper that changes
busy-release/refresh microticks. A typed domain helper may own actual duplicate
phases, not be a mega context, generic manager or moved mega handler. Any candidate
must have genuinely lower combined cognitive/decisions and no transferred debt,
authoritative full-context main55a comparator PASS0 and no new lint warning.
No suppression, baseline generation/repair, threshold or exclusion changes.

Original fresh nineteen-spec explicit coverage union should measure396PASS and
full-file100% on both workspace and fraction policy. Retain any failed attempt
honestly; do not weaken tests or fill branch counters with fake fixtures/private
React access. Build a behavior/test matrix and identify genuinely missing paths
before authoring a new rendered characterization spec with explicit ownership.
First phase is ANALYZE/CHARACTERIZE/DESIGN ONLY. Do not commit/merge/pick,
write runtime/tests/config or start another hotspot without Coordinator phase
approval. Author holds the first heavy-test window; reviewer initially uses
bounded read-only/static/differential analysis only. Independent heavy replay
follows terminal author evidence and an explicit slot transfer.

## Stop condition

One coherent eight-handler lifecycle responsibility; preserved behavior,
100% complete modified runtime, green pertinent tests/type/lint/ratchet,
independent original/source review, distinct final certificate and sequential
integration. Stop on ambiguous invariants/matching or an unexplained new failure.
Do not call the global campaign complete after this slice.
