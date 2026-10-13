# R70 — original notice generation interleaving tests on private PostgreSQL

## Scope and snapshot

Verification/test consolidation only; no new runtime refactor. Complete original
`backend/tests/ruolo/test_notice_generation_concurrency.py`, 36 identities skipped
in the immutable R62 backend certificate. Sources, assertions, fixtures,
configuration, migrations, timeout and policies remain unchanged.

Integration worktree `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`,
branch `refactor/complexity-campaign-20261008`, initial HEAD
`2c727b410e1a3b8d6bc43d752318452e2f656e3d`. Actual main and merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`; original `55a1b1d35911451e018b662c2acc450bf5994ea2`
is historical, not substituted for current main. Main and its untracked
`backend/tests/test_bonifica_result_normalization.py` preserved.

Registry established before independent reviewer assignment. Existing original
swarm reviewer `/root/r64_baseline` reused without model override/config edit or
CLI retry. Preflight accepted before native launch; terminal independently
accepted afterward. Reviewer writes only external `review/`, no native jobs.
Prior R69 WAL ENOSPC failure remains frozen; its separately authorized, reviewed
capacity correction passed 125 original tests, not an erased failure or retry.

## Native result and behavior matrix

**36 PASS, 0 skip/fail/error, 0 NOT_RUN**, JUnit 25.922 seconds. One complete
native invocation, retry zero. Exact original names match historical XML,
prepared selection, raw new XML and independent terminal audit.

| Behavior | Original coverage of variants | Fresh result |
| --- | --- | --- |
| Committed payment removes eligibility | 2 years × 2 modes × 3 phases | 12 PASS |
| Committed notification removes eligibility | 2 years × 2 modes × 3 phases | 12 PASS |
| Committed STEP recovery removes eligibility | 2 years × 2 modes × 3 phases | 12 PASS |
| Change before generation | No rendered document or draft | PASS |
| Change during renderer / before final commit | One private draft, review_required | PASS |
| Any disqualifying change | reminder_enabled false, no published reminder/batch notice | PASS |

Original tests use separate SQLAlchemy connections and real commits, selection,
accounting, writers, number reservations and registration. This is deterministic
interleaving, **not a truly simultaneous threaded race**. Three original storage/
renderer patches remain: synthetic document bytes do not certify PDF/DOCX,
end-to-end publication or the future confirmation protocol. Existing geo stubs
do not certify GIS; these paths do not exercise external providers.

## Isolation and evidence custody

Reviewed R69 V2 capacity reused: PostgreSQL 16.15 pinned local image
`sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea`,
PGDATA tmpfs 1 GiB, memory cap 2 GiB, one CPU, no image pull. Network none,
read-only root, no ports/named volumes/application mounts; sole new owned short
Unixsocket bind beneath a 0700 parent. UUID schemas, synthetic users/history/
notices and temporary files only. No production DB, quota/auth or WAL durability
change. Replacement environment alone does not exclude repository .env influence
on imported settings; no universal ambient-provider absence certificate claimed.

Private DB identity/schemas/user relations/routines and zero advisory locks
exact before/after; not a byte-level complete-catalog comparison. Positively
identified owned container stopped/removed and absence verified; tmpfs destroyed.
43 existing container and 67 volume sets unchanged. Empty owned socket directory
retained, not shared-resource deletion. Integration 2852 / main 2851 protected
input hashes exact; original test bytes equal HEAD/main. Freeze and manifests
preserve mutable prepublication documents and immutable historical receipts.

## Quality gates and coverage

`make complexity-ratchet BASE_REF=main`: exit 0, **PASS, 0 findings**, actual
baseline commit `a51a48dc4caefbdd1aea82fe4d749054b9465970`. No baseline update,
threshold/exclusion/ignore or coverage policy change. Global matcher/baseline
ambiguity remains distinct from the change gate. Final diff-check and Graphify
publication receipts are recorded in the companion JSON and durable manifest.

Initial external checkpoint finalizer exited 1 before publication: its JSON
parser selected the Make echo's `${BASE_REF:-origin/main}` brace, not the next
line's JSON. Original script and diagnosis retained; only external receipt
parser corrected for a distinct sealing verification. V2 stopped before
publication because the existing reports/** ignore hides the new companion
JSON from untracked enumeration. Its raw failure and original script retained;
explicit staging of only the four admitted documents includes the companion
with path-specific force, matching prior versioned companion reports. No ignore
policy changed. The active V3 sealing log is excluded from its own manifest and
bound afterward in the handoff chain, avoiding mutable-file checksum cycles.
No native test, scanner or Graphify rerun and no application/test/policy edit
for these bookkeeping corrections.

Coverage **NOT_MEASURED_UNCHANGED_RUNTIME**; not a new full-file coverage claim.
No full certified suites/report repeated for identical protected inputs. Last
full metrics remain 1681 files / 20360 callables / 1920 errors / 2736 warnings /
4656 overlapping findings. **No complexity reduction credit** for this check.

## Admission and residual gaps

Classification **VERIFIED_EXISTING_TEST_VARIANTS_NO_CHANGE_RUNTIME**. Only this
report, companion JSON, ownership registry and PROGRESS admitted to the local
documentation checkpoint. No caches, DB, dependencies, build or generated graph
admitted; main concurrent source and R43/R51/R63 partials remain excluded.

New 36 historically skipped identities verified. R68 + R69 + R70 verify
**162 of 449**, leaving **287 unverified by these follow-ups**. Historical R62
7142 PASS / 449 SKIP is unchanged, not rewritten as a complete backend rerun.
7 E2E skips, worker full-file coverage FAIL, matcher ambiguity, excluded partials
and the extreme complexity tail remain. Goal **ACTIVE / INCOMPLETE**.
No new runtime refactor, branch, push or main merge.

## Durable handoff and next decision

Evidence root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r70-notice-concurrency-pg`.
`FINAL_HANDOFF_MANIFEST.json` binds raw native receipts, review, source freezes,
resource custody and published documents. `publication/POST_COMMIT.json` and
`publication/HANDOFF_CHAIN.json` bind the later commit without checksum cycles.
Parent handoff: R69 `resume-20261013/publication/HANDOFF_CHAIN.json`.

Native manifest: 86 records, SHA
`543c766c349475489dd001add8e18f46ded6385dfd28c98f8d75ba08cb6887a2`.
Terminal review SHA
`20d906760b3b5f2d0c82ae49f3a21b87320cb1cf99640bd6619385fd35fa3ed9`;
review manifest SHA
`96b2c4072a02a5258f8a395504f7193ce85ef3384d24a5afc4fd7f7d2b0ac6e1`.
Stop after this checkpoint. Next decision: prioritize a separate coherent
unchanged-test prerequisite among remaining gaps; do not infer new refactoring
authorization or global completion.
