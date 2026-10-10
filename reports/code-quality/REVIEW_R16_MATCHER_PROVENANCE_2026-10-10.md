# R16 matcher provenance — independent review

## Scope and custody

Reviewer `/root/r16_matcher_review`, worktree
`/home/cbo/CursorProjects/GAIA-campaign-20261010-r16-matcher-review`, branch
`review/complexity-r16-matcher-provenance`, HEAD
`54705ef8123b7992f4c7e1ff028cadb7718c3294`.
Allocation precedes activation in the Coordinator's
`MULTI_AGENT_OWNERSHIP_R16_MATCHER_2026-10-10.md` registry.
This NEW report is the only writable repository path. Author runtime/tests,
application runtime, baselines, configuration and retained evidence remain
read-only. No commit, source import, candidate application or baseline update.

Checkpoint, project complexity skill and applicable rules loaded. Exploration
uses bounded source/diff reads and source hashes. No Graphify corpus supports
this tooling slice; no graph extraction or root analysis is performed during
the static allocation.

**Verdict: ACCEPT — frozen tooling-only source871ebffc/testd2752cac.**
The initial allocation was STATIC ONLY; historical observations below retain
that distinction. Coordinator subsequently imported exactly frozen
runtime871ebffc/testd2752cac/report30a16375 through `apply_patch` and explicitly
transferred exclusive heavy. Independent executed evidence appears at the end
of this report. All identified blockers are closed. The extra byte-regression
probe's first explained metadata-harness failure is preserved separately from
the corrected full-metadata comparison. No frontend candidate acceptance.

## Design observations

The fallback is invoked only after the existing resolver returns ambiguity.
Failure to establish proof preserves the original ambiguity. It rescans
immutable-base and current private byte snapshots, comparing the complete
per-path callable multiset including name, kind, span, fingerprint and primary
metrics. This is stronger than accepting caller-supplied hashes or spans.

Text mapping is derived internally from Git zero-context diff and validated
against complete snapshot gaps and hunk contents. The revised design requires
unique unchanged context before and after a callable, with uninterrupted
mapping from each context line to its respective boundary. Owners must have
the exact mapped baseline span; source-mapped consumers must be unique.
An additional guard checks whether existing resolver routes or equivalent
groups already claim the proposed owner. Existing metric comparisons remain
in the common comparator flow after provenance selection.

The initial before-only context design was insufficient for repeated closing
boundaries. Author revisions now require both contexts. This observation is
closed at design level, subject to frozen-source adversarial validation.

## Initial blocking findings communicated to author

1. **Replacement refs break immutable-source custody.** `git show SHA:path`
   honors Git replacement refs. A full forty-character source commit does not
   by itself guarantee bytes from that immutable object. Replacement content
   can preserve callable records while changing surrounding context, which
   supplies the fallback's identity evidence. Immutable lookup must disable
   replacements and have a real replacement-ref contract test.
2. **Malformed commit metadata escapes fail-closed handling.** `re.fullmatch`
   is executed before the exception boundary and assumes a string. A baseline
   with `source_commit: null` or a numeric value passes the existing baseline
   key/count integrity checks, then raises `TypeError` on an ambiguous record.
   The fallback must reject malformed provenance and preserve the original
   ambiguity instead of propagating a Python exception.
3. **Malformed current Python source escapes fail-closed handling.** A valid
   scanned report can become stale before fallback reads its source. A fresh
   snapshot containing `def broken(` raises `SyntaxError` in `scan_python`.
   The present exception set does not include `SyntaxError`; invalid source
   must leave ambiguity unresolved, with a genuine source-byte negative test.

These are static findings; no executable reproduction is claimed by reviewer.
Author owns any corrective changes and tests.

### Frozen revision bfec53 — initial findings addressed

Exact observed runtime SHA-256
`bfec53fdb99b4f7689e6779530042bbca247750e97094e7032962c4ccf49bf44`
and new test SHA-256
`82908420c4e2e4503aeb27655724aedb7471cce9153c5085d8548e8b5a864337`
match Coordinator's frozen allocation.

