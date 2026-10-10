# R19 V2 integration / R16 faithful diagnosis

## Snapshot and ownership

Authorized correction and read-only diagnosis start at integration9f62fe26,
immutable main/merge-base55a1b1d35911451e018b662c2acc450bf5994ea2.
Ownership registry precedes activation; author, independent review and R16
diagnosis use separate branches/worktrees with exclusive writable scopes.
Heavy gates serialized. No main reset, cleanup, install or concurrent work import.

## R19 V2 behavioral acceptance

One driver-mismatch responsibility: typed database inputs, temporal operator
selection and response mapper. The route retains inputs through final response,
matching original locals and preserving ORM weak-reference identity semantics.
Original collections are never overwritten by later families. Other seven
family statements and twelve other top-level functions AST-identical. Queries,
filters, ordering, canonical display, side effects, API and transactions unchanged.
Rejected V1 remains frozen/excluded; its meaningful actual-route counterprobe
still distinguishes BEFORE/AFTER. No PostgreSQL isolation certification.

| Gate | Coordinator original / V2 | Independent | Integrated root |
| --- | --- | --- | --- |
| Focused driver/lifetime |56 /56 PASS |56 PASS |Included ORM contracts |
| Nine-file ORM union |250 /250 PASS |250 PASS |250 PASS |
| Failure / error / skip |0 /0 /0 |0 /0 /0 |0 /0 /0 |
| Actual full-file analytics statements / branches |661/661+288/288 /641/641+272/272 |641/641+272/272 |641/641+272/272 |
| NEW helper statements / branches |49/49+16/16 |49/49+16/16 |49/49+16/16 |
| Orphan helper statements / branches |27/27+10/10 |27/27+10/10 |27/27+10/10 |
| Immutable55a ratchet |PASS0 |PASS0 |PASS0 after EACH publication |

Every selected full-file statement/branch counter is positive and100%; zero
missing/partial branches. Ten synthetic focused diagnostics are excluded from
all ORM coverage unions, not used to fabricate coverage. Four analytics legacy
pragma exclusions unchanged, only import-related line shift; helpers zero exclusions.

## Metrics and classification

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| anomalies_analytics cognitive |298 |239 |-59 (-19.80%) |
| anomalies_analytics cyclomatic / LOC |137 /372 |112 /320 |-25 /-52 |
| Combined cognitive |855 |829 |-26 (-3.04%) |
| Combined decisions |536 |536 |0 |
| Combined cyclomatic |568 |572 |+4 from four new callables |
| Callable LOC / file effective LOC |1355 /1298 |1390 /1352 |+35 /+54 |
| Errors / warnings |19 /12 |19 /14 |0 /+2 |
| Fresh global files / callables |1672 /20316 |1673 /20320 |+1 /+4 |
| Fresh global errors / warnings |1926 /2740 |1926 /2742 |0 /+2 |
| Fresh global findings |4666 |4668 |+2 |

**IMPROVED**: aggregate cognitive decreases without a mega-helper, decision count
unchanged. New helper warnings loadercyclomatic10 and itemparams5 declared;
all helpers below error. Not finding-count reduction. Extreme tail unchanged:
5 above300,17 above200,55 above100. Authoritative campaign start1956errors /
2758warnings /4714findings gives current -30errors(-1.53%)/-16warnings(-0.58%)/
-46findings(-0.98%). Findings are overlapping metrics, not independent problems.

Application domains initial→current error/warning: backend1035/1688→1033/1690;
frontend878/881→850/863; worker runtime35/134→35/134. Worker tests8/55 unchanged
and separate from runtime. Baseline/scope/thresholds/ignore unchanged.

## Publication and source custody

| Accepted publication | Dedicated commit | Integration commit |
| --- | --- | --- |
| R19 V2 runtime, new test and slice report |a7c75dde9ec508e537f5ecc065ba2eebd102fea6 |d43d4426 |
| Independent ACCEPT review |ce0b7c3ea3b9e23b463b7dfbf2f945386a1d8a62 |72f416a4 |
| R16 read-only diagnosis ONLY |49334bdd2497003bdee26747206f35eea677aba7 |f8a449e7 |

Each actual integration immutable55a Make ratchet PASS0/findings[]. Native logs:
`/tmp/gaia-r19-v2-{author,review}-integration-ratchet-20261010.log` and
`/tmp/gaia-r16-diagnosis-integration-ratchet-20261010.log`, with `.exit` files.
Independent protects3563 paths and all four frozen inputs, main/baseline exact.
analytics52469893/helperd290e58e/newtest4943e9cd/SLICEbaa1ef12 byte-exact.
Independent reviewdbfe4825 and diagnosis9409906e byte-exact to publication.

Evidence: Coordinator `/tmp/gaia-r19-v2-20261010/coordinator-audit.json`;
independent `/tmp/gaia-r19-v2-review-20261010/final-audit.json` plus46-artifact
frozen manifestSHA d3bbe7a471515a3acf162e8eff9a9a55f008ddfb5d60e8154df46d7cb19cd514;
root `/tmp/gaia-r19-v2-integration-20261010/` unionJUnit/coverage/raw logs/exits.
Fresh full-source report `/tmp/gaia-r19-v2-integrated-20261010.json` and `.md`.

## R16 diagnosis, not acceptance

Unchanged full-context comparator reports native exits0(original→55a),
2(candidate original metadata),2(candidate faithful Git metadata),0(local
non-authoritative control),1(negative metric12→13). All3563tracked and237retained
inputs exact. The unchanged Sincronizza callback shifts -5lines; positional
fallback ties it to Chiudi. Group87 is not87 new functions. Correcting diff
metadata alone does not resolve ambiguity. Candidate remains BLOCKED_MATCHING,
not applied or integrated; projected -1warning excluded from campaign delta.
Evidence `~/.cache/gaia-campaign/20261010-r16-matching-diagnosis/replay/`.

User subsequently authorizes a SEPARATE matcher activity after this closure.
No matcher change, identity choice, line padding, baseline repair or candidate
acceptance is included in this publication.

## Failure accounting and maintenance

Root global complexity-check remains historical FAIL30 (CLI1/Make2), exact known
backendMCP13/frontendMCP1/frontendRuolo1/workerTests15 paths. It is distinct from
the change ratchet PASS0 and is not absorbed into baseline38e6.
First root style invocation FAIL2 because system python3 lacks Ruff; retained
style.log/.exit. Allocated invocation-only recovery uses existing installed
backend/.venv/bin/python via QUALITY_PYTHON: PASS0. No install/config/source fix
or erased failure. Precommit documentation hook skips automatic update without
TTY; explicit domain progress and docs structure changes supplied separately.
Earlier ancillary wrong-cwd hash/tool-handle lookups are recorded in SLICE.

Dedicated Operazioni Graphify force-pruning patch and code target PASS0:
534nodes1533edges26communities. Domain docs target PASS0/chunk1/1done, no semantic
failure:52nodes67edges7communities,5674input2304output tokens/$0.0060estimated.
Graph ignored, not complexity proof. Platform docs target has separate closure
evidence: PASS0/chunk1/1done/no semantic failure,680nodes918edges107communities,
12752input2095output tokens/$0.0085estimated. Final postcommit
immutable55a gate native evidence is reserved at
`/tmp/gaia-r19-v2-integration-20261010/postcommit-ratchet.log` and `.exit`;
no status inferred from prior integration gates.
Existing GIS focused10/GIS5/full54PASS7existingSKIP remains attributed, not rerun.
Full global final suites and PostgreSQL verification not performed here.
Global campaign **ACTIVE / INCOMPLETE**; no next runtime family authorized.
