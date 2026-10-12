# R67 — Existing worker recovery migration, private PostgreSQL verification

## Snapshot and ownership

Test/environment-only continuation after R66 checkpoint92c4cfc7. Dedicated
branch `refactor/complexity-campaign-20261008`; main/actual merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Historical55a1b1d remains the
campaign origin, not today's merge-base. Previous turn is verified progress;
global goal remains INCOMPLETE. Registry precedes native work; prior PROGRESS,
registry and read-only inputs frozen before updates.

Unchanged existing test:
`modules/elaborazioni/worker/tests/test_sister_recovery_migration.py`, SHA256
`c54935bdd79d899c3e6761604f0ac9655a10013817c422e50fc7b96059f43ecb`.
Unchanged migration:
`backend/alembic/versions/20260905_1100_sister_recovery_window.py`, SHA256
`ca709d8222f373d2ced959b7b98e2bbd28dcc10807cd58d8f4057f9495a44352`.
No runtime, test, application schema, auth, quota, baseline, threshold,
exclusion or coverage-policy modification. No new refactor or main merge.

## Historical gap and new test matrix

R50's complete worker suite remains782PASS/1PGskip. The PostgreSQL variant
was skipped because GAIA_TEST_POSTGRES_URL was absent. That historical skip
is preserved, not rewritten as a historical PASS. R67 supplies a new private
PostgreSQL environment and executes the original full two-parameter test.

| Behavior | Original assertion | New V4 result |
| --- | --- | --- |
| Historical row gets no invented first-submission date | Existing row remains(1,None) after upgrade | SQLite and PostgreSQL PASS |
| PostgreSQL column keeps timezone semantics | Reflected column timezone is True | PostgreSQL PASS |
| Downgrade removes only added column | Reflected columns exactly[id] | Both PASS |
| Row retained after downgrade | Row ID still1 | Both PASS |
| Probe transactional isolation | Temporary table and rollback | Private DB before/after user-relations/schema exact |

**2 PASS, 0 skip, 0 fail, 0 error**, native pytest0,0.36s. No assertions changed,
tests deselected, added fake coverage or test retries. Neither a full Alembic
upgrade chain nor concurrent PostgreSQL production transactions are certified.
This closes one specific unverified test variant with fresh evidence; it does
not turn the unchanged historical suite certificate into a new full-suite run.

## Preserved preparation failures and causal corrections

- V1 STOP before pytest: root-owned0700 PGDATA tmpfs parent prevents postgres
  traversal after entrypoint user switch. Owned container removed; cleanup
  assertion separately failed due capitalized versus lowercase Docker absence
  text. Exact43existing containers/67volume sets later confirm no leak.
- Distinct same-image permission diagnostic reproduces0700exit1 and0755exit0
  using the real entrypoint directory setup/gosu. No DB/test/runtime change.
- V2 preparation accepted independently; fixes parent0755, case-insensitive
  absence check and early terminal-container detection. STOP before pytest:
  pg_isready accepts bootstrap server before target database exists.
- V3 independently reviewed stronger readiness requires PID1postgres plus
  actual target-DB SQL. STOP before pytest: image's bootstrap psql clears
  PGHOST and uses default /var/run/postgresql, while only /sockets is listening.
- V4 independently reviewed sole socket correction adds the already-private
  /var/run/postgresql tmpfs socket beside /sockets. No network/host port/volume
  or test change. Final-server readiness and original tests genuinely PASS.

Three failed preparation attempts remain distinct durable receipts. None ran
pytest; V4 is the sole test invocation, not a blind test retry. Infrastructure
readiness polling is recorded separately from test attempts. Permission
diagnostic, exact pinned entrypoint source and each version diff are preserved.

## Private environment and closure

Pinned local image, no pull:
`sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea`,
actual server PostgreSQL16.15. Dedicated token-labelled container, networknone,
no published ports, listen_addresses empty, root read-only, PGDATA tmpfs,
no named volumes. Sole host bind is newly created Unix-socket subdirectory
inside owned0700 short temporary root. No application paths/data mounted.

The image enables trust for private Unix sockets; this is not application auth
modification. External access is restricted by owned0700 socket root, no
container network, no ports. Tests receive synthetic private settings with an
explicit replacement environment dictionary, no inherited provider variables.
Database queries bind current_database/user/version and inet_server_addrNULL;
private schema/user-relations unchanged before/after test. No production DB
connection or production migration application is performed.

All created test/diagnostic containers stopped and removed after positive
full-ID/name/token/image/isolated-mount identity checks. Owned tmpfs databases
destroyed. Empty owned short socket roots retained without deleting evidence.
Existing43container and67volume sets exact, comparing sets rather than unstable
Docker output ordering. All2852integration/2851main protected input hashes exact
against R66 and before/after V4. Main HEAD/status and known untracked Bonifica
test preserved; no resets, cleanup of others' resources or concurrent edits.

## Gates, metrics and classification

Actual-main ratchet and diff-check receipts are recorded in the companion JSON.
No scanner baseline rewrite. Global baseline/matcher ambiguity remains distinct.
Source/test inputs unchanged; certified full suites and complexity full report
not repeated. Last measured1681files/20360callables/1920errors/2736warnings/
4656overlapping findings remain unchanged. Coverage is not measured by this
test-only environment verification; R65 helper100 remains valid and pool523/
522→523/full-worker100 remain FAIL. No runtime complexity reduction credit.

Classification: **VERIFIED_EXISTING_TEST_VARIANT — NO_CHANGE_RUNTIME**.
Independent preflight/terminal review and Graphify docs publication are bound
in `R67_WORKER_POSTGRES_2026-10-12.json`. Global goal remains INCOMPLETE:449backend
and7E2E skips still NOT VERIFIED, pool coverage, matcher ambiguity, excluded
R43/R51/R63 and extreme tail remain unresolved. No automatic new refactor.

## Durable handoff

Evidence root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r67-worker-pg`.
Contains immutable V1/V2/V3 STOPs, cause probes, V4 raw native XML/log/argv/exits,
DB inventories, container identities/closure, custody hashes and reviewer
receipts. Selective local checkpoint commit only, no push or main merge.
Next: separately prioritize remaining legitimate suite skip prerequisites;
do not infer broader PostgreSQL verification from this single variant.
