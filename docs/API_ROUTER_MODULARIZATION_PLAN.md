# API and Router Modularization Plan

## Objective

Reduce the ownership and navigation cost of the largest frontend API barrels
and backend FastAPI routers without changing public imports, HTTP contracts,
authorization, route precedence, or runtime behavior.

The work is structural. A split is classified as
`REORGANIZED_AND_CHARACTERIZED` unless the measured callable complexity also
decreases without moving debt.

## Compatibility invariants

- `@/lib/api` and `@/types/api` remain supported public facades.
- Domain clients depend on `@/lib/api/core`, never on the facade that exports
  them.
- Existing exported names and TypeScript signatures remain unchanged.
- FastAPI paths, methods, operation identifiers, response models, tags,
  dependencies, and registration order remain unchanged.
- Shared backend behavior lives in services, queries, policies, or serializers;
  route modules remain thin HTTP adapters.
- Existing direct imports from legacy `router.py` modules remain available
  during migration through explicit compatibility re-exports.

## Execution slices

1. Capture frontend export inventories and the generated OpenAPI document.
2. Extract the frontend HTTP transport into `frontend/src/lib/api/core.ts`.
3. Split runtime clients and types by bounded domain, retaining facade exports.
4. Split Utenze routing as the lowest-complexity backend pilot.
5. Split Network routing, isolating statistics and subject-correlation helpers.
6. Split Presenze routing, isolating dashboard, bank-hours, scheduling, import,
   sync, and export responsibilities.
7. Split Me routing into self-service status/Presenze, summary, Operazioni, and
   asset groups while preserving private helper imports and monkeypatches.
8. Split GIS Platform routing into catalog, external/query, import, layer,
   annotation, change-request, and export/audit groups.
9. Split the Catasto bulk anagrafica router into normalization, matching,
   resolvers, execution, exports, uploads, persons, holders, authoritative
   lookup, and ordered route groups.
10. Compare export inventories and OpenAPI snapshots, then run targeted tests,
   full relevant suites, coverage, lint/typecheck, and the complexity ratchet.
11. Refresh frontend/backend Graphify corpora and update architecture, structure,
   coverage, hotspot, and progress documentation with measured results.

Each slice must be independently reviewable. A new failure, ambiguous baseline
match, changed HTTP contract, or inability to demonstrate an invariant stops
the next slice until the cause is understood.

## Baseline

Baseline snapshot captured on `main@6d6278cb`:

| File | LOC | Cognitive max | Cyclomatic max |
| --- | ---: | ---: | ---: |
| `frontend/src/lib/api.ts` | 5,339 | 54 | 30 |
| `frontend/src/types/api.ts` | 4,403 | 0 | 0 |
| `backend/app/modules/utenze/router.py` | 1,983 | 39 | 28 |
| `backend/app/modules/network/router.py` | 2,630 | 209 | 109 |
| `backend/app/modules/presenze/router.py` | 4,616 | 111 | 64 |

The source files currently contain more physical lines than the scanner LOC
values because the scanner excludes blank/comment-only lines.

## Execution status (2026-09-05)

- Type facade completed: `frontend/src/types/api.ts` is an eight-line
  compatibility barrel over seven domain barrels in `frontend/src/types/api/`;
  Presenze and Elaborazioni are further divided into bounded base/operations
  files to remain below the file-level quality threshold.
- The existing import path and all consuming TypeScript code pass the global
  typecheck.
- Runtime facade completed: `frontend/src/lib/api/index.ts` preserves the
  `@/lib/api` contract and delegates to 15 responsibility-oriented modules.
  The public inventory is unchanged (`450` exports before and after, with no
  missing or additional names).
- Characterization now covers every branch of the extracted runtime slice:
  `1,263/1,263` statements, `826/826` branches, `420/420` functions and
  `1,195/1,195` lines. The focused API suite contains `811` passing tests.
