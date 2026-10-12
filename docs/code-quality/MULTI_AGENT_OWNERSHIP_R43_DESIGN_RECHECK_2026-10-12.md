# R43 — Presenze design recheck

User selected a new Presenze design after the rejected R42 consolidation.
R43 already implements that design externally; it is not admitted. This
follow-up must not silently restart R42, create an overlapping candidate or
modify frozen R43 inputs. The separate test-fixture decision remains pending.

Snapshot: integration HEAD `114fbf7196382c6446a7963c34bd89e4c9795ef5`,
main/merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Concurrent work in main remains untouched.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
|---|---|---|---|---|---|---|
| Coordinator | Presenze planning | This registry; new recheck evidence only | Revalidate custody and pending decision | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | ACTIVE |
| Design reviewer | Presenze UI | Existing R43 source/spec/evidence read-only; new `reports/code-quality/RECHECK_R43_PRESENZE_DESIGN_2026-10-12.md` only writable | TERMINAL static recheck; no new runtime defect, source grant still pending | Existing R43 review-worktree | review/complexity-r43-presenze-profile-policy | READY_FOR_REVIEW |
| R43 runtime owner | Presenze UI | Frozen author page and test | No edits or retries until separate fixture decision | Existing R43 author-worktree | refactor/complexity-r43-presenze-profile-policy | BLOCKED |

Existing R43 base:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r43-presenze-profile-policy`.

Review assignment: read the project instructions and checkpoint skill, the
R43 integration/final reports, original page in integration and candidate page
in author-worktree. Review only the contract-profile policy and its effect.
Validate captured-kind versus latest-editor behavior, nullable state, OR
defaults, clone/no-op identity, property and setter ordering and dependencies.
Distinguish prospective metrics from accepted improvement. Confirm the exact
two fixture diagnostics and immutable failure lineage. Report whether there
is a new design issue requiring a runtime change. Do not modify runtime,
fixtures, frozen reports, baseline, matcher, thresholds or configuration; do
not execute native tests/scanners/builds or create commits. Write only the new
recheck report under the existing dedicated reviewer worktree and stop.

Graphify orientation: the backend Presenze query exits 2 because that corpus
has no graph in integration; its log is retained. The separate frontend
query succeeds and is the appropriate UI corpus. Neither result is a
complexity or runtime certification.

Independent recheck completed, report SHA256
`0679f5981ff86d284ef11116da8b61626897a84ee2d7a5d5ff0fcd5998c95758`.
Imported byte-exact through apply_patch; no Git merge or runtime admission.
Custody revalidation: STOP47, HOLD14, R58 completion161, zero drift.
Prospective cognitive360→347 remains uncredited; strict fixture correction
decision is still pending, so native gates and runtime changes are not started.
