# Capacitas — Modal updater reachability

## Ownership and snapshot

- Agent: `modal_provenance`; ownership is this report only, with disposable
  experiments under `/tmp/gaia-modal-probe/`.
- Branch: `refactor/complexity-modal-provenance`; source HEAD
  `3d7a998c6a2a57d37c6425949c21bc3c29167369`.
- Merge-base against `main`: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Preflight `git status --short` empty. No runtime, test, baseline, tooling,
  threshold or exclusion was modified. No integration was performed.
- Runtime `frontend/src/components/elaborazioni/capacitas-workspace.tsx`
  SHA256 `d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`.
- Inherited fifteen-spec union: 306 PASS, 903/929 branch arms, 97.20%; the
  full-file 100% gate remains FAIL. These numbers were not remeasured here.

## Finding classification

| Source line | Updater responsibility | Classification | Evidence |
| --- | --- | --- | --- |
| 3166 | Radio selection | UNKNOWN_REACHABILITY | No genuine false-arm witness; conditional live-event argument below is not a comprehensive React scheduling proof |
| 3206 | Begin synchronization | UNKNOWN_REACHABILITY | No genuine false-arm witness; begin update is synchronous before the API await |
| 3214 | Successful asynchronous response | REACHABLE | Native keyboard replacement, close, then successful old request; actual V8 null-arm hit |
| 3217 | Unsuccessful asynchronous response | REACHABLE | Same sequence, valid `ok:false` response; actual V8 null-arm hit |
| 3220 | Rejected asynchronous response | REACHABLE | Same sequence, rejected API Promise; actual V8 null-arm hit |

The three asynchronous guards are **not redundant defenses**. Their false
arms must remain. This report does not authorize removal of the two unresolved
guards either. Previous five-arm UNKNOWN statements remain historical; current
provenance is three reachable plus two UNKNOWN.

## Exhaustive state writers

`resolveModal` is initialized to null at 652 and is private to the workspace.
The complete `setResolveModal` inventory is:

1. 3123: a background anomaly row's `Risolvi` button replaces state with a
   fresh object, `busy:false`, `error:null`, `success:false`.
2. 3166: radio selection functionally updates an existing object or returns null.
3. 3193: `Chiudi` sets null; the button is disabled only for the currently
   displayed modal object's `busy` flag.
4. 3206: synchronization marks the current object busy before awaiting API.
5. 3214/3217/3220: pending request completion functionally updates current
   state, retaining null when it has already been cleared.

No effect, polling callback, section change, token-loss handler or cleanup
directly clears modal state. List replacement alters `anomalie`, not modal state.
The section-independent modal is rendered outside the active-section blocks.

The missing invariant is not "Chiudi is enabled while the original request is
pending"; it is **the pending request does not own the currently displayed
modal**. Another row can replace that modal with a non-busy object. The current
modal overlay has no focus trap, `inert` background or keyboard suppression.
Its fixed-position background prevents ordinary pointer clicks on rows, but
does not remove the background buttons from native sequential keyboard focus.
No React state manipulation or detached callback is required.

## Native user-action witness

The disposable harness mounts the unchanged real workspace with React 18.3.1
`createRoot`. The real polling hook, presentation components and DOM handlers
execute. Only API/auth boundaries and unrelated shell/modal children are
substituted. API rows match the actual anomaly contract; the deferred response
has the actual fraction-resolution fields. There are no fake setters, private
handler calls, parser substitutions or runtime instrumentation.

For each success, unsuccessful response and rejection:

1. Click `Aggiorna lista`, receiving two valid anomaly rows: Uras and Terralba.
2. Open Uras through its public `Risolvi` button; click `Sincronizza`.
3. Observe `Chiudi` disabled and retain the pending API Promise.
4. Press native browser Tab repeatedly until Terralba's background `Risolvi`
   button receives focus. Press native Enter, not a forced pointer click.
5. Observe that the visible modal now describes Terralba and `Chiudi` is enabled.
6. Click that enabled public `Chiudi`; the owner workspace remains mounted
   and its modal state is now null.
7. Settle the old Uras API Promise through the API-boundary mock.
8. Observe no reopened modal and no browser page error. Success removes Uras,
   not Terralba; unsuccessful response and rejection retain both rows.

Six cases pass: three outcomes with ordinary createRoot and the same three
with real React StrictMode. Keyboard focus records are retained, including the
background row owning the focused button. StrictMode is explicit experimental
coverage, not an assertion about the deployed Next.js configuration.

## Actual branch execution, not inference from UI alone

Playwright's Chromium precise V8 coverage was started before page navigation.
It recorded the Vite-transformed unchanged workspace script and actual updater
functions. For each corresponding asynchronous updater:

- Callable execution count is positive: 1 without StrictMode, 2 with StrictMode.
- The conditional object-expression arm has V8 count 0.
- The function source has exactly `prev ? { ... } : null`; its remaining
  branch therefore executes with null. Across six experiments there are nine
  actual null-arm executions.

`coverage-audit.mjs` independently asserts these properties against the saved
raw function/range coverage, rejecting ambiguous scripts or absent ranges.
This is concrete evidence for the three targeted branches. It is **not** a
Vitest full-file coverage result and is not added to the official 903/929 union.

