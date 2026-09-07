# GAIA Complexity Report

- Commit: `3d4bbeb18ebe39b2db142d004a39f418018c44b7`
- Files: `1320`
- Callables: `18080`
- Violations: `4515` (`2064` error, `2451` warning)

## Top callable

| Path | Symbol | Line | Cog | Cyc | LOC | Nest | Params |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `frontend/src/app/presenze/giornaliere/page.tsx` | `PresenzeGiornalierePage` | 813 | 577 | 482 | 2314 | 3 | 0 |
| `frontend/src/features/organigramma/organigramma-workspace.tsx` | `OrganigrammaWorkspace` | 1550 | 477 | 363 | 1779 | 3 | 1 |
| `frontend/src/components/elaborazioni/capacitas-workspace.tsx` | `ElaborazioniCapacitasWorkspace` | 528 | 472 | 416 | 2631 | 2 | 1 |
| `frontend/src/components/elaborazioni/settings-workspace.tsx` | `ElaborazioniSettingsWorkspace` | 345 | 404 | 336 | 1580 | 2 | 1 |
| `frontend/src/app/utenze/[id]/page.tsx` | `DetailContent` | 214 | 393 | 306 | 1909 | 2 | 1 |
| `frontend/src/app/catasto/anomalie/page.tsx` | `CatastoAnomaliePageContent` | 175 | 390 | 342 | 2109 | 2 | 0 |
| `backend/app/modules/operazioni/routes/analytics.py` | `fuel_analytics` | 338 | 366 | 208 | 402 | 4 | 5 |
| `backend/app/modules/operazioni/routes/analytics.py` | `anomalies_analytics` | 1102 | 365 | 160 | 388 | 4 | 5 |
| `backend/app/modules/catasto/routes/anagrafica/execution.py` | `execute_bulk_search_payload` | 50 | 363 | 68 | 320 | 10 | 3 |
| `frontend/src/app/catasto/gis/page.tsx` | `CatastoGisPage` | 303 | 338 | 302 | 1911 | 4 | 0 |
| `frontend/src/app/elaborazioni/page.tsx` | `ElaborazioniPage` | 239 | 309 | 255 | 1421 | 2 | 0 |
| `backend/app/modules/catasto/routes/anagrafica/exports.py` | `_build_bulk_export_rows` | 265 | 281 | 135 | 114 | 3 | 2 |
| `frontend/src/app/me/me-page-content.tsx` | `MePageContent` | 347 | 271 | 256 | 1133 | 2 | 1 |
| `backend/app/services/elaborazioni_bonifica_sync.py` | `_run_bonifica_sync_background` | 354 | 269 | 47 | 232 | 13 | 3 |
| `frontend/src/components/elaborazioni/bonifica-sync-workspace.tsx` | `ElaborazioniBonificaSyncWorkspace` | 332 | 259 | 202 | 835 | 4 | 1 |
| `frontend/src/components/catasto/gis/MapContainer.tsx` | `MapContainer` | 444 | 252 | 173 | 967 | 3 | 1 |
| `frontend/src/app/presenze/collaboratori/[id]/page.tsx` | `PresenzeCollaboratoreDetailPage` | 100 | 233 | 212 | 1600 | 2 | 0 |
| `frontend/src/components/elaborazioni/batch-detail-workspace.tsx` | `ElaborazioneBatchDetailWorkspace` | 52 | 222 | 182 | 762 | 3 | 1 |
| `frontend/src/app/presenze/export/page.tsx` | `PresenzeExportPage` | 266 | 209 | 172 | 1097 | 3 | 0 |
| `backend/app/modules/network/router/helpers/traffic.py` | `_build_network_statistics_summary` | 264 | 209 | 109 | 226 | 4 | 2 |
