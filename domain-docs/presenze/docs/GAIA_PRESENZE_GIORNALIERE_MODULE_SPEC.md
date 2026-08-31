# GAIA Presenze Giornaliere - Specifica modulo

> Fonte tecnica iniziale: repository locale `/home/cbo/CursorProjects/presenze-scraper`.
> Obiettivo: creare in GAIA un modulo per gestire le giornaliere degli utenti presenti in `application_users`, importando o sincronizzando dati dal portale Inaz.

## 1. Sintesi

Il modulo `presenze` deve permettere a GAIA di leggere, normalizzare, archiviare e consultare le giornaliere lavorative degli utenti applicativi. La sorgente esterna e il portale Inaz `https://serviziweb.inaz.it/portalecbo/default.aspx`, oggi gestito dal tool Python `presenze-scraper` tramite Playwright perche il portale usa iframe, pagine ASP.NET e funzioni JavaScript lato pagina.

Il dato principale da portare in GAIA e la giornata utente: data, utente applicativo, stato import/sync, timbrature o intervalli, ore extra, motivazione e collegamento al record grezzo letto da Inaz.

Nel dettaglio collaboratore, il tab `Cartellino` deve privilegiare leggibilita operativa: le sezioni di dettaglio a bassa frequenza (`Riepilogo giornata`, `Totali giornata`, `Richieste`, `Anomalie`) sono pensate come pannelli espandibili con indicatori sintetici nel titolo, cosi l'operatore puo aprire solo i blocchi rilevanti.

## 2. PRD

### 2.1 Problema

Le giornaliere e gli extra orario oggi sono gestiti con estrazione manuale o semi-automatica dal portale Inaz e con file Excel mensili. Questo crea:

- duplicazione tra portale Inaz, Excel e GAIA;
- difficolta a ricostruire lo storico per utente;
- assenza di audit trail su chi importa, modifica o approva;
- export e riepiloghi non integrati con `application_users`.

### 2.2 Obiettivi MVP

- associare ogni giornata a un record `application_users.id`;
- importare giornaliere da file JSON/CSV/XLSX generati da `presenze-scraper`;
- predisporre sync controllata via worker Playwright per leggere Inaz direttamente;
- visualizzare calendario mensile per utente;
- evidenziare extra orario, anomalie e giornate senza dettaglio;
- esportare un riepilogo mensile compatibile con il modello Excel oggi usato;
- tracciare job di import/sync con stato persistente.

### 2.3 Non obiettivi MVP

- scrivere dati sul portale Inaz;
- automatizzare approvazioni formali lato Inaz;
- sostituire il sistema presenze Inaz;
- salvare credenziali Inaz in chiaro;
- gestire payroll o cedolini.

### 2.4 Attori

- `super_admin`: abilita modulo, credenziali tecniche, job e manutenzione;
- `admin`: importa/sincronizza giornaliere e corregge record;
- `reviewer`: valida anomalie e riepiloghi;
- `viewer`: consulta le proprie giornaliere o quelle autorizzate.
- `hr_manager`: supervisiona recuperi maturati/fruiti, rettifiche manuali e workflow approvativo.

### 2.5 Visibilita organizzativa e approvazione

- `admin`, `hr_manager` e `super_admin` mantengono visibilita completa sui dati Presenze;
- `dirigente`, `capo_settore`, `capo_operai` e `capo_reparto` sono posizioni dell'Organigramma canonico, non ruoli RBAC globali;
- dirigenti e capi vedono soltanto i collaboratori assegnati al proprio sottoalbero organizzativo;
- la gerarchia manageriale concede lettura e approvazione, mentre un override `read` concede soltanto la lettura;
- gli override `approve` e `full` consentono anche la validazione delle giornaliere;
- il collegamento tra collaboratore Inaz e utente GAIA usa `PresenzeCollaborator.application_user_id`;
- nei contratti outbound verso GATE lo stesso valore viene esposto come `gaia_user_id`; non viene derivato da username, email, nome o matricola;
- `owner_user_id` identifica chi ha importato il dato e non concede visibilita organizzativa;
- la modifica dei dati operativi resta distinta dall'approvazione e continua a richiedere i permessi applicativi dedicati;
- durante la migrazione restano attivi in dual-read supervisori e gerarchia Accessi legacy.

## 3. Stato sorgente Inaz

