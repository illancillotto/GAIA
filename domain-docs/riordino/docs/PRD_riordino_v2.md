# GAIA Riordino — Product Requirements Document v2

## Changelog rispetto a v1
- Aggiunta matrice step template Fase 1 e Fase 2 (sezione 8)
- Definito modello branching: tutti gli step presenti, rami non pertinenti marcati `skipped` (sezione 8.3)
- Aggiunta entità `RiordinoAppeal` per ricorsi (sezione 10)
- Definita gerarchia territoriale: Comune → Maglia → Lotto → Particelle (sezione 7.1)
- Definito storage documenti: filesystem locale (sezione 9.6)
- Chiarita integrazione auth: FK verso tabella application_users esistente (sezione 6)
- Chiarita integrazione soggetti: modulo utenze GAIA esistente (sezione 6)
- Aggiunto sistema scadenze con notifiche in-app (sezione 8.4)
- GIS MVP: solo link manuale (sezione 5.2)
- PREGEO/DOCTE/estratto mappa: step workflow con documento obbligatorio (sezione 8.1)
- Aggiunto campo `outcome_code` + `outcome_notes` su step decisionali (sezione 10)

---

## 1. Contesto

GAIA è la piattaforma interna del Consorzio di Bonifica dell'Oristanese. Backend monolitico modulare FastAPI, frontend unico Next.js, database PostgreSQL condiviso.

Path canonici modulo Riordino:
- backend: `backend/app/modules/riordino/`
- frontend: `frontend/src/app/riordino/`
- docs: `domain-docs/riordino/docs/`

Il modulo digitalizza il processo di riordino catastale, oggi frammentato tra file, portali esterni e conoscenza operativa implicita.

---

## 2. Visione

Un sistema unico per governare il procedimento di riordino dalla fase istruttoria fino all'aggiornamento GIS finale, con tracciabilità completa, gestione eccezioni strutturata e audit trail.

---

## 3. Obiettivo di prodotto

- Apertura e gestione pratiche di riordino
- Governo delle due fasi procedurali (Approvazione Decreto → Attuazione Decreto)
- Tracciamento step, decisioni, eccezioni, documenti, esiti e attori
- Collegamento dati catastali, soggetti, lotti, particelle
- Avanzamento controllato con stati e autorizzazioni
- Audit completo delle operazioni

---

## 4. Problemi da risolvere

### Stato attuale
- Flusso frammentato tra fogli, note, portali esterni, memoria operatori
- Nessun tracking strutturato di step, esiti, tempi, responsabilità
- Difficoltà a ricostruire stato pratica e motivazioni decisioni
- Eccezioni catastali gestite in modo non omogeneo
- Scollamento tra fase amministrativa, attuazione tecnica e GIS

### Esiti attesi
- Pratica univoca consultabile end-to-end
- Ogni step con stato, responsabile, timestamp, documenti
- Storico decisioni e eccezioni
- Dashboard avanzamento e colli di bottiglia
- Base dati coerente per reporting

---

## 5. Scope funzionale

### 5.1 In scope

**A. Gestione pratiche Riordino**
- Creazione pratica con metadati: titolo, codice, comune, maglia, lotto, descrizione, responsabile
- Collegamento a soggetti (via modulo utenze), particelle, documenti
- Stato generale pratica

**B. Fase 1 — Approvazione Decreto**
Step definiti in sezione 8.1.

**C. Fase 2 — Attuazione Decreto**
Step definiti in sezione 8.1.

**D. Gestione ricorsi (entità dedicata)**
- Entità `RiordinoAppeal` con: ricorrente, data presentazione, scadenza, commissione, esito, documenti
- Collegamento a pratica e fase 1

**E. Workflow e stati**
- Stati pratica, fase, step (sezione 11)
- Regole avanzamento (sezione 8.3)
- Scadenze con notifiche in-app (sezione 8.4)
- Audit trail completo

