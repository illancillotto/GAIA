# R36 — Independent Presenze INAZ punch projection review

## Ownership

Reviewer owns only this NEW report and private `review-evidence/`; worktree
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r36-presenze-detail/review-worktree`,
branch `review/complexity-r36-presenze-detail`, initial HEAD
`c2ab91b0a885cec2fa8f9b421a90e46e58c6b51b`, actual main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`, initial status clean.
No reviewer runtime/test/config/baseline/shared-source write, native heavy gate,
commit, merge or push. Registry governs author activation separately.

## Status

TERMINAL READY_FOR_REVIEW / ACCEPTED IMPROVED for exact formatting-only V5.
Author native results independently audited below; no native gate rerun by
reviewer. Final verifier/root integration remain separate obligations. Reviewer
terminal manifest is produced AFTER this final report; no later rewrite allowed.

## Exact source binding

- Original page SHA256:
  `194686c9f2887ff8551289081e9c483023e0047692753a8f3b522429520a6111`.
- Accepted exterior V4 SHA256:
  `4b6eeef2ef330182b732adf7b4122183e9d43dc78cad53a89d9951c7e33dfe05`.
- V4 path: sibling `author-evidence/prospective-v4.tsx`.
- Applied author V5 SHA256:
  `deb4e9a072c1876a0fc67ca0398a727d06c826aaaadc104bc262f45211273cf8`.
  Independent `v5-binding.mjs`/log exit0 proves EXACT V4 minus its single last
  EOF newline, with actual author runtime byte-identical to V5. Therefore V4
  structural/domain/DOM proofs inherit without semantic change. Author V4
  diffcheck failure is retained separately; no native test had run on V4.
  Do NOT claim raw Babel File/Program AST byte equality across the removed LF:
  container end/loc metadata differs. Our own proof explicitly strips source
  location metadata for semantic comparison; author separately disclosed and
  corrected its raw-container assertion failure. No fabricated captured stderr
  or rerun of a successful native gate is used to establish equivalence.
- Existing fixture spec SHA256:
  `22e0cd481996f8024de5121daaf9bd268b52ac41aaf8738ec45055d8805cecdc`.

## Single responsibility

ONE INAZ punch detail projection/component. Request/anomaly cards, identity,
permissions, editor commands, refresh/polling and monthly summaries unchanged.
The real policy simplification shares each projected row's raw authorized
fallback/time resolution between sort and display, precomputes deterministic
sort keys once per row, and derives selected rows/copy/authorization once per
detail projection. A small hook-free typed domain component renders that model.
It is not acceptance of moving the original JSX alone: whole-file cognitive,
cyclomatic and normalized decision totals fall beyond a redistribution.

## Behavioral invariants and equivalence

- Real domain fields are JSON primitive values and ordinary arrays/objects:
  `frontend/src/types/api/presenze-base.ts:169`, API matrix/detail wrappers in
  `frontend/src/lib/api/presenze-people.ts:342`/`:384`, ordinary JSON decoder in
  `frontend/src/lib/api/core.ts:98`. No proxy/getter/reviver injection.
- Every successful helper operation is total for those declared nullable
  string/array fields: string normalization, terminal formatting, regex,
  numeric two-digit conversion, iteration and comparison have no external
  services, clock, await, mutation or application callback.
- Precomputing labels before sort commutes on that domain. Original sorting
  already copies rows; V4 maps to NEW row objects and sorts only the new array.
  Repeated internal call count/order is intentionally NOT preserved. This is
  observable-equivalence, not identical literal execution tracing, and does not
  certify malformed values or arbitrary effectful test stand-ins.
- Sort resolution: truthy punch time normalized directly; otherwise matching
  authorized direction may use first truthy paired time. No fallback gives the
  same empty sort time/MAX_SAFE_INTEGER. Minute order, direction E/U/other,
  lexical final tie-break, and stable equal-row ordering remain exact.
- Display: raw truthy whitespace time is retained then normalized, so a blank
  authorized annotation behaves exactly as before. Detail existing times are
  not annotated; paired existing authorized times are. Missing times may only
  borrow a matching paired authorized punch; otherwise dash. E-before-U request
  regex precedence and ACC matching remain unchanged. Display direction labels
  retain case-sensitive E/U behavior, distinct from normalized sorting.
