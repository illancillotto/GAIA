# R88 — Private proxy redirect correction preparation and review

## Scope and authorization

User explicitly authorizes preparation/review of sole private proxy correction,
without new E2E. New immutable external candidate; original environment-v3 proxy,
R86sources/run/seals/failure DB untouched. No GAIA runtime/test/fixture/auth/quota/
main/baseline/threshold/exclusion/coverage-policy changes. Original native case0
SKIP/case1NOT_RUN and partial spec92fae5dc remain NOT_ADMITTED.

Snapshot integration HEAD68be307aaf2f30664975b7af57ac78dd279bfef8,
branch refactor/complexity-campaign-20261008,
main/merge-basea51a48dc4caefbdd1aea82fe4d749054b9465970, BASE_REF=main.
No new branch/worktree, native launcher or execution authorization.
Ownership registry assigned nonoverlapping external preparation/review paths.

## Implementation and behavioral contracts

Candidate changes exactly two original sites: import pure redirect helper;
response.writeHead header argument goes through helper. Reverse substitution
recovers exact immutable original proxy. Routing/prefix strip/upstream ports/
method/Host/forwarded headers/request pipe/status/response pipe/error502/abort/
listen loopback/SIGTERM close code unchanged.

Helper accepts only original /api/ backend requests, numeric301/302/303/307/308,
own single string Location matching exactly one raw case-insensitive header.
Root-relative single-slash or parsed-origin http://127.0.0.1:39081 without
credentials; raw target path must equal stripped raw request path with exactly
one slash added/removed. Insert /api without URL reserialization; preserve raw
authority/encoding/query/hash and other header identities, original object unmutated.

Unsupported origins/ports/HTTPS/localhost/network-path/relative/credentials,
normalized dot paths/control/backslash/bad percent, duplicate/malformed headers,
already-prefixed/unrelated targets, frontend/nonredirect pass through unchanged.
Parsed URL-origin equality can accept WHATWG-equivalent numeric IPv4 spellings,
retaining original raw spelling; not a literal-authority-equality claim.

Repository nginx rule is broader, rewriting any matched absolute HTTP(S) backend
Location. Candidate deliberately narrows to fixed public-origin slash redirects
and adds root-relative support/refusal safeguards. This restores the observed
district routing contract, not universal nginx parity or redirect sanitization.

## Tests and honest coverage

11Node unit contracts PASS,0FAIL/skip. Pure helper and actual candidate source
through VM module with fake HTTP/process; no sockets/listeners/browser/DB/native
stack. Tests verify positive/negative redirects, raw suffix preservation/header
identities and original handler route/body/error/abort/SIGTERM wiring.

Instrumentation iteration1 exit0/tests11PASS but zero runtime coverage rows:
empty all-files100 explicitly REJECTED, log/interpretation preserved. Distinct
iteration2 same sources/tests, explicit helper AND candidate100line/V8branch/
function each, thresholds100/exit0 and raw V8 retained. Experimental VM warning
preserved. Combined V8-instance evidence, not per-instance full path coverage.
Separate statement counter unavailable and NOT declared100; coverage policy
unchanged and no runtime admission gate claimed satisfied.

## Independent review

SOURCE_CONTRACT_ACCEPTED / NO_NATIVE_ADMISSION,70/70source/hash/provenance/
instrumentation checks, no checker error. Existing unit suite not repeated by
reviewer. Pure in-memory countertest candidate PASS; three significant mutants
rejected via AssertionError: baseline identity mapper, wrong-origin acceptance,
duplicate-Location acceptance. No socket/app import/test stack/server/DB launch.

Preparation17manifest entries/seal and review26file seal verified by Coordinator.
Original proxy4a4da2cf/main concurrency/spec/node/nginx pins exact. Both agents
stopped. No claimed actual SKIP cause, native readiness, streaming/backpressure,
HTTP parser/network timing/browser redirect/E2E assertion proof or deployment.
Readiness/test workflow and driver provenance remain separate unchanged scopes.

## Durable evidence

Root /media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r88-private-proxy-redirect/.
- preparation/proxy.candidate.mjsSHAe8c2dc9311a6f1b1e42eab9b11dc439404005c8144f7504f92ce493ff9a9fcb6.
- preparation/api-redirect-location.mjsSHA35e47982c708ee1939a90cb03e9b4855b2a7bc1b7beeeb149bcb21ff0925cab2.
- preparation/MANIFEST.jsonSHA4be17b9a523bb6631aea8e1ded1ad5a31d7f48487c597a09015cef6183596e35.
- preparation/SHA256SUMSSHA8e5e5ba4ae0bd2ea02d7c274682322025ad4205279bab3ebee55a378444d7baf.
- review/INDEPENDENT_REVIEW.mdSHA036c82a570c17b76a83e1fd7e0a6bb016a4f333958c41832eb0ae7eefa02f39f.
- review/REVIEW_SHA256SUMSSHAc53403c16fcc197b838fc5bfe20e4ee5857c3eb454004bd33efda5885d6ee443.
- pre-publication-docs/ and pre-disposition-docs/ freeze mutable registry/progress.

## Classification and stop

External source contract corrected and characterized; no application complexity
reduction claimed or finding eliminated. GAIA runtime metrics unchanged, no new
ratchet/check/full-suite run. Last R85actual-mainPASS0 historical, not a fresh gate.
No candidate/native admission or global campaign completion. Stop at preparation/
review checkpoint as authorized. Any subsequent native check requires separate
decision, new identity/pins/paths/review and original isolation/auth/timeout gates;
do not modify or reuse R86run. No automatic E2E/retry or readiness/driver repair.

## Graphify publication limit

After reviewers stopped and fresh heavy-slot guard was quiet, dedicated
make graphify-platform-docs ran once. Session44261terminal exit0 but HTTP429
usage_limit_reached caused semantic chunk1/1failed and partial-results warning.
Classification PARTIAL, never PASS from exit0. Cached graph995nodes1287edges/
161communities does not prove new R88semantic indexing. Log preserved in
publication/graphify.log. No retry/model fallback, baseline/policy change or
graphify-out commit. Source/runtime files in repository unchanged, no code-graph
refresh required. Final quota note added after freeze and remains unindexed.
