# R50 Worker Pool V2 — Complexity Slice Report

## Ownership

New `modules/elaborazioni/worker/tests/test_sister_pool_r50_characterization.py`,
this distinct report, private author-v2-evidence. Fresh SSD author-v2-worktree,
branch `refactor/complexity-r50-worker-pool-characterization-v2`; no application,
existing-test, tooling, baseline, configuration, exclusion or main modification.
V1 remains immutable and failed Ruff I001, despite its31passing tests.

## Baseline / target callable

Clean HEAD114fbf7196382c6446a7963c34bd89e4c9795ef5;
main/merge-base55a1b1d35911451e018b662c2acc450bf5994ea2.
Runtime sister_credential_pool SHA256
b39a936771c238e13d63f82b8b269a55118818c9ea1d8ccdd3e4cf6b080ff894
equal to original, integration and main. R47 full worker gap: pool
lines449/450/451/523, edges105→107/448→449/450→448/450→451/522→523;
retry_metadata line22/edge21→22 outside this slice.

## Behavioral invariants

- Configured credentials respect active status, batch allowlist and ownership.
- Manual batches ignore autosync profiles; perpetual batches require enabled
  profiles but configured IDs do not depend on the current availability window.
- Merge preserves known credential object identity, quarantine and membership;
  metadata refreshes even when no member is added, and new members append once.
- Real asyncio runner tasks wait on an event. A real SQLite refresh persists a
  new credential and synchronous announcement releases the event before either
  runner finishes. No task state/factory/scheduler/all/asyncio.wait fabrication.
- Runtime behavior, transaction boundaries, portal contracts, retry and coverage
  policy are unchanged. No application complexity reduction is claimed.

## Characterization tests

| Behavior | Existing test | Missing | Added | Result |
|---|---|---|---|---|
| Manual configured IDs with closed schedule, owner/allowlist/inactive filtering | Existing load-query tests | Configured-ID query loop | Real SQLite manual test | PASS |
| Perpetual enabled/disabled/missing profiles vs current schedule | Existing profile-load tests | Configured-ID query loop | Real SQLite perpetual test | PASS |
| Merge without additions preserves identity/quarantine and refreshes metadata | Existing positive merge | No-add branch105→107 | No-add then genuine-add test | PASS |
| Pending runner refresh, persisted new member and announcement/event ordering | Existing initial-runner tests | Refresh lifecycle | Real ORM/async test | PASS |
| Second all-done guard true branch522→523 | None | Reachability | Static scoped analysis; no fake test | STILL MISSING |

## Changes

V2 only reorders the original new test's import block according to Ruff I001,
plus formatter whitespace. Body AST and import multiset are independently
identical to V1; no assertion, fixture semantics or four-test responsibility
change. V1 freeze26members rehashed without drift. New spec SHA256
2fdef746e402920a6ab52519ba64a4f980884c473f6cbf303c8f0e85780930e8.

First read-only stdin preparer returned mixed stdout/stderr; source-output
guard rejected it before any source write or test launch. This metadata
diagnostic is explicitly recorded. Distinct preparer separated stderr, then
applied the formatted source via apply_patch; no test retry or runtime repair.

## Metric before / metric after / delta

Runtime bytes, callable/file metrics and complexity findings unchanged; delta0.
No debt transfer, architectural cleanup, extreme-tail or global reduction credit.
R47 whole-worker coverage6072/6077statements,1624/1630branches becomes
6075/6077statements,1628/1630branches through legitimate added characterization.
Pool full-file327/331statements,83/88branches becomes330/331statements,
87/88branches. This is coverage improvement, not runtime simplification.

## Tests

Targeted native session49937 TERMINAL0:31PASS in3.30s,27old plus4new.
Ruff check PASS and new-file format-check PASS on exact final2fdef746 spec.
Complete unchanged `make test-worker`, session86837 TERMINAL0:782PASS,
one skipped, all53testfiles match exact recursive/top-level inventory and all
53native per-file result blocks. Existing52files plus new four-test module,
no suite narrowing, retry, old-test change or skipped assertion.

