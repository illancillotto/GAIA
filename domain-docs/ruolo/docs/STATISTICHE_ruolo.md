# Statistiche Ruolo

## Obiettivo

La pagina `Ruolo / Statistiche` deve fornire una lettura operativa del ruolo consortile, non solo un riepilogo numerico.  
L'operatore deve poter:

- capire rapidamente l'andamento delle annualità
- distinguere problemi anagrafici da problemi catastali
- identificare i comuni più rilevanti o più critici
- aprire direttamente le liste di lavoro coerenti con il dato osservato

## Superficie funzionale attuale

Frontend:
- route: `frontend/src/app/ruolo/stats/page.tsx`
- console principale calcolo ruolo: `frontend/src/app/ruolo/calcolo-gaia/page.tsx`
- console tecnica audit: `frontend/src/app/ruolo/controlli-capacitas/page.tsx`
- lista avvisi con drilldown coerente su `anno` e `comune`: `frontend/src/app/ruolo/avvisi/page.tsx`
- lista particelle con filtri operativi anche su `match_status` e `match_reason`: `frontend/src/app/ruolo/particelle/page.tsx`

Backend:
- `GET /ruolo/stats`
- `GET /ruolo/stats/particelle`
- `GET /ruolo/stats/comuni?anno=YYYY`
- `GET /ruolo/stats/analytics?anno=YYYY`
- `GET /ruolo/stats/calcolo-gaia?anno=YYYY`
- `GET /ruolo/stats/calcolo-gaia/export?anno=YYYY`
- `GET /ruolo/stats/capacitas-check?anno=YYYY`
- `GET /ruolo/stats/capacitas-check/comuni?anno=YYYY`
- `GET /ruolo/stats/capacitas-check/export?anno=YYYY`

## Console `Calcolo ruolo`

La console `Calcolo ruolo` e la vista operativa principale per capire se il ruolo pubblicato e coerente con tre sorgenti distinte:

- `Ruolo inCASS`: importi letti dal partitario del ruolo pubblicato salvato in `ana_payment_notices.raw_detail_json`
- `Excel Capacitas`: importi `0648` e `0985` presenti nel file Excel importato nel batch Capacitas attivo
- `Calcolo GAIA`: ricalcolo interno da `imponibile_sf * aliquota_0648/0985` sulle righe Capacitas attive
- righe anomale che spiegano gran parte del gap

Espone:
- KPI con `Ruolo inCASS`, `Calcolo GAIA`, `Excel Capacitas`, gap `inCASS/GAIA` e gap `Excel/GAIA`
- tabella per `CF/P.IVA` con importi dei tre mondi nello stesso payload
- diagnosi operativa (`Priorita ruolo`, `Priorita GAIA`, `Priorita Excel`, `Allineato`)
- segnale `Guidato da anomalie` quando almeno il 95% del gap `Excel/GAIA` nasce da righe gia marcate anomale
- drilldown `Apri calcolo` con breakdown per comune, righe particella per particella e anteprima delle righe Excel Capacitas
- export CSV della console con valori `Ruolo inCASS`, `Calcolo GAIA`, `Excel Capacitas`, diagnosi e stato confronto

Regole:
- il payload `calcolo-gaia` e autonomo: contiene gia valori ruolo, stato confronto e diagnosi; il frontend non deve ricostruirli appoggiandosi alla console audit
- il confronto economico usa solo `0648` e `0985`
- `0668` resta visibile in summary ma non entra nel delta verso Excel Capacitas/GAIA
- `anomalous_only=true` filtra solo i casi davvero guidati da anomalie, non tutte le posizioni con una riga anomala

## Console `Audit Capacitas`

La console audit conserva lo scopo di trasformare il confronto `ruolo vs Capacitas` in una vista tecnica di lavoro, non solo in un widget di dashboard.

Espone:
- KPI su delta totale, delta `0648`, delta `0985`, `0668` informativo
- mismatch per `CF/P.IVA` con drilldown diretto su `Ruolo / Avvisi`
- breakdown per `comune` con drilldown territoriale sugli avvisi
- export CSV degli scostamenti

