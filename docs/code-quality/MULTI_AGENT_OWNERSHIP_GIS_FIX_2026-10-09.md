# GAIA — GIS E2E fix ownership

User clarified «FAIL test GIS», superseding the provisional coverage target.
Capacitas closure is stopped; its worktree is preserved and never integrated.
Main dirty55a untouched. Baseline, runtime, thresholds, retry and timeout
settings are immutable for this test-only slice.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
| --- | --- | --- | --- | --- | --- | --- |
| GIS E2E fix (gis_test_fix) | Catasto GIS tests | frontend/tests/e2e/catasto-gis.spec.ts; private test-only helper adjacent if justified; domain-docs/catasto/docs/GIS_E2E_CAMERA_SYNC_2026-10-09.md; reports/code-quality/SLICE_GIS_E2E_FIX_2026-10-09.md | Fix premature native canvas click through observable render/camera synchronization; preserve actual fiscal search, popup request and panel assertions, motion semantics and timeouts | GAIA-campaign-20261009-gis-test-fix | fix/gis-e2e-camera-sync | ACTIVE |
| GIS E2E review (gis_fix_review) | Integration | reports/code-quality/INTEGRATION_GIS_E2E_FIX_2026-10-09.md; approved exact test-only source cherry-pick | Review synchronization validity and motion/load stress evidence; no runtime/private React lookup or fake map state | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | ACTIVE |
| GIS E2E verifier (gis_final_verifier) | Final browser verification | reports/code-quality/VERIFICATION_GIS_E2E_FIX_2026-10-09.md only | Fresh focused repeat and integration full browser suite with skips/attempts recorded | GAIA-campaign-20261009-gis-verification | verify/gis-e2e-camera-sync | ACTIVE |

Do not disable real user gesture handling, change production animation,
increase retry/timeout, drop popup assertions or use arbitrary sleeps. Prefer
actual stable-render/target observation using public browser behavior. Do not
commit React-fiber traversal, private MapLibre patching or probe instrumentation.
Reduced-motion alone must not conceal lack of default-motion synchronization.
Use synthetic own credentials/stack only; check ports/resources before startup,
record and clean only owned services. Commits/branch integration authorized only
inside campaign branches after independent review; no main merge/push/PR.
