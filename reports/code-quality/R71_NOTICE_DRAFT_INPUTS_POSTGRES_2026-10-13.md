# R71 — original draft input provenance tests on private PostgreSQL

## Scope, ownership and snapshot

Verification only, no runtime refactor. Full original
`backend/tests/ruolo/test_notice_draft_inputs.py`: **58 identities**, comprising
37 PostgreSQL skips and 21 PASS in the immutable R62 backend certificate.
No source, assertion, fixture, migration, timeout, auth/quota or policy change.

Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`, starting HEAD
`0cb2463ae2b3b39fcbbdc8f4056773c2e46672e8`. Actual main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`; original `55a1b1d35911451e018b662c2acc450bf5994ea2`
remains historical. Main and concurrent untracked Bonifica source untouched.

Ownership registry predates reviewer assignment. Existing original swarm
reviewer `/root/r64_baseline` owns external `review/` only, accepts preparation
before native launch and independently accepts terminal results afterward.
No model/config override, CLI retry or native job by reviewer. Coordinator owns
new docs/evidence and PROGRESS after freezing prior mutable documents.

## Native result and characterization

**58 PASS, 0 skip/fail/error, 0 NOT_RUN**, JUnit 40.735 seconds; one full-file
invocation, retries zero. Complete original identities independently matched
against historical XML and raw new XML. No easier filtered subset.

| Behavior | Original assertions and execution | Result |
| --- | --- | --- |
| Scoped capture/cache/copied basis/pending ORM/nested exceptions/day | Original SQLite unit fixture and deliberate token/date patches | PASS; unit scope only |
| Real pre-read revision/epoch/basis and deterministic digest | Actual migrated PG generation and integrity review | PASS |
| Changes while rendering/before final commit | Separate committed PG writer cannot mint fresh token | PASS |
| Mixed lot after payment/notification/STEP writer | Whole review rejected, drafts remain private | PASS |
| Stale ORM/policy cache | Refreshed before generation reads | PASS |
| Legacy/tampered basis/artifacts/manifest | Review refused | PASS |
| Inconsistent batch/origin/state/public path/count/budget | Review refused; original budget patches disclosed | PASS |
| Render failure/untracked generation | Rollback/capture cleanup, no retroactive basis | PASS |
| Input-basis downgrade/upgrade | Actual private migration preserves artifact bytes, assigns no revision | PASS |

37 previously skipped PG identities are freshly verified; 21 prior unit PASS
are reconfirmed, not counted as newly resolved skips. Original synthetic renderer
patches remain. Storage helper genuinely executes under the runner's private
TMPDIR. Mixed 2024 items inherit whole-batch quarantine when a protected year
is present; no NAS/provider dispatch path required. Original SQLite read_revision,
date and budget patches are not mislabeled as live PostgreSQL proof.
Review explicitly does not authorize dispatch or enable confirmation. No real
PDF/DOCX, GIS, external provider, E2E confirmation or simultaneous-thread claim.

## Private environment and custody

Reviewed R70 isolation/capacity reused with only new identity/socket/test target:
local pinned PostgreSQL 16.15 image
`sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea`,
1 GiB PGDATA tmpfs / 2 GiB memory, one CPU, network none, read-only root,
no ports/named volumes/application mounts or image pull. New owned short
Unixsocket under 0700 parent, UUID schemas and synthetic data only.
Replacement environment alone does not exclude all repository .env influence;
call-path review is bounded, not a universal provider-absence certificate.

Private DB identity/schemas/user relations/routines and zero advisory locks
exact before/after. Owned container positively identified, stopped/removed,
absence confirmed; tmpfs data destroyed. Empty owned socket root retained.
43 existing containers / 67 volumes exact sets; 2852 integration / 2851 main
protected input hashes exact. Original source bytes match HEAD/main. Prior
failures, main concurrent source, excluded R43/R51/R63 and freezes preserved.

## Quality gates, metrics and admission

Actual-main ratchet, final diff-check and Graphify publication results are bound
in the companion JSON and durable handoff receipts. No baseline update,
threshold/exclusion/ignore or coverage policy change; global matcher/baseline
ambiguity remains separate from the change gate. Full certified suites and
complexity report not repeated for unchanged protected inputs.

Coverage **NOT_MEASURED_UNCHANGED_RUNTIME**; worker full-file 100% remains FAIL.
Last full metrics unchanged: 1681 files / 20360 callables / 1920 errors /
2736 warnings / 4656 overlapping findings. No complexity reduction credit.
Classification **VERIFIED_EXISTING_TEST_VARIANTS_NO_CHANGE_RUNTIME**.
Only this report, companion JSON, ownership registry and PROGRESS admitted
to the local docs checkpoint; no caches/DB/dependencies/build/generated graph.

R68 + R69 + R70 + R71 verify **199 of 449** historical backend skip identities;
**250 remain unverified by these follow-ups**. Historical R62 7142 PASS / 449 SKIP
unchanged, not a rewritten complete-suite certificate. 7 E2E skips, worker
coverage FAIL, matcher ambiguity, excluded partials and extreme tail remain.
Goal **ACTIVE / INCOMPLETE**, no new runtime refactor, push or main merge.

## Durable handoff and next decision

Evidence root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r71-notice-draft-inputs-pg`.
Native manifest 88 records, SHA
`871819dd6d6ae4234d28bac00f5ed2297085948da2e9a70d597f468fc57401cd`.
Terminal review SHA
`9c72303df5e0c19d934d4235c000d1c23595df6091d10e7574a3145145926aad`;
final review manifest SHA
`b886cb576d70189fce85f8c55c939129068cc458a5d23501d1eed32e31ca1a9d`.
`FINAL_HANDOFF_MANIFEST.json` binds stable evidence and publication snapshots;
`publication/POST_COMMIT.json` and `publication/HANDOFF_CHAIN.json` bind the
later commit without checksum cycles. Parent: R70 publication handoff chain.
Next decision is a separate coherent unchanged-test prerequisite; do not infer
new runtime refactoring authorization or global completion from these results.
