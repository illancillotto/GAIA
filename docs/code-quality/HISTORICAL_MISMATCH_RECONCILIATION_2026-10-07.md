# Historical baseline mismatch reconciliation — 2026-10-07

## Resolution

The 21 historical mismatch findings require **no new baseline repair**.
All 21 corrected measurements are already recorded in commit
`dc66972813970573ec5d1dd8d0b3426fa6c56116`
(`fix(quality): repair stale baselines only from clean runtime`), an ancestor
of current HEAD/main `703f8411871e88e10b1c45151ba035f6b1f35a8f`.
The current baseline retains those corrected values.

This closes the provenance question left open by the campaign reports. Their
earlier recommendation to prepare another clean-worktree repair is superseded
for these 21 findings. No runtime changes, baseline generation, reference
substitution, thresholds, exclusions, commits or history rewrites are needed.
This is metadata reconciliation, **not an additional complexity reduction**.

The historical comparison against
`6b61fd27d325459866259c4b7cba133e661ea38f` still fails: Git correctly reads
the stale baseline stored in that immutable commit. It is retained as an
explicit historical diagnostic, not reported as PASS. The authoritative
current campaign gate remains the existing merge-base with `main`.

## Evidence

Each row was identified by **path and callable name**, not name alone (route
functions have colliding names). Sources were loaded with `git show`, parsed
with `PyVisitor`, and checked against both historical and current baseline
records. Every lookup is unique. An independent read-only specialist repeated
the provenance analysis.

Paths:

- XLSM: `backend/app/modules/presenze/services/xlsm_export.py`.
- Ruolo: `backend/app/modules/ruolo/tributi_repositories.py`.
- inCASS: `backend/app/services/elaborazioni_capacitas_incass.py`.

The first row is XLSM, the last is inCASS; all intervening rows are Ruolo.
“HEAD” is the committed baseline at `703f8411`; “current” is the measured
working-tree source. Historical source is measured at `6b61fd27`.

| Callable | Metric | Historical recorded | Historical source | Repaired `dc669728` | HEAD | Current |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `count_operai_paid_rest_days` | params | 1 | 2 | 2 | 2 | 2 |
| `_batch_load_registered_mail_notification_dates` | nesting | 2 | 3 | 3 | 3 | 3 |
| `import_posta_online_registered_mails` | loc | 70 | 72 | 72 | 72 | 72 |
| `import_posta_online_registered_mails` | params | 5 | 6 | 6 | 6 | 6 |
| `list_registered_mails` | cyclomatic | 9 | 15 | 15 | 15 | 15 |
| `list_registered_mails` | cognitive | 8 | 19 | 19 | 19 | 19 |
| `list_registered_mails` | loc | 41 | 59 | 59 | 59 | 59 |
| `_upsert_posta_online_registered_mail` | cyclomatic | 10 | 20 | 20 | 20 | 20 |
| `_upsert_posta_online_registered_mail` | cognitive | 9 | 25 | 25 | 25 | 25 |
| `_upsert_posta_online_registered_mail` | loc | 53 | 72 | 72 | 72 | 72 |
| `_upsert_posta_online_registered_mail` | nesting | 1 | 2 | 2 | 2 | 2 |
| `_upsert_posta_online_registered_mail` | params | 4 | 5 | 5 | 5 | 5 |
| `_registered_mail_recovery_status` | cyclomatic | 3 | 5 | 5 | 5 | 5 |
| `_registered_mail_recovery_status` | cognitive | 2 | 4 | 4 | 4 | 4 |
| `_registered_mail_recovery_status` | loc | 14 | 20 | 20 | 20 | 20 |
| `_registered_mail_recovery_status` | params | 2 | 3 | 3 | 3 | 3 |
| `mark_registered_mail_recovery_on_payment` | cyclomatic | 3 | 4 | 4 | 4 | 4 |
| `mark_registered_mail_recovery_on_payment` | cognitive | 2 | 4 | 4 | 4 | 4 |
| `mark_registered_mail_recovery_on_payment` | loc | 20 | 21 | 21 | 21 | 21 |
| `mark_registered_mail_recovery_on_payment` | nesting | 1 | 2 | 2 | 2 | 2 |
| `list_incass_sync_jobs` | params | 1 | 3 | 3 | 3 | 3 |

Committed HEAD source also equals the corrected value in every row. This does
not assert that every other metric or record in the full baseline is fresh;
the previously disclosed inCASS file-LOC difference remains separate.

Current baseline SHA256, unchanged before/after verification:
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
Machine-readable evidence with source hashes:
`/tmp/gaia-mismatch-provenance.json`; reproduction script:
`/tmp/gaia-verify-historical-mismatches.py`. These local artifacts are ephemeral;
the table and immutable commit references above preserve the conclusion.

## Tests and counterchecks

| Verification | Result |
| --- | --- |
| `git merge-base --is-ancestor dc669728 HEAD` | PASS, exit 0 |
| 21 historical/source/repaired/HEAD/current assertions | PASS |
| `BASE_REF=main make complexity-ratchet` | PASS, zero findings, merge-base `703f8411` |
| `BASE_REF=6b61fd27 make complexity-ratchet` | FAIL, same 21 historical mismatches; not waived |
| `make quality-test QUALITY_PYTHON=backend/.venv/bin/python` | 169 PASS, including clean-runtime repair safeguards |
| 21 independent metric-increase counterchecks | PASS: all deliberately increased measurements rejected |

Counterchecks load the complete audit, then filter comparison to the three
affected paths, avoiding the known partial-scan matching limitation. The
unmodified report passes against the current committed baseline. Each check
increments exactly one affected metric by one in an independent in-memory
copy; all return exit classification 1 with the corresponding
`legacy_metric_regression`. No on-disk report or baseline is mutated.
This verifies metric enforcement, not application behavior or coverage.

Logs: `/tmp/gaia-mismatch-main-ratchet.log`,
`/tmp/gaia-mismatch-historical-ratchet.log`,
`/tmp/gaia-mismatch-quality-tests.log`,
`/tmp/gaia-mismatch-counterchecks.log`.

## Remaining limits

This documentation-only reconciliation does not repeat the already completed
application suites or claim they all pass. See `VERIFICATION_2026-10-07.md`:
the legacy ANPR test failure, unavailable E2E backend and campaign quantitative
targets remain open. Full-file coverage evidence for the nine campaign runtime
files is unchanged. No new runtime or test-policy change is introduced.
