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

Updated source `1d8c8411`, accepted as `b0a4ac2a`, supersedes the five-arm
UNKNOWN statement below. Real native keyboard navigation reaches a background
row's enabled Risolvi control, replaces the busy modal, then closes the new
non-busy modal before the old API Promise settles. Six real-browser cases
(normal/StrictMode × success/failure/rejection) and precise V8 range coverage
prove null-arm execution at3214/3217/3220. These three defenses are necessary
and must remain. Only3166/3206 are still UNKNOWN. Independently reproduced
audit: `/tmp/gaia-modal-probe/coordinator-audit.log`, six witnesses/nine null
executions. Official union coverage still903/929 until C12 is independently
integrated; browser evidence is not added to Vitest counters. See
`CAPACITAS_MODAL_REACHABILITY_2026-10-08.md`. Historical line-number spellings
in the paragraph below do not replace current source locations.

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

Missing-sheet guards285/382 are **REACHABLE** with actual no-sheet OOXML
bytes. Root disposable probe serializes a real workbook, rewrites its
`xl/workbook.xml` sheet collection to `<sheets/>` through actual CFB ZIP
serialization, then parses the bytes with unmockedSheetJS0.20.3:SheetNames[].
Original15887bytes versus modified15834bytes; `/tmp/capacitas-empty-workbook.xlsx`
SHA256`e183290b3d727164c295d684b6098419d164ae4821734bd2ab9f04d346836da8`.
This is a malformed upload accepted by the parser, not a fabricated parser
return. `/tmp/capacitas-empty-workbook-probe-corrected.log` exit0; first attempts
failed CFB relative-path lookup/update, corrected archive paths only. C9 owns
two real UI upload characterization cases separately; it must be reviewed
before integration. This evidence does not remove either guard.
There may be additional uncovered defensive arms outside this initial ledger.

Integration4 complete residual ledger39arms identifies five further
construction-impossible candidates, bringing the conditional proved total
to21 (five modal guards stillUNKNOWN):

-258 `normalizeImportHeader(value ?? '')` only receives `Object.keys` string
  elements, never null/undefined; the function is private and has no other
  callsite. Empty raw header string still does not take the nullish arm.
-2482 commune/sub nullish fallbacks and2483/2484 label/commune fallbacks,
  four arms. Batch items come exclusively from the reader's constructed
  normalized strings and computed label. Mandatory commune/foglio/particella
  are validated nonempty; optional sub is always a string including empty.
  No API job result supplies this local preview list and no UI setter allows
  a user to insert null. A fake setter or private callback is not coverage.

These retain their guards unchanged. Other13 residual arms are assigned to
C10/C11 genuine presentation/snapshot/toggle cases; their coverage is pending,
not inferred. Source ownership remains test-only.

## Decision boundary

Current Integration6 report `f8c4f670`, source `53e9405b` integrated `acdc9515`:
actual312-test/16-spec union covers906/929 arms (97.52%), full-file gate FAIL.
The three genuinely reachable late-response guards3214/3217/3220 are now
characterized, not removed; no previous arm loses coverage. Complete residual
ledger23 arms/22 source lines:21 conditional construction/library candidates
plus two modal arms3166/3206 still UNKNOWN. Artifact
`/tmp/gaia-capacitas-integration6-residual-ledger.json`. Runtime remains unchanged.
The five-arm UNKNOWN and26-arm ledgers below are explicitly historical.

Integration5 report `7c7dcc0c` independently accepts C10/C11 and measures the
actual fifteen-spec union:306 PASS,903/929 branch arms (97.20%), full-file gate
FAIL. All13 assigned reachable arms now have genuine hits, with no previously
covered arm lost. The exhaustive residual ledger contains26 arms on25 source
lines, with no missing location: the21 conditional construction/library
candidates above and five modal UNKNOWN arms. Artifact
`/tmp/gaia-capacitas-integration5-residual-ledger.json`, SHA256
`41d341b0d1f5f7ef32cc41427b56a19cf91ce2980e9696e2de43d82e8e298512`.
This closes the assigned reachable-path test work, not the runtime coverage
policy or modal-race proof. Runtime and all defensive expressions are unchanged.

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
