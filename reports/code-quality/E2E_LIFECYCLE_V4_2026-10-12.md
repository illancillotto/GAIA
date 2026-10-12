# Private E2E V4 — Chromium path diagnosis and verified checkpoint

## Scope and snapshot

User reactivates the global goal after checkpoint4d6cdfd9. No new application
refactoring. Integration branch `refactor/complexity-campaign-20261008` input
HEAD `4d6cdfd9a835297ca50a3f28860d8da9b97bcb72`; current main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Historical initial snapshot
`55a1b1d35911451e018b662c2acc450bf5994ea2` is not today's merge-base.
Ownership: `docs/code-quality/MULTI_AGENT_OWNERSHIP_E2E_DIAGNOSIS_2026-10-12.md`.
Coordinator sole native owner, two disjoint static reviewers. Main tracked
runtime unchanged; known untracked Bonifica characterization test preserved.

## Explained failure and local environment correction

V3 failed before assertions at full Chromium launch. Browser-only diagnostic
comparison with identical Chromium executable/options: TMPDIR131bytes gives
SIGTRAP; private short25byte root launches Chromium147 and renders a synthetic
data page. Logging-only argument is disclosed, not a test/config change.
Independent real Unixsocket bind long147byte pathname fails, short41 succeeds.
An additional strace probe with original106byte TMPDIR reproduces SIGTRAP next
to ProcessSingleton socket setup. No database/stack/application request in probes.

This proves a temporary-path-dependent environment issue and a working
correction; no precise Chromium C++ source line attribution is claimed.
V4 only changes TMPDIR to newly created private owned0700 nonsymlink root
`/tmp/gaia-e2e-_xkm88cq` (22bytes), validated before each launch. No channel
switch, browser reinstall, quota/auth changes, test edits or weakened assertions.
Four new path/socket/refusal tests PASS. Existing guard bytes/schema exact V3;
its32guard tests plus detached proof and six supervisor tests remain historical
accepted evidence, not falsely reported as rerun or full external-tool coverage.

Accepted V4 runner SHA256
`dbe3a092d656c4d9100f02d248e2fc7d84b1fbaa80b01da0c7058de675e53aab`;
privateTMP helper
`9fe1a5c0786c7e7dacab1cfc3623ba3679cc24d46456d699a923e3b9d29469dc`.
Fresh originalDB copy, new evidence root, documented environment difference;
V3 raw FAIL and earlier STOP receipts remain unchanged. This is a distinct
explained verification, not an unrecorded retry of a failed native case.

## Native results and fidelity

| Result | Count |
| --- | ---: |
| Full current collection |61 |
| Attempts, each retry0 |61 |
| PASS |54 |
| Explicit SKIP, NOT VERIFIED |7 |
| FAIL |0 |
| NOT_RUN |0 |

Original24specs, config, case order and project/file/line/column/fulltitle
identities matched. Each selected list/result is exactly one case/one attempt;
workers1/retries0/max-failures1. One native invocation and owned stack restart
per case; this is explicitly NOT one uninterrupted monolithic suite execution.
Current native result fidelity and complete collection are verified independently
of the old R61 build's incomplete historical serving-byte archive.

Quota-failing historical case42 `ruolo-avvisi.spec.ts:34` PASS.
Full Chromium case55/56 `ruolo-solleciti.spec.ts:9` PASS at1440px/390px:
real PDF-viewer extension and successful load, 409 conflicts, confirmation,
export/download and no overflow checks remain intact. Mocked MCP preview
case59 and contextual widget case60 PASS; not proof of live MCP/model services.

## Seven skips, not PASS

- One removed single Catasto search, explicit existing skip.
- Two Catasto drilldowns: no distretto data in the private SQLite stack.
- Two optional GIS territorio cases: activation flag intentionally unchanged.
- Two private Docker/MCP integration cases: optional synthetic stack unavailable.

Exact native skip annotations are retained in `root-terminal-audit.json` and
each raw native JSON. No new skip or exclusion added; these remain NOT VERIFIED.

## Safety, custody and evidence

Initial authorized synthetic reset removes21sessions/20devices.61completed
case receipts subsequently remove21sessions/21devices total. Cleanup only
AFTER native result, stopped actual owned handles, recursive kernelpopulated0,
free ports and real rollback-mode BEGINEXCLUSIVE. Durable before-image/row
inventory precedes target-only sessions/devices DELETE;280other tables, schema
and FKs exact per transaction. Original R49 DB SHA256 remains
`ebc902bd5479951f0e3971c85fd21423bee368a21f6c2b0c02eea3fa0a71524d`.
All owned cgroups empty/removed and services terminal, no shared-scope kill.
Private nonadversarial ownership remains bounded, not a global raw-reader census.

Protected2732inputs/main custody exact before/after. R61 sources1047/1047 and
selected200artifacts match; current serving1405/nft253/browser8 snapshots stable.
No retrospective full historical serving-byte provenance claimed. No certified
frontend unit/build/backend suite repeated with identical inputs.

External evidence root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/e2e-lifecycle-v4`.
Diagnosis root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/e2e-lifecycle-v3/diagnosis-v4`.
Sources/freezes, reviews, complete collection,61native outcomes,61cleanup
inventories and original-copy reset, final custody and PDF screenshots retained.
Screenshots hardcoded by unchanged specs under/tmp are copied durably; no claim
made about their historical pre-run bytes. Prior mutable registry/PROGRESS
archived before updates. Companion V4 JSON indexes paths/checksums/manifests.
No DB/cache/dependencies/build/browser artifacts/graphify-out committed.

## Completion boundary

Both specific blockers now removed: synthetic devices do not accumulate;
full Chromium/PDF cases pass with a short private temporary path.
This is not completion of the global complexity campaign.449backend skips,
worker full-file coverage failure, global baseline/matcher ambiguity, seven
E2E skips and excluded R43/R51/R63 partials remain open. Extreme hotspots
and strategic reductions remain incomplete; no new refactor grant inferred.
Global objective stays INCOMPLETE/ACTIVE, not COMPLETE. No push/main integration.

## Independent gates

Both reviewers reconstructed raw61outcomes and verified61case cleanup plus
collection reset,62terminal cgroup scopes, custody and exact frozen inputs.
Runner terminal review SHA256
`ce6cf313a7cdbdd725b84896648dd081f259052d13c993fd39b0f20dbdbf150c`;
cleanup terminal review
`d02043818bbedf626400fa09683f3566a862c2bd07da6693879a6f73aed20779`.
No reviewer native test/browser/DB execution. Ratchet against actualmain PASS,
zero findings; baseline/matcher hashes unchanged, diff-check PASS.
