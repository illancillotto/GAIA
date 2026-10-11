# R36 — Independent Final Verification

## Ownership

Verifier owns this NEW report and the exact admitted-source installation solely
for verification in `final-worktree`, branch
`verify/complexity-r36-presenze-detail`, under
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r36-presenze-detail`.
Base HEAD `c2ab91b0a885cec2fa8f9b421a90e46e58c6b51b`; actual main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Registry read before action;
dedicated tree originally clean. No agent commit, merge, push or main edit.

## Exact source binding

- Original page SHA256:
  `194686c9f2887ff8551289081e9c483023e0047692753a8f3b522429520a6111`.
- Candidate V5 SHA256:
  `deb4e9a072c1876a0fc67ca0398a727d06c826aaaadc104bc262f45211273cf8`.
- Target: `frontend/src/app/presenze/giornaliere/page.tsx` only. Candidate
  installed with `apply_patch` after fresh independent original gates and
  Coordinator native-token grant; final installed bytes match exactly.
- V5 differs from statically accepted V4 only by removal of one trailing LF.
  No original test, setup, coverage configuration, baseline, threshold, ignore,
  shared runtime or other application source changed.

## Single responsibility and invariants

Only the selected daily INAZ punch projection: detail-vs-paired choice,
authorized-time fallback and annotation, normalized chronological sort keys,
presentation labels and its compact hook-free domain child. Shared computation
removes repeated policy, rather than merely moving JSX. Request/anomaly UI,
APIs, authorization, identity, surrounding modal, state/effects/dependencies,
handlers, lifecycle and async boundaries are outside the slice.

Existing mounted tests exercise the real page with JSON DTO API fixtures, not
mocked internal projection results. Independent reviewer source/whole-AST/JSX
equivalence supplements native gates; it is not coverage or exhaustive proof.
Pure internal invocation counts/order intentionally change. Observable
equivalence applies to declared JSON primitive/array DTOs, not arbitrary
effectful getters/proxies or invalid DTO types. Stable sort priorities, fallback
limits, terminal formatting, classes/keys and badge text segmentation remain
preserved by exact-source review and mounted scenarios.

## Characterization matrix

| Behavior | Existing test | Missing / Added | Result |
| --- | --- | --- | --- |
| Supervisor modal and validation permissions | page: `renders the monthly matrix, opens the day modal and lets a supervisor validate only` | None / none | PASS before and after |
| Detail rows, normalization, anomaly surroundings | page: `uses detail punches when no paired punch exists and includes anomaly metadata` | None / none | PASS before and after |
| Authorized E/U fallback and annotations | regressions: `renders detail punch times, authorization and stable direction ordering` cases | None / none | PASS before and after |
| Missing times without invented paired rows | page: `keeps missing authorized times without inventing a paired punch` | None / none | PASS before and after |
| Auth-only section without detail rows | page: `shows an authorized %s punch without inventing missing INAZ rows` | None / none | PASS before and after |
| Chronology and stable equal-key ordering | page: chronological detail test and `orders equal-time equal-direction punch rows stably and preserves missing directions` | None / none | PASS before and after |
| Paired copy, row count and terminal formatting | page: `keeps the Inaz detail section for authorized punches even when detail rows are redundant`; regressions boundary cases | None / none | PASS before and after |
| Loading, refresh, failures, navigation, polling/cleanup | Existing seven whole-page specs | None / none; unchanged AST | PASS before and after |

## Native tests and coverage

One independent original invocation and one candidate invocation, serialized
after author token release. Both **496/496 PASS**, zero failure, pending,
todo/skipped assertion status; all seven expected specs present and every
assertion passed. Native logs contain no unhandled/error/failure diagnostic.
No retry, filtering of test cases, added test, policy/configuration change or
new exclusion. Exact command from `frontend/`:

```bash
VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx \
./node_modules/.bin/vitest run \
tests/unit/presenze-giornaliere-{page,regressions,r6,r7,r8,r9,summary-r26}.test.tsx \
--maxWorkers=1 --coverage --reporter=json \
--outputFile=<phase>-tests.json --coverage.reportsDirectory=<phase>-coverage
```

| Full-file dimension | Original covered / total | Candidate covered / total | Coverage |
| --- | ---: | ---: | ---: |
| Statements | 1041 / 1041 | 1040 / 1040 | 100% / 100% |
| Branch arms | 1119 / 1119 | 1106 / 1106 | 100% / 100% |
| Functions | 307 / 307 | 306 / 306 | 100% / 100% |
| Lines | 854 / 854 | 853 / 853 | 100% / 100% |

Audited raw coverage contains exactly the full modified page; every statement,
function and branch-arm counter is positive, counter/map keys agree, zero
skipped maps and all four Istanbul dimensions total=covered with skipped=0.
Denominators change with the admitted source, not through narrowing coverage.

## Metrics

Fresh whole-repository native reports before/after, no parse/exception errors.
Original report exact matches Coordinator fresh original. Every other runtime
file metric and callable/finding object is unchanged (1672 other files).

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive | 367 | 360 | -7 |
| Principal cyclomatic | 323 | 316 | -7 |
| Principal effective LOC | 1988 | 1945 | -43 |
| Principal nesting / params | 2 / 0 | 2 / 0 | 0 / 0 |
| File cognitive SUM | 1062 | 1048 | -14 |
| File cyclomatic SUM | 1201 | 1191 | -10 |
| File normalized decisions SUM(cyclomatic-1) | 892 | 883 | -9 |
| File effective LOC | 2809 | 2803 | -6 |
| File callable count | 309 | 308 | -1 |
| useState / useEffect | 21 / 13 | 21 / 13 | 0 / 0 |
| Global callables | 20324 | 20323 | -1 |
| Global errors | 1922 | 1922 | 0 |
| Global warnings | 2741 | 2739 | -2 |
| Global findings | 4663 | 4661 | -2 |

Global files remain 1673; findings overlap and are not independent problems.
All six added named helpers/components have zero finding. Their
cognitive/cyclomatic/LOC/nesting/params are respectively:
`resolveInazPunchTime` 6/6/5/1/2;
`formatProjectedInazTime` 9/7/7/1/3;
`projectInazPunchRow` 4/5/14/0/2;
`compareInazPunchRows` 2/3/7/1/2;
`buildInazPunchDetail` 4/5/14/0/1;
`InazPunchDetail` 5/6/46/1/1.
Aggregate normalized decisions genuinely fall; no transferred hotspot.

## Other gates

- `npm run typecheck -- --incremental false`: exit0, whole configured
  application typecheck, no emit or incremental metadata writes.
- `./node_modules/.bin/next lint --file src/app/presenze/giornaliere/page.tsx`:
  exit0. Three warnings remain: unchanged unused loading state and two unchanged
  effect dependencies. Next lint deprecation notice is retained. No lint ignore.
- `make complexity-report REPORT_JSON=<phase>-complexity.json
  REPORT_MD=<phase>-complexity.md`: original0/candidate0, full official scope.
- `make complexity-ratchet BASE_REF=main`: exit0, exact actual main55a
  baseline binding, `findings: []`. Strict parser verifies the complete expected
  Make echo prefix and parses the full remaining JSON; no first-brace heuristic.
- `git diff --check`: original0/candidate0.
- Complete raw/source/metrics/custody audits: original0/candidate0.

## Custody

All **3660** tracked original paths captured before native work; original audit
verifies all3660 exact, candidate verifies **3659** nonowned tracked files exact.
Candidate page hash separately bound; HEAD and actual merge-base unchanged.
Main concurrent HEAD, binary diff hash and status hash unchanged. Existing seven
specs, baseline, thresholds, exceptions, tooling and shared files included in
this custody, not trusted from a narrow selected list. Only runtime diff is
the exact page (101 added / 105 removed text lines), plus this NEW verifier
report. No branch integration performed by verifier.

## Diagnostics

`final-evidence/TOOL_DIAGNOSTICS.md` preserves two pre-native invalid observation
calls (`cell_id=none`) and one malformed Git-header transport patch. All failed
before any native gate/source edit. Distinct unnumbered-hunk `apply_patch`
installation followed exact original-source revalidation. These are tool
transport/observation mistakes, not product/test failures; none erased or
silently counted PASS. Original and candidate native gates each run once.

Author's separate metadata-parser failure/recovery is not replaced by this
verification; independent auditor uses strict Make prefix/fullJSON parsing.
Reviewer metadata diagnostics and rejected exterior proposals remain separate.

## Classification

**IMPROVED / READY_FOR_REVIEW** for this coherent admitted responsibility:
principal and aggregate cognitive/decision/LOC reductions, no new finding,
full-file100 and mounted behavior preserved by available evidence. No claim of
P1 >=50% completion: principal360 remains extreme. No global campaign completion.

## Limits and next action

No frontend build, stack E2E, broad backend/frontend/worker suite,
`complexity-check` or Graphify invoked by verifier: these are Coordinator
integration/global obligations. Historical baseline30, R25 matcher and other
coverage blockers remain separate/unresolved. Real stack integration is not
proved by mounted unit tests. Coordinator must review/import exact admitted
bytes, perform its own integration checkpoint and required Graphify update.
Stop after this responsibility; no second hotspot or new test scope admitted.

## Evidence / commit

Private `final-evidence/`: one-shot `gates.sh`, `audit.cjs`, custody snapshot,
original/candidate tests JSON/log/argv/exits, raw coverage and HTML/Cobertura,
whole complexity JSON/Markdown, types/lint/ratchet/diffcheck logs, audits,
source binding and retained tool diagnostics. Terminal manifest created only
after this final report/source binding; no evidence rewrite after freeze.
Commit: NONE (Verifier). Native token released at terminal.
