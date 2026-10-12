# GAIA — Historical baseline provenance revalidation 2026-10-11

## Scope and result

Read-only continuation of the required baseline provenance task while R43
awaits a separate test-only correction decision. The original temporary
provenance JSON/script are unavailable, so this activity independently
recomputes every historical record from available Git objects rather than
accepting the older report as numerical evidence.

Fresh session99623 TERMINAL0: **30/30 records, 14 paths, 71 callable source
scans**, plus explicit file-LOC measurements. 15 REAL_REGRESSION and
15 TEST_ONLY_DIVERGENCE; UNKNOWN0. All 14 current source files are byte-identical
to the authoritative snapshot in integration, its HEAD and concurrent main,
and CLEAN in both worktrees. **None of these 30 divergences is introduced by
the campaign.** No baseline, runtime, matcher, threshold or exclusion changes.

This does not certify the complete global comparison, remove its newer
ownership ambiguities, authorize R43 correction or replace missing application
gates. No application complexity reduction is credited.

## Snapshot and binding

- Integration HEAD: `114fbf7196382c6446a7963c34bd89e4c9795ef5`.
- Authoritative snapshot / merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Baseline SHA-256: `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
- Baseline source commit: `11ed944a46ebdeb32ad50c14e7fca90b2c55f1fd`, not the main merge-base.
- Current admitted matcher SHA-256: `32b117502901ba56f1213b8871a25604c8723b710d45e0855b2da10bc6e251fc`.
- JS helper SHA-256: `faf340a36a2a3730d313be34b17a89e1c96c6310084d3b63739e0a3fbf446b8d`.
- Original provenance report SHA-256: `da60f6088d702c8cd53997b22644b843fefbc03abec5554ffac53cbe6422d315`.
- New diagnostic script SHA-256: `26a57716a050942f8d5556ba0da3292af1d5e024f303d37e4ff20a79af2fca11`.

## Verification performed

For every record, read the registered baseline value and independently measure
the AST at its declared source commit, the last historical baseline-writing
commit b89e598c, and snapshot55a. Assert that all baseline-origin values agree
and that snapshot values reproduce the historical table. Measure both parent
and commit for the introducing transition and the transition producing the
current value; verify those commits are ancestors of snapshot55a.

Callable names must identify exactly one record within each source scan.
The two explicit `<file>` LOC records are measured as files with the existing
official effective_loc implementation, not treated as callable identities.
Compare actual source bytes in integration, integration HEAD, snapshot55a and
main; inspect per-path Git status. Recheck all protected source hashes and
baseline bytes after the activity. Custody drift: zero.

## All 30 revalidated records

Every row has CLEAN integration/main status and campaign_changed=false.
The full JSON additionally preserves baseline-source and last-baseline AST
values, both full commit/parent identities, both measured transitions and
per-path source hashes.

| # | File | Callable / scope | Metric | Baseline | Current | Introducing transition | Classification |
|---|---|---|---|---:|---:|---|---|
| 1 | `backend/app/modules/wiki/mcps/auth.py` | `verify_token` | loc | 21 | 22 | `1995a1fc` (21→24) | REAL_REGRESSION |
| 2 | `backend/app/modules/wiki/mcps/cli.py` | `main` | cyclomatic | 3 | 4 | `1995a1fc` (3→5) | REAL_REGRESSION |
| 3 | `backend/app/modules/wiki/mcps/cli.py` | `main` | loc | 22 | 28 | `1995a1fc` (22→28) | REAL_REGRESSION |
| 4 | `backend/app/modules/wiki/mcps/data/cli.py` | `main` | loc | 26 | 29 | `1995a1fc` (26→29) | REAL_REGRESSION |
| 5 | `backend/app/modules/wiki/mcps/data/server.py` | `create_server` | loc | 28 | 31 | `1995a1fc` (28→31) | REAL_REGRESSION |
| 6 | `backend/app/modules/wiki/mcps/data/service.py` | `DataService.__init__` | loc | 7 | 8 | `1995a1fc` (7→8) | REAL_REGRESSION |
| 7 | `backend/app/modules/wiki/mcps/data/service.py` | `DataService.__init__` | params | 2 | 3 | `1995a1fc` (2→3) | REAL_REGRESSION |
| 8 | `backend/app/modules/wiki/mcps/experiment_cli.py` | `live` | loc | 3 | 4 | `85b179b0` (3→4) | REAL_REGRESSION |
| 9 | `backend/app/modules/wiki/mcps/experiment_runner.py` | `experiment_manifest` | loc | 29 | 30 | `1995a1fc` (29→30) | REAL_REGRESSION |
| 10 | `backend/app/modules/wiki/mcps/http.py` | `create_http_app` | cyclomatic | 1 | 2 | `1995a1fc` (1→3) | REAL_REGRESSION |
| 11 | `backend/app/modules/wiki/mcps/http.py` | `create_http_app` | cognitive | 0 | 1 | `1995a1fc` (0→2) | REAL_REGRESSION |
| 12 | `backend/app/modules/wiki/mcps/http.py` | `create_http_app` | loc | 44 | 50 | `1995a1fc` (44→52) | REAL_REGRESSION |
| 13 | `backend/app/modules/wiki/mcps/http.py` | `create_http_app` | nesting | 0 | 1 | `1995a1fc` (0→1) | REAL_REGRESSION |
| 14 | `frontend/src/app/wiki/mcp/page.tsx` | `WikiMCPPreview` | loc | 54 | 55 | `1995a1fc` (54→55) | REAL_REGRESSION |
| 15 | `frontend/src/components/ruolo/registered-mails-console.tsx` | `RegisteredMailRow` | loc | 39 | 40 | `2908e0e1` (39→40) | REAL_REGRESSION |
| 16 | `modules/elaborazioni/worker/tests/test_sister_browser_reliability.py` | `_Page.__init__` | loc | 11 | 12 | `47e74500` (11→12) | TEST_ONLY_DIVERGENCE |
| 17 | `modules/elaborazioni/worker/tests/test_sister_browser_reliability.py` | `_Page.locator` | cyclomatic | 3 | 4 | `47e74500` (3→4) | TEST_ONLY_DIVERGENCE |
| 18 | `modules/elaborazioni/worker/tests/test_sister_browser_reliability.py` | `_Page.locator` | cognitive | 2 | 3 | `47e74500` (2→3) | TEST_ONLY_DIVERGENCE |
| 19 | `modules/elaborazioni/worker/tests/test_sister_browser_reliability.py` | `_Page.locator` | loc | 6 | 8 | `47e74500` (6→8) | TEST_ONLY_DIVERGENCE |
| 20 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice` | cyclomatic | 6 | 7 | `47e74500` (6→7) | TEST_ONLY_DIVERGENCE |
| 21 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice` | cognitive | 11 | 16 | `47e74500` (11→16) | TEST_ONLY_DIVERGENCE |
| 22 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice` | loc | 35 | 46 | `47e74500` (35→46) | TEST_ONLY_DIVERGENCE |
| 23 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice` | nesting | 3 | 4 | `47e74500` (3→4) | TEST_ONLY_DIVERGENCE |
| 24 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice.scenario` | cyclomatic | 6 | 7 | `47e74500` (6→7) | TEST_ONLY_DIVERGENCE |
| 25 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice.scenario` | cognitive | 11 | 16 | `47e74500` (11→16) | TEST_ONLY_DIVERGENCE |
| 26 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice.scenario` | loc | 33 | 44 | `47e74500` (33→44) | TEST_ONLY_DIVERGENCE |
| 27 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice.scenario` | nesting | 3 | 4 | `47e74500` (3→4) | TEST_ONLY_DIVERGENCE |
| 28 | `modules/elaborazioni/worker/tests/test_worker_repository.py` | `test_document_path_builders_cover_subject_and_immobile_fallbacks` | loc | 28 | 33 | `7d5aa2db` (28→33) | TEST_ONLY_DIVERGENCE |
| 29 | `modules/elaborazioni/worker/tests/test_worker_reliability.py` | `<file>` | loc | 567 | 584 | `7d5aa2db` (567→584) | TEST_ONLY_DIVERGENCE |
| 30 | `modules/elaborazioni/worker/tests/test_worker_repository.py` | `<file>` | loc | 512 | 534 | `7d5aa2db` (512→534) | TEST_ONLY_DIVERGENCE |

## Preparation failure preserved

V1 session92848 TERMINAL1 at record29 because the diagnostic script initially
assumed every record was callable-scoped. Records29/30 are explicitly file LOC
in the original report and registered baseline. This is a diagnosed local
replay preparation omission, not a runtime or matcher regression.
No complete or partial PASS is credited to V1.

V1 source/log/exit remain byte-exact; DIAGNOSIS_V1.md records their hashes.
Separate V2 adds only correct explicit file scope and fresh output names,
retaining all 30 records and every original assertion. No prior evidence is
overwritten. This replay does not retry any frozen R43 application gate.

## Evidence and reproduction

Private evidence:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r44-baseline-revalidation`.

