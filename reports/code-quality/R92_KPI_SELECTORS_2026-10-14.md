# R92 — Catasto KPI selector correction: preparation and review only

## Authorization and identity

User «autorizzo» approves preparation/review of the bounded KPI selector correction,
without new E2E. No activation, runtime/driver/DB repair, commit or main merge.
Integration branch `refactor/complexity-campaign-20261008`, HEAD
`7f39510ab1ef1d4e531d8b12a4eb6b36f556cee4`, main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. BASE_REF=main unchanged.

## Correction and invariants

R91 first-case FAIL was strict `Particelle` text matching export span, KPI
paragraph and tab button. Four existing KPI visibility assertions now use
`workspace.locator(".metric-card").getByText(label, { exact: true })`.
Separate Particelle/Anomalie button assertions are preserved. No assertion is
removed, no first-match workaround introduced, no timeout extended.

Exact comparison against the frozen pre-R92 spec proves removing those four
scope tokens reconstructs every original byte. Authentication, readiness/skip,
iframe/row actions, URLs, all other assertions and case-two bytes are unchanged.
Readiness helper/test, runtime district page/MetricCard and frontend configs/
package lock hashes remain unchanged. Source labels correspond to real cards.

## Characterization matrix

| Behavior | Existing evidence | Added | Result |
| --- | --- | --- | --- |
| KPI selected despite export/button duplicate labels | R91 raw three-match failure; runtime card source | Four real MetricCard DOM cases | PASS in DOM model |
| Missing KPI is not replaced by export/tab text | No native missing-KPI run | Four missing-card cases | PASS in DOM model |
| Hidden KPI stays a failing visibility condition | No native hidden-KPI run | Four hidden-card cases | PASS in DOM model |
| Duplicate KPI is not resolved by first position | Strict Playwright contract, not rerun | Four duplicate-card cases retaining two matches | PASS in DOM model |
| Exact label, old collision and separate tab checks | Frozen R91 source | Three source/DOM cases | PASS |
| Existing readiness contract | R90 characterization | No modification, 27 original cases rerun | PASS |
| Both original drill-down cases | R91 first FAIL / second NOT_RUN | None, E2E not authorized | NOT_RUN in R92 |

DOM tests use Testing Library/jsdom and actual MetricCard rendering plus assertions
on the current spec's selector syntax. They do not execute Playwright's browser
selector engine, strictness, retries, native visibility/layout, authentication,
DB or downstream transitions. Duplicate count is evidence of retained ambiguity,
not a native strict-mode execution. No native success claim is made.

## Checks and preserved failures

- `npm run test:unit -- tests/unit/catasto-drilldown-kpi-selectors.test.ts tests/unit/distretti-readiness.test.ts --maxWorkers=1`: final 46 PASS, 2 files.
- Targeted `tsc --project <external>/verification/tsconfig.json --noEmit`: PASS;
  covers spec/helper/two unit files/setup and imported dependencies.
- `git diff --check`, exact restoration, helper/test comparison and protected
  input hashes: PASS. Complexity ratchet/report and full suites NOT_RUN for this
  test-only preparation; no new runtime metric or coverage claim.
- Initial unit attempt: 42 PASS / 4 FAIL in cleanup after manually removing a
  React-managed card. New fixture uses React unmount; same missing-card assertions
  retained. Full failed log/source preserved, not overwritten or declared PASS.
- Initial targeted typecheck: FAIL because the external config excluded Node
  types. Original config/log preserved; only external typeRoots/types corrected,
  repository config unchanged. Separate final check PASS.

Coverage requirement for modified runtime is not triggered: no runtime modified.
No coverage exclusions, thresholds, baseline, ignores or dependency changes.
R91 original first FAIL/second NOT_RUN and secondary strict-drain failure remain
historical facts; driver is unchanged and not repaired by this preparation.

## Review, evidence and remaining limits

Ownership registry recorded before reviewer dispatch. Independent source review:
**SOURCE_PREPARATION_ACCEPTED / NO_NATIVE_EXECUTION / NOT_ADMITTED**;
258/258 source/hash/receipt checks, not application tests. Reviewer stopped,
10-file seal verified by Coordinator; exact four-token restoration confirmed.
Source was not edited after acceptance. Reviewer disclosed an ancillary
seal-verification log accidentally written to `/tmp/r92-review-seal-verify.txt`;
preserved in reviewer-ancillary/, no prior code/evidence overwritten. Coordinator
also retained a wrong-cwd hash-check observation: four relative paths unavailable,
then exact check from checkout PASS; no mutation or application failure.
Durable root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r92-kpi-selectors/`.
`before/` preserves mutable docs/spec before edits. `verification/` retains
failed attempts, final logs, preservation receipt, diffs and current source hashes.
Historical R91 terminal manifest revalidated unchanged before this preparation.

Independent review report SHA256:
`2cc6d8191fede00d98ef73a92f245d79a301185631e18b50bf2702ae5e59895d`.
Review seal SHA256:
`3aa386b63b335fe7105e2b8742c8feba78d5721117e160f1eca0df5e2f2e9ef2`.
Immutable preparation seal SHA256:
`e58566bd49f32d63c04c8a9435b66c20cb7475e343251913b2d01b6dacd772b7`.
Closure documents were frozen again before final annotations. Graphify dedicated
platform-docs target after tests terminal: exit0, chunk1/1done,
1026 nodes/1341 edges/163 communities, no semantic warnings. Ignored output not
staged; closure annotations after refresh are not claimed indexed.

Entire accumulated spec/readiness candidate remains NOT_ADMITTED. Future native
verification requires a separately prepared/reviewed new source/environment binding
and a separate execution grant; do not reuse R91 wrapper/run or consumed grant.
Downstream parcel text risks are unexecuted, not corrected in this slice. Global
complexity campaign remains incomplete; no new refactoring hotspot opened.
