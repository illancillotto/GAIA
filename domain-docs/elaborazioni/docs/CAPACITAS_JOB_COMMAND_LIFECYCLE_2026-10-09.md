# Capacitas — rerun/delete command lifecycle

## Scope

R12 isolates the duplicated lifecycle of eight existing rerun/delete handlers
in `frontend/src/components/elaborazioni/capacitas-workspace.tsx`.
Reviewed source `3b511b6d` / SHA256 `b69cbc44` is independently APPROVED/IMPROVED,
finally certified and integrated as `673026e7`. Review-only `8da06a90` and
certificate-only `bfe0b2d7` are integrated as `29f29497` and `b7e3ff2c`.
All three sequential authoritative main55a ratchets PASS0. Campaign remains
ACTIVE/INCOMPLETE. No API, job status, polling or functional change is introduced.

`runCapacitasJobCommand` receives the selected job ID, the existing imported API
as a separate unbound function, and typed family/action state ports. The closed
rerun/delete union restricts reload/expiry to rerun and row mutation to delete.
Eight existing named handlers bind the original endpoint and family setters.
No new component, hook, context, export or runtime module is introduced.

## Behavioral contract

1. Read the stored token synchronously; missing token remains a no-op.
2. Set the selected busy ID before entering the original try boundary.
3. Await the original API with the captured token and requested ID. Ignore its
   returned ID, as before; do not bind an API receiver or add another await.
4. Rerun success clears family session expiry, confirms the requested ID, clears
   the command error and awaits the original loader. That loader reads the token
   again and owns refresh authentication/error behavior.
5. Delete success confirms the ID, clears the command error and filters the
   current row state functionally. It neither resets expiry nor requests a list.
6. Command failures display Error.message or the exact family/action fallback.
   Genuine command ApiError401/403 is still an ordinary command error; loader
   authentication handling must not be applied to command failures.
7. Finally clears the scalar busy ID even when another command remains pending.

| Family | Rerun/delete confirmation prefix | Non-Error failure suffix |
| --- | --- | --- |
| Terreni | Job | Terreni |
| Particelle | Job particelle | particelle |
| History | Job storico | storico anagrafico |
| inCASS | Job avvisi | avvisi |

## Concurrency deliberately preserved

The scalar busy ID is not a reference count: a later dispatch overwrites it and
an earlier completion can clear it. Last completion still determines notices
and errors. Deletion filters current rows; a later manual/polling list response
can resurrect a deleted row. There is no generation guard, cancellation,
single-flight command controller or race fix. Polling and monitor lifecycle
remain those documented in `CAPACITAS_JOB_MONITOR_LIFECYCLE_2026-10-09.md`.

## Characterization and measured reduction

80 new public-UI cases characterize deferred command/refetch failures, token
change/loss, command-versus-loader auth errors, different-ID completion orders,
early busy release and delete versus manual/real polling. All twenty specs are
frozen, with real usePolling and genuine ApiError; no private React access or
counter-driven coverage fixtures. Original and actual modified full suites both
pass476/20 with zero skip. Independent original and runtime replays agree.

Both complete runtime files have100% statement/branch/function/line coverage:
workspace715/798/248/622; unchanged fraction policy9/6/6/8 after refactoring.
Project/explicit-new-test TypeScript, owned ESLint, integrity and authoritative
main55a ratchet pass. Distinct final verification additionally passes4655whole
frontend tests/306files, smoke18, clean build, full lint with35unchanged warnings,
56native command scenarios+genuine login and32overlap timelines. Browser virtual
clock drives actual polling; it is not a wall-clock timing proof. Pertinent
E2E4PASS; full available E2E54PASS7historicalSKIP0retry/flaky. Optional GIS/provider/
PostGIS skips are not passing certification. All owned resources are terminal;
no global backend/worker suite completion is claimed.

Principal cognitive391→359, cyclomatic360→336, callable LOC2527→2487.
Combined cognitive926→871, decisions803→762, raw cyclomatic1062→1016;
effective file LOC3131 unchanged. New helper9cognitive/8cyclomatic/24LOC is
below every warning threshold. State31/effect2 unchanged. Finding counts17error/
16warning remain unchanged: the principal still exceeds thresholds, while
aggregate decision duplication genuinely decreases. Classification IMPROVED
does not mean the extreme hotspot or global campaign is resolved.

Source, invariants, test matrix and command evidence are in SLICE_R12 and
REVIEW_R12 reports under `reports/code-quality/`. Baseline/soglie/scope/config
remain unchanged; historical global30 finding objects must be handled separately.
