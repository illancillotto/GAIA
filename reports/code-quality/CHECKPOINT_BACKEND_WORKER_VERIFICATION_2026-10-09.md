# Checkpoint — complete backend and worker verification, 2026-10-09

**BACKEND PASS; WORKER FAILED / INCOMPLETE. Heavy RELEASED after terminal audit.**
Global campaign remains **ACTIVE / INCOMPLETE**. This is checkpoint evidence on
`34c13604f49de64ced59bf6846998556e7c873b9`, not last-wave/global certification.

## Ownership and reproducibility

Distinct checkpoint verifier TUI `01a1222c-ba79-7a42-8717-4bd1b8374ce0` read FIRST
the integration checkpoint ownership registry. Work exclusively in
`/home/cbo/CursorProjects/GAIA-campaign-20261009-suites-verification`, branch
`verify/complexity-campaign-suites-20261009`. HEAD and merge-base/main
`55a1b1d35911451e018b662c2acc450bf5994ea2` captured before/after.
Initial working tree clean; all existing tracked source, tests, configuration,
tooling, baseline and reports read-only. The sole repository write is this report.
R14 actors terminal/released per registry; R16 author `01a12214` and reviewer
`01a121e9` revalidated idle/completed via actual TUI read/list. No R16 matching
analysis, candidate application, source/refactor/fixture/config fix or commit/import.
No competing project pytest observed at preflight. Exclusive heavy suite window;
backend and worker serialized. No restart, retry, exclusion or provider opt-in.

Installed interpreter: `/home/cbo/CursorProjects/GAIA/backend/.venv/bin/python`,
Python 3.12.3; no installation or package changes. Private fresh evidence:
`/home/cbo/.cache/gaia-campaign/20261009-checkpoint-suites/verifier/`. Exact argv, cwd, synthetic environment, runner and child PID/start-ticks
in `*-invocation.json`, `*-process.json`. Parent environment replaced with a
minimal test environment: APP_ENV=test, disposable SQLite in private evidence,
synthetic JWT/mobile/bootstrap/master-key settings, no portal/PostgreSQL credentials.
No worktree `.env` exists. PYTHONPATH includes worktree root + backend + worker.
Bytecode, pytest cache and temp paths external; backend default pytest selection
and configured addopts/warning filters preserved. `-ra` and JUnit only add evidence.

## Suite outcomes

| Suite | Result | Passed | Skipped | Failures/errors | Evidence |
| --- | --- | ---: | ---: | --- | --- |
| Complete backend, backend cwd | PASS, exact child exit 0 | 6714 | 449 | 0 / 0 | backend.log, backend-junit.xml, backend-exit.json |
| Complete existing make test-worker, one attempt | FAILED / INCOMPLETE | 116 observed | 0 observed | Coverage/process evidence infrastructure failure; no test assertion failure observed | worker.log, worker-runner-failure.txt, worker-terminal-observation.json |

Backend raw summary: `6714 passed, 449 skipped, 19 warnings in 1371.68s (0:22:51)`.
JUnit independently contains 7,163 cases: 6,714 passed, 449 skipped, zero errors
and failures. JUnit time 1371.497 s; pytest summary 1371.68 s; runner child elapsed
1385.117396 s. Native session **33706 terminal exit 0**, exact pytest PID **2202976**
reaped; `/proc` absent. All 19 warnings retained in raw log and
`backend-warnings.txt`: runpy already-imported module warnings and Pydantic
serializer warnings. Configured default filters intentionally unchanged.

## All backend skips

447 PostgreSQL-dependent cases unavailable, 1 OSGeo and 1 pyproj unavailable.
These are skipped, not passed; no disposable PostgreSQL provisioned/opted in.
Every skipped testcase name, reason and original detail is retained in
`backend-skips.json`, `backend-skips.tsv` and raw JUnit, with full names below.

| Exact reason | Count |
| --- | ---: |
| GAIA_TEST_POSTGRES_URL non configurato | 161 |
| GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race | 120 |
| Concorrenza verificata su PostgreSQL, non simulata da SQLite | 2 |
| Concorrenza reale verificata su PostgreSQL | 6 |
| Concorrenza e row lock richiedono PostgreSQL | 1 |
| GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza | 111 |
| PostgreSQL integration tests require a PostgreSQL DATABASE_URL | 18 |
| OSGeo non disponibile per generare lo shapefile di test. | 1 |
| pyproj non disponibile per il fallback pyshp. | 1 |
| PostgreSQL integration tests require TEST_DATABASE_URL to be configured | 14 |
| GAIA_TEST_POSTGRES_URL not configured | 12 |
| TEST_WHATSAPP_POSTGRES_URL requires a disposable PostgreSQL | 2 |

## Worker failure and all discovered file outcomes

Unmodified existing `make test-worker` discovered 52 files in sorted order and
preserved separate Python/coverage/pytest processes for each file. Overrides only
select the installed interpreter and external coverage output destinations.
`PYTEST_ADDOPTS=-ra` adds skip reporting, not selection. No fixture/test exclusions.

Eight files reached pytest summaries totaling 116 PASS, no skips/assertion errors.
The eighth (`test_captcha_solver.py`) printed `4 passed` / pytest `SystemExit: 0`,
then coverage save failed with `sqlite3.OperationalError: no such table:
coverage_schema`, `coverage.exceptions.DataError`, and raw Make `Error 1`.
Concurrently the private process recorder failed with **OSError [Errno 28]
No space left on device**. Native session **83403 exit 1**. Original Make PID
**2254220** and final coverage PID **2254413** absent on terminal observation.
The recorder failure prevented reaping/logging the exact Make process returncode;
that numeric code is **unavailable**, not inferred from the raw Make diagnostic.
Original partial `worker-descendants.json` retained, validity/remaining PID
observations in `terminal-audit.json`. No wrapper timeout/restart/retry.

