# GAIA — Final Verification, 2026-10-08

## Certification status

**PROVISIONAL — final complete backend suite still running.**

The campaign change has a passing differential complexity gate and independently
verified full-file coverage for each changed runtime. No complete campaign or
all-suite-green certification is issued until the corrected backend run ends.
Skipped PostgreSQL/provider/data scenarios remain explicitly unverified.

## Snapshot and provenance

- Initial main / authoritative merge-base:
  `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Frozen integrated runtime / scanner source commit:
  `897dddeadbd93aa3dc849c14cefa491c68e4315a`.
- Verification worktree:
  `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`.
- Before scanner JSON: `/tmp/gaia-campaign-clean-before.json`.
- Final scanner JSON/Markdown:
  `/tmp/gaia-complexity-final.json`, `/tmp/gaia-complexity-final.md`.
- Parser/exception errors: **zero / zero**.

The user audit has 1665 files / 20261 callables and includes concurrent local
work. The committed clean initial checkout has 1662 files / 20257 callables.
Campaign deltas below compare the same committed scope, never attribute those
three concurrent files to campaign removals, and never use October 7 figures.

## Global metrics

| Official scanner scope, including worker tests | Clean before | Final | Delta | Delta % |
|---|---:|---:|---:|---:|
| Files | 1662 | 1662 | 0 | 0.00% |
| Callables | 20257 | 20261 | +4 | +0.02% |
| Error findings | 1956 | 1947 | -9 | -0.46% |
| Warning findings | 2758 | 2750 | -8 | -0.29% |
| All findings | 4714 | 4697 | -17 | -0.36% |
| Cognitive sum | 81931 | 81714 | -217 | -0.26% |
| Cyclomatic sum | 83666 | 83541 | -125 | -0.15% |
| Effective file LOC sum | 332181 | 332143 | -38 | -0.01% |
| Callable LOC sum | 328259 | 327960 | -299 | -0.09% |
| Nesting sum | 10600 | 10602 | +2 | +0.02% |
| Parameter count sum | 28724 | 28730 | +6 | +0.02% |

Callable LOC can overlap for nested callables; -299 is not 299 source lines
deleted. Aggregate nesting/parameters increase because small new helpers exist;
the unchanged threshold ratchet reports no new violation or legacy regression.
Findings are metric signals, not independent defects.

| Application scope excluding worker tests | Clean before | Final | Delta |
|---|---:|---:|---:|
| Files | 1608 | 1608 | 0 |
| Callables | 18936 | 18940 | +4 |
| Effective LOC | 318776 | 318738 | -38 |
| Error / warning | 1948 / 2703 | 1939 / 2695 | -9 / -8 |
| Findings | 4651 | 4634 | -17 |
| Callables cognitive >300 | 8 | 8 | 0 |
| Callables cognitive >200 | 18 | 17 | -1 |
| Callables cognitive >100 | 55 | 55 | 0 |

The extreme tail is still substantial; this is a bounded safe improvement,
not the strategic tail-reduction target being fully achieved.

## Domain findings

| Domain / exact corpus prefix | Error before | Error after | Warning before | Warning after |
|---|---:|---:|---:|---:|
| Backend overall | 1035 | 1033 | 1688 | 1690 |
| Frontend overall | 878 | 871 | 881 | 871 |
| Worker runtime | 35 | 35 | 134 | 134 |
| Catasto backend | 186 | 186 | 233 | 233 |
| Ruolo backend | 117 | 117 | 230 | 230 |
| Presenze backend | 93 | 93 | 240 | 240 |
| Wiki backend | 108 | 106 | 193 | 195 |
| Legacy elaborazioni services | 120 | 120 | 156 | 156 |
| Operazioni backend | 103 | 103 | 107 | 107 |
| Network backend | 75 | 75 | 65 | 65 |
| Frontend app/presenze | 78 | 74 | 101 | 96 |
| Frontend components/elaborazioni | 82 | 79 | 108 | 103 |
| Frontend app/utenze | 31 | 31 | 15 | 15 |
| Frontend app/catasto | 60 | 60 | 56 | 56 |

Subset rows overlap overall totals. Backend warning +2 is the Wiki ranking
moving from error to warning thresholds; total Wiki findings remains 301.
Network finding counts remain 12 despite measured aggregate improvement.

## Modified runtime and debt transfer check

| File / callable | Cognitive before | After | File cognitive sum before→after | File cyclomatic sum before→after |
|---|---:|---:|---:|---:|
| Presenze page / principal | 550 | 525 | 1530→1472 | 1526→1470 |
| Settings workspace / principal | 402 | 366 | 718→621 | 689→634 |
| Network traffic / statistics summary | 209 | 181 | 322→297 | 181→176 |
| Wiki conversation metrics / refresh | 188 | 178 | 312→275 | 145→136 |

All four modified runtime files improve aggregate cognitive/cyclomatic metrics.
No debt was moved to unmeasured files. The complete Git runtime diff has only
these four paths; no domain relocation, new service, shared manager or baseline
change exists. Review/integration evidence is in `INTEGRATION_CHECKPOINT_2026-10-08.md`.
Presenze's initial -50% / below-250 target remains unmet (525).

## Runtime coverage certification

| Runtime | Statements | Branch outcomes | Functions | Evidence |
|---|---:|---:|---:|---|
| Presenze giornaliere page | 1186/1186 | 1336/1336 | 310/310 | `/tmp/p1-presenze-after-v2-coverage/coverage-final.json` |
| Elaborazioni settings workspace | 477/477 | 658/658 | 127/127 | `/tmp/p6-settings-after-coverage/coverage-final.json` |
| Network traffic helper | 276/276 | 92/92 | — | `/tmp/gaia-integration-b4-coverage.json` |
| Wiki conversation metrics | 265/265 | 102/102 | — | `/tmp/gaia-integration-b5-coverage.json` |

Counts were independently read from JSON; **100% full-file**, not differential
coverage. Frontend integration files match validated candidate bytes exactly.
Backend integration coverage was rerun after cherry-pick. No new exclusion or
ignore was added; backend modified files have zero excluded statements.
Coverage is behavioral characterization under mocked boundaries/SQLite, not
a guarantee of live provider or PostgreSQL concurrency semantics.

## Suite evidence

| Suite / command | Result | Artifact / qualification |
|---|---|---|
| Complete frontend `npm run test:unit -- --maxWorkers=2` | PASS: 4056 tests / 281 files | `/tmp/gaia-campaign-frontend-final-tests.log` |
| Frontend `npm run build:clean` | PASS | `/tmp/gaia-campaign-frontend-final-build.log` |
| Frontend smoke | PASS: 18 | `/tmp/gaia-campaign-frontend-smoke.log` |
| Complexity tooling `make quality-test` | PASS: 169 | `/tmp/gaia-campaign-quality-final-tests.log` |
| Worker `make test-worker`, corrected environment/root PYTHONPATH | PASS: 778; skip 1; 52 test files | `/tmp/gaia-campaign-worker-final-tests3.log` |
| Full E2E, serial disposable stack | PASS: 52; skip 7 | `/tmp/gaia-campaign-e2e-final-serial.log`, `.json` |
| Full backend on initial clean source, root cwd | FAIL: 1; PASS 6497; skip 449 | `/tmp/gaia-campaign-backend-base-tests.log`; environment invocation failure |
| Failing backend module, correct backend cwd | PASS: 26 | `/tmp/gaia-campaign-backend-small-rerun.log` |
| Complete backend on final frozen source, correct backend cwd | RUNNING; not PASS | `/tmp/gaia-campaign-backend-final-corrected2-tests.log` |

The frontend/build/E2E runs precede only the subsequently integrated backend
metrics slices; no frontend runtime change follows these runs. Network and Wiki
backend integration additionally reran their relevant route/service tests.
Complete final backend is running against the frozen integrated source.

### Failures retained, not hidden

- Original full backend failure:
  `test_database_sqlite_engine_options_in_subprocess`, `ModuleNotFoundError: app`.
  The root-cwd test subprocess lacks the backend import path. It happened on
  the initial clean source; the unchanged module passes 26 cases from backend
  cwd. The original complete invocation is still **FAIL**, not relabeled PASS.
- A premature corrected full-backend attempt was stopped by SIGTERM before
  final source collection; it is **INTERRUPTED**, not PASS. The second corrected
  run is the authoritative final suite.
- Worker attempt 1: missing required test DATABASE_URL/JWT settings caused
  collection failure. Attempt 2: root absent from PYTHONPATH caused
  `scripts.sister_autosync_efficiency` import failure. Both logs are retained.
  The corrected third attempt finishes exit 0.
- E2E complete attempt 1: 51 PASS / 7 skip / 1 login navigation timeout in
  Catasto Distretti. Unchanged isolated Distretti file: 2 PASS in 3.7s.
- E2E complete attempt 2: 51 PASS / 7 skip / 1 missing shift-editor control
  after reload in Presenze operational controls. Unchanged isolated file:
  3 PASS in 6.4s. Complete serial rerun: 52 PASS / 7 skip, exit 0.
  These demonstrate sensitivity to concurrent execution; the failing attempts
  remain evidence. Neither timeout nor test assertion was weakened.

### Skips and coverage limitations

- Backend initial complete suite: 449 skipped; no blanket claim these are
  PostgreSQL-only or verified. Final corrected suite's skip count is pending.
- Worker: 1 PostgreSQL recovery migration test skipped because
  `GAIA_TEST_POSTGRES_URL` is absent. Coverage's `Combined 51 files, skipped 1`
  describes coverage data files and is distinct from that test skip.
- E2E 7 skips: obsolete single Catasto search (1), absent imported distretto
  data for drilldown (2), optional GIS opt-in disabled (2), live synthetic MCP
  gateway/provider opt-ins absent (2). No campaign skip was introduced.
- Whole worker runtime coverage: statements 6072/6077 (99.9177%), branches
  1624/1630 (99.6319%), combined 99.8573%; 21 existing excluded lines.
  Missing paths remain in `sister_credential_pool.py` and
  `sister_retry_metadata.py`. Worker runtime is unchanged by this campaign;
  this is not 100% repository coverage.
- Test-only prerequisite slices P2/P3/P4/P5 remain runtime-blocked on coverage;
  their tests passing does not authorize their production refactors.

## Complexity gates and protected files

Final report: PASS, no parse/config exception errors.
Final `make complexity-ratchet BASE_REF=main`: **PASS, zero findings**.
`make complexity-check`: **FAIL, exactly 30 historical findings** (13 backend
MCP, 2 frontend, 15 worker tests). None is on any modified campaign runtime
path. CLI reports failure code 1, and the Make command consequently exits 2.
The findings retain their pre-campaign values and paths; no baseline repair
was used to make this separate global status green.
Logs: `/tmp/gaia-campaign-final-{complexity-report,ratchet,check}.log`.

`git diff 55a1b1d3 HEAD` is empty for `config/code-quality/`,
`tools/code_quality/`, `Makefile`, `frontend/vitest.config.ts`, package/config
files inspected and complexity skill tooling. Baseline SHA-256 is unchanged:
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
No baseline generation/repair, threshold change, ignore or exclusion occurred.
Global historical divergence provenance remains a separate problem:
`BASELINE_PROVENANCE_2026-10-08.md` identifies 15 runtime REAL_REGRESSION and
15 TEST_ONLY_DIVERGENCE findings predating the campaign.

Backend changed-file Ruff/style/format gate PASS for five files:
`/tmp/gaia-campaign-backend-final-lint.log`. Runtime preservation check against
the frozen source is clean. Graphify code refreshed through the dedicated
frontend, Network and Wiki Make targets; graph output is not committed and
is not treated as a complexity metric.

## Remaining top 30 cognitive hotspots

| # | Callable | Cognitive | Cyclomatic | Callable LOC | Path |
|---|---|---:|---:|---:|---|
| 1 | PresenzeGiornalierePage | 525 | 432 | 2194 | `frontend/src/app/presenze/giornaliere/page.tsx` |
| 2 | ElaborazioniCapacitasWorkspace | 472 | 416 | 2631 | `frontend/src/components/elaborazioni/capacitas-workspace.tsx` |
| 3 | DetailContent | 391 | 304 | 1908 | `frontend/src/app/utenze/[id]/page.tsx` |
| 4 | CatastoAnomaliePageContent | 390 | 342 | 2109 | `frontend/src/app/catasto/anomalie/page.tsx` |
| 5 | ElaborazioniSettingsWorkspace | 366 | 316 | 1527 | `frontend/src/components/elaborazioni/settings-workspace.tsx` |
| 6 | fuel_analytics | 366 | 208 | 402 | `backend/app/modules/operazioni/routes/analytics.py` |
| 7 | anomalies_analytics | 365 | 160 | 388 | `backend/app/modules/operazioni/routes/analytics.py` |
| 8 | CatastoGisPage | 334 | 298 | 1896 | `frontend/src/app/catasto/gis/page.tsx` |
| 9 | MePageContent | 271 | 256 | 1133 | `frontend/src/app/me/me-page-content.tsx` |
| 10 | _run_bonifica_sync_background | 269 | 47 | 232 | `backend/app/services/elaborazioni_bonifica_sync.py` |
| 11 | ElaborazioniBonificaSyncWorkspace | 259 | 202 | 835 | `frontend/src/components/elaborazioni/bonifica-sync-workspace.tsx` |
| 12 | MapContainer | 246 | 169 | 953 | `frontend/src/components/catasto/gis/MapContainer.tsx` |
| 13 | PresenzeCollaboratoreDetailPage | 233 | 212 | 1600 | `frontend/src/app/presenze/collaboratori/[id]/page.tsx` |
| 14 | ElaborazioneBatchDetailWorkspace | 216 | 177 | 751 | `frontend/src/components/elaborazioni/batch-detail-workspace.tsx` |
| 15 | PresenzeExportPage | 209 | 172 | 1097 | `frontend/src/app/presenze/export/page.tsx` |
| 16 | sync_from_whitecompany | 205 | 77 | 290 | `backend/app/modules/organigramma/services/whitecompany_sync.py` |
| 17 | RuoloTributiPageContent | 204 | 173 | 1064 | `frontend/src/app/ruolo/tributi/page.tsx` |
| 18 | run_network_scan | 195 | 101 | 267 | `backend/app/modules/network/services.py` |
| 19 | UtenzeSubjectsSection | 184 | 169 | 991 | `frontend/src/components/utenze/utenze-subjects-section.tsx` |
| 20 | TrackingContent | 183 | 159 | 913 | `frontend/src/app/network/tracking/page.tsx` |
| 21 | AnagraficaBulkPanel | 181 | 155 | 839 | `frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx` |
| 22 | _build_network_statistics_summary | 181 | 101 | 214 | `backend/app/modules/network/router/helpers/traffic.py` |
| 23 | refresh_wiki_conversation_daily_metrics | 178 | 49 | 153 | `backend/app/modules/wiki/services/conversation_metrics.py` |
| 24 | CatastoImportPage | 175 | 149 | 1114 | `frontend/src/app/catasto/import/page.tsx` |
| 25 | ImportContent | 173 | 160 | 971 | `frontend/src/app/utenze/import/page.tsx` |
| 26 | RuoloDashboardPage | 168 | 157 | 1147 | `frontend/src/app/ruolo/page.tsx` |
| 27 | OrganigrammaWorkspace | 167 | 147 | 1086 | `frontend/src/features/organigramma/organigramma-workspace.tsx` |
| 28 | WikiRequestsPage | 166 | 132 | 759 | `frontend/src/features/wiki/WikiRequestsPage.tsx` |
| 29 | GaiaUsersPage | 162 | 146 | 1011 | `frontend/src/app/gaia/users/page.tsx` |
| 30 | PresenzeConfigurazionePage | 158 | 148 | 1135 | `frontend/src/app/presenze/configurazione/page.tsx` |

## Verification decision

Differential safety and compliant modified-runtime coverage are demonstrated.
The remaining complete final backend run must be awaited before final suite
certification. Historical global complexity divergence remains separate from
the campaign gate. No further runtime wave is authorized by this verification
report, and uncharacterized hotspots remain blocked rather than merged.
