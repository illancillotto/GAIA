# R23 — Authorized cache-only storage recovery

## Authorization and scope

User authorized cleanup of **sole cache ricreabili**, after inventory, without
touching code, worktrees or campaign evidence; subsequent answer requested
inventory of additional recreatable caches. Root performed a fresh inventory,
then removed only the following explicitly named inactive Jest transform caches.
No `git clean`, reset/stash, baseline generation/repair, browser/dependency or
host-data removal was performed.

## Inventory and removal

All paths are immediate children of `/tmp/jest_rs/`:

| Cache directory | Files | Payload bytes | Allocated bytes |
| --- | ---: | ---: | ---: |
| jest-transform-cache-93a33452ae856338932962f745fda28c-33e9a252a52783adb262261baf4dff05 | 32,240 | 992,526,692 | 1,057,882,112 |
| jest-transform-cache-a05021b654b17a517c3cad1485662801-33e9a252a52783adb262261baf4dff05 | 25,866 | 822,316,909 | 874,270,720 |
| jest-transform-cache-fa8187de4227eb94874bd04a46a6733b-33e9a252a52783adb262261baf4dff05 | 4,740 | 147,157,325 | 156,794,880 |
| **Total** | **62,846** | **1,962,000,926** | **2,088,947,712** |

Guarded inspection verified user ownership, no symlinks, expected two-hex-digit
cache buckets and hash-suffixed transform/map filenames, no writes within five
minutes, no detected active test runners and no detected handles/maps/cwd using
candidate directories. Process guards rerun before each removal. `lsof +D` on
the two largest directories also returned no entries. Fourteen GUI/session
processes did not permit descriptor/maps inspection; their readable command
lines identify systemd/PAM, Cursor sandbox/renderers, SSH agent/sessions, not
test runners. These access limits are retained rather than claiming unrestricted
OS-wide inspection. No processes were stopped.

## Actual storage and preservation

Deletion command exited **0**; all three candidates absent afterward.
Root filesystem available bytes **169,852,928 → 2,267,160,576** (approximately
162 MiB → 2.11 GiB). Difference includes concurrent shared-host allocations;
cache allocated bytes are not equated to exact filesystem free-space delta.
`/dev/shm` remains approximately 274 MiB available and was not cleaned.
Remaining caches, browser profiles/installed browsers, dependencies, worktrees,
source code and all previous reports/raw evidence were untouched.

Main/integration HEAD, status/diff hashes, baseline hashes, and complete Git
worktree-registry hash were identical before/after. Main HEAD55a, integration
HEAD35d4121e, baseline38e6b794 unchanged. Main protected diff9f85e574 and
status0d54d4eb match prior custody. R23 author tree remains clean at35d on
characterize/complexity-r23-utenze-preview; original Utenze sourceb0f822da and
old21/NAS45specs79ef3010/8f2258e4 independently confirmed unchanged afterward.

## Reproducible evidence and impact

Private evidence directory:
`/home/cbo/.cache/gaia-campaign/20261011-storage-r23-safe-cache-cleanup/`
contains `cleanup.py`, frozen `inventory.json`, `apply.json`, `apply.log`.
Inventory command: `python3 <evidence>/cleanup.py` (0).
Removal command: `python3 <evidence>/cleanup.py --apply` (0).
Do not rerun removal: recorded targets are deliberately absent now.

Coordinator subsequently ran actual `make complexity-ratchet
BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2
QUALITY_PYTHON=backend/.venv/bin/python`: **PASS**, native exit0, parsed
`findings: []`; `ratchet.log`/`ratchet.exit` preserved in the evidence directory.
`git diff --check` also passed. No baseline repair/generation occurred.

Later read-only inventory found additional caches, not removed: remaining
`/tmp/jest_rs` approximately1.6GiB, uv158MiB, pnpm metadata163MiB, thumbnails179MiB.
Those are only size candidates, not admitted cleanup targets. Shared filesystem
free space later rose to approximately5.5GiB independently of this three-cache
removal; that additional host activity is not attributed to the campaign.

This is storage recovery only, not a runtime change, coverage waiver, complexity
reduction or campaign completion. No application suites were run for cleanup.
R23 original preview ANALYZE ONLY can proceed; native test admission remains a
separate coordinator checkpoint. Clean/full frontend builds and final broad
suites are not admitted or certified by this headroom alone.

Dedicated documentation maintenance used `make graphify-platform-docs`, not a
generic repository-root extraction. First actual exit0, semantic chunk1/1done,
no warnings/failures:733nodes1026edges106communities;173cached3re-extracted;
12,817input/3,072outputtokens, estimated$0.0100. Logs/exit retained. Final refresh
is run separately after author analysis governance reaches READY_FOR_REVIEW;
no runtime/code-graph boundary changed. Generated graphs remain ignored.

Final dedicated docs refresh **actual exit0**, chunk1/1done, no warnings or
semantic failures:744nodes1045edges113communities,173cachehits3re-extracted,
13,001input/4,736outputtokens, estimated$0.0128. Separate final logs/exit retained.
Post-cleanup complete runtime custody matched **all1673** frozen R22 source
inputs, zero mismatches; baseline exact. `final-runtime-custody.json` retained.
Author analysis is frozen/READY_FOR_REVIEW, no new tests/heavy/runtime admitted.

## Continuation inventory — no further deletion

Fresh read-only `du -sh` inventory on 2026-10-11 reports `/tmp/jest_rs`1.6GiB,
`~/.cache/uv`158MiB, `~/.cache/thumbnails`179MiB and the complete
`~/.local/share/pnpm/store`1.8GiB. The latter is the whole package store, NOT
the previously identified163MiB metadata-only candidate; do not equate them
or admit deleting installed dependency content. These are size observations,
not ownership/activity/provenance checks or automatic cleanup authorization.
Root currently has approximately5.0GiB free; `/dev/shm`274MiB unchanged.
No additional cache was removed, no active cache or browser/dependency/evidence/
worktree touched. Available headroom suffices for the bounded R23 publication
checkpoint; full builds and final broad-suite admission remain separate.
