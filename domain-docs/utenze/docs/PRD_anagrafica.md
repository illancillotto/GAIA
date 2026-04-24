# GAIA Anagrafica — Gestione Anagrafiche Soggetti del Consorzio
## Product Requirements Document v1.0

> **Regola repository**
> GAIA Anagrafica non introduce un backend separato. Usa il backend monolite modulare condiviso.

> Consorzio di Bonifica dell'Oristanese — Marzo 2026
> Documento interno — uso riservato

---

## 1. Overview del modulo

GAIA Anagrafica è il modulo di gestione delle anagrafiche dei soggetti del Consorzio di Bonifica dell'Oristanese all'interno della piattaforma GAIA. Fornisce un registro centralizzato di tutti i soggetti (persone fisiche e giuridiche) che intrattengono rapporti con il Consorzio, con importazione guidata dall'archivio NAS esistente, classificazione dei documenti allegati e strumenti di ricerca avanzata.

> **Posizione nel sistema**
> GAIA Anagrafica è il quinto modulo della piattaforma. Condivide autenticazione JWT, database PostgreSQL e infrastruttura Docker con gli altri moduli GAIA. Si integra con GAIA Catasto per la correlazione tra soggetti e visure, e con GAIA Accessi per l'associazione utenti-permessi NAS.
>
> Come gli altri moduli GAIA, l'accesso ad Anagrafica dovrà essere integrato anche nel sistema di abilitazione moduli e sezioni già esistente: flag modulo su `application_users`, sezioni bootstrap, sidebar frontend e home dei moduli.

### 1.1 Contesto: Archivio NAS esistente

Il patrimonio documentale da gestire risiede attualmente su NAS Synology all'indirizzo:

```
smb://nas_cbo.local/settore catasto/ARCHIVIO/
```

La struttura dell'archivio è:

```
ARCHIVIO/
├── A/
│   ├── Cognome_Nome_CODFIS/
│   │   ├── documento1.pdf
│   │   └── ...
│   └── ...
├── B/
├── ...
└── Z/
```

Dati di contesto (rilevati a marzo 2026):
- **27 cartelle** di primo livello (lettere A–Z + cartelle speciali come TELERILEVAMENTO)
- **~6.248 cartelle** anagrafica (una per soggetto)
- **~26.012 file** totali (~30k incluse sottocartelle)
- **~9,3 GiB** occupati su volume da 3,9 TiB
- Nomenclatura cartelle soggetto: `Cognome_Nome_CODFIS` o `RagioneSociale_PIVA`
- Contenuto eterogeneo: PDF pratiche, ingiunzioni, estratti debito, relazioni di notifica, GIF, sottocartelle annidate

### 1.2 Obiettivi

- Centralizzare l'anagrafica dei soggetti in un registro strutturato e ricercabile
- Importare progressivamente le cartelle NAS con classificazione automatica e manuale dei documenti
- Classificare e catalogare i ~26.000 file in categorie omogenee
- Collegare ogni soggetto ai propri documenti allegati, con link diretto al file sul NAS
- Integrare con GAIA Catasto per correlare soggetti a visure e pratiche
- Fornire strumenti di ricerca per operatori e responsabili di settore
- Supportare l'operatività quotidiana del Consorzio (pratiche, ingiunzioni, corrispondenza)

### 1.3 Non obiettivi MVP

- OCR automatico del contenuto dei PDF
- Firma digitale dei documenti
- Workflow di approvazione pratiche
- Notifiche push o email automatiche
- Portale self-service per i soggetti esterni
- Sincronizzazione bidirezionale con il NAS
- Scrittura o modifica di file sul NAS

Nota: il modulo è read-only verso il NAS ma può scrivere nel database GAIA e, se abilitato, nello storage locale GAIA per documenti caricati manualmente.

---

## 2. Requisiti funzionali

### 2.1 Anagrafica soggetti

Il nucleo del modulo è il registro dei soggetti. Ogni soggetto ha una scheda completa con dati anagrafici e documentali.

