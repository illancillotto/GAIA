# R92 — KPI selector preparation and review ownership

User «autorizzo» answers the bounded request to prepare/review only the KPI
selector correction after R91 FAIL. No new E2E, service activation, driver repair,
runtime modification, fixture change, commit, push or merge on main.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Coordinator | Catasto test-only preparation | frontend/tests/e2e/catasto-drilldown.spec.ts; frontend/tests/unit/catasto-drilldown-kpi-selectors.test.ts; this registry; R92 report; PROGRESS; external r92-kpi-selectors excluding review/ | Four KPI selectors prepared; 46 focused unit tests and targeted typecheck PASS; independent source acceptance, no native admission | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | READY_FOR_REVIEW |
| r78_mvt_review | Independent bounded source review | Exclusive external r92-kpi-selectors/review/; checkout and other evidence read-only | Source preparation accepted, 258 inspection checks, 10-file seal; reviewer stopped; whole candidate NOT_ADMITTED | Shared read-only checkout | No new branch | READY_FOR_REVIEW |

HEAD `7f39510ab1ef1d4e531d8b12a4eb6b36f556cee4`, main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`; BASE_REF=main unchanged.
Ownership recorded before reviewer dispatch. R91 agents are stopped; native
grant consumed. Historical registries/seals and failure DB remain immutable.
Current spec/helper/readiness test/PROGRESS frozen before edits under external
`r92-kpi-selectors/before/`. Entire accumulated candidate remains NOT_ADMITTED
until the required native verification; no claim that DOM/static checks are E2E.

Review completed and stopped; no source edits after accepted snapshot. Report
`review/INDEPENDENT_REVIEW.md` and seal verified by Coordinator. Reviewer reported
one ancillary seal-verification log accidentally written to /tmp; preserved in
external reviewer-ancillary/ and documented, not hidden as exact ownership.
Graphify docs refreshed; no runtime graph update needed for test-only selectors.
