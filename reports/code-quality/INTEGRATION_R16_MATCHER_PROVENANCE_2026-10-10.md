# R16 matcher — separate source-provenance fix

## Authorization and snapshot

User approves a separate matcher activity after R19 closure54705ef8; main and
authoritative merge-base55a1b1d35911451e018b662c2acc450bf5994ea2 unchanged.
Ownership registry precedes activation; author/reviewer/final verifier have
separate dedicated branches/worktrees, exclusive writable report/test paths.
Application runtime, baseline, thresholds, scope, existing tests and retained
R16 artifacts are not changed. Candidate34af is not applied or integrated.

## Fix and invariant

Existing matcher priorities remain unchanged; only a residual ambiguity can
request a source-bound proof. Immutable bytes use baseline.source_commit
11ed944a46ebdeb32ad50c14e7fca90b2c55f1fd via Git without replacement refs.
Fresh scans bind every per-path callable record (kind/name/span/fingerprint/
all primary metrics) to both source snapshots. Verified zero-context diff,
unique unchanged exterior anchors on both boundaries and one mapped baseline
span establish ownership. Missing/stale/ambiguous proof retains exit2.
Local success/refusal snapshot cache and owner ledger prevent context-race
or duplicate consumption. Exact/fingerprint/multiset reservations still apply.
Exterior `source_paths` provides bytes, never identities or arbitrary mappings.

## Accepted evidence

Frozen runtime871ebffc4742c7bdf0a8847dfac7d91132d862953179599c2ce27531f0b99f43;
newtestd2752caceeec3f13d9ee03a69caaedaeea10139864ca7067d2fc9663042e9dd6;
SLICE30a16375d8b23bbabccc7f1f28a57dd56d068bac291a09f7387597ea254c9170.
Independent reviewcdbe69a53744ae5e8b5c1a676f9b0eaa971d9d3db14cb8d49e5c653ff0538562
explicitly ACCEPT_TOOLING_ONLY. No complexity-reduction classification.

| Gate | Author | Independent |
| --- | --- | --- |
| Full tests/code_quality suite |215 PASS |215 PASS |
| Full modified runtime statements / branches |844/844 +332/332,100% |844/844 +332/332,100% |
| Missing / partial / excluded |0 /0 /0 |0 /0 /0 |
| Actual55a Make complexity-ratchet |PASS0 findings[] |PASS0 findings[] |
| Style / Ruff / new-test format |PASS0 |PASS0 |
| Protected tracked / retained inputs |3569 /237 exact |3569 /237 exact |
| Full-context original / candidate / faithful / local exits |0 /0 /0 /0 |0 /0 /0 /0 |
| Below-threshold legacy cognitive12→13 |native1 |native1 |

Independent extra byte-negative freshly scans real Sincronizza conditions:
native1, cognitive14→47 and cyclomatic10→26 on outer/inner handler. Complete
236-path faithful metadata preserved, fresh250path records within full1672files/
20317calls. Passing projection does not prove UI behavior/coverage equivalence.
Real pre-race draft fails equal-signature alternating-anchor contract; final
cache/ledger contracts pass. Git replacement refs, malformed commits/Python,
stale/forged records, repeated/moved callbacks, duplicate owners/consumers and
malformed hunk cases are tested without weakening existing contracts.

## Failure accounting

Intermediate full suites192PASS/99.81% and208PASS/99.82% fail100% honestly;
missing branches completed with genuine tests. Pre-race213/829+326 belongs
only to that earlier draft, not final source. Initial postpatch old ambiguity
expectation fails0vs2; unchanged resolver and missing-proof exit2 controls
preserve characterization while new bound proof is expected0.
Private custody script missing replay/ path fails before authorized correction.
First independent extra negative wrapper drops non-Capacitas diff metadata,
returns unrelated Presenzeambiguity2 and assertsFAIL1; raw wrapper/log/result
preserved. A separate authorized corrected private probe yields real native1.
No source/test/config/baseline weakening or erased failure.
Coordinator import first patch rejects numbered hunk header, no edit; normalized
apply_patch import hashes exact. Invalid tool wait/lookup requests change no
files or gates; these are bookkeeping failures, not successful validation.

An additional final verifier started a fresh suite before late pause arrived;
entire owned process tree SIGSTOPped, then same processes SIGCONT after old
reviewer probe terminal. Brief overlap disclosed, not perfect serialization.
No kill/retry or runtime edits. Its final certificate is recorded separately.

## Complexity cost and limits

