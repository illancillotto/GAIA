# R87 — Read-only diagnosis of R86 SKIP

## Snapshot and scope

Integration checkout GAIA-campaign-20261008-integration,
branch refactor/complexity-campaign-20261008,
review HEAD3be2709fa219bea99bba3e84b2349d4f9fb33dcc,
main/merge-basea51a48dc4caefbdd1aea82fe4d749054b9465970, BASE_REF=main.
SpecSHA92fae5dc66f7372f0a587c310b1ea05117de8ad2c1233ad83f2f7acd1f2d5dbb
remains partial/uncommitted/NOT_ADMITTED. No source/fixture/private-proxy correction,
native launch, runtime/test/main/DB/baseline/policy change or new refactoring.

## Independently corroborated source findings

1. Frontend district list requests /catasto/distretti without trailing slash,
   through API base whose source default is /api. R86private proxy strips /api
   and routes upstream to backend39083, retaining original Host.
2. FastAPI district route registers slash list, no enclosing /api or root_path;
   installed Starlette slash redirect builds Location from backend scope path.
   Preserved log confirms307. Private proxy passes headers unchanged: a followed
   /catasto/distretti/ goes to frontend39082, not backend. Source-derived mismatch
   versus nginx/server-routes.conf, which restores API prefix on redirects.
3. UI heading is independent of async data/KPI loading. Empty DataTable renders
   no table; original count snapshots rows and skips zero without loading/error/
   completed-empty distinction. Playwright client/server queryCount is not a
   retrying readiness assertion; zero can also reflect retriable query errors.

No actual Location/browser chain captured. Source default API base is not fresh
compiled-build constant proof; repository nginx config is not deployed traffic
verification. Do not infer subsequent Next response/rendering or a guaranteed
PASS after correcting the private proxy.

## Actual cause and terminal classification

R86first identity21:5 ORIGINAL_SKIP, no failed assertions, retry0; second60:5
NOT_RUN. Private failure DB contains active non-FD district/parcel per earlier
sealed limited diagnosis; not reopened here. Logs have no completed list200/KPI
before shutdown. Missing browser/loading/error snapshots prevent identifying
which coexisting mechanism governed zero rows. Actual SKIP cause remains unproven.

Secondary driver drain rejects already-terminal namespace exit1; it masks primary
SKIP at the top level but kernel receipts still prove empty/removal. BackendPID53
allowed-15 is not proxyPID55 and not the failing parent status. No automatic fix
to strict admission, driver status, readiness, API path or timeout inferred.

## Evidence and coverage

Independent SOURCE_DIAGNOSIS_CORROBORATED / ACTUAL_R86_SKIP_CAUSE_UNPROVEN,
175/175source/AST/hash/Git/evidence checks, no reviewer checker error; not175app
tests.16frozen diagnosis records and83native-terminal checksum entries match.
Additional route-wiring/dependency source inspected without operational imports.
Reviewer stopped;32review-file seal verified by Coordinator. Coverage not measured;
complexity metrics/runtime unchanged. No new ratchet/check/full-suite execution,
last actual-mainPASS0 remains historical R85 on unchanged runtime.

External root:
/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r86-native-parent-binding/.
- SOURCE_DIAGNOSIS_20261014.mdSHA3e283215ec1be9317c4b32bcf3fc2557f9ca3afc563756f2f91b7c6439d7ed13.
- source-diagnosis-20261014/MANIFEST.json and SHA256SUMS bind16frozen inputs.
- source-diagnosis-review/INDEPENDENT_DIAGNOSIS_REVIEW.mdSHA
  fe0cef625254fa17f064367fa0a6de2c47109f8bf5b904a872c5fd49917ba7ff.
- source-diagnosis-review/REVIEW_SHA256SUMSSHA
  3a8ce72d1a80d8be2e6fdc81fef78fe556c8727e36f2681404d518ba825b8c7d.
- Mutable docs frozen in source-diagnosis-review-handoff/pre-publication-docs/.

## Next decision and stop

Pending question: authorize new source-only private proxy correction preparation
and review, with explicit positive/negative redirect cases, no E2E launch. Original
proxy/run must remain immutable. Same-origin API restoration must not rewrite
unrelated origins/non-API frontend redirects. Readiness adaptation and driver
provenance cleanup remain separate decisions. Native once-only authorization is
exhausted; any future execution needs new identity/review/pins/gates/decision.
No global completion or refactor admission; preserve full campaign objective.
