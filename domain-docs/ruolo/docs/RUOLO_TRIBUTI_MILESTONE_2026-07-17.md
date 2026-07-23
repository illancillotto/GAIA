# GAIA Ruolo - Milestone Sezione Tributi

Data: 2026-07-17

Aggiornamento: 2026-07-22

## Decisione architetturale

La gestione tributi viene implementata come sezione interna del modulo `ruolo`, non come modulo
GAIA separato.

Motivazione:

- il dominio applicativo e lo stesso degli avvisi a ruolo;
- il tracciamento pagamento ha come chiave operativa il `codice_cnc` / avviso;
- i dati necessari esistono gia nel read-model `ruolo_avvisi`, `ruolo_partite`,
  `ruolo_particelle`;
- i link CapaciTas e la generazione dei solleciti partono dagli avvisi a ruolo;
- la sezione deve mostrare anche avvisi non collegati ad Anagrafica GAIA, gia supportati dal
  modello `ruolo_avvisi.subject_id = NULL`.

Percorso frontend previsto:

- `/ruolo/tributi`
- `/ruolo/tributi/import-pagamenti`
- `/ruolo/tributi/solleciti`
- `/ruolo/tributi/[avvisoId]`

Prefisso API previsto:

- `/ruolo/tributi/...`

## Aggiornamento 2026-07-22 - gestori annualita tributo

La sezione Tributi ora gestisce una matrice configurabile per stabilire chi ha in carico le
annualita del tributo. La regola e necessaria per attribuire correttamente le somme dovute e per
preparare i successivi calcoli differenziati per soggetto gestore.

Configurazione iniziale:

- fino al 2017: `Agenzia delle Entrate`, policy `external_ade`;
- 2018-2021: `STEP - Agenzia recupero crediti`, policy `external_recovery`;
- dal 2022: `Consorzio/GAIA`, policy `internal_gaia`.

Nota sul confine 2022:

- la specifica operativa ricevuta contiene una sovrapposizione testuale sul 2022;
- GAIA configura il 2022 nella gestione diretta Consorzio/GAIA per evitare range sovrapposti;
- se il 2022 deve essere attribuito a STEP, l'operatore puo aggiornare i range dal pannello
  `Gestori annualita tributo` senza modifica codice.

Implementazione:

- nuova tabella `ruolo_tributi_year_managers` con range `year_from` / `year_to` aperti;
- validazione backend contro range attivi sovrapposti;
- seed iniziale in migration Alembic e fallback runtime per ambienti creati con `metadata.create_all`;
- endpoint `GET/POST/PUT/DELETE /ruolo/tributi/year-managers`;
- `GET /ruolo/tributi/avvisi` e `GET /ruolo/tributi/solleciti/candidates` accettano
  `manager_key`;
- lista, dettaglio tributo e wizard solleciti espongono il gestore annualita e la
  `calculation_policy`.

## Aggiornamento 2026-07-22 - wizard solleciti batch

La generazione dei solleciti non e piu trattata come operazione isolata sul singolo avviso.
Il flusso operativo principale e un wizard batch dentro `/ruolo/tributi`.

Decisioni confermate:

- chiave utenza: `codice_fiscale_raw` normalizzato;
- una utenza puo includere piu avvisi e piu anni;
- il wizard richiede una selezione esplicita delle annualita da includere nel nuovo avviso;
- default operativo attuale del wizard: annualita `2024` e `2025` quando l'anno di emissione
  corrente e `2026`;
- ordinamento candidature per nominativo e comune;
- selezione automatica delle utenze aperte con cartella NAS disponibile, con possibilita di
  selezione manuale tramite codice fiscale/P.IVA;
- output: un PDF per utenza, non un PDF globale;
- contenuto PDF: avviso di sollecito e partitario nello stesso documento;
- perimetro annualita: solo avvisi non saldati dal 2022 in poi;
- salvataggio: `{ana_subjects.nas_folder_path}/solleciti/{CF}_avviso_sollecito_{anni}.pdf`;
- batch e item restano tracciati anche se il PDF non viene generato, ad esempio per cartella NAS
  mancante o errore LibreOffice;
- invio email/PEC/SMS escluso dal perimetro corrente.

Regola archivio NAS per solleciti:

- se il soggetto GAIA collegato ha `nas_folder_path`, GAIA salva il PDF in quella cartella;
- se il soggetto GAIA esiste ma `nas_folder_path` e mancante, GAIA deriva il path canonico da
  `{UTENZE_NAS_ARCHIVE_ROOT|ANAGRAFICA_NAS_ARCHIVE_ROOT}/{lettera}/{nome_cartella}`;
