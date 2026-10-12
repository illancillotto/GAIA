# Emissione anomalie dei veicoli dismessi — R58

Il refactoring locale mantiene in `routes/analytics.py` la selezione dei mezzi
dismessi, le query dei rifornimenti e delle sessioni, il caricamento dei mezzi
referenziati e i due cicli di emissione. Query, bind, ordine, filtri temporali,
autorizzazione, conteggi e ordinamento stabile non cambiano.

`services/inactive_vehicle_anomalies.py` contiene due mapper tipizzati verso
`AnomalyItem` e una politica condivisa per l'etichetta: targa, codice, ID mezzo.
L'ID di fallback resta lazy; il codice viene riletto per i dettagli, senza
cache. Nei rifornimenti la conversione dei litri precede tale rilettura.
I rifornimenti precedono le sessioni anche quando queste hanno timestamp minore.
Nessun nuovo commit/rollback, retry o servizio esterno.

Caratterizzazione: 37 nuovi casi persistiti/HTTP, 457 casi storici conservati
e 49 contratti puri aggiuntivi. Questi ultimi verificano input transitori/null,
letture, short-circuit ed eccezioni; non simulano raggiungibilità della route.
543 test PASS nei due gate distinti, zero skip. Coverage full-file dei quattro
runtime: 100% statement/branch; il mapper ha 8 statement e nessun arco branch
misurato, quindi le letture condizionali sono protette dai contratti espliciti.
Restano soltanto i due guard difensivi storici della route, quattro righe escluse.

Metriche misurate: callable principale cognitive238→221, cyclomatic112→104,
LOC320→302; aggregate possedute cognitive723→711, cyclomatic501 invariata.
Decisioni fisiche342→340. LOC file route1193→1179, route+mapper1193→1212:
l'aumento di19 è dichiarato, non contato come miglioramento LOC globale.
Ratchet contro main55a PASS, zero finding nuovi; baseline e soglie invariati.
Report: `reports/code-quality/SLICE_R58_INACTIVE_VEHICLES_2026-10-12.md`.
