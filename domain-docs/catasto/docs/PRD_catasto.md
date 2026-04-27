# PRD — GAIA Catasto

> Stato documento
> Documento di dominio allineato alla struttura reale del repository al 22 aprile 2026.
> Il codice resta la fonte primaria in caso di divergenza:
> `backend/app/modules/catasto/`, `backend/app/services/catasto_*`, `frontend/src/app/catasto/`, `frontend/src/components/catasto/`.

## Scopo

`catasto` e il dominio GAIA dedicato a dati e documenti catastali.

Nel repository attuale il modulo non coincide piu con il runtime operativo delle lavorazioni massive: batch, credenziali, CAPTCHA, richieste singole e monitoraggio esecutivo sono stati spostati in `elaborazioni`.

Questo PRD descrive quindi il perimetro reale di `catasto` oggi:

- dizionario comuni catastali
- archivio documenti catastali
- consultazione e dettaglio dei documenti
- anagrafica territoriale `cat_*` per distretti, particelle, utenze irrigue e anomalie
- distinzione esplicita tra catasto catastale ufficiale e catasto consortile operativo
- import Capacitas Fase 1 e basi geospaziali PostGIS
- ricerca anagrafica da riferimenti catastali, singola e massiva
- workflow anagrafica e lookup massivo chiusi fino a Fase 5 sul perimetro corrente
- dettaglio particella arricchito con vista del catasto consortile e storico occupazioni
- superfici frontend dedicate alla navigazione del patrimonio documentale

## Obiettivi di prodotto

Obiettivi correnti del dominio:

- offrire un archivio consultabile dei documenti catastali prodotti dalle lavorazioni
- rendere i documenti ricercabili per metadati catastali e intervallo temporale
- permettere download singolo e download multiplo in ZIP
- esporre un dizionario comuni riusabile dai flussi applicativi che producono o interrogano dati catastali
- mantenere `catasto` come dominio dati separato dal runtime esecutivo

Obiettivi non piu interni al dominio `catasto`:

- orchestrazione batch
- gestione credenziali SISTER
- gestione CAPTCHA
- monitoraggio realtime delle esecuzioni
- richieste singole o massive come workflow operativo

Queste responsabilita vivono nel dominio `elaborazioni`.

## Perimetro funzionale attuale

### 1. Dizionario comuni

Il dominio espone una base comuni catastali usata per:

- lookup applicativo
- validazione input nei workflow a monte
- gestione amministrativa dei comuni censiti

### 2. Archivio documenti catastali

Il dominio espone un archivio documentale con:

- lista documenti
- ricerca per testo libero
- filtri per comune, foglio, particella e date
- dettaglio documento
- download PDF
- download ZIP di selezioni multiple

### 3. Frontend di consultazione

Il frontend `catasto` oggi non e una dashboard operativa completa.

Le superfici attive sono:

- pagina dominio placeholder
- archivio documenti
- dettaglio documento

Le route `catasto` che puntavano ai flussi operativi sono mantenute come redirect o compatibilita verso `elaborazioni`.

## Architettura canonica

GAIA usa backend unico, frontend unico e database unico.

Superfici canoniche del dominio `catasto`:

- router backend: `backend/app/modules/catasto/router.py`
- route backend: `backend/app/modules/catasto/routes.py`
- modelli re-export: `backend/app/modules/catasto/models.py`
- schemi re-export: `backend/app/modules/catasto/schemas.py`
- servizi dominio: `backend/app/services/catasto_comuni.py`, `backend/app/services/catasto_documents.py`
- frontend dominio: `frontend/src/app/catasto/`
- componenti frontend dominio: `frontend/src/components/catasto/`

Vincoli architetturali:

- `catasto` non e il runtime operativo delle visure
- il worker `modules/elaborazioni/worker/` resta un componente tecnico condiviso ma non definisce il perimetro di questo PRD
- il runtime operativo vive nel modulo `elaborazioni`
- i dati del dominio `catasto` convivono nel database condiviso con gli altri moduli

