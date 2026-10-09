# R14 Operazioni — certified integration checkpoint

## Snapshot and ownership

Campaign ACTIVE / INCOMPLETE. Official initial snapshot is main/merge-base
55a1b1d35911451e018b662c2acc450bf5994ea2, audit8October1665files/20261callables/
1956error/2758warning/4714findings. No7October operational baseline.

Dedicated integration branch refactor/complexity-campaign-20261008; concurrent
main untouched (binarydiff9f85e574/status0d54d4eb). Ownership registries govern
R14 author, independent reviewer, distinct final verifier and Coordinator;
exclusive worktrees, no overlap. R15 ended independently reviewed NO_CHANGE.
R16 is a new credential-default responsibility, original characterization only.

## Actual reduction and behavioral invariants

Only nested fuel_analytics._op_km changes. Guard clauses reduce cognitive54→33
(-38.89%), cyclomatic24→22, nesting4→2. EffectiveLOC20 and completefile1255
unchanged; no helper relocation or new callable. Outerfuel282→261cognitive,
169→167cyclomatic,350LOC unchanged. All29non-target actual named functions and
whole module AST excluding only _op_km remain exact.

Unique weighted decisions23→21: TWO genuine removals, not four from inclusive
nested/enclosing scanner sums. Fullscanner cognitive880→838 versus inclusive
all31actual883→841 explicitly double-counts this subtree. Existing28scanner
versus31recursive named-function limitation unchanged, no tooling repair.
One nesting warning removed, no cognitive/cyclomatic error eliminated.

UUID/link/legacy/sentinel/name precedence, zero/negative/NaN, exact case and
whitespace, eager variants, positive short circuit, copies, conversion/errors,
five SELECT SQL/binds/order, full response and no writes remain characterized.
Actual ORM truthiness independently checked. No identity reconciliation,
authorization/date/ranking/normalization/query/transaction/response change.

## Independent verification and coverage

Original author56focused/204union and independent original replay204PASS;
source author204PASS, independent runtime review204PASS, DISTINCT final
prospective complete-current-campaign replay204PASS0skip142.489s. Final analytics
661statements288branches100%, helper27statements10branches100%; no new coverage
marker/exclusion/ignore, four historical excluded lines retained. Supplementary
live-AST tests use synthetic filename and cannot inflate runtime coverage.
Real ORM cases assert complete response, five exact SELECTs and no mutation.

Final Ruff/format/style13files and immutable55a actual Make ratchet PASS0.
Detailed raw JUnit/coverage/process/source inventory:
VERIFICATION_R14_OPERAZIONI_OPERATOR_KM_2026-10-09.md, frozen b77100ee.
All3532protected paths exact;13recorded gate processes terminal, no server/
browser/Docker/provider resources created. SQLite does not certify PostgreSQL.

No fresh global backend/worker/frontend/build/E2E/provider suite in this bounded
backend certificate. Earlier R13 frontend/E2E and GIS test-fix certificates are
attributed, not rerun or represented as fresh R14 results. Final global suites
remain required before global completion; optional provider skips are not PASS.

## Sequential integration

| Publication | Integrated commit | Gate |
| --- | --- | --- |
| Original spec/CHAR d7cc251c | ad8e3939 | immutable55a ratchet PASS0 |
| Original independent review cf4f36dd | f645ee06 | immutable55a ratchet PASS0 |
| Source/SLICE 3881427a | 8799e1af | immutable55a ratchet PASS0 |
| Runtime independent review b128e396 | e7566896 | immutable55a ratchet PASS0 |
| Distinct final certificate c59cf85a | 28a12572 | immutable55a ratchet PASS0 |
| R15 NO_CHANGE readiness 995e3778 | bebbcad1 | immutable55a ratchet PASS0 |
| R15 independent rejection review c7bfb36b | b748c06a | immutable55a ratchet PASS0 |

ONE publication at a time, actual gate after EACH. No main merge, reset, stash,
baseline inflation, threshold/exclusion/ignore or package/tooling change.

## Root independently reproduced accounting

