# GAIA — Independent Round 3 Verification

## Status

**Scoped integration GREEN; global goal ACTIVE / INCOMPLETE.**
Evidence cut-off updated: `2026-10-08 17:46 UTC` (19:46 Europe/Rome).
R3 has real, modest reductions and zero change-ratchet regressions. The full
backend suite completed6608PASS449skip/exit0. Fresh R3 browser confirmation passes after an
initial failed full run; the intermittent GIS risk is unresolved. This is an evidence
checkpoint, not global campaign completion or authorization for another slice.

## Ownership and snapshot

Independent verifier owns this report only; runtime, baseline, shared files
and tooling are read-only. Activation registry `d1c6f678`; initial HEAD
`d1c6f6780415e7b95ad4cabe59e66f3d1d8f947d`, authoritative merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`.
Integration worktree `GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`. Initial untracked integration report
was owned by another agent and preserved. No commit by this verifier yet.

R3 sequential integration independently marked GREEN in reports committed
`8c4e8c40` and `c7d79229`. Scanner snapshot
`c7d7922988b9e987172081e523aff4ec20763204`; later registry-only governance
and progress commits through `d3844df6` do not change runtime or protected
files, independently checked by diff. Final backend runtime
`0b1a0d3767e4e75b4cf34cfe0daf737609e6ccb0`; UI runtime
`b0dd9228b8f2f492264b372bee0a9875b05426f9`.
Main/concurrent work is neither copied, reset nor incorporated.

## Independent commands and artifacts

Executed in integration, not inferred from agent claims:

```bash
make complexity-report QUALITY_PYTHON=backend/.venv/bin/python \
  REPORT_JSON=/tmp/gaia-r3-integrated-complexity.json \
  REPORT_MD=/tmp/gaia-r3-integrated-complexity.md
make complexity-ratchet BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python
make complexity-check QUALITY_PYTHON=backend/.venv/bin/python
APP_ENV=test DATABASE_URL=sqlite:////tmp/gaia-r3-quality.db \
  backend/.venv/bin/python -m pytest -q tests/code_quality \
  -o addopts='' -o cache_dir=/tmp/gaia-r3-quality-cache --tb=short