### 3.1 Tool esistente

Nel repo `presenze-scraper` sono presenti tre entrypoint:

- `presenze-straordinari`: login/navigazione e scraping righe potenzialmente legate a straordinari;
- `presenze-crea-mesi`: crea file Excel mensili partendo da `Straordinari.xlsx`;
- `presenze-popola-excel`: legge giornate dal calendario Inaz e popola i file mensili.

Dipendenze rilevanti:

- Python `>=3.11`;
- `playwright`;
- `openpyxl`;
- `python-dotenv`.

### 3.2 Endpoint e superfici Inaz osservate

Il codice non usa API REST documentate. Usa navigazione browser:

| Superficie | Tipo | Uso |
| --- | --- | --- |
| `https://serviziweb.inaz.it/portalecbo/default.aspx` | pagina ASP.NET | login e ingresso portale |
| frame con campi `input[type='text']` e `input[type='password']` | DOM | login automatico quando possibile |
| frame URL contenente `HomeCliente/Home.aspx` | iframe | calendario presenze |
| `#WdgtCalendarCaption` | elemento DOM | mese/anno corrente del calendario |
| funzione JS `WdgtCalendarMove(step)` | funzione pagina | cambia mese calendario |
| `span.WdgtCalCell` | elemento DOM | giorno cliccabile |
| funzione JS `WdgtCalendarOpen(cell)` | funzione pagina | apre dettaglio giorno |
| frame URL contenente `Cartellino_Giorno.aspx` | iframe | dettaglio giornata |
| funzione JS `ChiudiFunzione2('')` o `#btnChiudi` | funzione/bottone pagina | chiude overlay dettaglio |

Queste superfici vanno trattate come fragili: ogni modifica del portale Inaz puo rompere la sync. Il modulo GAIA deve quindi supportare import file come fallback stabile.

### 3.3 Campi estratti dal tool

`presenze-straordinari` produce righe generiche:

- `source_url`;
- `frame_url`;
- `table_index`;
- `row_index`;
- `kind`: `extra_orario`, `anomalia_straordinario`, `maggior_presenza`, `maggiorazione`, `straordinario`, `altro`;
- `matched_text`;
- `hours`;
- `cells`.

`presenze-popola-excel` produce record piu vicini al dominio giornaliera:

- `day`;
- `motivation`;
- `start_time`;
- `end_time`;
- `duration`.

Regole osservate:

- la data del dettaglio e cercata nel body con formato `dd/mm/yyyy`;
- `extra orario` con valore `00:00` significa nessuna giornata extra da importare;
- righe anomalia con codice che inizia per `STRNA` possono contenere intervalli inizio/fine;
- in assenza di intervalli anomalia, il tool usa prima/ultima timbratura `E`/`U`;
- la motivazione default nel tool e `Attivita di sviluppo applicativi per i progetti GAIA e Teti`.

## 4. Architettura GAIA proposta

### 4.1 Namespace

Backend canonico:

```text
backend/app/modules/presenze/
  __init__.py
  router.py
  bootstrap.py
  models.py
  schemas.py
  repositories.py
  routes/
    giornaliere.py
    imports.py
    sync_jobs.py
    exports.py
  services/
    parser.py
    import_service.py
    sync_service.py
    excel_export.py
```

Frontend:

```text
frontend/src/app/presenze/
  page.tsx
  giornaliere/page.tsx
  import/page.tsx
  sync/page.tsx
  utenti/[id]/page.tsx

frontend/src/components/presenze/
frontend/src/lib/api.ts
frontend/src/types/api.ts
```

Documentazione:

```text
domain-docs/presenze/docs/
```

### 4.2 Modello di integrazione

Il modulo deve avere due canali:

1. Import file: JSON/CSV/XLSX generato o compatibile con `presenze-scraper`. E il percorso MVP piu sicuro.
2. Sync diretta: job Playwright dedicato, eseguito preferibilmente fuori dal processo API se diventa lungo o fragile.

Seguire la regola GAIA gia presente in `docs/ARCHITECTURE.md`: i job monitorabili e lunghi devono avere stato persistente e, se necessario, worker dedicato.

### 4.3 Credenziali e sessioni