Disk observation after the failure: filesystem at 100%, 73 MiB available; own
bytecode cache 88 MiB, backend test temp evidence 188 MiB. Removed **only this
verification's 88 MiB disposable bytecode cache** to permit durable evidence/report
writes; `cache-cleanup.json` retains exact before/after filesystem observations.
Backend test temp, SQLite, raw logs/JUnit and partial recorder evidence preserved.
The existing Make EXIT trap removed its own `gaia-worker-coverage.HXw8WX` temporary
coverage data. No final worker JSON/XML/combine report produced. No full worker
coverage assertion is possible. ENOSPC and coverage data save failed in the same
incident; the raw worker traceback itself reports the missing schema, not a test
assertion or direct ENOSPC message. No further cause/semantic diagnosis delegated.

The next 44 files were NOT RUN, not skipped. First seven coverage invocations
returned sufficiently for Make to advance; eighth pytest PASS does not certify
its failed coverage invocation. Fresh partial counts supersede any provisional
first-file interpretation; previous 778PASS/1SKIP/52files is historical only.
All observed summaries are in `worker-per-file.json`; all undispatched files in
`worker-not-run.json`.

| Discovered file | Observed pytest outcome | Make per-file stage |
| --- | --- | --- |
| `tests/test_anti_captcha_client.py` | 2 passed in 0.05s | advanced to next file |
| `tests/test_autodoc_sync.py` | 10 passed in 1.80s | advanced to next file |
| `tests/test_browser_session.py` | 27 passed in 0.24s | advanced to next file |
| `tests/test_browser_session_correlation_coverage.py` | 22 passed in 0.24s | advanced to next file |
| `tests/test_browser_session_forms_coverage.py` | 28 passed in 0.22s | advanced to next file |
| `tests/test_browser_session_lifecycle_coverage.py` | 19 passed in 0.20s | advanced to next file |
| `tests/test_captcha_result.py` | 4 passed in 0.05s | advanced to next file |
| `tests/test_captcha_solver.py` | 4 passed in 0.80s | coverage save FAILED |
| `tests/test_distretto_export_runner.py` | NOT RUN | not reached |
| `tests/test_llm_captcha_solver.py` | NOT RUN | not reached |
| `tests/test_posta_online_client.py` | NOT RUN | not reached |
| `tests/test_posta_online_client_branch_closure.py` | NOT RUN | not reached |
| `tests/test_posta_online_cooldown.py` | NOT RUN | not reached |
| `tests/test_posta_online_sync_branch_closure.py` | NOT RUN | not reached |
| `tests/test_registry_auto_import.py` | NOT RUN | not reached |
| `tests/test_runtime_runner.py` | NOT RUN | not reached |
| `tests/test_simaxis_section_fallback.py` | NOT RUN | not reached |
| `tests/test_sister_ade_persistence_boundary.py` | NOT RUN | not reached |
| `tests/test_sister_auth_gate.py` | NOT RUN | not reached |
| `tests/test_sister_browser_reliability.py` | NOT RUN | not reached |
| `tests/test_sister_cadastral_browser_session.py` | NOT RUN | not reached |
| `tests/test_sister_checkbox_category_html.py` | NOT RUN | not reached |
| `tests/test_sister_claim_scan.py` | NOT RUN | not reached |
| `tests/test_sister_credential_pool.py` | NOT RUN | not reached |
| `tests/test_sister_efficiency.py` | NOT RUN | not reached |
| `tests/test_sister_http_health.py` | NOT RUN | not reached |
| `tests/test_sister_init_portale_501_recovery.py` | NOT RUN | not reached |
| `tests/test_sister_observability.py` | NOT RUN | not reached |
| `tests/test_sister_recovery_migration.py` | NOT RUN | not reached |
| `tests/test_sister_recovery_policy.py` | NOT RUN | not reached |
| `tests/test_sister_request_diagnostics.py` | NOT RUN | not reached |
| `tests/test_sister_request_rows.py` | NOT RUN | not reached |
| `tests/test_sister_requests_navigation.py` | NOT RUN | not reached |
| `tests/test_sister_requests_navigation_html.py` | NOT RUN | not reached |
| `tests/test_sister_retention.py` | NOT RUN | not reached |
| `tests/test_sister_reused_menu_html.py` | NOT RUN | not reached |
| `tests/test_sister_review_persistence.py` | NOT RUN | not reached |
| `tests/test_sister_selectors.py` | NOT RUN | not reached |
| `tests/test_sister_telemetry.py` | NOT RUN | not reached |
| `tests/test_sister_visura_selection.py` | NOT RUN | not reached |
| `tests/test_sister_worker_files.py` | NOT RUN | not reached |
| `tests/test_sister_worker_watchdog.py` | NOT RUN | not reached |
| `tests/test_visura_flow.py` | NOT RUN | not reached |
| `tests/test_worker.py` | NOT RUN | not reached |
| `tests/test_worker_architecture_coverage_closure.py` | NOT RUN | not reached |
| `tests/test_worker_batch_coverage.py` | NOT RUN | not reached |
| `tests/test_worker_batch_finalization.py` | NOT RUN | not reached |
| `tests/test_worker_orchestration_coverage.py` | NOT RUN | not reached |
| `tests/test_worker_reliability.py` | NOT RUN | not reached |
| `tests/test_worker_repository.py` | NOT RUN | not reached |
| `tests/test_worker_runner.py` | NOT RUN | not reached |
| `tests/test_worker_runtime_helpers.py` | NOT RUN | not reached |

