# Capacitas — job-monitor lifecycle contract

## Scope and status

R11 is local behavior-preserving quality work in
frontend/src/components/elaborazioni/capacitas-workspace.tsx.
Reviewed source55827bde/a2327063 is independently certified and integrated
01a9ada4; report-only certificate5981be8d integrated81be6d41. Both post-pick
main55a ratchets PASS0. INTEGRATION_R11 records accepted source/certificate
custody and closure gates. Campaign ACTIVE/INCOMPLETE; no feature or main merge.

Four existing loaders retain names, silent=false defaults and API contracts.
Private typed monitor config binds family, list, application callback and four
setter ports. Shared refresh owns token/expiry/loading/auth/error/finally;
family callbacks own snapshots. Domain selectors deduplicate status decisions.
No new hooks, contexts, reducers, exports or components.

## Exact lifecycle

1. Read stored token synchronously at dispatch. Missing token sets expiry,
   exact family error and resume message, returning before loading or API.
2. Normal requests set loadingtrue before the same list API; silent requests
   never touch loading or ordinary error. inCASS still sends limit300.
3. On response, clear expiry before reading the current prior in-flight ref.
   Apply family snapshot, then clear error only on normal success.
4. Classify authentic ApiError401/403 before Error.message/fallback. Auth failure
   follows the same expiry/error/resume sequence even when silent; normal
   finally releases loading, including auth early return.
5. Non-auth normal rejection displays Error.message or exact family fallback;
   non-auth silent rejection neither reads message nor changes prior error.
   Family application exceptions remain inside the original try/catch.

Terminal statuses: succeeded/completed_with_errors/failed. In-flight statuses:
pending/processing/queued_resume. Filter/map/Set retains API order/ID semantics;
cancelling/cancelled/unknown are not reclassified.

| Family | Snapshot and completion ordering |
| --- | --- |
| Terreni | Only silent/nonempty prior ref finds FIRST tracked terminal in API order; modal before ref replacement, then jobs. Normal refresh never opens completion modal. |
| Particelle | Read prior ref, replace ref, set jobs, then normal tracked-terminal notice only. |
| History | Prior ref, replacement, jobs; FIRST valid terminal result, repeat original guard, stored result, then normal tracked-terminal notice. |
| inCASS | Same ref/jobs/normal-notice order as Particelle; limit300 and visible-job presentation unchanged. |

History retains stored reports through active/invalid/empty lists; existing valid
first-job presentation can override stored data. Terreni modal follows current
job when present, otherwise snapshot. No guard removal or result normalization.

## Polling and concurrency

Original usePolling callbacks/options, two effect bodies/dependencies/order,
visibility/cleanup and command awaits are unchanged. Three families keep15s;
inCASS keeps20s through100jobs and45s above100. Poll-to-poll single-flight does
not prevent manual overlap. Tokens are captured at dispatch, refs at resolution.
No generation, abort, latest-wins or race fix: late responses can replace newer
rows or clear newer expiry while prior error/guidance remains visible; later auth
can freeze polling. Dispatch-local callbacks expose no identity and capture only
original render closure/stable setters/refs/imported values.

## Validation and accounting

58new original public-UI cases:8auth,2reversed Terreni order,48manual/polling
outcome/order timelines. Real usePolling, deferred API boundaries and separate
intermediate DOM observations protect rows/loading/errors/token/result/modal and
next polling eligibility. All18prior specs frozen. Author/source review396/19
zero skip, both complete files100%, lint0/type/diff/mainratchet0/protected/Graphify
PASS. Independent8248source-order/microtick comparisons are supplementary only.

Principal455→391cognitive/404→360cyclomatic/2625→2527LOC; combined1022→926cognitive,
872→803decisions/3140→3131fileLOC, error22→17/warning19→16. All nested ancestry
counted, state31/effect2 unchanged. Earlier new hook warning was rejected, not
waived; one generated EOF blank explicitly removed before final actual replay.

R11 readiness/characterization/design/SLICE/REVIEW_SOURCE reports record source
proof. Distinct VERIFICATION_R11 certifies396focused/19spec and4575whole-frontend
tests/305files with no unit skips;789statements/818branches/253functions/684lines
in the entire workspace and the entire fraction policy are100%. Project and
explicit new-spec typecheck, owned lint0, smoke and clean build pass. Full lint
retains35exact historical warnings, not a clean-warning repository claim.

Native browser evidence covers24monitor cases plus2genuine logins, public actions
and real polling callbacks, using explicitly disclosed Playwright browser-clock
advancement, not wall-clock interval certification. Existing pertinent E2E4PASS;
full E2E54PASS/7historicalSKIP/0retry/flaky. Provider/PostGIS/optional GIS skips
are not passing certification. Original overlap/stale-response behavior remains.
The initial broader-scope coverage failure and startup502browser attempt are
retained in the certificate; no test/config/policy/timeout was weakened.

Global30complete finding objects equal R10: historical15runtime regressions and
15test-only divergences, none introduced by this slice. Baseline/scope/soglie
unchanged. Owned processes/containers/network/ports/credentials were cleaned up;
the ordinary Vitest generated timing-cache update is disclosed, not restored.
No fresh full-backend/worker suite or global campaign completion is certified.
