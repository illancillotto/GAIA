# R36 AUTHOR — Presenze INAZ Punch Detail Complexity Slice Report

## Ownership

Initially only this NEW report and private sibling author-evidence writable;
Coordinator later admitted exclusive exact punch projection in the page.
Worktree author-worktree, branch refactor/complexity-r36-presenze-detail.
HEAD c2ab91b0a885cec2fa8f9b421a90e46e58c6b51b; actual main/merge-base55a1b1d35911451e018b662c2acc450bf5994ea2.
Original page SHA194686c9f2887ff8551289081e9c483023e0047692753a8f3b522429520a6111.
Final page SHAdeb4e9a072c1876a0fc67ca0398a727d06c826aaaadc104bc262f45211273cf8.
Runtime page admitted/applied via apply_patch; all existing tests/configs intact;
commits NONE. Independent static reviewer accepted exact V4 and V5 EOF binding.

## Baseline

Installed authoritative js_ast_metrics.mjs from integration scans exact original/exterior sources.
before.json: principal367cognitive323cyclomatic1988LOC/nesting2/params0.
Whole page1062cognitiveSUM1201cyclomaticSUM2809LOC309callables21state13effect.
Normalized decisions = SUM(cyclomatic−1)=892.

## Target callable and single responsibility

Daily INAZ punch detail ONLY; request/anomaly/editing sections excluded.
A real selected-record projection chooses detail-vs-paired source once, computes
normalized/resolved times for both sorting and display, retains authorization,
stable order and terminal presentation. Small domain-specific InazPunchDetail
component invokes projection INSIDE original selectedRecord&&editor modal gate.

This is not merely a JSX relocation: old sorting/display separately resolve the
same missing-time authorization fallback; V3 resolves once and removes duplicate
policy decisions. Repeated array derivation/terminal formatting also disappears.

## Behavioral invariants

- DTO fields are plain typed JSON values, arrays and records, not effectful mocks.
- Original selectedRecord&&editor mount gate unchanged; no modal-independent eager reads.
- No API/state/effect/dependency/event/permission/auth/identity/date modification.
- Selection retains existing shouldShowDetailPunchRows policy byte-for-byte.
- Detail-vs-paired comparison is original index-sensitive normalized tuple policy.
- Own truthy time wins; missing time uses first matching authorized paired time only.
- Existing own time annotated ONLY paired-source+authorized direction.
- Missing matching authorized time annotated when actual paired fallback exists.
- Time parsing keeps /^\\d{2}:\\d{2}$/ semantics; actual V3 source literal matches original.
- Direction display stays case-sensitive E/U; sorting/fallback normalizes trim+upper.
- Comparator minutes→E/U/other priority→localeCompare identical; native stable sort.
- Projection maps fresh rows before sorting, never mutates input arrays.
- Auth-only zero rows keeps section/label, no count or rows.
- Identical DOM/tag/classes/text/key strings, record-id/index row keys, row order.
- Literal pure helper call order not claimed identical; observable JSON output and DOM are the contract.
- Eager per-row calculation inside child remains total for genuine typed DTO strings/null:
  regex/trim/format/pure lookup/number arithmetic only. No new external calls.

## Characterization tests

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Detail/pair equivalence, normalized time, E/U fallback | giornaliere-page renders detail punch times / preserves identical paired-detail | none | none | Original496PASS and candidate496PASS |
| Stable equal keys / missing direction | giornaliere-regressions orders equal-time equal-direction rows | none | none | Candidate496PASS/full-file100 |
| No paired authorized fallback | giornaliere-regressions keeps missing authorized times | none | none | Candidate496PASS/full-file100 |
| Auth-only empty section and hidden count | giornaliere-regressions shows authorized E/U without inventing rows | none | none | Candidate496PASS/full-file100 |
| Exact chronological priority vs direction case | existing tests cover time/direction; exterior cross-product supplements proof | none identified | none | Candidate496PASS plus finite source proof |
| Full-page existing state/mutations/modals | original seven-spec suite | none | none | Candidate496PASS/full-file100 |

## Exterior changes and rejected diagnostics

prospective.tsx V1: no runtime writes; project helper cyclomatic14 warning,
principal only−1. REJECTED design.

prospective-v2.tsx SHA00fe357ed12075e8cb7a3152a81dbe49682bbbca453946bdcf681d05e659f680:
small helpers but principal only−1; reviewer found incorrectly double-escaped
time-match regex and selected-record-only eager computation bypassing editor gate.
REJECTED, retained unchanged; not a runtime regression.

prospective-v3.tsx SHA13a2122795fab2ede8b4d78c0d024a035ffd4dbacaa3afce6879801081eedfd9:
correct genuine regex; no parent eager projection; small child inside original gate.
Independent reviewer found V3 countLabel merged the original JSX text-node
segmentation (visible text unchanged). V3 retained as diagnostic, NOT admitted.

prospective-v4.tsx SHA4b6eeef2ef330182b732adf7b4122183e9d43dc78cad53a89d9951c7e33dfe05:
same source as V3 except projection provides rowLabel and original child numeric,
space, plural-label, space text nodes are retained. Same metrics as V3 below.
V4 independently STATIC ACCEPTED and admitted. Exact application exposed a
single extra blank line at EOF; preflight diffcheck exit2 retained. Coordinator
authorized DISTINCT V5 removing ONLY one trailing LF, no other byte change.
V5 SHAdeb4e9a072c1876a0fc67ca0398a727d06c826aaaadc104bc262f45211273cf8.
Full Program.body AST byte-for-byte structurally equal with positional metadata
retained; whole semantic AST equal excluding only start/end/loc metadata.
Installed complete scanner JSON V4/V5 byte-identical; reviewer accepted binding.

