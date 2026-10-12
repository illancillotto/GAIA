# Bonifica — inherited date guard prerequisite

The campaign removes only an unreachable inner decision in `_resolve_job_params`
within `backend/app/services/elaborazioni_bonifica_sync.py`. The outer predicate
already ensures a date-aware entity. `_resolve_date_window_from_job` calls the
date-aware resolver synchronously: successful resolution produces both dates;
validation/overflow failures propagate unchanged. Assign the inherited dates
directly, preserving parsing, default windows, explicit-date and multi-entity
bypass, latest-job query ordering, response and exceptions.

Author, independent final and integration root each verify186tests (89new).
Full-file statement398/398 and branch126/126 coverage100%; no new exclusions or
test-policy change. Root ratchet against authoritative main55a has zero findings.
Target cognitive18→10, cyclomatic12→9, nesting3→2; aggregate cognitive430→422.
No responsibility moved, no DB/retry/external-call change. Original coverage
FAIL100 on unreachable branch is preserved, not misreported as original PASS.

This is a separate prerequisite, not the orchestrator refactor. The background
orchestrator remains cognitive269/nesting13; result normalization remains a
distinct future slice requiring characterization and authorization. Main and
baseline unchanged. Campaign ACTIVE/INCOMPLETE; no main merge or commit.
