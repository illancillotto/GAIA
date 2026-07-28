# Ruolo inCASS - policy sync row avvisi

Data: `2026-07-28`

## Decisione

La griglia ricerca avvisi inCASS e' la fonte operativa corrente per stato pagamento e importi sintetici degli avvisi Capacitas.

Durante ogni sync inCASS, anche quando il job e' light e non scarica dettaglio, partitario o PDF, GAIA deve aggiornare sempre i campi normalizzati derivati dal row:

- `importo_carico`
- `importo_sgravio`
- `importo_riscosso`
- `importo_residuo`
- `importo_riporto`
- `importo_rateizzato`
- `importo_annullato`
- `stato_code`
- `stato_label`
- `data_scadenza`
- `data_pagamento`
- `ultimo_invio`
- `lista_id`
- `lista_descrizione`
- recapito sintetico del destinatario

Il payload raw del row resta salvato in `ana_payment_notices.raw_row_json` per audit e diagnosi, ma non deve essere l'unico punto in cui il dato aggiornato e' disponibile.

## Payload pesanti

Dettaglio avviso, partitario, PDF e mailing sono payload pesanti. Nelle sync light possono essere preservati:

- `detail_info_html`
- `detail_info_text`
- `pdf_links_json`
- `raw_detail_json`

Questa separazione consente di mantenere aggiornati residuo, riscosso, stato e date senza riscaricare sempre il dettaglio.

## Backfill 2026-07-28

Le migration `20260728_1100` e `20260728_1110` riallineano i record storici gia' presenti:

- `20260728_1100_backfill_incass_notice_amounts_from_raw_row.py`: copia gli importi normalizzati da `raw_row_json`.
- `20260728_1110_backfill_incass_notice_row_metadata.py`: copia `DataPagamento`, `DataScad` e `UltimoInvio` dai row raw, gestendo anche date con orario.

Verifica locale post-backfill sul corpus inCASS:

- mismatch `DataPagamento`: `0`
- mismatch `UltimoInvio`: `0`
- record raw row verificati: `144537`

## Caso guida

Per `RMNMRC66E30G113G`, avviso `020240001597450` anno `2024`, il row inCASS riportava gia':

- `Riscosso`: `-3272.03`
- `Differenza`: `4908`
- `DataPagamento`: `12/06/2026`
- `UltimoInvio`: `ORD`

Prima della correzione questi valori erano aggiornati in `raw_row_json`, ma gli importi normalizzati potevano restare ai valori precedenti nelle sync light.
