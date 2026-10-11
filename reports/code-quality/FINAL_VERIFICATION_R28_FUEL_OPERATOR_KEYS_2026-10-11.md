# R28 — Final Verification: Fuel Operator Keys

## Status

ACCEPT_IMPROVED. Independent original31 focus and original/candidate342 real-only
unions pass; genuine full-file100 statement/branch coverage, native before/after
metrics, compensated debt audit, Ruff/new-spec format, actual-main55a ratchet and
final custody pass. Initial private auditor schema failure remains preserved;
separate corrected raw audit does not rerun tests or weaken any policy.
No Graphify, build or installation executed by this verifier.
The global campaign remains ACTIVE / INCOMPLETE.

## Ownership and Snapshot

- Exclusive output: this NEW final-verification report and private evidence
  `~/.cache/gaia-campaign/20261011-r28-final/`.
- Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261011-r28-fuel-operator-keys-final`.
- Branch: `verify/complexity-r28-fuel-operator-keys`.
- Initial HEAD: `fed2cc7d0f2ee1dd128b6d11f68655179b9711d7`; initial status clean.
- Actual merge-base with main: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Root authoritative R28 registry read before any output creation.
- Runtime, old tests, baseline, tooling and all other campaign outputs read-only.
- Coordinator alone publishes exact paths; this verifier does not commit.

## Frozen Inputs

- Original runtime SHA-256:
  `e877a34cc20b570306939f9f527048bf77584f6b1d3e78f9b4addf557fc46279`.
- Frozen author runtime SHA-256:
  `49b9ffeef7851e12aa4e8a309fb63356d226a6526cffbdaef052d4c9d3fde0d7`.
- NEW author specification SHA-256:
  `f899cf78f3842663108e624dc79658d36b5645de03676cab161ad36f21638163`.
- Baseline SHA-256:
  `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.

All four hashes were read independently. At static admission the verifier runtime
remained original; author runtime and NEW specification were read cross-worktree.
Coordinator later imported the exact NEW specification, then separately authorized
the byte-exact candidate patch only after fresh original acceptance.
Existing ignored dependency links resolve to the integration dependency graph;
no dependency installation or version change was made.

## Static Behavioral Invariants

The diff adds one typed nested `_fuel_operator_key` selector and replaces
exactly two duplicated branches in `fuel_analytics`. It changes no query, ORM
retention list/map, route-loop local, response constructor, sort or consolidation.

1. UUID selection still uses `is not None`; a zero UUID is not treated as absent.
2. The selected UUID attribute is still read twice: condition then return.
3. Only when UUID is absent is the raw name checked, then read again if truthy.
4. Names remain untrimmed and case-sensitive; empty/None falls back to the exact
   captured `__no_operator__` sentinel, including its pre-existing collision.
5. Primary top-operator name consolidation remains distinct from per-vehicle
   related raw grouping; changing both to consolidated keys would be functional.
6. Log/vehicle order, stable ties, related top-five limits, metrics and station
   projections remain outside the selector and byte-unchanged in the diff.
7. Query order, inclusive day filters, permission checks, transaction boundaries,
   ORM strong references and all other anomaly/fuel responsibilities remain intact.

Static source equivalence supports native admission; it is not a replacement for
independent genuine characterization, full-file coverage or actual-main ratchet.

## Prepared Verification Matrix