**F. Gestione documentale**
- Upload per pratica/fase/step
- Classificazione, versione, preview metadati
- Storage filesystem locale

**G. GIS MVP**
- Link manuale a riferimenti GIS
- Registrazione aggiornamenti come eventi
- Nessuna sync automatica nel primo rilascio

**H. Dashboard e report**
- Elenco pratiche, avanzamento per fase, pratiche bloccate, issue aperte, ultimi eventi
- KPI temporali rimandati post-MVP (solo conteggi per MVP)

### 5.2 Out of scope (primo rilascio)
- Automazione PREGEO/DOCFA da GAIA (sono step manuali con allegato)
- Visualizzazione mappa embedded (futuro)
- Sync automatica GIS
- Firma digitale embedded
- Portale pubblico esterno
- BPMN engine enterprise
- KPI temporali (tempo medio fase, tempo risoluzione issue)
- Gestione frazionamenti multi-lotto (futuro)

---

## 6. Attori utente

Tutti gli utenti sono nella tabella `application_users` esistente. I soggetti (proprietari, intestatari) sono gestiti dal modulo utenze.

### Ruoli modulo Riordino

| Ruolo | Permessi |
|---|---|
| `admin` | Full CRUD, configurazione, override transizioni |
| `riordino_manager` | Create/update pratiche, approvazione passaggi fase, chiusura issue, dashboard completa |
| `riordino_operator` | Aggiornamento step assegnati, upload documenti, apertura issue, aggiornamento task |
| `riordino_tecnico` | Gestione step tecnici (PREGEO, DOCTE, estratto mappa, GIS), chiusura anomalie tecniche |
| `viewer` | Sola lettura |

I ruoli sono mappati sulla tabella ruoli GAIA esistente. Il modulo riordino registra i propri permessi nel sistema centralizzato.

### Transizioni per ruolo

| Azione | manager | operator | tecnico |
|---|---|---|---|
| Creare pratica | ✓ | | |
| Assegnare pratica | ✓ | | |
| Avanzare step | ✓ | ✓ (propri) | ✓ (propri) |
| Approvare passaggio fase | ✓ | | |
| Aprire issue | ✓ | ✓ | ✓ |
| Chiudere issue | ✓ | | ✓ (tecniche) |
| Upload documenti | ✓ | ✓ | ✓ |
| Archiviare pratica | ✓ | | |

---

## 7. Modello operativo

### 7.1 Gerarchia territoriale

```
Comune
 └── Maglia
      └── Lotto (obiettivo: 1 proprietario per lotto)
           └── Particella (N per lotto, con foglio/particella/subalterno)
```

Una pratica opera a livello di **lotto**. Ogni pratica ha:
- `municipality` (comune)
- `grid_code` (maglia)
- `lot_code` (lotto)
- N `riordino_parcel_links` (particelle nel lotto)

### 7.2 Pratica come entità principale

Una pratica contiene:
- Metadati principali + gerarchia territoriale
- Fase corrente
- Stato corrente
- Soggetti collegati (via modulo utenze)
- Particelle/lotti collegati
- Step e task
- Documenti
- Ricorsi (Fase 1)
- Issue/anomalie
- Eventi audit
- Riferimenti GIS (link manuali)

### 7.3 Fasi

Due fasi sequenziali:
1. **Fase 1 — Approvazione Decreto**
2. **Fase 2 — Attuazione Decreto**

Regola: Fase 2 `in_progress` solo se Fase 1 `completed`.

### 7.4 Step di fase

Ogni fase ha step predefiniti generati da template (sezione 8.1).
Tutti gli step vengono creati alla creazione pratica.
Gli step dei rami condizionali non pertinenti vengono marcati `skipped` con motivazione.

### 7.5 Eccezioni

Anomalie gestite come **issue** con tipologia, severità, descrizione, impatto, azione correttiva.
Ricorsi gestiti come entità dedicata **appeal**.

---

