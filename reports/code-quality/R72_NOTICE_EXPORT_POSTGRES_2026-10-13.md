# R72 — committed export and concurrency on private PostgreSQL

## Snapshot and ownership

Verification only, no runtime refactor. Full original
`backend/tests/ruolo/test_notice_export.py`, 27 historical PostgreSQL skips.
Sources, fixtures, assertions, timeout, migrations and policies unchanged.
Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`, starting HEAD
`e7effa2ac094099a99506bd87f0a5c6b9d3ec616`. Actual main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`; original 55a1b1d is historical.

Registry predates assignment. Existing swarm reviewer `/root/r64_baseline` owns
external review only; Coordinator owns docs/evidence and PROGRESS after freeze.
Independent preparation accepted before launch; terminal accepted with disclosed
nonruntime metadata drift. No model override, repository edit or native job by
reviewer. Prior mutable documents, parent checkpoint and failures preserved.

## Native result and characterization matrix

**27 PASS, 0 skip/fail/error, 0 NOT_RUN**, JUnit 18.510 seconds. One full original
invocation, retry zero; exact historical identities independently verified.

| Behavior | Original verification | Result |
| --- | --- | --- |
| Original bytes/manifest/hash and idempotence | Genuine ZIP contents, one archive, each audited claim | PASS |
| Payment/notification/STEP before or after first export | New/repeated download blocked after genuine committed writer | 6 PASS |
| Writer during packaging | No archive or claim committed | PASS |
| Two simultaneous exporters | Original ThreadPoolExecutor2 / Barrier10s; equal bytes, one archive/two claims | PASS |
| Tampered/missing confirmation, reservations, bytes, manifest/date | Delivery refused; no extra claim | 14 PASS |
| Confirmation changed during packaging | Fresh snapshot fence rejects delivery | PASS |
| Native constraint commit failure | Exception, no returned bytes or stored archive | PASS |
| Regeneration identity uniqueness | New identity allowed before export; duplicate export requires explicit correction | 2 PASS |

Actual private transactional confirmation, PostgreSQL locks, real ZIP packaging
and audit claims executed. Unlike earlier deterministic writer interleavings,
the two-export case uses genuine simultaneous threaded packaging; original
barrier/timeout unchanged. Generation renderer remains mocked with synthetic
document bytes; storage is real under private TMPDIR. This is service-level
verification, not real PDF/DOCX, auth/API/HTTP/E2E/GIS/provider or NAS proof.
No production confirmation/dispatch, auth/quota or functional change authorized.

## Preserved custody failure and concurrent work

Original after-native `inventory.py` failed its complete-main-snapshot assertion:
protected entries had already compared exact, but main status gained
` M .codex/config.toml` beside pre-existing untracked Bonifica. Main HEAD/base
unchanged. The shell lacked errexit and continued; overall exit 0 does **not**
certify that inventory. Missing inputs.after-native.json remains missing.
No original redirected inventory process log exists: only a labeled tool-output
transcription and diagnosis, not retrospectively claimed raw byte evidence.

Native test/cleanup exit 0 is separate and genuine. Original manifest 92 records
preceded drift diagnosis, so Coordinator's initial contrary message was corrected.
Distinct custody observation/supplement preserves the original failure and
explicitly checks only the documented status delta; no native retry or original
inventory alteration. Independent review verifies 2852 integration / 2851 main
protected app/test/quality-control hashes exact, actual heads/base unchanged.

Concurrent Codex config: 16 additions/2 removals, keys command/args/PYTHONPATH/
sandbox_mode; values not published. Committed/current hashes are bound externally.
**Author UNKNOWN; CONCORRENTE and excluded.** Not edited, staged, copied, overridden
or attributed to this campaign; no effective model change inferred. No claim
that every working-tree/control setting globally remained unchanged.

Reviewer-only audit v1–v4 failed incorrect static assumptions (status, receipt
spelling, Python -m selection); raw scripts/logs/exits retained. Authoritative
static audit v5 passes. These are not native failures or native retries.
Two incorrect observation-tool cell handles are also disclosed externally;
actual reviewer delivery was awaited without restarting any job.

## Private environment and resource custody

Reviewed pinned local PostgreSQL 16.15 image
`sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea`,
1 GiB PGDATA tmpfs / 2 GiB memory / one CPU, network none/read-only root,
no ports/named volumes/application mounts/image pull. New owned short Unixsocket
under 0700 parent; UUID schemas and synthetic users/notices/claims only.
Replacement environment alone does not exclude all repository .env influence;
selected call-path review is not a universal ambient-provider absence certificate.

Private DB identity/schemas/user relations/routines and zero advisory locks exact
before/after. Positively owned container stopped/removed, absence confirmed and
tmpfs destroyed. Empty socket root retained. 43 original containers / 67 volumes
exact sets. No production/shared resource removed or concurrent work overwritten.

## Gates, admission and remaining scope

`make complexity-ratchet BASE_REF=main`: **PASS, 0 findings**, actual baseline
commit a51a48dc. Final diff-check and Graphify docs publication receipts in JSON
and durable handoff. Baseline/threshold/exclusion/ignore/coverage policy unchanged;
global matcher ambiguity remains separate. Full suites/report not repeated for
unchanged protected runtime inputs. Coverage NOT_MEASURED_UNCHANGED_RUNTIME;
worker full-file 100% remains FAIL. No complexity reduction credit; last metrics
1681 files / 20360 callables / 1920 errors / 2736 warnings / 4656 overlapping findings.

Classification VERIFIED_EXISTING_TEST_VARIANTS_NO_CHANGE_RUNTIME, with bounded
custody acceptance, **not** conversion of original full-snapshot FAIL to PASS.
Only report/JSON/registry/PROGRESS admitted to local documentation checkpoint.
Concurrent main config/Bonifica, excluded R43/R51/R63, cache/DB/dependencies/build/
generated graph not admitted. No push, main merge or new runtime refactor.

Cumulative fresh verification **226 of 449** historical backend skip identities;
**223 still unverified by follow-ups**. R62 historical 7142 PASS / 449 SKIP remains
unchanged. 7 E2E skips, worker coverage FAIL, matcher ambiguity, excluded partials
and extreme tail remain. Global goal **ACTIVE / INCOMPLETE**.

## Durable handoff

`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r72-notice-export-pg`.
Native manifest SHA `c725187d7837537e578320932680935088995d453928f9b7c034bbfa3dee333c`;
100-record custody supplement SHA
`8e9cd7ab0ede0666a38b8f6910ae5ac63b3d6f9b627530b88fc9912f28f7070d`.
Terminal review SHA `1347cb1e0b37041636014457230ac3d87a5793e33d2a6e70c741d4d1bc17999c`;
review manifest SHA `8295a26f14ae6c779e1aff0a0dd2ef16c573f5b54d3d17a7dc817aa2166b5dd4`.
FINAL_HANDOFF_MANIFEST.json binds stable receipts and published docs;
publication/POST_COMMIT.json and HANDOFF_CHAIN.json bind later commit, without
checksum cycles. Parent: R71 handoff. Next decision: another coherent existing
test prerequisite, not implied new refactoring or global completion.