- `nome_cartella` viene normalizzato per filesystem, troncato a 96 caratteri e completato con
  suffisso CF/P.IVA, ad esempio `Societa Per La Bonifica ..._00050540384`;
- la cartella `solleciti` viene creata al momento della generazione PDF;
- se il path archivio e sotto `/volume1`, la creazione cartella, l'upload e il download usano il
  NAS connector SSH condiviso del backend, non una scrittura diretta su mount locale/container;
- se l'avviso non e collegato ad alcun soggetto GAIA, il batch resta `failed` con errore
  `Cartella archivio NAS mancante per l'utenza`.

Template operativo versionato:

- `backend/app/modules/ruolo/templates/Avviso_Sollecito_Template.docx`

Origine del file importato nel progetto:

- `/run/user/1000/gvfs/smb-share:server=nas_cbo.local,share=settore%20catasto/TRIBUTI/Annamaria Salaris/Avviso_Sollecito_Template.docx`

Nota implementativa:

- il template viene copiato preservando header, immagini, stili e relazioni del DOCX originale;
- GAIA sostituisce i campi visibili `MERGEFIELD` del template operativo e appende il partitario
  generato dai dati importati;
- se il template non e raggiungibile, GAIA usa un fallback DOCX minimale e traccia l'anomalia
  tramite il payload/item generato;
- la conversione in PDF usa LibreOffice headless; in assenza di LibreOffice l'item viene marcato
  `failed` con errore esplicito.
- l'immagine Docker backend include `libreoffice-writer` e `fonts-dejavu`, cosi la conversione
  DOCX -> PDF e disponibile anche nel runtime containerizzato.
- se un runtime di produzione non ha LibreOffice disponibile, GAIA genera comunque il DOCX
  nello stesso percorso NAS, marca l'item `generated_docx` e abilita il download senza preview
  PDF; la UI mostra `Preview PDF non disponibile` e `Scarica DOCX`.

Regola numero avviso:

- il numero avviso del nuovo bollettino non usa piu i codici CNC come intestazione primaria;
- formato: `1 + anno_emissione(4) + anni_riferimento(2+2+...) + progressivo(5)`;
- `anno_emissione` coincide sempre con l'anno corrente in cui il wizard genera il batch;
- `anni_riferimento` concatena in ordine crescente le ultime due cifre delle annualita selezionate;
- il `progressivo` e unico globale per l'anno di emissione e identifica in modo univoco
  l'avviso per quella combinazione di anno emissione e annualita di riferimento;
- esempio per emissione `2026`, annualita `2024` e `2025`, progressivo `00078`:
  `12026242500078`.

Aggiornamento template batch multi-annualita:

- il template operativo non usa piu righe hardcoded `Ruolo 2022` e `Ruolo 2023`;
- la testata usa un oggetto dinamico costruito dal batch, ad esempio
  `Tributi Consortili anno 2024` oppure `Tributi Consortili anni 2022, 2023, 2024 e 2025`;
- il riepilogo importi usa una singola riga template `Anno_Ruolo` che GAIA replica per ogni
  annualita presente nel batch;
- i riferimenti avviso nel riepilogo sono aggregati per anno, nel formato
  `2022: CNC...; 2023: CNC...`;
- la logica consente di assorbire nuovi anni tributari senza ulteriori modifiche al `.docx`.

Aggiornamento naming template:

- il file operativo versionato e stato allineato al nome
  `backend/app/modules/ruolo/templates/Avviso_Sollecito_Template.docx`;
- il precedente nome storico `Avviso_Sollecito_22.23_R1_da_mail_ordinarie.docx` non e piu usato
  dal workflow applicativo.

## Aggiornamento 2026-07-22 - dettaglio tributo e link CapaciTas

La modale `Dettaglio tributo` su `/ruolo/tributi` e stata mantenuta come superficie principale
di consultazione rapida, senza sidebar dedicata, e compattata per ridurre spazio verticale non
operativo.

Decisioni implementate:

- il link CapaciTas mostrato in dettaglio usa prima l'URL manuale salvato su
  `ruolo_tributi_avviso_status.capacitas_url`;
- se l'URL manuale non e configurato, GAIA cerca il link importato da `inCASS` in
  `ana_payment_notices.detail_url`;
- il fallback `inCASS` riconcilia per anno tributario, `source_system = incass` e codice
  fiscale/P.IVA normalizzato;
- il link `Apri avviso CapaciTas` viene esposto nell'header della modale e nei dati posizione,
  evitando una card separata che consumava spazio;
- se non esiste alcun link, la UI mantiene il messaggio esplicito `Link CapaciTas non configurato`.

Aggiornamento UI successivo:

- gli avvisi con saldo aperto espongono l'azione rapida `Avviso sollecito` direttamente in
  `Elenco tributi`;
