# R19 — Independent original ORM lifetime review

## Ownership and snapshot

- Reviewer: `/root/r19_orm_lifetime_review`, independent of the author.
- Worktree: `GAIA-campaign-20261009-r9-presenze-review`.
- Branch: `review/complexity-r19-orm-lifetime`.
- HEAD: `98639b4be554c39e493489d3dd1fb3e9825ac219`.
- Actual merge-base with main: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Allocation: integration registry
  `docs/code-quality/MULTI_AGENT_OWNERSHIP_R19_ORM_LIFETIME_2026-10-10.md`.
- Only this new report and private execution evidence are writable. No runtime,
  old test, imported characterization, configuration or baseline was edited.
- Imported test SHA256:
  `74f2b509810372fd32381c8f1d23217ca9ca6141bae0f5390cf3385845dcd028`.
- Imported author report SHA256:
  `a25bb55868902773e6f4e2d98f3b77f5fcc8845dc68e9a5f603ecb6d5aa0c7b7`.
- Initial protected3557path manifest verification PASS0:
  `/tmp/gaia-r19-lifetime-review-protected-20261010.sha256`, SHA256
  `876f7140576cc32db9cbd033e5fee4468855f58603095808c1885dfc8d51b350`.
- Initial tracked diff empty; status contains only the two imported new files.

## Independent source review

The test imports the actual analytics module through the backend path provided
by the existing conftest and calls its public `anomalies_analytics` function.
It checks endpoint identity in the actual application route registry. No AST
compiled runtime, source replacement, copied handler, fake query result or
private runtime method participates in the three contracts.

The original driver family stores loaded sessions, `vehicles_map2`, users and
assignments as route-frame locals. In particular, `vehicles_map2` retains the
vehicle beyond completion of driver response mapping and through the later
fuel/inactive queries. The inactive family queries the same Vehicle identity
again without refresh or populate-existing; normal SQLAlchemy identity reuse
preserves the already loaded plate. This is an observable lifetime invariant,
not merely an assumption that equal query order implies equal response data.

The seed function creates entities in a separate session, commits, closes and
returns before reader execution. It returns no entities. No fixture, output
dictionary or observer closure anchors the reader vehicle: the load listener
keeps only `weakref.ref` objects and the boundary dictionary keeps scalars.
The reader uses its unmodified normal identity map and delegates each scalar
statement to the real SQLAlchemy `Session.scalars` implementation. No pinning,
expunge/expire/refresh manipulation or reader-side update manufactures retention.

The engine uses a uniquely named shared-memory SQLite database and QueuePool.
The writer acquires a DBAPI connection distinct from the checked-out reader,
executes a real Core UPDATE and exits `engine.begin()` before the next read.
A separate Core witness SELECT on a non-reader connection observes the committed
`AFTER` value. Each case asserts one updated row and zero reader dirty objects.
The witness need not use a connection different from the already released writer;
the contract correctly requires distinction from the live reader only.

## Behavior matrix and literal oracles

| Behavior | Independent inspection | Fresh result |
| --- | --- | --- |
| All families: first driver vehicle remains alive/in identity map at the first fuel-log query; writer commits AFTER; both mismatch and inactive labels remain BEFORE | Complete literal JSON, total2, by-type/by-severity, exact14 scalar table sequence, complete boundary dictionary | PASS |
| Driver-only: writer commits during assignment loading while vehicle remains alive; mismatch label remains BEFORE | Complete literal JSON, total1, exact4 table sequence and full boundary dictionary | PASS |
| Inactive-only: no prior driver load/identity retention; writer commits before the first vehicle read; inactive label is AFTER | Complete literal JSON, total1, exact4 table sequence and full boundary dictionary | PASS |

These are meaningful positive and negative filter controls, not three identical
calls with renamed expectations. Fixed dates are passed explicitly as the
requested date range. The seeded usage session is closed, so orphan handling
does not introduce a moving-time response. All asserted payloads are literal
domain values rather than expectations recomputed with the runtime algorithm.
The shared inactive constant is altered only for the literal AFTER control.
The query oracle verifies scalar table order, not SQL text, bound parameters
or every possible SQLAlchemy operation.