- non committare mai credenziali Inaz;
- salvare eventuali credenziali tramite il vault/servizio credenziali gia usato in `elaborazioni`, o introdurre un record cifrato coerente con quel pattern;
- non salvare `.presenze-storage-state.json` in repository;
- ogni sessione Playwright deve avere timeout, retry limitato e audit log.

## 5. Data model proposto

### 5.1 Flag modulo utenti

Aggiungere a `application_users`:

- `module_presenze boolean not null default false`.

Aggiornare:

- `backend/app/models/application_user.py`;
- `backend/app/schemas/auth.py`;
- `backend/app/schemas/users.py`;
- `backend/app/repositories/application_user.py`;
- `backend/app/services/bootstrap_admin.py`;
- `frontend/src/types/api.ts`;
- UI amministrazione utenti in `/gaia/users`;
- `enabled_modules` e `permission_resolver`.

Per `super_admin`, includere `presenze` nella lista moduli sempre abilitati.

### 5.2 Tabelle dominio

`presenze_daily_records`

| Campo | Tipo | Note |
| --- | --- | --- |
| `id` | uuid pk | |
| `application_user_id` | fk `application_users.id` | utente GAIA proprietario |
| `work_date` | date | data giornaliera |
| `status` | string | `draft`, `imported`, `reviewed`, `approved`, `rejected` |
| `source` | string | `manual`, `file_import`, `presenze_sync` |
| `start_time` | time nullable | primo ingresso o intervallo extra |
| `end_time` | time nullable | ultima uscita o intervallo extra |
| `ordinary_duration_minutes` | int nullable | opzionale |
| `extra_duration_minutes` | int nullable | da Inaz `extra orario` |
| `motivation` | text nullable | motivazione extra |
| `raw_payload_json` | json nullable | snapshot grezzo |
| `source_frame_url` | text nullable | diagnostica Inaz |
| `source_hash` | string nullable | deduplica |
| `created_by_user_id` | fk nullable | chi ha importato/creato |
| `updated_by_user_id` | fk nullable | ultimo editor |
| `created_at`, `updated_at` | timestamptz | |

Nel modello reale GAIA il record giornaliero include anche:

- causale assenza normalizzata (`resolved_absence_cause`);
- stato validazione (`validation_status`, `validated_by_user_id`, `validated_at`, `validation_note`);
- rettifiche operative (`km_value`, `trasferta_minutes`, `trasferta_montano`, `reperibilita_*`, override straordinario/MPE, `manual_note`);
- classificazione festivita/recuperi:
  - `holiday_kind`
  - `grants_recovery_day`
  - `recovery_day_credit`
  - `uses_recovery_day`
  - `recovery_day_debit`
  - `recovery_day_balance_delta`

Vincolo raccomandato:

- unique parziale o logico su `(application_user_id, work_date, source_hash)` per evitare duplicati import.

Note export XLSM:

- `KM AUTO` usa `km_value`;
- `REPERIBILITA'` nel template HR resta un flag `X`, anche se in GAIA il dato e strutturato (`hours/days/shifts`);
- `N. ORE TRASFERTA` usa `trasferta_minutes`;
- `COMUNE MONTANO` usa `trasferta_montano`, ma nel template legacy occupa la stessa cella della trasferta ore, quindi in export prevale `X`;
- il template sorgente di default va configurato con `PRESENZE_EXPORT_TEMPLATE_PATH`.

`presenze_daily_intervals`

| Campo | Tipo | Note |
| --- | --- | --- |
| `id` | uuid pk | |
| `daily_record_id` | fk cascade | |
| `kind` | string | `punch`, `extra`, `anomaly`, `manual` |
| `start_time` | time nullable | |
| `end_time` | time nullable | |
| `duration_minutes` | int nullable | |
| `label` | string nullable | es. `STRNA...` |
| `raw_cells_json` | json nullable | riga tabellare originale |

`presenze_import_jobs`

| Campo | Tipo | Note |
| --- | --- | --- |
| `id` | uuid pk | |
| `status` | string | `pending`, `running`, `completed`, `failed` |
| `filename` | string nullable | |
| `requested_by_user_id` | fk `application_users.id` | |
| `target_user_id` | fk nullable | se import per singolo utente |
| `date_from`, `date_to` | date nullable | |
| `total_records`, `records_imported`, `records_skipped`, `records_errors` | int | metriche |
| `error_detail` | text nullable | |
| `params_json` | json nullable | |
| `created_at`, `started_at`, `finished_at` | timestamptz | |

