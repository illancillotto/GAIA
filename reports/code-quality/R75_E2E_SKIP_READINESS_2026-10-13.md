# R75 — seven E2E skips, exact prerequisites and current readiness

## Snapshot and user decisions

Analysis of original tests, not new test or runtime development. Dedicated
branch refactor/complexity-campaign-20261008, initial15b1defc; actual main/base
a51a48dc, historical55a1b1d not gate substitute. User prioritizes7E2Eskips before
other PostgreSQL executions and authorizes one future targeted runtime slice
**after verification phase**. R74 preparation independently accepted, native
52cases queued/NOT_RUN. Main concurrent config/Bonifica and historical receipts
preserved. No Wiki live-provider invocation, browser, DB, stack startup, seed or
device cleanup during this analysis. Graphify documentation maintenance is separate.

## Seven original cases

| Case | Original skip | Exact missing prerequisite / disposition |
| --- | --- | --- |
| Catasto single anagrafica search | Unconditional; removed feature | Empty test body/no assertions. Cannot turn into PASS by setting environment. Do not reintroduce feature or silently delete test for a greener count; explicit obsolescence/test-consolidation decision needed. |
| District → parcel detail | Empty private district table | Real synthetic district/parcel associations and original backend queries; fixture must support first-row selection and detail assertions, not mocked grid responses. |
| District → anomalies workspace | Empty private district table | Same consistent private dataset and original navigation/filter/no-anomaly-or-close assertions; no production import. |
| GIS desktop/mobile console | Optional flag absent | Original flag plus browser/WebGL/frontend and parcel tile request path; original API/auth stubs retained, not live auth/GIS proof. |
| GIS consultation/sheets/measure/print/QGIS | Optional flag absent | Rendered feature hit-test with matching parcel identity/tile or compatible original overlay fixture; original mocked PDF/print/QGIS and provider-error assertions unchanged. |
| Wiki Docker synthetic console | Isolated gateway absent | Private synthetic user/real login, deterministic300subjects, real tools/audit history/gateway/model and correct private routing; no shared compose mounts or fake response. |
| Wiki synthetic login→gateway→MCP→model | Explicit live fixture/provider opt-in absent | Loopback backend URL, original positive ID4a00bb81-2eb8-5fbc-81fe-98e6858033af and negative absent-subject assertions; real tool calls/model, not mocked provider substitute. |

All seven source identities and hashes remain exact against immutable historical
61case receipt:54PASS/7SKIP/0FAIL/NOT_RUN. This turn executes **zero native cases**,
resolves **zero skips**; classifications are not new functional verification.

## Fresh authoritative readiness

- All1405recorded frontend server/static build artifacts exact, missing0/drift0;
  BUILD_ID unchanged. Existing build/dependency entry points present. This is
  historical build-byte continuity, not a new build/running-stack certificate.
- No legacy owned loopback39081/39082/39083 listeners or synthetic-named running
  containers at captured observation. Names alone are not ownership/provider
  evidence; no existing/shared service touched or inferred safe for reuse.
- Original private proxy routes /api/ to backend and every other path to Next.
  It has **no explicit tile service**. Original MapContainer requests
  /tiles/cat_particelle_current/{z}/{x}/{y}; GIS smoke intercepts different
  /api/catasto/gis/tiles paths. Changing the flag alone does not prove vector
  tile readiness. The first case checks tile requests, not successful tile data.
  Hit-testing uses actual queryRenderedFeatures. An original alternative exists:
  search supplies a GeoJSON polygon with PARCEL_ID; overlay fill/centroid layers
  participate in default parcel click dispatch. Therefore missing base vector
  tiles does not prove consultation impossible. Original overlay publication,
  visibility, geometry/click compatibility and WebGL still need verification;
  do not force a feature hit or replace the original callback/assertions.
- Both GIS cases already mock login, catalog/interrogation/sheet PDF/print and
  QGIS. A future PASS remains bounded UI smoke, never live RAS/AdE/auth/PDF/QGIS
  certification. Source documentation states this limit explicitly.
- Wiki compose is a shared deployment recipe, reading .env and config/runtime
  mounts. Do not launch it as a private fixture. Isolated clone must bind only
  private synthetic paths, deterministic dataset manifest and real user/login;
  login creates device/session, requiring already-reviewed synthetic cleanup.
- Wiki provider contract requires gpt-reserve plus configured URL/key; secrets
  neither read nor published by this analysis. Provider readiness/opt-in/budget
  remain unverified; do not replace model/toolchain with canned responses.

## Evidence and retained failure

Read-only stdlib/hash/Git/port/container observation, no application imports.
First static auditexit1 incorrectly assumed historical skipped was scalar7;
receipt stores seven complete records. Original checker/log/exit preserved.
Distinct V2 validates exact list type/length, auditexit0; no native retry or
test/assertion change. Source/build/route/provider prerequisite freezes retained.
Native outcome remains NOT_RUN, coverage NOT_MEASURED_UNCHANGED_RUNTIME.

Independent reviewer V1 also exits1 before automated identity/build checks:
it incorrectly equates external evidence JSON with a differently-shaped summary
JSON. Original STOP/script/log/exit/36record manifest retained; no V1acceptance
or independent build rehash inferred. A distinct static V2 assignment validates
evidence and corresponding semantic fields separately, not a native retry.

V2 independent auditexit0 accepts **STATIC_PREREQUISITE_ANALYSIS_NOT_EXECUTION_READY**:
all7identity/source bindings and1405build artifacts rehashed, no native case,
resolved skip or execution-readiness certificate. Reviewer stopped;1336member
output archived byte-exact onSSD. ReviewSHA
8b432842d87f1e7cde7a67b6fb510aaaa3f42cc10f9f5592706546edf8650186;
manifestSHAda3dcfefe9a181533cdf152ca950d82581837b26c01eeb72344416d775ad34fa.

Actual-main ratchet and diff/Graphify receipts bound in companion JSON/handoff;
baseline/thresholds/exclusions/ignore/coverage policy unchanged. No global-baseline
PASS or complexity reduction claim. Worker100FAIL, historical backend199skip,
matcher ambiguity, excludedR43/R51/R63partials and extreme tail remain.
Latest full metrics1681files/20360callables/1920errors/2736warnings/4656overlapping
findings unchanged, not remeasured by this analysis. Goal ACTIVE/INCOMPLETE.

## Next sequence

1. Prepare one owned isolated GIS UI environment with original2case collection,
   recorded build/browser/tiles/network containment; review before one full-file
   run with original assertions/timeouts/retry0. Preserve any failure, no blind retry.
2. Prepare genuine private Catasto district/parcel dataset and verify referential
   and geometry/query requirements before original2case drill-down execution.
3. Separate original Wiki gateway/model fixture with bounded real-provider
   opt-in/budget, deterministic dataset and login/device custody, then original
   positive/negative/tool-history assertions. No provider counterfeit.
4. Keep obsolete empty test distinctly unverified until explicit disposition;
   then revisit queued R74 and choose one current-ranking hotspot for the newly
   authorized targeted slice. These steps are not a completion claim.

Durable root:
/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r75-e2e-skip-readiness.
CURRENT_SKIP_READINESS.json binds original identities,1405artifact audit and
fresh stack observation; publication/handoff manifest binds exact files/commits.
