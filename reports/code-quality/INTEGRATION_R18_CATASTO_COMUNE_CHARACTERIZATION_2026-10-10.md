# R18 — Original Comune characterization integration

## Ownership and snapshot

Dedicated integration branch `refactor/complexity-campaign-20261008` only;
start218670c73b7abdcb0210e61ac04e15271c9ebc41, authoritative baseline/merge-base
55a1b1d35911451e018b662c2acc450bf5994ea2. R18 author and SAME independent
reviewer completed their exclusive allocations; heavy explicitly released.
Coordinator exclusively publishes accepted artifacts and runs closure gates.
R19 V1 rejected, R16 ambiguous candidate excluded, main concurrent work preserved.

## Independent test-only acceptance

| Gate | Actual independent result |
| --- | --- |
| Final frozen original spec |46PASS, zero fail/error/skip |
| Original P4/utility/R17/R18 union |196PASS, zero fail/error/skip |
| Union with actual full-page coverage |196PASS, coverage gate FAIL1 |
| Project and tests-inclusive types |PASS0, separate native executions |
| Scoped lint |PASS0 |
| Original page AST |PASS0, every metric object unchanged |
| Actual immutable55a Make ratchet |PASS0, findings[] |
| Protected tracked inputs / author artifacts |3550paths /47entries, zero mismatches |

Coverage:522/643statement81.18%,427/645branch66.20%,148/194function76.28%,
484/595line81.34%;121missing statements/218arms/46functions/111lines.
Empty-selection private batch guard remains honestly uncovered: disabled
public control is not altered to fabricate access. No runtime refactor allowed.

## Preserved failures and publication

Private closure parser mistakenly treated raw_decode end index as text;
Coordinator allocated only parsing of the existing native output with the
decoded object. Another audit compared different git-status display formats;
both incidents retained. No native gate or input/spec oracle modified or rerun.
Ordinary reviewer report save failed Errno30 read-only sandbox. Final report
was frozen privately, then Coordinator published it byte-exact after release.

| Publication | Author/reviewer commit | Integration commit |
| --- | --- | --- |
| Original spec and CHAR |bb01abcfc84954fe6e0773eaa2186412400afb66 |b4ade2e63ec65e001e047035cdb18f6ff3310560 |
| Independent final review |559f186663f15f261e9ccd0ca8f1afb17bc4c646 |e9da9e854c6392fc449176dbe0e665853ced201f |

After EACH integration actual Make ratchet against immutable55a PASS0.
Native logs/exit files: `/tmp/gaia-r18-author-integration-ratchet-20261010.*`
and `/tmp/gaia-r18-review-integration-ratchet-20261010.*`.

## Frozen inputs and evidence

Spec63e29633a3733258395e8760739240b1e5c0ca3ce1fa40cf4b7e79a81359273b;
CHAR8415c5244e0147ec58ea24763c67f977177d9b0d9043f5ba458c0d838ba39b54;
review0589e0bdaa436e2ad2029dc9a577d2af3ff91a7e98e8efe110aeaf50bc26d903.
Independent evidence `/tmp/gaia-r18-independent-original-replay-20261010/`;
FINAL_FREEZE.json SHA38972d9d598ca9e27273b8c92813d9c4f57ac7a7850c33872048b8045705569a.

Root runtime diff from218 is empty. Principal390cognitive/342cyclomatic/2109LOC
unchanged; global prior certified1672files20316callables1926errors2740warnings
4666findings remains attributed, not a fresh whole-repository scan. Baseline,
thresholds/exclusions untouched. Classification **NO_CHANGE — ORIGINAL_CHARACTERIZED**.

## Closure limits

Disk externally recovered to12GB; no Coordinator deletion. Dedicated
platform-docs Graphify PASS0, chunk1/1done, no semantic failure;654nodes884edges
105communities,11757input2628output tokens, estimated$0.0089. Patch target
applied first; graphs ignored and not committed. Native evidence:
`/tmp/gaia-r18-graphify-platform-docs-20261010.log` and matching `.exit`.
Closure postcommit gate runs after this documentation publication; native
evidence is reserved at `/tmp/gaia-r18-closure-postcommit-ratchet-20261010.log`
and matching `.exit`, not inferred from earlier passing snapshots.
No runtime structure change, frontend code
graph refresh/build/E2E/full final suites are not claimed in this test-only
checkpoint. Global campaign ACTIVE/INCOMPLETE. Next runtime requires full-file
100% and equivalence; R19 correction and R16 ambiguity require their decisions.
