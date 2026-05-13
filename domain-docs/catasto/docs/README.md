# GAIA Catasto Docs

## Scopo

Questa cartella contiene la documentazione del dominio `catasto` e i riferimenti collegati al runtime operativo oggi ospitato in `elaborazioni`.

Usare questo indice per capire rapidamente quali file sono:

- operativi
- storici
- file-ponte mantenuti per compatibilita

## Documenti operativi

- `PRD_catasto.md`
  Documento di riferimento per perimetro, architettura, API e stato corrente del dominio `catasto`.
  Include anche la Fase 1 territoriale `cat_*`, la ricerca anagrafica fino a Fase 5 e il requisito PostGIS.

## Documenti storici

- `archive/PROMPT_CODEX_catasto.md`
  Prompt storico del periodo di transizione `catasto` -> `elaborazioni`.
- `archive/PROMPT_CLAUDE_CODE_catasto.md`
  Prompt storico del periodo di transizione `catasto` -> `elaborazioni`.
- `archive/PROMPT_CLAUDE_CODE_frontend_restructure.md`
  Documento storico. Il refactor frontend descritto e gia stato completato e non va usato come prompt operativo corrente.

## File-ponte per compatibilita

- `ELABORAZIONI_REFACTOR_PLAN.md`
  Rimando compatibile al piano attuale in `domain-docs/elaborazioni/docs/ELABORAZIONI_REFACTOR_PLAN.md`.
- `SISTER_debug_runbook.md`
  Rimando compatibile al runbook tecnico attuale in `domain-docs/elaborazioni/docs/SISTER_debug_runbook.md`.

## Regole pratiche

