# R16 matcher: immutable source provenance

## Ownership and result

Author `/root/r16_matcher_author`, worktree
`GAIA-campaign-20261010-r16-matcher`, branch
`fix/complexity-r16-matcher-provenance`, unchanged HEAD
`54705ef8123b7992f4c7e1ff028cadb7718c3294`. Authoritative merge-base and baseline
retrieval commit: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Allocation precedes activation in the Coordinator's
`MULTI_AGENT_OWNERSHIP_R16_MATCHER_2026-10-10.md`.

Tooling-only implementation and characterization, awaiting independent review.
No application source, existing test, configuration, baseline, or retained R16
artifact changed; no commit, candidate application, or R16 runtime certification.
This is added matching functionality, not a complexity reduction.

## Matching contract

The previous matcher remains the first resolver, including exact keys,
fingerprint reservations, duplicate metric multisets, wholly-added handling,
renames/moves/splits, and positional fallback. Its ambiguity can be resolved
only by fresh source proof; otherwise the original finding and exit2 remain.

The proof reads immutable Git bytes using `git --no-replace-objects show` from
**baseline.source_commit**, which is
`11ed944a46ebdeb32ad50c14e7fca90b2c55f1fd` for the retained baseline. This differs
from the authoritative55a baseline retrieval commit. Both entire per-path
callable multisets must match fresh scans of their source snapshots: name,
kind, spans, fingerprints, and all five primary metrics. This verified the
R16 baseline records against11ed944;55a was not silently substituted.

Git generates a fresh zero-context snapshot diff with external diff/textconv
disabled, deterministic Myers algorithm, and indent heuristic disabled.
The parser verifies hunk bounds, unchanged gaps/tail, and exact removed/added
payload against both complete snapshots. Only unchanged lines map.
Both callable boundaries must map to one baseline span; single-line spans
are refused. Each boundary must also have an unchanged, globally unique line
within eight exterior lines, connected to it by an uninterrupted mapping.
This is a conservative refusal window, not positional padding or a distance
tie-breaker. Multiple owners/consumers, reserved fingerprints, and owners
already claimed through another existing resolver route are rejected.

A single comparison caches one fully bound source snapshot/mapping per path,
including refusal. It never rereads anchor context for another ambiguous
callable. The cache is local to that comparison; a new comparison revalidates
the source. A local provenance-owner ledger additionally prevents reuse of a
baseline identity through two proof attempts. No global cache was added.

The optional keyword-only `source_paths` comparison argument supplies exact
source bytes for private exterior projections. It supplies neither identities
nor line mappings and does not apply source to the checkout. Stale/forged
records, malformed commits, missing/invalid sources, scanner/Git failures,
ambiguous mappings, and malformed diffs fail closed. No public CLI flag or
baseline schema/configuration change was added.

## Characterization and gates

New hermetic tests first established original0, shifted ambiguity2, and a
below-threshold cognitive regression1 with the unchanged engine. The first
postpatch old expectation failed because the newly proven owner passed;
Coordinator authorized keeping the characterization as resolver behavior and
missing-provenance exit2 while asserting the new bound-source behavior.
The original failure output remains in the session history.

Final new tests include real Python/JS snapshots, native CLI0/1/2, truthful
exterior bytes, stale/forged records, malformed commits/Python, unavailable Git,
Git replacement refs, reordered unanchored callbacks, actual duplicate exact
fingerprint claims, duplicate owners/consumers, reserved siblings, single-line
refusal, edited boundaries/anchors, and malformed diff payloads. Existing
matching/rename/move/multiset/wholly-added contracts remain unchanged.

| Gate | Final result |
| --- | --- |
| Full `tests/code_quality` with real subprocess Coverage patch |215PASS, exit0|
| Full runtime statements |844/844,100%, zero excluded statements|
| Full runtime branches |332/332,100%, zero missing/partial branches|
| `make complexity-ratchet BASE_REF=55a…` |PASS0, findings[]|
| `make style-ratchet BASE_REF=55a…`, installed interpreter |PASS0|
| New test Ruff format check; touched-file Ruff check |PASS0|
| Python syntax; `git diff --check` |PASS0|

Coverage uses a private temporary config with `branch=True`,
`source=tools/code_quality`, `patch=subprocess`, and `parallel=True`; the report
selects the complete modified `complexity.py`. No repository coverage gate,
scope, threshold, exclusion, existing test, or baseline was weakened.
Two intermediate full-suite measurements192PASS/99.81% and208PASS/99.82%
failed the100% coverage requirement; their logs/JSON are retained separately.
Only genuine no-owner/one-line/cross-route cases completed the missing branch.
One private custody-script invocation failed with FileNotFoundError because
its retained-manifest path omitted `replay/`; the located existing path was
corrected only in the new private script, with the first failure preserved in
session output. No unexplained runtime/test failure was retried or absorbed.