```

Logs `/tmp/gaia-r3-independent-{complexity,ratchet,check}.log` and
`/tmp/gaia-r3-quality-tests.log`. Read-only evidence script
`/tmp/gaia-r3-independent-evidence.py`, output
`/tmp/gaia-r3-independent-evidence.json`, includes all domain groups, hashes,
coverage counters, tails and top 30. No baseline generation/repair was invoked.

## Clean versus concurrent audit counts

The official October 8 audit remains **1665 files / 20261 callables**,
4714 findings, 1956 errors and 2758 warnings. It included concurrent source
changes, despite its source_commit metadata pointing at main55a. The clean
55a report is **1662 files / 20257 callables**, with the same finding totals.
They are distinct source populations, not contradictory scanner results.

Three audit-only files were not silently imported into integration:
`backend/app/modules/presenze/services/gate_inaz_details.py`,
`backend/app/modules/presenze/services/inaz_assigned_calendar.py`,
`backend/app/modules/ruolo/services/posta_online_recipient_columns.py`.
Common-file metric differences also occur in Presenze `gate_mobile_payloads.py`,
`operai_schedule_policy.py` and Ruolo `tributi_repositories.py`.
The dirty audit adds 17 cognitive, 19 cyclomatic and 80 LOC relative to clean55a.
Campaign attribution below uses the clean population, while retaining the
official audit numbers explicitly. No October 7 numbers are used.

| Metric | Official concurrent audit | Clean55a | Integrated R2 | Integrated R3 |
|---|---:|---:|---:|---:|
| Files | 1665 | 1662 | 1665 | 1668 |
| Callables | 20261 | 20257 | 20266 | 20280 |
| Errors | 1956 | 1956 | 1943 | 1938 |
| Warnings | 2758 | 2758 | 2749 | 2749 |
| Findings | 4714 | 4714 | 4692 | 4687 |
| Cognitive sum | 81948 | 81931 | 81566 | 81400 |
| Cyclomatic sum | 83685 | 83666 | 83437 | 83377 |
| Effective file LOC, tests included | 332261 | 332181 | 332206 | 332233 |
| Application files, worker tests excluded | 1611 | 1608 | 1611 | 1614 |
| Application callables | 18940 | 18936 | 18945 | 18959 |
| Application effective LOC | 318856 | 318776 | 318801 | 318828 |

Clean55a evidence `/tmp/gaia-campaign-clean-before.json`; R2
`/tmp/gaia-r2-integrated-complexity.json`; official audit
`/tmp/gaia-complexity-complete-2026-10-08.json`. Include/exclude lists are
identical in clean55a, R2 and R3. An additional finding is not automatically
an independent problem; metric overlap remains visible.

## Deltas and anti-laundering

| Metric | R2 → R3 | Clean55a → R3 |
|---|---:|---:|
| Errors | -5 (-0.257%) | -18 (-0.920%) |
| Warnings | 0 | -9 (-0.326%) |
| Findings | -5 (-0.107%) | -27 (-0.573%) |
| Cognitive sum | -166 (-0.204%) | -531 (-0.648%) |
| Cyclomatic sum | -60 (-0.072%) | -289 (-0.345%) |
| Effective file LOC | +27 (+0.008%) | +52 (+0.016%) |

All helpers are included; source totals independently reproduce integration:

| R3 slice | Main cognitive | Aggregate cognitive | Aggregate cyclomatic | Aggregate LOC | New helper findings |
|---|---:|---:|---:|---:|---:|
| Presenze monthly model | 506 → 437 | 1429 → 1332 (-97) | 1442 → 1414 (-28) | 3042 → 3046 (+4) | 0 |
| Settings credential commands | 335 → 296 | 606 → 540 (-66) | 620 → 596 (-24) | 1891 → 1919 (+28) | 0 |
| Fuel vehicle model | 332 → 322 | 991 → 988 (-3) | 604 → 596 (-8) | 1282 → 1277 (-5) | 0 |

All three are `IMPROVED`, not mere relocation. Fuel reduction is specifically
small; moved judgement has zero net benefit and is counted. LOC growth in
frontend models is disclosed. Neither state/effect concentration nor remaining
large callable debt is declared solved. No rejected branch is silently merged.

## Area and domain findings

| Area | Clean error | R2 error | R3 error | Clean warning | R2 warning | R3 warning |
|---|---:|---:|---:|---:|---:|---:|
| Backend | 1035 | 1033 | 1033 | 1688 | 1689 | 1689 |
| Frontend | 878 | 867 | 862 | 881 | 871 | 871 |
| Worker runtime | 35 | 35 | 35 | 134 | 134 | 134 |
| Worker tests | 8 | 8 | 8 | 55 | 55 | 55 |

| Domain | Clean error | R2 error | R3 error | Clean warning | R2 warning | R3 warning |
|---|---:|---:|---:|---:|---:|---:|
| Backend Catasto | 186 | 186 | 186 | 233 | 233 | 233 |
| Backend Ruolo | 117 | 117 | 117 | 230 | 230 | 230 |
| Backend Presenze | 93 | 93 | 93 | 240 | 240 | 240 |
| Backend Wiki | 108 | 106 | 106 | 193 | 195 | 195 |
| Backend legacy Elaborazioni | 120 | 120 | 120 | 156 | 156 | 156 |
| Backend Operazioni | 103 | 103 | 103 | 107 | 106 | 106 |
| Backend Network | 75 | 75 | 75 | 65 | 65 | 65 |
| Frontend Presenze | 87 | 82 | 79 | 121 | 115 | 115 |
| Frontend Elaborazioni | 82 | 79 | 77 | 109 | 104 | 104 |
| Frontend Catasto | 143 | 140 | 140 | 157 | 158 | 158 |

Domain grouping uses backend module paths, legacy elaborazioni service prefix,
and frontend app/components/features domain segments. Complete 46 groups are
in the evidence JSON; unlisted groups are not excluded from global totals.

## Extreme tail and assigned hotspot outcomes

Application callable tail, worker tests excluded:

| Cognitive threshold | Clean55a | R2 | R3 |
|---|---:|---:|---:|
| >300 | 8 | 8 | 7 |
| >200 | 18 | 17 | 17 |
| >100 | 55 | 55 | 55 |

Settings leaves >300; it remains 296. Presenze 550→437 (-20.55%) does not
achieve the initial ≥50% or <250 slice target. Capacitas472, Utenze391 and
CatastoAnomalie390 remain unchanged. Fuel366→322 remains >300; anomalies
365→361 only reflects the approved prior invariant guard prerequisite, not
a substantive anomalies refactor. Campaign targets are still far away.

## Full-file coverage independently inspected

Counters read from integration JSON, not averaged percentages. All **six R3
modified runtime files** have 100% statement/branch counters; unchanged
collaborator selector also verifies 30/30 statements, 22/22 branches.

| Runtime | Statements | Branch outcomes | Functions | Last statement / physical source line |
|---|---:|---:|---:|---:|
| Presenze page | 1093/1093 | 1245/1245 | 301/301 | 3034 / 3036 |
| Monthly insights | 60/60 | 43/43 | 6/6 | 117 / 118 |
| Settings workspace | 455/455 | 556/556 | 118/118 | 1811 / 1813 |
| Settings commands | 24/24 | 26/26 | 7/7 | 95 / 96 |
| Analytics | 664/664 | 302/302 | — | Coverage missing lines/branches empty |
| Fuel vehicle model | 20/20 | 8/8 | — | Coverage missing lines/branches empty |

V8 mapping reaches the runtime tail; remaining physical lines are closing
syntax, not omitted runtime. Physical source counts use `splitlines()`;
integration report's counts are one larger from a trailing-newline convention.
No whole-file ignore or censored tail. JSON paths:
`/tmp/r3-integration-p1-coverage/coverage-final.json`,
`/tmp/r3-integration-p6-coverage/coverage-final.json`,
`/tmp/r3-integration-p3-coverage.json`.
Analytics retains four original defensive excluded lines 369/370/869/870;
handler/pragma text is unchanged. New helper has zero excluded lines.
Runtime diff adds no coverage ignore, pragma, noqa or eslint-disable.
This is not repository-wide 100% or exclusion-free coverage.

## Baseline provenance and protected files

Change ratchet `BASE_REF=main`: **PASS / zero findings / exit0**.
Registered baseline check: **FAIL / 30 findings**; scanner exit1, Make exit2.
All 30 finding objects, including baseline/value/delta/reason/path/symbol,
are **exactly equal in order and multiset** to R2
`/tmp/gaia-r2-integrated-global-check.log`. No affected path belongs to the
campaign diff. Distribution remains backend MCP13, frontend2, worker tests15.
The preexisting provenance report/classifications remain authoritative;
these findings are neither attributed to this campaign nor ignored/repaired.

Independently SHA-256 compared clean55a Git blobs against current disk:
baseline, exceptions, scanner, Babel helper, Makefile, Ruff config, frontend
package/Vitest config, backend coverage config and pytest config are all
**byte-identical**. Full hashes are in the evidence JSON. Key hashes:

- Baseline `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
- Scanner `315bc71fb48521f0049c968c8c4f262bdbb7077ad091c8f5f991b8088dc065af`.
- Babel helper `faf340a36a2a3730d313be34b17a89e1c96c6310084d3b63739e0a3fbf446b8d`.