- la stessa azione e disponibile nella modale `Dettaglio tributo`;
- l'azione genera un batch singolo per codice fiscale/P.IVA, usando il template interno e il
  raggruppamento multi-anno gia previsto dal wizard;
- dopo la generazione GAIA apre una modale di preview PDF con pulsante `Scarica PDF`;
- il viewer PDF embedded della modale nasconde la toolbar nativa e parte con zoom 125%, per
  evitare download browser con nome blob e mantenere come unico download guidato il pulsante GAIA;
- se il codice fiscale/P.IVA e mancante o il PDF non e scaricabile, la pagina mostra un errore
  operativo esplicito.
- ogni riga e la modale `Dettaglio tributo` espongono anche `Dettaglio soggetto`, che apre una
  modale embedded su `/utenze/{subject_id}?embedded=1` quando l'avviso e collegato ad Anagrafica
  GAIA;
- nella modale soggetto resta disponibile `Apri pagina` verso `/utenze/{subject_id}`, mentre gli
  avvisi orfani mostrano il controllo disabilitato.

## Aggiornamento 2026-07-22 - KPI header sezione tributi

La testata di `/ruolo/tributi` espone ora indicatori sintetici coerenti con il flusso operativo
dei solleciti, calcolati sul perimetro filtrato corrente della pagina.

KPI mostrati:

- `Da inviare`: avvisi aperti non ancora marcati come inviati;
- `Avvisi inviati`: avvisi per cui esiste evidenza di invio;
- `Via PEC`: avvisi inviati con recapito PEC rilevato dal sync `inCASS`;
- `Via raccomandata`: placeholder operativo, oggi a `0` finche non arriva l'Excel esterno con il
  dettaglio raccomandate;
- `Totale avvisi`: totale record nel perimetro filtrato;
- `Totale via PEC`: totale avvisi con invio PEC nel perimetro filtrato;
- `Totale via raccomandata`: totale avvisi raccomandata, oggi a `0` per assenza del file esterno.

Regole dati confermate:

- la summary backend e pubblicata da `GET /ruolo/tributi/summary`;
- il conteggio `PEC` usa i dati di postalizzazione sincronizzati da `inCASS`, in particolare le
  evidenze `mailing_list` / `mailing_delivery`;
- il conteggio `raccomandata` non viene ancora dedotto in automatico dai dati disponibili in
  GAIA e resta esplicitamente non valorizzato fino alla consegna del tracciato Excel dedicato;
- appena `inCASS` sincronizza un invio PEC, il KPI corrispondente e immediatamente conteggiabile
  senza attendere l'Excel raccomandate.

Verifica quality gate:

- i test mirati backend e frontend per questa change risultano validati al `100%` di coverage sui
  file runtime toccati in data `2026-07-22`.

## Aggiornamento 2026-07-22 - import pagamenti CapaciTas

La pagina `/ruolo/tributi/import-pagamenti` e ora operativa per importare export CapaciTas in
formato CSV, XLSX o XLSM senza bloccare il rilascio su un unico tracciato fisso.

Decisioni implementate:

- parser CSV con fallback encoding `utf-8-sig`, `utf-8`, `cp1252`, `latin-1` e parser Excel tramite
  `openpyxl`;
- mapping colonne opzionale via JSON, con autodetect sugli alias noti quando il mapping non e
  fornito;
- matching prudente: prima `codice_cnc + anno_tributario`, poi `codice_utenza + anno_tributario`;
- nessun matching automatico su CF/PIVA, nominativo o importo quando la riga e ambigua;
- import in `ruolo_tributi_payments` con `source = capacitas_excel`;
- audit job in `ruolo_tributi_payment_import_jobs`, includendo contatori, stato, errore e report
  `unmatched/errors` salvato in `mapping_json`;
- deduplica su `source + payment_reference`, con riferimento deterministico generato quando il file
  non espone un riferimento pagamento esplicito;
- aggiornamento dello stato sintetico dell'avviso dopo ogni pagamento importato.

Superfici operative:

- `POST /ruolo/tributi/import-pagamenti`;
- `GET /ruolo/tributi/import-pagamenti/jobs`;
- `GET /ruolo/tributi/import-pagamenti/jobs/{job_id}`;
- `GET /ruolo/tributi/import-pagamenti/jobs/{job_id}/unmatched`;
- UI con upload file, mapping JSON opzionale, storico job, KPI job e tabella righe da verificare.

Verifica quality gate:

- backend validato con coverage `100%` su `tributi_routes.py`, `schemas.py` e
  `tributi_repositories.py`;
- frontend validato con coverage `100%` su
  `src/app/ruolo/tributi/import-pagamenti/page.tsx` e `src/lib/ruolo-api.ts`.