- Runtime metrics before: LOC `5,339`, callable `419`, cognitive sum/max
  `545/54`, cyclomatic sum/max `850/30`, one error-level file violation.
  Metrics after across the facade and extracted modules: LOC `5,080`, callable
  `420`, cognitive sum/max `545/54`, cyclomatic sum/max `851/30`. The remaining
  file-level debt is one warning on `network.ts`; no callable debt was reduced.
- The frontend result is therefore `REORGANIZED_AND_CHARACTERIZED`, not
  `IMPROVED`. The extra callable/cyclomatic point is the now independently
  detected `credentialIds.forEach` callback, not a new behavioral branch.
- Utenze pilot completed: `app.modules.utenze.router` is now a compatibility
  package assembling contiguous route groups for imports, Bonifica staging,
  subjects, documents and reporting. Shared serializers and the subject detail
  projection live under `backend/app/modules/utenze/routes/`.
- The normalized OpenAPI snapshot is byte-identical before and after: `746`
  paths, `876` operations, SHA-256
  `e5d00458a818f5c9af7e9d54b2aa6905d647c7b82588fb1382a1e18e5b34fada`.
  Legacy imports for `get_anagrafica_import_service`, `get_stats` and
  `_build_subject_detail`, including the NAS monkeypatch point, remain valid.
- Utenze coverage is `100%`: `870/870` statements and `220/220` branches with
  `89` passing tests. Metrics change from LOC `1,983`, cognitive sum/max
  `417/39`, cyclomatic sum/max `409/28` to LOC `2,050`, cognitive `409/39`,
  cyclomatic `403/28`. One warning remains on `routes/support.py` at LOC `640`;
  there is no error-level file violation and no Utenze ratchet finding.
- Network router completed: `app.modules.network.router` is now a compatibility
  package that assembles the same 39 endpoints from bounded route modules for
  VPN access, overview, devices, tracking, firewalls, scans, and floor plans.
  Device/RDAP, endpoint labels, tracking/inference, traffic, scan, and Sophos
  helpers are separated by responsibility; every scanner file remains below
  the file-level LOC warning threshold.
- Network compatibility points remain public: `_resolve_device_label`,
  `run_network_scan`, `poll_sophos_firewall_metrics`, and the `urllib` namespace
  used by existing imports and monkeypatches. The normalized OpenAPI remains
  byte-identical at `746` paths and `876` operations, SHA-256
  `2392ea45da9938cfcd0773e2d7e253023604e8e38697b922404c04c950510a4e`.
- Network coverage is `100%`: `1,405/1,405` statements and `452/452` branches
  in the final focused run. Metrics move
  from LOC `2,630`, callable `87`, cognitive sum/max `1,101/209`, cyclomatic
  sum/max `774/109` to aggregate LOC `2,943`, callable `87`, cognitive
  `1,101/209`, cyclomatic `774/109`; final aggregate LOC is `2,942` after
  removing one intermediate list. The LOC increase is module import/facade
  overhead; callable complexity and debt are unchanged.
- The Network result is `REORGANIZED_AND_CHARACTERIZED`. The ratchet reports no
  Network finding; its global failure remains limited to concurrent
  Elaborazioni changes outside this slice, so the baseline was not updated.
- Graphify was refreshed after the structural change: Network has `429` nodes,
  `1,093` edges, and `18` communities; backend has `8,178` nodes, `20,710`
  edges, and `448` communities. The platform docs graph was also refreshed
  successfully, with all changed semantic files extracted.
- Presenze router completed: `app.modules.presenze.router` is now a compatible
  package facade over 11 route groups and 8 helper modules. Access/supervisors,
  configuration, collaborators/giornaliere, recovery, bank hours, import,
  sync configuration, guidance, sync jobs, exports, and dashboard keep their
  historical registration order.
- Public helper imports used by `me`, Gate Mobile, and tests remain available;
  the facade also forwards and restores legacy monkeypatches across the owning
  modules. The canonical identity mapping remains exclusively
  `presenze_collaborators.application_user_id -> application_users.id`.