Root fresh Make report and actual globalcheck after all seven imports, external
audit compares EVERY complete file/callable/violation/scope/engine/summary object
with the distinct prospective final certificate: exact. All30complete globalcheck
finding objects exact certificate/R13 historical provenance, not aggregate-only.
All seven raw gate JSON findings empty; source, seven specs, helper, Capacitas and
baseline bytes exact prospective certificate. Main concurrent hashes unchanged.

| Metric | Official initial8October | Integrated R14 | Delta | Delta percent |
| --- | ---: | ---: | ---: | ---: |
| Files |1665 |1672 |+7 |+0.42% |
| Callables |20261 |20316 |+55 |+0.27% |
| Error |1956 |1926 |-30 |-1.53% |
| Warning |2758 |2740 |-18 |-0.65% |
| Findings |4714 |4666 |-48 |-1.02% |

Application excluding worker tests1618files/18995callables/318970effectiveLOC/
4603findings. Current R14-local change removes ONE warning relative to R13;
global campaign deltas include previously certified slices and are not all R14.
Findings overlap;48fewer findings does NOT mean48independent defects.

complexity-ratchet PASS0 is the change gate. Global complexity-check FAIL30
(Make2/scanner1) remains a separate unchanged provenance issue. Baseline SHA256
38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95 exact.
No baseline generation/repair/verify or regression absorption performed.

Root evidence: ~/.cache/gaia-campaign/20261009-r14-coordinator/, including
integration-*-ratchet.log/.exit, integrated-complexity.json/md,
integrated-global-check.log/.exit, integrated-audit.json and audit_integrated.py.
Collector terminal PASS; no new gate failure or waiver. Earlier author/reviewer
fixture/Babel/private-harness failures remain preserved in their reports.

## R15 and R16

R15: bounded independently reviewed NO_CHANGE. Direct/async/error-only exterior
designs increase LOC; async wrapper changes busy release in36of41supplementary
traces. Stubbed reload/builder and serialized reference limits explicit. No
implemented slice, runtime coverage/gate claim, impossibility proof or reduction.

R16 static design/review07d9/b43c accepted ONLY for separate characterization.
Candidate34af projects principal347→339, combined861→839cognitive,
752→730decisions,3126→3120LOC;118pure contracts,243unallocated profiles exact.
These are projections, NOT actual IMPROVED. Source8111/all21specs unchanged.
New original task01a12214 owns ONLY new R16 public-UI unit spec and CHAR report,
static drafting until explicit postcommit-green heavy transfer. Independent
original replay, full-context gates and runtime review/final still required.

## Graphify and closure

Author code graph528nodes1522edges26communities is attributed. Coordinator
fresh dedicated graphs are terminal PASS: Operazioni-code530nodes1524edges/
26communities, Operazioni-docs39nodes52edges8communities, platform-docs610nodes/
821edges95communities. Both docs logs contain chunk1/1done and no failed semantic
chunk warning. Reported estimates: domain926input/2267outputtokens/$0.0040,
platform12101input/2528outputtokens/$0.0089; code AST has no LLM cost. Estimates
are not provider billing. Final postcommit ratchet has a separate root cache log;
its terminal result must be checked before reporting closure. Graphify is not complexity proof,
graphs remain ignored/uncommitted. No stale-symbol/source relocation occurred.

## Risks and recommended continuation

Extreme tail remains5>300/17>200/55>100, strategic target NOT achieved.
Finish R16 original characterization/replay before ANY source implementation.
Continue prioritized safe extreme-tail slices under exclusive ownership and
full-file100%, then fresh full final suites. Historical30provenance and provider/
PostGIS gaps remain visible, not waived. Global objective ACTIVE / INCOMPLETE.

## Detailed current domains and remaining top30

Before columns below are immediate R13 certificate, not official8October.
# R14 fresh global accounting

Path-based accounting, not semantic responsibility proof. backend/app/modules domain; backend elaborazioni legacy services separate; frontend app/features/components first domain folder consolidated, remaining shared layers separate; worker tests separately visible.

## All domains

