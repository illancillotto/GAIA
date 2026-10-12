# Bonifica — result normalization slice R64

The background sync keeps the existing entity dispatch, credential/session
lifecycle, fetched rows, runtime snapshots, synchronous domain services, entity
order, transactions and cleanup. A small same-file `_normalize_sync_result`
converts explicit selected counters and `list[str]` into `_SyncExecutionResult`.
It counts every error, preserves order and joins only the first20 messages;
an empty list produces `None`, whereas one empty string produces `""`.
Reports' event counters and organization-chart entry counters are not substituted
for the existing synced/skipped counters. Vehicle, refuel and usage-session
counters remain explicitly selected at their respective call sites.

This deduplicates ten deep conditional normalizations into one shallow pure
policy. No generic context, dynamic attribute dispatch, relocation or new
orchestration framework is introduced. The legacy service remains in place;
moving responsibilities into a domain module is not necessary for this slice.

Measured candidate: orchestrator cognitive269→174, cyclomatic47→37, LOC232→202.
Whole-file cognitive422→328, cyclomatic181→173, effective LOC738→717.
Helper cognitive1/cyclomatic2/LOC9/parameters3 has no findings; nesting13 in
the orchestrator is residual debt, not claimed fixed.

Six pertinent suites preserve existing route/domain integration tests and add
67 cases for concrete result shapes, SQLite persistence, partial failure,
continuation, commit sequence, truncation boundaries, whitespace/newline/empty
messages and error-list operation order. Original required-email fixture
failure is preserved; the user-approved one-field test correction does not
change runtime, schema or assertions. OriginalV2 and candidate253 cases pass.
Independent candidate full-file statement400/400 and branch126/126 coverage100;
two preexisting excluded unsupported-entity lines remain explicitly unverified.
SQLite does not prove PostgreSQL concurrency/provider production behavior.

Coordinator exact integration also verifies253PASS and400statement/126branch100;
full report is exact to the author candidate. Post-integration ratchet, Graphify
and publication receipts bind final admission. The campaign goal remains
ACTIVE / INCOMPLETE; no changes to baseline, thresholds, exclusions, coverage
policy, tracked main runtime or external services.