`presenze_sync_jobs`

Uguale a import job, con in piu:

- `sync_mode`: `date_range`, `month`, `single_day`;
- `headless`;
- `storage_state_ref` o riferimento vault/sessione;
- `last_portal_url`;
- `diagnostic_payload_json`.

`presenze_holidays`

Configurazione calendario tipizzata:

- `ordinary`: festivita ordinaria;
- `suppressed`: festivita soppressa che genera diritto a recupero;
- `working_override`: eccezione lavorativa senza semantica festiva.

`presenze_recovery_adjustments`

Rettifiche manuali HR persistite con:

- `adjustment_date`
- `delta_days`
- `kind` (`credit`, `debit`, `correction`)
- `approval_status` (`pending`, `approved`, `rejected`)
- `approval_note`
- audit: creatore, ultimo aggiornamento, revisore e timestamp revisione

`presenze_collaborators`

Nel modello reale il collaboratore Inaz non e solo un alias di `application_users`, ma il centro del dominio Presenze. Oltre ai dati anagrafici importati, espone:

- `application_user_id`: mapping opzionale verso utente GAIA;
- `contract_kind`: `operaio`, `impiegato`, `quadro`, `altro`;
- `operai_group`: `agrario`, `catasto_magazzino` oppure `null`;
- `standard_daily_minutes`: standard giornaliero usato dalle regole operative e dalle conversioni in giorni equivalenti.

Questi campi possono essere derivati inizialmente dal template orario, ma devono restare correggibili da admin/HR perche il template Inaz non e una fonte contrattuale completa.

Il mapping usa `application_users` come anagrafica canonica indipendentemente dallo stato dell'account. Un utente GAIA inattivo o privo del modulo Presenze puo quindi identificare un collaboratore, partecipare all'organigramma e rendere governabili le sue giornaliere, ma non acquisisce login, accesso al modulo o permessi operativi. Riattivazione e abilitazioni restano operazioni separate ed esplicite.

Un `application_user_id` puo essere associato al piu a un collaboratore attivo nel mapping: l'indice unico parziale lo garantisce a livello DB. Ogni variazione di mapping (map, remap, unmap) lascia traccia in `presenze_collaborator_mapping_audit` con autore, motivo e timestamp; le operazioni noop non generano audit.

Per l'integrazione GATE, `application_user_id` e `gaia_user_id` rappresentano la stessa identita applicativa: il primo e la foreign key interna, il secondo e il nome del campo nel contratto. `PresenzeCollaborator.id`/`collaborator_id` resta la chiave tecnica dei record Presenze e `employee_code` resta la matricola. Questi namespace non sono intercambiabili. Il payload di giornaliere e anomalie legge sempre il mapping corrente `PresenzeCollaborator.application_user_id`; l'eventuale copia denormalizzata su `PresenzeDailyRecord` non viene usata per autorizzare. Lo scope di responsabili e squadre non usa fallback tramite username, email, nome o matricola; mapping mancanti o ambigui falliscono chiusi.

## 6. Endpoint GAIA proposti

Tutti sotto prefisso `/presenze` incluso da `backend/app/api/router.py`.

### 6.1 Giornaliere

| Metodo | Path | Permesso | Descrizione |
| --- | --- | --- | --- |
| `GET` | `/presenze/giornaliere` | `inaz.giornaliere` | lista paginata con filtri |
| `POST` | `/presenze/giornaliere` | `inaz.edit` | crea giornaliera manuale |
| `GET` | `/presenze/giornaliere/{id}` | `inaz.giornaliere` | dettaglio |
| `PUT` | `/presenze/giornaliere/{id}` | `inaz.edit` | aggiorna record manuale/correzione |
| `POST` | `/presenze/giornaliere/{id}/review` | `inaz.review` | marca reviewed/approved/rejected |
| `DELETE` | `/presenze/giornaliere/{id}` | `inaz.admin` | eliminazione controllata |

Filtri minimi:

- `application_user_id`;
- `date_from`;
- `date_to`;
- `status`;
- `source`;
- `has_extra`;
- `q`.

### 6.2 Vista utenti e calendario