## Integrity and terminal release

Fresh before/after SHA256 manifests independently compare every protected tracked
path, not only status: **3537/3537 worktree paths exact**, including all runtime,
old/new-existing tests, configuration, baseline and historical reports.
**3341/3341 tracked main paths exact**; concurrent main status and binary diff
SHA256 `9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`
unchanged. Main untracked names/status preserved; no pre/post byte manifest of
untracked main contents collected. HEAD/merge-base/status/diff all exact before
this sole new report. **92 installed distributions' versions/METADATA/RECORD
hashes exact**; this is a metadata inventory, not every dependency file byte hash.
Baseline SHA256 `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`
exact, no generation/repair/matching/scope change. `integrity.json` retains full
comparisons. Actual terminal process audit retained; no suite process restarted.
No production DB, browser, provider opt-in, Docker/network/volume/service resources
created by this verifier. Heavy window RELEASED; no further suite/gate attempted.
Report/evidence hashes frozen separately in `FREEZE.json` / `EVIDENCE_SHA256.json`
to avoid self-reference. No commit, import or integration delegated/performed.

## Limits and next decision

Backend run did **not collect coverage**; no repository/full-file 100% claim.
Historical changed-runtime 100% certificates remain separately scoped and are
not substituted by this suite. Worker full behavior/coverage remains unverified.
No frontend/browser/PostgreSQL/PostGIS/external-provider certification, no new
complexity measurement or full AST/global ratchet claim from these suites.
No structural/runtime/domain docs changed, therefore no Graphify refresh required
or performed in this report-only scope. Global extreme-tail reductions and R16
user decision remain outstanding. Coordinator may allocate a separate fresh
worker attempt only after handling disk capacity; no retry authorized here.

## Appendix — every backend skipped testcase