## 8. Step template e workflow

### 8.1 Matrice step template

#### Fase 1 — Approvazione Decreto

| Seq | Codice | Titolo | Obbligatorio | Condizione | Documento richiesto | Decisionale |
|-----|--------|--------|-------------|------------|--------------------|----|
| 1 | `F1_STUDIO_PIANO` | Studio del Piano | sì | — | no | no |
| 2 | `F1_INDAGINE` | Indagine: raccolta dati utenti e identificazione lotto | sì | — | no | no |
| 3 | `F1_ELABORAZIONE` | Elaborazione | sì | — | no | no |
| 4 | `F1_PUBBLICAZIONE` | Pubblicazione Piano da parte del Comune | sì | — | sì (atto pubblicazione) | no |
| 5 | `F1_OSSERVAZIONI` | Periodo osservazioni e ricorsi (90gg) | sì | — | no | sì |
| 6 | `F1_RICORSI` | Gestione ricorsi | no | `F1_OSSERVAZIONI.outcome = 'ricorsi_presenti'` | sì (documenti ricorso) | no |
| 7 | `F1_COMMISSIONE` | Nomina commissione regionale e verifiche | no | `F1_RICORSI` attivo | sì (verbale commissione) | no |
| 8 | `F1_RISOLUZIONE` | Risoluzione e pubblicazione Piano/Decreto | sì | — | sì (decreto) | no |
| 9 | `F1_TRASCRIZIONE` | Trascrizione a cura del consorzio (entro 30gg) | sì | — | sì (nota trascrizione) | no |
| 10 | `F1_CONSERVATORIA` | Note trascrizione in Conservatoria | sì | — | sì (attestazione) | no |
| 11 | `F1_VOLTURA` | Voltura catastale tramite AdE | sì | — | sì (ricevuta voltura) | no |
| 12 | `F1_CARICAMENTO` | Caricamento sistema e aggiornamento GIS/Mappa | sì | — | no | no |
| 13 | `F1_OUTPUT` | Output Fase 1: dati validati e caricati | sì | — | no | no |

#### Fase 2 — Attuazione Decreto

| Seq | Codice | Titolo | Obbligatorio | Condizione / Branch | Documento richiesto | Decisionale |
|-----|--------|--------|-------------|---------------------|--------------------|----|
| 1 | `F2_SCARICO_DATI` | Scarico dati catastali particelle del lotto | sì | — | no | no |
| 2 | `F2_CSV` | Disponibilità file CSV (particelle, lotti, proprietari) | sì | — | sì (file CSV) | no |
| 3 | `F2_VERIFICA` | Verifica qualità/coerenza, classe coltivazione, intestazioni | sì | — | no | sì |
| 4 | `F2_ESTRATTO_MAPPA` | Richiesta estratto di mappa | sì | `F2_VERIFICA.outcome = 'conforme'` | sì (estratto mappa) | no |
| 5 | `F2_FUSIONE` | Fusione porzioni: unione quote stessa qualità (istanza unica) | no | branch=`anomalia`, `F2_VERIFICA.outcome = 'non_conforme'` AND tipo=`fusione` | sì (istanza) | no |
| 6 | `F2_DOCTE` | Variazione porzioni tramite DOCTE | no | branch=`anomalia`, `F2_VERIFICA.outcome = 'non_conforme'` AND tipo=`variazione` | sì (documento DOCTE) | no |
| 7 | `F2_PREGEO` | PREGEO per gestione mappali e unificazione qualità | sì | — | sì (file PREGEO) | no |
| 8 | `F2_MAPPALE_UNITO` | Ottenimento Mappale Unito | sì | — | sì (mappale unito) | no |
| 9 | `F2_RIPRISTINO` | Ripristino porzioni per colture originali | no | branch=`anomalia`, `F2_VERIFICA.outcome = 'non_conforme'` AND tipo=`fusione` | no | no |
| 10 | `F2_ATTI_RT` | Atti di aggiornamento RT (contestuali) | sì | — | sì (atti RT) | no |
| 11 | `F2_AGG_GIS` | Aggiornamento GIS/Mappa nei sistemi | sì | — | no | no |
| 12 | `F2_DOCUMENTO_FINALE` | Generazione pratica, protocollo e documento finale | sì | — | sì (documento finale) | no |