## Modello dati di riferimento

Entita di dominio oggi rilevanti per `catasto`:

- `catasto_comuni`
- `catasto_documents`
- `cat_import_batches`
- `cat_schemi_contributo`
- `cat_aliquote`
- `cat_distretti`
- `cat_distretto_coefficienti`
- `cat_particelle`
- `cat_particelle_history`
- `cat_utenze_irrigue`
- `cat_intestatari` (legacy, non piu fonte primaria per le ricerche massime anagrafiche)
- `cat_capacitas_intestatari`
- `cat_anomalie`

Distinzione semantica obbligatoria:

- `cat_particelle` e `cat_particelle_history` rappresentano la particella catastale ufficiale proveniente da shapefile / servizi Agenzia Entrate-Territorio
- `cat_utenze_irrigue` rappresenta oggi una fotografia annuale del ruolo Capacitas 0648/0985 e identifica chi paga / usa realmente l'acqua in una specifica annualita
- `cat_capacitas_intestatari` rappresenta gli intestatari proprietari / aventi titolo estratti dallo scrape Terreni Capacitas e collegati, quando possibile, all'anagrafica GAIA
- `ana_persons` rappresenta il dato anagrafico corrente normalizzato in GAIA; `ana_person_snapshots` conserva lo storico puntuale dei cambiamenti nel tempo
- le ricerche massive `comune/foglio/particella/intestatari` devono leggere gli intestatari correnti da `ana_persons` quando il CF e collegabile, non da `cat_intestatari`
- il dominio non deve piu trattare `cat_utenze_irrigue` come semplice “appendice del ruolo”: il file Capacitas contiene gia il primo livello del catasto consortile reale
- il catasto consortile reale e distinto dal catasto catastale: una particella catastale puo essere utilizzata da un soggetto diverso dal proprietario, puo essere gestita in affitto verbale, mezzadria, divisione familiare o suddivisa in piu porzioni irrigue operative

Nota di integrazione territoriale:

- il campo applicativo `cod_comune_capacitas` usato oggi nei flussi Catasto/Capacitas contiene il codice numerico sorgente scambiato da Capacitas
- il mapping da `codice catastale comune` dello shapefile a questo codice Capacitas non deve essere hardcoded nel service, ma derivato dal dataset di riferimento del dominio
- il dataset di riferimento locale mantiene anche il `codice catastale` e il `codice comune ufficiale` per evitare derive semantiche tra naming storico e anagrafica amministrativa reale
- il valore `0` non va trattato come codice comune valido: indica un mapping mancante e va considerato anomalia tecnica o dato incompleto
- prima di aggiungere nuovi comuni o nuove sorgenti shapefile, aggiornare il dataset di riferimento e i test di integrazione, non il SQL inline
- la tabella `cat_comuni` e la sorgente canonica per l'anagrafica comuni; `cat_particelle`, `cat_particelle_history` e `cat_utenze_irrigue` referenziano il comune tramite `comune_id`
- nelle particelle territoriali `superficie_mq` mantiene il significato di superficie catastale sorgente; la superficie derivata dai poligoni viene salvata separatamente in `superficie_grafica_mq`
- `superficie_grafica_mq` viene ricalcolata da PostGIS sulla geometria normalizzata in `EPSG:4326` tramite trasformazione metrica a `EPSG:3003`, cosi da evitare ambiguita tra dato amministrativo e dato GIS
- nel catasto consortile derivato da `Capacitas Terreni`, GAIA puo correggere il comune canonico nei casi storici noti `Arborea/Terralba`, mantenendo comunque il comune sorgente Capacitas come dato tracciato e consultabile

### Catasto consortile operativo

Per il Consorzio la realta operativa non coincide sempre con la sola intestazione catastale.

Casi da supportare:

- proprietario catastale diverso dal soggetto che paga l'annualita consortile
- affitto verbale o formale
- divisione di fatto tra fratelli, parenti, aziende o soci
- mezzadria / utilizzo condiviso
- particella catastale suddivisa in piu porzioni irrigue reali con una o piu bocchette / utenze
- variazioni storiche dell'utilizzatore reale per anno o per voltura

