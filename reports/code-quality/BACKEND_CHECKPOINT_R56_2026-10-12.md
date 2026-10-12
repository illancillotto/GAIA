# GAIA — R56 full backend verification after R52

## Result and scope

Fresh default full backend suite on admitted post-R52 source, native session
37710 TERMINAL0: **7056 passed, 449 skipped, zero failures/errors**,2380warnings
in1276.06seconds. All five native launcher/custody gates exited0. Pytest ran once;
metadata audits are separate observations, not test retries. Independent final
review0ad519a8 verifies PASS WITH SKIPS; its73record freezecfd00d35 rehashes
with zero drift. The report is imported byte-exact into integration.

Runtime classification: **NO_CHANGE — BACKEND_AVAILABLE_SUITE_PASS_WITH_SKIPS**.
Campaign remains ACTIVE/INCOMPLETE, full objective unchanged. Skipped cases are
unverified, not PASS; no full-file coverage, PostgreSQL behavior or global
campaign completion is inferred from a default SQLite run.

## Snapshot and command

Integration `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`,
branch refactor/complexity-campaign-20261008;
HEAD114fbf7196382c6446a7963c34bd89e4c9795ef5,
main/merge-base55a1b1d35911451e018b662c2acc450bf5994ea2.
Main contains concurrent work and was not modified. R43 Presenze remains
external NOT_ADMITTED; no pending decision was inferred.

From integration backend, with existing repository testpaths/configuration:

```bash
APP_ENV=test DATABASE_URL=sqlite:///<R56-evidence>/test-db.sqlite \
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -ra --maxfail=1 \
  --junitxml=<R56-evidence>/backend.xml \
  -o cache_dir=<R56-evidence>/pytest-cache
```

Python3.12.3/pytest9.0.3 and selected dependency metadata/binary bound before/
after. Optional GAIA_TEST_POSTGRES_URL/TEST_DATABASE_URL/
TEST_WHATSAPP_POSTGRES_URL were unconfigured and were not changed to reduce
skips. Private SQLite/cache avoid production database/cache mutation. No test
selection, timeout/skip/config/policy/dependency/source/assertion change.

## Exact collection and historical comparison

Actual current JUnit has7505cases,7056pass449skip0failure0error. Source inventory
1603 versus historical R45 1602: only analytics.py runtime changed by admitted
R52 and its new test_operazioni_hours_anomaly_r52.py. No backend input removed.
Thirty-six genuine new R52 test cases explain the count delta7020→7056; do not
substitute a guessed78 or count supplemental source assertions as native cases.

Raw historical identity Counter is NOT identical:7465old case descriptors match
exactly, four parameterized invalid-workbook names embed generated XLSX bytes
and differ. Four replacements are narrowly paired by actual content evidence,
not silent name normalization or arbitrary nearest-match fallback. Their test
source SHAa14dc28b and constructor/parameter list are unchanged.

Eight archived candidate payloads have exact hashes/sizes, valid ZIP CRCs and
forward pytest-rendered names exactly matching their respective raw native IDs.
Ordered nine-member inventories and every non-core uncompressed byte match;
only created/modified core metadata and ZIP timestamps differ. All other core
properties stay authoritative. This is a constrained proof for these eight
archives, not a general bijective reverse-decoder claim. All raw IDs preserved.
Complete content-signature comparator rejects modified worksheet data, changed
creator, reordered members and removed member for each of four pairs.
With these explicit pairs, all7469old outcomes/skip reasons are retained and
the only additional cases are the36R52cases. No native assertion/test renamed.

## Skips and diagnostics

All449skip identifiers/reasons remain in raw JUnit and metadata summary:
447PostgreSQL/provider transaction/race/integration cases and two geospatial
cases missing OSGeo/pyproj. They are not executed successes. SQLite cannot
certify production PostgreSQL locking/isolation/race or transaction semantics.
2380warning occurrences retained in raw backend.log, no new suppression; the
existing pytest filterwarnings configuration remains unchanged. Comparison with
historical R45 warning count2376 is observational, not proof of a new regression.

## Custody and immutable history

All1603backend tracked/untracked source/test/config hashes, selected package
metadata/Python binary, integration/backend/main state and baseline/matcher/
admitted Presenze hashes are exact before/after/live. Input manifest SHA:
`70890a62c94cd52b38ff9dfede367445fb4d55fa83ee1f9e15678c13fb12e4c1`.
No baseline/threshold/ignore/config/source/dependency change, commit/push/Gitmerge.

R55original258record publicationed09721a remains intact via companion21e9015a:
five mutable integration-input byte snapshots and253unchanged immutable records.
Nested R54/R53 companions preserved. No frozen evidence rewritten for doc updates.

## Preparation STOPs retained separately

- Reviewer first static STOP: Python -m pytest confused with pytest marker filter;
  unreached conftest variable-name assumption also diagnosed. Distinct static V2
  passed before native launch, with narrowing counterexamples; originals retained.
- Root first metadata STOP: four date-bearing raw workbook IDs not exact;
  first stderr exceeded bounded tool output and no complete local stderr exists.
  ROOT_METADATA_STOP/DIAGNOSIS explicitly record that limitation and correction.
- Distinct root V2 failed a guessed archive filename, V3 overescaped root encoder
  literals, V4 an accidentally retained duplicate unaliased Counter. Each exact
  script/argv/log/exit/diagnosis retained. No native test/config/assertion repair.
- Distinct V5 validates actual terminal/current-case/content/custody proof and
  emits backend-summary-v5.json. Do not report every metadata exit as a native
  gate or imply that the earlier audit observations were PASS.

## Evidence and limitations

Private base:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261012-r56-backend-verification`.
Root-evidence retains launcher/all native argv/logs/exits/terminal, raw JUnit,
beforeafter manifests, all STOPs and separate V5metadata proof. Reviewer-evidence
retains actual archived workbook bytes/content diagnosis; no runtime/test repair.

Current JUnit SHA:
`c228ed0449f659a0aea5349ae9fffa1892f94d261daccb4e2f5025923547a3b9`.
Root V5metadata summary SHA:
`0267fc1acf56e3821a13116c170b037adcfed3e18248f0fdba03e0831ccd0646`.

Current frontend R54 5153unit/320spec+18smokePASS and R55build163of163PASS are
separate evidence. No worker/E2E/provider/coverage/global certificate inferred.
Runtime metrics and last admitted R53ratchet remain unchanged, no fresh
complexity gate or reduction credit for this runtime-NO_CHANGE verification.
R43test-only/R51/E2E/Bonifica/worker decisions remain distinct and pending.

Independent `FINAL_R56_BACKEND_VERIFICATION_2026-10-12.md` separately verifies
default scope, every raw case/status/skip, all1603live inputs, R55/R54/R53 archive
bindings and eight workbook payloads;20same-comparator negative checks reject
arbitrary payload alterations. Its own first broad-exit terminal audit STOP is
preserved: metadata exits are not native gates. Distinct terminal V2/final
audit names the five native gates and records every preparation failure separately.

## Documentation maintenance

Dedicated `make graphify-platform-docs`, session82439 TERMINAL0:
`chunk 1/1 done`, no failed semantic chunk warning.619nodes/723edges/
126communities,6210input1850outputtokens, estimated cost $0.0054. Exact argv/log/
exit retained, generated graph ignored. This is not code complexity or test evidence.