| Metodo | Path | Permesso | Descrizione |
| --- | --- | --- | --- |
| `GET` | `/presenze/users` | `inaz.giornaliere` | utenti GAIA con `module_presenze=true` |
| `GET` | `/presenze/users/{user_id}/calendar` | `inaz.giornaliere` | calendario mensile/periodo |
| `GET` | `/presenze/users/{user_id}/summary` | `inaz.giornaliere` | KPI periodo |

### 6.2.b Collaboratori Inaz

| Metodo | Path | Permesso | Descrizione |
| --- | --- | --- | --- |
| `GET` | `/presenze/collaborators` | `inaz.giornaliere` | lista collaboratori Inaz con mapping GAIA, profilo contrattuale e gruppo operai |
| `PUT` | `/presenze/collaborators/{id}/application-user` | `inaz.admin` | aggiorna mapping collaboratore -> utente GAIA (`reason` obbligatorio, non blank) |
| `GET` | `/presenze/collaborators/{id}/application-user-audit` | `inaz.admin` | storico audit map/remap/unmap del collaboratore |
| `PUT` | `/presenze/collaborators/{id}/contract-profile` | `inaz.admin` | aggiorna `contract_kind`, `operai_group` e `standard_daily_minutes` |
| `GET` | `/presenze/collaborators/{id}/calendar` | `inaz.giornaliere` | cartellino periodo del collaboratore |
| `GET` | `/presenze/collaborators/{id}/summary` | `inaz.giornaliere` | riepilogo eventi e KPI periodo |
| `POST` | `/presenze/collaborators/{id}/schedule-assignments` | `inaz.admin` | assegna template orario, rifiutando duplicati esatti di template e validita |

### 6.3 Import file

| Metodo | Path | Permesso | Descrizione |
| --- | --- | --- | --- |
| `POST` | `/presenze/import/upload` | `inaz.import` | upload JSON/CSV/XLSX e avvio job |
| `GET` | `/presenze/import/jobs` | `inaz.import` | lista job |
| `GET` | `/presenze/import/jobs/{job_id}` | `inaz.import` | dettaglio job |
| `POST` | `/presenze/import/preview` | `inaz.import` | validazione senza persistenza |

Payload upload:

- `file`;
- `application_user_id` opzionale se il file contiene gia username/email;
- `date_from`, `date_to` opzionali;
- `dedupe_mode`: `skip`, `replace`, `upsert`.

### 6.4 Sync Inaz diretta

La superficie operativa primaria e `/elaborazioni/presenze-sync`, coerente con l'hub dei worker esterni e delle sync batch. Il dominio dati, le credenziali, i permessi e il contratto API restano Presenze; `/presenze/sync` e mantenuta come route legacy compatibile sulla stessa workspace.

| Metodo | Path | Permesso | Descrizione |
| --- | --- | --- | --- |
| `POST` | `/presenze/sync/jobs` | `inaz.sync` | avvia sync Playwright |
| `GET` | `/presenze/sync/jobs` | `inaz.sync` | lista sync |
| `GET` | `/presenze/sync/jobs/{job_id}` | `inaz.sync` | stato sync |
| `POST` | `/presenze/sync/jobs/{job_id}/cancel` | `inaz.sync` | richiesta stop best-effort |

Payload sync:

```json
{
  "application_user_id": 1,
  "date_from": "2026-05-01",
  "date_to": "2026-05-31",
  "headless": true,
  "dedupe_mode": "upsert"
}
```

### 6.5 Export

| Metodo | Path | Permesso | Descrizione |
| --- | --- | --- | --- |
| `GET` | `/presenze/export/giornaliere.xlsm` | `inaz.admin` | export sincrono legacy del file giornaliere `.xlsm` |
| `POST` | `/presenze/export/jobs/xlsm` | `inaz.admin` | crea job asincrono per export giornaliere `.xlsm` |
| `GET` | `/presenze/export/jobs/xlsm` | `inaz.admin` | storico job export giornaliere |
| `GET` | `/presenze/export/jobs/xlsm/{job_id}/artifacts/{artifact_name}` | `inaz.admin` | download artefatti `xlsm`, `summary`, `progress`, `log` |
| `GET` | `/presenze/export/straordinari/preview` | `inaz.giornaliere` | preview mese precedente dei giorni con extra effettivo per il collaboratore selezionato o associato all'utente corrente |
| `POST` | `/presenze/export/jobs/straordinari` | `inaz.giornaliere` | crea job asincrono per richiesta straordinari `.xlsx`, con motivazioni giornaliere compilate in dashboard |
| `GET` | `/presenze/export/jobs/straordinari` | `inaz.giornaliere` | storico job richiesta straordinari visibile secondo perimetro utente/admin |
| `GET` | `/presenze/export/jobs/straordinari/{job_id}/artifacts/{artifact_name}` | `inaz.giornaliere` | download artefatti `xlsx`, `summary`, `progress`, `log` |

