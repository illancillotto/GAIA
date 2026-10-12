# R38 — Settings hydration source provenance

## Decision and limits

**ADMIT_SOURCE_OWNERSHIP_ONLY — no observed conflicting live source owner.**
Current settings source is clean in every present registered worktree; R38 author
is the sole assigned runtime owner, initially ANALYZE ONLY. Admission does not
authorize runtime edits: Coordinator must grant them after original full-file
coverage and design review. R37 remains parked, STOP / NOT ADMITTED. Campaign
globally ACTIVE / INCOMPLETE; no integration checkpoint is declared green.

Authoritative ownership registry read before acting:
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R38_SETTINGS_HYDRATION_2026-10-11.md`
in the integration checkout. Only this NEW report and private provenance evidence
were written. No runtime/test/tooling/config/baseline edits or native-heavy gates.
Read-only Git used `GIT_OPTIONAL_LOCKS=0`; no reset/deletion/cleanup/commit.

## Fresh census

Owned source: `frontend/src/components/elaborazioni/settings-workspace.tsx`.
Provenance/integration HEAD: `114fbf7196382c6446a7963c34bd89e4c9795ef5`.
Main/merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Expected admitted source SHA256:
`ddb7113ba1586ffca6cb31de52f14dbba511d1f42fb9faec68dfb3ca98121a63`.
Dedicated branch: `review/complexity-r38-settings-provenance`.
Census UTC: 2026-10-11T17:11:10.361876 to 17:11:14.714911.

- 165 registered worktrees, 150 present, 15 missing/prunable directories.
- All150 present trees contain the source; all150 owned-path statuses clean.
- 114 actual sources match expected SHA;10 committed source variants observed.
- 217 local branches captured with commit/source hashes, no remote-owner claim.
- Full status, owned status, full binary diff custody, owned binary diff, HEAD,
  merge-base, last-three source commits and committed base/source diff recorded.
- Main source6641effc is its committed55a version, not dirty or campaign source.
- Integration and dedicated R38 source matchddb7113b; no copy from dirty main.

Missing15 paths remain registered and untouched; full list in census.json and
worktrees.porcelain. They are `/tmp/gaia-*` snapshots including W1/release/baseline
trees. Unavailable directories are NOT asserted terminal or clean, recreated or
pruned. Older branch names/committed source differences are not evidence of live
ownership. Latest admitted settings history: b0dd9228,3f9863fb,0861f811.

## Ownership corroboration

Direct current collaboration observation: Coordinator, R38 author/provenance/
reviewer running; R29 reviewer and R30 author/reviewer completed. R38 registry
permits one runtime owner only. Absence of R37 agents from listing is not terminal
proof; independently rehashed explicit R37 STOP/frozen receipts establish closure.
No unexplained dirty source owner or unresolved source overlap observed.
This bounded census cannot prove absence of external IDE/process/remote activity;
any renewed source edit requires reassessment rather than silent overwrite.

## R37 frozen custody

All listed members independently rehashed, zero missing/hash mismatches:

| Receipt | Members checked | Freeze SHA prefix | State |
| --- | ---: | --- | --- |
| R37 root STOP |75|ce582072|STOP / NOT ADMITTED|
| R37 static reviewer |19|383fbc50|TERMINAL_STATIC_ACCEPT_V3|
| R37 final verifier |25|5f910c87|TERMINAL_STOP_NOT_ADMITTED|
| R37 provenance |2939|e164f3a7|TERMINAL|

Final receipt has24 private evidence entries plus1 report =25 checked members;
this distinction resolves the abbreviated prior count, not a changed manifest.
Root frozen candidate source3ae8b186 matches parked integration source; source
custody is recorded separately. No frozen artifact changed/copied/imported and
no R37 gate repeated. Static acceptance does not imply native admission.

## Main custody

Main HEAD/base/source/full-status/full-binary-diff exact before/after.
Binary diff SHA256:
`9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`.
Status SHA256:
`0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`.
Concurrent main work was preserved; status is not an all-untracked-content audit.

## Evidence and handoff

Evidence root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r38-settings-hydration/provenance-evidence`.
Reproducers census.py/audit.py/finalize.py, original observations, census and
admission-audit JSON retain command/exits and exact custody/member hashes.
Report/evidence frozen in terminal-freeze.json. Native-heavy token NEVER_ACQUIRED.
Source-ownership blocker: NONE observed. Original coverage, candidate behavior,
metrics, ratchet, review and independent final acceptance remain unproven here.
No integration/publication before R37 ratchet green or explicit exclusion decision.