Conseguenza di modello:

- `cat_particelle` resta il layer catastale ufficiale
- va introdotto un layer dati ulteriore per il catasto consortile reale, collegato ma non sovrapposto alla particella catastale
- il file `R2025-090-IRR_Particelle_0648_0985_260416.xlsx` e da considerare sorgente primaria annuale del catasto consortile lato ruolo/acqua, non solo import contabile
- il recupero arricchito da Capacitas sezione Terreni deve integrare storico, titoli, porzioni irrigue, eventi di voltura e dati di riordino fondiario

Entita correlate ma governate dal runtime `elaborazioni`:

- `catasto_credentials`
- `catasto_connection_tests`
- `catasto_batches`
- `catasto_visure_requests`
- `catasto_captcha_log`

Regola pratica:

- se l'entita serve a consultazione, archivio o metadatazione del patrimonio catastale, resta nel perimetro di questo PRD
- se l'entita serve a orchestration, execution o monitoraggio runtime, va documentata in `elaborazioni`

### Dataset comuni di riferimento

Il dominio Catasto usa un dataset applicativo locale:

- `backend/app/modules/catasto/data/comuni_istat.csv`

Questo dataset contiene per ogni comune:

- `cod_istat`
  codice numerico sorgente usato oggi da Capacitas nei join applicativi del dominio
- `codice_catastale`
  codice catastale alfabetico del comune, usato tipicamente negli shapefile
- `codice_comune_formato_numerico`
  codice comune ufficiale numerico
- `codice_comune_numerico_2017_2025`
  variante numerica ufficiale ISTAT/Province usata negli estratti amministrativi recenti

Vincoli:

- non usare `codice_comune_formato_numerico` al posto di `cod_istat` senza un refactor esplicito di schema e join
- non duplicare il mapping in costanti Python o `CASE` SQL
- tutte le validazioni e i mapping shapefile devono dipendere dallo stesso dataset
- nelle response API e nel frontend preferire `cod_comune_capacitas` per evitare l'equivoco con il codice ISTAT ufficiale
- nell'import shapefile il codice catastale comune va letto prima da `CODI_FISC` o varianti equivalenti del layer sorgente; `CFM` e `NATIONALCA` restano solo fallback di compatibilita

## API di dominio correnti

### Comuni

- `GET /catasto/comuni`
- `POST /catasto/comuni`
- `PUT /catasto/comuni/{comune_id}`

Note:

- `POST` e `PUT` sono endpoint amministrativi

### Documenti

- `GET /catasto/documents`
- `GET /catasto/documents/search`
- `POST /catasto/documents/download`
- `GET /catasto/documents/{document_id}`
- `GET /catasto/documents/{document_id}/download`

### Fase 1 territoriale

- `POST /catasto/import/capacitas`
- `GET /catasto/import/history`
- `GET /catasto/import/{batch_id}/status`
- `GET /catasto/import/{batch_id}/report`
- `GET /catasto/distretti/`
- `GET /catasto/distretti/{distretto_id}`
- `GET /catasto/distretti/{distretto_id}/kpi`
- `GET /catasto/distretti/{distretto_id}/geojson`
- `GET /catasto/particelle/`
- `GET /catasto/particelle/{particella_id}`
- `GET /catasto/particelle/{particella_id}/history`
- `GET /catasto/anomalie/`

### Fase 4 anagrafica

- `POST /catasto/elaborazioni-massive/particelle`

Note:

