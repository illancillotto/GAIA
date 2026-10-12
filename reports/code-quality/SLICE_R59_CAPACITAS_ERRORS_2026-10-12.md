# R59 — Capacitas Operation Errors Complexity Slice Report

## Ownership and snapshot

Dedicated author/reviewer/verifier branches and worktrees, registered before
delegation. HEAD114fbf7196382c6446a7963c34bd89e4c9795ef5, authoritative
main/merge-base55a1b1d35911451e018b662c2acc450bf5994ea2. Main concurrent work
preserved. No commit, push, Git merge, baseline/scope/threshold/ignore change.

SSD evidence root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261012-r59-capacitas-errors`.
Registry `docs/code-quality/MULTI_AGENT_OWNERSHIP_R59_CAPACITAS_ERRORS_2026-10-12.md`.

## Baseline and target callable

Admitted workspace92a5e1e2: principal298cognitive275cyclomatic2398LOC;
file762cognitive906cyclomatic3108LOC253callables31useState2useEffect.
Baseline38e6/matcher32b exact. One responsibility: fixed-fallback error
feedback across twelve credential/command/parser/refetch/anomaly catches.

## Behavioral invariants

Only Error identity selects .message, read once, including empty strings;
non-Error .message getters stay unread. Same fallback literals/setters/order,
auth classification, catch/finally, API/payloads, rows, cleanup, polling and
React state/effect boundaries. Computed external monitor/command fallbacks
remain lazy and untouched. No helper move/compact layout to force a PASS.

## Characterization tests

| Behavior | Existing test | Missing | Added | Result |
|---|---|---|---|---|
| Twelve operation catches, ordinary Error and fallback | Original24 specs/604 cases | Getter and empty-message policy edges | Four mounted cases per catch | Original/candidate PASS |
| Error getter read once, including empty message | Partial original coverage | Cardinality and banner suppression | Included in48 public cases | PASS |
| Non-Error getter unread and null fallback | Partial original coverage | Lazy identity counterexamples | Included in48 public cases | PASS |
| Re-fetch auth bypass and busy cleanup | Existing certificati auth cases | Auth Error.message getter bypass | One mounted countertest | PASS |
| Existing success/error/auth/lifecycle/async behavior | Exact604 original raw identities | No original test change | None | PASS, unchanged multiplicities |

NEWspec10bdbd9134b2475e217ceb7c629eae8b921fa2186d3c1243359076a706847496:
49 genuine public mounted cases, complete typed DTO/API mocks, no extracted
runtime snippets, state interception, disabled tests or coverage spoofing.

## Changes and classification

Candidate088338d6 inserts a private typed same-file policy and twelve narrow
replacements. Independent restoration reproduces original source bytes;
root AST restoration exact. Genuine duplication reduction, not a mega-helper.

Nevertheless runtime is **REGRESSED / REJECTED_FOR_INTEGRATION** because the
authoritative file-LOC ratchet fails. Only NEW characterization spec is
accepted: **NO_CHANGE / ORIGINAL_CHARACTERIZED**. Integration runtime remains
exact92a5; accepted metric delta is zero. No candidate source was applied to
integration, so no rollback was required.

## Metrics — rejected candidate only

| Metric | Original | Rejected candidate | Delta |
|---|---:|---:|---:|
| Principal cognitive |298|273|-25|
| Principal cyclomatic |275|263|-12|
| Principal LOC |2398|2398|0|
| File cognitive sum |762|708|-54|
| File cyclomatic sum |906|882|-24|
| File LOC |3108|3111|+3|
| Callable count |253|254|+1|
| Physical conditional nodes |207|196|-11|
| Physical decisions, if/logical/catch/loops/non-default cases |401|390|-11|
| Same convention including switch dispatch |402|391|-11|
| State/effect count |31/2|31/2|0|

New helper1cognitive2cyclomatic3LOC/nesting0/params2, below all thresholds.
238 source-fingerprint survivors and20072 nonowned callable records exact.
Physical counts are not the overlapping cyclomatic-minus-callables aggregate.
No rejected metric/finding/extreme-tail delta is credited to the campaign.

## Tests and coverage

Original26346 TERMINAL0, actual12 named gates0. Candidate47071 TERMINAL2:
nine named stages0, ratchet fails, final two native stages NOT_RUN.
Each actual run653PASS/25specs =604 historical raw multiset+49NEW,
zero failure/pending/todo/skip. Types/strictNEW/lint PASS before/after.
Strict gate retains662 configured roots plus3 extras, no removed roots,
strict=true/noEmit/incrementalfalse/zero diagnostics.

| Full-file coverage | Original | Rejected candidate |
|---|---:|---:|
| Workspace statements |725/725|726/726|
| Workspace branch arms |733/733|711/711|
| Workspace functions |253/253|254/254|
| Workspace lines |633/633|634/634|
| Unchanged fraction statements/branches/functions/lines |9/6/6/8 all100|9/6/6/8 all100|

All raw maps/counters positive, source locations and implicit else arms
validated; countertests PASS. No source exclusions added. Original/candidate
coverage source hashes bound, not inferred from rounded summary percentages.

## Ratchet and integration

Candidate actual-main comparison: CLI1/Make2, one
`legacy_file_metric_regression`: fileLOC baseline3109→3111 (+2). Local original
3108→3111 (+3) is distinct from the baseline delta. This is a real regression,
not matcher ambiguity or one of the historic30 divergences. Aggregate
cognitive improvement does not override the gate; baseline remains unchanged.

Candidate native diff-check/custody-after NOT_RUN. Separate post-STOP metadata
rehashes all3674 inputs unchanged, without retrying native gates. STOP123
manifest c36601daf865f5a2a9e75f88b8f1ff889d1bcd7932a74dc65816aff396995fc3
retains original failure/source/scripts/reports. Ancillary read/metadata
errors, including13→actual12 stage miscount, retained and corrected separately.

Test-only actual integration90103 TERMINAL0/all7gates0: full project types,
new-spec lint, full report, main55a ratchet/findings[], diff-check and1052
frontend/tooling bindings before/after. Two explicit separate admitted
GIS/Settings context differences recorded, not attributed to R59. No repeat
unit run solely for integration labels: fresh original653 evidence is source-
bound; full campaign suites are not certified by these targeted receipts.

## Accepted global delta

Fresh integration report:1676files20345callables1920errors2735warnings4655
overlapping findings. All callable and file records exactly equal R58 complete
report. Application1621files19014callables319060LOC; tail3>300/17>200/55>100
unchanged. Accepted reduction0;49 tests added, no runtime debt credit.
Independent final disposition and current global-check status are separate
publication receipts, not inferred PASS.

Additional independent final auditf692ed68/116records accepts only test-only
CHARACTERIZATION/NO_CHANGE and runtime rejection; STOP123 rehash exact.
Report FINAL_R59_ADDITIONAL_DISPOSITION_2026-10-12.md imported byte-exact,
reviewer freeze0396a7f8. Fresh global65499 exits2 sameGAIAusers ambiguous
identity/four candidates; local change ratchetPASS0, no baseline repair.

## Files changed and commit

Integration: only NEW mounted spec and quality reports/registry/progress.
Rejected runtime source stays frozen in the dedicated author worktree.
No commit. Graphify code has no admitted boundary change to refresh;
platform documentation maintenance is Coordinator-owned.

## Residual risks and next slice

R59 alternative-design decision pending; never shrink helper formatting or
relocate it solely to bypass file LOC. R43 separate fixture correction remains
pending; its frozen source/tests are untouched. Full frontend/backend/build/
worker/E2E and global baseline provenance obligations remain open.
Campaign ACTIVE/INCOMPLETE; stop this responsibility, not the overall goal.
