# GAIA release preflight — 2026-10-07

User authorizes committing and deploying all local changes and checking the
194 existing main commits above the CED checkout `6b61fd27`. Main baseline
before this release is `703f8411`. Production includes independently deployed
Capacitas and personnel hotfixes; preserve their operational configuration.

## Validation

| Check | Result |
| --- | --- |
| Full backend snapshot | 6476 passed, 449 skipped, 1976.07s |
| Frontend unit | 3986 passed, 277 files |
| Frontend smoke | 18 passed |
| Frontend typecheck, lint, build | Passed, existing lint warnings retained |
| Browser suite, disposable real-auth backend | 52 passed, 7 existing skips |
| Complete worker target | 778 passed, 1 skipped |
| Quality tooling | 169 passed |
| Complexity ratchet against main | Passed, zero findings |
| Changed-file Python style | Passed |
| PostgreSQL personnel tests | 4 passed |
| Upgrade on isolated production schema | 20261005_1500 to 20261007_1600 passed |
| Latest personnel resolver regression suites | 140 passed, full-file 100% statements/branches |
| SISTER HTTP health focused suite | 5 passed, full-file 100% statements/branches |
| Remote backend, frontend, shared worker images | Build passed |

Backend/worker coverage reports and focused campaign evidence measure complete
modified runtime files. Worker overall coverage is 99.86%; this is distinct
from the 100% measured for changed worker runtime. Empty live package initializer
has no executable statements. No new exclusion or baseline change is applied.
The last personnel resolver change was incorporated after the full backend run
and separately validated with the 140-test regression suite. Its bytes match
the active personnel-impianti-v2 backend. Backend and worker images were rebuilt.

Fresh-database migration bootstrap fails on missing legacy `org_unit`; the
actual deployment upgrade is validated against an isolated copy of the CED
schema, without production rows. Skips do not certify unavailable live services.
No CI runs were listed for the preceding main SHA; local evidence does not
claim successful GitHub CI.

## Release preparation

- Build/source directory: `/opt/gaia/releases/20261007-all-draft`.
- Images: `gaia-backend:release-all-20261007`,
  `gaia-frontend:release-all-20261007`,
  `gaia-elaborazioni-worker:release-all-20261007`.
- Effective Compose is reconstructed per active service from its actual
  Compose inputs. Existing ports, storage, runtime data, secret mounts,
  Capacitas pacing/cooldown, continuous windows and worker concurrency remain.
  Old code binds into `/app` are replaced by the release images; frontend
  runs its production build. MCP connector remains a separate Compose project.
- Config, hotfixes, patch and container inventory backup is checksum-verified
  under `/mnt/gaia-archive/gaia-release-backups/20261007-all-release`.
  Full database dump is in progress: completion, TOC and checksum must be
  verified before restart or migration. It predates the final personnel import,
  so retain the team's later verified selective backup as well.
- The standard deploy script cannot be used unchanged on the dirty CED
  checkout because it ignores active overlays. Preserve that checkout and
  release from the separate directory with an explicit rollback configuration.

This report is preflight evidence, not proof of a completed deployment.
Deployment still requires verified backup, final image import smoke, graceful
worker stop, migrations and post-start health/HTTP checks. No personnel import
is repeated; the team already performed its separately authorized import.

Local evidence: `/tmp/gaia-release-*`; prior campaign evidence remains in
`docs/code-quality/VERIFICATION_2026-10-07.md` and its follow-up reports.
