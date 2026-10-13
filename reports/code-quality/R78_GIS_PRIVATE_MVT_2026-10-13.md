# R78 — Faithful private MVT fixture: original GIS FAIL preserved

Current status: original execution completed on 2026-10-13 with **1 PASS /
1 FAIL / 0 SKIP**, no retry. Publication checkpoint and goal **BLOCKED** after
fresh three-turn external-heavy-job audit. The terminal section supersedes historical
pending/blocked entries, which remain preserved as preparation history.

## Authorization and snapshot

User chose **Fixture MVT privata, test identico**. Only the missing vector data
prerequisite is in scope, not runtime, original spec, route mocks, assertions,
timeouts, test order, authentication, quota, coverage policy or baseline.

Integration `GAIA-campaign-20261008-integration`, dedicated branch
`refactor/complexity-campaign-20261008`, HEAD unchanged
`e458dcdeaac64ff8d8740524900cc3a0f576b411`; actualmain/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Historical55a1b1d remains provenance.
Main concurrent config/untracked Bonifica test untouched and excluded. No branch,
push, main merge or commit in this preparation checkpoint.

## Fixture and isolation design — initial checkpoint

Private `mvt_fixture.mjs` uses the already-installed MapLibre GeoJSONVT/vt-pbf
encoder and a separate vector-tile/PbfReader decoder, with no new dependency,
Docker/PostGIS container, database, credentials or provider call. Exact original
triangle coordinates and UUID are retained. No relocated/additional polygon,
duplicate identity, forced hit, private UI callback or PNG-as-vector replacement.

The proxy is designed to serve actual `/tiles/cat_particelle_current/{z}/{x}/{y}`
MVT, source-layer `cat_particelle_current`, version2/extent4096; other requests
stream to the unchanged read-only Next build. Planned ports39082/39083 inside
one owned cgroup and loopback-only network/PID namespace, read-only root except
native output and private0700tmp. Guard helpers match R76 byte-exact. Adapted
runner captures additional five MVT-package file sets and fails closed on
recognized competing heavy processes; this is not a global scheduler lock.

Self-check design covers eleven sampled zooms10..20, decode/identity/closed-ring,
all reconstructed vertices within original triangle plus1MVTpixel quantization,
interior parcel point, negative municipal point and empty remote tile. These
checks are **not yet successfully executed**. Original parcel/municipality bboxes
remain disjoint; supplying faithful tiles does not guarantee selection following
the original municipal focus. No PASS prediction or full live GIS claim.

## Preserved preparation results — initial checkpoint

| Phase | Result | Consequence |
| --- | --- | --- |
| Static V1 | STOP: null-prototype decoder properties versus strict equality | Frozen initial source; property spread corrected privately |
| Static V2 | 35checks/0failed | Accepted statically, not executable certification |
| Static V3 | 15checks/0failed, vertex checks added | Accepted statically, not executable certification |
| Original preparation capture | Exit0 | Protected2732input set/build/dependency/browser receipt exact at capture |
| First executable fixture check | Exit1 before body: installed6.1.1 has named GeoJSONVT, not default export | No tiles/proxy/browser; log/source retained, static review limitation acknowledged |
| Static V4 | 9checks/0failed; actual API import/class corrected | Accepted statically; sourceSHA74014e413edf669b12e0a439a1f62a94af64938d9b367d64a0f2fe22e1b6ce2b |
| Distinct V4 capture attempt | GuardSTOP/exit1 before capture | Unrelated TBOWvitest restarted; no corrected fixture check |
| Finite process waiter | 600s, exit3/free slot unavailable | No native/test/build/scanner launch, no unrelated process terminated |

V4 capture/self-check and reviewed execution readiness remain pending. Original
specSHA`ff632044932bb386848c6dc1b9449358cb1686adafc7c2039180538d5000b043`
unchanged. R76 original1PASS/1FAIL/0SKIP and all historical receipts immutable.
There is no new E2EPASS, resolvedskip, coverage or complexity credit. Later
original sheet/print/QGIS steps remain NOT_VERIFIED.

## Gates and admission

`git diff --check`: PASS. Current scanner/ratchet/Graphify gates **NOT_RUN** due
to competing heavy processes, not PASS inferred from R77. Last actual-main
ratchetPASS0 belongs to R77 only. No baseline/scope/threshold/ignore/exclusion/
coverage change. Runtime **NO_CHANGE**, private fixture **PARZIALE**, not admitted
as verified. Documentation working changes remain uncommitted until checkpoint
publication gates; no generated/evidence/cache/build/DB/dependency files staged.

At11:35:29+02:00 unrelated Jest processes2768297,2776871,2787790 remain active.
Both private waiters terminated, independent reviewer completed/stopped; no
owned native server/browser/DB/container exists. Goal ACTIVE/INCOMPLETE, not
COMPLETE or implicitly PAUSED. Latest global metrics not newly measured.
Remaining backend199unverified skips, five other E2Eprerequisites, worker100FAIL,
matcher ambiguity, excluded candidates and extreme hotspots remain separate.

