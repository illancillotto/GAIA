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
- console dedicata controllo economico: `frontend/src/app/ruolo/controlli-capacitas/page.tsx`
- lista avvisi con drilldown coerente su `anno` e `comune`: `frontend/src/app/ruolo/avvisi/page.tsx`
- lista particelle con filtri operativi anche su `match_status` e `match_reason`: `frontend/src/app/ruolo/particelle/page.tsx`

Backend:
- `GET /ruolo/stats`
- `GET /ruolo/stats/particelle`
- `GET /ruolo/stats/comuni?anno=YYYY`
- `GET /ruolo/stats/analytics?anno=YYYY`
- `GET /ruolo/stats/capacitas-check?anno=YYYY`
- `GET /ruolo/stats/capacitas-check/comuni?anno=YYYY`
- `GET /ruolo/stats/capacitas-check/export?anno=YYYY`

## Console `Controlli Capacitas`

La console dedicata ha lo scopo di trasformare il confronto `ruolo vs Capacitas` in una vista di lavoro, non solo in un widget di dashboard.

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

Nota di hardening:
- il backend riusa la stessa espressione SQLAlchemy per `SELECT` e `GROUP BY` nei breakdown aggregati (`analytics`, `capacitas-check/comuni`) per evitare `GroupingError` PostgreSQL sui `coalesce(...)`

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
- test pagina avvisi con applicazione dei filtri `anno/comune`
- test pagina particelle con applicazione dei filtri `match_status/match_reason`

## Evoluzioni consigliate

- export CSV dei sottoinsiemi aperti dai grafici
- confronto tra due annualità
- vista heatmap `anno x comune`