Static review confirms immutable lookup now uses `--no-replace-objects`,
malformed commit metadata is checked with `isinstance(commit, str)`, and fresh
invalid Python snapshots are caught as `SyntaxError`. Genuine replacement-ref,
malformed-commit, invalid-source and actual two-copy ownership contender tests
are present. The initial three blockers and the single-sibling coverage gap
are addressed at source/design level, pending independent execution.

### Preliminary blocker: one byte snapshot per comparison

Each ambiguous record independently calls `validated_source_mapping`, which
rereads the same source path. No per-comparison path snapshot/cache or consumed
provenance-owner ledger exists. The full callable signature multiset binds
callable records, but does not bind context bytes across these independent
reads: Python module-level label assignments/comments can change without any
callable signature change; the JS fingerprint also omits literal values.

The refusal/identity proof therefore may derive from different byte versions
for different records in one comparison. `unique_mapped_callable` checks
consumers against one mapping only, and `unclaimed_source_owner` checks only
the preexisting resolver, not owners claimed by an earlier provenance fallback.
The code lacks a safeguard against snapshot A proving current C1 -> baseline B
and snapshot B proving current C2 -> the same B with both signature multisets
unchanged. This is a static safety mechanism finding; no executed counterexample
is claimed. Coordinator holds publication for byte coherence.

Requested correction: cache the immutable validated mapping and both source
line snapshots per path for the lifetime of one `compare` call, including
refusals. A fresh comparison must create fresh local state. All ambiguous
records for a path then derive proof from the same source read; absent proof
cannot silently be retried against different bytes midway through a comparison.
An author-owned contract should alternate source bytes containing changed
non-callable context while preserving callable signatures and verify exactly
one current source read per path, then fresh reads for the next comparison.
No reviewer scanner/comparator/gate was executed to investigate this issue.

## Required adversarial evidence before acceptance

- Genuine source ownership contention: append TWO copies of the baseline
  fixture's final handler after `NEXT_LABEL`. Current fingerprint multiplicity
  becomes two, bypassing the earlier unique-fingerprint reservation, while
  the ordinary resolver maps each copy to the sole baseline fingerprint owner.
  The ambiguous changed original must not inherit that already claimed owner.
  The revised cross-route guard appears to reject this, but the earlier
  monkeypatched single-sibling test exercises only the reservation shortcut.
- Reordered anonymous handlers and repeated boundaries must not be assigned
  by whichever textual alignment Git happens to choose. Modified or absent
  unique context/boundaries must preserve ambiguity.
- Missing/stale/forged current or baseline callable records, partial per-path
  scans, duplicate owners/consumers and incompatible snapshots must fail closed.
- Immutable 55a baseline custody and negative cognitive 12→13 regression remain
  mandatory. R16 candidate acceptance cannot follow from tooling acceptance.
- Full tooling suite plus real subprocess full-file 100% statement/branch
  coverage, immutable-base ratchet and style checks require independent runs
  after freeze. The global historical thirty findings remain visible.

## Reviewed evolving source checkpoints

Author files are evolving and these are observation hashes, not release hashes.

| File | Observed SHA-256 |
| --- | --- |
| `tools/code_quality/complexity.py`, helper extraction revision | `5227d4e2eba9cf329d89ec8649cbfafed6dc1069f25e1920bac70a22f16df876` |
| NEW `tests/code_quality/test_complexity_r16_provenance.py` | `6356cf7cd86331d6852f447f90f08354109687d627fb73efaa198a27d489345a` |

Static reads confirm no baseline, thresholds, exclusions, existing tests or
application runtime appear in the author's working diff. Read-only
`git diff --check` emitted no errors at observation time. This report creates
no metric reduction claim. Campaign remains ACTIVE/INCOMPLETE; V1 rejected;
R16 candidate remains excluded; R19 closure is preserved.