## Obiettivo funzionale

Creare una sezione operativa per tracciare pagamenti, scoperti e solleciti degli utenti a ruolo.

La sezione deve includere:

- tutti gli avvisi a ruolo, inclusi anni precedenti non pagati;
- avvisi collegati e non collegati ad Anagrafica GAIA;
- stato pagamento per avviso CNC;
- supporto a pagamenti parziali e multipli;
- distinzione tra morosita, sospensione, contestazione, annullamento e da verificare;
- note operative storicizzate;
- link diretto a CapaciTas;
- generazione da GAIA del documento di sollecito, senza invio automatico;
- import pagamenti CapaciTas da CSV/XLSX/XLSM con mapping opzionale e report anomalie.

## Perimetro MVP

### Incluso

- Lista tributi basata su `ruolo_avvisi`.
- Filtri per anno, stato pagamento, scoperti, codice CNC, codice utenza, CF/PIVA, nominativo,
  soggetto collegato/non collegato.
- Calcolo saldo avviso: `importo_totale_euro - somma_pagamenti_validi`.
- Registro pagamenti per avviso, con supporto a piu righe di pagamento.
- Stato operativo manuale dell'avviso.
- Note interne per avviso.
- Link CapaciTas apribile dalla riga e dal dettaglio.
- Registro solleciti predisposti.
- Generazione documento sollecito da template `.docx`.
- Permesso applicativo dedicato per accesso/modifica sezione tributi.
- Audit minimo: utente creatore, data creazione/modifica, fonte del dato.

### Escluso dal primo rilascio

- Invio email/PEC/SMS del sollecito.
- Riscossione coattiva.
- Integrazione diretta real-time con CapaciTas.
- Firma digitale o protocollazione automatica del sollecito.
- Motore autonomo di calcolo del tributo.

## Fonti dati

### Dati ruolo

Fonte primaria: read-model `ruolo_avvisi`, `ruolo_partite`, `ruolo_particelle`.

Campi principali:

- `ruolo_avvisi.id`
- `ruolo_avvisi.codice_cnc`
- `ruolo_avvisi.anno_tributario`
- `ruolo_avvisi.subject_id`
- `ruolo_avvisi.codice_fiscale_raw`
- `ruolo_avvisi.nominativo_raw`
- `ruolo_avvisi.codice_utenza`
- `ruolo_avvisi.importo_totale_euro`

### Dati anagrafici

Priorita di lettura:

1. Anagrafica GAIA quando `subject_id` e valorizzato.
2. Recapiti digitali importati dal sync `inCASS avvisi` in `ana_persons.email` o `ana_companies.email_pec`.
3. Spedizioni e ricevute presenti in `ana_payment_notices.raw_detail_json.mailing_list`.
4. Dati raw da inCASS/CapaciTas presenti su `ruolo_avvisi`.

La sezione deve funzionare anche quando il soggetto non e collegato in GAIA.

### Pagamenti

Fonte prevista: export pagamenti CapaciTas in formato CSV, XLSX o XLSM.

Decisione operativa:

- importare tracciati con riga intestazione, mapping JSON opzionale e autodetect degli alias noti;
- accettare importi italiani o numerici Excel e date italiane/ISO/Excel;
- mantenere in report le righe non abbinate o non valide, senza creare pagamenti forzati.

Chiave di riconciliazione preferita:

1. `codice_cnc` / avviso;
2. fallback su `codice_utenza + anno_tributario`;
3. CF/PIVA, nominativo e importo restano solo dati raw di revisione, non chiavi automatiche.

## Modello dati proposto

### `ruolo_tributi_payment_import_jobs`

Traccia ogni import di pagamenti da CapaciTas.

Campi principali:

- `id` UUID PK
- `filename`
- `source` default `capacitas_excel`
- `status`
- `started_at`
- `finished_at`
- `records_total`
- `records_imported`
- `records_matched`
- `records_unmatched`
- `records_errors`
- `error_detail`
- `mapping_json`
- `triggered_by`
- `created_at`

### `ruolo_tributi_payments`

Registra i pagamenti associati a un avviso.

Campi principali:

- `id` UUID PK
- `avviso_id` FK `ruolo_avvisi.id`
- `import_job_id` FK nullable
- `codice_cnc_raw`
- `codice_utenza_raw`
- `anno_tributario`
- `paid_at`
- `amount`
- `payment_reference`
- `payment_method`
- `source`
- `status`: `valid`, `reversed`, `duplicate`, `to_review`
- `raw_payload_json`
- `created_by`
- `created_at`
- `updated_at`

Vincoli:

- non assumere un solo pagamento per avviso;
- supportare pagamenti parziali;
- supportare storni o righe duplicate marcandole senza cancellazione distruttiva.

