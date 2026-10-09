# R4 Fuel Related Mapping — Independent Final Verification

## Ownership and frozen snapshot

Verifier `r4_fuel_verifier` owns only this report, in dedicated worktree
`GAIA-campaign-20261009-r4-fuel-verification`, branch
`verify/complexity-r4-fuel-related`. Initial clean HEAD `22681c0c`; authoritative
main/merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Exact source `6b1bec8d98571240c809fdf39f82c65af1c8c04f` was applied as
`2c009b3239fe4a3528ec9e93ee9700eaeabd0c8f` after Coordinator authorization.
Independent reviewer subsequently approved that exact source; review report
commit `afcb2146d7a6a41016548924ef55b1d5bc4b7fd9`.

No additional source, configuration, baseline, threshold, exclusion or tooling
changes were made by this verifier. Dirty main was neither edited nor copied.
Source identities:

- Analytics SHA256 `7e21f0f8decae49a795c8cd5ecbfd2df0ada48692fd113a905a9d4f50fda2aff`.
- R4 test SHA256 `713a4e9b009b3dc3dbafd02e800c59142b00001fe37940d049eb79dadac6bd47`.

## Evidence and independently executed checks

Durable artifacts, commands, raw logs, coverage/JUnit XML and exit files:
`/home/cbo/.cache/gaia-campaign/20261009-r4-fuel/verifier/`.
All accepted results below were executed on the frozen source in this worktree;
author/reviewer results are not substituted for verifier execution.

| Verification | Result | Artifact |
| --- | --- | --- |
| Five focused analytics suites | 110 PASS, zero skip, exit0 | `focused.log`, `focused-junit.xml`, `focused.exit` |
| Full-file modified analytics statements | 673/673,100%,zero missing | `focused-coverage.json` |
| Full-file modified analytics branches | 302/302,100%,zero partial/missing | `focused-coverage.json` |
| Unchanged R3 vehicle helper | 20/20 statements,8/8 branches,100% | `focused-coverage.json` |
| Wider Operazioni selection | 198 PASS,14 PostgreSQL skips,86 warnings,exit0/67.01s | `operazioni.log`, `operazioni-junit.xml`, `operazioni.exit` |
| Complete backend suite | 6620 PASS,449 skips,2272 warnings,zero failure/error,exit0/1184.72s | `backend-full.log`, `backend-full-junit.xml`, `backend-full.exit` |
| Differential persisted fixtures | 40/40 whole responses,SQL,parameters,order,input snapshots equal;exit0 | `differential.log`, `differential.exit` |
| Complete AST report | PASS,exit0;1668 files,20282 callable,zero parser/exception errors | `after.json`, `after.md`, `report.exit` |
| Author/reviewer report equality | Complete file/callable/violation objects exactly equal | `metric-audit.json`, `reviewer-equivalence.log` |
| Frozen runtime/protected Git object equality | Source/reviewer/verifier tree and blob IDs identical | `frozen-object-manifest.json` |
| Complexity ratchet main55a | PASS,zero finding,exit0 | `ratchet.log`, `ratchet.exit` |
| Global baseline check | FAIL30,Make exit2/scanner1;exact30 historical audit objects | `global-check.log`, `global-check.exit`, `global-findings.json` |
| Compile/backend style ratchet | PASS,exit0 | `style.log`, `style.exit` |
| Protected files and whitespace | Diff empty;diff-check PASS | Independent Git checks |

Focused run takes90.539s by JUnit. Existing test JWT short-key warnings remain
visible; no warnings or failures were hidden by new filters. Entire modified
analytics file is measured, not just new helpers or selected lines. Four
preexisting defensive excluded lines are unchanged in content and semantics;
no exclusion was added. Coverage gate `--cov-fail-under=100` exits0 with both
statement and branch counts independently checked in the JSON.

## Behavioral checks

