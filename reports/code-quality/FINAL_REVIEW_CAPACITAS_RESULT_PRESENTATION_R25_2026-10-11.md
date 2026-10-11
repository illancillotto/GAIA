# R25 Capacitas result presentation — Independent review

## Ownership and status

Independent reviewer `r25_final_review`; ownership registry ACTIVE before spawn.
Only this NEW review report is writable in the dedicated sparse review tree.
Runtime, existing/new characterization inputs, tests, configuration, tooling and
baseline are read-only, imported exclusively by Coordinator when admitted.

- Worktree: `GAIA-campaign-20261011-r25-capacitas-results-review`.
- Branch: `review/complexity-r25-capacitas-result-presentation`.
- HEAD: `9660bfdeb72c276e52fd5c0c785d4d59d8607c61`.
- Immutable merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Preflight: clean tree, expected HEAD and base confirmed.
- Current admission: ORIGINAL accepted; failed candidate gate diagnosed READ-ONLY.
- Native heavy token: RELEASED after terminal session46339 and complete custody.
- Candidate runtime: inspected in author tree only; no import or acceptance credit.

## Baseline and target

Fresh independent ORIGINAL native evidence confirms workspace main cognitive324,
cyclomatic301, LOC2412; file cognitive811, cyclomatic953, LOC3087,
251callables,31useState,2useEffect. Native independent report exactly reproduces
R24 files/callables/violations/scope/engines/summary/parse and exception errors.
Root fresh ORIGINAL559/23specs/full100 is independently audited
at `~/.cache/gaia-campaign/20261011-r25-original`; it does not replace reviewer
native original/candidate verification with the new immutable specification.

## Static design review

One bounded responsibility is supported by actual three consumers: Particelle,
Storico and InCass result-item tables. All three share table shell, headers,
tbody iteration and exact two-comparison outcome-cell presentation. They do not
share domain row fields, row keys, nullable fallback rules, slices or empty gates.

Prefer local typed `items`, `columns`, `renderRow` props, directly
`items.map(renderRow)`. Each caller retains the complete keyed `<tr>` and its
domain cells. Do NOT add `getRowKey` callbacks, an intermediate map wrapper,
row-family dispatch, untyped cell dictionaries, mega context or shared UI edits.
Local outcome cell receives exact success status (`imported` ONLY for Storico,
`synced` ONLY for Particelle/InCass), preserving `failed` and amber fallback.

Provisional physical plan: result-item loops3→1, heading loops0→1 and exact
outcome comparisons6→2:9→4 physical decisions/iterations. This is a prediction,
not measured credit. Other row branches move and earn ZERO reduction credit.
Native aggregate sums, callable count, effective LOC, new callable maxima and
physical source/AST review must jointly demonstrate no debt laundering.

## Behavioral invariants / test matrix

| Behavior | Existing tests | Missing | Added / result |
| --- | --- | --- | --- |
| Particelle cloned reverse latest8, nonempty valid gate | monitor/presentation | exact DOM and key reconciliation | new author spec pending; NOT RUN |
| Storico API order, all rows, table even empty | storico-monitor | exact DOM and key reconciliation | pending; NOT RUN |
| InCass first12, original-length truncation, nonempty gate | incass-monitor | exact DOM and key reconciliation | pending; NOT RUN |
| Raw case-sensitive synced/imported/failed/other statuses | existing normal status paths | imported vs synced, uppercase, unknown class witnesses | pending; NOT RUN |
| Domain keys, nullish fallback and per-cell classes | existing partial assertions | native silent polling same-key reuse / changed-key replacement | pending; NOT RUN |
| Auth, lifecycle, commands, polling, guards, progress | immutable23specs | no change admitted | full original/candidate union pending |

Key proofs must use actual mounted exported workspace and native `usePolling`.
Manual loading temporarily unmounts rows and cannot prove reconciliation.
Particelle keys include job/id/label, Storico subject/idxana/index (no job id),
InCass job/subject/identifier/index. Data transforms, result guards, table parent
wrapper classes, header/cell order, error precedence and optional payment/skipped
suffixes remain exact. No additional DOM node or changed status normalization.

## Prepared independent verification

