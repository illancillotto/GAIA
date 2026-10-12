# R69 — reviewer configuration diagnosis and residual E2E prerequisites

## Snapshot and immutable prior checkpoint

Dedicated HEAD `990f645c84bf3d030b1d69e75412b5e3762d9d8d`, branch
`refactor/complexity-campaign-20261008`; main/base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Previous goal turn is progress:
original125Ruolo test identities, input custody and unsupported-reviewer
checkpoint were recorded. No new runtime refactoring; source/test/migration,
baseline/threshold/exclusions/coverage/auth/quota and main remain unchanged.
Prior PROGRESS/registry archived before mutable updates. Existing R69 preflight
report and41record handoff remain historical; new receipts do not rewrite them.

## V2 failure and demonstrated cause

Global config observed model=gpt-6.1-sol; V2 attempted one separate inherited-
default read-only review, no model/config override. Process session55111 is
terminalexit1. Actual startup header selectedgpt-5.4 and received the same503
unsupported-plan error as V1. Both raw process attempts preserved, no accepted
review and no pytest/privateDB/container. CLI internal transport reconnections
are not represented as accepted reviews or application test retries.

Read-only diagnosis identifies project-local `.codex/config.toml` model=gpt-5.4,
contrasting with global model=gpt-6.1-sol. These files were not modified by
Coordinator. The global-only inference of a changed effective default was
wrong; no earlier config capture establishes that any external change occurred
during the turn. The earlier external-change claim is withdrawn. Original V2
prompt/config observation retained as evidence of this mistake, not provenance
of an actual effective model switch.

Pending user decision remains: authorize the specifically named read-only
reviewer model without editing config, or retain R69 without native execution.
No third automatic attempt or workaround by moving cwd. No application failure
or coverage conclusion is inferred from reviewer infrastructure failure.

## Seven E2E skip prerequisites, read-only inventory

Original V4 terminal audit and source hashes are bound in external
`E2E_SKIP_PREREQUISITES.json`. All seven exact identities/annotations inspected
against unchanged HEAD/main source. No skipped test is executed or markedPASS.

| Cases | Source | Actual prerequisite / limit |
| ---: | --- | --- |
| 1 | catasto-anagrafica.spec.ts:14 | Unconditional skip for removed single-search feature; test body has no assertions. Re-enable alone cannot certify behavior; requires separate test-retirement/consolidation decision, not restoring a feature. |
| 2 | catasto-drilldown.spec.ts:14 and52 | Real distretto rows, linked parcel and valid detail surfaces in private data. No request mocks in these cases; import/seed prerequisite must not manufacture absent behavior. |
| 2 | gis-territorio.spec.ts:381 and439 | PLAYWRIGHT_GIS_TERRITORIO_ENABLED=true. Original cases mock auth, map/provider APIs and synthetic GIS responses; any future PASS proves UI smoke only, not live authentication, externalGIS or PostGIS. |
| 1 | wiki-mcp-console.spec.ts:3 | GAIA_MCP_LIVE_CONSOLE=1 and isolated synthetic gateway/user/dataset/tool history; no live provider assertion may be replaced with mock coverage. |
| 1 | wiki-mcp-preview.spec.ts:3 | GAIA_MCP_LIVE_BROWSER=1, explicit fixture/provider opt-in and loopback GAIA_MCP_SYNTHETIC_BACKEND_URL; genuine gateway/MCP/model response/provenance required. |

No opt-in activated, synthetic DB seeded, provider contacted or browser launched.
This distinguishes an obsolete empty test from environment-dependent cases and
identifies the boundary of optional mocked GIS smoke versus live-stack proof.
Historical V4 54PASS/7SKIP unchanged; all7remain unverified.

## Status and handoff

R69 remains **BLOCKED_BEFORE_NATIVE_REVIEW**; full125test file NOT_RUN. Two R68
freshly verified backend skip identities remain valid; other447R62 identities
unverified, historical449count untouched. Worker100FAIL, matcher ambiguity,
excluded R43/R51/R63 and extreme tail remain. Global objective ACTIVE/INCOMPLETE,
not globally blocked/paused/complete. No push/main merge/runtime admission.

Diff-check and source custody recorded externally. Last executed ratchet remains
R68mainPASS0; unchanged protected sources do not justify rerunning full suites
or claiming a new scanner result. Graphify docs receipt/semantic status and
new durable manifest bind this follow-up separately from prior freezes.
Evidence root remains
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r69-notice-revision-pg`.
