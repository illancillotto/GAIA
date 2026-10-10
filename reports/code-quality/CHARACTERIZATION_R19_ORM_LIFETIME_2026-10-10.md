# R19 — Original ORM lifetime characterization

## Ownership and snapshot

- Agent: `/root/r19_orm_lifetime_author`.
- Worktree: `GAIA-campaign-20261008-catasto-ui`.
- Branch: `test/complexity-r19-orm-lifetime`.
- Original HEAD: `98639b4be554c39e493489d3dd1fb3e9825ac219`.
- Authoritative merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Allocation: `MULTI_AGENT_OWNERSHIP_R19_ORM_LIFETIME_2026-10-10.md`.
- Only new test and this report are writable; runtime and existing tests remain
  unchanged. No rejected V1 or proposed V2 runtime is imported or repaired.
- Protected original inputs: 3557 paths in
  `/tmp/gaia-r19-lifetime-original-protected-20261010.sha256`, manifest SHA256
  `876f7140576cc32db9cbd033e5fee4468855f58603095808c1885dfc8d51b350`.
- Original analytics source SHA256:
  `1ab2e68ebe466f4853ecc86fc0c4d28ca682a1671555a7b5c0d80c0ecc68651d`.

## Responsibility and behavioral invariants

One responsibility: vehicle identity retention between the driver-mismatch
family and later anomaly queries while a distinct writer commits a new plate.

The actual imported original `analytics.anomalies_analytics` is called directly.
Its endpoint identity is checked against the real application route registry;
there is no compiled AST, synthetic source filename, source substitution,
copied runtime implementation, fake scalar result, or private handler invocation.

The seed uses a separate session that commits and closes before the reader
starts. It returns no entities, and the seed function has already returned at
the first read. There are no user/vehicle/session fixtures retaining entities.
The loaded-entity observer records weak references only, including the first
vehicle load. Boundary snapshots contain booleans, numbers and strings, never
strong ORM references. The reader's normal SQLAlchemy weak identity map is not
patched, pinned, expired, refreshed, or synchronized with the writer.

All scalar queries execute through a real `Session.scalars`. The session
subclass records table order and introduces exactly one external Core table
update before the first query matching a literal case-specific table. The
writer uses `engine.begin()` on a distinct DBAPI connection, exits that context
to commit, and a separate Core witness SELECT verifies `AFTER` before the
reader continues. Affected row count is exactly one; reader dirty count remains
zero. These checks distinguish a real committed update from a mock or a
reader-side mutation.

The isolated engine uses a randomly named shared-memory SQLite database and
`QueuePool`, not `StaticPool`: reader and writer connections cannot alias.
The reader executes ordinary SELECTs, and no read transaction is committed,
rolled back or otherwise modified to permit the writer. This follows the
previous successful diagnostic setup rather than asserting file-database
journal or PostgreSQL isolation behavior. Each engine is disposed in `finally`.

The seeded usage and assignment dates are fixed within the explicit requested
one-day period; no moving default window or current-time assertion is involved.
The session is closed, so the orphan-session family cannot create time-dependent
items. Users are active and the other relevant tables are empty.

## Test matrix

| Behavior | Existing test/evidence | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| All families retain the first driver vehicle at the first fuel-log query; both labels remain `BEFORE` despite committed `AFTER` | Private independent R19 differential diagnostic demonstrated original vs rejected V1, but compiled its original route | Versioned actual-route characterization | `test_all_anomaly_families_reuse_driver_vehicle_after_distinct_writer_commit` | PASS — original focused execution |
| Driver-only filter retains the vehicle while assignments load; label remains `BEFORE` after writer commit | Existing analytics suites cover mismatch output, not this writer boundary | Meaningful filtered retention control | `test_driver_only_preserves_loaded_vehicle_during_assignment_query` | PASS — original focused execution |
| Inactive-only filter has no preloaded driver vehicle and reads `AFTER` committed before its first vehicle query | Previous differential probe did not include filtered controls | Counter-control showing external update is observable without prior identity retention | `test_inactive_only_reads_committed_plate_without_driver_identity_retention` | PASS — original focused execution |
| Full literal JSON, ordering and by-type/severity counts; literal full scalar table order; distinct writer/witness and unchanged reader | Previous diagnostic had full-route JSON and query table order | Reproducible assertions on the actual original runtime for all three cases | Shared real ORM setup and each test's literal oracle | PASS — all three original cases |

The full route requires 14 scalar-table queries, the driver-only case four,
and the inactive-only case four. No query SQL equivalence is claimed by this
table-order oracle. Request/response equality covers this seeded scenario only,
not the entire endpoint behavior or permission dependency evaluation.

## Changes and metrics

- Added `backend/tests/test_operazioni_driver_mismatch_lifetime.py`.
- Added this characterization report.
- No runtime, existing test, fixture, baseline, config, threshold, exclusion or
  dependency changes. No installation, cleanup, branch creation or integration.
- No fresh complexity scan is authorized in this static allocation. Runtime
  before/after source bytes are unchanged; no complexity reduction is claimed.

