# R67 — existing worker PostgreSQL migration test

Previous goal turn is progress: R66 native contract observations/counterexample
changed the safe next decision; guard preserved and checkpoint92c4cfc7 committed.
Current branch refactor/complexity-campaign-20261008; actual main/merge-base
a51a48dc4caefbdd1aea82fe4d749054b9465970. No new runtime refactor.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Coordinator | Worker migration verification | This registry; new R67 report/index; PROGRESS after freeze; external r67-worker-pg except review | V4 native terminal0; original2testPASS, no runtime modification; publication pending | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | READY_FOR_REVIEW |
| /root/r64_baseline | Evidence and isolation audit | External r67-worker-pg/review only | ACCEPTED_UNCHANGED_TWO_DIALECT_MIGRATION_VERIFICATION; native inputs/receipts/custody/cleanup verified | Existing R64 baseline reviewer | review/complexity-r64-provenance | READY_FOR_REVIEW |

Read-only: modules/elaborazioni/worker/tests/test_sister_recovery_migration.py,
backend/alembic/versions/20260905_1100_sister_recovery_window.py and all runtime.
Local image digest pinned; no image pull. Dedicated container networknone,
read-only root, PGDATA tmpfs, only newly owned Unix socket bind, zero hostports,
no existing volumes/DB/container touched. Record startup/readiness/test failure
without automatic test retries; always close only positively owned container.
No suite-wide skip elimination, coverage100 claim or deployment/migration apply.
Historical R50 skip stays preserved; new verification is a distinct certificate.

V1 STOP before pytest: PGDATA tmpfs parent0700 prevents traversal after entrypoint
switches to postgres. Separate real permission probe reproduces0700FAIL and
0755PASS with same pinned image/entrypoint. V1 cleanup removed owned container,
but case-sensitive absent-message assertion also failed; receipts retained.
New V2 changes only private tmpfs parent0755, lowercase absence check and early
terminal-container detection. No test/migration change or blind V1 retry.
Coordinator must receive preflight review before distinct V2 native launch.

V2 reviewed launch also STOP before pytest: pg_isready accepted the image's
temporary bootstrap server before target DB creation. Container closurePASS,
existing Docker inventories exact. New V3 readiness requires final PID1postgres,
pg_isready and actual psql current_database match. All other isolation/test/
cleanup inputs unchanged; V2FAIL preserved. Preflight review before V3 launch.

V3 correctly rejects bootstrap; reveals image docker_setup_db psql defaultsocket
mismatch. Native STOP before pytest, cleanupPASS. V4 adds existing private
container tmpfs /var/run/postgresql to Unixsocket directories beside /sockets;
image explicitly clears PGHOST, so no PGHOST workaround. Other isolation/test
bytes exact. Preserve V3FAIL; preflight before distinct V4 preparation.

V4 terminal review accepted2PASS/0skip/0failure, SHA256
bab881f5f31b7a563de34e1d7cf9a4b8e3015f7385852a7ea30b67cac26c4483.
Reviewer static-only, stopped. Selective docs checkpoint allowed; no runtime
admission, worker100 PASS or historical suite rewrite implied.