## Durable handoff and next steps

External root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r78-gis-private-mvt`.
Frozen mutable PROGRESS/registry/parent handoff/spec; private scripts, V1/V3
failures, V4guardSTOP, review versions and waiter observations preserved.
`review/STATIC_SHA256SUMS_V4` rechecked exact. `SESSION_CHECKPOINT.md` and
`HANDOFF_MANIFEST.json` bind this partial checkpoint; no historical receipt edited.

1. Fresh status/merge-base and full process inventory; wait for a free heavy slot.
2. Distinct log names for corrected capture/self-check; never overwrite failures.
3. Independent preparation review on successful receipts, recapture source hash
   custody if any private preparator changes; original spec remains identical.
4. One separate original full-file execution, workers1/retries0/maxfail1, original
   timeouts; preserve FAIL and stop without automatic repair or retry.
5. Terminal review, relevant gates/Graphify, selective documentary checkpoint
   commit only; no unrelated runtime hotspot or global completion claim.

## Continuation 11:49 — verified wait, not a new test attempt

Prior sealed50record handoff rehashed exact; current documentary files archived
before update. Fresh initial blockingJest2776871 observed live with kernel
starttime8533843; it subsequently disappeared and different liveJest2820483
occupied the slot. Owned resume-1 waiter session62442 finished its600s bound,
exit3/no free slot. Original process was not restarted or killed by this work.
At11:49:27+02:00 replacementJest still live, elapsed9m52s. No corrected capture,
self-check, scanner/ratchet/Graphify or browser launch. Fresh diffcheckPASS and
original specSHA exact; no runtime/config diff. Existing failures unchanged.

User asked for an optional quiet execution window; pending answer is not
permission to kill other jobs or weaken one-heavy-process rule. Global goal
remains ACTIVE/INCOMPLETE. Current handoff supplement in external
`continuation-20261013/` binds bounded waiter evidence; original sealed manifest
and receipts remain immutable. No checkpoint commit until pending gates.

## Third-turn blocked audit 11:50

Same competing-heavy-work condition confirmed across three consecutive goal
turns, including two finite waiters and fresh live/proc observation of2820483.
Corrected capture/self-check/native outputs still absent. Preparation/static
review cannot replace execution; no meaningful further change without a free
slot. Goal marked **BLOCKED**, not PAUSED or COMPLETE. No new test, repair,
baseline change or commit. External `blocked-audit-20261013/` stores live process
and decision evidence; resume only after external readiness change, with fresh
process/status/custody checks. Historical ACTIVE entries remain historical.

## Resumed goal — V5 executable preparation accepted, native not run

User explicitly resumed goal ACTIVE; blocked audit restarts fresh.12:01 process
inventory free. Fresh V4captureexit0, private self-checkexit1 after one valid
populatedtile: installed aggregateVectorTile drops emptylayers, so original
private assertion incorrectly demanded that key. Failure/partialtile/source/
capture retained; no native/browser/server. Earlier staticreview was not proof
of executability and missed that decoder behavior.

V5 leaves encoder/index/triangle/UUID/serving/spec unchanged. RawVectorTileLayer
envelope parser verifies exactlyone correctlayer/version/extent/sourcecount;
aggregatekeys are empty iff count0. This verifies valid emptyPBF, not permissive
acceptance. Static15checks accepted. Three V5capture attempts refused before
capture due externaljobs; fourth freshguard/capture and selfCheck bothexit0.

| Fresh V5 evidence | Result | Scope limit |
| --- | --- | --- |
| Original protected inputs | 2732exact, same original spec/build/browser/dependency receipt | Custody, not fresh original GISPASS |
| MVT dependencies |108files captured/rechecked | Existing installed packages, no dependency change |
| Self-check |11zooms10..20 PASS, exactUUID/layer/version2/extent4096 | Eleven sampled tiles, not full tile plane |
| Vertex reconstruction |Max outside0.5035932624545847MVTpixel, all below1pixel | Quantized/clipped originaltriangle; no geometry relocation |
| Municipal negative samples |0hits, original geometrydisjoint | Not native camera state or sufficient selection correction |
| Empty tile |Valid31bytePBF, SHA b73c6638c3e7ce55e4932dfb219b0ee202c836f7d158d830274bfd3b5b6fa26c | Independent decoder/parser validation only |
| Independent preparation review |1970checks PASS, accepted original one-time launch after freshfree slot | No reviewerNode/browser/provider execution; nativeNOT_RUN |

PREPARATION_MANIFEST_V5 SHA
`fe9b50c9031a008c640825dc330b32cf97d90e9c25422cc3b5fb4cc809449e03`,23records
rehashed exact. Independent `review/EXECUTION_PREPARATION_V5_REVIEW.md`, Python
PBFdecoder/geometry checks, consumed-byte freeze and checksum bind results.
Current fixtureSHA671a34ac49b3332802a030e7c12af8fc4c330493d1957070b65f5375d39be2bb,
runnerSHA8aeeee63cd2c42b680ce7d23e93229431c3d00e066d3ff97c11e794ff4cfd273.

After another observedfree slot, fresh original-launch guard refused restarted
GaTePlaywright/TypeScript and Cinearchivepytest before native directory/cgroup/
namespace/server/browser creation. execute-v5.exit1 is **guardSTOP**, not an
originalGISfailure/retry. Subsequent boundedwait60770endedexit3/no free slot.
Corrected fixture now genuinely verified; original twoGIScases still NOT_RUN
for R78. R76retained1PASS/1FAIL/0SKIP unchanged; no new originalPASS/resolvedskip,
coverage/complexity credit. No runtime/spec/assertion/timeout/baseline changes.

Fresh diffcheckPASS. Actual-main ratchet/Graphify stillNOT_RUN while external
heavyjobs active; no commit/newbranch/push/mainmerge. Goal ACTIVE/INCOMPLETE,
not oldBLOCKED or COMPLETE. External `RESUMED_CHECKPOINT.md`/new manifest bind
currentstate; earlier sealed/checkpoint/blockedreceipts immutable. Next quietslot:
freshcustody/guard -> onceoriginalfullfile -> terminalreview -> gates/Graphify/
selective documentarycommit. No speculative runtime refactor before verification.

## Resumed third-turn audit — current goal BLOCKED

At12:58:47 freshliveTBOWVitest3117149/3118943 confirms the same externalheavy
condition across three consecutive resumedturns. Secondturnwaiter90698completed
600s exit3; currentnative directory and secondlaunchlog remain absent. Preparation
and1970review are complete but cannot replace originaltestexecution/gates. No
meaningful furtherauthorized progress without externalfree slot. GoalBLOCKED,
not COMPLETE/PAUSED; oldblockedthreshold was not reused. Currentaudit/live/proc
receipt in external `resumed-blocked-audit/`. No native/test/scanner/Graphify
launch, commit or baselinepolicychange; all historicalfailures/receipts retained.

## Authorized restoration and terminal original execution

User explicitly authorized restoring the checkout from Trash. Same-filesystem
no-clobber move preserved directory device/inode 66306:2634173, expected branch,
HEAD and all three documentary changes. Original Trash metadata and historical
provenance receipts preserved. Git recognizes the original worktree without
pruning or repair. Main status and concurrent file hashes unchanged.

Restoration custody: 2732 protected files, 253 NFT closure, 8 browser executables,
1405 build files, 108 MVT dependencies and 5 preparator modules exact; all 23
preparation and 6 provenance-manifest entries also exact. Receipt and checksums
in external `checkout-provenance-20261013/RESTORE_AUTHORIZED_RECEIPT.md` and
`RESTORE_SHA256SUMS`. A checksum command initially used the wrong manifest working
directory; correct reviewer-directory verification passed all entries. Both
command outputs preserved, no input repaired or historical checksum changed.

After a fresh free-heavy-slot check, the accepted V5 runner executed **once**:

```text
python3 -B -X pycache_prefix=<external-root>/cold-bytecode <external-root>/run_gis.py execute
```

Original spec, config, route mocks, assertions, order and timeouts unchanged.
Collection exit 0; two original chromium cases, workers 1, retries 0,
max-failures 1. Execution exit 1, native supervisor exit 1, outer runner exit 1.

| Original case | Result | Verified limit |
| --- | --- | --- |
| GIS console and toolbar tools fit desktop and mobile viewports | PASS, 3679 ms | Original mocked/isolation scenario only |
| territorio smokes map consultation, sheets, measurements, print and QGIS | FAIL, 29651 ms | Detail-panel close button absent at spec line 508 after original 20000 ms expectation |

Playwright stats: 1 expected, 1 unexpected, 0 skipped, 0 flaky. Global reporter
error states max-failure stopping, not a third test case. The failure reproduces
the same assertion as historical R76, but is a distinct genuine MVT run. Later
sheet/measurement/print/QGIS assertions remain unverified; no full live GIS,
authentication, provider, export, coverage or complexity improvement claim.

Proxy request log records 34 MVT HTTP 200 responses: 28 empty and 6 populated
tiles. Fixture remains the exact original triangle/UUID and actual source-layer.
Supplying faithful tiles did not resolve the original workflow; camera/order
causality needs the terminal evidence review, not a speculative runtime fix.

Isolation receipts show separate network namespace, only loopback, repo/build
read-only; backend/database NOT_STARTED and providers unreachable. Before/after
captured inputs equal; cgroup terminal receipt populated 0, pids empty. Proxy
and Next handles terminated; no retry or cleanup of unrelated processes.

Evidence: `execute-v5-distinct-2.log/.exit`, `native/` JSON reports, argv, isolation,
containment, custody, screenshots, trace, video and tile-request log. Mutable
documents frozen before update under `terminal-checkpoint-20261013/`. Independent
terminal review and current ratchet/Graphify publication gates pending; historical
R77 PASS not reused. No runtime/test change, baseline inflation or new refactor.

Classification: runtime **NO_CHANGE**; private fixture characterized but **not
admitted as a successful GIS resolution**. Goal ACTIVE/INCOMPLETE. No automatic
repair/retry: a separate authorized decision is needed for the next GIS action.

## Independent terminal review and documentary admission checkpoint

`review/TERMINAL_V5_REVIEW.md` accepts the terminal evidence **with original
native failure**, not GIS PASS. 2941 checks PASS, 487 consumed files frozen
byte-exact; `TERMINAL_V5_SHA256SUMS` independently rechecked exit 0. Reviewer
launched no test, scanner, browser, runtime import, database or provider.

The failed-case browser trace contains 22 MVT responses, all HTTP 200: six
populated and sixteen empty. Independently decoded raw response bodies match
proxy hashes, sizes, source-layer, version, extent and original UUID geometry.
Twelve further proxy requests lack a retained first-case network trace and
are not claimed independently body-verified. No popup API request appears in
the failed-case trace. Trace archive integrity passes (297 members), SHA256
`0dfd10d27604ebb1ef050c547076a6eab781ad089fc6d7ae3b6f6e4ae9592398`.

Missing-vector data was materially addressed; camera/focus/hit-test root cause
is not proven. Retained unrelated HTTP 404 and external-image network errors
are not labeled PASS or assigned unproven causality. Later assertions remain
NOT_VERIFIED. Native sources, original spec and historical failures immutable.

Current `git diff --check`: PASS. Intended gate remains exactly
`make complexity-ratchet BASE_REF=main`, actual merge-base `a51a48dc...`.
**NOT_RUN**: the first readiness waiter found a free slot after 40 seconds,
but external TypeScript/pytest jobs restarted before the subsequent preflight.
A separate 242-second bounded waiter ended while external Jest jobs remained
live. No scanner invocation or ratchet log/exit was created. This is not a
ratchet failure or a PASS inherited from an earlier checkpoint. Graphify
platform-docs also NOT_RUN under the same single-heavy-job rule despite local
API configuration; no code-graph update needed for unchanged R78 runtime.

Review and all owned native/waiter handles are terminal. Three documentary
files remain uncommitted; no generated artifact, cache, build, dependency, DB
or graph output staged. Pending publication gates prevent checkpoint commit,
not failure preservation. Main's concurrent files remain unchanged and excluded.
Global baseline ambiguity is separate and has not been remeasured or repaired.
No current global metric/coverage improvement or resolved-skip claim.

User decision requested for one distinct next action: bounded read-only
camera/hit diagnosis, separately authorized refocus in the test workflow with
all assertions/timeouts preserved, or keep GIS excluded. No answer is assumed.
Durable handoff: external `terminal-checkpoint-20261013/CHECKPOINT.md` and
`HANDOFF_MANIFEST.json`; pre-update documents and old seals retained.
Goal ACTIVE/INCOMPLETE: this turn progressed from native NOT_RUN to reviewed
terminal evidence. Do not reuse historical blocked-turn counts or mark COMPLETE.

## Latest publication-block audit

The fresh resumed audit now reaches three consecutive goal turns with the
same genuine external-heavy-job blocker: the terminal native/report turn's
bounded gate waiter, continuation 1's verified 182-second wait, continuation
2's fresh PID/start-tick checks. No previous blocked run is counted. Current
Jest identities 3397726/start9469723 and 3425519/start9500329 are confirmed live.

No further safe publication action is available without external readiness;
the user's separate GIS choice remains unanswered, not implicit authorization.
Goal **BLOCKED**, not COMPLETE or an unsolicited PAUSED. Ratchet and Graphify
remain NOT_RUN; no inherited gate PASS, retry, repair, baseline update or commit.
All owned waiters and native/reviewer handles terminal. Current status/branch/
HEAD/base unchanged; main concurrent work excluded. Fresh diff-check PASS.

New durable supplement `gate-continuation-2/BLOCKED_CHECKPOINT.md` and
`BLOCKED_MANIFEST.json` contain live preflight, frozen pre-update documents and
current documentary hashes. Earlier seals remain historical and unmodified;
their mutable-document bytes are preserved in the new freeze, not rewritten.
Resume only after a current-state readiness/decision change. Do not repeat
native GIS automatically or declare the full campaign achieved.
