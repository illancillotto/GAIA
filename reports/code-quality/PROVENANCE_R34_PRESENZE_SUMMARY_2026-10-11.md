# R34 — Presenze monthly summary ownership provenance

## Decision and scope

**ADMIT_HISTORICAL_TERMINAL.** The sole dirty owned runtime snapshot is the
explicitly stopped, frozen and excluded R26 candidate. Its current source and
binary diff exactly match the historical rejection records. There is no observed
dirty external owner conflict on `frontend/src/app/presenze/giornaliere/page.tsx`.

This decision authorizes only Coordinator consideration of NEW R34 ownership.
It does not revive R26, accept its design, certify R34 behavior or permit copying
its candidate. Tests, full-file coverage, metrics and ratchet remain separate
admission gates. Whole campaign remains ACTIVE / INCOMPLETE.

Only this NEW report and NEW private provenance evidence were written. No
runtime, old spec, baseline, threshold, configuration, historical evidence,
main checkout or historical worktree was modified. No commit, merge or push.

## Authoritative references and original bytes

| Item | Observed value |
| --- | --- |
| Main / operative merge-base | `55a1b1d35911451e018b662c2acc450bf5994ea2` |
| Campaign HEAD | `3e4ad9f030370a2d21cd4c28a6f7cc569c287dde` |
| Provenance branch | `review/complexity-r34-presenze-provenance` |
| Provenance HEAD / merge-base | `3e4ad9f030370a2d21cd4c28a6f7cc569c287dde` / `55a1b1d35911451e018b662c2acc450bf5994ea2` |
| Original integration / R34 author / provenance source SHA256 | `d362df3199fbf65dc4566b56d4029fe72135c910f3e39e691b3e3535516fa940` |
| Main source SHA256, clean owned path | `c1f27f1da0f708eec191b081a9b3d75dcad5ef3b0cec102ee8c81df7f4014f39` |
| Census completion timestamp | `2026-10-11T14:37:41Z` |

Main source differs from campaign source through already accepted campaign
commits, not an uncommitted edit on main. Campaign history ends with the accepted
page mutation/labelling/anomaly slices `c51b6038`, `ecdcc93c`, `bee3fd53`.
Both immutable HEAD and current original source hashes were captured.
Main contains unrelated concurrent tracked/untracked work, including backend
Presenze and Ruolo; that work is protected and is not imported into R34.

Registry was read before this activity:
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R34_PRESENZE_SUMMARY_2026-10-11.md`
in the integration checkout. Initial dedicated provenance tree was clean.

## Complete registered-worktree census

`git worktree list --porcelain` yielded **149 registered worktrees**:

- **134 existing directories**: complete short status, owned-path short status,
  HEAD, branch, actual main merge-base, current source SHA256, last three
  owned-path commits and `git diff --binary HEAD -- <owned-path>` captured.
- **133 existing owned sources**; the older `gaia-agent-operazioni` worktree
  lacks this page. The path-status warning is an absent historical source,
  not a failed test or omitted present worktree.
- **15 absent directories**, each registered as prunable by Git. Their source
  and working-tree state are UNAVAILABLE, not asserted clean or terminal.
  No prune, deletion, recovery or mutation was performed.
- Exactly **one present dirty owned page**, the historical R26 author below.
  All other present owned pages have clean targeted Git status.

Complete per-tree observations are in private `census.tsv` and `census/NNN.*`.
Absence and committed differences were kept explicit rather than silently
equated to clean current source. Existing clean external branches are NOT
claimed terminal: a clean path proves only no observed local edit at census.
New external messages/edits would require Coordinator reassessment.

## Historical dirty source and frozen owner

| Item | Bound observation |
| --- | --- |
| Worktree | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r9-presenze-mutations` |
| Branch | `refactor/complexity-r26-presenze-summary` |
| HEAD | `19197441f71e479d410edca5bc88c6fb9f26b091` |
| Owned status | ` M frontend/src/app/presenze/giornaliere/page.tsx` |
| Candidate source SHA256 | `3e68dbf4ffd19bcb1e971b3d3685cd948dee90b04fea86b55fd576a6a0685d9d` |
| Current binary diff SHA256 | `28a0b3b4aa785d0f8d70b73eaad87c23db94001e4ee763ed323a3ae9bcc8c7da` |
| Historical candidate patch SHA256 | `28a0b3b4aa785d0f8d70b73eaad87c23db94001e4ee763ed323a3ae9bcc8c7da` |
| Historical STOP receipt SHA256 | `56c17fa492a74e265bdad6b325f9a92e08d30111df17e2a002649378aa86e25c` |
| Classification | HISTORICAL_TERMINAL; R26 NO_SAFE_CHANGE / NOT_ADMITTED retained |

Source-bound proof, independently inspected read-only:

1. Historical `CODE_ONLY_STOP.md` in
   `/home/cbo/.cache/gaia-campaign/20261011-r26-presenze-summary/` explicitly
   identifies source3e68, stopped fileLOC2812→2813 and changed tone/formatter
   evaluation order; no native candidate gates or equivalence claim.
2. `cmp` confirms historical `candidate-code-only.patch` is byte-exact with the
   newly captured current binary diff. This is stronger than relying on a
   branch name or old timestamp.
3. The original campaign registry, R26 rows, explicitly records FROZEN /
   NOT_ADMITTED for the runtime candidate, original test-only publication
   MERGED and **no ongoing writable ownership**. Its reviewer row records
   original-only acceptance; candidate append was never activated.
4. `INTEGRATION_R26_CHARACTERIZATION_2026-10-11.md`, the author slice report,
   `PROGRESS.md` R26 closure and private `R26_HANDOFF_2026-10-11.md` independently
   preserve the same rejection/source/HEAD and excluded runtime disposition.
5. Current managed-agent census contains no live R26 author/reviewer. This
   corroborates the explicit closure records; it is not claimed to discover
   every external process or unseen remote branch.

The historical R26 reviewer tree at `388b052b` has a CLEAN owned page and an
untracked original characterization spec. That spec hashes
`ea775e5ca3a1356a3b59be9a70ca3daf13abb9b4b886e46128bd9746f95c666e`,
exactly the integrated original spec; it is the preserved read-only review
input, not active new runtime ownership. It was not staged or deleted.

## Commands, evidence and custody

No heavy gate was run. Read-only commands were `git status --short`, owned
status/diff/log, `git rev-parse`, `git merge-base HEAD main`, registered-worktree
list, SHA256, exact historical-patch comparison and targeted instruction/
closure reads. Checkpoint skill and applicable project/complexity rules read;
large PROGRESS chronology was consulted through bounded relevant sections.

New private directory:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r34-presenze-summary/provenance-evidence`.
It contains complete census TSV, original Git registry, per-tree status/log/
binary diff, immutable source hashes, critical-source hashes, provenance
reference hashes and closure checks. Historical directories/evidence remain
untouched. No test, coverage, Graphify, complexity report/check/ratchet or
baseline command was executed or claimed PASS by this provenance agent.

## Remaining limits and handoff

This admission resolves historical dirty-owner provenance only. The global
historical30 findings are separate and unresolved. Original full100 must be
proved afresh before R34 mutation; candidate equivalence and actual reduction
are unproven. New R34 design may not absorb rejected R26 code or its metric
forecast. Coordinator alone activates runtime ownership and serial native
token; all historical snapshots remain frozen.
