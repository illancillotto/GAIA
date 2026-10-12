# Settings SISTER — loaded credential hydration

R38 isolates one pure field-projection policy from the settings workspace.
`loadedSisterCredentialFields` projects the seven fields shared by selected and
default credential refresh; `refreshSisterCredentialForm` preserves selected-first
lookup, strict ids, first-match semantics and default-only-on-blank-username.
The React functional updater still executes at its original transition point.

No API, hook/effect order, authorization, password handling, unsaved schedule or
draft behavior changes. An unchanged form retains its object identity; projection
retains unknown fields and password/schedule references. Failed reload/recovery,
missing selected id, default fallback id and deferred/reversed completions are
characterized through actual mounted UI/public API tests, not private hook mocks.
Plain JSON DTOs are the contract; getter/proxy equivalence is not asserted.

Original80-case characterization, candidate author, independent final and root
integration each verify the complete workspace at100% statement/branch/function/
line coverage. Root80tests/11new PASS, types/lint and actualmain55a ratchet PASS0.
The full-file gate has456statements/552branch arms/120functions/401lines, all hit.

Native cognitive decreases workspace296→280 and file509→468; cyclomatic file
551→535, callableLOCsum2416→2355. File effectiveLOC1702 and11state/2effects remain
unchanged. Both pure helpers stay below warning thresholds; no metric debt is
transferred. This is a small IMPROVED slice, not resolution of all Settings debt.
Baseline, thresholds, exclusions, config and old tests remain unchanged.

Reproduce tests from `frontend/`:

```bash
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/settings-workspace.tsx npm test -- --run tests/unit/elaborazioni-settings-sister.test.tsx tests/unit/elaborazioni-settings-presenze-tab.test.tsx tests/unit/campaign-settings-hydration-r38.test.tsx --maxWorkers=1 --coverage
```

Run `make complexity-report` and `make complexity-ratchet BASE_REF=main` from the
campaign checkout; main/merge-base55a1b1d35911451e018b662c2acc450bf5994ea2 remains
authoritative. The campaign is incomplete; this does not certify Bonifica/R37,
the separate matcher candidate or broad backend/frontend/build/worker/E2E suites.
