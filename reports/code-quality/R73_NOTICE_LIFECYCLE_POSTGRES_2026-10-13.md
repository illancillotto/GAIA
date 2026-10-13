# R73 — recorded-attempt lifecycle on private PostgreSQL

## Snapshot and ownership

Verification only: full original `backend/tests/ruolo/test_notice_lifecycle.py`,
no runtime, test, assertion, fixture, migration or policy change. Worktree
`/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`, starting HEAD
`e167e981f26d5fffbda4aee2870091d8d6b7edeb`. Actual main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`; original 55a1b1d is historical,
not substituted for the current gate reference.

Registry precedes review assignment. Coordinator owns report/index/registry/
PROGRESS and external evidence; existing `/root/r64_baseline` owns external
review only, no native jobs or repository writes. Independent preparation and
terminal accepted; reviewer stopped. Mutable documents frozen before updating.

## Native result and characterization matrix

**48 original identities: 46 PASS / 2 SKIP / 0 fail/error/NOT_RUN**, JUnit
10.865 seconds. One original full-file invocation, retry zero. Exact historical
names independently verified, not a selected passing subset.

| Behavior | Original verification | Result |
| --- | --- | --- |
| Past shipment declarations, audit/version/notification and stale retry | Original request/API/history assertions on both dialects | PASS |
| Postal/PEC/messo/other duplicates and undated tracking | Existing imported-attempt and evidence assertions | PASS |
| Failure after audit | Original injected ValueError; state rolled back | PASS |
| Invalid/future declarations and missing/reconciled documents | Original 422/404/409 cases | PASS |
| Viewer/module-disabled/inactive/denied section and unauthenticated access | Original real JWT/user/permission dependencies, 401/403 | PASS |
| Read-only eligibility and history reload | Original repository-return stubs disclosed; never authorizes dispatch | PASS |
| Attempt/attempt and attempt/edit serialization | Original two-thread PostgreSQL races / Barrier timeout10s | 2 PASS |
| SQLite race variants | Original dialect deliberately cannot verify PostgreSQL concurrency | 2 SKIP, UNVERIFIED |

The two retained skips have exact original reason
`Concorrenza reale verificata su PostgreSQL` and names:
`test_concurrent_attempts_and_edits_are_serialized[sqlite-attempt]` and
`test_concurrent_attempts_and_edits_are_serialized[sqlite-edit]`.
They are not PASS. This file originally had 22 PASS / 26 SKIP; exactly **24**
prior PostgreSQL skips freshly pass, not 26.

Actual module FastAPI/TestClient routes and real JWT validation/permissions run
on synthetic actors. Only get_db is overridden to private fixture sessions.
API commits release nested savepoints under an outer fixture transaction rolled
back at teardown, not independently durable outer API commits. PostgreSQL races
use committed private seed and independent sessions: one saved/one conflict,
version2/one audit/at-most-one attempt. Original threads/timeouts unchanged.
record_attempt registers past shipment; it does not dispatch to providers.
snapshot_poste reads synthetic private DB rows. Diagnostic stubs/failure injection
remain original. Not full-app initialization, login/password/session/device/
quota/browser/E2E/GIS/provider/NAS or production dispatch certification.
Repository .env influence is not universally excluded. The synthetic 21-byte
JWT key produces 88 InsecureKeyLengthWarning warnings; no security/config fix
or production-key claim is made. Coverage was not measured.

## Custody and private environment

Protected 2852 integration / 2851 main app/test/control input paths and hashes
exact before/prelaunch/after-native. Main HEAD/status and concurrent config digest
exact; unknown-author `.codex/config.toml` and untracked Bonifica test preserved,
excluded, not copied or staged. This R73 custody PASS does not rewrite R72's
historical complete-snapshot FAIL or R69's initial capacity FAIL.

Pinned local PostgreSQL16.15 image
`sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea`,
reviewed 1GiB PGDATA tmpfs / 2GiB memory / one CPU, network none/read-only root,
no ports/named volumes/application mounts/image pull. New owned short socket
under 0700 parent; synthetic users/notices and private UUID schemas only.
DB identity/schemas/user relations/routines exact before/after, advisory locks0.
Owned container stopped/removed after identity/label/mount checks; absence
confirmed, tmpfs destroyed. Socket parent retained at `/tmp/g73-6ns8mpqv`.
43 original containers / 67 volumes exact **sets** with no duplicates; initial
unsorted/final sorted line order differs and is not a resource mutation.

## Gates and admission

`make complexity-ratchet BASE_REF=main`: **PASS, 0 findings**, actual baseline
commit a51a48dc. Diff-check and Graphify platform-docs publication receipts are
bound in companion JSON and durable handoff. No baseline, thresholds, exclusions,
ignore, auth/quota or coverage policy changed. No global-baseline PASS claimed;
matcher/baseline ambiguity remains separate. Full suites/complexity report not
repeated for identical runtime inputs. Coverage NOT_MEASURED_UNCHANGED_RUNTIME;
worker full-file100 remains FAIL. No complexity reduction credit; latest full
metrics remain 1681 files / 20360 callables / 1920 errors / 2736 warnings /
4656 overlapping findings, not newly measured by R73.

Classification VERIFIED_EXISTING_TEST_VARIANTS_NO_CHANGE_RUNTIME. Only this
report, companion JSON, registry and PROGRESS admitted to one local docs commit.
Concurrent main config/Bonifica, R43/R51/R63 partials, cache/DB/dependencies/build/
generated graph excluded. No new refactor/branch/push/main merge.

The first publication-only seal failed parsing the Make echo's shell-variable
brace as JSON, before manifest/commit creation. Original script/log/exit frozen;
distinct static sealing corrects JSON-start selection with separate receipts.
This is not a native test/ratchet failure or retry; no scanner is repeated.

Cumulative fresh verification **250 of 449** historical backend skip identities;
**199 still unverified by follow-ups**. Immutable R62 7142 PASS / 449 SKIP
certificate unchanged. Seven E2E skips, worker coverage FAIL, matcher ambiguity,
excluded partials and extreme hotspots remain. Global goal **ACTIVE/INCOMPLETE**.

## Durable handoff

`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r73-notice-lifecycle-pg`.
121-record native manifest SHA
`df060af7c62af88a613c57b9cf0b2632efb7880a21b774e133636149881b68ba`.
Terminal review SHA
`54fa540c1f70ed68e9206f7b3878ac1b76ece92ec099716a9f1b4233569de2ae`;
review checksum manifest SHA
`0934d8c63e813fcd92285c6a41ea4f43018a1db15d7e76b95db007a378b280d5`.
FINAL_HANDOFF_MANIFEST.json binds stable receipts and published docs;
publication/POST_COMMIT.json and HANDOFF_CHAIN.json bind later commit/custody
without checksum cycles. Parent R72 handoff retained. Next prerequisite requires
its own ownership/preflight; no implied new runtime refactoring or completion.
