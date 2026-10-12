# GAIA — Private E2E synthetic-device readiness 2026-10-12

## Scope and outcome

**STATIC_READY_FOR_LIFECYCLE_REVIEW — NOT LAUNCHED**. User authorized reset of
only existing synthetic device/session records in the private E2E database.
This report does not execute that reset, mutate a database, start a stack,
collect/run tests, build, scan or retry R49. Prior provenance report remains
byte-identical SHA256 `77f18f531b33875d756cf825cfb07862b98380fbf744915e0036c872c425c687`.

Ownership was registered before delegation. Worktree/branch remain SSD resume
`r64-baseline` / `review/complexity-r64-provenance`, HEAD and merge-base main
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Only this new report and external
`e2e-readiness/` artifacts are owned; no commit or application/helper installation.

## Historical failure preserved

R49 V3 already ran the complete collection24specs/61cases once, worker1,
retries0, max-failures1:37PASS,1FAIL,5explicit skips,18not-run. The failing
Ruolo case stopped during actual loginHTTP403, before its domain assertions:
super_admin's existing20-active-device quota was exhausted. Original JSON,
trace/screenshot/video, DB, argv/log/exits and input manifests remain unchanged.
Neither the61-case collection nor the37passing cases certify an entire suite.

Historical private stack gateway39081/Next39082/FastAPI39083 was seeded through
existing models into SQLite282tables with one synthetic admin and85sections;
no INAZ mapping or cadastral seed. Owned children were terminated in R49.
This static activity does not infer current process liveness from old PID files.

## Read-only database proof

The historical DB is:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r49-e2e-checkpoint/environment-v3/e2e-db.sqlite`.
SHA256 `ebc902bd5479951f0e3971c85fd21423bee368a21f6c2b0c02eea3fa0a71524d`
matches the immutable2131-record native-stop freeze. Seed receipt binds the
same absolute SQLite URL and admin role. No live DB or dotenv secrets are read.

Fresh stdlib SQLite connection used URI `mode=ro` plus `PRAGMA query_only=ON`.
Database bytes before/after match; no WAL/SHM/journal sidecar exists.

- Exactly one application user: id1, usernameadmin, rolesuper_admin, active.
- Exactly20 devices, all user1/statusactive, first/last IP127.0.0.1.
- Exactly21 sessions, all user1/admin/sourcegaia_login/IP127.0.0.1:
  20login_allowed and1login_blocked `max_active_devices:20`.
-282tables; `PRAGMA foreign_key_check` yields zero violations.
- Only incoming reference to the two target tables is
  `network_vpn_sessions.device_id → network_vpn_devices.id ON DELETE SET NULL`.
  Devices also reference application_users withCASCADE; session user references
  application_users withSET NULL. Delete sessions before devices, not users.

Inspector terminal0 confirms read-only ownership/count/FK/custody evidence.
It is not a test-suite or mutating-cleanup PASS. Nonsecret IDs/session events
are retained in `private-db-inspection.json`; no password/token is inspected.

## Lifecycle proposal and pending decision

Initial reset releases the20slots but does not prevent new browser-context
device IDs from accumulating again over61cases. Existing frontend stores a
client-device UUID in localStorage; isolated contexts receive different IDs.
Quota enforcement remains unchanged at20. Removing tokens/logging out is not
evidence that persistent active device rows are removed.

Proposed private runner: preserve original DB; operate on a distinct candidate
copy; freeze the full current case collection and run every exact identity once
with workers1/retries0 and unchanged config/assertions/timeouts. AFTER native
case completion, result preservation and worker/owned-stack termination only,
snapshot and reset the permitted synthetic session/device rows transactionally.
Restart unchanged stack for the next identity. Never clean during a case or
before its assertions; on failure preserve and STOP, no masked failure/retry.

All unrelated table contents and FKs must match before/after each cleanup.
Schema, user/counters, domain data, quota/auth policy, test source and application
runtime are never reset. Candidate path and ownership are fail-closed; unknown
user/IP/source/FK or unexpected table difference stops the cleanup.

**Separate decision needed:** extend existing-row authorization to lifecycle
cleanup of newly-created synthetic rows AFTER each completed case, and accept
the disclosed one-case-per-native-invocation/quiescent-stack shape. This is not
equivalent to the original single Playwright invocation; reviewer must verify
collection parity, order/hook assumptions and no inter-case behavior obligation.
No serial-mode suite declaration was found in the current24specs, but that alone
does not certify identical execution semantics. Original single-process test
results remain the reference failure, never overwritten or relabeled.

An async reporter `onTestEnd` alone is unsafe: installed Playwright1.59.1 sends
testEnd from WorkerMain and advances its loop; dispatcher invokes reporter
without awaiting cleanup. No application auth patch, request interception,
shared browser device-ID, quota increase or worker monkeypatch is authorized.
The proposed fail-closed cleanup source and runner design are **NOT EXECUTED,
NOT TESTED**; a subsequent independent review/token grant is required.

## Current-source and stack parity limits

All24current specfiles match R49 hashes exactly; no added/removed/changed spec.
Full current61-case collection has **NOT_RUN** and must still be established.
Among2712previous protected inputs,11now differ:7runtime backend,2backend tests,
CatastoGIS page and Capacitas workspace. Exact path/hash differences are retained
in `input-parity.json`. Prior R49 build/runtime/input manifest is therefore not
a certificate of current runtime. Config/test flags must not be silently changed.

Use current certified build inputs only after exact artifact/dependency/build
custody verification. No fresh build is authorized here. SQLite/mock-heavy
specs do not prove PostgreSQL/PostGIS, provider, INAZ mapping or production
parity. The5optional skips remain unverified; backend449skips and worker gaps
remain separate. A future privately-managed run is not a live-stack8080 proof.

The V3 supervisor inherits a sanitized `env -i` whitelist and injects synthetic
credentials/private DB; proxy preserves API routing to owned loopback services.
Copied scripts must receive new evidence paths and preserve before/after input,
baseline, matcher, build and main custody. V3's current filenames refuse reuse,
and its original seed refuses an existing DB: do not edit or rerun frozenV3.
No application .env may load; no inherited provider flags/secrets are authorized.

## Evidence and handoff

New private directory:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/e2e-readiness`.

- `inspect_private_db.py`, `inspection.log/exit`: new read-only execution.
- `private-db-inspection.json`, SHA256
  `8b8841720cc41100075ccb1693819151a5166b84e1c1084451b6f0ff5c768fb5`.
- `input-parity.json`:11source differences and hashes of14R49critical artifacts.
- `RUNNER_DESIGN.md`, `proposed_cleanup.py`: separate private proposals, not run.
- `SHA256SUMS`: durable manifest covering new artifacts and copied report.

Before any authorized execution: independently preserve a fresh complete DB
copy, verify original hash/freeze and current inputs, inspect process handles/
free owned ports, allocate one heavy token, review proposed cleanup and its
first-failure semantics. Preserve every per-case before/afterDB, exact deleted
row receipt, native outcome/exit, unaffected-table checks, logs and final custody.
Do not overwrite R49 files, prior freezes, or this static receipt.

Graphify extraction NOT_RUN due static-only ownership/heavy-token separation;
no runtime responsibility changed here. Coordinator manages publication's
documental Graphify obligation. Global goal remains ACTIVE/INCOMPLETE.
This readiness activity does not resolve historical global matcher ambiguity,
admit R64/R43/R63 or certify any new E2E PASS.