**Regola branching Fase 2**: alla creazione pratica, tutti gli step vengono generati. Quando lo step `F2_VERIFICA` viene completato:
- Se `outcome = 'conforme'`: gli step con branch=`anomalia` vengono marcati `skipped` automaticamente
- Se `outcome = 'non_conforme'`: l'operatore specifica il `tipo` anomalia e il sistema attiva gli step pertinenti, skipping gli altri del branch `anomalia`

### 8.2 Step decisionali

Gli step marcati come "Decisionale = sì" hanno due campi aggiuntivi:
- `outcome_code`: codice esito strutturato (enum per step). Es: `conforme`, `non_conforme`, `ricorsi_presenti`, `nessun_ricorso`
- `outcome_notes`: note libere motivazione

L'outcome dello step decisionale guida l'attivazione/skip degli step condizionali successivi.

### 8.3 Regole di avanzamento

1. Uno step può passare a `done` solo se:
   - i campi obbligatori sono completi (outcome per step decisionali, documento per step con doc richiesto)
   - non ci sono issue `blocking` collegate allo step
2. Uno step `skipped` deve avere `skip_reason` valorizzato
3. Il passaggio da Fase 1 a Fase 2 richiede:
   - tutti gli step obbligatori di Fase 1 in stato `done` o `skipped` con motivazione
   - nessuna issue `blocking` aperta in Fase 1
   - nessun ricorso (`appeal`) in stato `open`
   - approvazione esplicita da `riordino_manager`
4. La chiusura pratica richiede:
   - Fase 2 `completed`
   - nessuna issue aperta
   - approvazione da `riordino_manager`

### 8.4 Sistema scadenze e notifiche

Il sistema gestisce scadenze calcolate:

| Evento | Scadenza | Notifica |
|--------|----------|----------|
| Apertura periodo osservazioni (`F1_OSSERVAZIONI`) | +90 giorni dalla data pubblicazione | Notifica in-app a 30gg, 7gg, 1g dalla scadenza |
| Trascrizione (`F1_TRASCRIZIONE`) | +30 giorni dalla data decreto | Notifica in-app a 7gg, 1g |
| Step con `due_at` impostato | data impostata | Notifica in-app a 7gg, 1g |

Le notifiche sono in-app (tabella `riordino_notifications` o sistema notifiche GAIA se esiste). Nessuna email/PEC nel primo rilascio.

---

## 9. Requisiti funzionali dettagliati

### 9.1 Creazione pratica

Campi richiesti:
- `title` (obbligatorio)
- `code` (generato automaticamente: `RIO-{ANNO}-{PROGRESSIVO}`)
- `municipality` (obbligatorio, da dizionario)
- `grid_code` (maglia, obbligatorio)
- `lot_code` (lotto, obbligatorio)
- `description`
- `owner_user_id` (responsabile, obbligatorio, FK → application_users.id (Integer))

Alla creazione:
1. Pratica in stato `draft`
2. Vengono generate le due fasi (Fase 1 `not_started`, Fase 2 `not_started`)
3. Vengono generati tutti gli step da template (sezione 8.1), stato `todo`
4. Viene registrato evento audit `practice_created`

### 9.2 Template step

I template sono configurabili in tabella `riordino_step_templates`:
- `id`, `phase_code`, `code`, `title`, `sequence_no`, `is_required`, `branch`, `activation_condition`, `requires_document`, `is_decision`, `outcome_options` (JSON)

Alla creazione pratica il sistema copia i template attivi in `riordino_steps`.

