# R100 — Fuel operator ordered-name policy

## Snapshot and ownership

Integration: `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`, HEAD
`7f39510ab1ef1d4e531d8b12a4eb6b36f556cee4`. Actual main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`; BASE_REF remains main. Initial
October8 `55a1b1d` provenance is historical, not substituted for the actual base.

Registry: `docs/code-quality/MULTI_AGENT_OWNERSHIP_R100_FUEL_OPERATOR_NAMES_2026-10-15.md`.
Author isolated branch `refactor/complexity-r100-fuel-operator-names` starts from
committed integration HEAD only. Original author handle disappeared on session
recovery; closure author finished only remaining gates. Reviewer and verifier
had disjoint evidence ownership and read-only source access. All STOP.

## Admitted source and invariants

Three exact reviewed source files applied through apply_patch to integration:

| File | SHA256 |
| --- | --- |
| backend/app/modules/operazioni/routes/analytics.py | b9cac27e093f69914c28f5ae584fb89ba3a929a9beaa2ff7bc1c9a824cb2ad16 |
| backend/tests/test_operazioni_operator_km_r14.py | c5034d4f95189fad1a83cde1b84bbb983f656b3afebc20f37d997b210ccd62d1 |
| backend/tests/test_operazioni_fuel_names_r100.py | dc5e887a2e1e371d4f1a5cf14796ef68d2df86af79d9003d55dcd821ba5ab2b1 |

One responsibility only: deduplicate ordered WCOperator name construction in
orphan fuel-group consolidation and `_op_km` fallback. Preserve both eager display
expressions, repeated property reads, outside-only strip, raw username, empty
variants, exceptions, collision/query/insertion order, raw related keys, positive
GAIA-user precedence and fresh returned maps. No SQL/API/auth/DB transaction or
identity-policy changes. Expanding the two helper calls restores the entire
original module AST. All original R14 nonfixture bytes and assertions are exact.

## Metrics

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| fuel cognitive |217|192|-25 (-11.52%)|
| fuel cyclomatic |148|138|-10|
| fuel effective LOC |329|327|-2|
| fuel nesting / params |3 / 5|3 / 5|0|
| nested `_op_km` cognitive |33|18|-15|
| file cognitive sum |706|676|-30 (-4.25%)|
| file cyclomatic sum |493|484|-9|
| file effective LOC |1179|1177|-2|
| callables |29|30|+1|
| error findings |18|16|-2|
| warning findings |10|13|+3|
| all findings |28|29|+1|

New helper cognitive10/cyclomatic11/LOC6/nesting0/params1 has an explicit new
cyclomatic warning. Two `_op_km` errors become warnings. No claim that all
findings decrease. Source has five fewer unique OR nodes68→63; nested scanner
spans overlap, so scanner deltas are not independent decision removals.
Classification **IMPROVED**: genuine cohesive deduplication, fuel below200,
not resolution of its orchestration or global campaign completion.

## Characterization, tests and coverage

- Original-source focused99PASS, terminal0, before runtime edits.
- Twelve new persisted public HTTP route cases cover exact formatting/nonmatches,
  nullable/empty names, raw username, raw related keys and name collisions.
- Original genuine428PASS log/XML/coverage retained, but terminal receipt lost
  on recovery and an unrelated external Jest overlapped. Not reconstructed away.
- Distinct independent genuine428PASS,78deselected,0skip/error/failure,
  terminal0, elapsed256.963s; source hashes exact before/after.
- Full analytics627/627statements and252/252branches100%; four reported runtime
  files711statements/278branches100%. Existing four defensive excluded lines
  unchanged; no new exclusion, pragma or policy change. Synthetic tests did not
  contribute runtime coverage.
- Supplemental78PASS, terminal0; two mutation probes PASS by rejecting reversed
  variant priority and bind-once property-read regression at original assertions.
- Ruff, new-test format, backend lint, scoped metrics and diff-check terminal0.
  Full main ratchet terminal0/findings[] in author and independent verifier.

## Preserved failures and limits

External probe first failed collection without backend conftest environment;
distinct invocation used exact test defaults and isolated SQLite. Second probe
correctly caught the original access-order assertion but failed traceback-text
inspection due an overbroad shared-inspect monkeypatch. Separate sibling probe
restored inspect after factory extraction, retaining every original assertion.
Both failures remain immutable. Reviewer/verifier receipt parsers also initially
failed on JSON selection; read-only sibling corrections reran no successful gate.
Manifest JSON checksum and checksum-text-file checksum identify different objects,
not a provenance mutation. Coordinator's nonexistent-handle waits had no process
effect and are documented externally; they are not test observations.

No full application suite is inferred from focused gates. Backend skipped cases
remain unverified; global baseline ambiguity/status is separate from the change
ratchet. R43/R63 excluded candidates stay excluded. Previous R99 six test sources
and unrelated integration/main work are preserved. No commit/push/main merge.

## Integration checkpoint

Exact source pins admitted following source review ACCEPT and independent
verification PASS. Integration runtime-gate runner initially refused launch on
external TypeScript/Jest processes; no tests were launched or retried. The
serialized slot observer confirmed live argv until they terminated, then fresh
integration lint-backend, full main ratchet, global report, graph query, Operazioni
code graph and diff-check each completed terminal0. Ratchet findings[] and
authoritative basea51a48dc confirmed. Code graph541nodes/1549edges/30communities.
All source pins and protected configuration hashes remained exact before/after
every gate. No baseline, thresholds, exceptions, coverage policy, tooling or
Makefile changed. Dedicated domain/platform docs graph refresh is also terminal0,
both chunk1/1done without semantic failure warnings. Domain graph133nodes/
167edges/13communities (841input/2415output tokens, estimated$0.0042);
platform1096nodes/1464edges/171communities (6452input/3315output tokens,
estimated$0.0079). These are graph-tool estimates, not complexity evidence.

Initial Graphify base-URL patch target failed import because the shared venv's
generic interpreter resolves to Python3.14 while its existing packages/config
are Python3.12. Receipt terminal2 is preserved. A private external entry point
uses the existing Python3.12 interpreter and canonical installed packages, with
execution-local PATH/PYTHONPATH only: no dependency install, shared-venv repair,
runtime or Makefile change. Dedicated patch target confirms already patched.
Both docs targets explicitly use gpt-reserve, overriding gpt-5.5 in local env.
An external Jest started after the domain graph's quiet preflight; that overlap
is retained, not claimed exclusive. The next platform launch was refused, then
waited for fresh quiet argv and ran once. No successful graph/test gate repeated.
Final receipt-only annotations are not claimed semantically indexed afterward.

## Current global measurement, not final campaign certification

Fresh full scan1681files/20361callables,1918errors/2739warnings/4657findings;
zero parse/exception errors. Compared with the immediately prior October14 scan:
errors-2, warnings+3, findings+1, callables+1. Every file and callable record
outside analytics.py is exactly equal, establishing this bounded slice delta.
Tail cognitive>300 remains3, >200 falls16→15, >100 remains55. Complete current
top30 retained in `integration-evidence/global-delta.json`.

Compared with initial October8 audit: raw errors1956→1918 (-38/-1.94%),
warnings2758→2739 (-19/-0.69%), findings4714→4657 (-57/-1.21%). Scope and
intervening/concurrent history differ; these are not exclusively campaign gains.
Strategic targets and extreme-tail elimination remain unmet. No full application
suite or global complexity-check is claimed for this bounded slice.

## Durable evidence and next step

Root `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r100-fuel-operator-names/`.

| Receipt | SHA256 of manifest |
| --- | --- |
| closure-evidence/MANIFEST.json,94members | fcb46c95d8ab69a21666b1a1b627dd57da0be10db6331450b9b7a1ff160531a3 |
| review/FINAL_REVIEW.sha256 | d8369efbd139e46d526e5aeab3ea85a57a6b0fff3471ad391585317cd064429e |
| verification/MANIFEST.json,43members/5parents | 897cf749869679d375285e2dbcc7d3ecbaa96f854d5f415205381a134cdc113f |

Independent handoff `verification/HANDOFF.md`; runtime integration evidence
`integration-evidence/`. Freeze-before-update archives preserved. Final checkpoint
handoff `integration-evidence/HANDOFF.md`, content manifest `MANIFEST.json` and
its `MANIFEST.sha256` checksum cover integration records, source/docs snapshots,
parent seals and preserved R99 inputs. All new source remains uncommitted on the
dedicated branch; no next hotspot started. Goal ACTIVE/INCOMPLETE.
