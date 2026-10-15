# Monthly anomaly group rendering — R108

Status: exact source independently admitted in integration (`c726f5c4`).

The Presenze daily page has two monthly anomaly grouping modes: day and
collaborator. Their section renderer shares the count/pluralization, anomaly
and analysis badges, and ordered card list. A discriminated input retains the
different group identities, headings and copy. This is an ordinary synchronous
renderer, not a new React component or reconciliation boundary.

## Preserved contract

- Each map returns the same keyed host `section`, with unchanged classes and
  child layout. Day headings retain the three direct children ISO date,
  separator and weekday; collaborator headings retain the supplied name.
- Day copy remains `da lavorare in sequenza` / `coll.`; collaborator copy
  remains `nel mese` / `totali`. Singular/plural and positive-count badge
  decisions are shared without changing labels or visibility.
- Group and card ordering is unchanged. Each card retains its record key,
  grouping mode, collaborator/schedule lookups and existing component type.
- Opening a card first clears `returnToCollaboratorModalId`, then sets
  `selectedRecordId` to that record. The two state updates remain separate
  and ordered; neither runs during rendering.
- No hooks, dependencies, grouping/filter algorithms, APIs, identity mapping,
  persistence, authorization, scheduling or test/config contracts change.

The finite source proof compares the exact AST remainder and element/key/
children/action/error traces for 3,888 cases. It supplements, not replaces,
the unchanged mounted native suite and full-file coverage. It does not claim
equivalence for adversarial property getters or exhaustive browser behavior.

The native candidate has 496 passing tests across seven specifications and
100% statements, branches, functions and lines for the complete runtime page.
Provider/native/test coverage maps agree; seven raw V8 page payloads are kept.
No independent raw V8-to-Istanbul replay is claimed. Integration source/spec/
configuration/dependency bytes were independently rebound to that native result;
no identical native suite was rerun. Actual integration main ratchet, fresh
global AFTER report, configured strict types and scoped lint all pass, with
separate post-copy acceptance `1ab1c656`. Graphify receipts and final round
custody belong to the R108 report and external terminal handoff/manifest.