Private runner/auditors prepared with `apply_patch` in
`~/.cache/gaia-campaign/20261011-r25-capacitas-results-review`.
They require separate phase-specific Coordinator activation manifest with frozen
source/spec SHA, approved union test count, expected HEAD/base and reviewer heavy
owner. No native phase can be invoked under current preparation-only admission.

Planned gates: focused NEW mounted specification; whole Capacitas24spec union;
native unchanged100coverage thresholds; independent raw Istanbul full-file audit
for EXACT workspace and existing fraction helper; full project typecheck, actual
new-spec import-closure typecheck, scoped lint, native full report and actual
`make complexity-ratchet BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2`.
Every native command writes command/log/exit separately and fails closed on its
first nonzero exit, without overwrite or retry. All1673official runtime inputs,
old23specs, configuration, baseline and protected main have custody guards.

Lightweight `review.py prepare` completed0: all1673source bytes match immutable
HEAD, original23spec bytes match immutable HEAD, six configuration files match,
baseline matches immutable55a, protected main diff/status remain exact.
`prepared-custody.json` preserves all source/spec hashes. `git diff --check`0;
only this NEW review report is untracked. This is static custody, not native
test/scanner/coverage certification; heavy token remains UNCLAIMED.

## Diagnostics

One lightweight read guessed absent root `20261011-r25-original/verify.py`
(`sed` exit2). Coordinator notified; actual audit recipe was located read-only.
No native test/scanner/typecheck/coverage command was started or retried.
No application failure, runtime mutation or acceptance follows that diagnostic.

## Preparation checkpoint (historical)

At the preparation checkpoint reviewer native tests, coverage, metric after/delta
and ratchet were NOT RUN. Current ORIGINAL results are recorded below.
No baseline/scope/threshold/ignore/exclusion change. No commit or merge.
Classification: `NO_CHANGE` / preparation only; final acceptance UNPROVEN.

## ORIGINAL independent admission and evidence

Coordinator updated registry before activation and imported NEW specification
using `apply_patch`: SHA256
`6c91bb4dcc2c1f3298852948b32ec564fa84d250768d4be2c28a8b3f2d323773`.
Runtime original SHA256 remains
`7f9d7883680d10f536e058323f241413fc6192fce14ca634a1b181ae107d293c`.
Static report7965 is preserved privately before amendment.
Phase-specific Coordinator admission retains HEAD9660/base55a, heavy reviewer
ownership, source/spec hashes and604approved native test count.

First activation wording excluded ORIGINAL report/ratchet, so the private runner
was briefly conditioned BEFORE any invocation. Coordinator separately explicitly
authorized both read-only gates before invocation; original prepared runner was
restored byte-exact (`b7683541`). No native command repeated or restarted.

