# R81 — Contemporaneous GIS layout measurements

## Ownership and provenance

User authorized only reacquiring canvas/panel together after detail visibility,
followed by a distinct verification. Dedicated branch
`refactor/complexity-campaign-20261008`, initialHEAD
`e458dcdeaac64ff8d8740524900cc3a0f576b411`, actualmain/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Main concurrent work excluded.
Historical55a1b1d provenance only; R78/R79/R80 failures and receipts immutable.

## Change and invariants

Remove early canvas `boundingBox()` acquisition after closing Console; acquire
canvas and panel via `Promise.all` after detail visibility. Null guards and all
three original placement checks unchanged: y>=0, y<20 and right-gap>=55.
R79 refocus and R80 whitespace readiness retained. No new wait or timeout,
no helper/click/candidate/mock/geometry/layout/runtime change.

Diagnosis source: R80 compressed snapshots record canvas right900,width680 at
early acquisition and right1280,width1060 at panel acquisition;380pxdifference
matches Console width and reconstructs -316+380=64px. Getter return not serialized;
panel right1216 inferred, not directly recorded. Offline diagnosis593crosschecks
PASS, independent reviewer unavailable then; no diagnosis native replay.
Do not infer R81PASS from this reconstruction.

## Test matrix

| Behavior | Existing test | Added | Result |
| --- | --- | --- | --- |
| Original layout thresholds/null guards | Original consultation case | Contemporaneous measurement | Native PASS |
| Desktop/mobile Console layout | Original first GIS case | None | Native PASS |
| Search/drawing/detail/sheets/measure/print/QGIS | Original consultation case | R79/R80 prerequisites retained | Native case PASS, all assertions reached |

## Evidence and gates

Root `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r81-gis-current-box/`.
Original/R80 specs, mutable documents and preexisting Git state frozen before edit.
Candidate SHA256 `503a704d8d152bf6258ec599dc38dfffc95e9aa308bce8102a3ba0565e5a966b`.
`measurement-only.diff` records R80delta; `authorized-spec.diff` binds complete
candidate change versusHEAD. Runner/faithful MVT fixture copied from R80,
exact protected-file hash permits only the candidate spec. Runtime/build/
dependencies/browser pinned; no backend/DB/provider, isolated namespaces,
read-only mounts and owned cgroup. Full-file run once after preparation review
and fresh quietslot, workers1/retries0/maxfail1; new native failure stops admission.

Runtime NO_CHANGE; runtime coverage not remeasured (identical bytes). No global
coverage/full-suite claim, baseline/threshold/exclusion/ignore/policy changes.
## Verification

Preparation capturePASS0. Independent reviewer unavailable due usage limit
observed in prior diagnosis, not retried/worked around. Coordinator bounded
preparation29checksPASS, explicitly NOT independent: exact R80delta, old assertions
and waits byte-identical, guard count retained, runner differs only by authorized
spec hash/new receipt name, fixture/modules unchanged, historical input custody
exact. Independent admission review remains required; native evidence is not
permission to bypass it or commit.

One distinct native full-file invocation: **2PASS/0FAIL/0SKIP/0FLAKY**,17.9s,
workers1/retries0/maxfail1, original config. Collection/execution/native/driver
exit0. Full consultation completes unchanged placement, territory sheets,
measurements, print and QGIS assertions under the existing mocks/private MVT.
Not certification of live provider, production authentication, real QGIS import
or live database. No full-suite rerun, no inherited PASS from historical runs.

Coordinator terminal2754checksPASS, explicitly NOT independent. Initial checker
expected interface names instead of socket.if_nameindex tuples and failed
offline; preserved in `check_terminal.v1.py`, `coordinator-terminal-review-v1.*`.
Corrected checker reads tuple names without changing native receipt or replaying
browser; `coordinator-terminal-review-v2.*` and
`coordinator-review/TERMINAL_CHECKS.json` record success.
All2732protected hashes current/exact, preparation==native-before==native-after,
private network namespace differs from host and onlyloopback, runtime/build
read-only. Owned cgroup empty/removed, Next/proxy exit0 after owned shutdown.
Main concurrent hashes unchanged; no external data mutation.

