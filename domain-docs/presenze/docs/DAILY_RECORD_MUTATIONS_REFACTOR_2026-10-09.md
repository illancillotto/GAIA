# Daily-record mutation lifecycle — local refactoring

## Scope

Candidate R9 is local to `frontend/src/app/presenze/giornaliere/page.tsx`.
Four existing commands remain at the same JSX callsites: KM, reperibilita,
editor save and validation. No API, backend, identity mapping, authorization,
hook, effect, state or rendering change. No new public abstraction or runtime
file. This document does not certify final integration or campaign completion.

## Responsibilities

- `buildDailyRecordEditorUpdate` is a private pure editor-form→manual-update
  payload mapper. Existing conversions, field order and validation-note
  permission remain identical; mapping executes inside the request try.
- `createDailyRecordMutationHandler` binds the four command-specific preparation
  callbacks to one shared persistence lifecycle, without side effects at render.
- The returned named `executeDailyRecordMutation` is the only async boundary:
  prepare, request, cache eviction, response application, success, catch/finally.
- Each preparation retains its own token/guard/normalization/start-state order.
  Inline commands share their no-op success and saving-ID reset; editor and
  validation share their saving-boolean reset but retain distinct success text.

`DailyRecordMutation` has only token, request, success, finish and errorMessage.
The factory's argument tuple expresses existing command signatures; it is not
a generic processing framework, exported API or dependency context.

## Preserved sequence

```text
user action
  -> returned async handler
  -> token / original guards / normalization / start-state writes (before try)
  -> request payload evaluation and awaited API (inside try)
  -> evict cache for captured token + response work_date
  -> apply response to records and detail cache
  -> original success behavior
  -> original Error-versus-fallback catch
  -> unconditional original scalar saving reset
```

No-op commands still return a resolved Promise. Preflight/start-state throws
still reject outside UI catch. Payload/API/cache/apply/success failures retain
partial effects and exact finally behavior. No additional async adoption layer.

## Intentional differences

KM does not acquire the reperibilita permission/ferie guard. Editor does not
acquire a new independent operational-edit permission guard. Validation still
requires `canValidate`; editor validation_note still depends on that permission.
Inline commands retain previous success text while pending; editor/validation
clear it before the request. These behaviors are characterized, not normalized.

Overlapping requests remain concurrent. Completion order still wins, and a
completion may clear the scalar saving flag while another request is pending.
Captured render state, late failures, changed response IDs, selection changes,
other-month responses and unmount cache effects are preserved. No race fix,
mutex, cancellation, debounce, retry or rollback introduced.

## Evidence and limits

19 new rendered original tests precede runtime changes. Author, independent
original reviewer and Coordinator each replayed472focused tests with original
full-file100% coverage. Actual named candidate472PASS; full page1035statement/
1139branch/306function100%. Frozen original differential covers101cases,
64overlaps,73timingcases/365microticks and2352editor payload combinations;
91protected helpers,75hooks,103other principal statements and482JSX nodes match.

Actual page aggregate cognitive1109→1093, principal399→385; measured aggregate
decisions934→923. Raw cyclomatic1230→1231, callable296→308, fileLOC2788→2812
and callableLOC4319→4364 are disclosed. Named candidate ratchet/mainPASS0;
source review and final full-suite/build/E2E/Graphify certification remain
separate gates. Principal remains extreme; this is not the end of the campaign.

Initial unnamed returned async function matched legacy Program<anonymous> debt
and failed five ratchet metrics. The genuinely new shared handler receives an
explicit semantic name, without renaming legacy code or changing behavior.
Exact oracles and ratchet rerun; initial failure retained. No baseline inflation,
threshold/exclusion/config/tooling changes. Thirty historical global divergences
and Capacitas97.52% coverage failure remain separate unresolved campaign items.