- Presenze OpenAPI was byte-identical immediately after the split at `746`
  paths and `876` operations, SHA-256
  `e5d00458a818f5c9af7e9d54b2aa6905d647c7b82588fb1382a1e18e5b34fada`.
  A later concurrent Organigramma change added `/organigramma/sync/inaz/preview`;
  the final isolated `/presenze` comparison remains byte-identical at `64`
  paths, SHA-256 `19da9c78abf3488310bca1c1ff29ac65969f4125d09d6c026e4225710a36b35c`.
  Coverage is `100%`: `2,292/2,292` statements and `696/696` branches with
  `241` API, helper, operai, Gate Mobile, and `me` tests.
- Metrics move from LOC `4,616`, callable `160`, cognitive sum/max `1,353/111`,
  cyclomatic sum/max `1,139/64` to aggregate LOC `5,267`, callable `163`,
  cognitive `1,370/111`, cyclomatic `1,154/64`. The 160 legacy callables retain
  exactly the original cognitive and cyclomatic totals; the three new callables
  belong only to facade compatibility. Maximum file LOC is `718`, removing the
  previous file-level error.
- The Presenze result is `REORGANIZED_AND_CHARACTERIZED`. The baseline was not
  updated: the ratchet identifies three moved callables whose fingerprints had
  already changed after its historical source commit (`list_collaborators`,
  `_apply_daily_record_filters`, `get_dashboard_summary`), plus concurrent
  Elaborazioni findings. Exact before/after metrics prove no Presenze callable
  regression; changing the matcher or absorbing the drift is out of this slice.
- Graphify was refreshed after the split: Presenze has `1,079` nodes, `3,432`
  edges, and `43` communities; backend has `8,379` nodes, `21,292` edges, and
  `478` communities. Platform docs has `1,935` nodes, `4,318` edges, and `144`
  communities; the final incremental refresh re-extracted all three remaining
  changed semantic files.

- Me router completed: `app.modules.me.router` is now a compatible facade over
  four ordered route groups and `common.py`. The 17 `/me` paths and operations
  are byte-identical, SHA-256
  `cb6eb0146e45c4d6d7b5631f48c4ee84ce7babce22f2a59e42e3eb63ea3d6c61`.
- Legacy private imports used by the period router and helper tests remain
  available. Facade forwarding preserves monkeypatches for overtime export,
  LibreOffice subprocess calls and the Network device-label resolver.
- Me coverage is `100%`: `369/369` statements and `70/70` branches with `129`
  API, helper and facade tests. All 29 legacy callable fingerprints match and
  retain cognitive `123`, cyclomatic `130`, LOC `765` and all 18 callable
  violations. The three new facade callables are below threshold.
- Aggregate package LOC is `990`, but the maximum file falls from `862` to
  `336` effective LOC and removes the file-level error. The result is
  `REORGANIZED_AND_CHARACTERIZED`; the global ratchet remains blocked only by
  historical changes outside Me, so baseline and tooling were not updated.
- Graphify was refreshed after code and docs changes: backend has `8,437`
  nodes, `21,457` edges and `471` communities; platform docs has `1,943`
  nodes, `4,348` edges and `143` communities after a successful incremental
  retry of the semantic chunk.

- GIS Platform router completed: `app.modules.gis.router` is now a compatible
  facade over seven ordered local route groups plus the existing Scheda and
  QGIS child routers. All 47 paths and 51 operations are byte-identical,
  SHA-256 `07d3eeae0e764aeff06e90d0b26704e0c976a8e53e8ea45717e39325f7ec2b95`.
- Route order, endpoint names/modules, module-level authorization and legacy
  access to `interrogazione_service`/`interroga` are preserved. Coverage is
  `100%`: `272/272` statements and `24/24` branches with 111 focused tests;
  the extended GIS suite passes with 220 tests.
