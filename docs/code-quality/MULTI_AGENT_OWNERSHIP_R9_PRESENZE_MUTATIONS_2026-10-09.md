# R9 Presenze daily-record mutations — exclusive ownership

Initial integration `a6e5fb7c405861b5f1aad4b55550d35f9d0115b6`, clean;
main/authoritative merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Previous goal turn PROGRESS: R8 reduced actual aggregate cognitive63/cyclomatic19,
removed5findings, independently reviewed/certified4472fullunits/build/E2E54PASS
7oldSKIP/fullpage100%/ratchetmain0. R8 source/review/verifier all terminal.
Global objective unchanged ACTIVE/INCOMPLETE; five>300callables remain.
Main dirty backend/Presenze/Ruolo/documentation concurrent work is not an input.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
|---|---|---|---|---|---|---|
| Coordinator | Governance | This registry; docs/code-quality/PROGRESS.md; reports/code-quality/MULTI_AGENT_COMPLEXITY_CAMPAIGN_2026-10-08.md | Exact design approval, ownership, integration gates | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | ACTIVE |
| R9 author | Presenze UI | frontend/src/app/presenze/giornaliere/page.tsx; frontend/src/app/presenze/giornaliere/daily-record-mutations.ts if justified; frontend/tests/unit/presenze-giornaliere-r9.test.tsx; reports/code-quality/SLICE_R9_PRESENZE_MUTATIONS_2026-10-09.md; domain-docs/presenze/docs/DAILY_RECORD_MUTATIONS_REFACTOR_2026-10-09.md | Analyze/design daily-record persistence lifecycle deduplication, then approved characterization/refactor | GAIA-campaign-20261009-r9-presenze-mutations | refactor/complexity-r9-presenze-mutations | ACTIVE |
| R9 reviewer | Independent review | reports/code-quality/REVIEW_R9_PRESENZE_MUTATIONS_2026-10-09.md only; source read-only | Original async ordering/exception oracle and protected AST, exact candidate review | GAIA-campaign-20261009-r9-presenze-review | review/complexity-r9-presenze-mutations | ACTIVE |
| R9 verifier | Independent final certification | reports/code-quality/VERIFICATION_R9_PRESENZE_MUTATIONS_2026-10-09.md only; source read-only | Frozen-source full-file coverage/fullfrontend/build/browser/ratchet | GAIA-campaign-20261009-r9-presenze-verification | verify/complexity-r9-presenze-mutations | PLANNED |

## Initial assignment: analyze/design only

Target extreme principal399cognitive/352cyclomatic/2020LOC, pageaggregate1109/
1230/file2788LOC. Single responsibility: four daily-record mutation flows
`persistKm`, `persistReperibilita`, `handleSaveEditor`, `handleValidation`.
Inspect repeated request/cache-eviction/apply/error/finally lifecycle and propose
typed domain-specific consolidation with real decision/duplication reduction.
Do not just relocate four functions or introduce megaContext/GenericManager.
Keeping local domain adapter may be safer than a new hook. New file is optional.
No automatic useReducer/hook lifecycle change or generic callback framework.
All functions/helpers including nestedcallbacks count in before/after totals.

Before runtime approval reconstruct exact preflight/token/permission order,
payload construction timing, synchronous failure boundaries, saving/error/success
state transitions, await/rejection behavior, cache token/work_date semantics,
record identity replacement/detail map, overlapping/stale requests and closure
capture. Preserving known races is required, not permission to fix behavior.
KM and reperibilita intentionally differ in authorization/preflight behavior;
editor/validation have distinct permissions, flags and success reset/messages.
Explicit characterization must cover these differences on original source.
INAZ refresh/polling/profile-save/meal-voucher callbacks/identity mapping are
out of scope. Existing `applyUpdatedRecord` and cache helper stay unchanged
unless exact design approval explicitly includes them; no incidental cleanup.

## Gates and stop condition

Author and reviewer independently verify preflight/metrics/invariants first;
design approval then original characterization must precede runtime edits.
100% statement/branch for every complete runtime modified, pertinent tests and
typecheck/lint, real aggregate cognitive/cyclomatic improvement/no laundering,
ratchetmainPASS0, independent source review before sourcefreeze/commit/integration,
then independent fullfrontend/build/browser gates. Stop this responsibility only.
No sharedlib/hooks/UI/layout/core, backend/worker, package/config/tooling/baseline/
threshold/exclusions/ignores modifications. No maincommit/merge/push/PR.
Exact reviewed campaign-only source/report commits and cherry-picks authorized
in phases by Coordinator. Unknown equivalence/concurrent edit/unexplainedfailure
stops slice. Capacitascoverage97.52%FAIL100 and historical30 baseline findings
remain separate. Do not falsely claim global target or principalbelow300.

## Preflight impact evidence

All78existingworktrees inspected for ownedpage: no dirty path.15historical/tmp
worktree handles absent, not pruned/deleted. Dirtymainbackend preserved. Last
ownedpagecommit ecdcc93c is reviewedR8, no current owner other than this registry.
Dedicated frontend Graphify query used for impact; graph not complexity proof.
Durable evidence `~/.cache/gaia-campaign/20261009-r9-presenze/`.

## Resumption — original characterization authorized

The GIS-only request is closed with independently verified evidence; it did
not authorize copying campaign code into the concurrent main checkout. The
global objective remains ACTIVE/INCOMPLETE. The previous turn confirmed the
existing GIS disposition and produced fresh readiness/ratchet evidence, but
made no further complexity reduction; resume the registered R9 responsibility.

Coordinator selects design A: one local named `DailyRecordMutation` type with
required `token`, `request`, `success`, `finish`, `errorMessage`. Preparation
executes synchronously inside the single async persistence helper before its
try; nonasync domain delegates return that exact Promise. Request payloads
execute inside try. Shared cache eviction and response application retain
their original ordering and captured token/response date. No new runtime file.

Author may now add only the registered R9 characterization test, and record
the original results in the assigned slice report. Runtime edits and commits
remain gated on explicit Coordinator approval after original tests and the
independent design oracle. Reviewer may inspect the external prototype and
extend the independent frozen-original oracle, without editing source/tests.
All overlapping microtask/error/preflight semantics must match exactly; count
every nested callback in the complexity comparison. No generic framework,
new state/hook, guard changes, or changes to the protected helpers/callsites.

Plaintext phase authorization:
`~/.cache/gaia-campaign/20261009-r9-presenze/coordinator/CHARACTERIZATION_APPROVAL.md`.