## Lifecycle, concurrency and unresolved synchronous arms

### Ordinary discrete events

Controls render only when modal state exists. Radio and begin handlers perform
their updates synchronously, with no async yield before those updater calls.
The normal real-browser discrete-event contract flushes updates between user
events; after an enabled close is committed, its controls are removed. The
token getter is a synchronous localStorage lookup in the real implementation,
not a callback that can legitimately mutate React state. A double click or a
click on a disabled close button therefore does not prove a null previous state.

This supports a conditional non-null argument for 3166 and 3206 under ordinary
live DOM dispatch. It does not justify a universal claim about queued event
replay, interrupted concurrent rendering, update-lane rebasing or every Next.js
lifecycle. No exhaustive scheduler/event-replay proof was completed, so those
two arms remain UNKNOWN rather than being removed to satisfy coverage.

### Pending completions and replacement

Pending completions retain the original request's captured row ID/fraction,
but update the **current** modal state rather than a request-owned state. The
keyboard witness uses that existing behavior. It does not change authentication,
request order, payload, filtering, exceptions or UI transitions. Results that
arrive while another modal is open can also update that other modal; correcting
this would be a separate functional/race decision, not this report's scope.

### Hiding, unmounting and remounting

The workspace owns modal state and returns `ProtectedPage` beneath itself in
nonembedded mode. ProtectedPage can stop rendering children on session or
permission loss; that hides the modal DOM but does not set the owner's state
to null. Changing workspace section likewise does not clear state.

Actual owner unmount is different: the old setter belongs to the old hook
queue, not a newly mounted workspace whose initial state is null. React's
`detachFiberMutation` disconnects return pointers; root lookup from a detached
fiber yields no mounted root. In React 18.3.1 `dispatchSetState` can eagerly
evaluate an updater before scheduling, using that queue's `lastRenderedState`.
Thus "updates after unmount never execute" is too strong; equally, "remount
starts null so the old updater receives null" is invalid. Neither observation
is a genuine witness for the unresolved synchronous arms.

StrictMode can repeat pure updater evaluation, but repetition alone does not
manufacture a null transition. In the measured race it repeats an already
real null-state completion; the three guards retain that null safely.

## Commands and artifacts

Executed successfully:

```text
node /tmp/gaia-modal-probe/run.mjs
node /tmp/gaia-modal-probe/coverage-audit.mjs
```

Last browser log: `/tmp/gaia-modal-probe/browser-coverage.log`, exit 0,
6/6 public-UI cases. Vite's initial dependency-resolution warning for bare
`react-dom` did not stop the server; six real pages loaded and executed the
dependency alias. Server and browser close in `finally`; no live service is
left behind. The probe uses localhost port 13743, not the GAIA stack.

Key SHA256 artifacts:

| Artifact | SHA256 |
| --- | --- |
| `/tmp/gaia-modal-probe/run.mjs` | `d48222c2cc127e6913900f5a16269ea3e542c975aaf53b6b653c03f0bcb396b3` |
| `/tmp/gaia-modal-probe/entry.tsx` | `87ecbfb550fa18948ef11d5e75c1d519126487594d05b96e364fe2ae4c4a298a` |
| `/tmp/gaia-modal-probe/boundaries.tsx` | `cae613162011cb79416207f6077ab50931828da357ee23e05dae65939e932987` |
| `/tmp/gaia-modal-probe/results.json` | `7b806331afe834e56c97f7c697a4f3a15797dc314098da2fa726e175cab0b831` |
| `/tmp/gaia-modal-probe/coverage-audit.mjs` | `40f37396461d6dca906fdca1b25ba82b7cbfc01c9fedb693fa4ba453bbb13534` |
| `/tmp/gaia-modal-probe/coverage-audit.json` | `2110bf9ea312cb49938cf7e1e645c3cb51d79c3163ba716e2468d08ef8b8688d` |

Raw coverage files are `/tmp/gaia-modal-probe/coverage-{false,true}-{success,failure,rejection}.json`.
React DOM 18.3.1 development source SHA256
`1459b808bc6991de5a1ec3a86d8beee32dbb6c14282cf13f84e00dfebfbdc025`;
relevant inspected functions at 3963, 4006, 14498, 15719, 16641 and 23709.
Playwright 1.59.1; Vite 8.1.3. The browser probe is local isolated evidence,
not an E2E validation of production CSS, deployed auth, external Capacitas or
all supported browsers. The keyboard witness depends only on background
focusability; this is visible in the actual component's lack of a focus trap.

## Classification, limitations and next action

Slice: **NO_CHANGE — PROVENANCE_ONLY**. Complexity, runtime bytes and official
coverage are unchanged; no newly passing ratchet or full suite is claimed.
Graphify is not complexity evidence and no component boundary changed here.

Next meaningful action: assign exclusive ownership of a test-only C12 slice
that exercises background public row replacement, enabled close and the three
late-response outcomes on the real workspace. Preserve these guards and
existing race semantics. Measure the actual cumulative Vitest coverage after
independent review. Expected reachable coverage gain is three arms, not five;
two modal guards and the twenty-one separate conditional candidates still need
their own evidence/decisions. Do not call the full-file gate green from this
disposable browser probe or authorize runtime cleanup from provenance alone.
