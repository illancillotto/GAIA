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

## Aggiornamento 2026-07-22 - wizard solleciti batch

La generazione dei solleciti non e piu trattata come operazione isolata sul singolo avviso.
Il flusso operativo principale e un wizard batch dentro `/ruolo/tributi`.

Decisioni confermate:

- chiave utenza: `codice_fiscale_raw` normalizzato;
- una utenza puo includere piu avvisi e piu anni;
- ordinamento candidature per nominativo e comune;
- selezione automatica delle utenze aperte con cartella NAS disponibile, con possibilita di
  selezione manuale tramite codice fiscale/P.IVA;
- output: un PDF per utenza, non un PDF globale;
- contenuto PDF: avviso di sollecito e partitario nello stesso documento;
- salvataggio: `{ana_subjects.nas_folder_path}/solleciti/{CF}_avviso_sollecito_{anni}.pdf`;
- batch e item restano tracciati anche se il PDF non viene generato, ad esempio per cartella NAS
  mancante o errore LibreOffice;
- invio email/PEC/SMS escluso dal perimetro corrente.

Template operativo versionato:

- `backend/app/modules/ruolo/templates/Avviso_Sollecito_22.23_R1_da_mail_ordinarie.docx`

Origine del file importato nel progetto:

- `/run/user/1000/gvfs/smb-share:server=nas_cbo.local,share=settore%20catasto/TRIBUTI/Annamaria Salaris/Avviso_Sollecito_22.23_R1_da_mail_ordinarie.docx`

Nota implementativa:

- il template viene copiato preservando header, immagini, stili e relazioni del DOCX originale;
- GAIA sostituisce i campi visibili `MERGEFIELD` del template operativo e appende il partitario
  generato dai dati importati;
- se il template non e raggiungibile, GAIA usa un fallback DOCX minimale e traccia l'anomalia
  tramite il payload/item generato;
- la conversione in PDF usa LibreOffice headless; in assenza di LibreOffice l'item viene marcato
  `failed` con errore esplicito.

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
- predisposizione per import pagamenti da Excel CapaciTas, da finalizzare dopo ricezione del
  file reale.

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
- Import Excel definitivo prima di avere il tracciato reale.
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

Fonte prevista: export Excel da CapaciTas.

Decisione operativa:

- non implementare un parser Excel speculativo prima del file reale;
- predisporre il modello dati e il job di import;
- implementare mapping e riconciliazione quando viene consegnato l'esempio.

Chiave di riconciliazione preferita:

1. `codice_cnc` / avviso;
2. fallback su `codice_utenza + anno_tributario`;
3. fallback assistito su CF/PIVA, nominativo e importo solo per casi da revisione.

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

1. upload Excel;
2. preview mapping colonne;
3. import job;
4. report matched/unmatched/errori;
5. revisione manuale dei non riconciliati.

Nel primo step si implementa solo la struttura UI e API job, mentre il mapping resta bloccato fino
alla ricezione del file reale.

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

Prerequisito:

- ricezione file Excel reale da CapaciTas.

Deliverable:

- analisi colonne;
- mapping deterministico;
- import job;
- report matched/unmatched/errori;
- deduplicazione;
- gestione import ripetuto.

Done when:

- l'import riconcilia pagamenti su `codice_cnc`;
- i casi non riconciliati sono consultabili e correggibili;
- reimport dello stesso file non duplica pagamenti validi.

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

## Decisioni aperte

| ID | Decisione | Impatto |
|----|-----------|---------|
| DT-01 | Stabilita e natura del token CapaciTas nel link dettaglio avviso | Decide se salvare URL completo o generare link runtime |
| DT-02 | Tracciato Excel pagamenti CapaciTas | Blocca parser e mapping import |
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
- import Excel quando disponibile.

Frontend:

- lista tributi e filtri;
- dettaglio avviso;
- azioni rapide;
- generazione sollecito;
- stati vuoti e casi non collegati ad Anagrafica.

Coverage:

- ogni file runtime nuovo o modificato deve essere coperto al 100%, secondo la policy repo.