### `ruolo_tributi_avviso_status`

Stato operativo dell'avviso rispetto al pagamento.

Campi principali:

- `id` UUID PK
- `avviso_id` FK unique `ruolo_avvisi.id`
- `payment_status`: `unpaid`, `partial`, `paid`, `overpaid`, `to_review`
- `workflow_status`: `moroso`, `contestato`, `sospeso`, `annullato`, `non_dovuto`, `rateizzato`
- `saldo_amount`
- `last_payment_at`
- `capacitas_url`
- `capacitas_avviso_code`
- `updated_by`
- `updated_at`

Nota CapaciTas:

- il link fornito ha formato `https://incass3.servizicapacitas.com/pages/dettaglioAvviso.aspx?...`;
- il parametro `token` potrebbe essere volatile o sensibile;
- prima di persistere token o URL completi va chiarito se il token e stabile, personale o
  temporaneo.

### `ruolo_tributi_year_managers`

Matrice configurabile delle competenze per annualita tributaria.

Campi principali:

- `id` UUID PK
- `manager_key`
- `manager_label`
- `year_from` nullable, range aperto verso il passato
- `year_to` nullable, range aperto verso il futuro
- `calculation_policy`
- `is_active`
- `notes`
- `updated_by`
- `created_at`
- `updated_at`

Vincoli applicativi:

- i range attivi non possono sovrapporsi;
- un range con `year_from = NULL` indica `fino al year_to`;
- un range con `year_to = NULL` indica `dal year_from`;
- la `calculation_policy` e il punto di aggancio per i futuri calcoli dovuto/competenza.

### `ruolo_tributi_notes`

Note operative interne.

Campi principali:

- `id` UUID PK
- `avviso_id` FK
- `body`
- `visibility` default `internal`
- `created_by`
- `created_at`
- `updated_at`

### `ruolo_tributi_reminders`

Registro dei solleciti predisposti.

Campi principali:

- `id` UUID PK
- `avviso_id` FK
- `template_id` nullable
- `status`: `draft`, `generated`, `discarded`
- `generated_document_path`
- `generated_at`
- `generated_by`
- `payload_json`
- `notes`
- `created_at`

### `ruolo_tributi_reminder_batches`

Registro batch di creazione solleciti per utenze morose.

Campi principali:

- `id` UUID PK
- `title`
- `status`: `running`, `generated`, `failed`, `partial_failed`
- `template_path`
- `filters_json`
- `items_total`
- `items_generated`
- `items_failed`
- `generated_by`
- `generated_at`
- `notes`
- `created_at`
- `updated_at`

### `ruolo_tributi_reminder_batch_items`

Singolo PDF da generare per una utenza raggruppata per codice fiscale/P.IVA.

Campi principali:

- `id` UUID PK
- `batch_id` FK
- `subject_id` nullable
- `codice_fiscale`
- `display_name`
- `comune_key`
- `years_json`
- `avviso_ids_json`
- `due_amount`
- `paid_amount`
- `saldo_amount`
- `nas_folder_path`
- `generated_document_path`
- `status`: `pending`, `generated`, `failed`
- `error_detail`
- `payload_json`
- `created_at`
- `updated_at`

### `ruolo_tributi_templates`

Template utilizzabili per generare i solleciti.

Campi principali:

- `id` UUID PK
- `name`
- `template_path`
- `version`
- `is_active`
- `created_by`
- `created_at`

Template iniziale di riferimento:

- `Avviso_Sollecito_morosi_R22_R23_R120.docx`

Il path di rete indicato dall'operatore e un riferimento operativo locale; non va hardcodato nel
codice applicativo. Il template va caricato/configurato tramite storage o configurazione
amministrativa.

## Regole di calcolo

### Stato pagamento derivato

Input:

- importo dovuto: `ruolo_avvisi.importo_totale_euro`;
- pagamenti validi: somma `ruolo_tributi_payments.amount` con `status = valid`.

Regole:

- `paid_sum = 0` -> `unpaid`;
- `0 < paid_sum < due_amount` -> `partial`;
- `paid_sum = due_amount` -> `paid`;
- `paid_sum > due_amount` -> `overpaid`;
- importo mancante o mismatch non risolvibile -> `to_review`.

### Stato operativo manuale

Lo stato operativo non deve sovrascrivere la contabilita del pagamento.

Esempi:

- avviso non pagato e non contestato -> `moroso`;
- avviso non pagato ma con contestazione aperta -> `contestato`;
- avviso sospeso amministrativamente -> `sospeso`;
- avviso annullato o non dovuto -> `annullato` / `non_dovuto`.

## API previste

### Lista e dettaglio