| Full testcase | Reason |
| --- | --- |
| `tests.dotazioni.test_postgres::test_migration_and_concurrent_take` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_confirmation_api::test_confirmation_permission_denied[postgresql-2]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_confirmation_api::test_confirmation_permission_denied[postgresql-3]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_confirmation_api::test_confirmation_permission_denied[postgresql-4]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_confirmation_api::test_confirmation_permission_denied[postgresql-5]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_confirmation_api::test_single_confirmation_request_rejected[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_confirmation_api::test_confirmation_error_contract[postgresql-DraftReviewBlocked-409]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_confirmation_api::test_confirmation_error_contract[postgresql-GenerationRevisionChanged-409]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_confirmation_api::test_confirmation_error_contract[postgresql-RevisionProtocolUnavailable-503]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_confirmation_api::test_confirmation_response_and_actor[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_confirmation_migration::test_postgres_confirmation_migration_roundtrip` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_confirmation_postgres::test_concurrent_confirmation_is_idempotent` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_confirmation_postgres::test_disqualifying_commit_blocks_confirmation[payment]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_confirmation_postgres::test_disqualifying_commit_blocks_confirmation[notification]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_confirmation_postgres::test_disqualifying_commit_blocks_confirmation[step]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_document_api::test_permissions_enforced_before_document_access[postgresql-preview-3]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_permissions_enforced_before_document_access[postgresql-preview-4]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_permissions_enforced_before_document_access[postgresql-preview-5]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_permissions_enforced_before_document_access[postgresql-export-2]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_permissions_enforced_before_document_access[postgresql-export-3]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_permissions_enforced_before_document_access[postgresql-export-4]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_permissions_enforced_before_document_access[postgresql-export-5]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_download_is_authenticated_private_and_correctly_typed[postgresql-preview-1]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_download_is_authenticated_private_and_correctly_typed[postgresql-preview-2]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_download_is_authenticated_private_and_correctly_typed[postgresql-export-1]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_document_errors_have_no_download_body[postgresql-preview-LookupError-404]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_document_errors_have_no_download_body[postgresql-preview-DraftReviewBlocked-409]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_document_errors_have_no_download_body[postgresql-preview-PreviewUnavailable-503]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_document_errors_have_no_download_body[postgresql-export-DraftReviewBlocked-409]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_document_errors_have_no_download_body[postgresql-export-GenerationRevisionChanged-409]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_document_errors_have_no_download_body[postgresql-export-RevisionProtocolUnavailable-503]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_document_api::test_export_get_cannot_create_a_claim[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_draft_inputs::test_real_generation_has_pre_read_basis[False-False]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_real_generation_has_pre_read_basis[True-False]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_real_generation_has_pre_read_basis[True-True]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_change_during_generation_never_gets_fresh_token[render-False]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_change_during_generation_never_gets_fresh_token[render-True]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_change_during_generation_never_gets_fresh_token[before_commit-False]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_change_during_generation_never_gets_fresh_token[before_commit-True]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_caller_stale_orm_and_policy_cache_refreshed` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_mixed_lot_refuses_whole_review_after_writer[payment]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_mixed_lot_refuses_whole_review_after_writer[notification]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_mixed_lot_refuses_whole_review_after_writer[step]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_legacy_and_tampered_drafts_refused[input_basis-None]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_legacy_and_tampered_drafts_refused[input_basis-value1]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_legacy_and_tampered_drafts_refused[artifact-tampered]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_legacy_and_tampered_drafts_refused[artifact-]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_legacy_and_tampered_drafts_refused[artifact_format-txt]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_legacy_and_tampered_drafts_refused[manifest-value5]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_incomplete_or_inconsistent_batch_refused[missing]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_incomplete_or_inconsistent_batch_refused[extra]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_incomplete_or_inconsistent_batch_refused[origin]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_incomplete_or_inconsistent_batch_refused[record_state]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_incomplete_or_inconsistent_batch_refused[public_path]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_incomplete_or_inconsistent_batch_refused[count]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_incomplete_or_inconsistent_batch_refused[failed]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_incomplete_or_inconsistent_batch_refused[basis_mismatch]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_missing_generation_refused[True]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_missing_generation_refused[False]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_untracked_generation_never_backfills_existing_draft` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_generation_failure_leaves_no_capture_or_draft` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_review_budget_refuses_large_lot[MAX_REVIEW_BYTES]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_review_budget_refuses_large_lot[MAX_REVIEW_ITEMS]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_batch_remaining_boundaries[status]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_batch_remaining_boundaries[generated]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_batch_remaining_boundaries[empty]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_batch_remaining_boundaries[wrong_batch]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_single_draft_attached_to_batch_is_refused` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_draft_inputs::test_migration_preserves_legacy_bytes_without_assigning_revision` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_drafts::test_draft_migration_postgres_parity` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_eligibility::test_verified_history_allows_generation_and_rechecked_changes_block[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_eligibility::test_accounting_and_external_signals_fail_closed[postgresql-changes0-saldo_non_verificato]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_eligibility::test_accounting_and_external_signals_fail_closed[postgresql-changes1-saldo_non_verificato]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_eligibility::test_accounting_and_external_signals_fail_closed[postgresql-changes2-saldo_non_esigibile]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_eligibility::test_accounting_and_external_signals_fail_closed[postgresql-changes3-saldo_non_esigibile]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_eligibility::test_accounting_and_external_signals_fail_closed[postgresql-changes4-gestione_esterna]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_eligibility::test_accounting_and_external_signals_fail_closed[postgresql-changes5-posizione_bloccata]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_eligibility::test_accounting_and_external_signals_fail_closed[postgresql-changes6-invio_incass_da_riconciliare]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_eligibility::test_unknown_history_missing_tax_code_and_orphan_positions_block[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_eligibility::test_pending_attempts_require_reviewed_non_notification_evidence[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_eligibility::test_poste_without_register_attempt_and_missing_recovery_are_blocked[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_export::test_exact_originals_manifest_and_audited_idempotent_export` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_changed_dependencies_block_new_and_repeated_downloads[False-payment]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_changed_dependencies_block_new_and_repeated_downloads[False-notification]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_changed_dependencies_block_new_and_repeated_downloads[False-step]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_changed_dependencies_block_new_and_repeated_downloads[True-payment]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_changed_dependencies_block_new_and_repeated_downloads[True-notification]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_changed_dependencies_block_new_and_repeated_downloads[True-step]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_writer_during_packaging_blocks_claim` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_two_simultaneous_exports_share_one_archive` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_invalid_or_tampered_confirmation_never_delivers[missing_confirmation]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_invalid_or_tampered_confirmation_never_delivers[digest]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_invalid_or_tampered_confirmation_never_delivers[basis]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_invalid_or_tampered_confirmation_never_delivers[identity]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_invalid_or_tampered_confirmation_never_delivers[number]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_invalid_or_tampered_confirmation_never_delivers[reservation_state]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_invalid_or_tampered_confirmation_never_delivers[reservation_identity]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_invalid_or_tampered_confirmation_never_delivers[reservation_number]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_invalid_or_tampered_confirmation_never_delivers[missing_reservation]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_invalid_or_tampered_confirmation_never_delivers[empty_number]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_invalid_or_tampered_confirmation_never_delivers[bytes]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_invalid_or_tampered_confirmation_never_delivers[old_date]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_invalid_or_tampered_confirmation_never_delivers[export_bytes]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_invalid_or_tampered_confirmation_never_delivers[export_manifest]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_changed_confirmation_between_capture_and_claim` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_commit_failure_does_not_return_bytes` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_regeneration_cannot_export_same_identity_twice[False]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export::test_regeneration_cannot_export_same_identity_twice[True]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_export_migration::test_export_migration_matches_models_and_roundtrips` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation::test_generated_reminder_is_registered_idempotently_without_notification[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_generation::test_generation_requires_actor_and_complete_scope[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_generation::test_preview_and_failed_batch_are_not_published[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before-payment-single-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before-payment-single-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before-payment-batch-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before-payment-batch-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before-notification-single-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before-notification-single-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before-notification-batch-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before-notification-batch-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before-step-single-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before-step-single-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before-step-batch-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before-step-batch-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[during-payment-single-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[during-payment-single-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[during-payment-batch-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[during-payment-batch-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[during-notification-single-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[during-notification-single-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[during-notification-batch-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[during-notification-batch-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[during-step-single-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[during-step-single-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[during-step-batch-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[during-step-batch-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before_commit-payment-single-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before_commit-payment-single-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before_commit-payment-batch-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before_commit-payment-batch-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before_commit-notification-single-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before_commit-notification-single-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before_commit-notification-batch-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before_commit-notification-batch-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before_commit-step-single-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before_commit-step-single-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before_commit-step-batch-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_generation_concurrency::test_disqualifying_commit_must_prevent_publication[before_commit-step-batch-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_import::test_concurrent_confirmations_do_not_duplicate[sqlite-False]` | Concorrenza verificata su PostgreSQL, non simulata da SQLite |
| `tests.ruolo.test_notice_import::test_concurrent_confirmations_do_not_duplicate[sqlite-True]` | Concorrenza verificata su PostgreSQL, non simulata da SQLite |
| `tests.ruolo.test_notice_import::test_preview_confirm_and_duplicate_content[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_import::test_conflicts_and_repeated_rows_do_not_overwrite[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_import::test_confirmation_rollback[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_import::test_import_authorization[postgresql-2]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_import::test_import_authorization[postgresql-3]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_import::test_import_authorization[postgresql-4]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_import::test_import_authorization[postgresql-5]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_import::test_import_not_found_and_invalid_input[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_import::test_poste_preserves_source_without_inferring_notification[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_import::test_import_migration_roundtrip[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_import::test_integrity_error_at_commit_rolls_back[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_import::test_concurrent_confirmations_do_not_duplicate[postgresql-False]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_import::test_concurrent_confirmations_do_not_duplicate[postgresql-True]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_concurrent_attempts_and_edits_are_serialized[sqlite-attempt]` | Concorrenza reale verificata su PostgreSQL |
| `tests.ruolo.test_notice_lifecycle::test_concurrent_attempts_and_edits_are_serialized[sqlite-edit]` | Concorrenza reale verificata su PostgreSQL |
| `tests.ruolo.test_notice_lifecycle::test_record_past_attempt_is_audited_atomic_and_stale_retry_does_not_duplicate[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_duplicate_detection_includes_imported_postal_attempts[postgresql-posta]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_duplicate_detection_includes_imported_postal_attempts[postgresql-pec]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_duplicate_detection_includes_imported_postal_attempts[postgresql-messo]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_duplicate_detection_includes_imported_postal_attempts[postgresql-altro]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_record_missing_notification_and_rollback_after_audit[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_record_attempt_preserves_previous_notification_in_audit_and_deduplicates_undated_tracking[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_invalid_or_future_declarations_are_rejected[postgresql-changes0]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_invalid_or_future_declarations_are_rejected[postgresql-changes1]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_invalid_or_future_declarations_are_rejected[postgresql-changes2]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_invalid_or_future_declarations_are_rejected[postgresql-changes3]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_invalid_or_future_declarations_are_rejected[postgresql-changes4]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_invalid_or_future_declarations_are_rejected[postgresql-changes5]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_invalid_or_future_declarations_are_rejected[postgresql-changes6]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_invalid_or_future_declarations_are_rejected[postgresql-changes7]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_attempt_permissions_are_server_enforced[postgresql-2-403]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_attempt_permissions_are_server_enforced[postgresql-3-403]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_attempt_permissions_are_server_enforced[postgresql-4-401]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_attempt_permissions_are_server_enforced[postgresql-5-403]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_missing_reconciled_and_unauthenticated_documents[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_diagnostic_empty_unlinked_and_missing_avviso_is_read_only[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_diagnostic_reloads_history_and_never_authorizes_dispatch[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_concurrent_attempts_and_edits_are_serialized[postgresql-attempt]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_lifecycle::test_concurrent_attempts_and_edits_are_serialized[postgresql-edit]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_concurrent_decisions_are_serialized[sqlite-reconcile]` | Concorrenza reale verificata su PostgreSQL |
| `tests.ruolo.test_notice_reconciliation::test_concurrent_decisions_are_serialized[sqlite-resolve]` | Concorrenza reale verificata su PostgreSQL |
| `tests.ruolo.test_notice_reconciliation::test_concurrent_decisions_are_serialized[sqlite-mixed]` | Concorrenza reale verificata su PostgreSQL |
| `tests.ruolo.test_notice_reconciliation::test_concurrent_undo_and_import_cannot_leave_a_stale_destination[sqlite]` | Concorrenza reale verificata su PostgreSQL |
| `tests.ruolo.test_notice_reconciliation::test_reconcile_moves_events_preserves_originals_and_invalidates_reviews[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_reconciliation_candidate_search_and_rejections[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_poste_target_is_rejected_even_with_positions[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_reconciliation_rollback_after_transfer[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_conflict_decision_is_audited_once_without_overwriting[postgresql-keep_existing]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_conflict_decision_is_audited_once_without_overwriting[postgresql-register_evidence]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_conflict_guards_and_preview_are_fail_closed[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_new_commands_require_editor_and_module[postgresql-2]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_new_commands_require_editor_and_module[postgresql-3]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_new_commands_require_editor_and_module[postgresql-4]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_new_commands_require_editor_and_module[postgresql-5]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_poste_reimports_and_conflicts_follow_reconciliation[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_undo_reconciliation_restores_events_without_restoring_assessments[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_undo_rejects_stale_versions_wrong_target_and_subsequent_edits[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_undo_rejects_later_reconciliations_and_dependent_imports[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_undo_requires_editor_and_rolls_back_atomic_transfer[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_concurrent_decisions_are_serialized[postgresql-reconcile]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_concurrent_decisions_are_serialized[postgresql-resolve]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_concurrent_decisions_are_serialized[postgresql-mixed]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_reconciliation::test_concurrent_undo_and_import_cannot_leave_a_stale_destination[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_concurrent_operators_cannot_overwrite_each_other[sqlite]` | Concorrenza e row lock richiedono PostgreSQL |
| `tests.ruolo.test_notice_register::test_historical_creation_keeps_annual_namespaces_and_no_debt[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_empty_historical_document_is_retained_for_anomalies[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_revision_preserves_original_and_audits_versions[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_missing_and_stale_documents_are_rejected[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_link_unlink_and_relink_invalidate_previous_scope_decisions[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_cumulative_document_links_multiple_avvisi[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_link_validates_ownership_year_and_duplicate_avviso[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_evidence_and_poste_outcome_do_not_automatically_prove_notification_or_step[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_notification_decision_requires_own_evidence_and_stays_local[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_step_is_independent_and_position_scoped[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_migration_roundtrip_and_model_parity[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_database_rejects_cross_document_evidence[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_database_rejects_unproven_or_invalid_notification[postgresql-perfezionata]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_database_rejects_unproven_or_invalid_notification[postgresql-unknown]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_database_rejects_unproven_recovery_and_source_duplicates[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_transaction_rollback_includes_document_and_audit[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register::test_concurrent_operators_cannot_overwrite_each_other[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_list_create_detail_audit_and_read_permissions[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_authentication_module_and_section_are_enforced[postgresql-None-401]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_authentication_module_and_section_are_enforced[postgresql-3-403]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_authentication_module_and_section_are_enforced[postgresql-4-401]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_authentication_module_and_section_are_enforced[postgresql-5-403]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_viewer_cannot_call_any_mutation[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_user_cannot_spoof_actor_provenance_or_confirmation[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_manual_positions_candidates_and_reversible_links[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_correct_position_requires_fresh_link_and_preserves_original[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_metadata_change_and_added_scope_invalidate_notification_but_not_noop[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_http_errors_are_atomic_and_do_not_leak_sql[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_missing_and_cross_document_resources_are_rejected[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_filters_search_and_pagination_are_consistent[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_year_and_step_filters_must_match_the_same_position[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_invalid_query_is_422_not_500[postgresql-params0]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_invalid_query_is_422_not_500[postgresql-params1]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_invalid_query_is_422_not_500[postgresql-params2]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_invalid_query_is_422_not_500[postgresql-params3]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_invalid_query_is_422_not_500[postgresql-params4]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_invalid_query_is_422_not_500[postgresql-params5]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_invalid_query_is_422_not_500[postgresql-params6]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_invalid_query_is_422_not_500[postgresql-params7]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_candidate_search_requires_text_and_escapes_wildcards[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_conflicting_and_incomplete_records_remain_visible[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_evidence_and_audit_pagination_does_not_mutate_state[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_register_api::test_openapi_contains_only_new_register_paths_and_explicit_contracts[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ana_companies]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ana_payment_notices]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ana_persons]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ana_subjects]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_avvisi]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_notice_attempts]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_notice_documents]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_notice_evidence]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_notice_import_batches]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_notice_import_rows]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_notice_notifications]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_notice_positions]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_notice_recoveries]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_particelle]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_partite]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_tributi_avviso_status]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_tributi_calculation_policies]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_tributi_payments]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_tributi_registered_mails]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_tributi_special_allocations]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_tributi_special_notices]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_tributi_templates]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[insert-ruolo_tributi_year_managers]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ana_companies]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ana_payment_notices]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ana_persons]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ana_subjects]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_avvisi]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_notice_attempts]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_notice_documents]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_notice_evidence]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_notice_import_batches]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_notice_import_rows]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_notice_notifications]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_notice_positions]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_notice_recoveries]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_particelle]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_partite]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_tributi_avviso_status]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_tributi_calculation_policies]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_tributi_payments]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_tributi_registered_mails]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_tributi_special_allocations]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_tributi_special_notices]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_tributi_templates]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[update-ruolo_tributi_year_managers]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ana_companies]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ana_payment_notices]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ana_persons]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ana_subjects]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_avvisi]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_notice_attempts]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_notice_documents]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_notice_evidence]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_notice_import_batches]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_notice_import_rows]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_notice_notifications]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_notice_positions]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_notice_recoveries]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_particelle]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_partite]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_tributi_avviso_status]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_tributi_calculation_policies]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_tributi_payments]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_tributi_registered_mails]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_tributi_special_allocations]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_tributi_special_notices]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_tributi_templates]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[delete-ruolo_tributi_year_managers]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ana_companies]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ana_payment_notices]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ana_persons]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ana_subjects]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_avvisi]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_notice_attempts]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_notice_documents]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_notice_evidence]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_notice_import_batches]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_notice_import_rows]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_notice_notifications]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_notice_positions]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_notice_recoveries]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_particelle]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_partite]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_tributi_avviso_status]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_tributi_calculation_policies]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_tributi_payments]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_tributi_registered_mails]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_tributi_special_allocations]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_tributi_special_notices]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_tributi_templates]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_every_dependency_raw_sql[truncate-ruolo_tributi_year_managers]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_copy_bulk_replica_and_one_revision_per_transaction` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_rollback_savepoint_and_noop_do_not_invalidate` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_revision_singleton_missing_rejects_reader_and_writer` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_incomplete_enforcement_is_refused[ALTER TABLE ruolo_avvisi DISABLE TRIGGER gaia_notice_revision_row]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_incomplete_enforcement_is_refused[ALTER TABLE ruolo_avvisi ENABLE TRIGGER gaia_notice_revision_row]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_incomplete_enforcement_is_refused[ALTER TABLE ruolo_avvisi DISABLE TRIGGER gaia_notice_revision_truncate]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_incomplete_enforcement_is_refused[DROP TRIGGER gaia_notice_revision_row ON ana_payment_notices]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_incomplete_enforcement_is_refused[DROP TRIGGER gaia_notice_revision_truncate ON ruolo_notice_positions]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_incompatible_isolation_is_refused[AUTOCOMMIT]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_incompatible_isolation_is_refused[REPEATABLE READ]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_incompatible_isolation_is_refused[SERIALIZABLE]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_engine_default_autocommit_is_refused` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_migration_parity_roundtrip_and_new_epoch` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_revision::test_revision_constraints[INSERT INTO ruolo_notice_generation_revision (id, epoch) SELECT 2, epoch FROM ruolo_notice_generation_revision]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_revision_constraints[UPDATE ruolo_notice_generation_revision SET revision = -1]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_fence_blocks_commits_not_rendering_and_later_invalidates` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_prior_writer_commit_or_rollback_is_observed[True]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_prior_writer_commit_or_rollback_is_observed[False]` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_uncommitted_writer_does_not_lock_read_or_render` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_lock_timeout_rolls_back_without_changing_revision` | GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |
| `tests.ruolo.test_notice_revision::test_real_domain_writers_advance_revision[payment-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_revision::test_real_domain_writers_advance_revision[payment-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_revision::test_real_domain_writers_advance_revision[notification-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_revision::test_real_domain_writers_advance_revision[notification-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_revision::test_real_domain_writers_advance_revision[step-2022]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_revision::test_real_domain_writers_advance_revision[step-2023]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_revision::test_real_additional_dependencies[partial_payment]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_revision::test_real_additional_dependencies[orphan]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_revision::test_real_additional_dependencies[incass]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_revision::test_real_additional_dependencies[policy]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_revision::test_real_additional_dependencies[unlink]` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_notice_revision::test_read_bypasses_stale_orm_identity` | GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |
| `tests.ruolo.test_registered_mail_campaign_preview::test_campaign_preview_api_permissions_cutoff_and_legacy_links[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_registered_mail_campaign_preview::test_registered_mail_summary_counts_all_rows_and_requires_view_access[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_registered_mail_campaign_preview::test_manual_registered_mail_association_rejects_missing_subject[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_registered_mail_campaign_preview::test_manual_association_forwards_validated_workbook_evidence[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_registered_mail_campaign_preview::test_reference_check_requires_editor_and_forwards_references[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_registered_mail_campaign_preview::test_manual_association_rejects_missing_mail_duplicate_and_unknown_notice[postgresql]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_tributi_notice_migration_postgres::test_notice_number_migration_upgrade_downgrade_upgrade` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_tributi_notice_registry_postgres::test_different_identities_survive_real_postgres_contention` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_tributi_notice_registry_postgres::test_same_identity_is_idempotent_under_real_postgres_contention` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_tributi_notice_registry_postgres::test_separate_processes_survive_real_postgres_contention[different-identities]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_tributi_notice_registry_postgres::test_separate_processes_survive_real_postgres_contention[same-identity]` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.ruolo.test_tributi_notice_registry_postgres::test_outer_transaction_rollback_releases_the_number_on_postgres` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.test_catasto_ade_wfs_integration::test_upsert_ade_parcels_persists_wfs_geometry_with_psycopg_typed_binds` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_ade_wfs_integration::test_apply_ade_alignment_updates_geometry_in_place_and_preserves_fk` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_ade_wfs_integration::test_apply_ade_alignment_matches_when_gaia_section_is_missing_and_ade_has_value` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_ade_wfs_integration::test_ade_alignment_report_dedupes_duplicate_ade_keys_preferring_base_reference` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_ade_wfs_integration::test_apply_ade_alignment_suppresses_missing_only_with_explicit_flag` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_ade_wfs_integration::test_apply_ade_alignment_handles_split_as_parent_suppressed_and_new_children` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_ade_wfs_integration::test_apply_ade_alignment_skips_new_parcels_when_comune_is_unmapped` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_ade_wfs_integration::test_apply_ade_alignment_standard_does_not_suppress_missing_gaia` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_batch_credential_allowlist_migration_postgres::test_allowlist_migration_preserves_rows_and_round_trips` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.test_catasto_dui_2026_overlay::test_load_raw_dataset_from_shapefile_reads_geometry_and_fields` | OSGeo non disponibile per generare lo shapefile di test. |
| `tests.test_catasto_dui_2026_overlay::test_load_raw_dataset_from_shapefile_uses_pyshp_fallback_when_osgeo_is_missing` | pyproj non disponibile per il fallback pyshp. |
| `tests.test_catasto_perpetual_sync_migration_postgres::test_perpetual_sync_migration_round_trip` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.test_catasto_shapefile_integration::test_finalize_shapefile_import_inserts_current_particelle_without_touching_distretti` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_shapefile_integration::test_finalize_distretti_shapefile_import_upserts_current_geometry_and_versions_history` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_shapefile_integration::test_finalize_distretti_shapefile_import_inserts_new_distretto_and_tracks_missing_snapshot` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_shapefile_integration::test_finalize_shapefile_import_allows_progress_updates_from_separate_session` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_shapefile_integration::test_finalize_shapefile_import_writes_history_on_changed_particella` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_shapefile_integration::test_distretto_geojson_route_returns_feature_for_geometry` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_shapefile_integration::test_distretto_geojson_route_returns_404_when_geometry_is_missing` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_shapefile_integration::test_finalize_shapefile_import_excludes_fd_distretto_from_upsert` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_shapefile_integration::test_finalize_shapefile_import_maps_cod_catastale_from_reference_dataset` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_catasto_shapefile_integration::test_finalize_shapefile_import_writes_history_when_only_geometry_changes` | PostgreSQL integration tests require a PostgreSQL DATABASE_URL |
| `tests.test_operazioni_integration.TestVehicleIntegration::test_create_and_retrieve_vehicle` | PostgreSQL integration tests require TEST_DATABASE_URL to be configured |
| `tests.test_operazioni_integration.TestVehicleIntegration::test_list_vehicles_with_filter` | PostgreSQL integration tests require TEST_DATABASE_URL to be configured |
| `tests.test_operazioni_integration.TestVehicleIntegration::test_start_and_stop_usage_session` | PostgreSQL integration tests require TEST_DATABASE_URL to be configured |
| `tests.test_operazioni_integration.TestVehicleIntegration::test_list_vehicles_orders_by_usage_frequency` | PostgreSQL integration tests require TEST_DATABASE_URL to be configured |
| `tests.test_operazioni_integration.TestVehicleIntegration::test_create_fuel_log` | PostgreSQL integration tests require TEST_DATABASE_URL to be configured |
| `tests.test_operazioni_integration.TestVehicleIntegration::test_create_maintenance` | PostgreSQL integration tests require TEST_DATABASE_URL to be configured |
| `tests.test_operazioni_integration.TestActivityIntegration::test_create_activity_with_catalog` | PostgreSQL integration tests require TEST_DATABASE_URL to be configured |
| `tests.test_operazioni_integration.TestReportCaseIntegration::test_report_and_case_linkage` | PostgreSQL integration tests require TEST_DATABASE_URL to be configured |
| `tests.test_operazioni_integration.TestAttachmentIntegration::test_quota_calculation` | PostgreSQL integration tests require TEST_DATABASE_URL to be configured |
| `tests.test_operazioni_integration.TestAttachmentIntegration::test_create_quota_metric` | PostgreSQL integration tests require TEST_DATABASE_URL to be configured |
| `tests.test_operazioni_integration.TestAttachmentIntegration::test_get_latest_metric` | PostgreSQL integration tests require TEST_DATABASE_URL to be configured |
| `tests.test_operazioni_integration.TestGpsIntegration::test_create_gps_track` | PostgreSQL integration tests require TEST_DATABASE_URL to be configured |
| `tests.test_operazioni_integration.TestTeamIntegration::test_create_team` | PostgreSQL integration tests require TEST_DATABASE_URL to be configured |
| `tests.test_operazioni_integration.TestTeamIntegration::test_create_operator_profile` | PostgreSQL integration tests require TEST_DATABASE_URL to be configured |
| `tests.test_presenze_mapping_postgres::test_presenze_mapping_migration_upgrade_downgrade_upgrade` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.test_presenze_mapping_postgres::test_presenze_mapping_unique_index_survives_real_postgres_contention` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.test_presenze_operations_postgres::test_manual_start_and_scheduler_share_lock_through_commit` | GAIA_TEST_POSTGRES_URL not configured |
| `tests.test_presenze_operations_postgres::test_concurrent_manual_grants_create_one_audit_entry` | GAIA_TEST_POSTGRES_URL not configured |
| `tests.test_presenze_operations_postgres::test_voucher_migration_round_trip_preserves_existing_daily_data` | GAIA_TEST_POSTGRES_URL not configured |
| `tests.test_presenze_personnel_profiles_postgres::test_personnel_migration_is_idempotent_and_rejects_destructive_downgrade` | GAIA_TEST_POSTGRES_URL not configured |
| `tests.test_presenze_shift_open_ended::test_ongoing_migration_preserves_rows_and_rejects_lossy_downgrade` | GAIA_TEST_POSTGRES_URL not configured |
| `tests.test_presenze_shift_workers_postgres::test_shift_migration_and_concurrent_retry_preserve_gate_authority` | GAIA_TEST_POSTGRES_URL not configured |
| `tests.test_presenze_whatsapp_postgres::test_postgres_lock_survives_app_commits_and_releases_on_exception` | TEST_WHATSAPP_POSTGRES_URL requires a disposable PostgreSQL |
| `tests.test_presenze_whatsapp_postgres::test_migrations_and_persistence_on_postgres` | TEST_WHATSAPP_POSTGRES_URL requires a disposable PostgreSQL |
| `tests.test_presenze_worker_leases_postgres::test_presenze_lease_migration_is_additive_and_round_trips` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.test_presenze_worker_leases_postgres::test_presenze_claim_skips_locked_job_and_respects_fair_order` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.test_presenze_worker_leases_postgres::test_presenze_lease_generation_fences_stale_postgres_owner` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.test_ruolo_autosync_migration_postgres::test_ruolo_autosync_migration_deduplicates_and_round_trips` | GAIA_TEST_POSTGRES_URL non configurato |
| `tests.test_sister_autosync_postgres::test_campaign_retry_locks_and_reloads_remote_evidence[True]` | GAIA_TEST_POSTGRES_URL not configured |
| `tests.test_sister_autosync_postgres::test_campaign_retry_locks_and_reloads_remote_evidence[False]` | GAIA_TEST_POSTGRES_URL not configured |
| `tests.test_sister_autosync_refill_postgres::test_refill_cannot_overtake_worker_or_another_planner[CatastoBatch]` | GAIA_TEST_POSTGRES_URL not configured |
| `tests.test_sister_autosync_refill_postgres::test_refill_cannot_overtake_worker_or_another_planner[CatastoVisuraRequest]` | GAIA_TEST_POSTGRES_URL not configured |
| `tests.test_sister_autosync_refill_postgres::test_refill_cannot_overtake_worker_or_another_planner[CatastoPerpetualSyncItem]` | GAIA_TEST_POSTGRES_URL not configured |
| `tests.test_sister_manual_retry_postgres::test_manual_retry_waits_for_batch_owner_and_rechecks_status` | GAIA_TEST_POSTGRES_URL not configured |
