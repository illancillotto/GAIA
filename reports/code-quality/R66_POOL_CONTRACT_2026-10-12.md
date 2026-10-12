# R66 — Dynamic SISTER pool completion contract

## Scope and snapshot

Read-only diagnosis following the committed R65 helper coverage closure.
Dedicated branch `refactor/complexity-campaign-20261008`, starting HEAD
`a6d4b7833dbf4a1bfdbd7879217930ddca88a8d0`; actual main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Global objective remains INCOMPLETE.
No new runtime refactor, guard removal, coverage exclusion, policy change,
baseline rewrite or manufactured worker100 certificate is authorized here.

Read-only pool SHA256:
`b39a936771c238e13d63f82b8b269a55118818c9ea1d8ccdd3e4cf6b080ff894`.
Read-only worker SHA256:
`bc8fec11dd44688161d7c5f32f3b5b029d50280b033d861c5ae0fc3c7b9607bf`.
Ownership registered before native work; PROGRESS and original registry frozen.

## Remaining coverage issue

R50 records pool statement523 and branch522→523 uncovered. R65 genuinely closes
the separate retry metadata gap, not this pool gap. The repeated completion
guard in `run_dynamic_credential_pool` is tempting to delete because line511
already checks completion and there is no explicit suspension before line522.
That observation alone is not a universal equivalence proof.

## New evidence: production contract

AST audit of current backend/worker runtime finds one actual pool call site:
`worker.py:1157`. Its callbacks are the real synchronous production functions:

- `refresh_shared_credential_pool`: queries current credentials, then excludes
  IDs in `started_ids` and `pool.rejected_ids`.
- `_batch_has_open_requests`: synchronous DB query.
- `announce_expanded_credential_pool`: synchronous status announcement.
- `_set_batch_operation`: synchronous DB update/commit.

All four definitions are synchronous and have no AST await/yield. The interval
after the first completion check and before the second contains no suspension.
The actual runtime source scan finds no configured eager/custom task factory,
nest_asyncio, uvloop or run_until_complete use. Worker entry uses asyncio.run.
This source audit does not enumerate arbitrary external DB event plugins,
signal handlers, monkey-patched libraries or deployed image bytes.

Under normal cooperative execution, the first false check implies a pending
runner T exists. Its ID remains in `started_ids`, because only done IDs are
removed. The production refresh therefore cannot replace T's dictionary entry.
The interval does not yield, so T cannot resume and complete. New eager-created
tasks may finish inline, but cannot make the preserved T complete. Thus the
second check remains false under this specific production callback contract.
Event.set completes waiter Futures; coroutine wakeups are scheduled, not run
inline. Local CPython3.12.3 stdlib source/hashes and callback docs are captured.

## New native observations, not fabricated coverage

Two real pool scenarios use actual SQLAlchemy credential objects, genuine
asyncio tasks/Event and read-only sys.settrace observations. A pending original
runner is released by a synchronous announcement; a distinct late credential
is introduced. Neither Task.done nor asyncio.wait is mocked or replaced.

| Native factory | First check511 | Second check522 | Next check511 | Outcome |
| --- | --- | --- | --- | --- |
| Default | original pending | original pending, new pending | both done | Both real runners finish |
| Official eager | original pending | original pending, new done | both done | Both real runners finish |

Both variants PASS the observation assertions, sole native probe exit0.
The official eager factory is exercised explicitly as a robustness experiment;
it is not installed in application runtime. These are diagnostic experiments,
not a coverage run, persisted DB test or production portal certification.

## Counterexample: do not claim a universally dead branch

A distinct native diagnostic deliberately returns an already-started credential
ID from the refresh callback. This violates the actual production filter but
is not rejected by the exported callable's type signature or runtime boundary.
With official eager scheduling, the dictionary replaces the still-pending task
with an immediately completed real task. Observations are511false→522true→523.
The original task remains pending when the pool returns; it is explicitly
cancelled and gathered afterward so no owned runner leaks from the experiment.
Separate native exit0, raw trace and cleanup assertions preserved; no retry.

This confirms the guard is reachable with a callback-contract violation. It
refutes an unconditional "line523 is impossible" claim, not the narrower
production proof. It must NOT be admitted as a fake coverage-closing test or
used to turn worker100 green. No code is changed to accommodate that input.
The missing branch is retained honestly rather than covered by misrepresenting
production semantics. Future cleanup needs an explicit supported callback
contract and an equivalence review; runtime hardening would itself be a
separate behavioral decision, not test consolidation.

## Result and gates

Classification: **DIAGNOSED — NO_SAFE_UNIVERSAL_CLEANUP**.
No runtime complexity reduction or full-worker100 PASS. Runtime/test/config
input identity is checked against R65 and current frozen sources; baseline,
thresholds, exclusions, coverage policy and main remain unchanged.
Last measured official metrics remain1681files/20360callables,
1920errors/2736warnings/4656overlapping findings, without a new full report.
No complete backend/frontend/worker/E2E suite is blindly repeated.

Independent review, the actual-main ratchet and publication receipts are bound
in the companion `R66_POOL_CONTRACT_2026-10-12.json` after terminal publication.
Known global baseline ambiguity stays distinct from the change ratchet.
Worker full coverage remains FAIL; PostgreSQL worker skip,449backend skips
and7E2E skips remain NOT VERIFIED. R43/R51/R63 and strategic targets remain open.

## Durable handoff and next decision

Evidence root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r66-pool-contract`.
Raw argv, logs, exits, probes, source freezes, AST audit, task observations and
independent review remain separate immutable receipts. No push or main merge.

Next decision: preserve the guard until the supported callback contract is
explicitly approved. Investigate other genuine test gaps in a separately
owned slice instead of deleting code merely to attain rounded coverage100.
