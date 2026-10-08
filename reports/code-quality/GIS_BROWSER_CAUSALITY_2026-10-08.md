# GIS — Read-only Browser Causality Investigation

## Scope and decision

Coordinator-owned diagnosis under registry1460954c. No runtime, E2E spec,
configuration, timeouts, retries, exclusions or baseline was changed. R3
runtime remains frozen; this report does not authorize the next runtime wave.
Original failure attribution remains **UNKNOWN**. The offline experiment
demonstrates a plausible library mechanism, not the original application's
unrecorded camera state. Explicit risk decision requested from the user is
still pending at this checkpoint.

## Original evidence

Source: `ROUND3_BROWSER_VERIFICATION_2026-10-08.md` and retained trace
`/tmp/gaia-r3-e2e-artifacts/catasto-gis-catasto-gis-fi-545c3-h-opens-parcel-role-details-chromium/trace.zip`.

- Initial full browser run:51PASS7skip1FAIL; unchanged focused diagnostic1PASS;
  unchanged full confirmation52PASS7skip. First failure remains recorded.
- `frontend/tests/e2e/catasto-gis.spec.ts:365` selects fiscal search result,
  closes search, then repeatedly default-center-clicks the native canvas.
  There is no explicit camera-completion synchronization before the first click.
- Search returned200. Trace recorded zero parcel-popup requests. Final
  screenshot places polygon center approximately580,421 versus canvas center
 750,442.5: clicking canvas center misses the visible polygon.
- Trace result selection starts11170.685ms; search-close starts11203.601ms;
  first canvas click starts11378.245ms and ends11523.438ms at750,442.5.
  These are Playwright action times, not measured `fitBounds` start/stop times.
- `frontend/src/components/catasto/gis/use-territorio-unified-search.ts:71`
  focuses geometry via `fitBounds`, duration700ms, padding48, maxZoom17.
  Installed MapLibre6.9.0 `src/ui/handler_manager.ts:473` stops camera movement
  when a native gesture becomes active.
- Optional tiles404 and layer endpoints503 occur in this disposable stack;
  unchanged subsequent passes mean they cannot alone be declared causal.
  No camera-event telemetry exists in the original trace.

Campaign GIS diff since main is the R1 Excel-reference normalization extraction,
not the fiscal-search/gesture handler. MapContainer and this E2E spec are
unchanged; R3 did not modify GIS. This excludes a direct change in the failing
flow, not every possible indirect regression. No original-state attribution
is proven by source inspection or subsequent passes.

## Offline experiment

Artifact `/tmp/gaia-gis-camera-causality.cjs`, SHA256
`ab8cf53bd37956ebebd1a7156447c7e5c648ac847f4314e6c0cb403a3e97df87`.
Reproduce with installed Playwright/Chromium and MapLibre dependencies:

```bash
INTERRUPTION_DELAY_MS=80 node /tmp/gaia-gis-camera-causality.cjs \
  > /tmp/gaia-gis-camera-causality-80.log 2>&1
```

The disposable script uses real MapLibre6.9.0, not a camera double. It serves
local ESM modules through Playwright route fulfillment at a synthetic origin,
with empty style and one parcel polygon. No server, backend, real credentials,
production resource or external request is needed. It resets center8.66/39.875,
zoom11 and fits bounds8.55/39.88–8.56/39.89 using700ms/padding48/maxZoom17.
Controls have no gesture; interventions use real Playwright native canvas
clicks during movement. It records `moveend`, projected parcel position and
actual `queryRenderedFeatures` center hits after900ms. The synthetic viewport
and style differ from the full application; experiment timing is not claimed
to equal the original timing.

Latest run exit0; JSON `/tmp/gaia-gis-camera-causality-80.json`, SHA256
`41d1d8d4dad906a9e59db8a35472d212b4306c83c273a5ecaa7ad2b8f9874bc9`.

| Scenario | Runs | moveend elapsed ms | Final center hit |
| --- | ---: | --- | --- |
| No gesture controls | 2 | 708;715.4 | 2/2 true |
| Click scheduled after80ms | 4 | 159.4;124;129;112.6 | 0/4 true |

All interventions stop before reaching the target camera center; final
longitude8.5775–8.6016 versus target8.555. Controls reach target8.555 and hit.
External requests:0. Actual gesture times differ from requested delay because
Playwright scheduling/actionability takes time. This is a demonstrated causal
effect **within this isolated experiment**.

## All attempts retained

1. Initial setup failed because this installed release provides ESM modules,
   not assumed `dist/maplibre-gl.js`; corrected local diagnostic loading only.
2. An assertion that every interrupted200ms click must miss failed. Camera
   interruption does not imply a miss once the polygon covers canvas center.
3. `/tmp/gaia-gis-camera-causality3.log`:200ms observations stopped early4/4,
   with2hits/2misses; observation run exit0, not universal miss proof.
4. `/tmp/gaia-gis-camera-causality-final.log`:200ms assertion requiring at
   least one miss failed when all four polygons already overlapped center.
5. Latest80ms run above:two controls hit, four interrupted gestures miss,
   exit0. This illustrates timing-sensitive hit geometry, not an application
   fix or a statistical guarantee. Earlier failures are not erased or PASS.

## Conclusion and next decision

**DEMONSTRATED:** native gesture can stop real MapLibre fit animation early,
leaving a polygon permanently away from the default canvas-click point.
**CORROBORATED_NOT_CAPTURED:** the original trace timing and final geometry
are consistent with that mechanism, but original camera events are absent.
**UNKNOWN:** definitive original root cause and attribution to the campaign.

Recommended separate investigation: capture camera events around the original
search-to-click sequence, compare authoritative snapshot and integrated runtime
under identical conditions, and evaluate synchronization with actual rendered
parcel geometry. Do not remove genuine user gesture behavior or increase
retries to conceal the failure. Any E2E/runtime change requires a separately
owned, reviewed slice; this report changes neither and accepts no risk for the
user. Safe test-only Capacitas characterization can continue meanwhile.