- `GET /ruolo/tributi/avvisi`
- `GET /ruolo/tributi/avvisi/{avviso_id}`
- `PATCH /ruolo/tributi/avvisi/{avviso_id}/status`
- `PATCH /ruolo/tributi/avvisi/{avviso_id}/capacitas-link`

### Pagamenti

- `GET /ruolo/tributi/avvisi/{avviso_id}/payments`
- `POST /ruolo/tributi/avvisi/{avviso_id}/payments`
- `PATCH /ruolo/tributi/payments/{payment_id}`

### Note

- `GET /ruolo/tributi/avvisi/{avviso_id}/notes`
- `POST /ruolo/tributi/avvisi/{avviso_id}/notes`
- `PATCH /ruolo/tributi/notes/{note_id}`

### Import CapaciTas

- `POST /ruolo/tributi/import-pagamenti`
- `GET /ruolo/tributi/import-pagamenti/jobs`
- `GET /ruolo/tributi/import-pagamenti/jobs/{job_id}`
- `GET /ruolo/tributi/import-pagamenti/jobs/{job_id}/unmatched`

### Solleciti

- `POST /ruolo/tributi/avvisi/{avviso_id}/reminders`
- `GET /ruolo/tributi/avvisi/{avviso_id}/reminders`
- `GET /ruolo/tributi/reminders/{reminder_id}/download`

## Frontend previsto

### `/ruolo/tributi`

Workspace principale.

Componenti:

- KPI: totale dovuto, totale incassato, saldo aperto, avvisi morosi, parziali, contestati;
- tabella avvisi con filtri e ordinamento;
- badge stato pagamento e stato operativo;
- azioni rapide: apri dettaglio, apri CapaciTas, genera sollecito, aggiungi nota.

### Dettaglio avviso

Pannelli:

- dati contribuente da GAIA o raw inCASS;
- importo dovuto, pagato, saldo;
- pagamenti;
- note;
- storico solleciti;
- link CapaciTas;
- dati partitario e particelle gia presenti nel modulo ruolo.

### `/ruolo/tributi/import-pagamenti`

Workflow:

1. upload CSV/XLSX/XLSM;
2. mapping colonne opzionale via JSON o autodetect alias;
3. import job;
4. report matched/unmatched/errori;
5. revisione manuale dei non riconciliati.

La pagina mostra storico job, KPI dell'ultimo job selezionato e righe da verificare. Il backend
mantiene deduplica e report anomalie per consentire reimport controllati.

### `/ruolo/tributi/solleciti`

Vista dedicata ai solleciti predisposti.

Filtri:

- anno;
- stato sollecito;
- stato pagamento;
- stato operativo;
- template;
- utente generatore.

## Permessi

La sezione deve usare permessi dedicati, non il solo accesso generico a `module_ruolo`.

Proposta section keys:

- `ruolo.tributi.view`
- `ruolo.tributi.manage_payments`
- `ruolo.tributi.manage_status`
- `ruolo.tributi.manage_notes`
- `ruolo.tributi.generate_reminders`
- `ruolo.tributi.import_payments`
- `ruolo.tributi.admin`

Regola MVP:

- solo utenti abilitati esplicitamente possono modificare pagamenti, stati, note e solleciti;
- gli utenti con solo vista possono consultare saldo e storico senza modificare.

## Milestone implementative

### T0 - Design e migrazione dati

Deliverable:

- documento milestone approvato;
- migration Alembic con nuove tabelle `ruolo_tributi_*`;
- modelli ORM;
- enums;
- section keys e bootstrap permessi.

Done when:

- `alembic upgrade head` funziona;
- `alembic downgrade -1` funziona;
- test ORM e migration coperti.

Stato 2026-07-17:

- implementata migration `20260717_1500_ruolo_tributi.py`;
- implementati modelli ORM `RuoloTributiPaymentImportJob`, `RuoloTributiPayment`,
  `RuoloTributiAvvisoStatus`, `RuoloTributiNote`, `RuoloTributiTemplate`,
  `RuoloTributiReminder`;
- implementati enum runtime per pagamenti, stati pagamento, stati workflow e solleciti;
- aggiunte section keys dedicate nel bootstrap modulo e nello script globale.

### T1 - Read model tributi e API base

Deliverable:

- repository query per lista tributi;
- calcolo saldo;
- endpoint lista/dettaglio;
- filtri principali;
- test backend.

Done when:

- la lista mostra tutti gli avvisi a ruolo, inclusi non collegati;
- anni precedenti non pagati emergono come saldo aperto;
- il dettaglio espone importo dovuto, pagato, saldo e stato.

Stato 2026-07-17:

