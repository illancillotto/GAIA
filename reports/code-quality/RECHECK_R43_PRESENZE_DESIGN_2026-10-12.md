# R43 — Presenze design recheck

## Ownership and disposition

Independent reviewer `/root/r43_design_recheck`, assigned by
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R43_DESIGN_RECHECK_2026-10-12.md` in
integration. Existing reviewer branch `review/complexity-r43-presenze-profile-policy`;
HEAD `114fbf7196382c6446a7963c34bd89e4c9795ef5`, main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. The pre-existing review report is
untracked and preserved. Only this new report is written.

**No new runtime design defect identified within the supported editor contract.**
This is a static recheck, not admission: R43 remains
**BLOCKED_TEST_SPEC_TYPES / NOT_ADMITTED**. The user selected a fresh design,
not a silent retry of R42 or authorization to repair immutable fixtures.

## Inputs checked

- Integration original page SHA256:
  `deb4e9a072c1876a0fc67ca0398a727d06c826aaaadc104bc262f45211273cf8`.
- External author candidate page SHA256:
  `64afdc85697e10946ee9c34c8545f410a0a0ac263842a33a13c67cffc69a93c0`.
- Reused test SHA256:
  `16a209cb4925c5f5cd47d4978328d75130b08b8ca951212cacf15bdb8cfcead4`.
- Original/candidate byte diff contains only the typed
  `normalizeContractProfileEditor` helper and the contract-kind effect change.
  Adjacent hydration/reset effect, inputs, API, permissions and JSX are unchanged.
- Previous independent review, integration HOLD report, final HOLD report,
  frozen native diagnostic/argv/exit files and current immutable manifests were
  read directly. No existing launcher or scanner was executed.

## Policy boundary and invariants

The pure policy receives latest nullable editor state and separately captured
rendered contract kind. React scheduling remains in the original effect. These
are different responsibilities; substituting `current.contractKind` for the
captured kind would change deferred-update behavior and is not part of R43.

| Behavior | Recheck conclusion |
|---|---|
| Rendered editor null | Original outer guard still prevents scheduling any updater |
| Latest editor null when updater executes | Helper returns exact null before accessing editor fields |
| Captured operaio | Always clone latest non-null editor; preserve group; minutes use logical OR with `420` |
| Captured impiegato | Always clone latest non-null editor; clear group, then apply logical OR with `385` |
| Other captured kind and falsy latest group | Return exact latest object identity, with no clone |
| Other captured kind and truthy latest group | Clone and clear only group |
| Rendered kind differs from latest editor kind | Captured kind selects policy; latest fields supply values and are spread unchanged |
| Truthy minute strings | `0` and whitespace remain unchanged; empty string defaults only for operaio/impiegato |
| Effect dependencies | Sole `[contractProfileEditor?.contractKind]` dependency is byte-identical; group/minutes changes alone do not rerun the effect |
| Setter scheduling | One functional updater remains scheduled for every non-null rendered editor; none is scheduled for null |
| Property/override ordering | Spread latest editor first; impiegato overrides group before minutes, exactly as original |
| Hydration/reset ordering | Neighboring effect and hook order unchanged; latest-null race protection remains inside updater |

Supported editor values are nullable plain records built from object literals
and spreads, with typed string fields. The helper does not mutate those
records, including during React updater replay. Arbitrary accessors/proxies
could observe fewer rendered-kind property reads; universal equivalence for
such out-of-contract objects is not claimed. No unrelated identity mapping,
network, save, authorization or synchronization behavior changes in this diff.

## Failure lineage and custody

R42 remains rejected for the real surviving-callback regression: cognitive
`2 -> 8`, cyclomatic `3 -> 7`, LOC `7 -> 18`. R43's source-policy design is
distinct; this recheck neither renames away R42's failure nor retroactively
admits it.

Direct metadata-only rehash of author STOP manifest:
`f5f9af52e490a64567cb0a917537cdc5de8971e94c696749173f6ee4bf60a0c0`,
47 entries, **0 drift**. Final HOLD manifest:
`2f7cc5d19b146342fe51c141f885a711c0b4768b09e25e89f6f17db4954ceac9`,
14 records, **0 drift**. Both manifests and every member remain untouched.

Author native session 88643 stopped terminal exit 1 at the first supplemental
strict test-source type failure. Its preserved log has exactly:

1. **TS2352**, `tests/unit/campaign-presenze-contract-profile-r42.test.tsx:39`
   through the assertion on line 53: incomplete object cast as
   `PresenzeDailyRecord`; 44 required fields absent. The diagnostic explicitly
   names `application_user_id`, `schedule_code`, `maggiorazione_minutes`,
   `override_straordinario_minutes` and 40 additional fields.
2. **TS2769**, the same file at line 69, column 82: `exact: true` is not a
   supported `ByRoleOptions` property in `screen.findByRole`.

These are immutable reused test-source defects, not runtime diagnostics
demonstrating a changed normalization behavior. The supplemental checker keeps
strict mode, all 662 configured roots plus three extra roots, no removed roots,
`noEmit: true` and `incremental: false`. The ordinary application typecheck
does not substitute for strict certification of this excluded test file.

| Gate | Preserved author evidence | This recheck |
|---|---|---|
| Preflight/diffcheck | Exit 0 | Not rerun |
| Mounted characterization | 506 pass, 0 fail/pending/todo; eight spec files | Not rerun |
| Full-page coverage | Statements 1036/1036, branches 1102/1102, functions 305/305, lines 849/849 | Recorded author output only; no new raw coverage certification |
| Official types | Exit 0 | Not rerun |
| Supplemental strict spec types | Exit 1, exactly two diagnostics | Frozen log inspected; not rerun |
| Lint/full report/ratchet/raw audit | NOT_RUN after STOP | NOT_RUN |
| Independent final/root native gates | NOT_RUN | NOT_RUN |

## Prospective metrics, not accepted delta

| Scope | Before | Prospective R43 | Delta |
|---|---:|---:|---:|
| Principal cognitive | 360 | 347 | -13 |
| Principal cyclomatic | 316 | 308 | -8 |
| Principal LOC | 1945 | 1922 | -23 |
| File cognitive sum | 1048 | 1023 | -25 |
| File cyclomatic sum | 1191 | 1174 | -17 |
| File effective LOC | 2803 | 2801 | -2 |
| Physical AST decisions | 587 | 585 | -2 |
| Policy/effect/updaters cognitive total | 21 | 9 | -12 |

Numbers are read from the existing static prospective evidence; no fresh
scanner or authoritative ratchet has certified the candidate. Helper cognitive
8, cyclomatic 7, LOC 21, nesting 1 and two parameters remain below thresholds.
Helper cognitive 8 exceeds the old three updater sum 7: that increase remains
explicitly disclosed because dispatch responsibility moves from the effect.
Two duplicated null guards actually disappear; the full policy boundary and
physical-decision totals decrease, unlike a same-debt helper move. This is a
plausible bounded improvement, not accepted `IMPROVED`, not 25 independent
problem removals and not extreme-tail elimination: principal 347 remains >300.
Hook counts remain 21 useState and 13 useEffect. No baseline or threshold change.

## Next authorized step

Wait for the distinct test-only fixture decision. If granted, use fresh
provenance and evidence paths, construct a fully checked valid DTO fixture
while preserving existing supplied values/actions/assertions, and remove only
the unsupported role-query option while preserving exact string-name matching.
No `unknown`/`Partial` escape, weakened roots, regex query or gate bypass.
Because fixture bytes change, repaired tests require fresh characterization on
the admitted original before candidate verification; immutable old tests are
not silently relabeled. Preserve the existing first-failure lineage.

No runtime rewrite is recommended by this static recheck. Coordinator must
still obtain genuine required gates before admission. No tests, scanner,
builds, Graphify extraction, commit, baseline/config edit or source repair was
performed. No dependency/service/component boundary changes were made here;
Graphify integration maintenance remains Coordinator-owned after admission.
Stop after this report; campaign remains ACTIVE/INCOMPLETE.
