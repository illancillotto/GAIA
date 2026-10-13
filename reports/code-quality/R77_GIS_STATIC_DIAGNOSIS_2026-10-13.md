# R77 — GIS failure: source and retained-trace diagnosis

## Scope and snapshot

Previous R76 is verified progress, not a successful native suite: layout1PASS,
consultation1FAIL,0SKIP,retry0. User prioritizes investigation of seven historical
E2E skips. The prior optional priority question is unanswered; this continuation
uses safe static diagnosis only, never implicit repair/fixture/rerun permission.
No runtime, test, assertion, timeout, mock, authentication, quota or policy change.

Integration branch `refactor/complexity-campaign-20261008`, initial HEAD
`e09cc835fc57a1d1269f611973ec14f1eb4bdb34`; actual main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Historical55a1b1d remains provenance,
not a substitute BASE_REF. Main concurrent config/Bonifica work remains excluded.

## Verified observations

| Evidence | Observed result | Limit |
| --- | --- | --- |
| Original trace click spec470, then472 | Parcel click completes before municipality click, both without recorded click error | UI delegates to async selection; click completion does not measure callback/React-state completion |
| Search and municipality WFS responses | One200 each; delivered body bytes and hashes retained | Original mocks, not live GIS |
| Parcel vector tile records | 26HTTP404,2status-1;0successful responses | Status-1 cause not assigned; not called aborted |
| Parcel popup requests | 0 in failed-case network stream | Does not directly measure queryRenderedFeatures output |
| Failure | Original button absent at spec508, unchanged20s expectation | R76 remains FAIL; later assertions not verified |

No new native process was launched. No new PASS, resolved skip or coverage credit.

## Conditional source transition

Original workflow selects the parcel and then the municipal search result. The
search UI delegates each click to `selectResult`. With map/token available and
an allowed completed focus, `onResultFocus(result)` replaces the single search
overlay through `buildSearchOverlay([result], true)`.

The builder retains only parcel-kind results with a feature. A municipality
result has kind`comune`: that builder returnsnull. **If the completed focus and
React update take this branch**, the parcel search overlay no longer participates
in map overlays. Actual parcel selection still requires an identified feature
from `queryRenderedFeatures`; it is not driven by clicking arbitrary empty canvas.

This source transition is deterministic under the stated preconditions. The
retained trace does not read back React state, callback completion, published
layers, camera coordinates or hit-test results. Therefore it supports an
unfulfilled selection prerequisite, not a complete native causal demonstration
or proof that every possible selectable feature was absent.

## Geometry and tile format

Delivered parcel bbox`[8.585,39.905,8.595,39.915]`, municipality bbox
`[8.55,39.75,8.68,39.88]`: disjoint, both within source comprensorio
`[8.39,39.62,8.93,40.13]`. Original response resources SHA1/SHA256 checked.
These are geographic coordinate facts, not camera/projection/visibility proof.

Original tile stub targets`/api/catasto/gis/tiles/**` and returnsimage/png.
Actual `particelle-source` is vector, using`/tiles/cat_particelle_current/{z}/{x}/{y}`.
A URL-only mock correction would still supply raster PNG, not valid MVT geometry
and identity. It is not an acceptable solution or admitted change.

The original GeoJSON search fixture is a potential alternate selection path, but
the source does not guarantee that path survives a completed municipality focus.
An owned genuine vector fixture or a separately authorized test workflow proposal
must make its intended selection prerequisite explicit, without forced features,
private callbacks, weakened assertions or changing runtime behavior.

## Source provenance

Ten examined spec/config/search/map files match R76 native source hashes, their
exact frozen copies and currentmain blobs. Read-only scoped gitdiffmain is empty.
Blame: original PNG/path stubdd5c9dc7e(2026-09-01), focus replacement and parcel
clickf8740678b(2026-09-10), actual tileURLe79200917(2026-06-03). The first two
commits are independently proven ancestors of snapshot55a1b1d.

This establishes pre-existing selected source assumptions, not a historical
native failure or global campaign behavior-equivalence. No regression attribution
to R76/R77 is supported. No broad source/build/browser certificate is inferred
from these ten files; historical trees were not rehashed by the reviewer.

## Analysis failures and independent review

Initial static analysisexit1: incorrect substring assumed an unescaped dot in
the source selector. Initial supplementexit1: assumed source ID`particelle`, while
actual ID is`particelle-source`. Scripts/logs/exits/partial freezes preserved.
Distinct corrected analysis/supplement reads exit0; no native retry or mutation.

Independent ACCEPTED_STATIC_FINDINGS_WITH_LIMITS,193checks/exit0. It reconstructs
trace/body/source/provenance facts and explicitly does not certify native root
cause, sufficient correction or a countertest. Reviewer stopped; exact output
copied from permitted/tmp to durableSSD and independently checksummed.
Manifest SHA256`64a6420bee96d94aa6cf3600076643353cd8a1f656801c190951e19f18958da9`.

## Gates and classification

One `make complexity-ratchet BASE_REF=main`: PASS0 against actualbasea51a48dc.
Diff checksPASS. Graphify frontend-query used for orientation only; platform-docs
refresh follows final documentation through the dedicated Make target. No graph
output committed or used as complexity evidence. No baseline/scope/threshold/
ignore/exclusion/coverage changes; global matcher ambiguity remains separate.

Runtime classification **NO_CHANGE**; this is a reviewed diagnostic checkpoint,
not an improved refactor. Coverage NOT_MEASURED_UNCHANGED_RUNTIME. Latest global
metrics remain the last recorded1681files/20360callables/1920errors/2736warnings/
4656overlapping findings, not newly measured here. Goal ACTIVE/INCOMPLETE.

HistoricalR62backend7142PASS/449SKIP immutable;250prior backend skips verified,
199unverified. R74native52case run queued. HistoricalE2E54PASS/7SKIP unchanged;
R76newly verifies one bounded UI identity, exposes oneFAIL; otherfive not run.
Worker100coverageFAIL, excludedR43/R51/R63, matcher ambiguity and extreme tail open.

## Handoff and next decision

Durable root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r77-gis-static-diagnosis`.
Original scripts/failures and source/trace freezes retained. Authoritative corrected
outputs `analysis-v2/DIAGNOSIS.json`, `supplement-v2/STATIC_FINDINGS.json`; independent
`review/STATIC_REVIEW.md`, consumed-byte archive and manifest. Source trace SHA256
`a86a592cb73f1864fcf5deb093e538aa89f339b510ad6402562bda3db3b7c31c`.
`publication/SESSION_CHECKPOINT.md` and detached final handoff manifest bind final
commit, exact admitted/excluded inventory, gates and pending decision. Initial
PROGRESS and ownership frozen before changes; R76historical receipts untouched.

Separate next decision: preserve original spec and characterize a private valid
MVT/geometry/identity prerequisite, or authorize a test workflow correction proposal
preserving all assertions and making parcel focus explicit after municipal search.
No such implementation/rerun admitted here. Otherfive E2E prerequisites remain
separate; no new runtime hotspot before the authorized verification phase closes.
