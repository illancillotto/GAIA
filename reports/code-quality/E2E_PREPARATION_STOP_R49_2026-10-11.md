# GAIA — R49 disposable E2E preparation STOP

## Actual result

Initial isolated stack supervisor TERMINAL1 during seed preparation:
`ModuleNotFoundError: No module named 'app'`. The private Python script runs
from its own evidence-directory sys.path, not the backend package root. The
launcher omitted an explicit backend PYTHONPATH. This is a diagnosed test-stack
preparation omission, not a demonstrated application or matcher regression.

No database was created, no service started, no Playwright test launched.
Teardown receipt has zero children. E2E suite **NOT_RUN**, not PASS or a browser
test failure. All2712protected inputs/main/admitted state unchanged, zero drift;
24E2Especfiles remain exact. Ports39081/39082/39083 remain unbound.

## Preservation and distinct environment proposal

R49 original scripts, supervisor/seed/preflight/custody logs and exits retained
without modification. No runtime/test/config/baseline repair or native retry.
R43 frozen candidate/spec remain external and its test-only decision pending.

Coordinator proposal for a separately named fresh environment preparation:
preserve seed/proxy/custody/test behavior and add only the missing explicit
backend/root package paths to PYTHONPATH, preserving any inherited tail. No
test flags, timeouts, assertions, optional-provider settings or source edits.
The original preparation remains failed, never relabeled PASS. A read-only
independent environment review precedes any fresh launch; new failures STOP.

## Evidence and status

Private evidence:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r49-e2e-checkpoint`.
Seed failure is captured before any database initialization. Supervisor
first-failure.json, seed.log/exit, before/after2712input manifests, custody
receipts and teardown.json bind the exact phase and lack of side effects.

Classification **NO_CHANGE — ENVIRONMENT_PREPARATION_STOP**.
Campaign ACTIVE/INCOMPLETE. Existing backend/frontend/worker/build certificates
remain separate; no E2E or complete-goal certificate. Main/baseline unchanged,
no commit/push/Gitmerge or frozen R43 repair.