- Selected projection still runs beneath `selectedRecord && editor`; component
  call sits at the original section location. No new hook/effect/dependency,
  memoization, callback or async boundary is introduced. Hook-free child produces
  no extra DOM wrapper and reevaluates on reconciliation using the same record.
- Auth-only zero-row section still shows authorization/heading without badge or
  row grid. Visibility, information copy, row count singular/plural, optional
  terminal block, classes, keys and order are unchanged. V4 preserves original
  numeric/space/row-label/space text-node segmentation rather than one count string.

## Independent static checks

`review-evidence/verify-projection.mjs` parses BOTH exact page sources. After
excluding only six removed punch helpers/six added punch helpers/two new types
and restoring the original punch section at the single new child call, the
WHOLE program AST is identical. All other imports, state, effects, dependencies,
handlers, permissions, modal surrounding JSX and request/anomaly UI are exact.
V3 and V4 diagnostics each exit0; their distinct source hashes are recorded.

The same source-bound script executes the actual isolated pure source functions
without mock helper returns against ordinary JSON DTO fixtures from the existing
spec (with currently required unrelated DTO fields filled). 24,624 finite
scenarios match visibility, authorization, information-copy policy, sorted
time/direction/terminal labels and input immutability. Includes null/empty/
whitespace time, normalized seconds, invalid time, E/U/other/whitespace direction,
terminal variants, request status/description variants, paired fallbacks and
empty/reversed detail cases. These are diagnostic supplements to actual mounted
tests, NOT coverage, exhaustive functional proof or a quality metric.

`verify-dom-v2.mjs` compares actual original/consequent and child-return JSX ASTs
after the source-proved pure projection substitutions. React JSX whitespace
normalization yields EXACT tag/attribute/class/key/condition/map topology and
text segmentation. Exit0 in `v4-dom-static-v2.log`.

The first comparator exit1 is retained in `verify-dom.mjs` and
`v4-dom-static.log`: standalone Babel `parseExpression` adds empty `errors:[]`
metadata absent from whole-program `parse`. The distinct corrective wrapper
SHA-binds the original script, ASSERTS every such errors array is empty and
removes only that parser metadata. No source/native-gate retry or ignored AST
logic change. No successful evidence has been rewritten.

## Test matrix

| Behavior | Existing mounted test | Missing / added | Result |
| --- | --- | --- | --- |
| Supervisor selected modal / permissions | page spec `renders the monthly matrix, opens the day modal and lets a supervisor validate only` | No test edit by reviewer | Author native PASS |
| Detail projection / normalization | page spec `uses detail punches when no paired punch exists and includes anomaly metadata` | No test edit by reviewer | Author native PASS |
| Identical paired/detail annotation | page spec `preserves identical paired/detail punches when authorization provides extra information` | No test edit by reviewer | Author native PASS |
| Missing authorized time / no invention | page spec `keeps missing authorized times without inventing a paired punch` | No test edit by reviewer | Author native PASS |
| Auth-only empty rows E/U | page spec parameterized `shows an authorized %s punch without inventing missing INAZ rows` | No test edit by reviewer | Author native PASS |
| Chronology, equal-key stability and direction priorities | page spec chronological scenario and `orders equal-time equal-direction punch rows stably and preserves missing directions` | No test edit by reviewer | Author native PASS |
| Paired copy / row count / terminal labels | page spec paired/detail duplication scenario | V4 keeps original text nodes | Author native PASS |
| Load/refresh errors, polling, cleanup, navigation | Existing seven page specs and whole-AST equality | Specs/configs unchanged | Author native PASS |

## Metric before / after / delta

Source-bound exterior before/V4 scanner values independently summed and
subsequently confirmed by actual whole native V5 report:

| Metric | Before | V4 | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive | 367 | 360 | -7 |
| Principal cyclomatic | 323 | 316 | -7 |
| Principal LOC | 1988 | 1945 | -43 |
| Whole-file cognitive SUM | 1062 | 1048 | -14 |
| Whole-file cyclomatic SUM | 1201 | 1191 | -10 |
| Whole-file normalized decisions (SUM cyc-1) | 892 | 883 | -9 |
| File effective LOC | 2809 | 2803 | -6 |
| Callables | 309 | 308 | -1 |
| useState / useEffect | 21 / 13 | 21 / 13 | 0 / 0 |

