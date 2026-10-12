# Capacitas — particelle monitor policy boundaries

Status: proposed boundaries only, NOT_ADMITTED. After the ratchet STOP the exact
candidate is preserved externally and runtime restored to admitted HEAD7f9d7883
through Coordinator-owned apply_patch. No policy below is credited as deployed;
temporary deactivation avoids contaminating independent campaign slices while
the separate positional-matcher decision is pending.

## Responsibility

The same-file pure helpers in `capacitas-workspace.tsx` isolate only particelle
monitor result validation, active session-expiration detection, speed/label
presentation and stop-button precedence. Existing cards and tables stay inline;
there is no JSX relocation, new component/hook/state/effect or API change.

`getParticelleJobResult` shares the existing weak result guard: only the three
numeric total/processed/progress fields are checked, without finite-value checks
or stronger nested-item validation. Its caller decides active versus terminal
handling. Session expiration still scans active jobs only, before rendering
cards, and examines every recent item, not merely the displayed latest eight.
Weak-valid terminal results do not acquire an eager recent-items validation.

`getParticelleActiveResultPresentation` is invoked only for a truthy active-job
result. It shares the double-speed predicate used for the suffix and selected
button style; Standard deliberately retains its independent predicate, including
the historical NaN distinction. Empty current label has no separator; window
labels and `parallel_workers ?? 1` preserve their original truthy/nullish rules.
The erased TypeScript assertions in JSX are dominated by the unchanged result
guard; they do not introduce optional fallback branches.

`getParticelleStopPresentation` preserves disabled state and cancelling-before-
busy caption precedence. Handlers, command arguments, ordering, result-over-error
precedence, terminal colors, latest-eight reversed-copy rows, keys, classes and
React text-node segmentation remain unchanged. Pure field-read order changes;
arbitrary effectful getters/proxies are not an equivalence claim.

## Verification

The original 23 mounted Capacitas specs remain immutable. Independent review
checks the unrelated AST, all 624 JSX nodes and 719 source-backed differential
scenarios, including 12 preserved malformed-active exceptions; these supplements
do not replace native mounted tests or coverage. Native command/log/exit/raw
coverage evidence is recorded separately in the R37 integration report.

Four helpers are below warning thresholds. The accepted static proposal reduces
principal cognitive324→307 and aggregate811→778, with two fewer physical
decisions. File LOC increases3087→3108 and summed callable LOC increases11;
these tradeoffs are explicit, not claimed LOC reductions. Immutable main file
baseline3109, coverage policy, thresholds and exclusions remain unchanged.
Native and independent-final admission remain mandatory before publication.
This responsibility does not eliminate the >300 hotspot or complete the campaign.

## Admission STOP

Candidate mounted559tests, full-file coverage100, types/lint/report pass, but
the actual main55a ratchet fails with one anonymous-handler LOC1→2 comparison.
Source-backed diagnosis shows the unchanged fraction-selection callback is
compared with the distinct close-button callback after positional shifts.
This does not waive the failed gate: R37 remains uncommitted and NOT_ADMITTED,
without credited reductions. Independent reviewer confirms incorrect binding;
separate matcher decision pending. Baseline/scope/thresholds/test/config unchanged.
Original metadata audit recovered without dropping synthetic else arms; candidate
native certification, raw/custody pipeline audit and Graphify refresh are not
claimed completed. Latest accepted campaign metrics remain R36.