Reviewer custody checkpoint: HEAD unchanged, `git status --short` contains
only this NEW report, and reviewer `git diff --check` passes. Immutable reviewer
baseline SHA-256 remains
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`;
original matcher remains
`315bc71fb48521f0049c968c8c4f262bdbb7077ad091c8f5f991b8088dc065af`;
JS AST scanner remains
`faf340a36a2a3730d313be34b17a89e1c96c6310084d3b63739e0a3fbf446b8d`.

## Fresh independent gates — final coherent freeze

Final imported runtime SHA-256
`871ebffc4742c7bdf0a8847dfac7d91132d862953179599c2ce27531f0b99f43`;
new test
`d2752caceeec3f13d9ee03a69caaedaeea10139864ca7067d2fc9663042e9dd6`;
author slice report
`30a16375d8b23bbabccc7f1f28a57dd56d068bac291a09f7387597ea254c9170`.
The unsuccessful Coordinator import attempt changed no inputs; the corrected
sanctioned import matches all three hashes exactly.

The new per-comparison context caches the full source mapping and both byte
line snapshots by path, including refusal when snapshot construction raises.
It resets on the next comparison. The owner ledger rejects an already claimed
baseline callable key. Source inspection and the genuine two-handler alternate
context test confirm the race blocker is closed. The independently executed
contracts also cover replacement refs, real two-copy reserved ownership,
malformed/absent/stale sources, duplicate consumers/owners, edited boundary
context, real JS snapshots and native CLI 0/1/2. The original resolver remains
the first route and absent source proof preserves its ambiguity.

| Independent gate | Native outcome |
| --- | --- |
| Complete `tests/code_quality`, Coverage subprocess patch | 215 PASS, exit0, 69.58s |
| Entire modified `complexity.py`, statements | 844/844, 100%, zero excluded/missing |
| Entire modified `complexity.py`, branches | 332/332, 100%, zero missing/partial |
| Actual `make complexity-ratchet BASE_REF=55a…` | exit0, findings[] |
| Actual `make style-ratchet BASE_REF=55a…` | exit0 |
| Installed Ruff touched-file check and new test format-check | exit0 / exit0 |
| `git diff --check` | exit0 |

The coverage config is private: `branch=True`, `source=tools/code_quality`,
`patch=subprocess`, `parallel=True`, report include selects the complete
modified runtime file. No repository policy/config/gate/threshold/exclusion is
modified. The full log contains no no-data/module-not-imported warning.

Fresh replay subprocesses use reviewer runtime, full retained reports,
immutable55a baseline and unchanged retained metadata; candidate bytes are
provided only through `source_paths`. No frozen script/result is executed in
write mode or altered, no frontend candidate is applied.

| Full-context replay | Native exit | Files / callables |
| --- | ---: | --- |
| Original changed scope -> immutable55a | 0 | 1672 / 20316 |
| Candidate with original metadata -> immutable55a | 0 | 1672 / 20317 |
| Candidate with faithful metadata -> immutable55a | 0 | 1672 / 20317 |
| Candidate -> local original, non-authoritative | 0 | 1672 / 20317 |
| Original negative `loadCredentials`, cognitive12 -> 13 | 1 | 1672 / 20316 |

The negative has exactly `legacy_metric_regression`, cognitive baseline12,
value13, delta1. Immutable source bytes are fetched from baseline source
`11ed944a46ebdeb32ad50c14e7fca90b2c55f1fd`, distinct from55a baseline retrieval.
Projected candidate exit0 demonstrates repaired identity resolution, not UI
equivalence, runtime approval or complexity reduction.

## Extra independent byte-regression probe — first failure retained

The reviewer created a private exterior candidate variant adding logical
conditions to the Sincronizza handler, freshly scanned its entire path and
replaced only those path records in the complete candidate report. Its first
wrapper expected comparator1 but received comparator2 for an unrelated
Presenze `CallExpression.map[0]<callback>`, candidates2; wrapper native1 came
from the failed assertion, not a metric regression.

Diagnosis: this private wrapper supplied authentic added lines ONLY for the
negative Capacitas source, accidentally discarding faithful added-line metadata
for other changed paths. That omission prevents an unrelated duplicate group's
wholly-added proof. This is a private test-harness error, not an unexplained
runtime failure or evidence of successful regression enforcement. Source,
first log/result and native exit are preserved under private evidence.
Coordinator was notified. The fully diagnosed correction is confined to a
separate private wrapper inside the allocated evidence/replay scope: retain
all236 faithful metadata paths and replace only Capacitas added lines. No
runtime/test/baseline repair or unexplained-failure retry. The original failing
wrapper/log/result remain unchanged. This first failure is not counted as a
passing gate.

The corrected independent variant uses fresh250-callable full-path source
records in the entire1672-file/20317-callable candidate report. Actual Git
added-line metadata yields392 added lines for Capacitas. Native comparator and
process both exit1, with four genuine legacy regressions: Sincronizza outer
`Program<anonymous>` and inner async callback each cyclomatic10 -> 26 and
cognitive14 -> 47. The actual variant changes only a private exterior source;
its unchanged unique boundary context still proves the baseline owner and the
common metric comparison rejects the increase. This verifies that resolved
ambiguity cannot hide a real source-byte regression. No frontend source was
applied or candidate runtime certified.

## Independent custody and evidence

Before/after all allocated gates: reviewer HEAD54705ef8 unchanged;
3570 tracked paths measured, only imported owned `complexity.py` differs from
index, all3569 protected tracked paths exact. Main HEAD55a and all3341 tracked
byte hashes/status are identical before/after, including its nine preexisting
modified paths. All237 retained inputs exist and match frozen manifests.
Imported frozen hashes and baseline38e6 remain exact. No commit or baseline
regeneration. Runtime/source/test/imported report are read-only after import.

Private evidence directory:
`/home/cbo/.cache/gaia-campaign/20261010-r16-matcher-review/`.
`independent_review.py`, `coverage.ini`, command/exit/log files, full coverage
JSON, five replay result JSONs and `custody-{before,after}.json` are independent
reviewer artifacts. The orchestrator terminates native0 only after checking
all real subprocess outcomes and exact custody equality.

The added tooling functionality has disclosed cost: existing compare
cognitive85/cyclomatic41 unchanged, LOC85 -> 92 and params4 -> 5; new proof
helpers add aggregate complexity. The official application ratchet scope
remains unchanged; this work is not `IMPROVED`. No supported Graphify module
target includes tooling; Coordinator owns platform-doc graph maintenance.
Historical global30 findings, V1 rejection and global campaign
ACTIVE/INCOMPLETE remain visible. No candidate frontend acceptance follows.

## Final verdict and release

**ACCEPT** the exact frozen tooling implementation and new tests: fail-closed
ambiguity is retained without trusted complete source proof; verified source
identity does not exempt metric comparisons. All three initial provenance
blockers and the per-comparison byte-coherence blocker are closed by inspected
code and fresh independent executable contracts. No unresolved source finding.

Final custody after the extra probe repeats every before manifest exactly:
3569 protected reviewer tracked paths, all3341 main tracked bytes/status and
all237 retained inputs unchanged; all three imported hashes exact;
baseline38e6 unchanged. Final custody script native0. No running reviewer
scanner/test/replay/gate subprocess remains. Exclusive heavy **RELEASED** to
Coordinator. No commit, publication/import into integration, baseline update,
frontend acceptance, `IMPROVED` classification or global completion claim.

Reproduction uses read-only installed interpreter
`/home/cbo/CursorProjects/GAIA-campaign-20261008-integration/backend/.venv/bin/python`:

- `independent_review.py`: full215 suite/real subprocess full-file100%, five
  distinct native replay cases, actual55a Make ratchet/style, Ruff and custody.
- `exterior_regression_corrected.py`: native1 is the asserted regression result,
  not wrapper success; result JSON contains the four expected metric findings.
- `final_custody.py`: native0, exact final before/terminal manifest equality.

All scripts and per-case command/exit/log/result/coverage/custody evidence live
in the independent private directory stated above. First failed extra wrapper
and its outputs are retained and explicitly excluded from passing evidence.
