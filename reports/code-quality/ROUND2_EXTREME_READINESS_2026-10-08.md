# GAIA — Round 2 extreme-tail readiness

## Scope and provenance

Read-only preparation for the next coherent slices, not authorization to
refactor these files. Integration HEAD `a91b6adf`, runtime identical to R1
`5a56f05c`, merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Coordinator owns this report; active R2 owners retain their runtime paths.
No runtime, test, threshold, baseline, exclusion or tooling changed.

Graphify frontend query in integration failed because its graph was absent;
the same dedicated target on main succeeded. Graph relationships are only
orientation, not proof of coverage, behavior or complexity.

## Measurement

Eight existing frontend suites: **95 PASS**, no skips. Coverage gate **FAIL**,
exit1. This is not a failed behavioral test and not a new runtime regression.
The coverage JSON is inspected per file, not just by global percentage.

| Runtime | Cognitive | Statement | Branch | Readiness |
| --- | ---: | ---: | ---: | --- |
| MePageContent | 271 | 189/359 | 223/619 | COVERAGE_GAP |
| PresenzeCollaboratoreDetailPage | 233 | 306/306 | 386/386 | TOOLING_100_WITH_LEGACY_EXCLUSION; review required |
| PresenzeExportPage | 209 | 0/0 | 0/0 | NOT_MEASURED; whole-file ignore, not full coverage |
| MapContainer | 246 | 205/205 | 106/106 | CENSORED_COVERAGE; not readiness100 |
| ElaborazioneBatchDetailWorkspace | 216 | 349/349 | 325/325 | TOOLING_100; candidate after invariant review |

Counts are from the unchanged scanner and V8 JSON. Zero denominator is not
100% evidence. A green file entry alone is insufficient for readiness.

### Legacy exclusions and instrumentation limits

- Export starts `v8 ignore start` at line1 and stops at1406: the operational
  component is entirely absent from statement/branch/function maps. No real
  full-file coverage can be claimed from this run.
- MapContainer's last mapped statement/branch starts at887, despite1546 source
  lines and the first `c8 ignore start` at889. Further click/overlay/focus/layer
  lifecycle code is absent from these maps. There are paired `c8 ignore end`
  comments in the source, but their observed effect is broader than the brief
  comment text implies. Cause must be verified independently; do not treat
  this censored measurement as proof that later runtime paths are covered.
- Collaborator detail has a legacy six-line ignore around mapping controls.
  The full-file maps reach line1713 of1729; any eventual slice must explicitly
  review that exclusion and characterize the modified responsibility.
- Batch detail maps reach line852 of862 and no local coverage ignore was found.
  Meaningful suite and behavioral invariants still require review before editing.

No exclusion is added, widened or changed to improve these results. The
existing exclusions are disclosed rather than silently interpreted as success.

## Reproduction

From integration `frontend/`:

```bash
VITEST_COVERAGE_INCLUDE='src/app/me/me-page-content.tsx,src/components/catasto/gis/MapContainer.tsx,src/app/presenze/collaboratori/[id]/page.tsx,src/app/presenze/export/page.tsx,src/components/elaborazioni/batch-detail-workspace.tsx' \
./node_modules/.bin/vitest run \
  tests/unit/me-page-content.test.tsx \
  tests/unit/catasto-gis-map-container-overlay-click.test.tsx \
  tests/unit/catasto-gis-map-overlay-helpers.test.ts \
  tests/unit/presenze-collaboratore-detail.test.tsx \
  tests/unit/presenze-collaboratore-detail-helpers.test.ts \
  tests/unit/presenze-export-page.test.tsx \
  tests/unit/elaborazioni-batch-detail-workspace.test.ts \
  tests/unit/batch-detail-interactions.test.tsx \
  --maxWorkers=1 --coverage \
  --coverage.reportsDirectory=/tmp/gaia-r2-extreme-readiness-coverage
```

Evidence: `/tmp/gaia-r2-extreme-readiness.log`,
`/tmp/gaia-r2-extreme-readiness-coverage/coverage-final.json`,
`/tmp/gaia-r2-coordinator-frontend-query.log`,
`/tmp/gaia-r2-coordinator-frontend-main-query.log`.

## Decision

Keep extreme-tail priority. Continue the three owned R2 slices; propose a
batch-detail state/action responsibility only after their integration checkpoint
is green. Me needs legitimate characterization closure. Export and MapContainer
need trustworthy full-file instrumentation evidence, not acceptance of the
censored report. Nothing here completes the global goal or removes hotspots.