## Tests, coverage and ratchet

The initial STATIC ONLY draft was accepted and the Coordinator explicitly
transferred exclusive ORIGINAL execution. Frozen test SHA256:
`240e462a98325a3cedcd58749b8be692956c0493acd46c0d7e4ecd30f22dec1d`.
Accepted static report SHA256:
`f63343b1181691621947bc32d9d06ea9883f7912e2cc4d08a2df0fc68a8cc004`.
Actual focused command:

```bash
PYTHONDONTWRITEBYTECODE=1 \
  /home/cbo/CursorProjects/GAIA-campaign-20261008-integration/backend/.venv/bin/python \
  -m pytest -q -p no:cacheprovider \
  backend/tests/test_operazioni_driver_mismatch_lifetime.py
```

Result: three original tests PASS, zero failures or skips, exit 0. Native
session 88503 was polled to terminal completion, not restarted. The output
contains three passing dots and `[100%]`; the repository's quiet settings do
not print a numeric summary for this invocation.

Then, sequentially, the same installed Python executed:

```bash
python -m ruff check --no-cache backend/tests/test_operazioni_driver_mismatch_lifetime.py
python -m ruff format --check --no-cache backend/tests/test_operazioni_driver_mismatch_lifetime.py
```

Scoped Ruff PASS, exit 0. First new-file format check FAIL, exit 1: the formatter
requires only that the witness SELECT `.where(...)` occupy one line instead
of three. The chain stopped and the exact failure was reported without a
correction or retry. The Coordinator then explicitly allocated only this
wrapping correction and the remaining gates in the ownership registry.

The author applied that whitespace-only change with `apply_patch`. The frozen
original test is retained privately as `test.before-format.py`, SHA240e462a.
Parsed ASTs before and after are exactly equal with source locations excluded;
proof exit 0. Final test SHA256:
`74f2b509810372fd32381c8f1d23217ca9ca6141bae0f5390cf3385845dcd028`.
No expression, literal oracle, runtime or old input changed. No needless
focused-test rerun was performed or inferred.

Then, serially, final new-file format check PASS0 and scoped Ruff PASS0. The
actual authoritative command completed on native session 45453, exit 0:

```bash
PYTHONDONTWRITEBYTECODE=1 make complexity-ratchet \
  BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2 \
  QUALITY_PYTHON=/home/cbo/CursorProjects/GAIA-campaign-20261008-integration/backend/.venv/bin/python
```

Ratchet PASS, zero findings; the raw JSON names the actual immutable55a base
reference and `findings: []`. The same native process was polled to terminal
completion, never restarted due to an observation timeout.

Exact private evidence directory:
`/tmp/gaia-r19-lifetime-original-20261010.YuQC7k/`.
Files `focused.log`/`focused.exit`, `ruff.log`/`ruff.exit`, and
`format.log`/`format.exit` preserve the original executions and exit codes.
Further evidence: `format-ast-equality.log`/`.exit`, `format-final.log`/`.exit`,
`ruff-final.log`/`.exit`, `ratchet.log`/`.exit`, and
`protected-after.log`/`.exit`. Post-gate verification of all3557 original
protected paths PASS, exit 0; original analytics source1ab2e68e is unchanged.
Working-tree status contains exactly the two new owned files; no tracked diff.
The preliminary repository/config inspection returned exit 2 because optional
queried `backend/pyproject.toml` and root pytest config paths do not exist;
this was a read-only discovery command, not an application or quality gate.

This test-only draft cannot establish full-file runtime coverage or authorize
any runtime fix. No coverage number is inferred from three meaningful cases.
Full-file statement/branch 100% policy remains unchanged. No runtime complexity
report or full-file coverage, type, Graphify, build or complete application
suite was executed in this allocation. The AST check concerns only formatting
identity of the new test, not a runtime scanner or source substitution.
Independent review and any separately allocated rejected-V1 counterprobe remain
Coordinator work; previously passing gates are not attributed to this
characterization.

## Classification and residual risks

`NO_CHANGE — ORIGINAL_CHARACTERIZED; READY_FOR_INDEPENDENT_REVIEW`.

Not `IMPROVED`; no runtime refactor, complexity reduction, full acceptance or
coverage claim. The first format failure and Coordinator-authorized resolution
are both preserved, not relabeled as an initial PASS. The rejected V1 remains
rejected regardless of its previous coverage and ratchet passes.

Limits: isolated synchronous SQLite ORM only; no PostgreSQL, API authorization,
network/service interaction, complete transactional isolation, real parallel
thread timing, production concurrency certification, or full endpoint coverage.
The writer interleaving is deterministic at actual query boundaries, not a
thread scheduler experiment. All three original weakref/boundary assertions
passed, but their narrow scope does not certify other database backends.

Author execution is terminal, inputs and evidence frozen, exclusive heavy
ownership RELEASED. No author commit, merge or integration was performed.

Recommended next action: Coordinator allocates independent review of the
original characterization and any separately owned rejected-V1 counterprobe.
No V2 runtime work is authorized by this characterization allocation.
