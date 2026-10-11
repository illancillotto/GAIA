# R36 — Presenze daily INAZ detail ownership provenance

## Decision

**ADMIT_HISTORICAL_TERMINAL.** Fresh registered-worktree census finds three
dirty copies of the owned page. One is the excluded R26 candidate, byte-exact
with its frozen STOP patch; two are retained R34 author/final snapshots,
byte-exact with the already accepted R34 source and committed diff. No observed
dirty live external owner conflicts with proposed NEW R36 ownership.

This decision resolves historical ownership only. It does not activate runtime
edits, accept a prospective design, certify equivalence/coverage, or authorize
copying the rejected R26 candidate. Coordinator alone admits ONE responsibility
after independent review and fresh original full-file100. Global campaign
remains ACTIVE / INCOMPLETE; Bonifica prerequisite decision remains separate.

## Ownership and authoritative snapshot

Only this NEW report and sibling private `provenance-evidence/` are writable.
No runtime/test/shared config/baseline or historical evidence edits; no heavy
gate, commit, merge, push, cleanup, prune or historical worktree restoration.

Registry read before preparation:
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R36_PRESENZE_DETAIL_2026-10-11.md`
from integration. Initial provenance owned working tree clean.

| Item | Observed value |
| --- | --- |
| Campaign/provenance HEAD | `c2ab91b0a885cec2fa8f9b421a90e46e58c6b51b` |
| Main/actual merge-base | `55a1b1d35911451e018b662c2acc450bf5994ea2` |
| Provenance branch | `review/complexity-r36-presenze-provenance` |
| Owned path | `frontend/src/app/presenze/giornaliere/page.tsx` |
| Integration/provenance/R36 author original SHA256 | `194686c9f2887ff8551289081e9c483023e0047692753a8f3b522429520a6111` |
| Main original SHA256 | `c1f27f1da0f708eec191b081a9b3d75dcad5ef3b0cec102ee8c81df7f4014f39` |
| Census timestamp UTC | `2026-10-11T15:42:08.169819+00:00` |
| Provenance tracked files | 3660 |

Main differs through committed campaign changes, not a dirty page on main.
Source history for every existing tree includes its last three owned-path
commits; integration history includes accepted R34 commit `0078b65c`.

## Complete registered-worktree census

`git worktree list --porcelain` captured **157 registered worktrees**:

- **142 present directories**, all captured for full short status, owned short
  status, HEAD, branch, actual main merge-base, owned last-three history and
  binary HEAD diff. All census command exit files are zero.
- **141 existing owned sources**, including three dirty frozen historical
  copies. The old `gaia-agent-operazioni` tree lacks this page.
- **15 missing registered directories**, retained as unavailable/prunable
  observations. No clean or terminal state asserted; no pruning/recreation.
- **138 present clean owned sources**; clean external branches are NOT assumed
  terminal or free of possible future edits. This is a local point-in-time audit,
  not inspection of all external processes or remote branches.

Complete records are private `census.json`, original `worktrees.porcelain` and
`census/NNN.*`; differing committed historical snapshots remain explicit.

## Dirty historical sources and owners

| Historical snapshot | HEAD | Source SHA256 | Current binary diff SHA256 | Disposition |
| --- | --- | --- | --- | --- |
| R26 author, `GAIA-campaign-20261009-r9-presenze-mutations` | `19197441f71e479d410edca5bc88c6fb9f26b091` | `3e68dbf4ffd19bcb1e971b3d3685cd948dee90b04fea86b55fd576a6a0685d9d` | `28a0b3b4aa785d0f8d70b73eaad87c23db94001e4ee763ed323a3ae9bcc8c7da` | HISTORICAL_STOPPED / NOT_ADMITTED |
| R34 SSD author-worktree | `3e4ad9f030370a2d21cd4c28a6f7cc569c287dde` | `194686c9f2887ff8551289081e9c483023e0047692753a8f3b522429520a6111` | `45e190739512b17199e3d521f8e4327a1a7952691069b51e9984c47c6a728cef` | HISTORICAL_TERMINAL / ACCEPTED_FROZEN |
| R34 SSD final-worktree | `3e4ad9f030370a2d21cd4c28a6f7cc569c287dde` | `194686c9f2887ff8551289081e9c483023e0047692753a8f3b522429520a6111` | `45e190739512b17199e3d521f8e4327a1a7952691069b51e9984c47c6a728cef` | HISTORICAL_TERMINAL / ACCEPTED_FROZEN |

Each row has targeted status ` M frontend/src/app/presenze/giornaliere/page.tsx`.
All three actual main merge-bases are55a. R34 paths are under
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r34-presenze-summary`.

