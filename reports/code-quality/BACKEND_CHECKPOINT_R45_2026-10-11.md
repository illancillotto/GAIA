# GAIA — R45 complete admitted-backend checkpoint

## Result and scope

Fresh complete backend suite on the currently admitted integration source:
**7020 passed, 449 skipped, zero failures/errors, 2376 warnings** in
1363.99seconds. Session67767 TERMINAL0; native process3279987 no longer exists.
JUnit independently confirms7469cases,7020pass,449skip, no failure/error.
Custody capture TERMINAL0, all1602 backend inputs unchanged. No code/test repair,
retry, baseline/config/scope/threshold change or R43 reactivation.

This is a current-source integration checkpoint, not final campaign completion.
Skipped scenarios remain unverified. No coverage measurement was requested or
inferred; per-slice coverage evidence remains separate. Full current frontend,
production build, worker and E2E certification remain outstanding, as do extreme
hotspot decomposition and strategic debt reduction.

## Snapshot and command

Integration: `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`.
HEAD114fbf7196382c6446a7963c34bd89e4c9795ef5, main/merge-base55a1b1d35911451e018b662c2acc450bf5994ea2.
Admitted uncommitted backend R40 date-guard prerequisite and its additive tests
are included. No Bonifica orchestrator refactor or concurrent main work copied.
Current Presenze source remains deb4, matcher32b and baseline38e6 unchanged.

From integration `backend/`:

```bash
APP_ENV=test DATABASE_URL=sqlite:///<R45-evidence>/test-db.sqlite \
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -ra --maxfail=1 \
  --junitxml=<R45-evidence>/backend.xml \
  -o cache_dir=<R45-evidence>/pytest-cache
```

Default test collection and repository pytest configuration preserved. No
additional test selection exclusions; no optional PostgreSQL/provider flags
configured at preflight or changed to remove tests. Explicit private SQLite
test database avoids modifying an application database. Maxfail1 would stop
on the first failure; none occurred. No application coverage gate was weakened.

## Skipped scenarios

| Exact JUnit skip reason | Cases |
|---|---:|
| GAIA_TEST_POSTGRES_URL non configurato |161|
| GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race |120|
| Concorrenza verificata su PostgreSQL, non simulata da SQLite |2|
| Concorrenza reale verificata su PostgreSQL |6|
| Concorrenza e row lock richiedono PostgreSQL |1|
| GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza |111|
| PostgreSQL integration tests require a PostgreSQL DATABASE_URL |18|
| OSGeo non disponibile per generare lo shapefile di test. |1|
| pyproj non disponibile per il fallback pyshp. |1|
| PostgreSQL integration tests require TEST_DATABASE_URL to be configured |14|
| GAIA_TEST_POSTGRES_URL not configured |12|
| TEST_WHATSAPP_POSTGRES_URL requires a disposable PostgreSQL |2|

All449 exact case identifiers and reasons retained in backend-summary.json and
backend.xml. Missing PostgreSQL settings leave447transaction/race/integration
cases unverified; the remaining2 geospatial cases lack OSGeo/pyproj. They are
not counted as PASS. SQLite evidence does not establish PostgreSQL locking,
isolation or production concurrency.

## Integrity and warnings

Before/after manifests bind1602 tracked/untracked backend source/test inputs,
integration HEAD/merge-base/backend status, main HEAD/status/diff hashes and
admitted Presenze/matcher/baseline hashes. All fields equal after execution;
custody changed keys: zero. No backend or main source mutations observed.

Full2376 warning messages/locations remain in the raw backend log. No warnings
were suppressed by this change; existing pytest configuration was used.
Observed categories include JWT test HMAC key-length warnings, Pydantic
serializer warnings and runpy already-imported-module warnings; none is silently
converted into a PASS for untested behavior or fixed outside the slice.
Host process census also observed an unrelated Piscaware frontend test run.
Only one GAIA heavy gate was launched, but host-wide exclusivity is not claimed;
no unrelated process was stopped or changed.

## Evidence

Private directory:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r45-backend-checkpoint`.

- run-backend.sh and backend.argv: exact launcher/command scope.
- backend.log, backend.exit, backend.xml: native result/all cases/warnings.
- inputs-before.json, inputs-after.json: all protected input hashes.
- custody-after.log/exit and backend-summary.json: independent terminal audit.
- JUnit SHA-256: `6995d1c5d3c67d253b0e396ce3a64c545e7e0fc5feaf20a1a562a5f8c6bd5051`.
- Summary SHA-256: `79b0c2b3274c5c50d0df7fdb1f73d938622f9041a49d85131bd97d1c001c2993`.

Platform Graphify session88581 TERMINAL0 after native backend token release:
`chunk 1/1 done`, no failed-semantic-chunk warning;510nodes/565edges/113communities,
11893input/2589outputtokens, estimated $0.0089. Exact Graphify log/exit retained
in R45 evidence, no generated graph tracked. `git diff --check` PASS.

The global report's Final metrics/top30 sections were corrected from obsolete
R8/R7 values to the admitted R41 full report SHAf0985cac. No new source scan or
runtime reduction credit follows from that documentation correction. Historical
October8 suite results are now explicitly historical, not current certificates.

## Remaining decisions and classification

**NO_CHANGE — BACKEND_AVAILABLE_SUITE_PASS_WITH_SKIPS**.
R43 runtime remains external and NOT_ADMITTED. Its separate test-only correction
decision is pending; native lint/report/ratchet/final gates remain NOT_RUN.
No frozen R42/R43 artifact changed or launcher retried.
Campaign ACTIVE/INCOMPLETE. No commit/push/Git merge or final-goal achievement.