The twelve new persisted-record cases execute the actual route across top
vehicle/operator and both related response levels: positive-only nullable
averages, signed/net totals, zero versus None, rounding, stable related ranking,
top-five limit, plate/name/id labels, raw WC/name/unknown identity, and exact
SELECT strings/parameters/order without writes. Existing98 focused tests remain
unchanged. Query and attribution calculations were not extracted or changed.

The inspected author differential script was rerun independently against40
seeded real SQLAlchemy fixtures, using this worktree's runtime and its own
isolated environment. Pre-slice `fuel_analytics` is compiled from frozen Git
source without its router decorator; both versions run against the same records.
The comparison checks entire response models plus query strings/bound values
and their order, identity-map column snapshots and no dirty/new/deleted objects.
This provides controlled SQLite equivalence evidence, not production PostgreSQL
or external-service certification. It is an independently executed shared
harness, not a separately authored differential implementation.

## Metrics and no laundering

Pre-slice metrics are independently measured directly from Git `22681c0c`
source via the current AST visitor. All26 original and28 final callable records
are retained in `metric-audit.json`; every unaffected callable fingerprint
matches. Fresh complete after-report objects exactly match both author and
reviewer reports, rather than comparing summary counts only.

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Fuel main cognitive | 322 | 282 | -40 (-12.42%) |
| Fuel main cyclomatic | 183 | 169 | -14 |
| Fuel main callableLOC | 348 | 350 | +2 |
| Fuel main nesting/params | 4/5 | 4/5 | 0 |
| Analytics aggregate cognitive | 978 | 943 | -35 (-3.58%) |
| Analytics aggregate cyclomatic | 585 | 578 | -7 |
| Analytics fileLOC | 1250 | 1265 | +15 |
| Analytics callable count | 26 | 28 | +2 |
| Global cognitive | 81400 | 81365 | -35 |
| Global cyclomatic | 83377 | 83370 | -7 |
| Global errors/warnings/findings | 1938/2749/4687 | 1938/2749/4687 | 0 |
| Global cognitive>300 callable | 7 | 6 | -1 |
| Global cognitive>200 callable | 17 | 17 | 0 |

New `_fuel_average_fields`: cognitive3,cyclomatic4,LOC9,nesting0,params1.
New `fuel_analytics._related_usage_item`: cognitive2,cyclomatic3,LOC14,nesting0,
params4. Both are below every warning threshold and have zero findings.
Repeated nullable mapping decisions are eliminated; the total cognitive decline
is35, not the principal's40. No mega-function relocation or new runtime file.
Explicit bounded LOC growth and unchanged finding counts are not represented
as LOC/finding improvement. Main is below300 but remains above error thresholds.

## Ratchet and provenance

Ratchet uses `main`, whose merge-base is authoritative55a, and passes with an
empty findings array. Globalcheck independently reproduces exactly all30
original supplied audit finding objects, matching the separate provenance
report:15 historical runtime regressions and15 test-only divergences. The audit
summary is read-only in original GAIA checkout; it is not versioned in this
verifier worktree. No baseline update/repair command was used.

Diffs against pre-slice commit for `config/code-quality/`, `tools/code_quality/`,
`backend/.coveragerc`, `Makefile`, `ruff.toml` and frontend coverage configuration
are empty. Unaffected analytics callable fingerprints and unchanged defensive
coverage pragmas are explicitly checked. Global baseline failure is not newly
introduced by R4 and is neither absorbed nor classified PASS.

## Skip policy and available-suite limits

All14 skipped wider Operazioni tests are in `test_operazioni_integration.py` and
require missing `TEST_DATABASE_URL` for disposable PostgreSQL. Their complete
test IDs and causes are retained in `operazioni-skips.json` and JUnit. They are
not treated as exercised contracts; no skip was added by the slice.