### R26 source-bound rejection

Live candidate diff is exact historical `candidate-code-only.patch` in
`/home/cbo/.cache/gaia-campaign/20261011-r26-presenze-summary/`. Current STOP
receipt SHA256 remains
`56c17fa492a74e265bdad6b325f9a92e08d30111df17e2a002649378aa86e25c`.
It explicitly records source3e68, fileLOC growth2812→2813 and changed evaluation
ordering, no native candidate admission. Registry/handoff/integration report
retain the excluded candidate and no ongoing writable ownership.

No R26 managed thread ID is present in R34 provenance report/closure evidence.
Current collaboration and bounded managed-task census show no live R26 owner;
absence alone is NOT used as proof of terminal state. Explicit source-bound
STOP and historical ownership closure establish the stopped/frozen disposition.
R26 stays rejected; R36 may not reuse it.

### R34 accepted freezes and actual task-state distinction

Current author/final source bytes equal frozen `author-evidence/prospective-page.tsx`.
Both current binary diffs equal the immutable Git diff from3e4 to accepted0078
for the owned page; no changed historical byte or new uncommitted amendment.
Independent read-only rehash of original immutable manifests:

| Prior manifest | SHA256 | Members rehashed | Failures |
| --- | --- | ---: | ---: |
| Author `FREEZE_SHA256.txt` | `92215866ef7e2c561c5aa29553c144199250c59029a603adb37fb8ebdc642613` | 66 | 0 |
| Final `terminal-freeze/manifest.json` | `07bca251dc132db1c1edcfc52dd937fdcd9cb844e66c8e2e1994b683918078ed` | 75 | 0 |
| Root `terminal-freeze/manifest.json` | `9d009bde3730e28eb792347b737e6d955b3bbdc2402266e8a9db9dc6491fef19` | 96 | 0 |

Coordinator supplied the authoritative live collaboration listing: R34 author,
reviewer and final verifier all **completed**, accepted task names
`/root/r34_presenze_author` and `/root/r34_presenze_final_verifier`.
Provenance agent's narrower current tree snapshot no longer lists these R34
tasks; that absence is recorded, not substituted for the supplied actual status.
Private `task-status-observation.md` preserves this attribution. Frozen root
closure handoff and final `closure-receipt.json` additionally record terminal
tasks/token RELEASED and source194686c9. Retained dirty sources are accepted
historical snapshots, not active current ownership.

## Protected concurrent main and custody

Main full binary diff SHA256:
`9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`.
Main short-status SHA256:
`0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`.
Fresh final capture matches both original values. Main concurrent Presenze,
Ruolo and documentation work is not imported, reset, staged or modified.

Baseline SHA256 remains
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`,
exact immutable HEAD bytes. Provenance runtime/test/config diff is empty.
Original page194686c9 remains unchanged in provenance and R36 author during
admission. No all-main-untracked-content audit is claimed from Git status alone.

## Commands and private evidence

Read-only commands: native status/ref/merge-base/worktree/log/binary diff,
SHA256 and exact comparisons, actual collaboration/task snapshot, instruction/
closure reads and manifest rehashes. Capture and admission audits exit0.
Optional ad-hoc distribution print had a disclosed extra-parenthesis SyntaxError
before execution; no writes/native gate occurred. A distinct final custody
script supplies the optional counts and final custody, exit0. No successful
native test or diagnostic gate was repeated.

Evidence base:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r36-presenze-detail/provenance-evidence`.
Includes census, initial registry, own/main/integration observations, original
hashes, `admission-audit.json`, accepted R34 immutable diff,
`closure-custody.json`, attributed task-state receipt and diagnostic note.
Final report and evidence are frozen once for Coordinator review.

No coverage, application test, complexity report/ratchet/check, Graphify or
baseline command run or claimed PASS by this provenance agent.

## Handoff and remaining limits

Ownership provenance is admitted, not the candidate implementation. Coordinator
must approve a substantial coherent responsibility and fresh full-file coverage
before sole runtime owner activation. Metrics/equivalence/native final review
remain unproven R36 gates. New live external edit requires renewed assessment.
Historical30, R25 matcher, Bonifica prerequisite and global extreme-tail/full
suite certification remain separate open work; no campaign completion claim.
