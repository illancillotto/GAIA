# Private E2E lifecycle V2 — preserved preparation STOP

## Grant and changes

User approves proceeding after the explanation of synthetic devices and the
separate harness-V2 correction request. Existing session/device cleanup grant
remains restricted to private synthetic data AFTER finished native cases.
No new application refactor/auth/quota/config/policy/main integration grant.
V1 source/tests/log/exit/schema are copied and hashed in new V2 freeze; original
STOP, historic R49 failure, terminal R64 receipts and main residual unchanged.

New private test source corrects hardlink creation using alias.hardlink_to(copy)
and proves same inode/nlink. RuntimeError refusals require exact messages;
expected external faults require exact errno/SQLite authorization cause.
Positive/no-op tests precede listener negatives; listener has SO_REUSEADDR,
owned PID/FD and socket diagnostics, free-port checks before/after. Additional
real SQLite/fsync boundary tests cover first-delete rollback, unrelated-table
side effects, intent-fsync failure, terminal-receipt failure and pre-delete BLOB
serialization refusal. Fail-fast, exclusive fresh output paths, no retries.
Cleanup source is BYTE-IDENTICAL to V1; none of its guards is skipped/weakened.

## Actual native outcome

Command: `PYTHONDONTWRITEBYTECODE=1 python3 <external-V2>/test_cleanup.py`.
Terminal1, first test `test_a_positive_and_noop` ERROR in setUp:
`PermissionError: [Errno 13] Permission denied: '/proc/2181/fd/0'`.
No helper cleanup call reaches transaction/deletion; no successful cleanup.json.
No positive/negative assertion is verified. Remaining cases NOT_RUN, never PASS.
New fault-test definitions are proposals, not verified behavior.

Read-only diagnosis: PID2181/PPID1/usercbo/command systemd, Yama ptrace_scope1.
The guard scans all same-UID /proc descriptors, including unrelated protected
user systemd. PermissionError is fail-closed, not ignored. This diagnoses the
current V2 refusal; it does NOT establish the historic V1 bind98 cause.
All three owned ports are currently free. Original historical private DB SHA
ebc902bd5479951f0e3971c85fd21423bee368a21f6c2b0c02eea3fa0a71524d unchanged.
No application stack/browser/E2E/build/scanner or historical DB mutation.

## Decision and safety alternative — NOT IMPLEMENTED

Stop native work and preserve failed V2. A separate current-source static review
may assess explicit owned-process identity/terminal handles/ports and a real
SQLite exclusive lock, instead of scanning unrelated protected services.
No catch-and-ignore PermissionError, arbitrary PID exclusion, privilege change,
systemd termination or loss of process/transaction safety is authorized.
Design/run decision requested separately; do not automatically retry V2 or call
the future alternative equivalent without proof. Worker/browser descendants,
unknown owned handles, inode/path swaps, snapshot consistency, lock contention,
pre-mutation durable inventory and failure/commit receipts must be demonstrated.

## Custody and limits

Independent static reviews are terminal, in new cleanup-review/REVIEW.md and
runner-review/REVIEW.md. Alternative is conditionally viable, not implemented
or certified. Critical runner finding: Playwright detaches Chromium into its
own process groups; supervisor leader termination alone cannot prove drain.
Future design must register PID/starttime/ancestry and detached groups, reject
unknown live descendants or required handle permission gaps, explicitly close
SQLite connections, refuse WAL and take real BEGIN EXCLUSIVE BEFORE snapshot.
Locks do not exclude unowned raw/idle file readers; do not claim global handle
absence. Private file lineage/access and bounded owned-process proof are a
different explicit safety contract requiring the pending decision and real
reader/writer/browser/fault countertests. No PermissionError catch-and-ignore.

External V2 root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/e2e-lifecycle-v2`.
Frozen V1, new cleanup/test source, native log/exit, fresh candidate copy,
proc-diagnostic.txt and STOP_SHA256SUMS retained without overwrite. Registry
predates reviews. Static agents have no native token or source-edit ownership.

R64 stays committed29994c62 and verified253/full100/ratchet0; no source change.
R61 source/artifact binding remains distinct from future E2E certification.
Historical37PASS/1FAIL/5skip/18NOT_RUN, backend449skip, worker coverage failure
and global baseline ambiguity remain open. Global campaign NOT COMPLETE.