Six new named helpers respectively cognitive/cyclomatic/LOC:
resolveInazPunchTime 6/6/5; formatProjectedInazTime 9/7/7;
projectInazPunchRow 4/5/14; compareInazPunchRows 2/3/7;
buildInazPunchDetail 4/5/14; InazPunchDetail 5/6/46.
All below warning thresholds; nesting<=1 and parameters<=3. Actual native
whole-report and authoritative merge-base ratchet corroborate these values and
confirm no transferred violation. All1672other runtime metric maps/callables exact.

## Rejected diagnostics

V1 had a prospective new warning; V2 was too small on principal AND contains a
real exterior regression: double-escaped time regex stops matching real HH:MM,
so direction priority reverses chronological rows. Rejected V2 source SHA256
`00fe357ed12075e8cb7a3152a81dbe49682bbbca453946bdcf681d05e659f680` remains intact.
`v2-regex-static-proof.mjs` SHA-binds and extracts that literal from source:
original U05:30/E10:03 order becomes E10:03/U05:30 in V2. Assertion proof exit0.
This is a rejected proposal, NOT a regression admitted into runtime or campaign.
V3 fixed regex and editor guard; V4 also restores original count text segmentation.

## Native gates, coverage and ratchet

Reviewer executes NO native UI/lint/type/report/ratchet gate. Coordinator reports
fresh original496/full100/provenance cleared; this is attributed to Coordinator.
Independent `native-raw-audit.mjs`/log exit0 inspects actual author raw source,
test outputs/maps, native gate exits, report and main/protected-file custody:

-496native persisted passed assertions across seven exact original specs;
  success true, zero failed/pending/todo, all assertion statuses passed.
- Full-file statements1040/1040, branches1106/1106, functions306/306 and
  lines853/853 all100. Full map/counter keys exactly aligned, each branch arm
  matches its location denominator, every counter positive/finite, no skip.
- Types/lint/report/actual main55a ratchet/custody/diffcheck/launch native0.
  Ratchet standalone JSON entire payload parsed after EXACT Make command echo,
  actual base main/55a/findings[], page present in changed_files.
-3659protected tracked SHA exact including old tests/configs/baseline/shared
  inputs; main HEAD/diff/status custody exact. All1672other metrics unchanged.
  Principal360/316/1945, file1048/1191/2803, six new helpers violations[].
- Original supplemental auditor exit1 remains preserved: naive first opening
  brace mistakenly captured Make shell expansion. Distinct author strict audit0
  reuses native outputs without rerun; reviewer independently parses the entire
  payload. Two positive/fifteen negative parser countertests pass; they reject
  wrong echo/base/commit, malformed/extra/trailing JSON, findings and bad schema.

Author terminal report SHA256
`fcca243bc603551fdf12ba160b5c249b6f5a62ee0118612fe042740b0950add4` reviewed;
author manifest SHA256
`74c0a461a90406c9b8701f7c1ae62de9fdac61609b262a6560184761c3754572`
independently rehashed82members/zero errors by `author-freeze-audit.mjs`/log.
Status TERMINAL_READY_FOR_REVIEW/token RELEASED, exact V5source. No author live
evidence rewritten by reviewer. Independent final verifier remains active;
this review certifies author evidence only, not an unrun separate final gate.
No threshold/baseline/config/exclusion change is authorized or required.

## Classification and remaining risk

ACCEPTED IMPROVED: real shared policy elimination + principal−7 cognitive,
whole-file−14 cognitive/−9 decisions, full-file100 and actual ratchetPASS, no
transferred findings, exact V5 source. Principal360 remains extreme,
useState21/useEffect13 unchanged; this slice
does not reach Wave1 strategic target or finish the campaign. Finite differential
diagnostics cannot certify UI lifecycle/native coverage; immutable actual mounted
suite and final verifier are required. Stop after this responsibility.

## Files changed / commit

Reviewer only: this NEW report and private diagnostic evidence. No commit.
Candidate not applied by reviewer. No shared source ownership taken.
