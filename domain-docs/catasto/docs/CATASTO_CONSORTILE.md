# Catasto Consortile — Disegno Operativo

> Stato documento
> Documento tecnico di dominio introdotto il 23 aprile 2026 per chiarire la distinzione tra catasto catastale ufficiale e catasto consortile reale.

## Premessa

Nel dominio GAIA Catasto esistono due piani informativi diversi:

- catasto ufficiale
  dato catastale proveniente da shapefile / Agenzia Entrate-Territorio
- catasto consortile reale
  dato operativo del Consorzio: chi usa realmente l'acqua, chi paga l'annualita, come una particella viene suddivisa o gestita nel tempo

Questi due piani non devono essere fusi in un'unica tabella.

## Stato attuale

Oggi il sistema dispone di:

- `cat_particelle`
  particella catastale ufficiale
- `cat_particelle_history`
  storico SCD2 della particella catastale ufficiale
- `cat_utenze_irrigue`
  righe annuali importate dal file Capacitas 0648/0985

Osservazione chiave:

- il file `R2025-090-IRR_Particelle_0648_0985_260416.xlsx` non e solo un file “ruolo”
- e gia una sorgente annuale del catasto consortile reale, perche indica il soggetto che utilizza e paga l'acqua

## Problema di dominio

Una particella catastale puo avere:

- piu proprietari catastali
- un utilizzatore reale diverso dal proprietario
- una suddivisione di fatto tra soggetti differenti
- porzioni irrigue operative
- variazioni di voltura e di utilizzo nel tempo
- riferimenti a riordino fondiario (`R.F.`, `Maglia`, `Lotto`)

Quindi:

- la particella catastale ufficiale non basta per rappresentare la realta consortile
- l'utilizzatore reale non puo essere dedotto solo dall'intestatario catastale
- il modello deve supportare storico, porzioni, relazioni molti-a-molti e snapshot annuali

## Principi di modellazione

1. `cat_particelle` mantiene solo il significato catastale ufficiale.
2. Il catasto consortile vive in tabelle separate ma collegate a `cat_particelle`.
3. Il file Capacitas 0648/0985 crea o aggiorna il legame tra particella catastale e utilizzatore reale per una annualita.
4. La sezione Terreni di inVOLTURE arricchisce questo legame con storico, titoli, terreni, riordino e dettagli operativi.
5. I dati recuperati da Capacitas vanno storicizzati come snapshot, non sovrascritti distruttivamente.

## Modello dati implementato al 23 aprile 2026

Le seguenti tabelle sono ora presenti nel DB e nel runtime backend:

- `cat_consorzio_units`
- `cat_consorzio_unit_segments`
- `cat_consorzio_occupancies`
- `cat_capacitas_terreni_rows`
- `cat_capacitas_certificati`
- `cat_capacitas_intestatari`
- `cat_utenza_intestatari`
- `cat_capacitas_terreno_details`

Copertura reale di questo step:

- creazione/aggiornamento dell'unita consortile a partire dalla riga Terreni Capacitas
- creazione di segmenti solo quando il dettaglio terreno espone dati di riordino
- creazione di una occupancy `capacitas_terreni` collegata a `CatUtenzaIrrigua` quando il `CCO` e l'anno coincidono
- salvataggio snapshot grezzi e normalizzati per ricerca, certificato e dettaglio terreno
- salvataggio intestatari del certificato in snapshot strutturato con link opzionale a `ana_subjects`
- popolamento di `cat_utenza_intestatari` per tenere traccia di tutti gli intestatari proprietari collegati a una specifica `cat_utenze_irrigue` in una determinata annualita
- aggiornamento dell'anagrafica corrente direttamente su `ana_persons` quando lo storico Capacitas espone dati piu ricchi del certificato sintetico
- salvataggio di ogni record storico remoto Capacitas in `ana_person_snapshots` con flag `is_capacitas_history`
- scrittura di snapshot differenziali aggiuntivi in `ana_person_snapshots` quando lo scrape storico modifica il profilo corrente
- esposizione lato Catasto del dato anagrafico corrente da `ana_persons` e dello storico da `ana_person_snapshots` quando esiste il collegamento
- tracciamento del comune sorgente Capacitas separato dal comune canonico GAIA
- esposizione nel dettaglio frontend della particella di:
  - unita consortili collegate
  - comune reale GAIA
  - comune sorgente Capacitas
  - stato di risoluzione comune
  - occupazioni storiche / correnti

