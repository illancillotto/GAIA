# Selected INAZ punch detail — R36

## Responsibility

`PresenzeGiornalierePage` delegates only its selected daily INAZ punch section
to the hook-free same-file `InazPunchDetail`. The child is mounted inside the
original selectedRecord-and-editor dialog gate. `buildInazPunchDetail` selects
the existing detail-versus-paired source, then projects each row's shared raw
time, chronological key, authorization annotation, direction and terminal label.
Rendering keeps the original tags/classes/key strings and text-node segmentation.
There is no new runtime file, effect, state, API, identity or permission policy.

`resolveInazPunchTime` is shared by sorting and display instead of separately
repeating authorized missing-time fallback. Truthy own time wins; only the first
matching authorized paired time may replace a missing time. Own-time annotation
applies only paired-source rows; actual matching fallback is annotated for either
source. Sort priorities remain minutes, E/U/other, locale comparison and stable
equal-key order. Display direction stays case-sensitive; sort/fallback retains
its original trim/uppercase normalization. Detail-versus-paired tuple comparison
and auth-only no-row section stay unchanged; original arrays are never mutated.

## Observable equivalence

The real API DTO is plain JSON strings/nulls/arrays. Projection helpers are total
and effect-free on that declared contract, so shared calculation and map-before-
sort preserve observable ordering and labels. Pure invocation/fiber call order
changes; literal traces and arbitrary effectful getters/proxies are not certified.
Independent whole unrelated AST, meaningful child JSX/DOM and source-bound finite
DTO differential proofs supplement the existing mounted tests, not replace them.
Request/anomaly/editor/validation sections, modal events and asynchronous effects
are outside this responsibility and remain unchanged.

## Evidence and limits

Principal cognitive367→360, cyclomatic323→316, LOC1988→1945. Whole-page cognitive
sum1062→1048, cyclomatic1201→1191, effectiveLOC2809→2803, normalized decisions
892→883. New child5cognitive/6cyclomatic/46LOC; all new helpers below warnings.
Old display-policy warning disappears rather than moving to an equivalent helper.

Author, independent native final and root integration:496 mounted tests in seven
unchanged specs PASS, modified page statements1040/branches1106/functions306/
lines853 all100%. Types/lint/report/actualmain55a ratchet0/findings[], raw coverage
and source custody audited. Baseline/scope/thresholds/ignore/config/tests unchanged.
Detailed evidence and retained rejected-proposal/tool diagnostics live in the
R36 campaign reports; no main merge/push or whole-project-suite claim.

This coherent slice is IMPROVED, not strategic P1 completion: principal360 remains
above300, and global extreme-tail/historical-baseline/final broad suites remain
open. Graphify is impact documentation, not evidence of complexity reduction.