### 9.3 Gestione ricorsi

Entità dedicata `RiordinoAppeal`:
- `id`
- `practice_id` (FK)
- `phase_id` (FK, sempre Fase 1)
- `step_id` (FK, sempre `F1_RICORSI`)
- `appellant_subject_id` (FK → ana_subjects.id (UUID))
- `appellant_name` (denormalizzato per consultazione rapida)
- `filed_at` (data presentazione)
- `deadline_at` (scadenza)
- `commission_name` (commissione nominata)
- `commission_date` (data nomina)
- `status` (`open`, `under_review`, `resolved_accepted`, `resolved_rejected`, `withdrawn`)
- `resolution_notes`
- `resolved_at`
- `created_by`, `created_at`, `updated_at`

Documenti del ricorso collegati via `riordino_documents` con `appeal_id`.

### 9.4 Gestione issue/anomalie

Come da v1, con aggiunta:
- `issue_category`: `administrative`, `technical`, `cadastral`, `documentary`, `gis`
- Le issue tecniche (anomalie catastali Fase 2) possono essere chiuse anche da `riordino_tecnico`

### 9.5 GIS MVP

Entità `riordino_gis_links`:
- Link manuale: operatore registra `layer_name`, `feature_id`, `geometry_ref`, `notes`
- Registrazione aggiornamento: step `F2_AGG_GIS` con evento audit
- Nessuna sync automatica, nessuna mappa embedded

### 9.6 Storage documenti

- Path: `/data/gaia/riordino/{practice_id}/{phase_code}/{step_code}/{filename_uuid}.{ext}`
- Limiti: max 50MB per file, MIME accettati configurabili (default: pdf, doc, docx, xls, xlsx, csv, jpg, png, tif, dwg, dxf, zip)
- Versionamento: nuovo record `riordino_documents` con `version_no` incrementale, vecchia versione non cancellata
- Soft-delete: campo `deleted_at` nullable, i file non vengono cancellati fisicamente

### 9.7 Cancellazione pratica

- Possibile solo in stato `draft`
- Solo `admin` o `riordino_manager`
- Soft-delete: `deleted_at` timestamp
- Evento audit `practice_deleted`

### 9.8 Concurrency

- Optimistic locking con campo `version` (integer) su `riordino_practices`, `riordino_steps`, `riordino_issues`
- L'API restituisce 409 Conflict se la versione non corrisponde

---

## 10. Entità di dominio

### RiordinoPractice
Pratica principale.

### RiordinoPhase
Istanza fase (2 per pratica).

### RiordinoStep
Step operativo generato da template. Include `outcome_code`, `outcome_notes`, `skip_reason`, `branch`.

### RiordinoTask
Task operativo figlio di step. Per attività manuali/tecniche che non sono step di fase.

### RiordinoAppeal ← NUOVO
Ricorso con dati specifici (ricorrente, scadenza, commissione, esito).

### RiordinoIssue
Anomalia, eccezione o blocco. Con `issue_category`.

### RiordinoDocument
Documento allegato e classificato. Con `appeal_id` opzionale e soft-delete.

### RiordinoParcelLink
Particella nel lotto (foglio/particella/subalterno/classe).

### RiordinoPartyLink
Relazione pratica ↔ soggetto (via modulo utenze).

### RiordinoGisLink
Link manuale a oggetti GIS.

### RiordinoEvent
Timeline/audit eventi.

### RiordinoChecklistItem
Checklist per step. Campi: `id`, `step_id`, `label`, `is_checked`, `checked_by`, `checked_at`, `is_blocking` (se true, step non chiudibile senza check).

### RiordinoStepTemplate
Template configurabile degli step per fase. Seed iniziale, modificabile da admin.

### RiordinoNotification
Notifica in-app per scadenze e assegnazioni. Campi: `id`, `user_id`, `practice_id`, `type`, `message`, `is_read`, `created_at`.

---

## 11. Stati