La richiesta straordinari usa il template `Straordinari.xlsx` del progetto `presenze-scraper`/`inaz-scraper`: intestazione collaboratore in `F7`, mese in `F9`, anno in `I9`, righe compilabili `13..41`, totale `H42 = SUM(J13:J41)`. Il periodo e sempre il mese precedente rispetto alla data corrente di GAIA; il frontend consente la selezione del collaboratore agli utenti con visibilita completa e usa automaticamente il mapping personale per gli utenti viewer con un solo collaboratore associato.

### 6.5.1 Richiesta straordinari operatore

Il workflow operatore non usa `/presenze/export`: quella sezione resta dedicata agli export giornaliere amministrativi. La richiesta straordinari compilabile dall'utente e pubblicata nella dashboard self-service:

| Metodo | Path | Permesso | Descrizione |
| --- | --- | --- | --- |
| `GET` | `/me/presenze/straordinari/preview` | modulo `presenze` sull'utente corrente | preview mese precedente dei soli giorni extra/MPE del collaboratore mappato all'utente |
| `POST` | `/me/presenze/straordinari/export/xlsx` | modulo `presenze` sull'utente corrente | genera e scarica il modulo Excel compilato dal template `Straordinari.xlsx` |
| `POST` | `/me/presenze/straordinari/export/pdf` | modulo `presenze` sull'utente corrente | genera l'Excel e tenta conversione PDF via `LibreOffice`/`soffice`; se il binario non esiste ritorna `503` |

Frontend:

- rotta `/me/straordinari`;
- sidebar "La mia attivita" con voce `Richiesta straordinari`;
- checkbox per selezionare le giornate da includere;
- textarea motivazione per ciascuna giornata;
- filtri locali `Tutte`, `Solo pausa detratta`, `Senza rettifica`;
- badge informativo sulle righe rettificate per pausa pranzo non rilevata o allineate alla fascia post-pausa;
- pulsanti `Scarica Excel` e `Scarica PDF`.

Regola pausa richiesta straordinari:

- la regola si applica solo quando le timbrature complete mostrano una giornata lunga con prima entrata prima delle `12:00`, ultima uscita almeno alle `15:30`, span minimo `8h` e nessuna pausa singola di almeno `30` minuti;
- GAIA detrae dagli straordinari solo la quota di pausa mancante, quindi `0` minuti se la pausa e gia almeno `30`, `15` minuti se la pausa rilevata e `15`, `30` minuti se non esiste alcuna pausa intermedia;
- se la detrazione azzera lo straordinario, la giornata viene scartata dalla preview e dall'export;
- se la riga resta valida, la fascia `start_time/end_time` viene ricondotta alla coda della giornata in base alla durata residua, evitando di stampare nel modulo l'intera fascia entrata/uscita.
- la flessibilita di `10` minuti riguarda solo la fascia ordinaria di ingresso/uscita e non viene esposta come detrazione sugli straordinari: se la pausa e valida e la durata importata supera la coda post-pausa di massimo `10` minuti, GAIA ricondice la durata alla fascia reale dopo pausa. Esempio: `07:25-13:50`, pausa `14:20`, uscita `19:30` produce `05:10` di straordinario/banca ore, non `05:20`.

### 6.6 Configurazione operai

| Metodo | Path | Permesso | Descrizione |
| --- | --- | --- | --- |
| `GET` | `/presenze/configuration/operai-rules` | `inaz.admin` | lista o inizializza le regole operative per gruppi operai |
| `PATCH` | `/presenze/configuration/operai-rules/{id}` | `inaz.admin` | aggiorna minuti attesi, sabati previsti e soglia MPE del gruppo |

## 7. Permessi e sezioni

Aggiungere a `backend/app/scripts/bootstrap_sections.py`:

| Key | Label | Module | Min role |
| --- | --- | --- | --- |
| `inaz.dashboard` | `Inaz - Dashboard` | `inaz` | `viewer` |
| `inaz.giornaliere` | `Inaz - Giornaliere` | `inaz` | `viewer` |
| `inaz.import` | `Inaz - Import` | `inaz` | `admin` |
| `inaz.sync` | `Inaz - Sync portale` | `inaz` | `admin` |
| `inaz.review` | `Inaz - Review` | `inaz` | `reviewer` |
| `inaz.export` | `Inaz - Export` | `inaz` | `reviewer` |
| `inaz.admin` | `Inaz - Amministrazione` | `inaz` | `admin` |

Usare `require_module("presenze")` per gate di modulo e `require_section(...)` dove serve controllo fine.

## 8. UX proposta

Route principali:

- `/presenze`: dashboard con KPI mese corrente, record da rivedere, ultimi job;
- `/presenze/giornaliere`: tabella filtrabile e calendario;
- `/presenze/festivita`: gestione festivita ordinarie, soppresse e override lavorativi;
- `/presenze/recuperi`: dashboard HR/super admin per saldi, timeline e rettifiche;
- `/presenze/utenti/[id]`: dettaglio utente con timeline mensile;
- `/presenze/import`: redirect tecnico alla console sync in Elaborazioni;
- `/elaborazioni/presenze-sync`: avvio e monitor sync Inaz, autosync, retry e artefatti job;
- `/presenze/sync`: wrapper legacy compatibile della stessa console;
- `/presenze/settings`: credenziali/sessioni, solo admin.

Componenti attesi:

- calendario mensile compatto per utente;
- tabella giornaliere con badge stato/sorgente;
- pannello dettaglio con intervalli, raw payload e note;
- wizard import con preview, deduplica e conferma;
- monitor job con polling leggero ogni 2-5 secondi per job attivi.

Comportamenti operativi gia implementati:

- se `resolved_absence_cause === "ferie"`, in modale giornaliera `KM carburante` e `Reperibilita giornaliera` sono disabilitati;
- i capisettore possono validare la giornata ma non applicare rettifiche operative;
- le rettifiche HR dei recuperi entrano nel saldo solo dopo approvazione.
- la lista collaboratori mostra e filtra `operai_group`, per distinguere rapidamente operai agricoli e catasto/magazzino;
- il dettaglio collaboratore consente agli admin di correggere profilo contrattuale, gruppo operai e standard giornaliero;
- il dettaglio giornata mostra le timbrature dettaglio Inaz solo se aggiungono informazione rispetto alle coppie ricostruite o se sono necessarie per spiegare una timbratura autorizzata (`request_status = ACC`).

## 9. Piano implementativo

### Fase 1 - Fondazioni modulo

- creare `domain-docs/presenze/docs`;
- aggiungere `module_presenze` a `application_users` con migrazione Alembic;
- aggiornare model, schema, repository, bootstrap admin, frontend types e admin users UI;
- aggiungere sezioni bootstrap `inaz.*`;
- creare router vuoto `/presenze/health` o dashboard summary minima.

### Fase 2 - Data model e API base

- creare modelli ORM `PresenzeDailyRecord`, `PresenzeDailyInterval`, `PresenzeImportJob`;
- aggiungere migrazione Alembic;
- aggiungere schemas Pydantic;
- implementare repository con filtri e paginazione;
- implementare CRUD giornaliere e summary utente;
- test backend su permessi, filtri, deduplica e serializzazione.

### Fase 3 - Import file MVP

- implementare parser JSON compatibile con `OvertimeEntry` e `OvertimeRow`;
- supportare CSV generato da `presenze-straordinari`;
- nell'import assistito, risolvere inizialmente `application_users` tramite `application_user_id`, username o email e salvare sempre la FK risultante; username/email non devono essere propagati né riusati come fallback di correlazione o autorizzazione GATE;
- aggiungere endpoint preview e upload;
- salvare job con metriche e scarti;
- UI upload con preview.

### Fase 4 - Export

- portare la logica utile da `monthly_excel.py` e `populate_excel.py`;
- generare XLSX mensile per utente/periodo;
- mantenere template configurabile;
- aggiungere export CSV.

### Fase 5 - Sync Playwright controllata

