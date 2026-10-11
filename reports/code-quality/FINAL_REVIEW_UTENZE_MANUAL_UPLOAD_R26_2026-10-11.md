# R26 Utenze manual upload — Independent Original Characterization Review

## Decision and limits

**ACCEPT_CHARACTERIZATION_ONLY.** The 49 new cases characterize the unchanged
production page through mounted public controls. They can be published as tests
after the Coordinator's integration gates. They do not authorize a runtime
refactor, do not establish full-file coverage, and receive no `IMPROVED` credit.

The fresh union is 170 passing cases across four specs, zero skips/todos. The
native coverage command exits **1**, exclusively because all four unchanged
100% thresholds remain unmet. Runtime remains **BLOCKED_COVERAGE**.

## Ownership and snapshot

- Ownership registered ACTIVE before reviewer activation by the Coordinator.
- Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261011-r26-utenze-review`.
- Branch: `review/complexity-r26-utenze-upload`.
- HEAD: `de76117a6ad9405fd013c3c7114d18625c2b8620`.
- Actual `git merge-base HEAD main`: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Reviewer writes only this NEW report and private evidence under
  `/home/cbo/.cache/gaia-campaign/20261011-r26-utenze-review/`.
- Original page, new frozen spec, three existing specs, config, baseline,
  dependencies and application code remain read-only. No commit or integration.

Reviewed the complete author characterization report, project instructions,
checkpoint and complexity skills, objective, quality validation/workflow,
original handlers, effects and modal JSX, and all 49 expanded new test cases.
Graphify/build/E2E/full application suites were not authorized for this review.

## Frozen inputs and custody

| Input | SHA256 |
| --- | --- |
| New manual-upload spec | `24878b60ce520369b94fc456c6ef28626a8bcc8511dc62085511cd825bd1e720` |
| Original page | `b0f822daf809b0744b912f0f159a2e833c556dda289466b6ed45329a79e3d6b1` |
| Original detail spec | `79ef301017ee78985d71b468300eba3239e901c9773eb56f60a033cd6ad13f98` |
| NAS R22 spec | `8f2258e4cb65b2242ac65fc39a1407fad9a6a48457060387ef7392e39c0ed6d9` |
| Preview R23 spec | `1fbcb0d529097bd4775daf09b661306dfd959d4bf57dd869dd11d2247c6d99b5` |
| Baseline | `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95` |

The private `inputs.sha256` also binds Vitest/TypeScript config and package file.
Main concurrent binary diff remains
`9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`;
main short-status remains
`0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`.
The reviewer tracked diff is empty before this report; the only imported
untracked code is the exact new test. No baseline inflation, scope, threshold,
ignore, dependency or runtime change.

Two ancillary read commands initially used incorrect relative paths (baseline
under docs rather than config; Makefile from frontend). Their diagnostics are
retained in the conversation; corrected read-only path checks succeed. They are
not native gate failures, retries, source changes or waived verification.

## Harness and behavioral review

The actual default page is mounted, including its real wrapper and domain
children. Only Next navigation, token storage and external API boundaries are
mocked. API mocks spread real unmodified exports. No React state/effect,
UUID, internal handler, application component or coverage counter is mocked.

Production `?embedded=1` avoids unrelated shell polling, not the domain page.
Complete typed company DTOs isolate subject-reference/status races; a separate
person case retains the real ANPR child and its external boundary. Real File
objects are passed through the native input and drag events; File identity is
asserted at upload boundaries. Conventional JSDOM FileList/transfer simulation
is not a browser chooser/E2E certification.

No deduplication is invented: the same File, filename or lastModified remains
independently selectable/editable. Uploads keep the captured array/token/ID,
sequential awaits, exact category and untrimmed notes, and singular/plural
messages. Partial failures retain all selected items; retry repeats earlier
successful uploads. Status rejection is absorbed, while dual explicit/effect
status requests can overwrite each other. These legacy semantics are preserved,
not silently fixed.

Busy pointer CSS is not bypassed with synthetic pointer interaction: the busy
selection case uses the existing focusable keyboard control and non-disabled
native file input. Native disabled controls are asserted. Escape closes the
modal without aborting requests; captured late success can clear a reopened
selection. Route changes retain old in-flight closures. Listener cleanup checks
actual callback-reference identity. No impossible DTO/internal-state injection.

## Characterization test matrix

Case IDs below are the actual frozen `focused.json` assertion order; ranges
group parameterized cases, not skipped or inferred tests. All existing 121 cases
remain immutable. Every row's Added/Result is NEW mounted characterization/PASS.

| Cases | Behavior | Existing coverage / missing distinction | Added | Result |
| --- | --- | --- | --- | --- |
| 1 | Read-only hides both entries; real edit confirmation enables them | Edit behavior existed; manual entry assertions missing | 1 | PASS |
| 2–4 | Both entries open same modal; eligible NAS hides only fallback | NAS visibility existed; manual transition missing | 3 | PASS |
| 5–8 | NAS path text, associated documents, real person/ANPR child | Fixtures existed; manual branches missing | 4 | PASS |
| 9–10 | Empty validation makes no calls; ordered append/default metadata | Manual command/list missing | 2 | PASS |
| 11–14 | Same File/name duplicates remain independent; null/empty selection retains list | No-dedup and selection guards missing | 4 | PASS |
| 15–18 | Click/Enter/space chooser activation; other key inert | Public chooser behavior missing | 4 | PASS |
| 19–20 | Drag highlight/preventDefault/stopPropagation; drop order and empty transfer | Public drag behavior missing | 2 | PASS |
| 21–23 | Per-row category/notes, remove/renumber, empty/binary arbitrary files | Metadata/list/file acceptance missing | 3 | PASS |
| 24–26 | Exact upload args/File identity; returned metadata ignored; notes verbatim | Manual API mapping missing | 3 | PASS |
| 27–29 | Strict sequential await/reload ordering; disabled controls; busy keyboard capture | Native busy and captured-list behavior missing | 3 | PASS |
| 30–32 | Explicit/effect status ordering/late overwrite, same-reference reload, plural/reset | NAS analogous cases did not cover manual command | 3 | PASS |
| 33–38 | Error/opaque first, partial second, reload rejection and retry repetition | Manual failure semantics missing | 6 | PASS |
| 39–42 | Absorbed status failures; retry message clearing; empty validation preserves success | Manual success/error coexistence missing | 4 | PASS |
| 43–45 | Cancel/Escape reset; backdrop/unrelated key do not close | Preview analogues did not cover manual modal | 3 | PASS |
| 46–49 | Late success/failure after Escape, captured route/token/ID, exact listener cleanup | Manual async/lifecycle missing | 4 | PASS |

The 28 plain definitions and 21 expanded parameterized cases total49. The
review does not claim simultaneous preview/manual precedence or a real browser
file chooser was newly exhaustively verified; existing preview characterization
remains in the union and runtime is unchanged.

## Fresh independent native evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Focused NEW spec | Native0; 49PASS/1 spec/no skip/todo | `focused.log`, `focused.json`, `focused.exit` |
| Old three specs + NEW exact-page coverage | Native1; 170PASS/4 specs, expected FAIL100 only | `union.log`, `union.json`, `union.exit`, `coverage/coverage-final.json` |
| Independent raw audit | 0; exact single runtime path, counts, zero skip markers; exactly four threshold errors | `audit.cjs`, `audit.log`, `audit.json`, `audit.exit` |
| Complete project + NEW spec strict types | Native0; 662 project roots, 661 runtime files, zero diagnostics | `types.log`, `types.exit` |
| Scoped NEW spec ESLint, zero warnings | Native0 | `lint.log`, `lint.exit` |
| Input custody | Native0; all manifest entries OK | `inputs.sha256`, `custody.log`, `custody.exit` |
| Actual-main complexity ratchet | Native Make0; baseline_commit55a/findings[] | `ratchet.log`, `ratchet.exit` |

The type verifier includes the complete parsed project roots, the NEW test and
Jest DOM typings, retains project strict options, checks the original page is in
the runtime source closure, and emits no diagnostics. It does not omit ambient
GeoJSON declarations or hide errors. Native heavy gates run serially under the
reviewer's exclusive token. No unexpected native failure or retry occurred.

## Coverage before, after and residual debt

Independently read fresh Coordinator-original raw121 coverage, then generated
fresh reviewer170 coverage against byte-identical page and unchanged thresholds.
Both raw files contain exactly the whole original page, same denominators, zero
skipped statements/functions/branches/lines.

| Dimension | Original121 | New union170 | Added covered | Still uncovered |
| --- | ---: | ---: | ---: | ---: |
| Statements | 370/576 (64.23%) | 437/576 (75.86%) | 67 | 139 |
| Branch arms | 408/610 (66.88%) | 460/610 (75.40%) | 52 | 150 |
| Functions | 80/176 (45.45%) | 109/176 (61.93%) | 29 | 67 |
| Lines | 364/536 (67.91%) | 426/536 (79.47%) | 62 | 110 |

This is meaningful original characterization progress, **not full100 PASS**.
No runtime statement/branch coverage credit is fabricated. No line-only or
differential waiver is used. Main callable remains cognitive391/cyclomatic304/
LOC1908; no runtime delta, relocation or complexity reduction is claimed.

## Reproduction

Run from this review worktree's `frontend` directory; `OUT` is the private
evidence directory stated above. Preserve outputs and exits, not just a pipe.

```bash
./node_modules/.bin/vitest run tests/unit/campaign-utenze-manual-upload-r26.test.tsx \
  --maxWorkers=1 --no-file-parallelism --reporter=default --reporter=json \
  --outputFile.json="$OUT/focused.json"

