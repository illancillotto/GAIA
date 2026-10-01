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
- `notice_code`: codice esatto dell'avviso (es. `SYN-N0121`), non codice utenza
- `subject_id`
- `tax_year`
- `status`
- `account_code`
- `limit`

Scope: `ruolo.read`

I filtri di `search_role_notices` sono combinati con AND. `account_code`
identifica un'utenza (es. `SYN-A0121`), non un avviso: non sostituire un campo
con l'altro. Zero risultati valgono solo per i filtri effettivamente applicati.

## `get_role_notice`

Input: `notice_id`

Scope: `ruolo.read`

Non espandere automaticamente tutti i record collegati.

## `get_payments_by_notice`

Per una domanda basata sul codice avviso: chiamare `search_role_notices` con
`notice_code`, poi usare l'`id` UUID del risultato come `notice_id`. Non dedurre
UUID o codice utenza dal codice avviso; seguire `next_cursor` se presente.

Input:
```json
{"notice_id":"uuid","limit":20}
```

Scope: `ruolo.read`

## `get_role_lines_by_notice`

Input: `notice_id` UUID, `limit` default 50/max 100, `cursor` facoltativo.
Scope: `ruolo.read`. Restituisce soltanto righe dell'avviso con FK particella,
importi e provenance; non espande automaticamente le particelle.
Necessario al contratto di integrazione avviso → righe → particella.

## Paginazione runtime v1

Ogni tool di ricerca o relazione accetta un `cursor` facoltativo e restituisce
`next_cursor`; ordinamento per UUID, scope/filtri/dataset/principal invarianti.
I get atomici non sono paginati. Cursori fuori contesto sono `INVALID_ARGUMENT`.
Gli omonimi restano liste di risultati da disambiguare dall'agente/utente:
nessun matching automatico, quindi `AMBIGUOUS_MATCH` e riservato a futuri
lookup univoci, non viene usato dalle ricerche v1.

## Tool rinviati nel runtime

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