Retained files: revalidate.py, revalidation.log/exit, DIAGNOSIS_V1.md,
revalidate-v2.py, revalidation-v2.log/exit and revalidated-records-v2.json.
The V2 script refuses to overwrite its output. To reproduce without changing
the saved evidence, use a fresh evidence directory and place a byte-identical
copy of revalidate-v2.py there, then run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 <fresh-evidence-directory>/revalidate-v2.py
```

Requirements: exact integration checkout path referenced in the script,
available Git objects, Python standard library, Node and the existing Babel
AST dependencies. Do not run baseline update/repair.

V2 JSON SHA-256:
`3374f053c9a656e304efdc6ff0a42e204f25eefbf9057fd45944d26fa1c646cc`.
`make graphify-platform-docs`, session58125 TERMINAL0: semantic
`chunk 1/1 done`, no failed-chunk warning; 507nodes/561edges/118communities,
11899input/3754outputtokens, estimated $0.0108. Log/exit retained in R44;
no generated graph tracked. `git diff --check` PASS. Admitted Presenze,
matcher and baseline hashes unchanged after documentation maintenance.

## Classification and remaining work

**NO_CHANGE — PROVENANCE_REVALIDATED**. Provenance of the initial historical30
is independently re-established on the current campaign state; those findings
remain visible debt, not accepted or absorbed regressions.

R39's corrected complete comparison separately returns exit2 for unproven
GAIA users / Organigramma ownership. This evidence does not classify those
ambiguities as historical30, nor declare a global PASS. R43 remains
NOT_ADMITTED, with lint/report/ratchet/final gates NOT_RUN. The campaign remains
ACTIVE/INCOMPLETE; extreme-hotspot reduction and full final suites remain open.
