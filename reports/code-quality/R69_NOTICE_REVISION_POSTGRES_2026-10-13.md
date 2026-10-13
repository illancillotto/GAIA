# R69 — Original Ruolo revision tests, isolated PostgreSQL verification

## Snapshot and scope

Verification-only resume of the global goal; initial HEAD
`0e23008cda3f75871a48c88945d1067ab96a63e3`, dedicated branch
`refactor/complexity-campaign-20261008`, actual main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Historical55a1b1d remains the
campaign origin, not today's base. Prior registry/PROGRESS archived before
mutable updates. All2852integration/2851main protected input hashes unchanged;
main and its untracked Bonifica test preserved. No runtime/test/fixture/migration,
configuration, baseline, threshold, exclusion, coverage/auth/quota policy change.

Original full file `backend/tests/ruolo/test_notice_revision.py`:125identities,
including124historical PostgreSQL skips and1SQLitePASS from immutable R62 XML.
Complete collection, not an easier selected subset. Shared real-domain fixture
and migration unchanged. Existing geo stubs disclosed; these tests do not prove
GIS or end-to-end notice confirmation.

## Reviewer transport recovery

User reactivated goal. Original swarm reviewer /root/r64_baseline is actually
reachable on this turn; existing task resumed without changing model/config,
moving CLI cwd or retrying CLI. Earlier V1/V2 CLI503 logs, mistaken global-only
model inference and corrected config diagnosis remain immutable. Pending CLI
model choice is unnecessary for this transport, not interpreted as approved.
Static original preparation accepted; private capacity correction separately
reviewed. Terminal independent review recorded in companion receipt.

## Original native failure retained

V1: sole original invocation terminatesexit1,105PASS,1failed identity plus its
teardownERROR,0skip,19NOT_RUN;12.991s JUnit. XML107records contain the duplicated
failure/error identity, not107distinct tests. PostgreSQL PANIC/FATAL writing
pg_wal/xlogtemp: **No space left on device**. Private PGDATA tmpfs128MiB exhausted,
OOMKilled=false. Server termination explains query/teardown connection failures;
no demonstrated application regression. DB-after metadata not verified forV1.
Owned container nevertheless removed, tmpfs destroyed, existing resources exact.

User explicitly authorizes a distinct verification changing only private DB
capacity after review. Original FAIL is not erased, merged or declaredPASS.
V2 has separate runner/evidence/container/socket: PGDATA tmpfs128MiB→1GiB,
container memory256MiB→2GiB; new identity only other diff. No WAL durability,
retry, application/test/timeout/assertion or production setting changed.
Reviewer static path-lookup failure and correction are also retained separately.

## Fresh V2 results and characterization matrix

**125 PASS, 0 skip/fail/error**,19.103s JUnit, one complete V2 invocation,
pytest retries0. Two native invocations overall: preserved failedV1 and separately
authorized capacity-correctedV2.125exact original identity names asserted.

| Behavior | Original assertions | Fresh V2 |
| --- | --- | --- |
| All23dependency tables insert/update/delete/truncate | Revision advances only at commit; stale token rejected | PASS92cases |
| COPY/replica and multiple writes in one transaction | One revision per transaction | PASS |
| Rollback/savepoint/no-op | Revision unchanged | PASS |
| Missing singleton / incomplete trigger enforcement | Reader/writer refuse unsafe protocol | PASS |
| Autocommit/repeatable-read/serializable rejection | Explicit compatible isolation required | PASS |
| Metadata parity, downgrade/re-upgrade, epoch and constraints | Actual migration/model consistency and stale epoch | PASS |
| Native concurrent commit fences | pg_blocking_pids observes blockers, commit/rollback and lock timeout semantics | PASS |
| Real domain writers and stale ORM identity | Payments, notifications, recovery, policy and extra dependencies invalidate | PASS |
| SQLite metadata-only | Runtime refuses PostgreSQL-only protocol | PASS |

New evidence verifies124previously skipped R62 identities. Combined with two
R68 identities,126of449historical skip identities now freshly verified;
**323 remain unverified by these follow-ups**. R62 historical7142PASS/449SKIP
certificate unchanged, not rewritten as a complete backend rerun.

## Isolation and custody

Pinned local PostgreSQL16.15 image
`sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea`;
no image pull. Networknone/read-only root/tmpfs data/no ports/no named volumes
or application mounts. Only new owned short Unixsocket directory host-bound,
0700parent. Synthetic replacement environment, unused private SQLite URL;
native test schemas created/dropped by original UUID fixtures, synthetic
users/notices and filesystem tmp_path, no external provider requests.

Reviewer limits: replacement process environment does not independently rule
out repository .env influence during settings import; no universal provider-
absence or production-privilege certificate is claimed. These particular
test paths exercise native DB behavior, not external dispatch. Private
superuser COPY/replica scenario is not a production-role change.

V2 DB identity, schemas, user relations, routines and zero advisory locks exact
before/after. Owned container removed, tmpfs database destroyed.43existing
containers/67volumes exact. Original source hashes and immutable V1/historical
manifests verified; no concurrent work overwritten or automatically admitted.

## Gates, metrics and remaining work

Actual-main ratchet/diff-check and Graphify docs publication are bound in final
receipt. No baseline inflation or threshold/policy modifications. Global baseline
ambiguity remains separate from change ratchet. No full suite/report rerun for
identical protected inputs. Last measured1681files/20360callables/1920errors/
2736warnings/4656overlapping findings remain; no complexity reduction credit.
Coverage not measured for unchanged runtime; worker100 remainsFAIL.

Classification **VERIFIED_EXISTING_TEST_VARIANTS_NO_CHANGE_RUNTIME**.323backend
skip identities,7E2Eskips, worker coverage, matcher ambiguity, excludedR43/R51/R63
partials and extreme tail remain. Goal ACTIVE/INCOMPLETE, not completed.
No new refactor, push or main merge; selective documentation checkpoint only.

## Durable handoff

`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r69-notice-revision-pg`
preserves historical CLI503s, V1 raw FAIL, explicit sizing authorization,
V2 native log/XML/argv/environment/exits, isolated DB inventories and cleanup,
independent review and immutable source freezes. resume-20261013 final manifest
and post-commit handoff chain bind gates/documents/commit without checksum cycles.
Next: separately prioritize another coherent unchanged PostgreSQL verification;
do not infer global completion or new runtime refactoring authorization.