| Requisito | Priorità | Descrizione |
|-----------|----------|-------------|
| RF-ANA-01 | MUST | CRUD completo: creazione, lettura, modifica, disattivazione logica |
| RF-ANA-02 | MUST | Distinzione tra persona fisica e persona giuridica (diverso set di campi) |
| RF-ANA-03 | MUST | Ricerca full-text per cognome, nome, codice fiscale, partita IVA, ragione sociale |
| RF-ANA-04 | MUST | Collegamento a cartella NAS originale (path smb://) per ogni soggetto |
| RF-ANA-05 | MUST | Import automatico da struttura cartelle NAS con parsing nome cartella |
| RF-ANA-06 | MUST | Gestione documenti allegati con classificazione per tipo |
| RF-ANA-07 | SHOULD | Storico modifiche anagrafica interrogabile: audit log operativo e snapshot puntuali dei dati persona |
| RF-ANA-08 | SHOULD | Collegamento a pratiche e visure GAIA Catasto |
| RF-ANA-09 | COULD | Deduplicazione soggetti (stesso CF/PIVA con cartelle diverse) |
| RF-ANA-10 | COULD | Export anagrafica in CSV/XLSX con filtri |

### 2.2 Campi anagrafica — Persona Fisica

| Campo | Obbligatorio | Note |
|-------|-------------|------|
| `cognome` | MUST | Estratto dal nome cartella |
| `nome` | MUST | Estratto dal nome cartella |
| `codice_fiscale` | MUST | Estratto dal nome cartella; validazione formato |
| `data_nascita` | SHOULD | Inserimento manuale post-import |
| `comune_nascita` | SHOULD | Inserimento manuale post-import |
| `indirizzo` | SHOULD | Residenza/domicilio |
| `comune_residenza` | SHOULD | |
| `cap` | SHOULD | |
| `email` | COULD | |
| `telefono` | COULD | |
| `note` | COULD | Campo libero |

### 2.3 Campi anagrafica — Persona Giuridica

| Campo | Obbligatorio | Note |
|-------|-------------|------|
| `ragione_sociale` | MUST | Estratta dal nome cartella |
| `partita_iva` | MUST | Estratta dal nome cartella |
| `codice_fiscale` | SHOULD | Può coincidere con P.IVA |
| `forma_giuridica` | SHOULD | Srl, Spa, Soc. Agr. Semplice, ecc. |
| `sede_legale` | SHOULD | |
| `comune_sede` | SHOULD | |
| `cap` | SHOULD | |
| `email_pec` | COULD | |
| `telefono` | COULD | |
| `note` | COULD | |

### 2.4 Gestione documenti

| Requisito | Priorità | Descrizione |
|-----------|----------|-------------|
| RF-DOC-01 | MUST | Catalogazione dei file NAS per soggetto con tipo documento |
| RF-DOC-02 | MUST | Classificazione tipi documento (vedi sezione 2.5) |
| RF-DOC-03 | MUST | Link diretto al file originale su NAS (path smb://) |
| RF-DOC-04 | MUST | Visualizzazione metadati: nome file, dimensione, data modifica, tipo |
| RF-DOC-05 | SHOULD | Upload di nuovi documenti associati al soggetto (solo storage locale GAIA, mai NAS) |
| RF-DOC-06 | SHOULD | Preview PDF inline per file già importati |
| RF-DOC-07 | COULD | Download singolo o ZIP di tutti i documenti del soggetto |

### 2.5 Classificazione tipi documento

Sulla base del contenuto osservato nell'archivio NAS:

| Codice | Etichetta | Descrizione |
|--------|-----------|-------------|
| `INGIUNZIONE` | Ingiunzione di pagamento | Atti formali di ingiunzione |
| `NOTIFICA` | Relata di notifica | Relazione di avvenuta notifica |
| `ESTRATTO_DEBITO` | Estratto di debito | Estratto posizione debitoria |
| `PRATICA_INTERNA` | Pratica interna | Documentazione interna (PE, protocolli) |
| `VISURA` | Visura catastale | PDF visure AdE/SISTER |
| `CORRISPONDENZA` | Corrispondenza | Lettere, comunicazioni varie |
| `CONTRATTO` | Contratto/Convenzione | Atti contrattuali |
| `ALTRO` | Altro | Non classificato o inclassificabile |

La classificazione avviene tramite:
1. **Pattern matching automatico** sul nome del file (es. `INGIUNZIONE-*`, `RELATA*`, `Estratto*`)
2. **Revisione manuale** da parte dell'operatore nella scheda soggetto

### 2.6 Import da NAS

| Requisito | Priorità | Descrizione |
|-----------|----------|-------------|
| RF-IMP-01 | MUST | Connessione al NAS via SMB/SSH per lettura struttura cartelle |
| RF-IMP-02 | MUST | Parsing nome cartella per estrarre dati anagrafici |
| RF-IMP-03 | MUST | Import per lettera (A, B, ... Z) o per batch manuale |
| RF-IMP-04 | MUST | Preview risultati prima del commit |
| RF-IMP-05 | MUST | Log dettagliato errori e warning di parsing |
| RF-IMP-06 | MUST | Idempotenza: re-import di una cartella non crea duplicati |
| RF-IMP-07 | SHOULD | Rilevamento automatico tipo soggetto (PF vs PG) dal nome cartella |
| RF-IMP-08 | SHOULD | Catalogazione automatica dei file con classificazione pattern-based |
| RF-IMP-09 | COULD | Import asincrono con progress bar per batch grandi |

#### Algoritmo di parsing nome cartella

```
Persona Fisica:  Cognome_Nome_CODICEFISCALE
                 → CF = 16 char alfanumerici (regex: [A-Z]{6}[0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z])

Persona Giuridica: RagioneSociale_TipoSocietà_PARTITAIVA  (es. 3M_Societa_Agricola_Semplice_01238060956)
                 → P.IVA = 11 cifre al fondo
                 → Tutto il resto = ragione sociale (underscore → spazio)

Fallback:        Non classificato — richiede revisione manuale
```

---

## 3. Modello dati

### 3.1 Tabelle principali

| Tabella | Descrizione |
|---------|-------------|
| `ana_subjects` | Anagrafica soggetti: `id, subject_type, status, source_system, source_external_id, nas_folder_path, nas_folder_letter, imported_at, created_at, updated_at` |
| `ana_persons` | Dati persona fisica: `subject_id, cognome, nome, codice_fiscale, data_nascita, comune_nascita, indirizzo, comune_residenza, cap, email, telefono, note` |
| `ana_person_snapshots` | Storico puntuale dei dati persona: `id, subject_id, source_system, source_ref, cognome, nome, codice_fiscale, data_nascita, comune_nascita, indirizzo, comune_residenza, cap, email, telefono, note, valid_from, collected_at` |
| `ana_companies` | Dati persona giuridica: `subject_id, ragione_sociale, partita_iva, codice_fiscale, forma_giuridica, sede_legale, comune_sede, cap, email_pec, telefono, note` |
| `ana_documents` | Documenti: `id, subject_id, doc_type, filename, nas_path, file_size_bytes, file_modified_at, classification_source, storage_type, local_path, uploaded_at, notes` |
| `ana_import_jobs` | Job di import NAS: `id, letter, status, started_at, completed_at, total_folders, imported_ok, imported_errors, log_json` |
| `ana_audit_log` | Log modifiche anagrafiche: `id, subject_id, action, changed_by, changed_at, diff_json` |

### 3.2 Enumerazioni

```
SubjectType: PERSON | COMPANY | UNKNOWN
SubjectStatus: ACTIVE | INACTIVE | DUPLICATE
DocType: INGIUNZIONE | NOTIFICA | ESTRATTO_DEBITO | PRATICA_INTERNA | VISURA | CORRISPONDENZA | CONTRATTO | ALTRO
ClassificationSource: AUTO | MANUAL
StorageType: NAS_LINK | LOCAL_UPLOAD
ImportJobStatus: PENDING | RUNNING | COMPLETED | FAILED
```

### 3.3 Indici di performance

- `ana_persons(codice_fiscale)` — unique
- `ana_person_snapshots(subject_id, collected_at)`
- `ana_companies(partita_iva)` — unique
- `ana_subjects(nas_folder_letter, nas_folder_path)`
- `ana_documents(subject_id, doc_type)`
- Full-text search su `cognome || ' ' || nome` e `ragione_sociale` (PostgreSQL `tsvector`)

### 3.4 Integrazione piattaforma GAIA

Per essere coerente con l'architettura reale del repository, il modulo richiede anche questi interventi trasversali:

- aggiunta del flag `module_anagrafica` su `application_users`
- aggiornamento della property `enabled_modules`
- bootstrap sezioni in `backend/app/scripts/bootstrap_sections.py`
- integrazione del modulo nelle sidebar e nella home frontend
- aggiornamento dei tipi API frontend relativi a `CurrentUser` e `ApplicationUser`

---

## 4. API Endpoints

Tutti gli endpoint sono esposti sotto il prefisso `/anagrafica`.

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/anagrafica/subjects` | GET | Lista soggetti con filtri, paginazione, full-text search |
| `/anagrafica/subjects` | POST | Crea nuovo soggetto manualmente |
| `/anagrafica/subjects/{id}` | GET | Dettaglio soggetto con documenti, audit log e `person_snapshots` per le persone fisiche |
| `/anagrafica/subjects/{id}` | PUT | Aggiorna dati soggetto |
| `/anagrafica/subjects/{id}` | DELETE | Disattivazione logica (status = inactive) |
| `/anagrafica/subjects/{id}/documents` | GET | Lista documenti del soggetto |
| `/anagrafica/subjects/{id}/documents` | POST | Upload nuovo documento locale |
| `/anagrafica/documents/{id}` | PATCH | Aggiorna classificazione documento (tipo, note) |
| `/anagrafica/documents/{id}` | DELETE | Rimuove documento dall'archivio GAIA (non dal NAS) |
| `/anagrafica/import/preview` | POST | Anteprima import lettera NAS (senza commit) |
| `/anagrafica/import/run` | POST | Avvia import lettera NAS con commit |
| `/anagrafica/import/jobs` | GET | Lista job di import con stato e log |
| `/anagrafica/import/jobs/{id}` | GET | Dettaglio job: log errori, statistiche |
| `/anagrafica/stats` | GET | Statistiche: totali per tipo, per lettera, documenti non classificati |
| `/anagrafica/export` | GET | Export CSV/XLSX con filtri |
| `/anagrafica/search` | GET | Full-text search unificata su tutti i campi chiave |

Tutti gli endpoint devono riutilizzare auth e controllo accessi condivisi del backend esistente. Oltre al controllo di modulo, le sezioni UI/API devono poter essere ricondotte a section key dedicate, coerenti con il bootstrap sezioni GAIA.

---

## 5. Architettura tecnica

### 5.1 Stack tecnologico

| Componente | Tecnologia |
|------------|------------|
| API modulo | FastAPI router `/anagrafica` — aggiunto al backend esistente |
| Frontend | Next.js — nuova sezione `/anagrafica` nel frontend esistente |
| Connessione NAS | Preferenza al riuso della configurazione NAS già esistente nel backend (`paramiko`/SSH). SMB opzionale solo se introdotto senza duplicare configurazione e credenziali |
| Parsing CF | `python-codicefiscale` o regex custom |
| Full-text search | PostgreSQL `tsvector` + `tsquery` |
| Export | `openpyxl` per XLSX, `csv` stdlib per CSV |
| Database | PostgreSQL — nuove tabelle migrate con Alembic |
| File storage | Volume Docker locale per upload nuovi documenti |

### 5.2 Struttura cartelle

```
backend/app/modules/anagrafica/
  models.py          # SQLAlchemy models
  schemas.py         # Pydantic schemas
  router.py or routes.py   # Entry surface coerente con il pattern scelto nel repo
  services.py        # Eventuale surface di compatibilità / export servizi
  repositories.py    # Accesso dati
  services/
    import_service.py    # Logica import NAS: connessione, parsing, commit
    parser_service.py    # Parsing nome cartella → dati anagrafici
    classify_service.py  # Classificazione automatica documenti
    export_service.py    # CSV/XLSX export

frontend/src/app/anagrafica/
  page.tsx                    # Dashboard / lista soggetti
  new/page.tsx                # Form creazione manuale
  [id]/page.tsx               # Scheda soggetto con documenti
  [id]/edit/page.tsx          # Modifica anagrafica
  import/page.tsx             # Wizard import NAS
  import/[jobId]/page.tsx     # Dettaglio job import
  search/page.tsx             # Ricerca avanzata

domain-docs/anagrafica/docs/
  PRD_anagrafica.md
  PROMPT_CODEX_anagrafica.md
```

Note architetturali operative:

- il router di modulo va incluso in `backend/app/api/router.py`
- i modelli del nuovo modulo vanno registrati nel bootstrap metadata usato da Alembic/ORM (`backend/app/db/base.py`)
- se servono wrapper legacy, devono essere secondari rispetto al namespace canonico `backend/app/modules/anagrafica/`

---

## 6. Pagine frontend

| Route | Contenuto |
|-------|-----------|
| `/anagrafica` | Dashboard: totali soggetti, documenti non classificati, ultimi importati, link rapidi |
| `/anagrafica?search=...` | Lista soggetti con ricerca, filtri tipo/status/lettera, ordinamento, paginazione |
| `/anagrafica/new` | Form creazione manuale: tab Persona Fisica / Persona Giuridica |
| `/anagrafica/[id]` | Scheda soggetto: dati anagrafici, lista documenti con tipo/preview/link NAS, audit log e storico snapshot persona |
| `/anagrafica/[id]/edit` | Modifica dati anagrafici |
| `/anagrafica/import` | Wizard import NAS: selezione lettera → preview → conferma → esecuzione |
| `/anagrafica/import/[jobId]` | Log dettagliato job: errori, soggetti importati, documenti catalogati |

---

## 7. Flusso import NAS — Dettaglio

```
1. Operatore seleziona lettera (es. "O") nel wizard frontend
2. Backend si connette al NAS via SMB/SSH
3. Lista le sottocartelle di ARCHIVIO/O/
4. Per ogni cartella:
   a. Esegue parser_service.parse_folder_name(folder_name)
   b. Determina SubjectType (PERSON / COMPANY / UNKNOWN)
   c. Estrae campi disponibili (CF, P.IVA, nome, cognome, ragione sociale)
   d. Lista i file presenti nella cartella (e sottocartelle)
   e. Per ogni file: classify_service.classify(filename) → DocType
5. Restituisce preview JSON con risultati attesi, errori, warning
6. Operatore conferma → commit:
   a. Crea/aggiorna record in ana_subjects
   b. Crea record in ana_persons o ana_companies
   c. Crea record in ana_documents (StorageType=NAS_LINK, nas_path=percorso SMB)
   d. Registra ImportJob completato con log
```

---

## 8. Classificazione automatica documenti — Pattern

```python
PATTERNS = {
    "INGIUNZIONE":      [r"(?i)ingiunzione", r"(?i)^ing_", r"(?i)_Ing_"],
    "NOTIFICA":         [r"(?i)relata", r"(?i)notifica"],
    "ESTRATTO_DEBITO":  [r"(?i)estratto.?debito", r"(?i)estrattoDebito"],
    "PRATICA_INTERNA":  [r"(?i)^PE_", r"(?i)prot"],
    "VISURA":           [r"(?i)visura"],
    "CORRISPONDENZA":   [r"(?i)lettera", r"(?i)comunicaz"],
    "CONTRATTO":        [r"(?i)contratto", r"(?i)convenzione"],
}
# Fallback: ALTRO
```

---

## 9. Integrazione con altri moduli GAIA

| Modulo | Integrazione |
|--------|-------------|
| GAIA Catasto | Collegamento `ana_subjects.id` ↔ `catasto_visure_requests` tramite codice fiscale/P.IVA — ricerca incrociata nella scheda soggetto |
| GAIA Accessi | Correlazione opzionale `ana_subjects.codice_fiscale` ↔ utente NAS per audit accessi |
| GAIA Inventario | Nessuna integrazione diretta nel MVP |
| GAIA Rete | Nessuna integrazione diretta nel MVP |

Infrastruttura piattaforma:

- `application_users`: nuovo flag `module_anagrafica`
- bootstrap sezioni: nuove key `anagrafica.*`
- frontend globale: aggiunta voce modulo in home, platform sidebar e module sidebar
- tipi API condivisi: aggiornamento DTO utente correnti

---

## 10. Non obiettivi MVP

- OCR automatico del contenuto testuale dei PDF
- Firma digitale o validazione firma nei documenti
- Workflow approvazione pratiche
- Notifiche email automatiche per scadenze
- Portale self-service per soggetti esterni
- Scrittura / modifica di file sul NAS
- Sincronizzazione automatica continua con il NAS (l'import è on-demand)
- Deduplicazione automatica soggetti senza supervisione operatore

Restano consentiti:

- scrittura nel database condiviso GAIA
- upload di documenti nello storage locale GAIA, se previsto dal caso d'uso

---

## 11. Priorità di sviluppo

1. Modello dati e migration Alembic
2. Parser nome cartella NAS + classificazione documenti
3. Connettore NAS con preferenza di riuso della configurazione SSH già presente; SMB solo se necessario e ben integrato
4. API import: preview e commit
5. API CRUD soggetti + documenti
6. Frontend: lista soggetti e ricerca
7. Frontend: scheda soggetto con documenti
8. Frontend: wizard import NAS
9. Integrazione piattaforma GAIA: flag modulo, sezioni, sidebar, DTO utente
10. Frontend: dashboard con statistiche
11. Full-text search PostgreSQL
12. Export CSV/XLSX
13. Integrazione lettura correlazione GAIA Catasto