Non ancora implementato:

- consolidamento multi-sorgente o deduplica avanzata
- scheduler esterno o coda dedicata separata dal backend applicativo per job massivi su portafogli di particelle

Aggiornamento operativo 27 aprile 2026:

- `POST /catasto/elaborazioni-massive/particelle` non e piu solo un lookup locale
- il flusso rimane locale-first su `cat_particelle`, `cat_utenze_irrigue`, `ana_subjects`, `ana_persons`
- quando una particella ha parametri Capacitas ricostruibili (`CCO`, `COM`, `PVC`, `FRA`, `CCS`) ma l'intestatario non e presente localmente, il backend apre live `rptCertificato.aspx`
- dagli intestatari del certificato usa `IDXANA` + `IDXESA` per aprire `dettaglioAnagrafica.aspx`
- il risultato massivo restituisce quindi gli intestatari correnti anche se prima non erano presenti in `ana_persons`
- il fallback live aggiorna l'anagrafica corrente locale; non importa automaticamente lo storico remoto completo, che resta un flusso separato
- nel JSON di match / export, `presente_in_catasto_consorzio` e vero se la particella ha almeno un'unita consortile attiva **oppure** una utenza di campagna collegata **oppure** intestatari noti (incluso arricchimento live); evita l'export \"non presente\" quando comune/foglio/particella e nominativi sono gia valorizzati
- export Excel elaborazioni massive: colonna `apri_involture` con formula `HYPERLINK` sulla stessa riga della URL in `link_involture` (testo \"Clicca qui\"); il CSV mantiene la colonna vuota (nessuna formula)
- il modulo `elaborazioni` espone ora anche un job dedicato di sync progressiva delle particelle GAIA:
  - fonte input: `cat_particelle` correnti gia presenti a DB
  - persistenza job: `capacitas_particelle_sync_jobs`
  - tracking per particella: `capacitas_last_sync_at`, `capacitas_last_sync_status`, `capacitas_last_sync_error`, `capacitas_last_sync_job_id`
  - politica di riesame:
    - di giorno rientrano soprattutto particelle non aggiornate nelle ultime `24h`
    - dopo le `19:00` la finestra di riesame scende a `6h` e il throttle tra richieste si accorcia

## Regola Arborea / Terralba

Caso reale emerso sul dominio:

- alcune particelle risultano ancora in Capacitas sul comune storico
- il catasto reale GAIA invece le censisce correttamente sull'altro comune
- i casi noti riguardano solo `Arborea` e `Terralba`

Regola implementata:

- durante il sync Terreni il sistema prova prima il match sul comune sorgente Capacitas
- se non trova la particella e il comune sorgente e `Arborea` o `Terralba`, prova automaticamente sull'altro comune della coppia
- se trova la particella sull'altro comune:
  - il comune canonico dell'unita consortile diventa quello reale di GAIA
  - i dati sorgente Capacitas vengono conservati in:
    - `source_comune_id`
    - `source_cod_comune_capacitas`
    - `source_codice_catastale`
    - `source_comune_label`
    - `comune_resolution_mode = swapped_arborea_terralba`

Conseguenza:

- GAIA mostra il dato territoriale reale
- il sistema non perde l'informazione storica/operativa che Capacitas lo riportava su un comune diverso
- nelle anomalie ruolo escluse dagli indici, i casi `cat_particella_match_reason = swapped_arborea_terralba`
  sono classificati con motivo dedicato `swapped_arborea_terralba` quando la particella corrente non ha distretto:
  non vanno confusi con il generico `senza_distretto` e richiedono verifica storico-catastale prima di qualunque correzione diretta.

## Modello dati proposto

### 1. Unita consortile

Entita logica che rappresenta il “bene consortile reale” su cui il Consorzio ragiona.

Proposta tabella:

- `cat_consorzio_units`

Campi chiave suggeriti:

- `id`
- `particella_id` FK verso `cat_particelle` nullable
- `comune_id`
- `cod_comune_capacitas`
- `sezione_catastale`
- `foglio`
- `particella`
- `subalterno`
- `descrizione`
- `source_first_seen`
- `source_last_seen`
- `is_active`

Nota:

- non sempre esiste corrispondenza 1:1 con la particella catastale
- una stessa particella catastale puo avere piu unita consortili se ci sono porzioni irrigue o gestioni separate

### 2. Porzione consortile / porzione irrigua

Serve per rappresentare frazionamenti reali, anche se non formalizzati a catasto.

Proposta tabella:

- `cat_consorzio_unit_segments`

Campi suggeriti:

- `id`
- `unit_id`
- `label`
- `segment_type`
  valori possibili: `full`, `porzione_irrigua`, `frazionamento_operativo`, `riordino_lotto`
- `surface_declared_mq`
- `surface_irrigable_mq`
- `riordino_code`
- `riordino_maglia`
- `riordino_lotto`
- `current_status`
- `notes`

### 3. Relazione utilizzatore reale / pagatore

Serve per dire chi usa realmente il bene in un dato periodo.

Proposta tabella:

- `cat_consorzio_occupancies`

Campi suggeriti:

- `id`
- `unit_id`
- `segment_id` nullable
- `subject_id` nullable verso anagrafica GAIA
- `cco`
- `fra`
- `ccs`
- `pvc`
- `com`
- `source_type`
  valori: `ruolo_0648_0985`, `capacitas_terreni`, `manuale`
- `relationship_type`
  valori: `proprietario`, `utilizzatore_reale`, `affittuario`, `mezzadro`, `comodatario`, `da_verificare`
- `valid_from`
- `valid_to`
- `is_current`
- `confidence`
- `notes`

### 4. Snapshot terreni Capacitas

Serve per non perdere lo storico restituito da `ricercaTerreni.aspx`.

Proposta tabella:

- `cat_capacitas_terreni_rows`

Campi suggeriti:

- `id`
- `search_key`
- `result_row_id`
  ID terreno Capacitas
- `cco`
- `fra`
- `ccs`
- `pvc`
- `com`
- `belfiore`
- `foglio`
- `particella`
- `sub`
- `anno`
- `voltura`
- `opcode`
- `data_reg`
- `superficie`
- `bac_descr`
- `row_visual_state`
  es. `current_black`, `historic_red`, `unknown`
- `raw_payload_json`
- `collected_at`

### 5. Snapshot scheda certificato

Proposta tabella:

- `cat_capacitas_certificati`

Campi suggeriti:

- `id`
- `cco`
- `fra`
- `ccs`
- `pvc`
- `com`
- `partita_code`
- `utenza_code`
- `utenza_status`
- `ruolo_status`
- `raw_html`
- `parsed_json`
- `collected_at`

### 5.b Snapshot intestatari certificato

Tabella introdotta:

- `cat_capacitas_intestatari`

Ruolo:

- conserva la fotografia sorgente degli intestatari letti dal certificato Terreni
- non e il master anagrafico corrente
- funge da snapshot tecnico/audit collegato alla singola acquisizione Capacitas
- se una sync successiva restituisce lo stesso payload certificato per lo stesso contesto (`CCO`, `COM`, `PVC`, `FRA`, `CCS`), GAIA riusa l'ultimo snapshot invece di crearne uno duplicato

### 5.c Intestatari annuali collegati all'utenza

Tabella introdotta:

- `cat_utenza_intestatari`

Ruolo:

- lega gli intestatari proprietari alla riga annuale `cat_utenze_irrigue`
- conserva il contesto storico della singola annualita (`anno_riferimento`, `data_agg`, `voltura`, `op`, `site`, `sn`)
- espone il collegamento al soggetto GAIA tramite `subject_id`
- usa `ana_persons` come fonte corrente e `ana_person_snapshots` come storico interrogabile

Principio operativo:

- `cat_utenze_irrigue` continua a rappresentare l'utilizzatore/pagatore annuale
- `cat_utenza_intestatari` rappresenta tutti gli intestatari proprietari noti per quella specifica utenza/anno
- i due concetti non devono essere fusi
- la persistenza applica una policy `replace` per `utenza_id + anno_riferimento`: ogni sync sostituisce il set annuale esistente con quello appena ricostruito
- il `CCO` da solo non e considerato sufficiente per il matching: serve sempre almeno `COM` Capacitas coerente, con `FRA` usata come ulteriore vincolo quando disponibile
- se il certificato non risolve una sola `cat_utenze_irrigue` target nel contesto corrente, GAIA non persiste link annuali per evitare associazioni massive errate
- l'endpoint `GET /catasto/particelle/{id}/consorzio` esclude dalla sezione `intestatari_proprietari` i record con titolo quota `0/0`, trattati come rumore non proprietario

Campi chiave:

- `certificato_id`
- `subject_id` nullable verso `ana_subjects`
- `idxana`
- `idxesa`
- `codice_fiscale`
- `denominazione`
- `data_nascita`
- `luogo_nascita`
- `residenza`
- `comune_residenza`
- `cap`
- `titoli`
- `deceduto`
- `raw_payload_json`
- `collected_at`

Regola:

- il dato Capacitas degli intestatari non deve essere scritto direttamente dentro `ana_persons`
- il primo scrape valido di un soggetto costituisce la baseline iniziale del profilo noto in GAIA, cioe l'"anno zero" da cui parte la storicizzazione
- prima viene salvato lo snapshot grezzo/normalizzato dell'intestatario
- poi, se esiste un match anagrafico su `codice_fiscale` o sul soggetto Capacitas gia noto, viene valorizzato `subject_id`
- quando il match aggiorna `ana_persons`, il cambiamento deve produrre uno snapshot in `ana_person_snapshots`
- nelle API Catasto il dato anagrafico mostrato all'utente deve uscire da `ana_persons`; lo snapshot Capacitas resta la traccia sorgente/origine

### 6. Snapshot dettaglio terreno / riordino

Proposta tabella:

- `cat_capacitas_terreno_details`

Campi suggeriti:

- `id`
- `result_row_id`
- `foglio`
- `particella`
- `sub`
- `riordino_code`
- `riordino_maglia`
- `riordino_lotto`
- `irridist`
- `raw_html`
- `parsed_json`
- `collected_at`

## Pipeline dati proposta

### Step 1 — seed annuale da file ruolo

Input:

- file `R2025-090-IRR_Particelle_0648_0985_260416.xlsx`

Output:

- `cat_utenze_irrigue`
- creazione/aggiornamento relazioni iniziali di occupazione reale

Regola:

- ogni riga e una evidenza annuale che un soggetto ha utilizzato e/o pagato una specifica particella per quell'anno

### Step 2 — arricchimento Capacitas Terreni

Input:

- ricerca `comune/frazione/sezione/foglio/particella`
- nei comuni dove la sezione catastale non coincide in modo banale con la lookup Capacitas, il backend puo applicare un mapping esplicito `comune + sezione -> frazione Capacitas` prima dei fallback euristici su comune/frazione
- caso storico `Terralba / sezione B`: la ricerca live Terreni su Capacitas deve poter interrogare `Arborea / frazione 31`, perche parte del catasto consortile risulta ancora registrato sul comune storico precedente
- nelle elaborazioni massive anagrafiche, se la particella e presente in `cat_particelle` ma non ha ancora legami consortili locali, il fallback live puo eseguire una sync Terreni mirata e salvare subito snapshot, unita consortili, occupancy e certificato, cosi il dataset locale si riallinea all'esito Capacitas trovato in tempo reale
- nelle elaborazioni massive anagrafiche, se una particella ha gia un `CCO` locale ma non esistono ancora le fonti minime per `link_involture`, il backend deve backfillare anche il certificato Capacitas e gli intestatari collegati, invece di limitarsi al solo match del `CCO`

Output:

- storico righe terreni
- scheda certificato
- dettaglio terreno
- dati riordino

Regola:

- per una particella possono esistere piu righe storiche
- tutte le righe vanno persistite
- il record visualmente corrente e solo una vista derivata, non l'unica verita da salvare

### Step 3 — consolidamento consortile

Output:

- unita consortile
- porzioni irrigue
- occupancies storicizzate
- legami a soggetti GAIA

## Import controllato Capacitas grid 2026

Scopo:

- importare il file Excel `catasto consortile` esportato da Capacitas come snapshot operativo 2026
- popolare solo tabelle consortili e snapshot raw
- non modificare mai `cat_particelle`

Sorgente:

- file reale usato in validazione locale: `ct0902026_grid (3).xlsx`
- il campo `CODICE` del file Excel corrisponde a `cat_consorzio_units.source_codice_catastale`
- il file rappresenta il catasto consortile Capacitas, non il catasto ufficiale GAIA

Tabelle coinvolte:

- `cat_consorzio_units`
- `cat_consorzio_occupancies`
- `cat_capacitas_grid_snapshots`
- `cat_capacitas_grid_rows`

Garanzie operative:

- `cat_particelle` resta invariata
- il dry-run non scrive su DB
- l'apply e idempotente sullo stesso file e sullo stesso `snapshot_year`
- le snapshot raw non vengono duplicate se `snapshot_year + file_hash` coincidono

Limiti di dominio da ricordare:

- il file Excel Capacitas puo contenere particelle obsolete, soppresse, frazionate, divise operativamente o fuori distretto
- il match con `cat_particelle` e quindi solo un collegamento al catasto ufficiale quando esiste un riscontro coerente
- in assenza di match ufficiale, l'unita consortile viene comunque salvata con i campi `source_*` Capacitas

Regola Arborea / Terralba nel grid 2026:

- si tenta prima il comune sorgente Capacitas
- se `Arborea` o `Terralba` non trovano match sul catasto ufficiale GAIA, si prova automaticamente l'altro comune
- se il match esiste sull'altro comune, i campi canonici puntano alla particella ufficiale GAIA
- i campi `source_*` preservano i valori originari Capacitas
- `comune_resolution_mode` viene valorizzato a `swapped_arborea_terralba`

Procedura locale:

- verificare che non esistano import attivi:
  - `docker compose exec -T backend pgrep -af import_capacitas_consorzio_grid.py`
- eseguire dry-run:
  - `docker compose exec -T backend python scripts/import_capacitas_consorzio_grid.py --xlsx-path '/home/cbo/Downloads/ct0902026_grid (3).xlsx' --snapshot-year 2026 --source-file 'ct0902026_grid (3).xlsx' --output-dir /tmp/gaia_capacitas_grid_import --dry-run`
- verificare il summary JSON e i contatori principali
- eseguire apply solo dopo la validazione:
  - `docker compose exec -T backend python scripts/import_capacitas_consorzio_grid.py --xlsx-path '/home/cbo/Downloads/ct0902026_grid (3).xlsx' --snapshot-year 2026 --source-file 'ct0902026_grid (3).xlsx' --output-dir /tmp/gaia_capacitas_grid_import --apply`
- rilanciare lo stesso apply per confermare l'idempotenza piena

Esito validazione locale del 4 luglio 2026:

- dry-run:
  - `rows_total=186017`
  - `unit_action_unit_created=151252`
  - `unit_action_unit_existing_exact=34024`
  - `unit_resolution_unit_swapped_arborea_terralba=1296`
  - `occupancy_created=34753`
  - `cat_particelle_unchanged=True`
- primo apply:
  - `rows_total=186017`
  - `unit_action_unit_created=131808`
  - `unit_action_unit_existing_exact=53310`
  - `unit_resolution_unit_swapped_arborea_terralba=1296`
  - `occupancy_created=159732`
  - `occupancy_existing_current=26246`
  - `cat_particelle_unchanged=True`
- apply ripetuto dopo fix di idempotenza:
  - atteso e verificato: `unit_action_unit_created=0`
  - atteso e verificato: `occupancy_created=0`
  - atteso e verificato: `raw_rows_inserted=0`
  - atteso e verificato: `cat_particelle_unchanged=True`

Nota di stabilizzazione:

- nel DB locale esistevano unita consortili duplicate storiche per alcune chiavi sorgente
- l'import grid 2026 ora considera alias logici tra unita duplicate e riusa le `occupancies` gia presenti invece di crearne di nuove sul duplicato
- questo rende stabile il re-run anche su database non perfettamente consolidati

Procedura server dopo validazione locale:

- eseguire backup completo del database prima di ogni `--apply` su server
- copiare o rendere disponibile il file Excel sul server in un path leggibile dal container/backend
- eseguire prima il dry-run sul server e archiviare il summary prodotto
- confrontare i contatori server con l'esito locale e con il contenuto del file
- eseguire `--apply` solo dopo validazione esplicita
- rieseguire lo stesso `--apply` una seconda volta per confermare `occupancy_created=0` e `raw_rows_inserted=0`

Esito validazione server del 4 luglio 2026:

- prerequisiti deploy:
  - backend server riallineato alle migration fino a `20260704_0900`
  - file Excel caricato in `/opt/gaia/runtime-data/imports/ct0902026_grid.xlsx`
  - backup DB completato prima del primo apply:
    - `/opt/gaia/backups/db/gaia-20260704-141119-pre-capacitas-grid-20260704.dump`
- dry-run server:
  - `rows_total=186017`
  - `unit_action_unit_created=151251`
  - `unit_action_unit_existing_exact=34025`
  - `unit_resolution_unit_swapped_arborea_terralba=1296`
  - `occupancy_created=34754`
  - `raw_rows_inserted=0`
  - `cat_particelle_unchanged=True`
- primo apply server:
  - `rows_total=186017`
  - `unit_action_unit_created=131807`
  - `unit_action_unit_existing_exact=53311`
  - `unit_resolution_unit_swapped_arborea_terralba=1296`
  - `occupancy_created=159732`
  - `occupancy_existing_current=26246`
  - `raw_rows_inserted=186017`
  - `cat_particelle_unchanged=True`
- secondo apply server per idempotenza:
  - `rows_total=186017`
  - `unit_action_unit_created=0`
  - `unit_action_unit_existing_exact=184716`
  - `unit_resolution_unit_swapped_arborea_terralba=1296`
  - `occupancy_created=0`
  - `occupancy_existing_current=185978`
  - `raw_rows_inserted=0`
  - `cat_particelle_unchanged=True`

Note operative sulla differenza locale/server:

- i contatori di dry-run e primo apply possono differire di poche unita rispetto al locale per effetto dello stato iniziale del DB server
- la validazione positiva e data da:
  - assenza di scritture su `cat_particelle`
  - riuso coerente di `cat_consorzio_units` e `cat_consorzio_occupancies`
  - `raw_rows_inserted=0` al secondo apply sullo stesso `snapshot_year + file_hash`
  - `occupancy_created=0` al secondo apply

Verifica test e coverage del 6 luglio 2026:

- test locali verdi:
  - `cd backend && python3 -m pytest tests/test_capacitas_consorzio_grid_import.py -q`
  - `cd backend && python3 -m pytest tests/test_incass_parsers.py tests/elaborazioni/capacitas/test_incass_partitario_parsing.py -q`
- coverage verificata sui file runtime dell'import:
  - `backend/app/services/capacitas_consorzio_grid_import.py`: `100%`
  - `backend/scripts/import_capacitas_consorzio_grid.py`: `100%`

## Regole applicative

1. `cat_particelle` non deve essere riscritta con dati di utilizzo reale.
2. Il proprietario catastale e l'utilizzatore reale devono poter coesistere.
3. Una particella con piu righe Capacitas nello stesso anno non e un errore: e storico consortile.
4. Il riordino fondiario va salvato come attributo strutturato.
5. Le porzioni irrigue vanno modellate come sotto-unita consortili, non come modifica distruttiva della particella catastale.

## Impatto architetturale

### Dominio `catasto`

Responsabilita:

- persistenza del catasto ufficiale
- persistenza del catasto consortile
- consultazione e comparazione tra i due livelli

### Dominio `elaborazioni`

Responsabilita:

- accesso a Capacitas
- scraping/estrazione da `ricercaTerreni`, `rptCertificato`, `dettaglioTerreno`
- salvataggio snapshot grezzi e normalizzati
- scheduling/job massivi di arricchimento

## Backlog minimo di implementazione

1. aggiungere modelli e migration per il catasto consortile
2. introdurre client `TerreniClient` in `backend/app/modules/elaborazioni/capacitas/apps/involture/`
3. parsare `ricercaTerreni.aspx` e `ajax/ajaxRicerca.aspx`
4. parsare `rptCertificato.aspx`
5. parsare `dettaglioTerreno.aspx`
6. salvare snapshot grezzi + campi strutturati
7. consolidare mapping `particella catastale -> unita consortile -> occupancies`
8. esporre UI Catasto con due viste:
   - catastale ufficiale
   - consortile reale

## Stato decisione

Decisione confermata:

- `cat_particelle` resta il catasto catastale ufficiale
- il catasto consortile reale viene modellato separatamente
- Capacitas Terreni e una sorgente primaria da integrare in `elaborazioni`