## Fresh independent gates

Private native evidence directory:
`/tmp/gaia-r19-lifetime-independent-20261010.HsjEIS/`.

All gates use the installed integration Python read-only. No dependency install,
symlink, cache cleanup, branch change or worktree creation occurred.

```bash
PYTHONDONTWRITEBYTECODE=1 \
  /home/cbo/CursorProjects/GAIA-campaign-20261008-integration/backend/.venv/bin/python \
  -m pytest -q -p no:cacheprovider \
  backend/tests/test_operazioni_driver_mismatch_lifetime.py
```

Native49404 terminal exit0, three passing dots/100%, zero failures or skips.
`focused.log` and `focused.exit` preserve this fresh independent execution.
Sequential scoped `python -m ruff check --no-cache` and
`python -m ruff format --check --no-cache` on the exact new test both PASS0;
native logs/exits are `ruff.*` and `format.*`. No correction or retry was needed.
The author's earlier formatter-only FAIL remains disclosed in its immutable
report; this independent PASS does not rewrite that history.

The actual immutable55a Make ratchet completed on native32065, exit0:

```bash
PYTHONDONTWRITEBYTECODE=1 make complexity-ratchet \
  BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2 \
  QUALITY_PYTHON=/home/cbo/CursorProjects/GAIA-campaign-20261008-integration/backend/.venv/bin/python
```

Raw `ratchet.log` explicitly records both `base_ref` and `baseline_commit` as
immutable55a and `findings: []`; `ratchet.exit` is0. This is a fresh actual Make
gate, not an inherited author result. Each live native session was polled to
terminal completion; none was restarted after an observation timeout.

An extra private summary parser failed1 after the successful native gate:
`ratchet-summary.log`/`.exit` preserve JSONDecodeError. It selected the first
opening brace in Make's echoed `${BASE_REF:-origin/main}` instead of the JSON
starting on the next line. Read-only inspection of the existing raw header
confirms this cause. The chain stopped, the Coordinator was notified, and no
parser repair, gate rerun, input fix or result relabeling followed. This ancillary
failure is not a runtime assertion, ratchet finding or hidden native gate failure.

Final verification of all3557 protected paths PASS0, tracked diff empty/PASS0.
The test74f2b509, author reporta25bb558 and analytics1ab2e68e hashes remain exact;
`protected-after.*`, `tracked-diff-after.*`, `frozen-inputs.sha256` and
`status-after.log` preserve the proof. Status contains exactly the two imported
files and this new review report, with no tracked modifications.

## Coverage, metrics and limits

No runtime file changed and no runtime complexity reduction is claimed.
Full-file statement/branch coverage is UNKNOWN in this allocation; these three
contracts do not certify it or replace the GAIA100% policy. No coverage, complete
backend suite, build, E2E or Graphify execution was allocated here.

This is deterministic synchronous SQLiteORM characterization at query boundaries,
not PostgreSQL/isolation certification or a parallel scheduler experiment.
Direct route invocation does not exercise FastAPI authorization dependencies.
It does not cover other entity lifetimes, all filter/date combinations, all
anomaly rules, SQL equivalence or every transaction/failure path.

## Decision

Static review and fresh focused/style/actual ratchet gates accept the narrow
ORIGINAL test-only characterization. Protected-input freeze is complete;
Coordinator retains the integration decision, including the disclosed ancillary
summary-parser failure. Classification:
`NO_CHANGE — ORIGINAL_CHARACTERIZED; READY_FOR_REVIEW`, not `IMPROVED`.
No runtime refactor or global completion is authorized by this review.
Rejected R19V1 remains rejected. A V1 counterprobe and V2 would require separate
ownership/allocation; neither was executed or modified here. No commit or merge.
Global campaign remains ACTIVE / INCOMPLETE.

All native execution is terminal. Inputs, this report and private evidence are
frozen at handoff. Exclusive GAIA heavy ownership RELEASED. No further action
is authorized in this reviewer worktree.