No threshold inflation, wider exclusions, baseline absorption or tooling edits.

## Tests and execution limits

| Gate | Result | Evidence / provenance |
|---|---|---|
| Independent integrated slice tests | 617 PASS, zero skip | Integration R3: P1 388, P6 131, P3 98, reviewed counters above |
| Complexity/tooling full suite | 169 PASS, 15.54 sec, exit0 | Executed by verifier; `/tmp/gaia-r3-quality-tests.log` |
| Full frontend unit suite | 4099 PASS, 283 files, exit0 | Coordinator executed on frozen R3 UI; inspected `/tmp/gaia-r3-frontend-full-tests.log` |
| Clean frontend build | PASS, exit0 | Coordinator session18097; `/tmp/gaia-r3-frontend-clean-build.log` |
| Worker full suite | 778 PASS, 1 skip, 52 test-file executions, exit0 | Coordinator executed; independently summed `/tmp/gaia-r3-worker-tests2.log` |
| Full backend suite | 6608 PASS,449 skipped,2272 warnings,1554.96s,exit0 | Coordinator session30021 completed, frozen0b1a0d37 unchanged; `/tmp/gaia-r3-backend-full-tests.log` |
| R3 browser/E2E initial full run | FAIL, exit1: 51 PASS / 7 skip / 1 failure | `/tmp/gaia-r3-e2e.{json,log}`; GIS timeout |
| R3 unchanged GIS diagnostic | PASS, exit0: 1 PASS / 0 skip | `/tmp/gaia-r3-gis-diagnostic.{json,log}`; no test/runtime change |
| R3 unchanged full confirmation | PASS, exit0: 52 PASS / 7 skip / 0 failure | `/tmp/gaia-r3-e2e-confirmation.{json,log}`; initial FAIL remains recorded |
| Integration typecheck, smoke, style, per-slice ratchet | PASS; smoke18PASS | Independent integration GREEN report, not duplicated here |
| Integration Graphify frontend/Operazioni | PASS, dedicated targets/query | `/tmp/r3-integration-{frontend,operazioni}-{graphify,query}.log` |
| Platform docs Graphify | PASS, semantic chunk1/1done, no failed-chunk warning | `/tmp/gaia-r3-platform-docs.log`; 282nodes275edges68communities |

