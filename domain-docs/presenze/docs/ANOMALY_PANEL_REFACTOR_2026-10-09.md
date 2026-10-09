# Presenze — anomaly-panel model, R7

## Responsibility

`frontend/src/app/presenze/giornaliere/anomaly-panel-model.ts` prepares ordered
monthly anomaly records and their day/collaborator groups. Classification,
reason selection, lifecycle, permissions, API calls, commands and JSX remain
in the daily page and are unchanged by this slice.

The model deduplicates the three priority comparator chains, the two group
collection loops and the exact anomaly/analysis count projections. Counting
still uses two exact filters, not a one-pass count or an unknown-kind fallback.
The shared comparator chain is lazy and stops on any result other than zero.

## Ordering contract

- Priority is `kindBase * 100000 - operational_missing_minutes`: anomaly0,
  analysis1; no normalization, clamping or nullish default.
- NaN from undefined/NaN/non-finite subtraction returns immediately; it must
  not invoke date/name fallback. Native stable sort treats it as a tie.
- Month: priority, date `localeCompare`, then collaborator name `localeCompare`.
- Day entries: priority, then name; day groups sort by date independently.
- Collaborator entries: priority then date; groups sort by descending blocking
  count, descending total, then collaborator label `localeCompare`.
- Comparison names use `name ?? ""`; group labels use `name ?? collaboratorId`.
  An existing empty name remains empty rather than becoming the ID.
- Maps preserve first insertion order, ties preserve source order, duplicates
  and record/item object identities remain intact. Group sorting copies arrays
  and never sorts the source collections in place.

## React boundary

The four modified memo callbacks retain their dependency arrays and hook
positions. The month classification/filtering, filtered panel records, first
critical record selection, editor state, group actions and rendering are
unchanged. There is no new state/effect, API hook, component or shared-library
dependency.

## Verification

Four UI characterization tests pass against the original page before runtime
edits and against the result; seven pure-model cases cover frozen duplicate
inputs, stable ties, empty collections, unknown-kind count behavior, numeric
edge cases and lazy NaN comparisons. Existing daily-page suites remain intact.

Focused verification:424PASS, zero skips, both full runtime files100% statements,
branches and functions. Principal cognitive420→403; affected-file aggregate
cognitive1222→1192/cyclomatic1309→1284. New model has no complexity findings.
Aggregate file LOC rises24, while callable LOC falls66; this is a cognitive and
cyclomatic improvement, not a file-LOC or finding-count reduction. Ratchet against
main55a passes with zero findings; baseline, thresholds and exclusions unchanged.

Independent review and integrated frontend/build/browser gates are recorded in
the campaign report rather than inferred from these author checks.