Skip: `tests/test_sister_recovery_migration.py:22`,
`GAIA_TEST_POSTGRES_URL not configured`; PostgreSQL behavior is NOT certified.
Native log, argv, coverage JSON/XML, individual results, exact skip, inventory
and exits preserved in author-v2-evidence. No global report/ratchet run by author.

Commands use absolute existing integration backend interpreter. Targeted:

```bash
python -m coverage run --branch --source=<author-v2-worker> \
  --omit=<author-v2-worker>/tests/* -m pytest -q -ra --maxfail=1 \
  -o cache_dir=<v2-evidence>/pytest-cache \
  tests/test_sister_credential_pool.py tests/test_sister_pool_r50_characterization.py
python -m ruff check modules/elaborazioni/worker/tests/test_sister_pool_r50_characterization.py
python -m ruff format --check modules/elaborazioni/worker/tests/test_sister_pool_r50_characterization.py
make test-worker WORKER_PYTHON=<absolute-integration-interpreter> \
  WORKER_COVERAGE_JSON=<v2-evidence>/full-coverage.json \
  WORKER_COVERAGE_XML=<v2-evidence>/full-coverage.xml
```

Full Make uses PYTEST_ADDOPTS='-ra --maxfail=1'. Existing per-file isolation,
runtime-only coverage source/omit, combine and temporary lifecycle are retained.

## Coverage

Targeted full-file coverage319/331statements96.37462236%,81/88branches
92.04545455% is a narrower selection, not the complete-worker certificate.
Full suite pool330/331statements99.69788520%,87/88branches98.86363636%,
combined99.52267303%: **FAIL100**. Only missing pool line523/edge522→523.
Full-worker6075/6077statements99.96708902%,1628/1630branches99.87730061%,
combined99.94809913%: **NOT100**. Other gap retry_metadata line22/edge21→22.
Native21existing excluded lines retained (pool12), none newly added.
No rounded-console100, threshold waiver, invented coverage or denominator change.

Under the ordinary cooperative loop, reaching line522 requires first all-done
check511 false. The intervening callbacks and create_task calls do not yield;
pending runners cannot complete until control returns to the event loop.
Event.set schedules wakeups rather than executing them synchronously. The test
asserts honest refresh/announcement/completion ordering; it does not fabricate
the uncovered true edge. This proof is scoped, not universal: custom eager task
factories with pending-ID replacement or reentrant callbacks are outside the
production-model characterization. No runtime guard-removal grant is inferred.

## Ratchet / custody / environment limits

Author complexity report/ratchet NOT_RUN by Coordinator scope; composite
integration gates and complete admitted-input custody follow independent review.
Pre/post custody1047tracked author inputs, main HEAD/status/diff/inputs and
integration tracked inputs: changed keys[] in targeted and full runs. New spec
separately hashed. This is NOT protection of every untracked concurrent source;
root will capture the complete admitted tracked/untracked input set.

Launchers set synthetic test credentials/settings, private SQLite paths,
PYTHONDONTWRITEBYTECODE=1 and root/backend/worker PYTHONPATH, and unset PostgreSQL
opt-in. They did NOT use env-i; inherited environment is not fully sanitized and
absence of all provider keys is not certified. Existing worker tests mock
network/portal boundaries; this is no production portal/browser certification.
No settings/exclusions/config changes or portal-lifecycle behavior claim.

## Classification / files changed / commit

**NO_CHANGE — CHARACTERIZED_WITH_RESIDUAL_FAIL100**.
Only new test and this V2 report, private evidence. No commit/push/Git merge,
baseline inflation, runtime mutation, second hotspot or original-freeze edit.
Candidate remains NOT_ADMITTED until independent review/root fresh gates.

## Residual risks / recommended next slice

Pool100 remains genuinely blocked under read-only-runtime scope, retry_metadata
gap unchanged, PostgreSQL skipped and actual portals untested. Root review,
Graphify publication obligations and integration ratchet remain separate.
Stop at this coherent characterization: do not remove line523 or simulate
scheduler state for coverage. Any new cleanup needs its own ownership and
explicit decision. Campaign remains ACTIVE/INCOMPLETE.