|Domain|Files|Callables|LOC|Error before|Error after|Warning before|Warning after|Max cognitive|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|backend/__init__.py|2|0|2|0|0|0|0|0|
|backend/accessi|19|111|1955|3|3|18|18|28|
|backend/api|13|13|193|0|0|0|0|5|
|backend/catasto|74|784|21948|186|186|233|233|146|
|backend/core|12|15|1053|0|0|1|1|4|
|backend/db|2|0|387|0|0|0|0|0|
|backend/dotazioni|8|38|734|0|0|9|9|20|
|backend/elaborazioni|78|522|10149|50|50|96|96|101|
|backend/gis|45|391|8266|16|16|71|71|27|
|backend/inventory|5|4|185|1|1|0|0|9|
|backend/jobs|2|3|114|1|1|4|4|20|
|backend/legacy-elaborazioni-services|22|456|9823|120|120|156|156|269|
|backend/main.py|1|5|102|0|0|0|0|9|
|backend/me|10|37|1339|8|8|12|12|38|
|backend/models|23|6|2623|1|1|1|1|5|
|backend/network|34|240|7078|75|75|65|65|195|
|backend/operazioni|51|309|11502|103|103|106|105|298|
|backend/organigramma|31|141|3452|21|21|24|24|205|
|backend/other-services|28|225|4354|24|24|48|48|51|
|backend/platform_scheduler_runner.py|1|3|71|0|0|0|0|1|
|backend/presenze|105|872|19383|93|93|240|240|87|
|backend/repositories|5|36|327|0|0|2|2|12|
|backend/riordino|71|192|4852|34|34|51|51|47|
|backend/ruolo|82|783|18934|117|117|230|230|95|
|backend/schemas|13|14|2358|3|3|1|1|29|
|backend/scripts|14|59|1119|2|2|13|13|23|
|backend/search|4|13|414|4|4|1|1|28|
|backend/shared|3|10|157|0|0|1|1|9|
|backend/utenze|36|334|9095|65|65|111|111|67|
|backend/utils|1|0|1|0|0|0|0|0|
|backend/wiki|124|678|18044|106|106|195|195|178|
|backend/worker_health.py|1|11|147|0|0|0|0|10|
|frontend/accessi|1|4|31|0|0|0|0|1|
|frontend/anagrafica|6|49|588|6|6|2|2|56|
|frontend/app|4|64|924|8|8|7|7|53|
|frontend/auth|5|48|623|5|5|4|4|17|
|frontend/catasto|107|1924|23260|140|140|158|158|390|
|frontend/dotazioni|15|89|430|0|0|4|4|12|
|frontend/elaborazioni|62|1290|14194|70|70|100|100|347|
|frontend/gaia|6|362|4134|37|37|34|34|162|
|frontend/gis|25|451|5746|9|9|22|22|95|
|frontend/inventory|2|5|154|0|0|0|0|4|
|frontend/layout|12|84|1421|4|4|7|7|49|
|frontend/login|1|15|306|3|3|0|0|26|
|frontend/mcp|1|1|7|0|0|0|0|0|
|frontend/me|8|202|2020|15|15|12|12|271|
|frontend/nas-control|11|204|2213|20|20|12|12|56|
|frontend/network|18|611|7688|61|61|35|35|183|
|frontend/operazioni|36|1017|12196|115|115|70|70|144|
|frontend/organigramma|18|449|4780|32|32|39|39|167|
|frontend/presenze|49|1423|14147|74|74|111|111|385|
|frontend/riordino|24|324|3129|26|26|7|7|60|
|frontend/ruolo|61|995|12339|70|70|74|74|204|
|frontend/search|2|68|702|6|6|4|4|53|
|frontend/security|1|3|72|0|0|0|0|3|
|frontend/shared-app|3|30|840|7|7|5|5|99|
|frontend/shared-hooks|3|14|135|0|0|2|2|12|
|frontend/shared-lib|77|1092|11436|7|7|37|37|35|
|frontend/shared-types|28|0|8547|2|2|5|5|0|
|frontend/table|3|10|177|1|1|1|1|13|
|frontend/ui|11|37|425|0|0|0|0|6|
|frontend/utenze|19|587|7829|64|64|48|48|391|
|frontend/wiki|41|662|9245|68|68|63|63|166|
|worker runtime|38|576|9071|35|35|134|134|122|
|worker tests|54|1321|13405|8|8|55|55|17|