- estrarre dal repo `presenze-scraper` un client interno o pacchetto riusabile;
- introdurre `PresenzeSyncJob`;
- eseguire sync con stato persistente, timeout e diagnostica;
- preferire worker dedicato se la sync supera tempi brevi o richiede browser persistente;
- mantenere import file come fallback operativo.

### Fase 6 - Review e audit

- stato `reviewed/approved/rejected`;
- note reviewer;
- storico modifiche principali;
- dashboard anomalie.

## 10. Test minimi

Backend:

- migrazione Alembic applicabile da database vuoto;
- `enabled_modules` include `presenze` quando `module_presenze=true`;
- super admin vede sempre modulo `presenze`;
- CRUD giornaliere con utente non autorizzato restituisce `403`;
- import preview normalizza `HH:MM` in minuti;
- import upsert non duplica stesso giorno/hash;
- export XLSX contiene date, motivazione, inizio, fine e durata.

Frontend:

- sidebar mostra modulo Presenze solo se abilitato;
- lista giornaliere gestisce loading, errore, vuoto e paginazione;
- import page mostra warning duplicati;
- calendario non rompe layout su mobile.

## 11. Rischi

- il DOM Inaz e fragile: selettori e funzioni JS possono cambiare;
- login Inaz puo richiedere MFA o passaggi manuali;
- sync Playwright dentro API puo saturare il processo web;
- matching tra utente Inaz e `application_users` va definito con un campo stabile;
- i file Excel legacy possono contenere formule/stili da preservare con attenzione.

Mitigazioni:

- import file come primo canale stabile;
- diagnostica raw su ogni job fallito;
- worker separato per sync browser;
- mapping utente configurabile;
- test con fixture HTML/JSON, non solo live portal.

Il mapping assistito distingue quattro esiti: alta confidenza applicabile in
batch, revisione manuale, nessun match e conflitto bloccato. Il batch non deve
applicare match medi o bassi e non deve consentire che due collaboratori
reclamino la stessa identita GAIA. Gli utenti inattivi restano identita
anagrafiche valide senza acquisire login o accesso al modulo.

## 12. Prompt Codex operativo

```text
Lavora nel repository GAIA mantenendo il backend come monolite modulare.
Crea il nuovo modulo `inaz` per gestire le giornaliere degli utenti presenti in
`application_users`.

Regole:
- nuovo codice backend sotto `backend/app/modules/presenze/`;
- nuove route sotto prefisso `/presenze`;
- aggiungi `module_presenze` a `application_users` con migrazione Alembic, model,
  schemas auth/users, repository utenti, frontend types e UI admin utenti;
- aggiungi sezioni `inaz.*` in `backend/app/scripts/bootstrap_sections.py`;
- collega ogni giornaliera a `application_users.id`;
- implementa prima import file e CRUD giornaliere, poi sync Playwright;
- non salvare credenziali Inaz in chiaro e non committare storage state Playwright;
- usa job persistenti per import/sync monitorabili;
- aggiorna o aggiungi test backend mirati e tipi/frontend API quando tocchi superfici pubbliche.

Riferimento Inaz:
- login URL `https://serviziweb.inaz.it/portalecbo/default.aspx`;
- calendario nel frame contenente `HomeCliente/Home.aspx`;
- dettaglio giorno nel frame contenente `Cartellino_Giorno.aspx`;
- funzioni pagina osservate: `WdgtCalendarMove(step)`, `WdgtCalendarOpen(cell)`,
  `ChiudiFunzione2('')`;
- output sorgente utile: `day`, `start_time`, `end_time`, `duration`,
  `motivation`, `kind`, `matched_text`, `hours`, `cells`.
```

## 13. File GAIA da toccare nelle prime iterazioni

- `backend/app/models/application_user.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/users.py`
- `backend/app/repositories/application_user.py`
- `backend/app/services/bootstrap_admin.py`
- `backend/app/services/permission_resolver.py`
- `backend/app/scripts/bootstrap_sections.py`
- `backend/app/db/base.py`
- `backend/app/api/router.py`
- `backend/alembic/versions/<nuova_revision>_add_inaz_module.py`
- `frontend/src/types/api.ts`
- `frontend/src/lib/api.ts` o nuovo `frontend/src/lib/api.ts`
- `frontend/src/components/layout/module-sidebar.tsx`
- `frontend/src/app/presenze/*`
- `backend/tests/test_presenze_*.py`
