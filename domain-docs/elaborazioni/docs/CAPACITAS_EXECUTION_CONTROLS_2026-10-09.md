# Capacitas — execution option controls

## Scope and current disposition

R13 deduplicates exactly four Terreni/Particelle double-speed/parallel controls
in `frontend/src/components/elaborazioni/capacitas-workspace.tsx`.
Author source3a22f966/SHA2568111c1a4 and independent review1a6aade1/SHA2569fae887f
are frozen and accepted IMPROVED. Distinct final certificateac922cb3 is integrated
03c25ac9 after original/source/review picks, all five main55a ratchetsPASS0.
Source integrated9e9e5421, review63ea4ead. Global campaign ACTIVE/INCOMPLETE.
No functional, API, job status, polling, authentication or identity change.

## Component contract

Private same-file `CapacitasExecutionToggle` shares active/inactive classes,
label and description selection using one boolean tuple index. Its typed props
are kind, active, family-specific descriptions and the existing onClick callback.
There is no hook/state/reducer/export/import/event wrapper or extra DOM node.

The actual element remains a native `button` with type button and exactly two
span children. Original classes, accessible name, family-specific
descriptions, layout/grid and sibling order remain exact. No disabled,
aria-pressed or tabindex attribute is added. Callback is forwarded directly.

Original functional setters stay at each call site: speed negates the current
boolean; parallel uses current workers greater than one ? one : two. No clamp,
coercion, state normalization or stale-render update replaces these semantics.
Two clicks queued before rerender compose correctly; the other option and family
state remain independent. Switching sections preserves each family's selection.

## Public mutation and asynchronous behavior

Create payloads retain all existing credential, batch, flags, limit, throttle
and auto-resume fields. Options remain editable during a pending create while
submit is disabled. The pending request and its confirmation retain the values
captured at dispatch; subsequent edits remain visible and determine the next
request. No race fix, cancellation, new effect or handler behavior is introduced.

The original public characterization adds16 meaningful cases: eight family ×
boolean combinations, four same-render double queues, two section persistence
cases and two pending-create/edit/next-submit cases. Original and modified full
Capacitas unions both pass492/21specs with zero skip. Real modal/hooks are used;
authentication/API boundaries are isolated. jsdom does not certify native keyboard
default behavior. Distinct final Chromium certifies genuine focus/Enter/Space,
Tab/ShiftTab and exact native DOM in both family orders,44trusted activations.
All eight configurations per order, pending payload capture/next request and
section persistence pass. Auth is genuine; domain APIs use synthetic intercepted
responses, so no external portal or real Capacitas job write is certified.

Accessible-name fixtures distinguish environments: jsdom without layout
concatenates the two spans, while real Chromium with compiled Tailwind block
spans inserts one separating space. Native browser assertions use the actual
rendered name; source text, classes and DOM remain identical. The first external
browser harness's copied jsdom name expectation failed before keyboard actions
and is retained, not presented as a runtime failure or passing attempt.

## Actual measured source reduction

Principal cognitive359→347, cyclomatic336→324, callableLOC2487→2455.
Complete workspace plus unchanged fraction policy cognitive871→861,
decisions762→752, rawcyclomatic1016→1007, callableLOC4615→4600,
effectivefileLOC3131→3126, callable count254→255. New private helper has
cognitive2/cyclomatic3/LOC17, below all warning thresholds. Genuine source
decisions in four controls14→4 and whole combined source440→430.
Owned finding counts17error/16warning remain unchanged; debt is not eliminated
merely because a principal score decreases. Principal remains extreme.

Full-file coverage after refactoring is100% in all four dimensions: workspace
718statements/778branches/249functions/625lines and unchanged policy9/6/6/8.
Author and independent runtime reviewer freshly reproduce these denominators,
type/lint, source integrity and full immutable55a Make ratchet0.

## Tooling limitations and residual risk

AST census counts70useState calls and2useEffect, unchanged by R13. The existing
scanner's regex counts31useState because it omits39generic calls. Both counts
are explicit, not reconciled by changing the scanner or baseline in this slice.
Findings can overlap and are not independent-defect counts. Historical global
30baseline divergences remain a separate provenance responsibility.

Source/behavior matrix and exact commands are in SLICE_R13, original CHAR,
independent original REVIEW_CHARACTERIZATION and runtime REVIEW_R13 under
`reports/code-quality/`. Distinct VERIFICATION_R13 additionally passes4671whole
frontend/307specs, smoke18, type/lint/cleanbuild, fullavailableE2E54PASS7historical
SKIP0retry/flaky. All37ownedprocesses terminal, isolated resources removed and
main untouched. Global30baseline finding objects remain exact historical.
Integration/metrics/provenance/top30 are in INTEGRATION_R13; backend/worker full
global closure and optional skipped-provider scenarios remain separate work.
