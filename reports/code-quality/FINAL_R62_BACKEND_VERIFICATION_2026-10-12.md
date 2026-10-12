# R62 independent backend verification — 2026-10-12

Disposition: **PASS_CURRENT_AVAILABLE_BACKEND_SUITE_WITH_SKIPS**. Actual fresh
suite receipts support **7142 passed, 449 skipped, zero failures/errors, 2384
warnings**, across **7591 JUnit cases**, in **1286.26 seconds**. Skips are
**NOT_PASS**. Campaign remains **ACTIVE/INCOMPLETE**; no new runtime change or
complexity improvement is claimed by this verification.

## Independent scope and receipts

Verifier owns only this new report and `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261012-r62-backend-verification/reviewer-evidence`. Integration runtime/tests/config,
all old evidence and R61 reviewers were read-only. Static preparation once
returned exit 0 / STATIC_READY. Root then confirmed inherited PYTEST_ADDOPTS,
PYTEST_PLUGINS and PYTEST_DISABLE_PLUGIN_AUTOLOAD empty before its single native
launch. The preserved `launch-observation.md` records that observation.

Root explicit terminal notification identifies **native session 68373, exit
0**. This verifier independently inspected all **five gate argv/log/exit**
receipts (custody-before, version, backend, custody-after, diff-check), terminal
receipt and raw JUnit/log. Process handle was coordinator-notified, not
independently attached. `audit_terminal.py` ran **once**, metadata-only:
`terminal.argv`, `terminal.log`, `terminal.exit=0`, `terminal-audit.json` retain
the result. No preparation/metadata/native failure occurred in this verifier's
assignment; no native tests/collection, scans, builds, Graphify, repair, install,
retry, policy/baseline edit, commit or old auditor rerun was performed.

Actual backend argv:

```text
env APP_ENV=test DATABASE_URL=sqlite:////media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261012-r62-backend-verification/root-evidence/test-db.sqlite /home/cbo/CursorProjects/GAIA-campaign-20261008-integration/backend/.venv/bin/python -m pytest -ra --maxfail=1 --junitxml=/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261012-r62-backend-verification/root-evidence/backend.xml -o cache_dir=/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261012-r62-backend-verification/root-evidence/pytest-cache
```

The runner is exactly R56's launcher except R62 path/label. Existing pytest
configuration remains unchanged (`testpaths=tests`, default addopts); private
SQLite/cache and PYTHONDONTWRITEBYTECODE=1 avoid shared cache/bytecode writes.
`--maxfail=1` stops the first failure. No selector or marker restriction was
introduced. The raw JUnit suite totals agree with the native log; raw names,
skip messages/text and all warning output are retained without suppression.
JUnit SHA-256 `9cc6b0d7f3e96f40a42e1404e47cb402f75ae73478841d9111472dbe8fdaf46d`;
native log SHA-256 `a4ba84e3a0d86af83399c9d8eaeb0c3046c074f736c5050f6f4a1237fcd56271`.

## Current source custody and R58 additions

Integration HEAD `114fbf7196382c6446a7963c34bd89e4c9795ef5`, main/merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
**1606 backend files** have identical before/after and independently live
rehashed inventories. Backend status, integration/main HEAD, main status/diff,
Presenze file, complexity baseline/matcher and selected dependency/Python
metadata match custody. Optional provider flags remain equal before/after and
to the review environment; no skip-reducing provider edit was made. Selected
metadata is not a complete dependency closure certificate.

Actual source delta from R56: added
`app/modules/operazioni/services/inactive_vehicle_anomalies.py` and two R58 test
modules; modified `app/modules/operazioni/routes/analytics.py`; no removals or
other backend input changes. The current router delegates inactive-vehicle fuel
and usage response mapping to the admitted service. The actual **86 new passing
cases** belong only to the source-characterized R58 modules:

| R58 native module | Passing cases |
|---|---:|
| test_operazioni_inactive_vehicle_mapper_r58 | 49 |
| test_operazioni_inactive_vehicle_r58 | 37 |

All 17 source test functions appear in the new native results. Mapper contracts
cover payload/fallback/read order and failure propagation; route contracts cover
real ORM predicates, dates, ordering, public permissions and response payloads.
Counts come from raw current results rather than predicted parametrization.

## R56 history and fresh workbook proof

R56 contains **7505 cases**: 7056 passed and 449 skipped. Current exact raw IDs
have **four missing and 90 added occurrences**: four generated workbook-ID
replacements plus 86 R58 additions. All other historical raw IDs are present.
All **7505 historical outcome/skip-message/skip-text multisets** remain equal
after only the four freshly proven workbook pair mappings; no existing pass
became a skip. All 449 skip reasons remain preserved across 12 reason groups.
PostgreSQL-dependent skips and unavailable OSGeo/pyproj cases remain NOT_PASS.

Fresh R56/R62 raw workbook IDs were decoded to candidate payloads, each checked
for exact pytest forward rendering and valid ZIP/CRC. Four unique ordered
member-content signatures establish one-to-one pairs from these actual inputs.
Raw IDs are preserved in terminal-audit.json and all **eight raw XLSX payloads**
are snapshotted. Generator source hash is unchanged across R56/current custody.
Every pair has exactly `docProps/core.xml` as the differing member content; only
the two qualified created/modified timestamp texts are ignored. Other member
contents, member order and stable ZIP metadata match exactly; ZIP timestamps
and corresponding core CRC/compression differences are explicitly recorded.
No generic name/timestamp normalization or R45/R56 pair reuse was used.

Actual-content counterchecks rejected changed worksheet bytes, changed creator
and reversed member order for every pair. Candidate decoding plus ZIP/CRC and
forward rendering proves these particular payloads; no general rendering
bijection or arbitrary workbook equivalence is claimed.

## Prior publication and immutable reviewer freeze

R61 publication freeze SHA-256
`4e04ece2fd354d293b9a7e9c3c8de90422a9bea2177c71425ff5503f707dc62f`
was rehashed both at static readiness and at final publication. All **1547
records** match: 1542 original immutable paths and the **five mutable integration
inputs through exact archived companion mappings**. Companion SHA-256
`987a7f694e2da7675c6d8ea53ba94482c60466c48d14cd4e1a641cb89b3d3132`.
No old publication freeze or nested companion was rewritten.

All consumed source/evidence bytes are copied into new content-addressed private
objects. `consumed-evidence-snapshots.json` maps original paths/hashes to copies;
future integration source/doc publication changes do not invalidate this freeze.
`freeze.json` binds this report and private files except itself/detached digest;
`freeze.sha256` binds the manifest. New files use mode 0444, directories 0555.
This is a SHA-256/read-only freeze, not an OS immutable-attribute claim.
No mutable integration document/source path is directly bound in freeze.records.

SQLite cannot certify PostgreSQL locking/isolation/races or transactions on that
engine. This available-suite result is not coverage, E2E, deployment, worker or
campaign completion certification. R43 remains NOT_ADMITTED; its separate grant
and R59/other campaign decisions are unchanged. R62 concludes one reviewed suite
checkpoint only.
