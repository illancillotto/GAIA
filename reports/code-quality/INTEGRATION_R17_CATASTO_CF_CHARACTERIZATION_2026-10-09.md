# R17 — Original Catasto CF wizard characterization checkpoint

## Status and scope

**ACCEPTED AND INTEGRATED — ROOT CHANGE RATCHETS PASS0.** Global campaign
**ACTIVE / INCOMPLETE**. Test-only slice: CF wizard loading, editable drafts,
application and refresh ordering. No Comune, Particella or AdE expansion;
no runtime refactor or complexity reduction is authorized or claimed.

Coordinator initial integration HEAD: `08e85360c581c1005426524d27055af8d4236a51`.
Author: `/root/r17_catasto_cf_original`, existing dedicated Catasto worktree,
HEAD `3b120c3ecfcb8e8b3544a4361ac35a1543a83590`, tracked content identical to
certified `ca203378`. Main/merge-base remains authoritative
`55a1b1d35911451e018b662c2acc450bf5994ea2`.

## Ownership and frozen inputs

Registry: `docs/code-quality/MULTI_AGENT_OWNERSHIP_R17_CATASTO_CF_CHARACTERIZATION_2026-10-09.md`.
Author writes only its new spec and characterization report. Independent
reviewer `/root/r17_cf_review` writes only its new review report. Coordinator
owns governance and integration. Existing clean terminal R16 review worktree
is reused on new dedicated branch `review/complexity-r17-catasto-cf`; old branch
is preserved. No new large checkout, reset, stash, cleanup or dirty-main import.

| Frozen input | SHA256 |
| --- | --- |
| Original anomalies page | `855e3ef09296d8024f894118ef6e9c0d6bf13dc63b4f653c6ce6202407a732f7` |
| New CF spec | `e4b97fcc3460641482b01f8d6b55b804b1c7f1d374f11b6cb0f60417e98840a2` |
| Author characterization | `b882beec4f3bd094f84f4fa2c973e69e8bdef623d1b61aa8d1ca48b13dca3545` |
| Author freeze, 38 entries / zero mismatches | `c5dca3e48156f74dab1a7e6303684bd38658c266c76273a35b382df159168b12` |
| Reviewer protected tracked-input manifest | `81de1797dff08253389376f2516f630f24b64294d8feab65259d1e953dc2930d` |
| Unmodified complexity baseline | `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95` |

Author protected manifest verifies 3541 original tracked paths, including
tracked TS build information. All eight author gates are terminal; exclusive
heavy resources were explicitly released before reviewer activation.

## Author characterization and gates

The real page is imported; API/auth/navigation/container/external-modal
boundaries are mocked. Public interactions assert literal requests, response
rendering, pending edits, normalized apply values, missing token handling,
error/fallback behavior, pagination and refresh ordering. No private handlers,
runtime clone, threshold override or implementation replacement.

| Author gate | Actual result |
| --- | --- |
| New focused CF spec | 34 PASS, zero skip/failure |
| New spec + original P4 manual + utility union | 150 PASS, three specs, zero skip/failure |
| Full-file coverage union | 150 tests PASS; coverage exit 1, unchanged 100% thresholds unmet |
| Project and separate tests-inclusive TypeScript | PASS, incremental disabled; tracked build information unchanged |
| Scoped lint | PASS, zero errors/warnings |
| Fresh original page AST | PASS; every file/callable/violation object unchanged |
| Actual immutable55a Make ratchet | PASS, exit 0, zero findings |

Original P4 DataTable `act(...)` warning remains in union logs and is not
suppressed. No author retry, configuration fix, source edit or commit.

## Actual complete-file coverage and runtime stop

| Dimension | Covered / total | Percent | Missing | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Statements | 449 / 643 | 69.82% | 194 | 0 |
| Branch arms | 342 / 645 | 53.02% | 303 | 0 |
| Functions | 125 / 194 | 64.43% | 69 | 0 |
| Lines | 416 / 595 | 69.91% | 179 | 0 |

One actual original source key, no virtual clone or restricted denominator.
All missing locations are retained in author's `coverage-analysis.json`.
The expected full-file coverage gate remains **FAIL100**. This useful test-only
characterization does not waive coverage: runtime remains **BLOCKED_COVERAGE**.
Historical P4 coverage is attributed, not a fresh standalone before run.