### 11.1 Stato pratica
`draft` → `open` → `in_review` → `completed` → `archived`
`open` → `blocked` → `open`
Cancellazione solo da `draft` (soft-delete).

### 11.2 Stato fase
`not_started` → `in_progress` → `completed`
`in_progress` → `blocked` → `in_progress`

### 11.3 Stato step
`todo` → `in_progress` → `done`
`todo` → `skipped` (con `skip_reason`)
`in_progress` → `blocked` → `in_progress`
`done` → `in_progress` (riapertura, solo manager, con evento audit)

### 11.4 Stato task
`todo` → `in_progress` → `done`
`in_progress` → `blocked` → `in_progress`

### 11.5 Severità issue
`low`, `medium`, `high`, `blocking`

### 11.6 Stato appeal
`open` → `under_review` → `resolved_accepted` | `resolved_rejected`
`open` → `withdrawn`

---

## 12. Regole di business

1. Una pratica non può avere più di una fase attiva contemporaneamente
2. Fase 2 si apre solo dopo chiusura valida Fase 1 (tutti step obbligatori done, no issue blocking, no appeal open)
3. Issue `blocking` impedisce chiusura step/fase correlati
4. Ogni passaggio di fase genera evento audit
5. Documenti versionati, mai cancellati fisicamente
6. Step obbligatori non eliminabili, solo `skipped` con motivazione da manager
7. Aggiornamenti GIS tracciati come evento pratica
8. Ogni ricorso deve avere esito esplicito o stato `open`/`withdrawn`
9. Step decisionali richiedono `outcome_code` per chiusura
10. Soft-delete su pratiche (solo da draft) e documenti
11. Optimistic locking su pratiche, step, issue

---

## 13. UI/UX target

### Sezioni frontend
- `/riordino` → dashboard modulo
- `/riordino/pratiche` → elenco pratiche
- `/riordino/pratiche/[id]` → workspace pratica
- `/riordino/configurazione` (solo admin)

### Workspace pratica
- Header: codice, titolo, stato, fase, owner, comune/maglia/lotto
- Progress workflow: stepper visuale con stato per step
- Pannello step corrente con azioni
- Pannello ricorsi (Fase 1)
- Pannello issue/anomalie
- Pannello documenti
- Pannello soggetti/particelle
- Pannello GIS links
- Timeline eventi
- Badge colore per status, fase, severità issue
- Notifiche scadenze visibili

---

## 14. API

### Pratiche
- `POST /api/riordino/practices` — crea pratica
- `GET /api/riordino/practices` — lista con filtri
- `GET /api/riordino/practices/{id}` — dettaglio completo
- `PATCH /api/riordino/practices/{id}` — aggiorna metadati
- `DELETE /api/riordino/practices/{id}` — soft-delete (solo draft)
- `POST /api/riordino/practices/{id}/archive` — archivia

### Workflow
- `POST /api/riordino/practices/{id}/steps/{step_id}/advance` — avanza step
- `POST /api/riordino/practices/{id}/steps/{step_id}/skip` — skip con motivazione
- `POST /api/riordino/practices/{id}/steps/{step_id}/reopen` — riapri (manager)
- `POST /api/riordino/practices/{id}/phases/{phase_id}/complete` — chiudi fase
- `POST /api/riordino/practices/{id}/phases/{phase_id}/start` — avvia fase

### Ricorsi
- `POST /api/riordino/practices/{id}/appeals` — crea ricorso
- `GET /api/riordino/practices/{id}/appeals` — lista ricorsi
- `PATCH /api/riordino/practices/{id}/appeals/{appeal_id}` — aggiorna
- `POST /api/riordino/practices/{id}/appeals/{appeal_id}/resolve` — chiudi con esito

### Issue
- `POST /api/riordino/practices/{id}/issues` — crea
- `GET /api/riordino/practices/{id}/issues` — lista
- `PATCH /api/riordino/practices/{id}/issues/{issue_id}` — aggiorna
- `POST /api/riordino/practices/{id}/issues/{issue_id}/close` — chiudi

