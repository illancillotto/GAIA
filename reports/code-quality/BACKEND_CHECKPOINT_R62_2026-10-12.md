# GAIA — R62 full backend verification after R58

## Result

Fresh default full backend suite, native session **68373 TERMINAL 0**, all
five launcher gates exit 0: **7142 passed, 449 skipped, zero failures/errors**,
2384 warnings, 1286.26 seconds. One native run, no retry. JUnit contains 7591
actual cases; root independently parsed its totals and the reviewer verified
every outcome, historical identity mapping, skip reason/text and input custody.

Classification: **NO_CHANGE / BACKEND_AVAILABLE_SUITE_PASS_WITH_SKIPS**.
Skips are NOT_PASS. Campaign remains **ACTIVE/INCOMPLETE**; this checkpoint
does not constitute a complexity reduction or final campaign certificate.

## Snapshot and command

Integration: `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`,
branch `refactor/complexity-campaign-20261008`.
HEAD `114fbf7196382c6446a7963c34bd89e4c9795ef5`;
main/merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Concurrent main work remained untouched. From integration backend:

```bash
APP_ENV=test DATABASE_URL=sqlite:///<R62-evidence>/test-db.sqlite \
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -ra --maxfail=1 \
  --junitxml=<R62-evidence>/backend.xml \
  -o cache_dir=<R62-evidence>/pytest-cache
```

Existing testpaths/configuration/addopts unchanged; root confirmed inherited
PYTEST_ADDOPTS, PYTEST_PLUGINS and PYTEST_DISABLE_PLUGIN_AUTOLOAD empty before
launch. Provider flags were captured, not changed to reduce skips. Private
SQLite/cache avoided production DB/cache changes. No selection, dependency,
timeout, skip, assertion, policy, runtime, baseline or matcher edit.

## Historical comparison and source custody

1606 backend inputs match before/after/independently rehashed live sources.
Compared with R56, three added inputs are the admitted mapper service and two
R58 test modules; only analytics.py changed, and no backend input disappeared.
Actual additional passing cases: 49 pure mapper + 37 persisted-route cases.
All 17 source-characterized R58 test functions appear in native results.

Raw historical IDs have four missing and 90 added occurrences. Four narrowly
proven replacements embed generated XLSX timestamps, not changed test behavior.
Fresh candidate-specific ZIP/CRC and exact forward-rendering evidence binds
eight payloads; ordered member contents match except created/modified core
timestamps and corresponding ZIP metadata. Raw IDs remain preserved. The same
comparator rejects changed worksheet, creator and member order for every pair.
With only these four explicit mappings, all 7505 R56 outcome/skip-message/text
multisets remain intact. No general normalization or old pair reuse was used.

449 skips retain 12 reason groups: 447 PostgreSQL/provider-dependent cases and
two missing geospatial dependencies. SQLite cannot certify PostgreSQL locking,
isolation, races or transaction semantics. Warnings remain unsuppressed; the
2380→2384 count is an observation, not a causal regression classification.

## Independent review and evidence

`FINAL_R62_BACKEND_VERIFICATION_2026-10-12.md` imported byte-exact, SHA256
`e792920bcbc6ba8ec73571bec78f404381ee572430ddb373da706389815fe01e`.
Reviewer terminal metadata audit ran once, exit 0. Its freeze contains 2936
records, 3201 consumed bindings and 2911 private content objects; root rehash
found zero drift. Mutable integration sources/docs are privately snapshotted,
not directly bound in the independent freeze.
Freeze SHA256 `7217f1f6a2eec1a8d67116a0df967819c3af16ab58b777793134fbb82d2f3572`.
JUnit SHA256 `9cc6b0d7f3e96f40a42e1404e47cb402f75ae73478841d9111472dbe8fdaf46d`.
Native log SHA256 `a4ba84e3a0d86af83399c9d8eaeb0c3046c074f736c5050f6f4a1237fcd56271`.

Evidence base:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261012-r62-backend-verification`.
R61 publication 1547 records preserved through five exact mutable-input
archives; companion `987a7f694e2da7675c6d8ea53ba94482c60466c48d14cd4e1a641cb89b3d3132`.
Original freezes/companions were not rewritten. No native or metadata failure;
an unrelated failed read of a guessed test filename is separately recorded
in launch-observation.md, not relabeled as a test run or silently discarded.

## Complexity, coverage and remaining decisions

Runtime/accepted metric delta 0. Last full report remains source-bound R59:
1676 files, 20345 callables, 1920 error, 2735 warning, 4655 findings.
No new scan, ratchet or global check is claimed by R62. R60 local ratchet
against main55a PASS/0 remains separate; baseline/matcher hashes stay exact.
The recorded global GAIA-users ambiguity is not repaired by this verification.
Default suite execution does not establish full-file coverage; R58 coverage
evidence is separately recorded in its admitted slice report.

R60 frontend and R61 production build are distinct source-bound checkpoints.
Worker/E2E, unavailable provider tests and further extreme-hotspot reductions
remain open. User-selected fresh Presenze design is already R43, external
NOT_ADMITTED pending the separate DTO/ByRole test-only correction decision.
No R42 retry, R43 fixture edit/admission, pending decision grant, commit, push
or Git merge is inferred from this verification.
