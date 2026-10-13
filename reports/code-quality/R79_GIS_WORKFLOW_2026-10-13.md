# R79 — GIS test workflow prerequisites

## Scope and provenance

Dedicated checkout `GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`, initial HEAD
`e458dcdeaac64ff8d8740524900cc3a0f576b411`, actual main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Main concurrent work excluded.
R78 diagnosis and original 1 PASS / 1 FAIL remain immutable. User authorized
continuation after diagnosis; this is a separate test-only change, not a retry
of the original test with unchanged inputs.

## Behavioral invariants and change

Same original parcel, municipality, triangle, UUID, MVT fixture, mocks, runtime,
build and dependencies. All existing assertions, timeouts, zoom clicks, candidate
clicks and helper retained. Two additions: select the public parcel-search result
again after drawing cleanup/zoom; assert public scale in metres after the existing
1000-ms wait. The parcel focus uses the original 700-ms fitBounds animation;
the test no longer assumes four rapid zoom clicks complete four whole increments.
No private map getter, forced feature hit or altered geometry.

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Desktop/mobile layout | Original first case | No | None | PASS |
| Search, municipal focus, drawing cleanup | Original consultation case | Parcel refocus before selection | Public result click | Reached scale assertion |
| Parcel selection prerequisite | Original detail assertion | Explicit scale readiness | Public scale assertion | FAIL: NBSP versus ASCII space |
| Detail, sheets, measures, print, QGIS | Original remaining assertions | Previously not reached | None weakened | NOT_REACHED |

## Evidence and validation

External root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r79-gis-test-workflow/`.
Original spec and preexisting documents frozen in `freeze/` before editing.
Original spec SHA256 `ff632044932bb386848c6dc1b9449358cb1686adafc7c2039180538d5000b043`;
candidate `b211546874358b7d85e7ae6e4165bde75ff8be6330b42abe1386257b485ef7dd`.
`authorized-spec.diff` records exactly two added lines. Fixture copied byte-for-byte
from R78, SHA256 `671a34ac49b3332802a030e7c12af8fc4c330493d1957070b65f5375d39be2bb`.

Private runner preserves isolated loopback/PID namespace, read-only checkout and
build, owned cgroup and exact input custody. The only allowed protected-file
delta is the explicit candidate spec hash; no broadened exclusions. Preparation
capture PASS (`prepare.exit=0`), all other historical protected inputs unchanged.
Independent preparation review accepted with 1838 checks PASS, receipts in
`review/PREPARATION_REVIEW.md` and `review/PREPARATION_SHA256SUMS`.
Exactly one distinct native execution, workers=1/retries=0/max-failures=1,
after review and quiet heavy slot: 1 PASS / 1 FAIL / 0 SKIP, no retry.
Consultation fails at the newly added scale assertion line498, not original
detail assertion: received `200\u00a0m` (non-breaking space), expected regex
contains ASCII space. This is a defect in the new readiness assertion; it does
not establish GIS/runtime regression or certify remaining assertions.
`execute.exit`, native/execution and native-terminal exit1 retained. Trace,
video, screenshot, reports and MVT request log preserved. Before/after capture
exact; cgroup terminal empty/removed and Next/proxy terminated.

The first checksum verification used the wrong working directory for review's
relative manifest paths and failed before any runner/test launch. Correct-root
verification passed; it did not cause a native retry. Both verification logs
retained; review must not misclassify the first error as a browser execution.

Runtime classification NO_CHANGE. Runtime coverage not remeasured because runtime
bytes unchanged; no full-suite or global coverage claim. Ratchet against actual
main PASS, zero findings, baseline commit `a51a48dc`; run once, logs and exit0
preserved. Baseline comparison and historical ambiguity remain separate.
Diff-check terminal PASS; main concurrent hashes unchanged. Graphify platform
docs initially NOT_RUN because external Jest jobs restarted after native. After
reviewer and heavy jobs ended, fresh guard allowed one `make graphify-platform-docs`:
exit0, chunk1/1 done, no semantic-failure warning. 936 nodes, 1194 edges,
159 communities, 6598 input/2246 output tokens, estimated $0.0062. Source hashes
in `graphify-source-hashes.sha256` bind the snapshot before receipt-only terminal
annotations; output hashes in `graphify-output.sha256`, graphify-out ignored.
No changed runtime/component boundary, no code graph update required.

## Admission and next decision

Candidate spec PARZIALE, excluded from commits. Preexisting R78 documentary work
retained, not silently admitted as GIS PASS. Independent terminal review accepted
the evidence WITH failure: 3014 checks PASS, receipts `review/TERMINAL_REVIEW.md`,
`review/TERMINAL_SHA256SUMS`, `review/terminal-v2/CHECKS.json` and separate NBSP
supplement. Initial reviewer trace-schema interpretation failure preserved;
corrected offline checker does not rerun the application or browser. No automatic
repair/retry: next proposed separate activity is correcting only the new regex
to accept whitespace (`\s`, including NBSP), with unchanged numeric/unit intent,
existing assertions and timeouts, followed by a distinct reviewed invocation.
No further code edit or native execution without that decision. Goal incomplete.

## Handoff

`HANDOFF.md`, `HANDOFF_MANIFEST.json` and `HANDOFF_MANIFEST.sha256` in the external
R79 root seal the failure, review, input custody, freezes, gates and current
repository documents. No candidate or documentary commit in this continuation;
six working-tree changes retained (three preexisting, three new), no staged files.
No runtime, main, baseline, threshold, exclusion or coverage-policy change.
