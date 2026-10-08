# Capacitas — Defensive Branch Provenance

## Scope

Coordinator read-only ownership3bf3925a. Workspace runtime SHA256
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`, unchanged
from authoritative55a1b1d3. This ledger grants no coverage exemption, runtime
ownership, guard removal, threshold/config change or baseline update. It does
not claim full-file100%, nor characterize every remaining uncovered behavior.
Registry/report evidence is separate from refactor acceptance.

## Construction-impossible fallback arms

The following nine arms from the initial V8 ledger are not reachable with
standard JS builtins and genuine inputs accepted by this implementation.
Branch IDs are artifact-specific; source expressions/lines are authoritative.

| Locations | Arms | Reason / invariant | Classification |
| --- | ---: | --- | --- |
|281,378 `file.name.toLowerCase().split('.').pop() ?? ''` | 2 | String split with a non-empty string separator always returns at least one element, even for empty names/no dot; pop therefore returns a string | CONSTRUCTION_UNREACHABLE |
|314,315,316,317,318 Terreni `headerMap.get(selectedKey) ?? selectedKey` | 5 | Selected alias comes from a Set of the same normalized Object.keys used to populate the Map; values are raw keys, necessarily strings, including empty string | CONSTRUCTION_UNREACHABLE |
|404,405 Storico same Map fallback | 2 | Same construction; optional key false branch is meaningful, but when key exists its mapped value cannot be null/undefined | CONSTRUCTION_UNREACHABLE |

`normalizeImportHeader` returns a string. `pickImportColumn` returns an alias
only if the Set contains it. The Map iterates the same first-row own enumerable
keys; duplicate normalized aliases can overwrite precedence but cannot remove
an entry or store undefined. Selection and access are synchronous, with no
interleaved mutation or user callback between construction and lookup. No
monkeypatch of String, Array or Map is legitimate coverage for these arms.
The proof does not authorize changing normalization or alias precedence.

## Installed SheetJS contract-dependent arms

Installed `xlsx` version0.20.3. Local library source `xlsx.mjs` SHA256
`1a0fb062ee9781b13f6687371b202aaefc53b6ce55b530c027e01f9c087b77db`.
Inspection limited to the two directly relevant serialization functions:

- `make_json_row` at27487 initializes `row` to `{}` with the actual options
  used here (header omitted), returning `{row, isempty}` or throwing.
- `sheet_to_json` at27531 initializes a fresh `out=[]`, index0, appends only
  `out[outi++]=row.row`, then sets length toouti. Empty/hidden source rows may
  be skipped, but do not create holes in the returned array. Success returns
  dense non-null object rows; a parser failure throws before caller iteration.

| Locations | Arms | Installed contract | Classification |
| --- | ---: | --- | --- |
|291,293,388,390 `data[0] ?? {}` after nonzero length | 4 | First returned element exists and is object, not null/undefined | LIBRARY_CONTRACT_UNREACHABLE |
|313,403 `data[index] ?? {}` for `index < data.length` | 2 | Output is dense, every indexed element is object | LIBRARY_CONTRACT_UNREACHABLE |

This is a proof conditional on **installed version and actual options**, not
a forever guarantee for future library upgrades or substituted parser mocks.
Type overloads returning generic arrays alone would not prove density. Sparse
fabricated sheet_to_json output would violate the inspected implementation.

Disposable corroboration `/tmp/capacitas-library-contract-probe.cjs` uses real
serialization/parsing for eight CSV/XLSX inputs: normal records, interior
blank rows, header-only and empty sheets. Command
`node /tmp/capacitas-library-contract-probe.cjs` exit0, observations in
`/tmp/capacitas-library-contract-probe.json`, no network or repository edits.
It checks own indices and non-null object rows. This finite experiment
corroborates, but does not replace, the library-source argument. It is not a
UI characterization test or a contribution to workspace coverage.

## Race-dependent modal arms remain unresolved

C4 sourcee9577559 adds an additional construction-impossible arm at2056:
after `Array.isArray(job.payload_json?.items)` succeeds, the same plain JSON
array is synchronously reread as `items?.length ?? 0`. Its length is defined,
so the nullish fallback cannot execute. Plain API JSON has no accessors; no
async yield occurs between checks. This does not cover fabricated getter side
effects or grant permission to remove the guard. Initial15-arm ledger is
therefore not exhaustive; this one brings proven candidate arms to16, still
separate from the five unresolved modal arms below. C4 appropriately retains
the defense and reports31/32 monitor branch arms rather than claiming100%.

Five `setResolveModal(prev => prev ? ... : null)` false arms at3166,3203,
3213,3217,3220 remain **UNKNOWN_REACHABILITY**, not proven dead:

- Modal renders controls only while state exists, but handlers and async
  requests may outlive the rendered state.
- User close is disabled while busy; unmounting does not demonstrate that a
  queued updater was evaluated with null. Invoking a detached private closure
  or forcing React state would not demonstrate a user-reachable race.
- C7 characterizes real close/busy transitions and retains these five arms;
  no artificial updater execution or full coverage claim.

Also do not infer missing-sheet guards285/382 are unreachable from this proof:
empty or corrupt workbook formats need their own actual parser evidence.
There may be additional uncovered defensive arms outside this initial ledger.

## Decision boundary

Test-only characterization can close legitimate reachable paths but cannot
honestly cover the nine standard-language construction arms, nor these six
installed-library arms using impossible fixtures. Full-file gate remains
FAIL and runtime refactoring remains unauthorized. No exclusions, ignores,
scope shrink, baseline repair or fake tests are proposed.

If later pursuing runtime cleanup, first obtain explicit Coordinator/user
decision for one separately owned behavior-preserving defensive-expression
slice, prove input/library invariants and preserve exceptions/alias ordering.
Do not remove the unresolved modal race guards under this evidence. Full-file
coverage and complexity ratchet remain prerequisites on the resulting runtime;
removing15 arms alone cannot resolve the many uncharacterized other paths.
GIS runtime risk decision also remains separate and pending. This report
does not reduce complexity and is **NO_CHANGE — PROVENANCE_ONLY**.