- implementato router `/ruolo/tributi`;
- implementati endpoint `GET /ruolo/tributi/avvisi` e
  `GET /ruolo/tributi/avvisi/{avviso_id}`;
- implementati filtri principali: anno, soggetto, ricerca unificata, CF/PIVA, comune,
  codice utenza, non collegati, stato pagamento, stato workflow e `open_only`;
- implementato calcolo derivato `unpaid`, `partial`, `paid`, `overpaid`, `to_review`;
- coperto con test API mirati.

### T2 - Pagamenti manuali e stati operativi

Deliverable:

- CRUD controllato dei pagamenti;
- gestione stato operativo;
- pagamenti multipli/parziali/storni;
- audit utente;
- test di calcolo saldo.

Done when:

- un avviso puo passare da non pagato a parziale/pagato/overpaid;
- lo stato operativo puo distinguere moroso, contestato, sospeso, annullato, non dovuto;
- nessuna modifica distruttiva cancella storico contabile senza traccia.

Stato 2026-07-17:

- implementato `POST /ruolo/tributi/avvisi/{avviso_id}/payments`;
- implementato `PATCH /ruolo/tributi/avvisi/{avviso_id}/status`;
- implementato `POST /ruolo/tributi/avvisi/{avviso_id}/notes`;
- la gestione storni/rettifiche e modifica pagamenti importati resta da rifinire nel ciclo
  successivo.

### T3 - Note e link CapaciTas

Deliverable:

- note interne;
- link CapaciTas su avviso;
- validazione URL;
- UI azioni rapide.

Done when:

- l'operatore puo annotare un avviso;
- l'operatore puo aprire CapaciTas dalla lista e dal dettaglio;
- la gestione token/URL e documentata dopo verifica con CapaciTas.

Stato 2026-07-20:

- implementate note interne su avviso con audit utente;
- implementata gestione link e codice avviso CapaciTas nello stato tributo;
- lista e dettaglio espongono azione diretta per aprire CapaciTas quando il link e disponibile;
- resta aperta DT-01 sulla natura del token CapaciTas e sulla policy definitiva di persistenza URL.

### T4 - Solleciti predisposti da GAIA

Deliverable:

- template registry;
- generazione `.docx` da template;
- registro solleciti;
- download documento generato;
- test su rendering placeholder.

Done when:

- da un avviso moroso/parziale si genera un sollecito;
- il documento contiene dati contribuente, codice CNC, codice utenza, anno, importi e saldo;
- il sollecito resta in storico come `generated`;
- nessun invio automatico viene effettuato.

Stato 2026-07-20:

- implementato registro solleciti `ruolo_tributi_reminders`;
- implementati endpoint `POST /ruolo/tributi/avvisi/{avviso_id}/reminders`,
  `GET /ruolo/tributi/avvisi/{avviso_id}/reminders` e
  `GET /ruolo/tributi/reminders/{reminder_id}/download`;
- implementata generazione `.docx` OpenXML minimale con dati contribuente, codice CNC, codice
  utenza, anno, importi e saldo;
- implementato download documento generato;
- implementata UI nel dettaglio avviso per generare il sollecito, visualizzare lo storico e
  scaricare il `.docx`;
- nessun invio automatico e stato introdotto.

### T5 - Import pagamenti CapaciTas Excel

Stato:

- completato import operativo CSV/XLSX/XLSM con mapping opzionale e autodetect alias.

Deliverable:

- parser CSV/XLSX/XLSM;
- mapping deterministico o autodetect;
- import job auditato;
- report matched/unmatched/errori;
- deduplicazione;
- gestione import ripetuto.

Done when:

- l'import riconcilia pagamenti su `codice_cnc + anno_tributario`;
- il fallback `codice_utenza + anno_tributario` copre gli export senza codice avviso;
- i casi non riconciliati sono consultabili nel report job;
- reimport dello stesso file non duplica pagamenti validi;
- la UI consente upload, mapping opzionale, storico job e revisione anomalie.

### T6 - Frontend operativo e hardening

Deliverable:

- pagine `/ruolo/tributi`, import, solleciti e dettaglio;
- test unit/frontend;
- test API;
- copertura 100% sui file runtime nuovi o modificati;
- aggiornamento Graphify del modulo/docs.

Done when:

- workflow completo verificato: consultazione -> nota -> pagamento -> stato -> sollecito;
- permessi verificati per utenti abilitati e non abilitati;
- documentazione aggiornata.

Stato 2026-07-17:

- implementata pagina `/ruolo/tributi` con KPI, filtri, lista avvisi, dettaglio laterale,
  pagamenti manuali, stato operativo, link CapaciTas e note;
- implementata pagina dettaglio dedicata `/ruolo/tributi/[avvisoId]` con gestione puntuale
  di pagamenti, stato operativo, link CapaciTas, note e storico;