Worker first attempt **FAILED** collecting autodoc: missing `JWT_SECRET_KEY`,
before production runtime execution. Retained `/tmp/gaia-r3-worker-tests.log`;
corrected environment rerun passed, not counted as an initially green run.
Worker skip is the PostgreSQL recovery migration parameter in
`test_sister_recovery_migration.py`, because `GAIA_TEST_POSTGRES_URL` is absent.
One no-data-collected coverage shard warning is recorded; combined worker
coverage is not 100%: 6072/6077 statements (99.918%), 1624/1630 branches
(99.632%), 21 existing excluded lines. Worker runtime is unchanged.
Frontend jsdom navigation warnings remain visible. No skip or unavailable
integration dependency is relabelled PASS. Backend PostgreSQL/live scenarios
cannot be certified from SQLite characterization alone.

### Browser evidence and unresolved intermittency

The earlier NOT RUN status is historical. JSON stats inspected independently:
initial full run started 17:27:01UTC, duration89.23sec, expected51/skipped7/
unexpected1/flaky0; diagnostic started17:29:37UTC, duration4.34sec, expected1;
confirmation started17:30:24UTC, duration83.70sec, expected52/skipped7/
unexpected0/flaky0. Playwright's per-run `flaky0` does **not** disprove
intermittency across these separate runs.

Initial failed case `tests/e2e/catasto-gis.spec.ts:365`,
`catasto gis fiscal search opens parcel role details`, could not find visible
`A ruolo` inside the parcel panel after map click within the ten-second
`toPass` budget; a pending popup request then ended with the test. Screenshot
and error-context artifacts remain under `/tmp/gaia-r3-e2e-artifacts/`.
Unchanged targeted and full reruns passed: no test weakening, runtime patch
or timeout inflation was applied to obtain the confirmation. Root cause is
**not demonstrated**; a timing/render/load hypothesis is not treated as proof
of harmlessness or unrelatedness. This initial FAIL is not converted into PASS.

Runs used the matching R3 stack, `PLAYWRIGHT_BASE_URL=http://127.0.0.1:8080`,
serial Chromium `--workers=1`, line/JSON reporters and isolated temporary
Playwright config. Credentials were environment-provided, not copied into
this report. R2 browser results remain historical only.
Seven unverified skipped cases remain: Catasto anagrafica single search,
two Catasto drilldown cases, two GIS territorio/viewport cases, local synthetic
Wiki MCP console and live synthetic Wiki MCP preview. Confirmation does not
certify these skipped dependencies/features. No duplicate backend suite was
started or interrupted; its running log had reached about45% at this cutoff.

