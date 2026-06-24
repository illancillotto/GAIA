# Delivery Point Mapping Shortlist 2026-06-24

## Stato

- Letture collegate: `44016 / 47105`
- Mapping manuali live inseriti: `7`
- Distretti con residuo piu alto:
  - `28`: `1004`
  - `24`: `864`
  - `31`: `315`
  - `35`: `237`

## Export allegati

- [delivery-point-mapping-candidates-distretto-28-2026-06-24.csv](/home/cbo/CursorProjects/GAIA/domain-docs/catasto/docs/delivery-point-mapping-candidates-distretto-28-2026-06-24.csv)
- [delivery-point-mapping-candidates-distretto-24-2026-06-24.csv](/home/cbo/CursorProjects/GAIA/domain-docs/catasto/docs/delivery-point-mapping-candidates-distretto-24-2026-06-24.csv)

Questi export elencano, per ogni `source_point_code` non collegato:

- numero righe residue
- `record_kind`
- matricole residue
- candidati GIS per match `exact`, `strip_suffix`, `dotted`, `alpha_suffix`
- eventuali candidati da `COD_CONT`

## Distretto 28

Osservazione:

- I casi residui sono quasi tutti `operator_activity` o `dismissed_point`.
- I codici base esistono spesso in entrambi i sottodistretti `28_1D_1L` e `28_1D_2L`.
- Senza validazione umana, il collegamento automatico resta ambiguo.
- L'export completo contiene `380` codici sorgente distinti per `1004` righe residue.
- Su `380` codici, `328` risultano `ambiguous_subdistrict`.
- Non emergono nuovi candidati utili da `COD_CONT` sui residui del `28`.

Candidati da validare manualmente, ordinati per frequenza e con target scelto solo come ipotesi di lavoro:

| source_point_code | record_kind | rows | candidate_strategy | candidate_distretto | candidate_point_code | note |
| --- | --- | ---: | --- | --- | --- | --- |
| `13_1_1` | `operator_activity` | 3 | `exact` | `28_1D_1L` | `13_1_1` | esiste anche in `28_1D_2L` |
| `13_1_1_A` | `operator_activity` | 3 | `strip_suffix` | `28_1D_1L` | `13_1_1` | esiste anche in `28_1D_2L` |
| `13_1_1_B` | `operator_activity` | 3 | `strip_suffix` | `28_1D_1L` | `13_1_1` | esiste anche in `28_1D_2L` |
| `14_1_11` | `operator_activity` | 3 | `exact` | `28_1D_1L` | `14_1_11` | esiste anche in `28_1D_2L` |
| `14_1_11_E` | `operator_activity` | 3 | `strip_suffix` | `28_1D_1L` | `14_1_11` | esiste anche in `28_1D_2L` |
| `14_1_1_A` | `operator_activity` | 3 | `strip_suffix` | `28_1D_1L` | `14_1_1` | esiste anche in `28_1D_2L` |
| `14_1_2` | `operator_activity` | 3 | `exact` | `28_1D_1L` | `14_1_2` | esiste anche in `28_1D_2L` |
| `14_1_4_A` | `operator_activity` | 3 | `strip_suffix` | `28_1D_1L` | `14_1_4` | esiste anche in `28_1D_2L` |
| `14_1_5` | `dismissed_point` | 3 | `exact` | `28_1D_1L` | `14_1_5` | esiste anche in `28_1D_2L` |
| `14_1_5_B` | `operator_activity` | 3 | `strip_suffix` | `28_1D_1L` | `14_1_5` | esiste anche in `28_1D_2L` |
| `14_1_6` | `dismissed_point` | 3 | `exact` | `28_1D_1L` | `14_1_6` | esiste anche in `28_1D_2L` |
| `14_1_6_C` | `operator_activity` | 3 | `strip_suffix` | `28_1D_1L` | `14_1_6` | esiste anche in `28_1D_2L` |
| `14_1_7` | `operator_activity` | 3 | `exact` | `28_1D_1L` | `14_1_7` | esiste anche in `28_1D_2L` |
| `14_1_7_C` | `operator_activity` | 3 | `strip_suffix` | `28_1D_1L` | `14_1_7` | esiste anche in `28_1D_2L` |
| `14_1_7_D` | `operator_activity` | 3 | `strip_suffix` | `28_1D_1L` | `14_1_7` | esiste anche in `28_1D_2L` |
| `15_11_2` | `operator_activity` | 3 | `exact` | `28_1D_1L` | `15_11_2` | esiste anche in `28_1D_2L` |
| `17_1_1` | `operator_activity` | 3 | `exact` | `28_1D_1L` | `17_1_1` | esiste anche in `28_1D_2L` |
| `17_1_2` | `operator_activity` | 3 | `exact` | `28_1D_1L` | `17_1_2` | esiste anche in `28_1D_2L` |
| `18_1_1` | `operator_activity` | 3 | `exact` | `28_1D_1L` | `18_1_1` | esiste anche in `28_1D_2L` |
| `19_1_1` | `meter_reading` | 3 | `exact` | `28_1D_1L` | `19_1_1` | esiste anche in `28_1D_2L` |

## Distretto 24

Osservazione:

- I residui restanti sono dominati da `operator_activity`.
- L'export completo contiene `302` codici sorgente distinti per `864` righe residue.
- Su `302` codici, `289` sono `operator_activity`.
- Non risultano candidati `exact`, `strip_suffix`, `dotted` o `alpha_suffix`.
- Restano solo `4` casi con `meter_match_present`, ma tutti deboli e con salto di famiglia:
  - `9E.1_1-1D` -> `24:9E.1_1-1B`
  - `11E_3-28D` -> `24:11E_4`
  - `7E.3_1-29D` -> `24:7E.3_1-28D`
  - `7E.4_1-26C` -> `24:7E.4_1-27C`
- Non sono emersi nuovi candidati manuali con confidenza alta comparabile a quelli gia applicati.

## Operativita consigliata

1. Validare manualmente il lato corretto (`28_1D_1L` o `28_1D_2L`) per la shortlist del distretto `28`.
2. Usare prima il CSV del `28` per spuntare in blocco i codici realmente associati a `1L` o `2L`.
3. Inserire i mapping via endpoint `POST /catasto/meter-readings/{reading_id}/delivery-point-mapping`.
4. Rieseguire `backend/scripts/backfill_delivery_point_manual_mappings.py` se servono riallineamenti batch.
