# Utenze — subject edit characterization, R101

Test-only characterization of the mounted detail page, without runtime changes.
Person/company and supported unknown subjects use real edit confirmation and
enabled controls. Exact save payloads preserve nullable fields, subtype keys,
common source/status/review and manual death-date/place transitions.

Pending save disables the save button but leaves fields editable. The eventual
server response replaces the local draft and restores read-only mode. Failure
retains edited fields and permits retry; terminating editing preserves unsaved
draft values through reopening. Tests cover these existing semantics, not new
behavior. Only API/auth/navigation boundaries are mocked, not React state.

The original five-spec203 cases plus ten new cases pass. Strict TypeScript and
scoped ESLint pass. Native test command exits1 solely because original full-page
coverage remains below unchanged100% thresholds:525/576statements,518/610branch
arms,159/176functions,496/536lines. The missing-subject save guard is not reached
by fabricating private state or firing disabled controls.

DetailContent cognitive391 remains unchanged. No runtime refactor is certified;
this is a characterization prerequisite, not a complexity reduction or coverage
exception. Complete report, ownership, preserved first types failure and evidence
paths: `reports/code-quality/R101_UTENZE_SUBJECT_EDIT_CHARACTERIZATION_2026-10-15.md`.
Final independent audit REJECTED admission for evidence custody: one first-failure
compiler metadata file was overwritten by v2, and automatic raw V8 output lacks
the worker page/maps. Original diagnostic log and current native provider report
remain available; provider comparison is not a raw-worker reconstruction. New
test remains in the separate author worktree, not integration. No receipt repair,
test rerun, runtime change or100% policy exception. Future evidence capture needs
separate preparation/review with per-execution immutable metadata.

A distinct prepared capture subsequently preserved six actual page-bearing
provider payloads and pre-report map equal to native report;213cases again pass,
native1 remains unchanged coverage failure. Independent current certificate is
also REJECT: the required immediate before/after converter checksum is missing.
Current converter identity cannot retroactively fill that receipt. Both verdicts
remain explicit, no third identical test run or source admission. Only these
documents are published; runtime391 and100% policy remain unchanged.
