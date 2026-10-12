# GIS parcel popup presentation policy — R57

The GIS page retains all popup state, map callbacks, effects and JSX. A local
typed pure module `frontend/src/app/catasto/gis/parcel-popup-presentation.ts`
encapsulates parcel role badge, incomplete identity, title, location and record
state policy. No backend/API/coordinate/authorization contract changes.

The paired badge class/label decision tree is shared, but both callers keep
independent ha_ruolo reads. Source-mode/inferred fallback is still computed
before these reads. Title uses truthy CFM/key fallback; location uses nullish
municipality fallback, preserving empty strings. Incomplete key short circuits
code→sheet→parcel; subalterno is tested then reread for its suffix. Suppression
takes precedence and skips the current-record property read.

Mounted original/candidate characterization73casesPASS; all page/helper four
coverage measures100, strict test types/lint/authoritative ratchet PASS. No JSX,
React dependency or async lifecycle moved. One initial NEW transport mock did
not return a Promise, failed before refactor and was corrected only in tests;
exact failure evidence remains separate from fresh successful gates.

Principal cognitive317→298, but real aggregate debt568→566: only two net points
and two duplicated decisions removed. New helper roots increase cyclomatic sum
by3; combined source LOC increases23. Helper isolation is not counted as a
19-point global improvement. useState/useEffect remain28/8.

See `reports/code-quality/SLICE_R57_GIS_POPUP_PRESENTATION_2026-10-12.md` for
before/after metrics, invariant matrix, gate evidence and remaining risks.
This local verified refactor does not complete the broader quality campaign.
