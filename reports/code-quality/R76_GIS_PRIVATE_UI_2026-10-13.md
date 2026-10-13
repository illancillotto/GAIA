# R76 — Original optional GIS UI: one PASS, one preserved FAIL

## Scope and snapshot

User priority: investigate seven historical E2E skips before further PostgreSQL
runs. Verification only, not a runtime refactor or test repair. Dedicated
integration branch `refactor/complexity-campaign-20261008`, initial HEAD
`d3c9f7f962ea6e483cdf036ecdaa18eff371413c`; actual main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Historical `55a1b1d` remains provenance,
not a substitute gate reference. Main concurrent config/Bonifica work untouched.

## Original test matrix

| Behavior | Existing test | Missing / Added | Result |
| --- | --- | --- | --- |
| Desktop/mobile console and toolbar; measurement transitions; parcel tile requests | gis-territorio.spec.ts:381, original chromium project | None added; original optional flag enabled | PASS, 3860ms |
| Search, parcel consultation, territorial sheet, measurement, print, QGIS | gis-territorio.spec.ts:439, original chromium project | No assertions or fixtures changed | FAIL, 30240ms, parcel detail button absent at line508 |
| Later assertions after parcel selection in second case | Same original test | Not reached | NOT_VERIFIED, not PASS |

One full-file collection and one native execution. Exactly two original identities,
one attempt each, workers1/retries0/max-failures1. Original config90s/expect20s,
selectors, geometry, click dispatch, mocks and browser flags unchanged. Native
stats1PASS/1FAIL/0SKIP, 35.1s rounded. Playwright's maximum-failures stop message
also appears as a global error; not an additional independently failed test.
Parent execution exits1. No retry, patch or timeout/assertion weakening.

## Failure and limits

Original `Chiudi dettaglio particella GIS` button never becomes visible after
the original candidate canvas clicks; the existing20s assertion fails. Trace,
video, screenshot and DOM/error context preserved. Exact root cause remains
UNCONFIRMED: this is not proof of a campaign runtime regression. Original parcel
polygon latitude39.905–39.915 and municipal search polygon39.75–39.88 are disjoint;
the original flow selects both and zooms before parcel clicks. Missing base tiles
and overlay/camera/hit-testing compatibility require a separate diagnosis, not
an assumed fix or forced selection. The trace records28parcel-tile requests;
request occurrence is not successful tile delivery.

Original auth/catalog/search/interrogation/PDF/print/QGIS stubs retained. Bounded
UI PASS is not live authentication, GIS/provider, document generation or QGIS
certification. No backend, DB, provider or real tile service was launched. Genuine
unmocked local API/tile responses remain frontend errors, not successful mocks.

Historical61case54PASS/7SKIP receipt remains immutable. Of those seven identities,
R76 freshly verifies one bounded UI PASS, exposes one FAIL and does not run the
other five. Do not call the historical suite60PASS/6SKIP, erase the failed case,
or declare all seven resolved. Catasto drilldown2, Wiki2 and obsolete empty1 remain.

## Isolation, custody and preserved preparation failures

Private bubblewrap network/PID namespaces; only loopback interface; different
network namespace inode checked inside. Repository/build/dependencies read-only;
only native evidence and private0700 `/tmp` writable. Server on isolated39082;
no production listener or shared stack touched. Original absolute screenshot
paths mapped into private tmp and copied byte-exact to durable SSD.

Owned cgroup entry before exec/fork. Frontend stopped cleanly with exit0; native
supervisor exit1 retained; cgroup kernel populated0/pids empty, owned directory
removed. Before/after2732protected E2E inputs, dependencies/build/browser/runner
and main custody identical. This2732member original E2E scope differs from2852
PG scope; no excluded discrepancy. No runtime/test/build/source modification.

PreparationV1 STOP: independent audit assumed wrong freeze path; original error
preserved. V2 STOP: importable sibling guard bytecode not captured; valid custody
gap preserved. V3 uses `-B` and private empty0700 pycache prefix before guard
imports in parent and child; original caches retained, not deleted. Independent
V3 ACCEPTED_PREPARATION after21984static checks, no native PASS implied. Old
manifests are historical, frozen corresponding runner bytes retained; V3 is the
authoritative prelaunch snapshot. Coordinator failed atomic patch attempts also
disclosed in external notes, not hidden successful mutations.

## Gates and remaining work

`git diff --check` PASS. One `make complexity-ratchet BASE_REF=main` invocation:
PASS0 against actual merge-basea51a48dc. No baseline, thresholds, exclusions,
ignore, auth/quota, coverage or test policy changes. Global baseline ambiguity
remains separate; no new global-check certificate inferred.

Coverage NOT_MEASURED_UNCHANGED_RUNTIME; no complexity reduction credit. Latest
metrics remain1681files/20360callables/1920errors/2736warnings/4656overlapping
findings, not a fresh measurement. ImmutableR62backend7142PASS/449SKIP unchanged;
250historical backend skips verified,199unverified. R74prepared native run queued.
Worker coverage100FAIL, matcher ambiguity, excludedR43/R51/R63, extreme tail and
full repository coverage remain open. Goal ACTIVE/INCOMPLETE, not COMPLETE.

## Durable evidence / handoff

Root `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r76-gis-private-ui`.
`native/`: original reports/inventories/argv/logs/artifacts, namespace/containment,
custody/screenshot checksums. `TERMINAL_SUMMARY.json`: bounded outcome/network
inventory. `review-v1/`, `review-v2/`, `review-v3/`: distinct immutable reviews.
V3review manifest SHA256
`2ce88e65bcd0503576a87fe9a811f287f320892fc8740cf6f275f9f1aad7e5a0`.
PreparationV3manifest SHA256
`545ef85859260a6f36d04b6f0057079315d90fba78eeb30f125dc52daf6f58c6`.
Terminal independent review and publication handoff are appended distinctly;
never rewrite old receipts. No external evidence, caches, DB, dependency, build
or graphify-out staged. Runtime admission blocked for this failure; documentation
checkpoint may be committed independently after terminal review.

Terminal review ACCEPTED_EVIDENCE_WITH_NATIVE_FAILURE,2602static checks,
477native files/305trace members frozen; reviewer stopped. Manifest SHA256
`c9938fa49dcc23de674b1b1bbe87ba1b5d5808f11b0cd7b4285503edce8fd730`.
Exact terminal bytes copied from permitted/tmp output to durable `terminal-review/`.
Evidence acceptance is not suite PASS; root cause remains NOT_ESTABLISHED.
Collection skipped2 are `--list` placeholders, not executed skips.

Graphify platform-docs first publication pass exit0,chunk1/1done/no semantic
failure;912nodes/1162edges/160communities. Final metadata publication uses the
same dedicated target separately; preserve both logs, no root graph scan.
`publication/SESSION_CHECKPOINT.md`, `FINAL_HANDOFF_MANIFEST.json` and detached
checksum contain final local commit, admission inventory and durable custody.

Next: diagnose original parcel geometry/camera/overlay from retained trace before
authorizing any fixture/runtime change or distinct native re-verification. Other
five E2E prerequisites remain separate responsibilities, not blanket enablement.
