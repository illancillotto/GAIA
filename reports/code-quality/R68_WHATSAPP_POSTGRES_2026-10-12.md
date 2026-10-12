# R68 — Presenze/WhatsApp: existing PostgreSQL checks verified

## Snapshot and ownership

Test/environment-only continuation from dedicated branch
`refactor/complexity-campaign-20261008`, HEAD
`8f7e0a8e1708002300a2b1e82313ab1fac4114fa`. Actual main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`; historical `55a1b1d` remains
the campaign origin, not the current base. Ownership registry precedes native
work; prior PROGRESS and registry archived. Main and its untracked Bonifica
test preserved. All agents were terminal before the scoped reviewer task.
Unrelated Next build was already terminal; no process was killed or overlapped.

## Historical inventory and fresh test matrix

Immutable R62 XML SHA256
`9cc6b0d7f3e96f40a42e1404e47cb402f75ae73478841d9111472dbe8fdaf46d`
contains 449 skips, 12 reason groups, 43 pytest classnames. Complete identity,
reason and detail inventory is external `R62_SKIP_INVENTORY.json`. R62's
7142PASS/449SKIP certificate remains historical and unchanged. R68 selects only
the original `backend/tests/test_presenze_whatsapp_postgres.py`, two skips
requiring `TEST_WHATSAPP_POSTGRES_URL`. No test/assertion/fixture was modified.

| Behavior | Original test | Fresh result |
| --- | --- | --- |
| Dedicated transaction advisory lock survives three application commits | lock test | PASS |
| Second connection excluded while lock held; reacquires after exception | lock test | PASS |
| Three original migrations, persistence, pending-day idempotence | persistence test | PASS |
| READ receipt dominates later FAILED; replay and notified-day mapping | persistence test | PASS |
| Notification uniqueness and config singleton enforce IntegrityError | persistence test | PASS |
| Downgrade/re-upgrade empties pending table | persistence test | PASS |

**2 PASS, 0 skip, 0 failure/error**, sole pytest invocation, retry0. JUnit suite
time1.406s. Real PostgreSQL, genuine SQLAlchemy connections/constraints/locks,
no simulated SQLite concurrency. No WhatsApp provider dispatch or external
messages. Existing fixture creates/drops one UUID schema per case. This does
not certify the complete migration chain or all Presenze concurrency behaviors.

Fresh evidence verifies two previously unverified identities. The other 447
R62 skip identities remain unverified by this follow-up; the historical449
count is not rewritten. Seven E2E skips remain unverified as well.

## Isolation and custody

Pinned local image
`sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea`,
PostgreSQL16.15; no image pull. Dedicated network-none container, read-only
root, tmpfs database/default socket, no ports/named volumes/application mounts.
Only newly owned Unix socket directory inside0700shortroot is host-bound.
Replacement environment contains synthetic settings and unused private SQLite
URL, no inherited production/provider credentials. Readiness requires final
PID1 postgres and actual target DB SQL, using the proven R67 setup.

Before/after DB identity, schemas, user relations and zero advisory locks are
exact. Positively owned container stopped/removed; tmpfs data destroyed. Existing
43container and67volume sets identical. All2852integration/2851main protected
input hashes identical to R67 and before/after R68. Test/migration/fixture bytes
match HEAD/main. No runtime, auth, quota, schema source, baseline, thresholds,
exclusions or coverage policy changed; no application complexity credit.

## Review, gates and limits

Independent preflight accepted preparation; independent terminal review accepts
the original two PostgreSQL tests, custody and cleanup. Actual-main ratchet
PASS0 against `a51a48dc`; diff-check recorded in companion JSON. Baseline and
exceptions hashes retain their established values. Global baseline/matcher
ambiguity remains separate. Complete suites and report not repeated for
identical protected inputs; last metrics remain1681files/20360callables/
1920errors/2736warnings/4656overlapping findings.

A static JSON extraction failed by selecting the `{` in Make's echoed
`${BASE_REF:-origin/main}` instead of the JSON object. Failure note preserved;
corrected extraction reads the first JSON line. Native gate was not rerun or
rewritten. No native test/preparation failure occurred in R68.

No coverage measured or100claim for unchanged runtime. Pool/full-worker100
still FAIL; R43/R51/R63 partials excluded, extreme tail and matcher ambiguity
unresolved. Classification: **VERIFIED_EXISTING_TEST_VARIANTS_NO_CHANGE_RUNTIME**.
Global objective **INCOMPLETE**, no new refactor, push or main merge.

## Durable handoff

`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r68-whatsapp-pg`
preserves input freezes, complete historical skip inventory, original native
argv/environment/log/XML/exits, DB/container inventories, closure and independent
review. Companion JSON binds terminal manifest and reviewer checksums; final
publication manifest and post-commit receipt bind remaining gates and commit.
Next decision: select one further coherent PostgreSQL verification prerequisite,
not a bulk run of all449skips against an unreviewed DB or new runtime refactor.
