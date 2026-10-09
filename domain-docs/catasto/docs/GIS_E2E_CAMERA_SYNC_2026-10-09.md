# GIS E2E — rendered parcel target synchronization

The fiscal-search E2E must not click canvas center merely because the result
button was clicked. Search starts a real 700ms camera animation. A native canvas
gesture can stop that animation before the searched parcel reaches the click
point. Subsequent clicks cannot repair the stopped camera.

The test now observes a browser screenshot of the real map canvas before the
native click. It requires the complete central 20x20 CSS-pixel patch to contain
the focused parcel's magenta highlight. This is **target-hittability**, not a
camera-idle or completed-animation assertion. The exact parcel popup request,
`A ruolo` panel and `CFM-4201` remain mandatory afterwards.

## Contract and constraints

- `TerritorioMapExperience.buildSearchOverlay` uses focused fill `#F000B8`,
  outline `#C4008E`, base opacity0.9, and a6-second pulse. The unfocused result
  is yellow. The fixture returns one polygon and no other magenta overlay.
- Pulse opacity spans0.22–0.98. Low-opacity frames may be ambiguous over actual
  basemap tiles; readiness waits for an adequately saturated actual frame.
  The predicate rejects green/white/yellow backgrounds and dim purple. It
  does not require equality with an uncomposited hex value. Red and blue
  dominance over green allow focused fill composited over river/water tiles,
  including captured RGB202/116/205. It intentionally does not impose red
  dominance over blue, which incorrectly rejects those real pixels.
- Every sampled pixel must be opaque in the composited browser screenshot,
  red>=190, green<=130, blue>=140, red-green>=70 and blue-green>=40.
  A full20x20 patch, rather than a single colored pixel, provides click margin.
- Screenshots use `animations: "allow"` and CSS scale. Image decoding happens
  in a separate2D canvas, not by reading the WebGL drawing buffer. No map
  instance, React fiber, private field or application state is inspected.
- Existing10-second `toPass`, retry intervals,5-second native canvas action,
  and1-second panel assertion remain unchanged. Screenshot action is bounded
  by the same5-second action budget. No sleep, snapshot baseline, reduced
  motion, production animation change or auth/config exemption is introduced.

## Regression protection

The same E2E spec includes pure pixel classification checks and browser
screenshot checks on a separate synthetic2D canvas. These prove that absent,
off-center and undersized highlights do not permit the native application
click, while a central40x40 highlight does. Compositing cases cover white,
green and blue basemaps at0.9/0.98 opacity and reject dim0.22 frames.
The synthetic canvas is confined to the helper test; the fiscal-search test
uses the unchanged real GIS application and native mouse gesture.

If styling, focus color, fixture geometry or overlay population changes,
review this visual contract explicitly. A missing/unclassifiable target must
fail rather than clicking speculatively. This test fix does not change the
application's user-gesture camera behavior.

See `reports/code-quality/SLICE_GIS_E2E_FIX_2026-10-09.md` for all attempts,
controlled reproduction, stress checks, commands, artifacts and limitations.
