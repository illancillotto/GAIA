# R61 additional independent build verification — 2026-10-12

Disposition: **PASS_SOURCE_BOUND_ADDITIONAL_BUILD_REVIEW**. The existing fresh
production clean-build result and its one-shot archive audit are supported by
the preserved argv/log/exit receipts, raw artifact bytes and matching source
custody. Campaign remains **ACTIVE/INCOMPLETE**; this review adds no runtime
change or metric improvement.

## Ownership and execution

This additional verifier owns only this new report and
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261012-r61-build-verification/additional-verifier-evidence`. Integration, old R60/R61 evidence, and the original reviewer's static
evidence were read-only. No native tests, builds, complexity scans, Graphify,
repairs, installs, retries, commits or original auditor reruns were performed.
The independent inspection ran once at 2026-10-12T04:33:57.561142+00:00 through
2026-10-12T04:33:58.020175+00:00; `verify.argv`, `verify.log`, `verify.exit` record
its exit **0**. Publication only reads verified bytes and writes new copies.

Coordinator notification identifies **native46012/cell2102, terminal 0**.
The handle is supported by coordinator notification and preserved notes;
this verifier did not attach to that process. The actual result review relies
on the build receipts and raw archives, rather than the handle or status alone.

## Actual build receipts

All seven launcher gates have preserved argv/log/exit and exit **0**:
ignored-cache, custody-before, version, npm-version, build, custody-after,
diff-check. `terminal.exit` is 0 and `terminal.txt` carries the completion
marker. The separate original `build-audit.argv/log/exit` also records exit 0.
The launcher refuses existing terminal/gate receipts and stops at the first
nonzero result. No failed native receipt was found or replaced.

The exact build argv is `npm run build:clean`; the source-bound package script
is `rm -rf .next && next build`, run in integration/frontend. The preserved
launcher uses `env -i`, Node **24.14.0**, npm **11.9.0** and disabled Next
telemetry. These are preserved-launcher facts; no new environment launch was
used to validate them.

The raw log shows Next **15.5.25**, successful compilation, lint/type-check
phase, exactly one **163/163** static-page completion, final optimization and
trace collection. All **35 warning lines** remain preserved. There is no
failed-compilation marker. Build log SHA-256:
`c1bed57da7cccf5c23e5bca4eddb077c4df8bddb632f426ff55e29c86d9bc069`.
Original completion audit SHA-256:
`552d8ec5d645b6bfe777bea402278375d309688f93530dfee2934317a34377c8`.

## Source and archive binding

Integration HEAD `114fbf7196382c6446a7963c34bd89e4c9795ef5`; main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. The before/after manifests are exactly equal
to R60 before/after custody. Independent live rehash and inventory comparison
confirmed **1047 frontend files**, **322 default unit specs**, selected **15
dependency/Node records**, frontend status, main HEAD/status/diff, complexity
baseline and matcher. Selected dependency metadata does not prove complete
dependency closure. All **1047 R60 source snapshots** were rehashed against
the same frontend inventory; no test suite was rerun for this label.

Every one of **200 archived artifacts** was independently checked for path,
size and SHA-256. The raw manifests/traces were parsed independently:

| Raw archived inventory | Verified count |
|---|---:|
| App-path manifest | 190 |
| Route manifest static / dynamic entries | 161 / 29 |
| Prerender static / dynamic entries | 158 / 0 |
| NFT files | 191 |
| NFT reference occurrences | 1997 |
| Next trace events | 5916 |

Build ID is **nST1uBT1SiPNlsNDgCMQn**. `standalone/server.js` is archived
and hashed; it was not launched. Counts describe distinct build inventories,
not total functional routes. NFT reference occurrences were counted, without
certifying all referenced-file existence or archiving a deployable closure.
The review depends on raw archived bytes, with no live `.next` persistence
assumption.

R60 original publication freeze remains SHA-256
`5a25d0a7bf95e412c237163fe322126e1f234ab38027a9bcef3a5990aeba3a2f`.
All **1183 records** were independently reverified: **1178 original paths**
and **5 mutable integration inputs via the exact companion archive**. Each
companion mapping matches original hash and byte count. No old freeze was
rewritten. Companion SHA-256:
`d8d4c02ed912f264ac7a9870d04191cda6c509eb8f0d8285d8f766f910bf2e32`.

## Immutable review publication and limits

`verification.json` binds all consumed paths/hashes. Every consumed byte is
copied to a new content-addressed object under additional-verifier-evidence,
with original-path mapping in `consumed-evidence-snapshots.json`; shared
publication/source edits after this review cannot invalidate those copies.
`freeze.json` binds this report and every private evidence file except itself
and its detached digest; `freeze.sha256` supplies that digest. New files are
read-only (0444), evidence directories 0555. This is a hash-bound read-only
freeze, not an OS immutable-attribute assertion. Publication verifies every
copy before freezing and preserves its first failure without retry.

No behavior, coverage, E2E, backend, worker, deployment, running-server,
external R43 test-type or campaign completion certification is inferred.
R43/R59 and other outstanding campaign decisions remain pending.
