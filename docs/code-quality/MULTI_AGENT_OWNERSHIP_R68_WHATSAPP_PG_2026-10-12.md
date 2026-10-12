# R68 — existing Presenze/WhatsApp PostgreSQL checks

Verification only after R67 checkpoint `8f7e0a8e1708002300a2b1e82313ab1fac4114fa`.
Dedicated branch `refactor/complexity-campaign-20261008`; actual main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Historical `55a1b1d` is not
the current merge-base. No new runtime refactoring or test modification.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Coordinator | Presenze PostgreSQL verification | This registry, new R68 report/index, PROGRESS after freeze; external r68-whatsapp-pg except review | Two original tests PASS, actual-main ratchet PASS0, custody and cleanup exact; selective docs checkpoint | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | READY_FOR_REVIEW |
| /root/r64_baseline | Isolation and evidence audit | External r68-whatsapp-pg/review only | Preflight and terminal ACCEPTED_EXISTING_TWO_POSTGRES_TESTS; static only, stopped | Existing reviewer | review/complexity-r64-provenance | READY_FOR_REVIEW |

Read-only ownership: `backend/tests/test_presenze_whatsapp_postgres.py`, its
three migrations and all application runtime. Each existing fixture creates
and drops its own UUID schema; test creates synthetic collaborator/message
rows only within that schema. Real advisory locks must survive app commits,
exclude a second connection and release on exception. Persistence test keeps
original receipt precedence, notification uniqueness, singleton constraint and
upgrade/downgrade assertions. No WhatsApp gateway or real messages are needed.

Pinned local PostgreSQL image; no pull. Dedicated network-none container,
read-only root, tmpfs PGDATA and default socket, one newly owned short Unix
socket bind, no ports or existing volumes. Replacement synthetic environment,
unused private SQLite URL, no production secrets. Readiness requires final
PID1 postgres plus actual target database SQL, as characterized in R67.

Freeze prior PROGRESS and R67 registry before updates. Preserve R62 XML and its
449 historical skips unchanged; any fresh PASS is a separate certificate.
One heavy process at a time; unrelated build is now terminal, never killed.
One pytest invocation, no automatic retry. Any failure stops admission;
cleanup only positively owned container. Independent preflight before native
launch. Full suites and complexity report not rerun for identical input bytes.
No coverage100 claim for unchanged runtime, baseline/policy edit, main merge or
push. Global objective remains INCOMPLETE.
