# R19 V1 — Rejection checkpoint

## Decision

**REGRESSED / REJECTED. Not integrated, not committed.** Campaign remains
ACTIVE / INCOMPLETE. Integration HEAD is
`218670c73b7abdcb0210e61ac04e15271c9ebc41`; authoritative merge-base is
`55a1b1d35911451e018b662c2acc450bf5994ea2`.

## Functional regression

The original route retains fetched ORM instances until its return. V1 releases
`DriverMismatchInputs` before subsequent anomaly queries. SQLAlchemy's weak
identity map can then reload an entity changed by a concurrent writer.

Independent isolated SQLite ORM diagnostic used a distinct writer connection
to commit plate `AFTER` between queries. Original retained the vehicle and
returned `BEFORE` for `inactive_vehicle.entity_label`; V1 lost that reference
and returned `AFTER`. Query order was identical and reader dirty count was zero.
Complete responses differ. This is a reproduced regression, not a suspected risk.

The original function was AST-compiled with a synthetic filename for this
diagnostic. Results are not PostgreSQL certification or full-file coverage proof.

## Surviving evidence

Directory: `/home/cbo/.cache/gaia-campaign/20261009-r19-independent-review/`.

| Artifact | SHA256 |
| --- | --- |
| lifetime-results.json | 649ba83982b9dddf96362329d919743d98f63eb3e83c1ef316bb8d48ff97d0c2 |
| lifetime-diagnostic.py | 6be604ab97ee9c0aa638e3f666a3746d17e7cae8b95a64499aff1b86d212d264 |
| lifetime-diagnostic.log | 649ba83982b9dddf96362329d919743d98f63eb3e83c1ef316bb8d48ff97d0c2 |
| lifetime-diagnostic.exit | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |

Diagnostic exit is 0, recording the response inequality successfully. Independent
focused log/exit records 53 PASS. Independent ORM union records 247 PASS,
10 synthetic diagnostics deselected, 60 warnings, full-file statement/branch
100%. These passing gates do not override the functional regression.

V1 measured target cognitive 298→239; combined cognitive 855→829, decisions
536→536, combined LOC 1298→1351, errors 19→19, warnings 12→14. Prior candidate
immutable-base ratchet PASS/0 remains evidence only for that rejected candidate,
not proof of functional equivalence or an accepted integration.

## Infrastructure and freeze limitations

Independent reviewer thread `01a121e9-741c-7f90-aa16-a492b838b89f` completed and
explicitly released heavy execution. ENOSPC prevented final report and manifest:
`REVIEW_R19_DRIVER_MISMATCH_2026-10-09.md` and `protected-after.json` are empty.
No claim of completed review freeze or full protected-path post-audit is made.

Coordinator rechecked surviving frozen reviewer input hashes:

| Input | SHA256 |
| --- | --- |
| analytics.py | 41c4fd196436c7bbbf0714622094356e3e323d338ffd8b9d2401ca5f2f6a29c5 |
| _driver_mismatch.py | 4d4a34c497baf1119d50486cfb999542d7bc40f57477a1de338b72df62d35821 |
| test_operazioni_driver_mismatch_r19.py | 4943e9cd74fc407c6263f99560b5f9eb22eccf01a45c11df8a0e5198ec69f262 |

Main binary diff hash `9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`
and status hash `0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`
remain unchanged. No runtime, baseline, threshold or exclusion changes in this
checkpoint; no cleanup or heavy-gate restart.

## Next decision

Disk had approximately 130 MB free after ENOSPC. User decision requested for
removing only the integration frontend `.next` regenerable build (842 MB).
Separately requested priority: correct this same slice with route-held typed
inputs, real ORM lifetime characterization and fresh independent review, or
return to Capacitas. Neither proposal is implemented by this checkpoint.

GIS failure is already resolved: retained final verification records focused
10 PASS, GIS 5 PASS and full E2E 54 PASS / 7 preexisting skips. See
`VERIFICATION_GIS_E2E_FIX_2026-10-09.md`; no fresh GIS rerun is claimed here.
