# GAIA — R50 SISTER pool characterization integration

## Snapshot and scope

Campaign branch `refactor/complexity-campaign-20261008`, HEAD
`114fbf7196382c6446a7963c34bd89e4c9795ef5`; main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Slice began October11 and root
verification completed after the Europe/Rome date boundary. Concurrent main
and uncommitted admitted runtime remain unchanged. No commit or Git merge.

The new test module characterizes one coherent SISTER credential-pool lifecycle:
configured eligibility versus availability, known/quarantined merge identity,
and genuine asynchronous refresh/announcement/completion. No runtime, old test,
retry policy, portal behavior, auth, data schema, baseline or tooling is changed.
R43/E2E fixture-lifecycle/Bonifica normalization decisions remain separate.

## Behavior and test matrix

| Behavior | Existing protection | New characterization | Root result |
|---|---|---|---|
| Manual configured IDs honor active/owner/allowlist, not current schedule/profile | Pool availability/query tests | Real persisted SQLite credentials and config distinguish configured vs available | PASS |
| Perpetual IDs require enabled profile, irrespective of closed schedule | Pool autosync profile tests | Real config JSON/query covers disabled/missing/foreign/inactive/unlisted | PASS |
| Merge retains object identity and quarantine, even with no additions | Positive merge tests | Same-ID replacement, rejected unseen member, tuple identity and refreshed metadata | PASS |
| Pending runners refresh and announce before finishing | Dynamic pool tests | Real tasks/Event, real DB insertion/allowlist/query, one-second refresh and ordered events | PASS |

All four tests use legitimate inputs. No internal return stub, patched
asyncio.wait/all/task state, new pragma, exclusion or weakened assertion.
In-memory SQLite is not PostgreSQL isolation or live-portal certification.

## Preserved first failure and separate V2

V1 targeted31PASS, then Ruff I001 import grouping FAIL: no format execution,
no admission. Author26-member and reviewer freezes remain immutable. Fresh
V2 changes only imports/format; the complete test-body AST and import multiset
are equal. No existing assertion is modified. V2 targeted31PASS/style/format
PASS, complete worker782PASS/1PGskip across53exact files. Author used synthetic
overrides, not env-i; inherited-environment and tracked-only custody limits are
explicit, not hidden. Independent reviewer4f3a57f8/freeze25fef358d5 permits
exact test-only root gates, not runtime cleanup or a coverage waiver.

## Independent root commands and result

Exact new spec SHA-256:
`2fdef746e402920a6ab52519ba64a4f980884c473f6cbf303c8f0e85780930e8`.
Transferred through apply_patch only after author/reviewer terminal review.
Root native40854 launched with env-i PATH/HOME/LANG/TMPDIR, then owned script
supplied synthetic settings, private SQLite URL, rootPYTHONPATH, absolute
existing backend interpreter and PYTHONDONTWRITEBYTECODE. No dependency install.

```sh
make test-worker WORKER_PYTHON=<absolute-integration-python> \
  WORKER_COVERAGE_JSON=<root-evidence>/coverage.json \
  WORKER_COVERAGE_XML=<root-evidence>/coverage.xml
python -m ruff check modules/elaborazioni/worker/tests/test_sister_pool_r50_characterization.py
python -m ruff format --check modules/elaborazioni/worker/tests/test_sister_pool_r50_characterization.py
make complexity-report REPORT_JSON=<root-evidence>/complexity.json REPORT_MD=<root-evidence>/complexity.md
make complexity-ratchet BASE_REF=main
git diff --check
```

Root **TERMINAL0**: worker782PASS/1skip, style/format/report/ratchet/diff/custody
all exit0. Sorted target inventory equals recursive inventory, all53 unique
files executed; no omission or repeated file. Skip retained exactly:
`test_sister_recovery_migration.py:22`, GAIA_TEST_POSTGRES_URL not configured.
PostgreSQL recovery migration remains unverified, not PASS.