- All 46 legacy fingerprints retain cognitive `6`, cyclomatic `52`, callable
  LOC `408`, nesting, parameters and nine parameter violations. The three new
  facade callables are below threshold. Aggregate package LOC is `709`, while
  maximum file LOC falls from `587` to `122`, removing the file-level warning.
- The GIS result is `REORGANIZED_AND_CHARACTERIZED`. Quality tooling and local
  style gates pass; the global ratchet/style failures remain historical and
  contain no finding under `backend/app/modules/gis/router/`.
- Graphify was refreshed after the structural change: backend has `8,493`
  nodes, `21,514` edges and `481` communities; platform docs has `1,946`
  nodes, `4,360` edges and `147` communities after one successful retry.

- Catasto bulk anagrafica routing completed: the former
  `app.modules.catasto.routes.anagrafica` monolith is now a compatible package
  facade over 11 responsibility-oriented modules. The 13 operations retain
  their method, path, order, endpoint name and legacy module declaration.
- The isolated OpenAPI document is byte-identical at 11 paths, SHA-256
  `c71647faeb8d71d05aa65ca2847e4ede74a2c2e4a4521e5a8a23afa8e9ff4709`.
  Facade forwarding also preserves direct helper imports and monkeypatches.
- Coverage is `100%`: `1,791/1,791` statements and `634/634` branches with
  `285` focused tests. Ruff check/format, compileall, diff check and all `66`
  code-quality tests pass.
- Metrics move from one file at LOC `3,486`, 122 callables, cognitive
  sum/max `2,087/363` and cyclomatic sum/max `1,354/135` to 12 files at
  aggregate LOC `3,943`, 125 callables, cognitive `2,101/363` and cyclomatic
  `1,367/135`; maximum file LOC is `712`. The aggregate increases are facade,
  import and independently scanned callback overhead, not a complexity
  reduction.
- The result is `REORGANIZED_AND_CHARACTERIZED`. A follow-up hardened move
  matching for unique qualified names from removed paths; all moved callables
  are now associated with their legacy metrics, including the seven whose AST
  fingerprints changed at modular boundaries. A second follow-up restored the
  exact pre-change layout of 49 AST-identical callable segments and rebuilt the
  remaining 10 from the legacy layout while proving AST equivalence with the
  modular runtime. The ratchet now passes with `findings: []`; baseline,
  thresholds and exceptions remain unchanged.
- Graphify was refreshed after code and docs changes: Catasto has `1,117`
  nodes, `2,674` edges and `52` communities; backend has `8,668` nodes,
  `21,972` edges and `483` communities; platform docs has `1,953` nodes,
  `4,380` edges and `144` communities.

Next action: stop this slice. Select any further router or service hotspot as a
new independent unit; do not start `gis/services.py` automatically.

## Final verification (2026-09-06)

- Frontend API: `811` tests; `1,263/1,263` statements, `826/826` branches,
  `420/420` functions and `1,195/1,195` lines on the 16 extracted runtime
  files. Targeted ESLint has no errors and 11 existing unused-helper warnings
  in generated/domain characterization tests.
- Backend routers: Utenze `89` tests (`870/870`, `220/220`), Network `68`
  tests (`1,405/1,405`, `452/452`), Presenze `241` tests (`2,292/2,292`,
  `696/696`), Me `48` selected tests (`369/369`, `70/70`), GIS `73` selected
  tests (`272/272`, `24/24`) and Catasto `285` tests (`1,791/1,791`,
  `634/634`). Each coverage run used a separate data file/process.
- `make quality-test` passes with `66` tests. Runtime/new-test Ruff check,
  format check, compileall and `git diff --check` pass.
- The global TypeScript check is currently blocked only by the concurrent
  `presenze/festivita/page.tsx` change (`HTMLArticleElement`), outside this
  slice. The global complexity/style ratchets remain blocked by concurrent
  Elaborazioni/worker changes and legacy whole-file style debt. The remaining
  API ratchet entries are metrics already present byte-for-byte at
  `main@c15f4e7a` before extraction; baseline, thresholds and exclusions were
  not changed to absorb them.
