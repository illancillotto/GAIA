# GAIA — R49 admitted-source E2E checkpoint

## Snapshot and ownership

Integration `refactor/complexity-campaign-20261008`, HEAD
`114fbf7196382c6446a7963c34bd89e4c9795ef5`, main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Admitted R38–R41 changes
remain uncommitted. Main concurrent work and external R43 are unchanged.
Ownership precedes the independent environment/result reviews.

## Distinct preparation attempts

The original attempt failed before database/service/browser creation because
the private seed script could not import `app`. Its 18-member freeze remains
immutable. V2 added explicit package paths but was never launched: independent
static review detected its form-encoded login probe contradicted LoginRequest.
Fresh V3 retained the package-path correction and sent JSON credentials as the
existing frontend/backend contract requires. Three helpers remain byte-identical.

Independent V3 review `57b9926d`, freeze `a4252d1a` verified 43 records and
allowed static readiness only with the exact `env -i` whitelist. Coordinator
verified that freeze, absent inherited optional flags and free ports before one
fresh launch. No provider secret, application `.env`, live database, existing
container, localhost8080 service or browser installation was used or changed.

## Commands and actual result

From integration, the reviewed launcher runs the private V3 supervisor with only
PATH/HOME/LANG/TMPDIR/PYTHONDONTWRITEBYTECODE/NEXT_TELEMETRY_DISABLED inherited.
The supervisor supplies synthetic credentials and a fresh private SQLite URL.
Seed created 282 existing-model tables, synthetic super_admin and 85 sections.
Owned loopback gateway39081/Next39082/FastAPI39083 health, login and identity
checks passed. No INAZ mapping or cadastral dataset was seeded.

Existing complete Playwright collection:

```sh
cd frontend
npm run test:e2e -- --workers=1 --retries=0 --max-failures=1 \
  --reporter=line,json --output=<private-environment-v3>/browser-artifacts
```

Native session83110 **TERMINAL1**, not PASS. All24 default specfiles/61 cases
are represented in JSON; no collection filter or assertion/timeout change.

| Outcome | Cases |
|---|---:|
| PASS | 37 |
| Failed | 1 |
| Explicitly skipped | 5 |
| Not run after first failure | 18 |

Native JSON combines the latter two categories as skipped23; audit separates
them using actual result records and skip annotations, not a success claim.
Duration148344.432ms, flaky0. Additional runner error reports stopping early
after the configured first failure. Every case and exact skip reason is retained
in `environment-v3/result-audit.json` and original `e2e-results.json`.

## Diagnosed failure and impact

`ruolo-avvisi.spec.ts:34` timed out at `loginAsAdmin` line11, before any Ruolo
search assertion. The browser trace shows actual login HTTP403 with:
"Limite dispositivi raggiunto: massimo 20 dispositivi attivi per utente."
Read-only private DB inspection finds exactly20 active devices for synthetic
user1,20 allowed-login session events and one blocked event
`max_active_devices:20`. Source enforces the existing super_admin quota.
Repeated isolated browser contexts exhaust that shared synthetic identity's
device quota; this is not evidence of a Ruolo-search regression. Enforcement
must not be disabled, the quota raised or an auth failure hidden to pass E2E.

All5 `catasto-gis.spec.ts` cases and the `gis-strumenti.spec.ts` smoke passed
in this attempt. Optional GIS Territorio cases remain explicitly skipped;
no PostgreSQL/PostGIS, provider or production-stack parity certificate follows.

## Custody, teardown and disposition

Before/after2712 protected inputs,24 specfiles, HEAD/merge-base, main state,
baseline, matcher and BUILD_ID are identical. No source/test/config/dependency
edit, retry, coverage inference or additional complexity credit. All3 owned
children terminated; ports39081/39082/39083 verified free after teardown.
Application source and registered baseline are unchanged.

Evidence directory:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r49-e2e-checkpoint`.
Original preparation failure, V2 static HOLD and V3 browser failure remain
separate. Trace/screenshot/video/log/DB/JSON/exit/custody preserved, no overwrite.
Classification **NO_CHANGE — E2E_STOP_PRIVATE_DEVICE_QUOTA**.

Campaign remains **ACTIVE / INCOMPLETE**. A distinct test-fixture lifecycle
decision is requested before correcting synthetic-device accumulation. R43's
test-only decision is separately pending; no frozen candidate is installed.
No commit, push, Git merge, baseline inflation or relaxed policy.