- Per modifiche a comuni o documenti catastali, partire dal PRD operativo di questa cartella.
- Il perimetro oggi chiuso arriva fino alla Fase 5 del dominio Catasto corrente: prima di aprire nuove tranche, verificare il file di avanzamento in `progress/2026-04-22_catasto_phase_progress.md`.
- Per il mapping comuni di Catasto, usare sempre il dataset `backend/app/modules/catasto/data/comuni_istat.csv` come sorgente di verita del dominio.
- Negli shapefile territoriali, trattare `CODI_FISC` come sorgente primaria del codice catastale comune; usare `CFM` e `NATIONALCA` solo come fallback.
- Non assumere che `cod_comune_capacitas` nel codice Catasto coincida con il codice comune numerico ufficiale ISTAT moderno: e il codice numerico sorgente scambiato da Capacitas.
- Se serve il codice ufficiale, leggerlo esplicitamente dalle colonne dedicate del dataset di riferimento e non ricostruirlo via `CASE` hardcoded.
- La tabella di riferimento `cat_comuni` e la sorgente canonica per i comuni del dominio: contiene `codice_catastale`, `cod_comune_capacitas`, codici ufficiali e metadata amministrativi.
- Nelle tabelle operative preferire `comune_id` come riferimento stabile; mantenere `cod_comune_capacitas` e `codice_catastale` solo come codici sorgente o di tracciabilita quando servono.
- Nella ricerca anagrafica particelle/intestatari, i link e gli intestatari Capacitas non vanno risolti con il solo `CCO`: usare sempre anche il contesto `COM/PVC/FRA/CCS` quando disponibile, perche diversi `CCO` risultano riusati su comuni o frazioni diverse.
- La stessa regola vale per la sync `Terreni`, per la sync singola/progressiva delle particelle e per i refetch certificati: quando GAIA collega snapshot/intestatari Capacitas a `cat_utenze_irrigue`, il perimetro minimo di sicurezza e `CCO + COM + FRA`; se il frontend prova ad aprire `rptCertificato` con un `CCO` localmente ambiguo senza contesto sufficiente, il backend deve rispondere con conflitto esplicito invece di scegliere un certificato arbitrario.
- Nelle risposte anagrafiche sui subalterni storici, esporre un `CCO` non corrente solo come dato descrittivo e sempre insieme al contesto `COM/PVC/FRA/CCS` disponibile; il solo `CCO` non va mai usato come chiave di sync, link certificato o lookup intestatari.
- Per i sub del Catasto Consorzio, non assumere equivalenza tra maiuscole e minuscole: i valori possono essere inseriti manualmente dagli operatori e vanno trattati come chiavi distinte salvo regole dominio esplicite.
- Nell'aggiornamento distretti da Excel della pagina `catasto/import`, il lookup verso `cat_particelle` ignora volutamente `SUB`: il file puo contenere subalterni, ma `cat_particelle` viene trattata come anagrafica canonica della particella base, senza moltiplicare record distinti per subalterno in questo flusso.
- Nello stesso flusso `Aggiorna distretti`, alcuni valori `COMUNE` del tracciato sorgente rappresentano alias territoriali che implicano anche la sezione catastale. Mapping oggi supportati: `ORISTANO*ORISTANO -> Oristano/A`, `DONIGALA FENUGHEDU*ORISTANO -> Oristano/B`, `MASSAMA*ORISTANO -> Oristano/C`, `NURAXINIEDDU*ORISTANO -> Oristano/D`, `SILI'*ORISTANO -> Oristano/E`, `CABRAS -> Cabras/A`, `SOLANAS*CABRAS -> Cabras/B`, `OLLASTRA SIMAXIS -> Simaxis/A`, `SAN VERO CONGIUS*SIMAXIS -> Simaxis/B`, `SIMAXIS*SIMAXIS -> Simaxis/A`, `SAN NICOLO ARCIDANO -> San Nicolo d'Arcidano`.
- Nelle superfici frontend del batch `Distretti Excel`, i codici tecnici backend (`ALREADY_ALIGNED`, `MATCHED`, `NOT_FOUND`, `COMUNE_NOT_FOUND`, `INVALID_ROW`, `DUPLICATE_CONFLICT`) non devono essere mostrati tali e quali agli operatori. Regola stabile: backend espone codici/esiti canonici per API e test, frontend li traduce sempre in etichette parlanti e descrizioni brevi orientate all'utente.
- Nell'export anagrafico delle particelle con sub, i dati storici del sub non sono considerati utili come intestazione corrente. Se un sub non ha un `CCO` corrente proprio ma la particella base ha una posizione corrente affidabile, l'intestatario esportato puo essere derivato dalla particella base e va segnalato esplicitamente nelle note.
- Lo stesso export espone anche `stato_ruolo` e `stato_cnc` letti dallo snapshot certificato Capacitas coerente con il contesto `CCO/COM/PVC/FRA/CCS`; la colonna `note` resta in coda al file.
- Nell'import massivo particelle/intestatari, valori come `27 sez.B` o `23 sez.C svil.A` nel campo foglio vanno normalizzati separando `foglio` e `sezione` prima del lookup.
- Per le anomalie storiche Arborea/Terralba, non forzare alias locali per sezione (`Arborea C -> Terralba B`). Se il match locale non esiste, il fallback corretto e un lookup live Capacitas senza sezione: prima sul comune richiesto, poi sul comune alternativo (`Arborea <-> Terralba`) se il primo non restituisce risultati.
- Le particelle collegate dal Ruolo con `cat_particella_match_reason = swapped_arborea_terralba` devono restare consultabili come particelle GAIA reali, ma la UI deve segnalare il comune sorgente Capacitas/Ruolo diverso in `catasto/particelle/[id]` e nel popup/scheda GIS tramite il payload `swapped_capacitas`.
- Nella pagina `catasto/particelle`, il toggle "Solo particelle con anagrafica" deve essere attivo di default e applicare un filtro backend reale sulla presenza di almeno una `CatUtenzaIrrigua` collegata alla particella. Se l'utente effettua una ricerca puntuale per `foglio + particella`, la riga va comunque restituita anche senza anagrafica e il frontend deve evidenziare esplicitamente lo stato `Senza anagrafica`.
- Nella stessa pagina `catasto/particelle`, il filtro `Codice fiscale / Intestatario` deve eseguire una ricerca parziale unificata sui campi dell'utenza irrigua (`cat_utenze_irrigue.codice_fiscale`, `denominazione`) e sugli intestatari annuali collegati (`cat_utenza_intestatari.codice_fiscale`, `partita_iva`, `denominazione`), cosi da trovare anche prefissi come le prime lettere del codice fiscale.
- Nella scheda `catasto/particelle/[id]`, il blocco `Utilizzatore / pagatore annualita` deve mostrare la `partita` Capacitas nel formato `CCO/FRA/CCS`, non il solo `CCO`. `FRA` e `CCS` vanno derivati dal contesto occupazione `COM/PVC/FRA/CCS` quando disponibile; `cod_frazione` e solo fallback.
- Nella modal di dettaglio particella (lista `catasto/particelle`, ricerca anagrafica, pannello GIS), lo stesso blocco utenze deve consentire l’apertura del quick view soggetto (`UtenzeSubjectQuickViewDialog`, iframe `/utenze/{id}?embedded=1`), il link certificato Capacitas con la stessa logica di contesto occupazione usata in `particelle/[id]` e l’avvio rapido della `visura per soggetto` tramite runtime `elaborazioni/SISTER` direttamente dalla scheda embedded.
- Nello stesso blocco, l'API puo esporre `subject_id` e `subject_display_name` risolti dalla GAIA anagrafica a partire dall'identificatore fiscale della riga utenza. Regola stabile: il collegamento e valido solo se l'identificatore corrisponde in modo univoco a un singolo soggetto locale; in caso di ambiguita il frontend non deve aprire una scheda utenza arbitraria.
- Nella pagina `catasto/particelle` il toggle "Visualizza solo particelle a ruolo" deve applicare un filtro backend reale, non un filtro locale sul dataset gia caricato: la sorgente preferita e `ruolo_particelle.cat_particella_id = cat_particelle.id`; per compatibilita con import storici non ancora backfillati resta valido il fallback via `catasto_parcels` su codice catastale, foglio, particella e subalterno/base.
- La dashboard `catasto` deve usare l'endpoint aggregato `GET /catasto/dashboard/summary` per mostrare KPI precisi su import, particelle, utenze, anomalie e distretti; evitare somme lato frontend dei KPI distretto e non mostrare metriche etichettate come stime quando il dato puo essere calcolato lato backend.
- La pagina `catasto/anomalie` non deve restare una semplice tabella di triage: deve comportarsi come console operativa con summary per famiglia, sezione esplicita `Code di lavoro` e wizard specialistici. Workflow oggi abilitati: correzione `codice_fiscale / partita IVA` per `VAL-02-cf_invalido` e `VAL-03-cf_mancante`, riallineamento `comune` per `VAL-04-comune_invalido` usando il mapping di `cat_comuni`, e riallineamento `particella` per `VAL-05-particella_assente`, con update della `CatUtenzaIrrigua` e chiusura delle anomalie aperte collegate.
- Nell'elaborazione massiva `catasto/elaborazioni-massive`, per il tracciato `Comune/Foglio/Particella/Intestatari` il campo `comune` deve accettare tre forme equivalenti: nome comune, `cod_comune_capacitas` numerico oppure codice catastale/Belfiore (es. `A357`).
- Nella pagina `catasto/gis`, i controlli di `Archivio layer salvati` per riempimento e opacita devono riflettere prima di tutto lo stato reale del layer gia caricato in mappa; se l'utente li usa su un layer non ancora caricato, il frontend deve caricare automaticamente quel layer in mappa applicando subito il valore scelto.
- Nella `Vista estesa` di `catasto/gis` i controlli operativi devono stare in una sidebar destra dedicata, cosi la mappa conserva piu altezza utile sul comprensorio verticale: il menu `Layer visibili` deve restare disponibile con gli stessi toggle di distretti, particelle, riempimento e highlight della sidebar standard, mentre `Disegna area` va spostato fuori dall'header dentro la stessa sidebar.
- Nella pagina `catasto/gis` la vista iniziale deve privilegiare i `Distretti` come layer areale tematico colorato, con `Particelle` spento di default per evitare il reticolo particellare sull'intero comprensorio. Il filtro `Distretto` deve restare disponibile sia nella sidebar standard sia nella `Vista estesa`, cosi l'operatore puo isolare un distretto e decidere solo dopo se accendere il dettaglio particellare.
- Nella pagina `catasto/gis` il layout operativo deve comportarsi come una console GIS web: mappa a tutta altezza utile, toolbar flottante sopra la mappa e sidebar destra persistente per layer, import, archivio e risultati, evitando il precedente framing da card gestionale.
- Nella pagina `catasto/gis` l'operatore deve poter scegliere lo sfondo mappa dalla sidebar: `Mappa` usa OpenStreetMap, `Satellite` usa un layer raster imagery compatibile MapLibre, `Google Earth` usa Google Map Tiles API solo se e configurata `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`.
- Gli shapefile catastali particellari vanno importati dichiarando correttamente il sistema di riferimento sorgente: per RDN2008 / UTM zona 32N usare `EPSG:7791` come default operativo; `EPSG:3003` va usato solo per dati Monte Mario / Gauss-Boaga. Non correggere disallineamenti GIS con offset manuali lato frontend.
- Nella pagina `catasto/gis` l'header contenutistico standard (`GIS` + descrizione) va nascosto per recuperare spazio verticale; il contesto resta nella topbar e nella toolbar flottante della console.
- Nella pagina `catasto/gis` il click su una particella deve aprire una scheda contestuale React, non solo un popup HTML della mappa: la scheda deve mostrare dati base catastali, stato anomalie, riepilogo `ruolo_particelle` aggregato preferendo `cat_particella_id` e usando `catasto_parcels` come fallback storico, e deve consentire l'apertura diretta della `ParticellaDetailDialog`.
- Il layer `cat_particelle_current` pubblicato via Martin deve esporre anche `ha_ruolo`, cosi la mappa puo distinguere visivamente le particelle a ruolo senza introdurre un layer geometrico separato; il match ruolo/GIS deve preferire `ruolo_particelle.cat_particella_id` e usare `catasto_parcels` come fallback per righe storiche non ancora allineate.
- Il dettaglio ruolo nel popup GIS carica l'anno tributario corrente se presente; se manca, usa l'ultimo anno precedente disponibile per quella particella e mostra importi separati manutenzione/irrigazione/istruttoria oltre al totale.
- I distretti in mappa devono essere mostrati principalmente come fill colorato per `num_distretto`; l'outline tecnico `cat_distretti_boundaries` va tenuto nascosto quando il fill e attivo, per evitare che geometrie frammentate producano un reticolo simile alle particelle.
- La sidebar GIS deve esporre un pannello espandibile `Distretti irrigui`: elenco selezionabile caricato da `/catasto/distretti`, colore stabile per distretto, selezione che filtra/centra la mappa e azione per mostrare o nascondere il particellare solo sul distretto selezionato.
- Il popup/scheda particella del GIS deve mostrare anche il titolare corrente disponibile: preferire `cat_utenza_intestatari` con titolo visibile, mostrando denominazione e codice fiscale/partita IVA; se assente usare come fallback la riga `cat_utenze_irrigue` piu recente.
- Le particelle devono restare cliccabili anche quando il layer visuale `Particelle` e spento: usare un layer hitbox trasparente sopra `cat_particelle_current`, mantenendo il filtro distretto corrente.
- Il download vettoriale ufficiale Agenzia Entrate va gestito tramite WFS `CP:CadastralParcel` su bbox limitate, tracciando ogni download in `cat_ade_sync_runs` e salvando lo staging in `cat_ade_particelle`; il servizio usa `EPSG:6706` con ordine assi lat/lon, quindi il backend deve convertire in WKT lon/lat e riproiettare a `EPSG:4326`. Questa fonte non sovrascrive automaticamente `cat_particelle`.
- La dashboard `catasto` deve mostrare un avviso/popup quando il riepilogo backend `ade_alignment` rileva particelle nuove nello staging AdE o geometrie variate rispetto a `cat_particelle`; il popup deve indirizzare l'operatore al GIS/allineamento guidato, senza applicare modifiche automatiche.
- Il report di allineamento AdE deve essere calcolato per `run_id`: le particelle `mancanti_in_ade` sono valide solo nello scope bbox del download, mentre nuove, variate e ambigue derivano dai match catastali normalizzati.
- La pagina `catasto/gis` deve esporre un wizard/pannello `Allinea particelle AdE` che consente bbox manuale, bbox da area disegnata o bbox da distretto selezionato; il pannello avvia il download WFS, legge il report del `run_id` e mostra i contatori senza eseguire apply automatici.
- Nella sidebar GIS il pannello `Allinea comprensorio AdE` deve essere collassabile: di default resta compatto per risparmiare altezza utile, ma continua a mostrare stato del run e accesso rapido all'avvio.
- Il report AdE deve includere anche una preview GeoJSON delle differenze, caricata dal wizard come overlay mappa: nuove AdE, geometrie AdE variate, geometrie GAIA correnti corrispondenti e mancanti AdE devono essere distinguibili cromaticamente prima di qualunque apply.
- Prima di introdurre apply automatici, il backend espone una preview dry-run `POST /catasto/gis/ade-wfs/alignment-apply-preview/{run_id}` richiamabile dal wizard GIS: stima inserimenti, aggiornamenti geometria, soppressioni e impatti su utenze, unità consorzio, selezioni GIS e riferimenti ruolo senza modificare `cat_particelle`; i match ambigui restano esclusi.
- L'apply reale è esposto con `POST /catasto/gis/ade-wfs/alignment-apply/{run_id}` e richiede `confirm=true`: inserisce nuove particelle AdE risolvibili su `cat_comuni`, aggiorna le geometrie variate in-place scrivendo prima `cat_particelle_history` e abilita la soppressione dei mancanti solo con `allow_suppress_missing=true`. Nel wizard GIS l'azione standard è abilitata solo dopo dry-run, conferma testuale `APPLICA <run>` e assenza di match ambigui; non applica soppressioni.
- Per modifiche a batch, credenziali, CAPTCHA, richieste singole o avanzamento runtime, verificare sempre anche `domain-docs/elaborazioni/docs/`.
- Non usare i documenti storici come sorgente primaria per implementazioni nuove.
- Se un file viene mantenuto solo per compatibilita, segnalarlo esplicitamente nel blocco iniziale del documento.
- I file-ponte compatibili restano nella root di `docs/`; i documenti storici non piu operativi vanno spostati in `docs/archive/`.
