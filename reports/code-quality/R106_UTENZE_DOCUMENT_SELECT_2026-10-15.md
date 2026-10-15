# R106 — Utenze document-type select isolation

## Responsibility and invariants

Two new real public mounted tests for enabled edit-mode document-type select
click isolation. Click alone preserves type,input,edit mode and initial reads,
with no update,reload,preview/download,mutation or navigation. Click-first
selection lifecycle changes type once, verifies exact API payload and update
before reload, waits for server hydration/NAS effect, re-enables editing and
clicks the refreshed select without further requests or accidental preview.
Real exported page/wrappers/domain children; API/auth/navigation boundaries
mocked only. Browser URL APIs untouched; absence of Blob output and zero
downloads asserted, not direct URL-call instrumentation.

Existing R23keyboard/row preview and R32change tables not duplicated or edited.
Ten previous specs and671runtime sources unchanged. No private-state/handler,
disabled-control or invalid-ID injection, runtime/config/shared helper/timeout
change, skip or assertion weakening. Exact new source SHA256
`e96f038e868c9239244a8064a7e622943e9c79c49a8af5e19d3d14571c0fa14e`.
Original pageb0f822da remains391cognitive304cyclomatic1908LOC; **NO_CHANGE**
runtime, not complexity reduction or runtime admission.

## Coverage and gates

| Original full page | R105 | R106 | Gain | Missing |
| --- | ---: | ---: | ---: | ---: |
| Statements |566/576|567/576|1|9|
| Branch arms |578/610|578/610|0|32|
| Functions |175/176|176/176|1|0|
| Lines |527/536|528/536|1|8|

Eleven-spec273PASS/zero failed,pending,todo,skip,unhandled. Native exit1/39.02s
preserved for unchanged100coverage thresholds; full-file100 FAIL remains9
statements32branch arms8lines. Maps/denominators unchanged; no coverage lost.
2727stable native temporal pins/86mandatory canonical inputs/671src;11actual
page-bearing provider payloads2595557B with manifest bytes/hashes checked.
Provider pre-report map equals native report and tests.json coverageMap.
No independent raw-to-Istanbul transformed-source replay claimed.

Strict670roots/663configured+6pending+setup,stricttrue/zero diagnostics,
terminal0/23.50s; scoped ESLint0/0.96s. Main ratchets and final source admission
are separately recorded in the terminal handoff, not inferred from test PASS.
One genuinely new-input native union; no retry or process interruption.
Author main ratchet0/43.97s and post-copy integration main ratchet0/43.84s,
findings[]/actualbasea51a48dc/stable2727pins. Independent unconditional final
ACCEPT_TEST_ONLY admits exact source; conditional receipt retained, reviewer
STOP. Final review manifest40cedbf5b5431297055f9b40392510ddfbaedde7955717c9d0ad52ba3a6b2943.
Frontend Graphify0/10.68s via dedicated target; remaining semantic graphs and
custody receipts belong to the terminal handoff rather than test admission.

## Isolation and residual admission barrier

Preventive ownership before dedicated author worktree/branch. Integration
HEAD7f39510ab1ef1d4e531d8b12a4eb6b36f556cee4, actualmain/merge-base
a51a48dc4caefbdd1aea82fe4d749054b9465970. R105156member seal9bb0171f verified
before71file dirty inventory; only three existing coordinator docs may change.
Five exact admitted pending specs copied with apply_patch; dependencies linked,
no installation. Preparation ACCEPT_PREP2724pins/86mandatory before execution.
No baseline/threshold/scope/exclusion/ignore/coverage-policy/runtime/shared-
tooling edits or commit,push,main merge. Preserve historical failures/refusals.

Separate read-only support audit classifies all32R105missing branch arms:
8public source paths,2plausible unproved,22guarded/contract-excluded. These
counts are static current-call-chain classifications, not new executed tests
or universally dead branches. R106 covers the previously missing select
function/statement, not those branch arms. The formatEuro null fallback has
only a numeric summary callsite; the modal Escape false arm is dominated by
effect installation and prior return. Therefore public characterization alone
cannot make this immutable full original page100 under current contracts.
Do not fabricate coverage or remove defense code without a separate decision.

A pending-save/recent-Visura-confirmation path has a concrete valid source
chain and could be a separate useful test; ANPR no-person callback remains
unproved. Neither path would remove the independent full100barriers. Avoid an
unbounded test-only campaign; keep Utenze runtime blocked pending decision and
select another original high-priority hotspot with real full-file100 evidence.

No global runtime scan/full application/build/E2E rerun for identical runtime.
Last R100metrics1681files20361callables1918errors2739warnings4657findings,
tails>300/>200/>100=3/15/55. Backend449historical skips include250later verified/
199remaining per R68–R73, none re-certified here. Full campaign ACTIVE/INCOMPLETE.

Evidence root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r106-utenze-document-select/`.
Independent final review:review/final-r106/DECISION.json. Terminal
gates,graphs,preservation audit,manifest and next action indexed by
coordinator-evidence/HANDOFF.md; support audit RESIDUAL_REACHABILITY_AUDIT.md.
