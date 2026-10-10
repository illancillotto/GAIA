# R19 — Rejected V1 counterprobe

## Purpose and result

The exact independently accepted ORIGINAL lifetime test was run read-only
against the rejected V1 actual imported route. No compiled AST/synthetic runtime,
source replacement, test weakening or fixture pinning. Private external test
SHA74f2b509810372fd32381c8f1d23217ca9ca6141bae0f5390cf3385845dcd028 matches
the approved file byte-for-byte.

Actual outcome **EXPECTED FAIL: 1 failed, 2 passed**, exit1,7.97seconds. The
all-families complete response assertion fails; driver-only and inactive-only
controls pass. This proves the new characterization detects the known V1
regression rather than merely exercising the code. V1 remains REJECTED and
is never integrated, even though its old coverage/complexity gates passed.

## Execution

Frozen review worktree `GAIA-campaign-20261008-network`, original HEAD218670c7
with exact rejected runtime hashesanalytics41c4fd19/helper4d4a34c4 unchanged.
Installed integration Python executed external pytest from this tree's backend
with PYTHONPATH pointing to that backend. Explicit test environment uses
isolated SQLite, synthetic auth secrets; real auth dependencies are not
certified by the direct route call. New test creates its own named in-memory
SQLite database and distinct writer connection, no production data.

```bash
python -m pytest -q -p no:cacheprovider \
  /tmp/gaia-r19-lifetime-v1-counterprobe-20261010/test_operazioni_driver_mismatch_lifetime.py \
  --junitxml=/tmp/gaia-r19-lifetime-v1-counterprobe-20261010/results.xml
```

Native14212 observed to terminal; no retry. Exact log/exits/JUnit retained at
`/tmp/gaia-r19-lifetime-v1-counterprobe-20261010/`.

| Artifact | SHA256 |
| --- | --- |
| pytest.log |dc0e1bf8ca704f0cf68c1a26523cf1ba2e35289dafbfec0473b6d09a05019d94 |
| results.xml |e8ece2e4c25f01663173efd0b5338b95e15f0b04d42ded1509be572758775d59 |

## Limits

No runtime coverage or PostgreSQL certification claimed. This deterministic
SQLite inter-query writer reproduces the response regression, not all possible
production isolation levels. JUnit/log report failure at full response equality
before subsequent boundary assertions; those later assertions are not claimed
executed in the failed case. Original and independent original executions
pass all three tests. No V2 correction authorized by this evidence alone.