Platform docs Graphify used dedicated `make graphify-platform-docs` with
`gpt-reserve`, concurrency1 and timeout180. Log explicitly contains
`chunk 1/1 done`, no failed semantic-chunk warning and 282nodes275edges/
68communities. Success is based on semantic completion, not exit status alone.

## Remaining top 30

Ordered by cognitive descending, application runtime only; paths in the
evidence JSON remove symbol ambiguity. Multiple metrics per callable are not
counted as separate independent problems.

| # | Callable | Domain | Cognitive | Cyclomatic | LOC |
|---|---|---|---:|---:|---:|
| 1 | ElaborazioniCapacitasWorkspace | Frontend Elaborazioni | 472 | 416 | 2631 |
| 2 | PresenzeGiornalierePage | Frontend Presenze | 437 | 385 | 2080 |
| 3 | DetailContent | Frontend Utenze | 391 | 304 | 1908 |
| 4 | CatastoAnomaliePageContent | Frontend Catasto | 390 | 342 | 2109 |
| 5 | anomalies_analytics | Backend Operazioni | 361 | 159 | 387 |
| 6 | fuel_analytics | Backend Operazioni | 322 | 183 | 348 |
| 7 | CatastoGisPage | Frontend Catasto | 317 | 281 | 1889 |
| 8 | ElaborazioniSettingsWorkspace | Frontend Elaborazioni | 296 | 265 | 1358 |
| 9 | MePageContent | Frontend Me | 271 | 256 | 1133 |
| 10 | _run_bonifica_sync_background | Backend legacy Elaborazioni | 269 | 47 | 232 |
| 11 | ElaborazioniBonificaSyncWorkspace | Frontend Elaborazioni | 259 | 202 | 835 |
| 12 | MapContainer | Frontend Catasto GIS | 246 | 169 | 953 |
| 13 | PresenzeCollaboratoreDetailPage | Frontend Presenze | 233 | 212 | 1600 |
| 14 | ElaborazioneBatchDetailWorkspace | Frontend Elaborazioni | 216 | 177 | 751 |
| 15 | PresenzeExportPage | Frontend Presenze | 209 | 172 | 1097 |
| 16 | sync_from_whitecompany | Backend Organigramma | 205 | 77 | 290 |
| 17 | RuoloTributiPageContent | Frontend Ruolo | 204 | 173 | 1064 |
| 18 | run_network_scan | Backend Network | 195 | 101 | 267 |
| 19 | UtenzeSubjectsSection | Frontend Utenze | 184 | 169 | 991 |
| 20 | TrackingContent | Frontend Network | 183 | 159 | 913 |
| 21 | _build_network_statistics_summary | Backend Network | 181 | 101 | 214 |
| 22 | AnagraficaBulkPanel | Frontend Catasto | 181 | 155 | 839 |
| 23 | refresh_wiki_conversation_daily_metrics | Backend Wiki | 178 | 49 | 153 |
| 24 | CatastoImportPage | Frontend Catasto | 175 | 149 | 1114 |
| 25 | ImportContent | Frontend Utenze | 173 | 160 | 971 |
| 26 | RuoloDashboardPage | Frontend Ruolo | 168 | 157 | 1147 |
| 27 | OrganigrammaWorkspace | Frontend Organigramma | 167 | 147 | 1086 |
| 28 | WikiRequestsPage | Frontend Wiki | 166 | 132 | 759 |
| 29 | GaiaUsersPage | Frontend GAIA users | 162 | 146 | 1011 |
| 30 | PresenzeConfigurazionePage | Frontend Presenze | 158 | 148 | 1135 |

## Risks and recommended checkpoint

The strategic extreme-tail goal remains unfinished; unchanged Capacitas,
Catasto anomalies and Utenze detail are still major concentrations. Existing
coverage blockers and concurrent Ruolo ownership are not overridden by a
green local ratchet. Seven application callables still exceed cognitive300.
Count improvements do not guarantee fewer independent engineering problems.

Before another runtime wave, complete the frozen R3 backend suite, retain the
initial browser failure and unresolved intermittent GIS risk despite the fresh
green confirmation, and preserve sequential ownership review. Then authorize one measured responsibility
with full-file coverage, not an indiscriminate module rewrite. No further
runtime work is performed by this verifier; no campaign completion is claimed.