### Documenti
- `POST /api/riordino/practices/{id}/documents` — upload
- `GET /api/riordino/practices/{id}/documents` — lista (filtri: fase, step, tipo)
- `GET /api/riordino/documents/{doc_id}/download` — download
- `DELETE /api/riordino/documents/{doc_id}` — soft-delete

### GIS
- `POST /api/riordino/practices/{id}/gis-links` — crea link
- `GET /api/riordino/practices/{id}/gis-links` — lista
- `PATCH /api/riordino/gis-links/{link_id}` — aggiorna

### Timeline
- `GET /api/riordino/practices/{id}/events` — lista eventi

### Dashboard
- `GET /api/riordino/dashboard` — riepilogo: conteggi per stato, fase, issue, ultimi eventi

### Configurazione (admin)
- `GET/POST/PATCH/DELETE /api/riordino/config/step-templates`
- `GET/POST/PATCH/DELETE /api/riordino/config/document-types`
- `GET/POST/PATCH/DELETE /api/riordino/config/issue-types`
- `GET /api/riordino/config/municipalities` — dizionario comuni

### Notifiche
- `GET /api/riordino/notifications` — lista notifiche utente
- `POST /api/riordino/notifications/{id}/read` — segna come letta

---

## 15. Requisiti non funzionali

### Sicurezza
- Auth centralizzata GAIA (tabella users esistente)
- Autorizzazioni per ruolo modulo (sezione 6)
- Audit trail per operazioni critiche
- Soft-delete, nessuna cancellazione fisica

### Performance
- Lista pratiche < 2s su dataset tipico
- Dettaglio pratica con lazy loading blocchi pesanti (documenti, timeline)
- Upload robusto e ripetibile

### Affidabilità
- Optimistic locking per concurrency
- Nessuna perdita allegati o eventi
- Retry sicuro su upload

### Coerenza architetturale
- Monolite modulare, nessun servizio separato
- Migration Alembic centralizzate
- FK verso users GAIA, soggetti via modulo utenze

---

## 16. Milestone di rilascio

### M1 — Fondazione dominio
- Step templates configurabili
- Entità base + migration
- CRUD pratiche
- Generazione fasi/step da template
- Timeline base
- **Done when**: pratica creabile via API con fasi e step generati

### M2 — Workflow Fase 1
- Avanzamento step Fase 1
- Gestione ricorsi (entità appeal)
- Scadenze con notifiche
- Upload documenti
- Validazione passaggio a Fase 2
- **Done when**: Fase 1 interamente percorribile, blocco corretto se prerequisiti mancanti

### M3 — Workflow Fase 2
- Step tecnici (PREGEO, DOCTE, estratto mappa)
- Branching condizionale (skip automatico)
- Issue management con anomalie catastali
- GIS links manuali
- Chiusura pratica
- **Done when**: percorso standard e anomalo entrambi gestibili

### M4 — Frontend
- Dashboard, lista, workspace pratica
- Pannelli: step, ricorsi, issue, documenti, GIS, timeline
- Notifiche in-app
- **Done when**: operatore gestisce pratica senza strumenti esterni

### M5 — Hardening
- Permessi fini
- Export dossier pratica
- Seed demo
- Test integrazione
- **Done when**: suite test verde, permessi verificati

---

## 17. Criteri di accettazione MVP

1. Pratica creabile con generazione automatica fasi/step
2. Fase 1 percorribile con gestione ricorsi
3. Fase 2 percorribile con branching condizionale
4. Documenti allegabili e versionati
5. Issue/anomalie collegabili
6. Timeline consultabile
7. Passaggi fase bloccati se prerequisiti mancanti
8. Dashboard e liste filtrabili
9. Audit trail completo
10. Notifiche scadenze funzionanti
