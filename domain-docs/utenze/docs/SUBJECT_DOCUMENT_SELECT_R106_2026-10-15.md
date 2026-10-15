# Document-type select click isolation — R106

The document row is a preview activation surface; its type selector is a
separate edit-mode control. Two new public mounted cases verify that clicking
the enabled selector does not bubble into preview/download, mutate data or
reload the subject. A click→selection change→server reload→re-enable→click
lifecycle preserves exact update payload/order and refreshed selected type
without accidental preview. Disabled controls are never clicked.

Existing R23row/Enter/Space preview cases and R32type-change cases remain
unchanged. New spec:
`frontend/tests/unit/campaign-utenze-document-select-r106.test.tsx`.
Actual exported page/wrappers/domain children mount; only API/auth/navigation
boundaries mocked. Browser URL APIs are not instrumented: zero downloads and
absent preview/blob-backed output are asserted, not a direct URL-call count.

Eleven-spec273PASS, two new cases. Original full-page coverage567/576statement,
578/610branch,176/176function,528/536line; identical maps and no lost coverage.
Full-file100 still FAILS:9statements32branch arms8lines. No runtime admission
or complexity improvement; DetailContent remains391cognitive/304cyclomatic/
1908LOC. Native coverage exit1 is preserved separately from all tests PASS.

Read-only source/contract audit in external R106
coordinator-evidence/RESIDUAL_REACHABILITY_AUDIT.md explains why further public
tests alone cannot close every residual guard/fallback. This is scoped current
call-chain evidence, not universal dead-code proof or permission to remove
guards, mock derived helpers, fabricate payloads or relax coverage. Utenze
runtime admission requires a separate decision; the full campaign may continue
on independently testable original hotspots without changing policy.

R106report and external coordinator-evidence/HANDOFF.md index final review,
gates,graphs,custody. Global campaign ACTIVE/INCOMPLETE.