## Coverage, before/after and remaining gaps

| Perimeter | Before R47 statement / branch | After root R50 statement / branch |
|---|---|---|
| Worker total |6072/6077;1624/1630|6075/6077;1628/1630|
| Pool missing |449,450,451,523; five edges|523;522→523|
| Retry metadata missing |22;21→22|22;21→22 unchanged|

Three previously missing statements and four branch edges are now exercised.
Worker statement99.967089% and branch99.877301%; pool330/331statement and
87/88branch. **Full-file/global100 remains FAIL**, not rounded or waived.
All21 existing excluded lines retained, zero added. No modified runtime file
coverage requirement is waived: worker runtime bytes are unchanged.

The second pool completion-check edge appears unreachable only under the
inspected production cooperative scheduler and synchronous callbacks. Independent
review explicitly limits that proof for custom/eager/reentrant environments.
No guard is removed; no fake scheduler is used to paint the branch green.
Retry metadata remains outside this responsibility and is not silently fixed.

## Metrics and ratchet

Root report SHA-256:
`504e7355bb6a893e8c5876a70e58c3d7b53366a272c995320fc048fa4791b311`.
All1673 prior file objects and all20329 prior callable objects equal the admitted
R41 report exactly. Only the new test adds1file/10callables/195effectiveLOC:
cognitive sum11/max6, cyclomatic sum19/max5, no violations. Runtime complexity
delta0; no strategic debt-reduction credit or component-boundary change.

Official totals:1674files/20339callables/1920errors/2735warnings/4655overlapping
observations. Application without worker tests stays1619files/19008callables/
1912errors/2680warnings/4592observations. Coda5>300/17>200/55>100 unchanged.
Actual main55a ratchet **PASS, findings[]**. Baseline SHA38e6b794, thresholds,
scope, excludes and matcher remain unchanged. Global baseline provenance and
residual matcher ambiguities are separate; no new global PASS is asserted.

## Custody, classification and evidence

Root before/after2808 tracked/untracked protected inputs, main source/status/
binary diff, branch/HEAD/base and admitted state are identical. Source-map/
scope comparison distinguishes the new test from all existing runtime records.
Evidence: SSD `.codex-gaia-campaign-20261011-r50-worker-pool-characterization/`
author/reviewer V1/V2 freezes and root-evidence exact commands/logs/exits,
coverage JSON/XML, inventory, whole report, ratchet and independent root audit.
No discarded failure, blind retry, worktree cleanup, baseline inflation or merge.

Classification **NO_CHANGE — ORIGINAL_RUNTIME_CHARACTERIZED**. The test-only
slice consolidates useful coverage, not an IMPROVED runtime claim. Final
independent composite evidence review and corpus receipt are recorded separately.
Campaign remains **ACTIVE / INCOMPLETE**, extreme hotspots and pending decisions
are not resolved by this checkpoint. Stop at this credential-pool responsibility.

## Publication closure — 2026-10-12

Independent final report75ebb4efab0c1c71f218673c09b5c98c3df57eff79385fe09a97825cbca3cffd
accepts the exact test-only addition; final38member freeze567466da and prior123
records retained. No application test or native gate was repeated at publication.

Dedicated worker Graphify70650 TERMINAL0:1710nodes/3910edges/89communities.
Platform docs Graphify45807 TERMINAL0:560nodes/632edges/119communities, semantic
chunk1/1 done and no semantic-failure warning;6712input/2487outputtokens,
estimated cost$0.0067. Both raw logs/exits live in root-evidence. Graph artifacts
remain ignored and uncommitted; neither graph is used as complexity proof.

Root publication freeze is a separate immutable receipt in root-evidence,
excluding mutable governance registry/PROGRESS/global report. R43 still awaits
a distinct test-only correction decision; its frozen candidate is not installed.
No runtime guard cleanup, Bonifica normalization or E2E fixture repair is granted.