- la funzionalità è solo in modalità massiva: accetta file `.xlsx` o `.csv` lato frontend e normalizza il payload verso il backend
- il match restituisce dati catastali, entrambe le superfici (`superficie_mq` catastale e `superficie_grafica_mq` GIS), ultima utenza, intestatari disponibili e top anomalie
- la vista risultati anagrafica espone anche `CCO` e `denominazione` dell'ultima utenza quando disponibili
- il filtro per nome comune usa l'anagrafica canonica `cat_comuni` come fallback applicativo e non dipende solo dal campo denormalizzato `cat_particelle.nome_comune`
- la risoluzione intestatari e `locale-first`: legge prima `ana_persons` / `ana_subjects`
- se l'intestatario manca localmente ma la particella ha riferimenti Capacitas ricostruibili, il backend usa un fallback live su `rptCertificato.aspx` e `dettaglioAnagrafica.aspx`
- il fallback live aggiorna o crea l'anagrafica corrente locale dell'intestatario
- il flusso massivo non recupera lo storico remoto completo Capacitas: quello resta nel modulo `elaborazioni/capacitas`

Vincoli infrastrutturali:

- la Fase 1 richiede PostgreSQL con estensione PostGIS disponibile
- nello stack locale Docker il servizio `postgres` usa un'immagine `postgis/postgis`
- le migration `cat_*` non sono compatibili con SQLite e vanno validate su PostgreSQL reale

## Evoluzione pianificata

Linea di evoluzione approvata per il dominio:

1. mantenere `cat_particelle` come anagrafica catastale ufficiale immutata nel suo significato
2. introdurre entita dedicate al catasto consortile reale e alle sue porzioni irrigue
3. usare il file Capacitas 0648/0985 come seed annuale del rapporto tra particella catastale e utilizzatore reale
4. aggiungere in `elaborazioni/capacitas` un recupero automatico dalla sezione Terreni di inVOLTURE per acquisire:
   - storico righe per foglio/particella
   - schede `rptCertificato`
   - dettaglio terreno `dettaglioTerreno`
   - dati di riordino (`R.F.`, `Maglia`, `Lotto`)
   - segnali di porzione irrigua e operazioni di frazionamento/affitto/voltura
5. consolidare questi dati in un modello storico consultabile lato Catasto/Consorzio

Riferimento tecnico dedicato:

- `domain-docs/catasto/docs/CATASTO_CONSORTILE.md`

## Frontend corrente

Route `catasto` realmente utili al dominio:

- `/catasto`
- `/catasto/archive`
- `/catasto/documents`
- `/catasto/documents/[id]`
- `/catasto/import`
- `/catasto/distretti`
- `/catasto/distretti/[id]`
- `/catasto/particelle`
- `/catasto/particelle/[id]`
- `/catasto/anomalie`
- `/catasto/ricerca-anagrafica`

Comportamento attuale:

- le pagine Fase 1 usano un wrapper frontend condiviso con navigazione di dominio uniforme
- `/catasto` e la dashboard Fase 1 del dominio
- `/catasto/archive?view=documents` e la superficie principale per l'archivio
- `/catasto/documents` reindirizza all'archivio documenti
- `/catasto/documents/[id]` mostra il dettaglio documento
- `/catasto/import` espone il wizard upload -> polling -> report anomalie
- il wizard import gestisce sia il completamento positivo sia il fallimento del batch con esposizione dell'errore applicativo
- il report import espone anche una sintesi batch da `report_json` con anno campagna, righe, distretti e comuni rilevati
- la pagina import espone anche uno storico dei batch recenti con filtro per stato, limite risultati, contatori e riapertura del report
- la pagina import espone inoltre un audit summary dei batch Capacitas con conteggi per stato e timestamp dell'ultimo completato
- `/catasto/import/[id]` espone il dettaglio dedicato di un batch con metadati, preview, contatori e lista anomalie
- il segmento frontend `/catasto` monta la navigation shell di dominio nel layout dedicato, non nel singolo wrapper pagina
- `/catasto/distretti` e `/catasto/distretti/[id]` coprono KPI e drill-down per distretto
- dalla dashboard `/catasto` il click su un distretto apre un workspace rapido in modale; da li i dettagli particella restano embedded senza sidebar completa e con navigazione indietro interna
- la modale di dettaglio particella usata dalla ricerca anagrafica espone anche il blocco di catasto consortile per consultazione rapida
- `/catasto/particelle` e `/catasto/particelle/[id]` coprono lookup e dettaglio con utenze/anomalie
- `/catasto/anomalie` espone la lista operativa con aggiornamento stato
- `/catasto/ricerca-anagrafica` espone ricerca singola e bulk da riferimenti catastali con preview dei match
- nelle liste e nei dettagli particella il frontend distingue esplicitamente `Sup. catastale` e `Sup. grafica` per evitare di sovraccaricare l'unico dato storico `superficie_mq`
- il dettaglio distretto embedded espone export diretti `CSV`, `XLS`, `PDF` sulla vista corrente e usa righe particella cliccabili per il drill-down
- `/catasto/ricerca-anagrafica` include export CSV/XLSX dell'elaborazione massiva
- il workflow mutativo sulle anomalie (`PATCH`) è riservato ad admin/super_admin, mentre la consultazione resta disponibile agli utenti Catasto attivi
- il flusso anagrafica e coperto anche da E2E browser dedicato oltre che da test backend e smoke frontend

