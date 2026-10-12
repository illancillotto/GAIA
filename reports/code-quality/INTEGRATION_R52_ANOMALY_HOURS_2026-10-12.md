# R52 — Hours discrepancy guard integration

## Ownership and snapshot

Registry predates separate SSD author/reviewer worktrees. Integration branch
refactor/complexity-campaign-20261008, HEAD114fbf7196382c6446a7963c34bd89e4c9795ef5;
actual main/merge-base55a1b1d35911451e018b662c2acc450bf5994ea2. Main concurrent
work unchanged. R43/R51 and other pending decisions were not reactivated.

Only runtime change: `analytics.py` hours_discrepancy emission guard. One new
test module; old tests/config/baseline/matcher read-only. Source0aa1f196 and
testb430bc30 imported byte-exact after independent reviewer50b7a529 acceptance.
Author87/reviewer21freeze records verified. No commit, push or Git merge.

## Behavioral invariants and characterization

Input → date parsing → unchanged inclusive/null-filtered queries → same ordered
int conversions/subtraction/abs → inverse integer guard → identical emission
→ unchanged stable severity sort/response. Successful diff is a nonnegative
integer, so <=60 complements >60 exactly. No loop-tail work is skipped.

| Behavior | Existing protection | Added or retained | Actual result |
|---|---|---|---|
| Signed0/59/60/61/119/120/121 and severity thresholds | R2 boundaries | New persisted signed matrix, negative/zero durations | PASS before/after/root |
| Null exclusion, query/bind/order, ORM state | Analytics characterization | Real SQL listener and persisted state receipts | PASS before/after/root |
| Inclusive/default/invalid/reversed date windows | Original analytics | New edge cases, captured-current-date seam | PASS before/after/root |
| Filters, stable ties, payload/count ordering | R2/R27 | Mixed-severity literal ordering and filters | PASS before/after/root |
| Anonymous401/module403/allowed200/type alias | Original public route | Real login and only DB override | PASS before/after/root |
| Other analytics and retained snapshot lifetime | Existing fifteen-spec union | Every unchanged old assertion retained | PASS before/after/root |

## Actual tests, coverage and style

Author original5091/candidate51392 TERMINAL0; root actual integration21779
TERMINAL0. Each has379genuine and78supplemental PASS/zero skip/failure/error,
15source hashes and457exact JUnit identities, disjoint complete partitions.
Supplemental synthetic/nested_ast/unflushed assertions run without coverage.
Root independently audits raw identities/JSON/XML, not summary booleans.

Analytics full-file statement623/623→624/624, branch252/252→252/252,100% both.
Four defensive exclusions413/414/883/884 unchanged; no new exclusions or policy
waiver. Added continue is covered. Unchanged driver/orphan helpers49/16 and27/10
also full100. Synthetic JWT-length warnings retained; Python3.12.3 environment
disclosed versus repository style target3.11. No external-provider/PG certificate.

Root env-i launcher with synthetic settings/private SQLite/storage, installed
interpreter/dependencies; no install or production settings change. All nine
gates exit0: genuine/coverage audit/supplement/union audit/Ruff/new-test format/
whole report/main55a ratchet/diff check. Initial patch-header preparation error
and invalid observation calls are documented separately; neither restarted
native tests or changed reviewed bytes. No native gate failure or blind retry.

Final read-only review identified Node provenance drift: R50 recorded24.14.0,
R52 isolated root recorded18.19.1 via system PATH. The initial equality audit
stopped and is preserved. Coordinator authorized a distinct static audit using
the existing `comparable_engines` rule, not a tooling or baseline change.
Analyzer identities/availability match; an unrecorded historical npm version
is not certified. Full object comparison can establish observed corpus
compatibility only, not universal cross-Node equivalence. No native rerun.

## Measured before / after / delta

| Metric | Before | Actual root after | Delta |
|---|---:|---:|---:|
| anomalies cognitive |239|238|-1 (-0.42%)|
| anomalies cyclomatic / LOC / nesting / params |112 /320 /4 /5|112 /320 /4 /5|0|
| File cognitive sum / max |724 /239|723 /238|-1 /-1|
| File LOC / callable / cyclomatic sum |1193 /29 /501|1193 /29 /501|0|
| Official files / callable |1674 /20339|1674 /20339|0|
| Error / warning / overlapping finding |1920 /2735 /4655|1920 /2735 /4655|0|

Root full report SHA2fd85c343b76e697e79f2282691d7ef662a93b5f9e14e1e5ff97f48f6f61c43c
compared with R50 SHA504e7355: every prior callable/file object except the
target/file cognitive and derived density fields unchanged; scope identical. Backend tests are
outside the official backend/app scope, so the new test adds no official AST
file/callable object. No scope expansion. Author whole totals differ because
its clean-HEAD source lacks admitted integration overlays; not a campaign delta.

Entire-module independent AST proof accepts only inverse guard/continue and
identical dedented append; operand layout is AST-neutral and gets no credit.
No helper relocation/duplication or new service. Physical decisions unchanged;
emission is one conditional level shallower, whole callable max nesting4 remains.

## Ratchet, custody and classification

Actual root BASE_REF=main/baseline55a PASS/findings[]. Baseline38e6b794 and
matcher32b11750 remain exact; no thresholds/config/exclusions changed. Global
historical baseline status is separate; complexity-check was NOT_RUN for R52.
Root2809protected inputs: no drift outside exact runtime/new-test paths, both
equal frozen author bytes; main input/status/binarydiff/HEAD unchanged.

Classification **IMPROVED**, small local guard only. No finding elimination,
removed extreme callable or substantial global reduction is claimed. Dedicated
final actual-root reviewad531b0a ACCEPT_VERIFIED_LOCAL_IMPROVEMENT;14record
freeze0c4868c8 checked, no mismatch. Initial independent source/raw author review
is completed. Corpus receipts/root freeze publication remain separate.
Existing global suites are historical checkpoints; full backend
suite after R52 is NOT_RUN. Campaign **ACTIVE / INCOMPLETE**.

## Evidence and next step

Graphify correct corpus targets completed serially: openai-base-url patch
already applied; operazioni-code reports no topology change; operazioni-docs
103nodes134edges11communities and platform-docs586nodes670edges119communities.
Both docs logs show chunk1/1done with no semantic-chunk failure, exit0. Model
gpt-reserve; cost estimates$0.0030/$0.0100. Ignored graphs are not versioned,
and graph outputs are not complexity evidence. Raw logs/exits in root-evidence.

SSD `.codex-gaia-campaign-20261012-r52-anomaly-hours`: frozen author/reviewer,
root-native commands/logs/exits/inventories/JUnit/coverage/fullreport/ratchet,
root-evidence exact identity/metric/custody audits and preparation diagnostics.
Final read-only composite review complete; stop this responsibility, admitted
to integration working tree without Git merge/commit. Pending R43/R51/E2E/
Bonifica/worker decisions remain separate.
