# R70 — original notice generation concurrent-change verification

Previous goal turn is verified progress: R69 original125tests passed after
explicitly authorized private-capacity correction; checkpoint2c727b41 committed.
Branch `refactor/complexity-campaign-20261008`, actual main/base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. No new runtime refactor.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Coordinator | Ruolo generation quarantine | This registry, R70 report/index and PROGRESS after freeze; external r70-notice-concurrency-pg except review | Full original36concurrent-change cases, no test edits, one isolated PG invocation | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | READY_FOR_REVIEW |
| /root/r64_baseline | Isolation and evidence review | External r70-notice-concurrency-pg/review only | Static preflight and terminal checks accepted; reviewer stopped | Existing review task, read-only integration inputs | Existing review task | READY_FOR_REVIEW |

Read-only: `backend/tests/ruolo/test_notice_generation_concurrency.py`,
`notice_history_fixtures.py`, both conftests, runtime and config. Same UUIDschema/
FK-closed metadata fixture already exercised by R69; private synthetic users,
notices and tmp_path. Original matrix2taxyears×2generationmodes×3changes×3phases.
Real separate committed PostgreSQL connection injects payment/notification/STEP
change before generation, during patched renderer, or before final commit.
Original renderer/filesystem mocks disclosed: no actual PDF/DOCX certification,
true simultaneous thread race or end-to-end confirmation proof. Selection,
writers, number reservations, commits and quarantine/no-publication assertions
are real. Existing geo stubs do not prove GIS.

Reuse reviewed R69V2 capacity: pinned localPG16.15, tmpfs1GiB/memory2GiB,
networknone/read-only/no ports/named volumes/application mounts, only new owned
short Unixsocket. No settings/durability/test/timeout/policy change, provider
dispatch or production database. Replacement synthetic environment does not
by itself exclude repo.env settings influence; source-call scope reviewed.

Freeze governance and original source; immutable R62 identity inventory. One
heavy job, one full36case pytest/maxfail1/no automatic retry. Preflight review
before launch, preserve failure and close only positively owned container.
Exact DBschemas/relations/routines/locks and source/resources beforeafter.
Coverage NOT_MEASURED for unchanged runtime, no complexity reduction credit,
baseline update/config override/new branch/push/main merge. GoalINCOMPLETE.

Terminal:36PASS/0skip/fail/error,25.922s,retry0; native receipt and independent
review accepted. DBmetadata/routines/zero locks,2852/2851source input hashes,
43container/67volume sets unchanged; positively owned container removed.
Actual-main ratchetPASS0.162of449historical skip identities now verified,
287remain. Only documentation checkpoint admitted; historical failures and
excluded partials untouched. Prepublication versions archived externally.
Post-commit handoff will bind selective local admission without a main merge.
