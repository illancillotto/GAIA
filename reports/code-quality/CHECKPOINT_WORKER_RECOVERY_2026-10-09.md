# Checkpoint worker recovery — 2026-10-09

**WORKER FAILED / INCOMPLETE after the sole authorized attempt3; heavy RELEASED.**
Backend remains independently PASS on the same protected source snapshot.
Global campaign remains **ACTIVE / INCOMPLETE**; no full worker, global-final or
last-wave certification. Original attempts1/2 remain FAIL, not waived/relabelled.

## Ownership and snapshot

Same distinct verifier TUI `01a1222c-ba79-7a42-8717-4bd1b8374ce0` read FIRST the
updated integration `MULTI_AGENT_OWNERSHIP_CHECKPOINT_SUITES_2026-10-09.md` current
phase and ownership rows. Sole new repository output: this recovery report.
Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261009-suites-verification`,
branch `verify/complexity-campaign-suites-20261009`, HEAD
`34c13604f49de64ced59bf6846998556e7c873b9`; merge-base/main
`55a1b1d35911451e018b662c2acc450bf5994ea2` unchanged. All runtime, tests, config,
tooling, baseline and old reports read-only; no source/test/config fixes,
installation, baseline/matcher changes, R16 diagnosis, commits/imports or merges.
No additional cleanup or retry in this phase. Exclusive heavy serialized window.

Fresh attempt3 evidence: `/home/cbo/.cache/gaia-campaign/20261009-checkpoint-suites/verifier/attempt3/`.
Both earlier attempts and original report/freeze/manifests were preserved
byte-identical during this phase; the previously authorized fixture deletion is
explicitly disclosed below and was **not** reversed or hidden.

## All suite attempts, terminal identities and scope

| Suite / attempt | Result | Passed | Skips | Failed tests | Files reached / discovered | Exit and terminal identity |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Original complete backend | PASS | 6714 | 449 | 0 | Complete configured tests | exact pytest exit0, PID2202976, native33706 |
| Worker attempt1 | FAIL / incomplete | 116 | 0 observed | 0 assertions observed; infrastructure failed | 8/52,44NOTRUN | native83403exit1; exact Make2254220 code NOT captured after recorderENOSPC; raw MakeError1 |
| Worker attempt2, explicitly authorized | FAIL / incomplete | 188 | 0 observed | 1 | 10/52,42NOTRUN | exact Makeexit2,PID2264418,native16194 |
| Worker attempt3, separately authorized | FAIL / incomplete | 357 | 0 observed | 4 | 22/52,30NOTRUN | exact Makeexit2,PID2279109,native34203 |

Counts describe each invocation separately and must not be summed as unique tests.
All observed testcase failure names/raw tracebacks/per-file summaries retained.
Original backend raw JUnit independently counts7163cases, 6714PASS449SKIP,
zero failures/errors,19warnings;1371.68pytest/1385.117396runner seconds. This
backend was not rerun or collected with coverage in recovery. Full names/reasons
of all449skips remain in the original report appendix and private rawJUnit /
`backend-skips.json` / `backend-skips.tsv`:447PostgreSQL-dependent,1OSGeo,1pyproj.
No missing optional dependencies installed, no PostgreSQL/provider opt-in.

Attempt1 stopped on coverage persistence DataError/missing coverage_schema during
concurrent ENOSPC of the process recorder. Exact Make returncode unavailable;
only native wrapper exit1/rawMakeError1/actual PID absent documented, not inferred.
Attempt2 stopped on
`tests/test_llm_captcha_solver.py::test_llm_solver_loads_cursor_auth_token_from_file`
with `KeyError: 'HOME'`: minimal synthetic invocation omitted HOME, which the test
requires in captured subprocess env. This is an explained invocation failure;
no source change was made. Its188PASS1FAIL/rawlogs/exactexit remain preserved.

## Attempt3 invocation and preflight

Capacity immediately before setup:380350464bytes (~363MiB), strictly greater than
256MiB (268435456bytes); rechecked before launch. Protected3537tracked worktree
paths exact versus original snapshot. `readonly-before.json` captures107previous
private evidence files' hashes plus immutable oldreport hash and original845missing
fixture entries. None of those107files changed/disappeared in this phase.

Same unmodified complete **make test-worker**, installed
`/home/cbo/CursorProjects/GAIA/backend/.venv/bin/python` (Python3.12.3), all52sorted
files, existing per-file coverage/pytest process isolation and coverage options.
Only invocation differences versus attempt2 are HOME provisioning and unique
private evidence/temp/SQLite/coverage-output destinations. PYTHONDONTWRITEBYTECODE=1
retained to disable transient bytecode writes; PYTEST_ADDOPTS=-ra retains reporting.
No selection/coverage/threshold/source/config/gate changes or tests-only substitute.

A fresh existing empty private HOME at `/home/cbo/.cache/gaia-campaign/20261009-checkpoint-suites/verifier/attempt3/empty-private-home`
was created and verified empty before launch. This is isolated subprocess env
provisioning, not use of real user's HOME/auth/portal credentials. Minimal synthetic
settings retained (APP_ENV=test, disposable SQLite, synthetic JWT/mobile/admin/
master-key values); installed dependencies read-only. Root+backend+worker PYTHONPATH.
`worker-invocation.json` records exact argv/cwd/env/runner; process/startticks,
all descendants and actual terminal codes retained separately.

## Attempt3 failure: long Chromium temporary socket path

The previous HOME testcase passed in attempt3. Test collection/execution advanced
through22files before `test_sister_checkbox_category_html.py` reported1PASS4FAIL.
All four failures are `playwright._impl._errors.TargetClosedError` at
`BrowserType.launch`; actual `/usr/bin/google-chrome` browser stderr states:

```text
FATAL:chrome/browser/process_singleton_posix.cc:313
Socket path too long:
/home/cbo/.cache/gaia-campaign/20261009-checkpoint-suites/verifier/attempt3/tmp/com.google.Chrome.*/SingletonSocket
```

The private long TMPDIR chosen for evidence caused the browser launch restriction;
this is an explained invocation failure, not evidence of a runtime regression.
Raw stderr contains each exact generated path, Chrome PID, full launch args,
Playwright call log, graceful cleanup and all failure tracebacks in `worker.log`.
No short-path correction or additional retry authorized/performed in this phase.

Exact failed testcase names:

- `tests/test_sister_checkbox_category_html.py::test_checkbox_only_row_uses_verified_category_without_remote_actions[nonEspletabili-Non evadibili-review]`
- `tests/test_sister_checkbox_category_html.py::test_checkbox_only_row_uses_verified_category_without_remote_actions[espletate-Espletate-ready]`
- `tests/test_sister_checkbox_category_html.py::test_checkbox_only_row_uses_verified_category_without_remote_actions[prelevate-Prelevate-ready]`
- `tests/test_sister_checkbox_category_html.py::test_checkbox_only_row_uses_verified_category_without_remote_actions[espletate-Non evadibili-unknown]`

No ENOSPC repeated; after terminal filesystem available412499968bytes (~393MiB).
Exact Makeexit2,PID2279109 reaped/absent,native34203exit2; runner elapsed76.633111s.
All46observed descendant PIDs absent (`terminal-audit.json`), no live handle
restarted for observation timeout. No coverage combine/final JSON/XML/report:
existing fail-fast Make behavior correctly stopped at the failing file. Prior
per-file coverage temporary data removed by the existing Make EXIT trap; no
verifier cleanup executed in recovery. **No full worker coverage result exists**.
Zero skips observed in reached22files; unexecuted30files are NOTRUN, not skipped.
No historical778PASS/1SKIP result substituted for fresh evidence.

## All52discovered worker files: attempt3 outcomes

`worker-per-file.json` preserves all reached summaries; `worker-summary.json`
retains the exact sorted-prefix equality, counts, all4failures and30NOTRUN paths.

| File | Raw pytest summary | Stage |
| --- | --- | --- |
| `tests/test_anti_captcha_client.py` | 2 passed in 0.05s | coverage invocation completed; next file reached |
| `tests/test_autodoc_sync.py` | 10 passed in 1.84s | coverage invocation completed; next file reached |
| `tests/test_browser_session.py` | 27 passed in 0.28s | coverage invocation completed; next file reached |
| `tests/test_browser_session_correlation_coverage.py` | 22 passed in 0.29s | coverage invocation completed; next file reached |
| `tests/test_browser_session_forms_coverage.py` | 28 passed in 0.24s | coverage invocation completed; next file reached |
| `tests/test_browser_session_lifecycle_coverage.py` | 19 passed in 0.23s | coverage invocation completed; next file reached |
| `tests/test_captcha_result.py` | 4 passed in 0.05s | coverage invocation completed; next file reached |
| `tests/test_captcha_solver.py` | 4 passed in 0.61s | coverage invocation completed; next file reached |
| `tests/test_distretto_export_runner.py` | 10 passed in 2.48s | coverage invocation completed; next file reached |
| `tests/test_llm_captcha_solver.py` | 63 passed in 0.36s | coverage invocation completed; next file reached |
| `tests/test_posta_online_client.py` | 21 passed in 4.15s | coverage invocation completed; next file reached |
| `tests/test_posta_online_client_branch_closure.py` | 1 passed in 0.41s | coverage invocation completed; next file reached |
| `tests/test_posta_online_cooldown.py` | 7 passed in 12.10s | coverage invocation completed; next file reached |
| `tests/test_posta_online_sync_branch_closure.py` | 8 passed in 2.27s | coverage invocation completed; next file reached |
| `tests/test_registry_auto_import.py` | 1 passed in 3.19s | coverage invocation completed; next file reached |
| `tests/test_runtime_runner.py` | 44 passed in 4.15s | coverage invocation completed; next file reached |
| `tests/test_simaxis_section_fallback.py` | 4 passed in 0.11s | coverage invocation completed; next file reached |
| `tests/test_sister_ade_persistence_boundary.py` | 1 passed in 4.15s | coverage invocation completed; next file reached |
| `tests/test_sister_auth_gate.py` | 26 passed in 7.80s | coverage invocation completed; next file reached |
| `tests/test_sister_browser_reliability.py` | 40 passed in 0.23s | coverage invocation completed; next file reached |
| `tests/test_sister_cadastral_browser_session.py` | 14 passed in 0.30s | coverage invocation completed; next file reached |
| `tests/test_sister_checkbox_category_html.py` | 4 failed, 1 passed in 14.95s | pytest failed; Make stopped |
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

## Previous cleanup and exact lost-evidence disclosure

After Coordinator's earlier explicit environmental authorization and before the
later STOP message, verifier inventoried1283backend-basetemp entries without
following symlinks (187907679bytes) and deleted ONLY verifier-created
`backend-pytest-tmp`. Initial inventory assertion on fixture symlinks stopped before
any deletion/test launch; corrected lstat/readlink inventory preserves ownership
and symlink target metadata. Setup failure retained, not a worker suite retry.
`backend-basetemp-removal-inventory.json` and `*-result.json` record exact inventory,
permission scope, pre/postspace and timing. No shared/user/old campaign cleanup.

**845 of the original911frozenmanifest entries are now absent**, ALL under that
authorized deleted basetemp. **66remainingoriginalentries exact**. RawbackendJUnit,
logs,skips/manifests, failedworker evidence and oldreport retained. Original freeze
manifest is unchanged, **not** rewritten to conceal loss or claim complete
retention. Fixture contents have not been reconstructed. This report supersedes
the original report's full-evidence-retention assertion ONLY for this explicit loss
and records all subsequent failures without modifying the original report.

Original public report and private `original-report-attempt1.md` SHA256 BOTH:
`0f9246122cc2ca3546bb7c2737a709a0824e78c4a63d9f7283af0a4f66908d8e`.
Original EVIDENCE_SHA256.json manifest SHA256 unchanged:
`9ccfc8580e2b9880b5abf07e9bb4f65b9adc1559400731e84ea9f159f3a96028`.
Original FREEZE.json immutable. Earlier88MiBownbytecodecleanup preceded that freeze;
its provenance remains separately recorded. No furthercleanup authorized/performed.

## Integrity, limits and release

Fresh before/after hashes: **3537/3537protectedtrackedworktree paths exact**,
**3341/3341trackedmain paths exact**, **92installed distributions' version/
METADATA/RECORD hashes exact**, HEAD/merge-base/gitstatus/binarydiff exact.
107pre-existing evidence files exact; prior reports/source/config/baseline untouched.
Main untracked names/status preserved, without a byte manifest for their contents.
Metadata inventory is not an every-installed-package-file byte hash. Baseline SHA
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95` unchanged;
mainbinarydiff `9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`
unchanged. Exact integrity and terminal audit private evidence retained.

Only the new recovery report writable in this phase. Oldreport frozen/untracked;
no commit/import/integration. No full backend/worker repository100%coverage claim:
backend did not collectcoverage; allworker attempts failed beforecombine. Existing
changed-runtime100%certificates retain separate scope and cannot replace this run.
No frontend/wholebrowser/PostgreSQL/PostGIS/externalprovider certification or R16
matching/source work. Browser was invoked only by existing worker test fixtures;
launch failures/terminal cleanup preserved. No Docker/network/volume/service
resources created by verifier. No structural/domain/runtime change and no Graphify
refresh needed/performed in report-onlyscope. Extreme-tail/globalfinal/R16decision
still outstanding; campaignACTIVE/INCOMPLETE.

Report SHA and new evidence manifest frozen separately in attempt3/FREEZE.json /
EVIDENCE_SHA256.json (self-hashes excluded); original freeze left unchanged.
**Heavy RELEASED**, allobserved processes terminal, no further action. A separate
Coordinator decision is required before any fourth attempt or TMPDIR correction.