## Stato fasi

Stato sintetico del modulo `catasto` sul perimetro oggi presente nel repository:

- Fase 1
  completata: import Capacitas, distretti, particelle, anomalie, wizard import e basi geospaziali PostGIS
- Fase 2
  completata sul perimetro attuale: hardening tecnico, integrazione shapefile/PostGIS, fixture workbook e smoke frontend
- Fase 3
  completata sul perimetro attuale: audit import, summary batch, dettaglio batch e permessi piu stretti sul workflow anomalie
- Fase 4
  completata: ricerca anagrafica singola e massiva con router backend, pagina frontend e test backend dedicati
- Fase 5
  completata sul perimetro corrente: E2E browser della ricerca anagrafica, affinamento stati UI, accessibilita input file e chiusura del workflow anagrafica end-to-end

Backlog residuo oltre la Fase 5 attuale:

- osservabilita piu ricca del dominio Catasto/Anagrafica
- eventuale reporting massivo piu strutturato
- ulteriori fixture territoriali e casi edge se il dominio si espande oltre il perimetro oggi modellato

Route `catasto` mantenute per compatibilita ma non piu canoniche:

- `/catasto/new`
- `/catasto/new-batch`
- `/catasto/new-single`
- `/catasto/batches`
- `/catasto/batches/[id]`
- `/catasto/settings`
- `/catasto/capacitas`

Queste route reindirizzano o riusano componenti del runtime `elaborazioni`.

## Integrazione con Elaborazioni

`catasto` dipende dal fatto che il runtime `elaborazioni` produca documenti e metadata compatibili con l'archivio.

Interazioni principali:

- `elaborazioni` usa `catasto_comuni` per lookup e validazione
- i documenti generati dalle lavorazioni vengono esposti dal dominio `catasto`
- il frontend operativo e in `frontend/src/app/elaborazioni/`, ma l'output documentale resta consultabile da `catasto`

Documentazione correlata:

- `domain-docs/elaborazioni/docs/ELABORAZIONI_REFACTOR_PLAN.md`
- `domain-docs/elaborazioni/docs/SISTER_debug_runbook.md`

## Stato attuale del modulo

Il modulo `catasto` oggi non e vuoto, ma e ridotto a un perimetro di dominio piu stretto rispetto allo storico:

- backend attivo per comuni e documenti
- frontend attivo per archivio e dettaglio documenti
- dashboard principale ancora volutamente minimale
- workflow operativi demandati a `elaborazioni`

## Regole di manutenzione documentale

- usare questo PRD per cambi a comuni, documenti, archivio e superfici di consultazione `catasto`
- non usare questo PRD per descrivere batch, credenziali, CAPTCHA o richieste runtime
- per cambi ai workflow operativi aggiornare la documentazione in `domain-docs/elaborazioni/docs/`
- se una route `catasto` esiste solo come compatibilita o redirect, dichiararlo esplicitamente nei documenti