## Metrics and classification

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive | 390 | 390 | 0 |
| Principal cyclomatic | 342 | 342 | 0 |
| Principal effective LOC | 2109 | 2109 | 0 |
| File effective LOC / callable count | 2267 / 197 | 2267 / 197 | 0 / 0 |
| File cognitive / cyclomatic | 794 / 868 | 794 / 868 | 0 / 0 |
| File useState / useEffect | 24 / 10 | 24 / 10 | 0 / 0 |
| File errors / warnings | 11 / 16 | 11 / 16 | 0 / 0 |

Classification: **NO_CHANGE — ORIGINAL_CHARACTERIZED**, never IMPROVED.
Certified aggregate runtime metrics remain 1672 files / 20316 callables /
1926 errors / 2740 warnings / 4666 findings; tail 5 above cognitive300,
17 above200 and 55 above100. These aggregates are attributed to the last full
runtime report, not a newly executed R17 global scan. Source is unchanged.

## Independent review and integration

Independent reviewer freshly reproduces focused34 / union150 PASS with zero
failure/skip, exactly the same actual full-page coverage FAIL100, TypeScript,
lint and immutable55a ratchet PASS0. Every original page/file/callable/violation
object matches both original Coordinator and fresh author records. All3546
reviewer protected paths remain exact. Report SHA256
`22326c23ac48b38069708be580e09c14061029f00e6f7a2c350f5ce88e3b10cc`;
48-entry final freeze SHA256
`fd39ac154d52cc7a411b6411f31634ed350088a96f22b5193d34231c01eab291`.
All reviewer heavy processes are terminal and explicitly released.

A private Node evidence-parser attempt failed because it located the opening
brace in Make's `${BASE_REF:-origin/main}`, not the JSON report. Coordinator
authorized only private parsing correction of that already terminal log;
analysis then PASS0. Original failure is retained, no gate was rerun and no
source/config/tooling changed. This is an explained evidence-helper incident,
not a hidden passing test or a source failure.

Coordinator publishes author35a1d1f5 and reviewer1d4bf80d as distinct coherent
commits. Accepted author publication35a1d1f5→2e33f0b9 and independent review
1d4bf80d→14ef9962 each passed a separate actual root immutable55a Make ratchet,
exit0/findings[]. Source/spec/CHAR/review hashes match approved frozen inputs.
Root runtime/config/tooling/baseline/package/Playwright diff against initial
08e85360 is empty. Logs: `publication1-ratchet.log`, `publication2-ratchet.log`
inside Coordinator evidence. Closure documentation is still being finalized.
Dedicated `make graphify-platform-docs` completed exit0, chunk1/1done, no
semantic chunk failure:647nodes876edges105communities,7137input2940output
tokens, estimated$0.0076. `graph-platform-docs.log` is retained; graph ignored.
This is documentation maintenance, not runtime complexity or behavior proof.
No runtime architecture changed. Closure's actual postcommit immutable55a
gate is retained as `postcommit-ratchet.log` in the same evidence directory,
separately from both publication gates; its outcome is not inferred from them.

## Other failures and limits

GIS E2E synchronization fix is already integrated in `286a82cc`; current spec
hash exactly matches approved `51f783e310aaa21f9feaeb868605058e489fbeaf4131270070503013413a95bf`.
Independent final evidence: focused repeat10 PASS, GIS5 PASS, full E2E54 PASS
with seven preexisting skips. These are previous certified runs, not R17 reruns.
See `reports/code-quality/VERIFICATION_GIS_E2E_FIX_2026-10-09.md`.

R16 Capacitas original full-file coverage is certified 100%; candidate remains
BLOCKED for ambiguous matching, not insufficient original coverage. No candidate
diagnosis or application is authorized here. Historical globalcheck30 remains
separate provenance, not attributed to these test-only changes or repaired.

Latest main binary diff SHA256 `9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`
and status SHA256 `0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`
are unchanged. Host disk capacity is critically low; ENOSPC must stop work,
not trigger unauthorized cleanup or uncontrolled retries. Build, E2E and full
application suites are not rerun or claimed PASS by this slice.

## Evidence and next boundary

Author: `~/.cache/gaia-campaign/20261009-r17-catasto-cf-original/`.
Independent reviewer: `~/.cache/gaia-campaign/20261009-r17-cf-independent-review/`.
Coordinator: `~/.cache/gaia-campaign/20261009-r17-coordinator/`.

Independent acceptance and sequential test-only publication are complete.
Any additional wizard characterization requires a separately allocated coherent
slice. No runtime decomposition until complete-file coverage is genuinely100%.
Global campaign objectives remain incomplete; this checkpoint is not closure.
