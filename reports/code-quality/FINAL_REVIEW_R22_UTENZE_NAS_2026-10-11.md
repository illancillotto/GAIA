# Independent final review R22 — Utenze NAS characterization

Verdict: **ACCEPT_CHARACTERIZATION_ONLY**. The new mounted characterization spec is acceptable for coordinator-controlled test-only integration. Runtime remains **BLOCKED_COVERAGE**; this review grants no runtime acceptance, 100% waiver or complexity reduction credit. Classification: **CHARACTERIZED_ONLY / NO_CHANGE complexity**. The original campaign remains **ACTIVE/INCOMPLETE**.

## Review allocation and immutable inputs

Reviewed independently in `/home/cbo/CursorProjects/GAIA-campaign-20261011-r22-utenze-nas-review`, branch `review/complexity-r22-utenze-nas`, HEAD `31436fc89e73d35fc4e6e7969441a7d8ba427bb2`, merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`. Assignment and R22 ownership registry were read before activation. Author was terminal/released; this reviewer alone held exclusive heavy execution. No agent spawning, runtime/test edits, commit, install, build or cleanup.

| Input | SHA-256 |
| --- | --- |
| Actual `frontend/src/app/utenze/[id]/page.tsx` | `b0f822daf809b0744b912f0f159a2e833c556dda289466b6ed45329a79e3d6b1` |
| Immutable existing 21-test `campaign-utenze-detail-page.test.tsx` | `79ef301017ee78985d71b468300eba3239e901c9773eb56f60a033cd6ad13f98` |
| Root-imported new 45-test `campaign-utenze-nas-r22.test.tsx` | `8f2258e4cb65b2242ac65fc39a1407fad9a6a48457060387ef7392e39c0ed6d9` |
| Author `CHARACTERIZATION_R22_UTENZE_NAS_2026-10-11.md` | `95402c0a8c600d7837719b94b8a44ac5b37af55a2d22831c71486f0dbfdc3089` |
| Immutable merge-base/current complexity baseline | `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95` |

Reviewer writes are limited to this new report and new private evidence under `/home/cbo/.cache/gaia-campaign/20261011-r22-utenze-nas-review/`. All source, specs, configuration, baseline and prior reports/evidence stayed read-only.

## Independent assertion and behavior assessment

The complete new spec and relevant actual page handlers, effects, eligibility and NAS controls were reviewed against existing tests and the author matrix. Tests import and mount the actual exported page, drive visible buttons/inputs/radio controls, and assert literal token/id, payload, request trace, busy controls, messages and current DOM. API-boundary mocks retain the real API module via `importOriginal`; unrelated child cards/layout/navigation/storage are isolated. No copied orchestration, handler extraction, source-string tests, fake coverage or runtime modification was found. No tests are skipped or weakened.

The real `ProtectedPage` module remains active. New scenarios enter via the actual module gate with `enabled_modules: ["utenze"]`, viewer role and empty granted keys. Existing immutable tests independently retain anonymous redirect and module-denied no-subject-call assertions. This is preserved characterization, not new authorization policy.

Meaningful behaviors covered by fresh native assertions:

- Status begins after subject resolution; subject remains visible during status loading/failure. Eligibility follows `can_import_from_nas` and positive pending count; missing-in-NAS is not an independent suppression condition. Edit/read-only/tab controls follow existing UI behavior.
- Header and status-card import send only the literal token/id, ignore unsaved input as an import argument, disable import controls during work, refresh the subject and preserve native **import → reload → explicit status → effect status** order. Reverse completion proves the older explicit response can overwrite the newer effect result.
- Import rejection prevents reload/status; successful server import followed by reload rejection exposes partial failure. Status errors are absorbed after import/save and their success message remains visible. Same-object reload avoids an extra effect request.
- Candidate search retains API ordering without score sorting or review filtering, chooses only the first candidate when initiating selection was empty, keeps existing paths, supports radio/custom paths, preserves old list/path after errors, and demonstrates captured selection versus edits during pending search.
- Save asserts exact selected/custom path and candidate/subject/null letter fallback, empty-path no-call validation, independent busy controls, subject-response hydration overwriting edits, retained edit/list state on update errors and **save → explicit status → effect status** order. Scalar status busy clears when one request completes while the other remains pending.
- Message clearing/preservation, overlapping candidate search/save and same mounted route id changes preserve current behavior. A late subject-1 status can overwrite subject-2 UI while the next import correctly addresses subject-2.

Null pending count, empty first candidate path and verbatim whitespace path are explicitly labeled boundary characterization. They do not establish API validation or desired business behavior. Fixtures do not normalize legacy races.

Residual optional NAS cases remain disclosed: not all mixed success/failure permutations of duplicate status requests; late old-subject GET overwriting the newer subject; duplicate-path candidate data; candidate identifier display branches for `partita_iva` and unavailable identifier. The route case proves late old status only. These omissions prevent exhaustive NAS/full-page certification but do not invalidate this coherent characterization unit.

## Fresh native verification — one attempt per gate

Every command, native log, exit and test JSON was newly generated in the reviewer private directory. Author logs were not substituted for fresh execution. `review.py` serializes gates and stops on any unexpected result. None occurred in the allocated native gates. A later read-only supplemental JSON reader returned exit 1 because it selected a brace in Make's echoed shell command instead of the JSON object. That auxiliary diagnostic is retained in `supplemental-json-reader.*`; it did not modify inputs, fail a native gate or cause a retry. Native Make log directly records the exact baseline commit and `findings: []`.

| Gate / evidence stem | Result |
| --- | --- |
| `union`: Vitest exact old/new spec paths, `--maxWorkers=1 --no-file-parallelism`, default + JSON reporter | Native exit 0; two specs, old 21 + new 45 = **66/66 PASS**, zero failed/pending/todo |
| `coverage-union`: same union, actual original full page, text + JSON coverage | **66/66 PASS**, native exit **1**, solely four unchanged global 100% threshold errors |
| `project-types`: `npm run typecheck -- --incremental false` | Native exit 0 |
| `new-spec-types`: actual project compiler options, roots new spec/next-env/jest-dom Vitest declaration, noEmit and incremental false | Native exit 0; **95 actual runtime imports, 0 diagnostics**, actual page present |
| `new-spec-lint`: `eslint tests/unit/campaign-utenze-nas-r22.test.tsx --max-warnings=0` | Native exit 0 |
| `native55a`: actual `make complexity-ratchet BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2 QUALITY_PYTHON=backend/.venv/bin/python` | Native exit 0; actual immutable baseline commit; **findings: []** |

Coverage include was exactly `src/app/utenze/\[id\]/page.tsx`. Reporters changed output format only: no threshold override, source exclusion or reduced line scope. Raw JSON contains exactly one absolute actual `[id]/page.tsx` key and matching internal path, nonempty statement/branch/function maps and positive counters. All map entries and covered/missing locations independently match frozen author native results. No synthetic skip metadata exists. `coverage-audit.json` retains every missing statement/function/branch and uncovered line; `coverage-region-audit.json` independently records region hits and map binding.

| Full original file dimension | Covered / total | Native percentage | Missing | Required |
| --- | ---: | ---: | ---: | ---: |
| Statements | 253 / 576 | 43.92% | 323 | 100% |
| Branch arms | 273 / 610 | 44.75% | 337 | 100% |
| Functions | 49 / 176 | 27.84% | 127 | 100% |
| Lines | 251 / 536 | 46.82% | 285 | 100% |

The original old-spec-only evidence was 209/576 statements, 229/610 branches, 36/176 functions and 208/536 lines. New characterization adds 44 statements, 44 branch arms, 13 functions and 43 lines, without changing denominators. This improvement in characterization coverage is not runtime readiness or complexity reduction.

Status/import/candidate/save bodies have positive real execution and fully covered body statements/arms; effect and quick eligibility are covered. The override retains two missing identifier arms; header manual-upload callback is outside this responsibility. Whole-file gaps include document grouping, ANPR/visura, personal-save branches, classification, upload/delete, previews/cleanup, document filtering and controls, manual upload UI, personal fields, Catasto and audit/metadata. Full-file FAIL100 remains explicit and blocking for runtime refactoring.

## Full context, custody and unchanged complexity

Before any native gate, all **1,673** paths from the frozen official R21 report were independently present and byte-exact to integration and the reviewer Git index, including worker tests. Reviewer tracked manifest has **2,643** hydrated files; **942** absent tracked paths carry authorized skip-worktree flags and are outside that complete official scanner set. Sparse checkout omitted unrelated assets/docs only and did not change scanner configuration/exclusions. The Make ratchet used the complete runtime context, not a partial scanner gate.

Custody snapshots before, immediately before ratchet and after all gates are exactly equal: all hydrated tracked source/config/spec bytes, author spec/report/private evidence, baseline and main are preserved. Main's **3,341** tracked-file manifest and existing changes are unchanged; binary diff SHA-256 remains `9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`, status SHA-256 remains `0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`.

All **124** entries of the previous R21 `FINAL-evidence-sha256.json` were independently revalidated; all prior R21 private files and current frozen author evidence remain unchanged. Prior final report remains SHA-256 `83c3d8e2667f49428300ecb96475ca1dec5621ece14e3cfa94094a75646a129d`. Combined frozen custody covers 165 files. No source/config/baseline edits or baseline regeneration.

No new whole-repository report was needed: runtime scanner inputs are exact and unchanged against the frozen official report, with fresh authoritative global Make ratchet proof. Metrics remain:

| Unit | Before = after cognitive | Before = after cyclomatic | Before = after effective LOC |
| --- | ---: | ---: | ---: |
| `DetailContent` | 391 | 304 | 1908 |
| Whole page | 729 | 723 | 2118 |
| Four NAS command/status callables, aggregate | 18 | 17 | 74 |

Whole page still has 176 callables; official 28 `useState` / 10 `useEffect` remains distinct from supplemental raw AST 50 useState calls. Global frozen inventory remains 1,673 files / 20,322 callables / 1,925 errors / 2,741 warnings / 4,666 records; five >300, seventeen >200, fifty-five >100 remain. Historical global finding 30 is not replaced by this characterization review.

Disk was checked before ratchet (341,106,688 available bytes) and remains bounded; text/JSON only, no HTML/dependency copies. Runtime structure/routing/services/workflows did not change. No Graphify refresh was delegated or performed; coordinator retains publication/governance and any integration Graphify obligations.

## Closure

**ACCEPT_CHARACTERIZATION_ONLY** for this exact new spec. Runtime is **BLOCKED_COVERAGE**, classification **CHARACTERIZED_ONLY / NO_CHANGE**, campaign **ACTIVE/INCOMPLETE**. Fresh full application suites are not claimed. No IMPROVED designation or global completion.

Report and private evidence are frozen by new SHA-256 manifest/terminal custody artifacts. Reviewer **STOP / HEAVY RELEASED**; coordinator alone controls test-only integration/publication. No further responsibility or runtime refactor is authorized by this verdict.