Independent static review identified a further source-coherence concern in
the preliminary `bfec53…` draft: labels/comments can change without changing
any callable signature, and separate fallback snapshots could disagree.
The new real two-handler race test alternates source bytes with equal complete
callable signatures but changed anchor context. Reconstructing the exact
`bfec53…` draft in a private file reproduced its assertion failure, native
process1, at the same race contract. Final code reads once per path, accepts
the coherent first snapshot, and rejects the changed anchors in a subsequent
fresh comparison. A separate contract proves both cached refusal and duplicate
provenance-owner rejection. Earlier213PASS/829+326 coverage belongs to the
pre-race draft and is retained, not certified as the final source.

## Retained-input projection

Fresh private replay reads the full retained20316-callable/1672-file original
and20317-callable candidate reports, immutable55a baseline, and original or
faithful Git added-line metadata. Full fresh per-path source scans establish
the binding before any proof. The candidate source remains the frozen34af
artifact; current runtime remains original8111. These are projected comparator
outcomes, not candidate application or runtime-equivalence evidence.

| Comparison | Previous native exit | Final native subprocess exit |
| --- | ---: | ---: |
| Original, changed scope→55a |0|0|
| Candidate, original metadata→55a |2|0|
| Candidate, faithful metadata→55a |2|0|
| Candidate→local original baseline, non-authoritative |0|0|
| Negative original loadCredentials cognitive12→13 |1|1|

The final replay keeps the complete original/candidate context and authentic
added-line metadata; it supplies only the byte-source exterior adapter.
Frozen original replay scripts/results were never changed. Historical global
30 findings remain a distinct existing gate state; the authoritative changed
ratchet is not a claim to eliminate those findings or complete the campaign.

## Manual toolkit metrics

Tooling is outside the unchanged official application scope. Separate full
before/after AST measurements disclose all added proof complexity.

| Callable | Before cognitive/cyclomatic/LOC/params | After |
| --- | --- | --- |
| compare |85/41/85/4|85/41/92/5|
| source_callable_signature |new|0/1/5/1|
| unchanged_source_lines |new|13/9/24/3|
| valid_source_hunk |new|15/13/12/5|
| validated_source_mapping |new|14/9/28/5|
| source_anchor |new|15/9/13/5|
| unclaimed_source_owner |new|15/10/16/6|
| unique_mapped_callable |new|6/7/10/4|
| source_provenance_owner |new|21/14/31/6|
| source_snapshot_mapping |new|2/3/6/6|
| claim_provenance_owner |new|2/3/8/2|
| valid_provenance_source |new|4/5/3/2|
| resolve_source_ambiguity |new|3/3/9/5|

All prior callable metrics except compare LOC/params remain unchanged.
The existing compare LOC debt grows7 and its optional API adds one parameter;
these are explicitly disclosed, not hidden in the application-only ratchet.
All new helpers remain below callable error thresholds; warnings still appear.
Toolkit cognitive sum561→671 and cyclomatic sum424→510 reflect new proof
functionality. The prototype mega-helper was decomposed by real proof concerns;
no metric reduction or debt-removal classification is claimed.

## Custody and handoff

3569 protected tracked paths match Git index object bytes, zero drift.
All237 retained inputs match their frozen SHA256 manifest, zero drift.
Baseline SHA256 remains
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.

Frozen final runtime SHA256:
`871ebffc4742c7bdf0a8847dfac7d91132d862953179599c2ce27531f0b99f43`.
Frozen new test SHA256:
`d2752caceeec3f13d9ee03a69caaedaeea10139864ca7067d2fc9663042e9dd6`.

Private new evidence:
`~/.cache/gaia-campaign/20261010-r16-matcher/`: coverage config/full logs/JSON,
native replay command/results/exit/logs, complete manual metrics, custody,
style and actual55a Make ratchet logs. Installed interpreter is read-only:
`/home/cbo/CursorProjects/GAIA-campaign-20261008-integration/backend/.venv/bin/python`.
No supported Graphify module target includes `tools/code_quality`; no application
module changed. Coordinator owns the platform-doc graph update for its docs.
Author releases exclusive heavy after terminal custody/report; independent
adversarial review is required before any integration or publication decision.