Exact native command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 ~/.cache/gaia-campaign/20261011-r25-capacitas-results-review/review.py original --admission ~/.cache/gaia-campaign/20261011-r25-capacitas-results-review/original-admission.json
```

Native runner/session46339 terminated0; every focused/union/audit/types/
spec-types/lint/report/ratchet/diff-check command exited0 independently.
Raw commands/logs/exits and artifacts preserved in private `original/`.

| Gate | Independent ORIGINAL result |
| --- | --- |
| NEW mounted public spec |45PASS,1spec,0failed/skipped/todo |
| Whole Capacitas union |604PASS,24specs,0failed/skipped/todo |
| Workspace full-file coverage |720/720statements,750/750branches,251/251functions,627/627lines |
| Fraction helper full-file coverage |9/9statements,6/6branches,6/6functions,8/8lines |
| Native100thresholds and raw audit |PASS; two exact files, positive totals, no zero-hit arm/function/statement or skipped mappings |
| Project types / spec import-closure types |PASS;135actual imported runtime files,0diagnostics |
| Runtime+fraction+24spec scoped ESLint |PASS,0warnings |
| Full official native report |1673files,20322callables,1924errors,2740warnings,4664findings; all records exact prior R24 |
| Actual immutable55a native ratchet |PASS,findings[] |
| Before/after custody |All1673official runtime sources,old23specs,configurations,baseline and protected main exact |

Static review of the actual45cases confirms they mount the real exported
workspace, leave `usePolling` native, mock only network/auth and unrelated
protection/modal boundaries, and inspect real DOM classes/order/node identity.
They cover three exact success policies, case-sensitive status/error/other
fallbacks, valid empty-family gates, unchanged-key polling reuse, domain-key and
job-key changes, reorder semantics, nullish-vs-empty identifiers, all14Storico
rows, latest8Particelle without API array mutation and first12InCass with
original15-length truncation. No extracted handlers, fake runtime filenames,
runtime mocks, threshold lowering, skip or existing-test changes.

One read-only summary query initially used nonexistent `qualified_name` and
printed `main[]`; corrected lookup used actual `name` and confirmed324/301/2412,
nesting2/params1. No gate invocation/retry or runtime mutation followed.

ORIGINAL disposition: `ACCEPT_ORIGINAL_CHARACTERIZATION`.
Runtime candidate, after metrics, physical proof and final acceptance remain
UNPROVEN/NOT RUN; no `IMPROVED` credit. Reviewer token RELEASED, await separately
frozen candidate import and Coordinator activation. No source/spec/config or
baseline change by reviewer; no commit.

## Failed candidate ratchet — independent read-only provenance

Separate Coordinator admission allowed existing frozen report/log/baseline and
source inspection only, with no heavy token, candidate import, scanner/native
replay/test/report/ratchet retry or code/test/config/tooling edit.
Original accepted reportd996 remains preserved privately byte-exact.

Author source8ea9b7cb, native report888704f5 and native ratchet log47310921 hashes
are independently confirmed. Existing first native gate failed Make2/CLI1 with
14legacy-metric findings, all `Program<anonymous>`. This is the NEW change gate,
not historical FAIL30; it remains FAIL and prohibits integration.

The authoritative baseline is loaded from55a; its `source_commit` is
`11ed944a46ebdeb32ad50c14e7fca90b2c55f1fd`. Immutable source spans at that actual
commit were inspected, not inferred from merge-base line numbers alone.
Four physically distinct candidate records explain the14findings:

| Callback responsibility | ORIGINAL span / cog,cyc,LOC,nesting,params | Candidate span / metrics | Findings / source-backed classification |
| --- | --- | --- | --- |
| Particelle result row |1652–1662 /2,3,11,0,1 |1682–1688 /0,1,7,0,1 |2 / naming+positional misattribution |
| Storico result row |2206–2232 /10,11,27,0,2 |2223–2237 /8,9,15,0,2 |4 / naming+positional misattribution |
| InCass result row |2853–2886 /11,12,34,0,2 |2848–2869 /9,10,22,0,2 |4 / naming+positional misattribution |
| Existing modal Sincronizza onClick |3194–3215 /3,4,22,1,0 |3176–3197 /3,4,22,1,0 |4 / unchanged callback positional misattribution |

The three rows were `content:CallExpression.map[0]<callback>` or
`content:items.map[0]<callback>`, now JSX `renderRow` arrow props. Their retained
domain-keyed `<tr>` and section-owned cells are visible in the exact bounded
author diff; only shell and duplicate status presentation changed. Every listed
row metric decreases or stays equal relative to its actual ORIGINAL source.
They are not growing rerun/delete/refresh handlers.

Existing modal onClick is EXACT original/candidate span bytes, identical
fingerprint023e933d8cbd06b2, identical five metrics. Its span hash is
`2be5d0ed8a6d857c97dbe962668b5a454ac17090914a25b234c223b292cd5d04`.
The actual baseline modal callback3202–3223 has14,10,22,1,0: its prior campaign
fraction-state simplification already reduced cognitive/cyclomatic; R25 does
not change it. A1LOC close-button callback is a different responsibility.

### Concrete scanner and resolver causality

Read `js_ast_metrics.mjs` callableName119–126 and walkAll161–185: JSX attribute
ownership is not named; `JSXExpressionContainer` parent falls through to inherited
`Program<anonymous>`. The `Program` key propagates from `walkAll(ast.program)`.
Its uppercase synthetic name also makes callableKind label these arrow props
`react_component`. A label is not a behavioral or domain identity.

Read `complexity.py` resolve_baseline_callable654–734 and unique_line_tiebreak:
no exact same fingerprint exists for these four candidate anonymous records.
Same-name legacy candidates are filtered by unique-fingerprint reservations,
then nearest source span can be returned before wholly-added handling or
same-path different-name fingerprint recovery. Static distance arithmetic on
the EXISTING frozen records demonstrates four unique nearest unrelated owners:

| Candidate line | Nearest baseline physical callback | Nearest / second distance | Native comparison emitted |
| --- | --- | --- | --- |
|1682 |1683Particelle Rilancia onClick |0 /1 |LOC1→7,params0→1 |
|2223 |2230Terreni Aggiorna job onClick |0 /13 |cyc1→9,cog0→8,LOC1→15,params0→2 |
|2848 |2827InCass Elimina onClick |21 /32 |cyc1→10,cog0→9,LOC1→22,params0→2 |
|3176 |3193modal Chiudi onClick |0 /5 |cyc1→4,cog0→3,LOC1→22,nesting0→1 |

In ORIGINAL the real modal baseline span3202–3223 overlaps current3194–3215
(distance0); unrelated Chiudi3193 is distance1. R25 shrinks preceding tables,
shifting this unchanged callback18lines earlier: now Chiudi3193 overlaps the
candidate, while the true legacy modal span is distance5. This explains why a
byte-identical callback changes the gate outcome. Source-provenance R16 is called
only on `ambiguity`, not on these successful but unrelated nearest-owner returns;
therefore it cannot correct this particular attribution in the current gate.

This is concrete source-backed naming/positional attribution confusion, not a
guess from global totals. None of the four groups totaling14findings demonstrates
an actual R25 callback metric increase. It does NOT certify all candidate
semantics, whole-file AST/physical reduction or a fixed matcher; no native
comparison was executed or waived during diagnosis. Candidate remains
`BLOCKED_CHANGE_RATCHET`, not `IMPROVED` or mergeable.

### Safe separate tooling activity and required tests

A separate explicitly owned tooling task could investigate stable JSX callback
ownership and preventing synthetic same-name nearest-line guesses from claiming
unrelated legacy owners. Preserve engine/baseline provenance, all ordinary
primary-metric comparisons, reservation multiplicities, scope and error gates.
Do not simply filter14findings, loosen thresholds, force new ownership or
regenerate baseline. Any design must prove ownership or fail closed.

Required real non-regression contracts: JSX row prop versus unrelated nearby
onClick; unchanged callback shifted across adjacent unrelated baseline span;
actual legacy callback whose metrics really increase; existing fingerprint
renames/moves; same-shape duplicates and reservation/multiplicity; callback
reorders and partly added spans; shifted/removed/inlined owners; source/report
staleness and ambiguous owners. Run full tooling100coverage and exact frozen
candidate native55a replay ONLY after separate admission; passing matcher alone
would still not grant independent runtime candidate acceptance.

Diagnosis reader initially treated file-level numeric `callables` as a list,
raising TypeError while summarizing existing JSON. Schema was inspected and
corrected to top-level `baseline.callables`, without native retry or file changes.
The diagnosis manifest retains four exact record origins/fingerprints/metrics
and selected unrelated spans. No application failure or runtime edit occurred.

Disposition: `BLOCKED_CHANGE_RATCHET / SOURCE_BACKED_MISATTRIBUTION`.
Freeze this read-only review and private diagnosis; stop. Heavy token UNCLAIMED;
no candidate imported, native rerun, commit, baseline inflation or gate waiver.
Final lightweight custody0 revalidates all1673reviewer original source inputs,
old23specs, admitted NEWspec6c91, configs/main/baseline unchanged after diagnosis.

## Residual risks / next action

- Candidate must not merely move callbacks/JSX; aggregate and physical proof required.
- Added callback identity ambiguity requires STOP, not baseline repair.
- New tests must reject DOM/key/status drift through real public mounted behavior.
- Full original/candidate coverage and unchanged historical30 provenance mandatory.
- Coordinator imports frozen inputs and admits serial ORIGINAL token only after
  author freeze/release; then independent review, not automatic acceptance.
