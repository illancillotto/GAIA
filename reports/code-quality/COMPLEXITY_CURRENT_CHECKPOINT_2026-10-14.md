# GAIA — Current complexity checkpoint, not final certification

## Snapshot and measurement

Integration branch `refactor/complexity-campaign-20261008`, HEAD
`7f39510ab1ef1d4e531d8b12a4eb6b36f556cee4`; actual main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Historical initial audit remains
`55a1b1d35911451e018b662c2acc450bf5994ea2`, October 8, not October 7.

Fresh full scanner exit0, no parse/exception errors. Durable evidence root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/complexity-current-20261014/`.
Files `report.json`, `report.md`, `scan.log`, `scan-exit.txt` retained.
JSON SHA256 `85a007a127d3a5aedadd745485f185a354eea653f21f13f76c104ffaa37d0f1a`.
Subsequent R96 changes are test-only, outside the runtime scanner corpus.

| Official scope | Initial | Current | Raw delta |
| --- | ---: | ---: | ---: |
| Files |1665|1681|+16|
| Callables |20261|20360|+99|
| Error findings |1956|1920|-36 (-1.84%)|
| Warning findings |2758|2736|-22 (-0.80%)|
| All findings |4714|4656|-58 (-1.23%)|

Application excluding worker tests:1625files/19027callables, versus initial
1611/18940. These raw global deltas include intervening/concurrent history and
scope growth: they are **not** exclusively attributable to admitted campaign
slices. Findings overlap across metrics; they are not independent problem counts.
No new complexity reduction is attributed to the test-only R96 correction.

## Remaining extreme tail

Cognitive >300:3; >200:16; >100:55. Threshold buckets overlap.

| Callable | Current cognitive |
| --- | ---: |
| Utenze DetailContent |391|
| CatastoAnomaliePageContent |390|
| PresenzeGiornalierePage |360|
| ElaborazioniCapacitasWorkspace |298|
| CatastoGisPage |298|
| ElaborazioniSettingsWorkspace |280|
| MePageContent |271|
| ElaborazioniBonificaSyncWorkspace |259|
| MapContainer |246|
| PresenzeCollaboratoreDetailPage |233|
| anomalies_analytics |221|
| fuel_analytics |217|
| run_network_scan |195|

Complete ranking is in the JSON, not limited to this table. Extreme-tail
elimination and strategic reduction targets remain unmet. Further work must use
small behavior-preserving slices, full pertinent coverage and independent review.

## Gates and limits

R96 actual `make complexity-ratchet BASE_REF=main` exit0/findings[], against
actual merge-base a51a48dc; no base substitution. Baseline, thresholds, exclusions
and coverage policy unchanged. Global scanner counts do not imply
`complexity-check` PASS, complete test coverage or campaign completion.
Backend skips remain unverified. Native R97 pending independently reviewed
fresh binding; R95 PASS/FAIL remains historical and immutable.

Coordinator metadata inspection initially indexed `.files` as an array; jq
refused the query, then corrected object-key inspection confirmed these counts.
No scanner rerun or report modification resulted. No commit/main merge/push.
Global goal ACTIVE/INCOMPLETE.