VITEST_COVERAGE_INCLUDE='src/app/utenze/\[id\]/page.tsx' \
./node_modules/.bin/vitest run \
  tests/unit/campaign-utenze-detail-page.test.tsx \
  tests/unit/campaign-utenze-nas-r22.test.tsx \
  tests/unit/campaign-utenze-preview-r23.test.tsx \
  tests/unit/campaign-utenze-manual-upload-r26.test.tsx \
  --maxWorkers=1 --no-file-parallelism --reporter=default --reporter=json \
  --coverage --coverage.reporter=text --coverage.reporter=json \
  --coverage.reportsDirectory="$OUT/coverage" --outputFile.json="$OUT/union.json"

node /home/cbo/.cache/gaia-campaign/20261011-r26-governance/type-spec-project.cjs \
  "$PWD" tests/unit/campaign-utenze-manual-upload-r26.test.tsx \
  'src/app/utenze/[id]/page.tsx'
./node_modules/.bin/eslint tests/unit/campaign-utenze-manual-upload-r26.test.tsx --max-warnings=0
node "$OUT/audit.cjs"
sha256sum -c "$OUT/inputs.sha256"
```

Optional admitted ratchet runs from worktree root as
`make complexity-ratchet BASE_REF=main`; actual main resolves to55a, never an
alternate reference to manufacture PASS. No baseline-generation/repair command.

## Classification, risks and next slice

**CHARACTERIZED_ONLY / NO_CHANGE complexity.** Publication must remain test-only
plus review/governance documents. Runtime refactoring stays blocked until
genuine full-file100 and separate bounded responsibility admission.

Residual legacy risks remain repeat uploads on partial retry, late stale closure
effects after navigation/Escape, status races and busy keyboard selection. The
new tests deliberately preserve these rather than develop features. Public
mounted unit characterization is not complete stack/browser certification.
Global historicalFAIL30 and frozen Capacitas R25FAIL14 remain separate and are
not resolved or waived by this review. Full campaign remains ACTIVE/INCOMPLETE.

Recommended next action: Coordinator publishes this exact NEW frozen spec only
after integration review/ratchet, and allocates the next original Utenze
characterization responsibility to close remaining real page coverage. No
runtime admission, automatic subsequent hotspot or global completion granted.

## Terminal ratchet, auxiliary diagnostics and release

The optional native `make complexity-ratchet BASE_REF=main` completed0 without
retry. Direct read of its original JSON proves `base_ref: main`,
`baseline_commit: 55a1b1d35911451e018b662c2acc450bf5994ea2` and final
`findings: []`. Independent final `git merge-base HEAD main` is exactly55a.
This PASS does not waive whole-file coverage or accept any runtime candidate.

Two subsequent auxiliary attempts to summarize that log had reader defects:
the first selected the Make command's `${BASE_REF}` brace instead of JSON; the
second parsed correctly but asserted nonexistent `merge_base` instead of the
actual `baseline_commit` field. The second diagnostic is frozen as
`ratchet-audit.log`/`ratchet-audit.exit` (exit1), **not claimed PASS and not
rerun**. Source-backed inspection establishes these are metadata-reader errors,
not native scanner failures; the original make command/log/exit remain intact.
The separately prepared raw characterization/coverage auditor passed0 before
this optional metadata inspection and is not changed or substituted.

Final tracked runtime diff is empty, baseline/config/source/spec manifest all
OK, and untracked paths are only the imported frozen NEW spec and this report.
Protected main custody remains exact. No native process remains live; exclusive
heavy token RELEASED to the Coordinator. Report and private evidence are frozen
for independent Coordinator custody/integration, with no commit or publication.