| Behavior / gate | Existing or NEW evidence | Independent status |
| --- | --- | --- |
| UUID precedence, zero UUID, raw-name/sentinel variants | NEW real persisted parametrized public-route specification, 24 cases | ORIGINAL/CANDIDATE PASS |
| Primary-only name consolidation | NEW 3 persisted cases | ORIGINAL/CANDIDATE PASS |
| Sentinel collision | NEW persisted case | ORIGINAL/CANDIDATE PASS |
| Stable first-seen ties and related-only limit | NEW persisted case | ORIGINAL/CANDIDATE PASS |
| Authentication, permissions and inclusive dates | NEW 2 authenticated route cases | ORIGINAL/CANDIDATE PASS |
| Whole analytics + driver/orphan behavior and ORM lifetime | Immutable 11 old specs + NEW spec, real-only union | ORIGINAL/CANDIDATE PASS |
| Original full-file coverage | Fresh 342 cases, analytics 634 statements / 264 branches | PASS100 |
| Candidate full-file coverage | Same 342 cases, analytics632/260; driver49/16; orphan27/10 | PASS100 |
| Complexity/debt/LOC/tail and unchanged-callable custody | Whole native reports, exact before/after auditor | PASS |
| Runtime Ruff and NEW spec formatting | Full touched runtime and NEW spec | PASS0 |
| Change gate | Actual `make complexity-ratchet BASE_REF=main`, actual base55a | PASS0/findings[] |
| Main/baseline/all-runtime/test custody | Hashes and exact-path diff | PASS |

Private original `run-focus.sh` and both phases of `run-union.sh` executed after
separate explicit token transfers. Both phases retain command, native exit,
XML, raw coverage, input hashes and independent audit. The first unexplained
failure stops the pipeline without retry or alteration of failed evidence.

## Prior Author Failure Attribution

Author original focus first recorded 29 PASS / 2 authentication FAIL, native1,
before any runtime change. Missing global-engine `application_users` originated
from the NEW specification calling `_auth_headers` before its real `get_db`
override. Coordinator separately admitted NEW-spec-only fixture correction:
override now covers login and public request, restoring its prior value.
Initial spec/log/XML/exit remain preserved; no app change or assertion weakening.
Author corrected original 31 focus and 342 union PASS/full100 were read as
author evidence only, not independent verifier results.

## Metric-Audit Preparation Correction

The initial unexecuted private audit incorrectly required strict decrease of
the raw cyclomatic aggregate. Coordinator supplied measured author evidence:
file raw sum513→514 while callable entries28→29; normalized
sum(cyclomatic−1)485→485. The native Python scanner counts nested-selector
decisions within the parent and separately within the helper. Physical repeated
if sites decrease4→2; real coverage branch outcomes264→260.

Coordinator separately authorized correction of this UNEXECUTED private audit
to normalized non-growth and raw increase no greater than added callable entries.
Strict cognitive/LOC reduction and all unchanged callable/runtime checks remain.
No native verifier failure, report rerun, application/test change, policy change,
baseline inflation or weakening of the actual ratchet has occurred here.
Author initial failed strict-normalized audit1 remains preserved in its evidence.
Raw aggregate growth must be explicitly disclosed, not described as a decrease.

## Coverage, Metrics, Ratchet and Classification

Independent original focus session3124/native0/audit0:31 PASS without skips.
Original union session1761: native0, XML342 tests /0errors /0failures /0skipped;
full100 analytics634statements264branch outcomes, driver49/16, orphan27/10.
The shell returned1 because the subsequent private audit accessed the absent
`summary.partial_branches`; actual Coverage JSON contains `num_partial_branches`.
Coordinator authorized a NEW `audit-union-schema-corrected.py` changing only that
field, no fallback. Retained raw original audit0 under new schema-corrected
labels; initial script/log/exit1 untouched and no tests rerun. Fresh native whole
original report session95220/native0:1673files20322callables1924errors2740warnings
4664findings, parser/exception errors empty. Independent original custody0:
all1673runtime unchanged, old specifications unchanged, main diff9f85/status0d54,
baseline38e6 and actual merge-base55a preserved.
Author baseline attribution only:
fuel cognitive250 / cyclomatic160 / LOC348; file LOC1204, cognitive sum757,
cyclomatic sum513, 28callables. No measured delta or IMPROVED classification
is granted by this static document.

The historical global baseline FAIL30 is separate from the authoritative
change ratchet. Baseline, thresholds, exclusions and ignore configuration
must not be changed to obtain PASS. Final application suites/build/E2E remain
uncertified; acceptance of this narrow slice cannot complete the global goal.

## Terminal Candidate Verification