## Remaining top30

|Callable|Path|Cognitive|Cyclomatic|LOC|Nesting|Params|
|---|---|---:|---:|---:|---:|---:|
|DetailContent|frontend/src/app/utenze/[id]/page.tsx|391|304|1908|2|1|
|CatastoAnomaliePageContent|frontend/src/app/catasto/anomalie/page.tsx|390|342|2109|2|0|
|PresenzeGiornalierePage|frontend/src/app/presenze/giornaliere/page.tsx|385|341|2023|2|0|
|ElaborazioniCapacitasWorkspace|frontend/src/components/elaborazioni/capacitas-workspace.tsx|347|324|2455|2|1|
|CatastoGisPage|frontend/src/app/catasto/gis/page.tsx|317|281|1889|4|0|
|anomalies_analytics|backend/app/modules/operazioni/routes/analytics.py|298|137|372|4|5|
|ElaborazioniSettingsWorkspace|frontend/src/components/elaborazioni/settings-workspace.tsx|296|265|1358|2|1|
|MePageContent|frontend/src/app/me/me-page-content.tsx|271|256|1133|2|1|
|_run_bonifica_sync_background|backend/app/services/elaborazioni_bonifica_sync.py|269|47|232|13|3|
|fuel_analytics|backend/app/modules/operazioni/routes/analytics.py|261|167|350|4|5|
|ElaborazioniBonificaSyncWorkspace|frontend/src/components/elaborazioni/bonifica-sync-workspace.tsx|259|202|835|4|1|
|MapContainer|frontend/src/components/catasto/gis/MapContainer.tsx|246|169|953|3|1|
|PresenzeCollaboratoreDetailPage|frontend/src/app/presenze/collaboratori/[id]/page.tsx|233|212|1600|2|0|
|ElaborazioneBatchDetailWorkspace|frontend/src/components/elaborazioni/batch-detail-workspace.tsx|216|177|751|3|1|
|PresenzeExportPage|frontend/src/app/presenze/export/page.tsx|209|172|1097|3|0|
|sync_from_whitecompany|backend/app/modules/organigramma/services/whitecompany_sync.py|205|77|290|6|2|
|RuoloTributiPageContent|frontend/src/app/ruolo/tributi/page.tsx|204|173|1064|3|0|
|run_network_scan|backend/app/modules/network/services.py|195|101|267|3|5|
|UtenzeSubjectsSection|frontend/src/components/utenze/utenze-subjects-section.tsx|184|169|991|3|1|
|TrackingContent|frontend/src/app/network/tracking/page.tsx|183|159|913|2|1|
|AnagraficaBulkPanel|frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx|181|155|839|2|0|
|_build_network_statistics_summary|backend/app/modules/network/router/helpers/traffic.py|181|101|214|4|2|
|refresh_wiki_conversation_daily_metrics|backend/app/modules/wiki/services/conversation_metrics.py|178|49|153|6|3|
|CatastoImportPage|frontend/src/app/catasto/import/page.tsx|175|149|1114|3|0|
|ImportContent|frontend/src/app/utenze/import/page.tsx|173|160|971|1|1|
|RuoloDashboardPage|frontend/src/app/ruolo/page.tsx|168|157|1147|1|0|
|OrganigrammaWorkspace|frontend/src/features/organigramma/organigramma-workspace.tsx|167|147|1086|2|1|
|WikiRequestsPage|frontend/src/features/wiki/WikiRequestsPage.tsx|166|132|759|3|1|
|GaiaUsersPage|frontend/src/app/gaia/users/page.tsx|162|146|1011|2|0|
|PresenzeConfigurazionePage|frontend/src/app/presenze/configurazione/page.tsx|158|148|1135|1|0|