## Metric before / native after / delta

| Metric | Before | Native V5 after | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive |367|360|−7|
| Principal cyclomatic |323|316|−7|
| Principal LOC |1988|1945|−43|
| File cognitiveSUM |1062|1048|−14|
| File cyclomaticSUM |1201|1191|−10|
| File effective LOC |2809|2803|−6|
| Callable count |309|308|−1|
| Normalized decision count |892|883|−9|
| useState/useEffect |21/13|21/13|0|

New callable cognitive/cyclomatic/LOC/nesting/params:
resolveInazPunchTime6/6/5/1/2;
formatProjectedInazTime9/7/7/1/3;
projectInazPunchRow4/5/14/0/2;
compareInazPunchRows2/3/7/1/2;
buildInazPunchDetail4/5/14/0/1;
InazPunchDetail5/6/46/1/1.
All below warning thresholds. Native whole report confirms these metrics and
all1672other files/callables unchanged. Old displayedInazPunchTimeLabel19cognitive/
12cyclomatic warning disappears, not transferred. Small modest slice, not
achievement of strategic extreme-tail target.

## Tests / Coverage / Ratchet

Coordinator fresh ORIGINAL496tests/four-dimension100 completed before runtime
admission; original native outputs not rerun by author. Author's one-shot V5
candidate native session63584 TERMINAL0, token RELEASED. Seven unchanged specs:
presenze-giornaliere-{page,regressions,r6,r7,r8,r9,summary-r26}.test.tsx.
496PASS/zero failed/pending/todo; raw assertion maps all passed, no skip.

Native full-page V8/istanbul maps, all counters positive/no mapping skip:
1040/1040statements,1106/1106branches,306/306functions,853/853lines all100.
All gates executed ONCE with persisted argv/log/exit:
- Vitest same seven specs --maxWorkers=1 --coverage; exact owned full-file include.
- npm run typecheck -- --incremental false:0.
- next lint --file src/app/presenze/giornaliere/page.tsx:0.
- make complexity-report to private candidate JSON/MD:0.
- make complexity-ratchet BASE_REF=main:0, actualmain55a/findings[].
- sha256sum -c inputs.sha256:3659protected tracked inputs exact.
- final git diff --check:0; full launch0.

Main concurrent HEAD/diff/status and all1672other source metric maps exact.
Global native1673files20323callables1922errors2739warnings4661observations;
versus original1673/20324/1922/2741/4663:two warning observations removed,
not two independent issues. No baseline/scope/threshold/config/exclusion/ignore
changes; no new tests necessary for existing full-file native100.

Diagnostics and corrected static audits preserved, no gate retry:
- V4 preflight blank EOF fail2 retained; DISTINCT authorized V5 removes one LF.
- Initial raw File-AST EOF proof failed due File/Program end+loc metadata only.
  Prior fullrawASTequal claim retracted immediately; failed original script and
  empty stdout retained, stderr only truncated tool output honestly disclosed.
  Distinct normalized proof0 plus independent reviewer exact-byte proof0.
- Initial supplemental audit1 misparsed Make echo shell expansion opening brace;
  overall initial audit FAIL despite earlier assertions. Original script/log/exit
  untouched. DISTINCT strict auditor0 reads existing native outputs only: exact
  single Make command prefix plus entire JSON, actualmain55a/findings[],2positive/
  15negative parser countertests0. Native tests/report/ratchet never rerun.

Exterior source differential: source-differential.cjs extracts exact named
pure declarations via installed Babel, transpiles only types via installed TS,
executes original and V3 isolated VMs. 36,750 combinations of time/direction/
terminal/status/authorization/source-mode => zero projection mismatches and
zero input mutations. JSON SHA484a27d5a2ad615d3953b36459c01f54de03d9311b91169ad56c2d144ed79cd9.
V4 distinct source-differential-v4.cjs/JSON independently compares the new
rowLabel contract on the same36,750 matrix, zero mismatches/mutations. This
distinct diagnostic preserves V3 results, no native gate rerun.
This is supplementary finite source evidence, NOT native UI test/coverage gate
and NOT exhaustive proof of every possible DTO.

## Classification

IMPROVED: target cognitive−7 and whole file cognitive−14/decisions−9, no transferred
warning and full-file100/ratchetPASS. This is a modest local slice, NOT achievement
of strategic extreme-tail target or certification of complete global campaign.
Root integration/independent final verification remain Coordinator obligations.

## Files changed / Commit

Modified owned page only plus NEW this report; private diagnostics/native proofs.
Existing test/config/baseline/shared files unchanged; no commit/import/merge.

## Residual risks

Independent reviewer exact-source projection/DOM/key/totality accepted; author's
full100 native results require separate final verifier/root admission before integration.
Global campaign incomplete; principal still360 (>300), unrelated
historical divergence/provenance and final suites remain separate.

## Recommended next slice

Do not begin another slice or rerun any successful gate. Await Coordinator
independent final verification/integration of exact V5 after terminal evidence freeze.
