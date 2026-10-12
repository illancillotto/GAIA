# R65 — SISTER retry metadata characterization

## Ownership and snapshot

Test-only slice on `refactor/complexity-campaign-20261008`, starting HEAD
`b93b636cdd20fb34ddcc2b8434d390984402b551`. Actual main/merge-base is
`a51a48dc4caefbdd1aea82fe4d749054b9465970`; historical campaign snapshot
`55a1b1d35911451e018b662c2acc450bf5994ea2` is not the current merge-base.
Exclusive ownership was registered before execution in
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R65_RETRY_METADATA_2026-10-12.md`.
Main and its untracked Bonifica test remain untouched.

Sole code addition: `modules/elaborazioni/worker/tests/test_sister_retry_metadata.py`,
SHA256 `9114ae34bdf575913bc3dc85d7fa54f9fa66fecf47e250fec7692f49610cdaf2`.
Runtime `sister_retry_metadata.py` is byte-identical to HEAD/main, SHA256
`a7e8494b973da6eb7755b2cf36c3a89304c626ae5c0ea0f5d991d8bdc29ac071`.
No runtime, existing test, baseline, matcher, threshold, exclusion, auth,
quota, schema or coverage-policy change. No new application refactor.

## Behavior and test matrix

| Behavior | Existing protection | Missing / added | Result |
| --- | --- | --- | --- |
| Four remote fields cleared, other request state retained | Worker reliability flows | Real mapped request, two successive calls, six parameter combinations | PASS |
| Baseline retained by identity for default/False | Existing retry flows | Empty/populated baseline, default and explicit False | PASS |
| Baseline cleared only for explicit True | Historical line22 / arc21→22 uncovered | Empty/populated baseline, explicit True | PASS |
| Correlation, invalid PDF and session reasons/codes | Existing coordinator test | Three exception cases with exact public tuple assertions | PASS |
| Coordinator deadline and fencing token | Existing reliability test | Existing test run unchanged | PASS |

The mapped instances are real SQLAlchemy objects, not helper mocks. Tests
verify in-memory behavior, not persistence/transactions or external portals.
No DB-backed fixture is requested; a private SQLite URL is supplied anyway.
Two invalid model keyword names were corrected before the first pytest run:
`error_code`→`last_error_code`, `attempt_count`→`attempts`.

## Native tests and coverage

Standalone new file: **9 PASS**, 0 skipped, 1.54s. Separate existing coordinator
case: **1 PASS**, 0 skipped, 2.07s. No test retry. Exact argv, logs, exits and
JUnit XML are durable in external evidence.

| Helper full file | Statements | Branches | Missing / excluded |
| --- | ---: | ---: | --- |
| Historical R50 | 16/17 (94.12%) | 5/6 (83.33%) | line22, arc21→22; no excluded lines |
| New standalone run | 17/17 (100%) | 6/6 (100%) | None |
| New run plus existing case | 17/17 (100%) | 6/6 (100%) | None |

Coverage measures the unchanged complete helper; the external report scope is
not a repository policy change. Both statement and branch counts are checked
directly in JSON, not inferred from rounded percentages. Tests genuinely cover
the explicit clear-baseline behavior without removing a guard or mocking it.

The full worker suite is **not rerun**: prior R50 certificate remains 782 PASS,
1 PostgreSQL skip, with runtime unchanged. Its recorded aggregate remains
6075/6077 statements, 1628/1630 branches; this focused run is not a replacement
full-worker certificate. Pool line523 / arc522→523 remains unresolved, therefore
full-worker100 remains **FAIL**. No scheduler manipulation or waiver.

Launcher used `env -i` with PATH/HOME/LANG/private TMPDIR and synthetic settings.
`LAUNCH_RECEIPT.json` is reconstructed from the actual tool invocation after
terminal execution, not a contemporaneous environment dump. Repository `.env`
can still be read by Settings; absence of every provider credential is not
certified. Selected tests do not invoke live providers.

## Metrics and gates

| Official scope including worker tests | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Files | 1680 | 1681 | +1 |
| Callables | 20358 | 20360 | +2 |
| Errors | 1920 | 1920 | 0 |
| Warnings | 2736 | 2736 | 0 |
| Overlapping findings | 4656 | 4656 | 0 |

Raw comparison with R64 `root-checkpoint/integration-complexity.json` proves
all previous file objects, callable sequence and findings exactly unchanged.
New test: effective LOC65, cognitive sum/max5, cyclomatic sum5/max4, no finding.
This is test consolidation, **not** a runtime complexity reduction.

`make style-ratchet BASE_REF=main`, Ruff new-file format check, full complexity
report, `make complexity-ratchet BASE_REF=main` and `git diff --check` all PASS.
Actual ratchet baseline commit `a51a48dc…`, zero finding; no BASE_REF switch.
Baseline hash remains `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
Exceptions hash remains `81a515050e5d312ac4a453fa1bdaa999cfc11ad6a652659776bf5747c6b69168`.
2850 integration and 2849 main protected source/test/tooling inputs show zero
drift before/after gates; configs independently match expected hashes and both
Git refs. Documentation and ignored generated artifacts are outside that
input inventory. Main HEAD/status also remain identical.

One evidence-postprocessing extraction failed by selecting Make's shell `{`
instead of the JSON boundary. `POSTPROCESSING_NOTE.md` preserves the explanation;
only static extraction was corrected. No native test/gate was repeated and the
raw ratchet receipt is unchanged. Global baseline check is not rerun or declared
PASS; its ambiguity remains distinct from the change ratchet.

## Review, publication and handoff

Independent static review, Graphify publication and durable manifest are recorded
in the companion `R65_RETRY_METADATA_2026-10-12.json` after terminal publication.
Mutable PROGRESS and ownership were archived before updates. Historical receipts
and failures were not rewritten. Evidence root:

`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r65-retry-metadata`

Selective local commit only; no push or main merge. Classification:
**TEST_ONLY_CHARACTERIZATION — NO_CHANGE_RUNTIME**. Global goal **INCOMPLETE**.
Seven E2E skips, 449 backend skips, worker PostgreSQL skip, pool coverage gap,
global matcher ambiguity, excluded R43/R51/R63 and extreme complexity tail remain
open. Recommended next decision: separately assess the pool guard's execution
contract; do not remove it or start a new runtime refactor automatically.