- aggiunti link in sidebar modulo Ruolo e dashboard;
- aggiunte pagine placeholder `/ruolo/tributi/import-pagamenti` e `/ruolo/tributi/solleciti`
  per evitare link morti e documentare i blocchi successivi;
- aggiunti test unitari frontend `frontend/tests/unit/ruolo-tributi-page.test.tsx` e
  `frontend/tests/unit/ruolo-tributi-detail-page.test.tsx`;
- resta da implementare workflow import Excel reale dopo ricezione del tracciato CapaciTas.

Stato 2026-07-20:

- completato workflow operativo consultazione -> nota -> pagamento -> stato -> generazione
  sollecito -> download documento;
- verificata coverage 100% su backend Tributi runtime
  (`tributi_routes.py`, `tributi_repositories.py`, `tributi_reminder_service.py`);
- verificata coverage 100% sulle pagine frontend principali
  (`/ruolo/tributi`, `/ruolo/tributi/[avvisoId]`, placeholder import/solleciti e client
  `ruolo-api.ts`);
- frontend typecheck e test unitari Ruolo/Tributi passano;
- aggiunti test unitari diretti per API client Ruolo/Tributi e placeholder
  `/ruolo/tributi/import-pagamenti`, `/ruolo/tributi/solleciti`;
- aggiornata la pagina lista `/ruolo/tributi` per aprire il dettaglio in modale larga invece che
  in sidebar, con azione CapaciTas visibile nell'header modale;
- aggiornati i filtri della lista: ricerca automatica da 3 caratteri e anno applicato solo quando
  scritto come anno completo a 4 cifre;
- da completare ancora: import Excel reale CapaciTas, vista dedicata avanzata
  `/ruolo/tributi/solleciti`, gestione definitiva storage/template amministrativo e verifica
  permessi con utenti applicativi reali.

Stato 2026-07-22:

- validato live il nuovo scraper Capacitas inCASS per supporto Tributi/Ruolo sui CF
  `MDDMGV77A51G113Q` e `FLCBTS63D10D665W`;
- sincronizzati 38 avvisi, 3 recapiti e 9 spedizioni PEC/email; le spedizioni sono salvate in
  `ana_payment_notices.raw_detail_json.mailing_list` e i recapiti aggiornano l'anagrafica utenza
  privilegiando la PEC quando disponibile;
- scaricate 2 ricevute ObjMan (`ACCETTAZIONE`, `CONSEGNA`) sull'avviso `020200004170960` come
  documenti `corrispondenza`; upload NAS non eseguito per assenza di `nas_folder_path` sul soggetto
  campione;
- hardening completato su paginazione Kendo rubrica/spedizioni, `intCodiceInvio=0`, apertura ObjMan
  con OTP e filtro dei metadati ricevuta per evitare replica su avvisi non correlati.
- la modal `Dettaglio tributo` e la pagina dettaglio dedicata espongono il riepilogo PEC inCASS:
  destinatario PEC, stato, data accettazione, data consegna e numero ricevute ObjMan archiviate.
- completato import pagamenti CapaciTas da CSV/XLSX/XLSM con mapping opzionale/autodetect,
  deduplica, storico job e report righe da verificare.

## Decisioni aperte

| ID | Decisione | Impatto |
|----|-----------|---------|
| DT-01 | Stabilita e natura del token CapaciTas nel link dettaglio avviso | Decide se salvare URL completo o generare link runtime |
| DT-02 | Tracciato pagamenti CapaciTas | Non blocca piu l'import: mapping opzionale/autodetect e report anomalie assorbono varianti CSV/XLSX |
| DT-03 | Dove conservare i `.docx` generati | Storage locale, NAS, DB metadata + filesystem |
| DT-04 | Placeholder definitivi del template sollecito | Necessario per rendering robusto |
| DT-05 | Utenti/gruppi abilitati ai permessi tributi | Necessario per bootstrap permessi in produzione |
| DT-06 | Politica di modifica pagamenti importati | Decide se consentire edit diretto o solo storno/rettifica |

## Test richiesti

Backend:

- repository lista tributi;
- calcolo saldo unpaid/partial/paid/overpaid;
- pagamenti multipli;
- storni;
- stati operativi;
- note;
- generazione sollecito;
- permessi;
- import pagamenti CapaciTas CSV/XLSX/XLSM.

Frontend:

- lista tributi e filtri;
- dettaglio avviso;
- azioni rapide;
- generazione sollecito;
- stati vuoti e casi non collegati ad Anagrafica.

Coverage:

- ogni file runtime nuovo o modificato deve essere coperto al 100%, secondo la policy repo.