Tooling outside unchanged official application scope: compare cognitive85 and
cyclomatic41 unchanged, LOC85→92/params4→5; aggregate cognitive561→671 and
cyclomatic424→510 reflect added proof functionality. All new helpers below
callable error thresholds, but warnings remain. **TOOLING_FIXED / NO_CHANGE
application runtime**, not IMPROVED. No automatic next hotspot or candidate
runtime acceptance; full global campaign remains ACTIVE/INCOMPLETE.

Evidence: `~/.cache/gaia-campaign/20261010-r16-matcher/`, independent
`~/.cache/gaia-campaign/20261010-r16-matcher-review/`, final
`~/.cache/gaia-campaign/20261010-r16-matcher-final/`. New root gates/publications
are appended after execution; no inference from author checks. Historical
global30 provenance remains distinct from change ratchet and is not absorbed.
Platform docs Graphify required for documentation; no supported code target
contains this tooling and no application dependency/component boundary changes.

## Final independent acceptance and publication

Distinct final task01a1274c-5903-7c81-8a87-499bed8a4fae ACCEPT_TOOLING_ONLY,
report818eabb36d6296b7925794c07560225cd5058df6bdd650af4e6ac29d41205fa5.
Fresh215PASS/full844+332100%, actual55a/style/Ruff PASS0, full-context replay
0/0/0/0/negative1 and independent byte-negative1, custody exact. Same paused
processes resumed, no kill/restart. All agents terminal and heavy RELEASED.

| Publication | Dedicated commit | Integration commit |
| --- | --- | --- |
| Tool, new test and SLICE |b3d4377f8c999e2ac59d3a00e34f55cf4dae3818 |269d3f09 |
| Independent ACCEPT review |a7fae4d23069a7b1b9948f30cd83f9be5f5a17ca |e8c8d4d5 |
| Final independent verification |392b0da7fc783a8c0cad8c822fadb9994c11f480 |b3efb126 |

Actual immutable55a Make ratchet AFTER EACH integration PASS0/findings[].
Logs `/tmp/gaia-r16-matcher-{author,review,final}-integration-ratchet-20261010.log`
and matching `.exit` files. Root full-tooling coverage and final baseline status
recorded separately after execution, never inferred from earlier gates.

## Root integrated verification

On integrated b3efb126, the fresh complete tooling suite passes215 tests in
31.88s. Runtime coverage is844/844statements and332/332branches,100% each;
missing/excluded lines and missing/partial branches are all zero. Installed-
interpreter style ratchet exits0. Native logs, JUnit and coverage counters:
`/tmp/gaia-r16-matcher-integration-20261010/` (`tooling`, `style`, `report`
exit files all0). These are root execution results, not inferred agent results.

Fresh full application report exits0:1673files/20320callables/1926errors/
2742warnings/4668findings. Every application metric object equals the post-R19
report; only generated_at, provenance and source_commit differ. The application
runtime diff from54705ef8 is0bytes. Report:
`/tmp/gaia-complexity-after-r16-matcher-20261010.json` and `.md`.

`make complexity-check QUALITY_PYTHON=backend/.venv/bin/python` remains
FAIL (CLI1/Make2), with exactly30 findings, byte-value-equivalent JSON finding
objects in the same order as the retained post-R19 global check. No finding is
new or absorbed. Global status and change ratchet remain separate.

Main binarydiff SHA256 remains9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b;
main status SHA256 remains0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87.
No cleanup, main edit, candidate application or baseline repair was performed.
The global campaign remains ACTIVE/INCOMPLETE. Candidate R16 needs its own
UI equivalence and full-file100% gate; this tooling closure does not accept it.

Documentation refresh and actual postcommit immutable55a ratchet evidence are
retained under the root evidence directory, with native exit files. A docs
refresh exit0 alone does not prove semantic extraction success.

Dedicated `make graphify-platform-docs` exits0 with chunk1/1done and no
semantic-failure warning:693nodes/941edges/108communities;167cache hits,
6files re-extracted;18058input/3316output tokens, estimated$0.0125. Base-URL
patch target exits0. Graph artifacts stay ignored and are not metric evidence.

Additional read-only comparison against the authoritative initial audit JSON
also confirms the exact30 finding objects/order. First diagnostic path lookup
failed because the audit JSON is absent from integration; the preserved main
copy was read instead. No native gate rerun or source/input modification.
Baseline SHA256 remains38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95;
diff of config/code-quality and Makefile against55a is0bytes.