Regole:
- il confronto economico usa solo `0648` e `0985`
- `0668` resta visibile ma non entra nel delta Capacitas
- la chiave primaria di confronto e il `codice fiscale / partita IVA` normalizzato
- il breakdown per comune e aggregato e serve a orientare la bonifica, non sostituisce il dettaglio anagrafico
- il breakdown per comune normalizza le denominazioni territoriali prima del merge: `FRAZIONE*COMUNE` confluisce in `COMUNE`, il casing viene uniformato, e gli alias noti come `SILI -> ORISTANO` e `SAN NICOLO D'ARCIDANO -> SAN NICOLO ARCIDANO` sono aggregati. Il payload espone anche le denominazioni sorgenti `source_comuni_ruolo` e `source_comuni_capacitas` per audit.

Nota di hardening:
- il backend riusa la stessa espressione SQLAlchemy per `SELECT` e `GROUP BY` nei breakdown aggregati (`analytics`, `capacitas-check/comuni`) per evitare `GroupingError` PostgreSQL sui `coalesce(...)`
- la console `calcolo-gaia` riporta direttamente anche il lato `ruolo`, per evitare falsi “nessun confronto disponibile” dovuti al fatto che `capacitas-check` nasce come lista mismatch e puo essere filtrata o limitata

## Dati esposti da `/ruolo/stats/analytics`

Per una singola annualità il payload unifica:

- `particelle_summary`
  - totale particelle
  - particelle collegate al catasto
  - particelle non collegate
  - particelle classificate `suppressed` da AdE
- `tributi_breakdown`
  - 0648 manutenzione
  - 0985 irrigazione
  - 0668 istituzionale
- `match_status_breakdown`
  - stato del collegamento catastale
- `match_reason_breakdown`
  - motivi principali del mancato match
- `distretto_breakdown`
  - concentrazione delle particelle per distretto
- `coltura_breakdown`
  - concentrazione delle particelle per coltura
- `comuni`
  - importi
  - numero avvisi
  - numero partite
  - numero particelle
  - residuo non collegato al catasto

## Grafici e strumenti disponibili

### Trend storico annualità

Visualizza:
- barre stacked `collegati / non collegati`
- linea del `totale_euro`

Serve a leggere:
- crescita o riduzione del carico annuale
- qualità del collegamento anagrafico nel tempo

### Focus annualità

Card operative per l'anno selezionato:
- avvisi
- qualità catasto
- importo complessivo

Drilldown disponibili:
- `Apri avvisi dell'anno`
- `Apri avvisi orfani`
- `Apri tutte le particelle`
- `Apri particelle non collegate`

### Qualità del collegamento catastale

Visualizza:
- distribuzione per `match_status`
- elenco leggibile dei bucket principali

Serve a separare:
- dato già conciliato
- residuo tecnico da bonificare

### Peso economico dei tributi

Visualizza:
- importo per codice tributo `0648`, `0985`, `0668`

Serve a capire quali voci pesano davvero nell'anno osservato.

### Cause principali del mancato match

Visualizza:
- top `match_reason` sulle particelle senza collegamento

Serve a orientare bonifiche e analisi sul residuo.

### Top comuni

Visualizza:
- totale economico per comune
- residuo non collegato

Ogni riga espone drilldown verso:
- `avvisi`
- `particelle non collegate`
- `tutte le particelle`

### Top distretti / Top colture

Visualizzano la composizione tecnica del ruolo per l'anno selezionato.

## Note implementative

- `num_avvisi` nel breakdown per comune conta gli avvisi distinti, non le partite
- `num_partite` e `num_particelle` sono esposti separatamente per evitare letture ambigue
- la pagina `avvisi` ora legge anche i filtri `anno` e `comune`, quindi i drilldown statistici sono coerenti

## Copertura minima attesa

Backend:
- test su `GET /ruolo/stats/comuni`
- test su `GET /ruolo/stats/analytics`

Frontend:
- test pagina statistiche con link di drilldown
- test pagina `calcolo-gaia` con apertura modal di dettaglio
- test pagina avvisi con applicazione dei filtri `anno/comune`
- test pagina particelle con applicazione dei filtri `match_status/match_reason`

## Evoluzioni consigliate

- export CSV dei sottoinsiemi aperti dai grafici
- confronto tra due annualità
- vista heatmap `anno x comune`
