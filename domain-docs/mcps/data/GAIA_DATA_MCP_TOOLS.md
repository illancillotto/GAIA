# GAIA Data MCP — catalogo tool v1

## Principi

- tool atomici;
- niente SQL libero;
- niente risposta finale;
- output ridotto;
- paginazione;
- provenance;
- scope.

## `search_subjects`

Input:
```json
{"query":"string","subject_type":"person|company|null","limit":10}
```

Scope: `utenze.read`

## `get_subject`

Input:
```json
{"subject_id":"uuid"}
```

Scope: `utenze.read`

## `search_irrigation_accounts`

Filtri:
- `account_code`
- `subject_id`
- `district_code`
- `campaign_year`
- `status`
- `limit`

Scope: `catasto.read`

## `get_irrigation_account`

Input: `account_id`

Scope: `catasto.read`

## `search_parcels`

Filtri:
- `municipality_code`
- `sheet`
- `parcel_number`
- `district_code`
- `crop`
- `limit`

Scope: `catasto.read`

## `get_parcel`

Input: `parcel_id`

Scope: `catasto.read`

## `get_accounts_by_parcel`

Input:
```json
{"parcel_id":"uuid","year":2026,"limit":20}
```

Scope: `catasto.read`

## `get_parcels_by_account`

Input:
```json
{"account_id":"uuid","year":2026,"limit":50}
```

Scope: `catasto.read`

## `search_role_notices`

Filtri:
- `subject_id`
- `tax_year`
- `status`
- `account_code`
- `limit`

Scope: `ruolo.read`

## `get_role_notice`

Input: `notice_id`

Scope: `ruolo.read`

Non espandere automaticamente tutti i record collegati.

## `get_payments_by_notice`

Input:
```json
{"notice_id":"uuid","limit":20}
```

Scope: `ruolo.read`

## Tool rinviati

Non introdurre inizialmente:
- `execute_sql`;
- `get_full_subject_context`;
- `search_everything`;
- tool che combinano automaticamente Docs/NAS/Trasparenza.

## Error model

- `INVALID_ARGUMENT`
- `NOT_FOUND`
- `AMBIGUOUS_MATCH`
- `PERMISSION_DENIED`
- `RESULT_LIMIT_EXCEEDED`
- `DATASET_UNAVAILABLE`
- `INTERNAL_ERROR`

## Provenance

```json
{
  "source":"gaia_synthetic_db",
  "entity":"syn_parcels",
  "record_id":"uuid",
  "dataset_version":"..."
}
```

## Hard caps iniziali

- search generiche: max 25;
- relazioni particella/utenza: max 100;
- righe avviso: max 100;
- pagamenti: max 50.