Complete backend run collected7069 tests, with6620 passing and449 skipped.
JUnit independently confirms zero failures/errors; saved shell exit is0.
The single process PID155612/session12434 ran from06:36:53 to06:56:50UTC;
observation waits did not restart it. All skip IDs and exact causes are retained
in `backend-full-skips.json`; grouped results in `backend-full-summary.json`:

| Missing capability / actual skip cause | Count | Impact |
| --- | ---: | --- |
| GAIA_TEST_POSTGRES_URL non configurato | 161 | PostgreSQL behavior unexercised |
| GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race | 120 | Real database race unexercised |
| Concorrenza verificata su PostgreSQL, non simulata da SQLite | 2 | Concurrency unexercised |
| Concorrenza reale verificata su PostgreSQL | 6 | Concurrency unexercised |
| Concorrenza e row lock richiedono PostgreSQL | 1 | Row locking unexercised |
| GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza | 111 | Concurrency unexercised |
| PostgreSQL integration tests require a PostgreSQL DATABASE_URL | 18 | PostgreSQL integration unexercised |
| PostgreSQL integration tests require TEST_DATABASE_URL to be configured | 14 | Operazioni PostgreSQL integration unexercised |
| GAIA_TEST_POSTGRES_URL not configured | 12 | PostgreSQL behavior unexercised |
| TEST_WHATSAPP_POSTGRES_URL requires a disposable PostgreSQL | 2 | WhatsApp PostgreSQL integration unexercised |
| OSGeo non disponibile per generare lo shapefile di test | 1 | GIS shapefile generation unexercised |
| pyproj non disponibile per il fallback pyshp | 1 | GIS projection fallback unexercised |

The449 total matches the prior campaign full-backend skip count. Exact current
IDs are recorded rather than assumed from that older run. R4 adds no skip or
test/config changes to the existing suites. Missing capability does not imply
those449 contracts passed; the executed suite result is PASS with explicit skips.

Reproduction from this worktree's `backend/` directory:

```bash
A=/home/cbo/.cache/gaia-campaign/20261009-r4-fuel/verifier
APP_ENV=test DATABASE_URL=sqlite:////home/cbo/.cache/gaia-campaign/20261009-r4-fuel/verifier/backend-full.db \
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -rs -o addopts='' \
  -o cache_dir="$A/backend-full-cache" --tb=short \
  --junitxml="$A/backend-full-junit.xml"
```

Frontend unit/build/E2E and worker suites were not rerun by this verifier. No
fresh PASS is claimed here for those suites; Coordinator owns any further
integration/browser gates. Graphify module maintenance is also Coordinator-owned,
not inferred from complexity metrics or this report.

## Attempts and diagnostics

The first verifier artifact-validation snippet looked for the unversioned
initial audit summary in its own clean worktree and raised FileNotFoundError.
It was corrected to read the supplied summary from original main without
editing it. That verifier setup failure is recorded in `audit-setup-failure.txt`;
it was not an application test failure and no PASS was claimed for that attempt.
The corrected object/coverage/protected-diff audit passes and is recorded in
`artifact-audit.log`. No suite restart, retry increase or source change followed.

## Classification and residual risks

**IMPROVED — R4 backend slice independently verified.** Frozen-source focused
and wider suites, full-file statement/branch100%, entire available backend suite,
controlled equivalence, true aggregate reduction and ratchet pass. This is a
bounded backend-slice certification, not a claim that skipped PostgreSQL
contracts or the full global multi-wave mission have been completed.

Global campaign remains ACTIVE/INCOMPLETE: extreme callable queue remains,
Capacitas full-file branch gate is separately unresolved at97.52%, global30
baseline divergences remain open, and SQLite/PostgreSQL skip limitations remain
explicit. No next hotspot or additional runtime edit is authorized by this report.

## Report commit

Report-only coherent commit; retrieve exact SHA with `git log -1 --format=%H --
reports/code-quality/VERIFICATION_R4_FUEL_RELATED_2026-10-09.md`. Do not integrate
the verifier's source cherry-pick again: integration already owns the exact source.