Ratchet once against actualmainPASS0findings, authoritative baseline commit
`a51a48dc`; diff-checkPASS. Global baseline ambiguity/skips/other campaign gates
unchanged, no baseline repair/inflation or threshold/policy changes.
Graphify docs completed once via `make graphify-platform-docs` after initial
quiet-slot guard stopped external Jest before any launch and bounded waiter
observed a fresh free slot. Exit0, chunk1/1done, no semantic-failure warning,
951nodes/1215edges/161communities;6078input/2558outputtokens, estimated$0.0065.
Source/output hashes bind graph snapshot; final receipt-only annotations postdate
it. Graphify-out ignored/not staged; no runtime/component-boundary change.

## Admission

Historical initial disposition was READY_FOR_REVIEW, not admitted because the
independent reviewer was unavailable. Fresh goal resume verified all113handoff
records before any update and preserved mutable docs in `admission-resume/`.
Independent review now **AMMESSO, test-workflow only**:2196bounded checks plus
19raw native-report/binary checks PASS. Raw report independently reconstructed
2PASS/0FAIL/0SKIP/0FLAKY/0RETRY,17851.018ms; exact candidate, runtime/build/main
custody, cleanup, recorded actualmain ratchet and Graphify receipt verified.
`review/INDEPENDENT_REVIEW.md`, `review/ADMISSION_SHA256SUMS`,
`review/admission-v2/CHECKS.json`, `review/RAW_REPORT_CHECKS.json`.
Reviewer stopped, no native/scanner rerun; no inherited broad/live-service claim.
Earlier availability and parse failures remain immutable historical receipts.
Runtime NO_CHANGE, no global completion or complexity-reduction claim.

Coordinator inventory admits only the exact spec and its evidence documents.
Historical R78/R79/R80 reports/registries are admitted as documentary receipts,
not the failed intermediate specs. Selective local commits on existing branch
authorized by prior consolidation instructions; no push/main merge. Immutable
snapshots still bind pre-publication HEAD; commit receipts recorded separately.

## Handoff and residual work

External `HANDOFF.md`, `HANDOFF_MANIFEST.json` and `.sha256` seal freezes, exact
spec delta, preparation/native/terminal receipts, reports, gates and final docs.
10unstaged files retained: existing PROGRESS/spec plus R78/R79/R80/R81 registries
and reports. This continuation adds only R81registry/report and updates owned
spec/PROGRESS; old registries/reports unchanged. No `git add`, commit, push/merge
or main write. Independent review reserved, NOT_RUN; all owned native/server/
waiter/gate processes terminal. Goal globally incomplete; no automatic new slice.

The above ten-file/no-commit paragraph is the initial pre-review checkpoint.
Current publication phase supersedes only that disposition. Commit plan:
R78–R80 historical documentary receipts; R81 admitted test and report/ownership;
then current PROGRESS and selective handoff receipt. No cache/DB/build/dependency/
graphify/private runner, unrelated partial candidate or main concurrent file may
enter those commits. Existing pre-commit docs automation is documented: its
supported SKIP_DOCS_UPDATE=1 avoids uncontrolled AI edits only for curated test
publication; no quality/test gate bypass. Exact files are staged individually.

## Selective local publication

Independent admission completed; local historical documentary commit ce57e1e5
and final test-workflow commit ef99dc16 on existing dedicated branch. Spec hash
remains503a704d... exactly; no new browser run or runtime change. Historical
intermediate failed candidate source is not committed. Registry MERGED denotes
integration-branch admission only. Final handoff/publication status in
`R81_GIS_PUBLICATION_CHECKPOINT_2026-10-13.md` and external `admission-resume/`;
old manifests/freezes retained. Main/push/PR untouched, global goal incomplete.
Separate publication waiter ended exit3 after240s with external Jest active;
current ratchet/Graphify NOT_RUN, no retry or native rerun. Earlier verified
native/ratchet/Graphify receipts remain immutable historical results. Final
documentary commit and checksums are bound in the separate publication handoff.
