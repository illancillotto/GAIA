# R64 — Independent final Bonifica verification

## Scope and snapshot

Dedicated `review/complexity-r64-bonifica-results` at HEAD/main merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Coordinator explicitly transferred
sole native token after author release. Exact candidate imported with
`apply_patch`: runtime SHA256
`f03279ca606ef3e2de6a77a35841205a063ff422174dd90695006c5ba77c4082`, NEWspec
`a3b01fd736878b0d95068a958e213773e13a6056dc4b252c4a150418e0aab150`.
No candidate modification, existing-test edit, baseline/config/policy edit,
commit, merge or push performed.

## Independent native gates

| Gate | Result | Durable evidence |
| --- | --- | --- |
| Six pertinent suites |253 PASS,0failure/error/skip |final-evidence/native.log, native/tests.xml |
| Full-file statement coverage |400/400100%,0missing |native/coverage.json, native/native.coverage |
| Full-file branch coverage |126/126100%,0missing |Same raw/JSON coverage |
| Runtime/test custody |1320 input hashes exact before/after |native/inputs-before.json, inputs-after.json |
| Backend compile/style |PASS,2changedfiles, NEWspec format checked |lint.argv/log/exit |
| Actual-main ratchet |PASS,0findings, baseline_commit a51a48dc |ratchet.argv/log/exit/base.txt |
| Diff whitespace |PASS |diff-check.log/exit |

Evidence root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/final-evidence`.
Runner `run_independent.py` disables dotenv loading and supplies synthetic
credentials/private SQLite only; no production or external portal access.
Coverage collects full runtime, no new exclusion. Two original unsupported
entity lines remain historic exclusions; no claim of zero exclusions.
JWT short-test-key warnings remain visible (50warnings), not hidden.

## Static reduction proof

Independent prior reverse-substitution binds all10selected counters/errors
and restores the complete original module AST. No changes to dispatch, query,
credential lifecycle, persistence, exception handling, retries or cleanup.
Principal cognitive269→174, cyclomatic47→37, LOC232→202; file sums
cognitive422→328 and cyclomatic181→173, fileLOC738→717. Helper1/2/9 under
thresholds, no transferred orchestration. See static review and frozen proof.
These metrics are author scanner evidence independently reviewed, not an
additional full scanner run. Nesting13 and residual legacy errors remain.

## Metadata auditor STOP — no admission certificate yet

Native gates above are terminal0 and are not retried. Subsequent independent
metadata auditor `audit_terminal.py` terminal1 at its own path assertion:
Coverage JSON uses cwd-relative key `app/services/elaborazioni_bonifica_sync.py`,
while auditor expected absolute root/backend path. Separate read-only inspection
confirmed raw CoverageDB file row has the expected absolute reviewer source.
This is an auditor path-binding assumption failure, not a runtime test failure;
full raw-arc/exclusion/author-manifest proof remains incomplete because auditor
stopped before those checks. Original186 retention and253 exact identity
multisets were checked before the STOP, but no complete auditorPASS is claimed.

Auditor source/log/exit copied byte-exact to `final-evidence/metadata-stop`
before any prospective correction. Original metadata receipts retained.
Coordinator notified; no auditor repair or retry without distinct grant.
No new scanner/tests/build/native reruns. Independent admission disposition
PENDING_METADATA_BINDING; runtime remains excluded until required proof.

## Handoff and residual scope

Sole native token RELEASED: tests/lint/ratchet processes terminal, no verifier
heavy process remains. Runtime and NEWspec remain exact frozen candidate;
only reviewer reports are authored. Historical original fixture67ERROR STOP,
authorized email-only repair and subsequent253PASS evidence remain separate.
Global baseline ambiguity,449 backend skips, worker coverage/E2E gaps and
global campaign incompletion remain unchanged and are not certified here.
Graphify integration remains Coordinator-owned. No new slice authorized.