All gates ran serially under the exclusive FINAL token after Coordinator exact
candidate admission. No original native test was rerun after schema correction.
Candidate342 session89743/native0/audit0, whole report session46588/native0,
compensated metrics audit0, Ruff0/format0, actual-main ratchet session14436/native0
and raw ratchet audit0, post-input hash check0 and final custody0.

| Metric | Original | Candidate | Delta |
| --- | ---: | ---: | ---: |
| Fuel cognitive | 250 | 240 | -10 (-4%) |
| Fuel cyclomatic | 160 | 158 | -2 |
| Fuel effective LOC | 348 | 344 | -4 |
| Fuel nesting / params | 4 / 5 | 4 / 5 | 0 |
| File cognitive sum | 757 | 749 | -8 |
| File effective LOC | 1204 | 1200 | -4 |
| File raw cyclomatic sum | 513 | 514 | +1 entry compensation |
| File callables | 28 | 29 | +1 |
| Normalized cyclomatic sum | 485 | 485 | 0 |
| Actual whole-file branch outcomes | 264 | 260 | -4 |
| Global errors / warnings / findings | 1924 / 2740 / 4664 | 1924 / 2740 / 4664 | 0 |
| Tail cognitive >300 / >200 / >100 | 5 / 17 / 55 | 5 / 17 / 55 | 0 |

New selector cognitive2/cyclomatic3/LOC6/nesting1/params1 has no violations.
Physical duplicated if sites4→2. Aggregated cognitive and LOC decrease while the
new selector remains small; complexity is not transferred to a mega-helper.
Raw cyclomatic aggregate does NOT decrease: the +1 is compensated by its added
callable entry; normalized sum is unchanged. This limitation is explicitly
disclosed and does not waive the actual native complexity ratchet.

Other27callables retain exact cognitive/cyclomatic/LOC/nesting/params/fingerprint/
violations. All1672other runtime bytes and all their report metrics are identical.
The sole runtime diff is frozen analytics49b9; specf899 remains exact and all11
old specifications remain unchanged. Main concurrent diff9f85/status0d54,
baseline38e6, thresholds/exclusions and actual merge-base55a remain unchanged.
Ratchet raw JSON confirms base_refmain, baseline_commit55a and findings[].

Coverage raw audits verify every actual statement and branch outcome covered,
zero missing/partial branches and no skips/synthetic credit. Original analytics
634/264→candidate632/260; unchanged driver49/16 and orphan27/10 full100.
The private report-only coverage filter changes no repository scope or100 policy.

Exact commands and raw evidence are under
`~/.cache/gaia-campaign/20261011-r28-final/`: focus/union commands, XML/native exits,
coverage JSON, before/after whole reports, metrics-audit, Ruff/format, actual
ratchet log/raw audit, source/spec manifests and custody JSON/logs/exits.
Inherited PYTHON/PYTEST/COVERAGE/QUALITY_PYTHON/NODE/CI overrides were absent;
per-union COVERAGE_FILE and --cov-config are explicitly recorded in commands.
Existing ignored dependency links were reused; no installation/build/cleanup.

## Residual Risks and Next Step

Original acceptance reported to Coordinator and token released. Preserve failed auditor SHA
`9aa43d02b04f832592897640972d1c1d85a0b5a97d8f05fb1ed5db78a38721b3`,
`audit-original.log`/exit1, actual native `union-original.exit`0 and all raw inputs.
Schema-only correction and separately admitted candidate verification are
complete. FINAL token released; report frozen for Coordinator exact-path review
and publication. Coordinator retains responsibility for Graphify, integration,
per-publication ratchet and integrated global-check provenance.

This is a bounded real cognitive/duplication improvement, not elimination of the
remaining250-class hotspot: fuel remains240 cognitive and344LOC; global extreme
tail/error/warning counts are unchanged. Broad backend/frontend/worker suites,
frontend clean build and stack E2E were not run here and remain uncertified.
Known historical globalFAIL30 is not repaired, reattributed or suppressed.
The original global campaign remains ACTIVE / INCOMPLETE.
