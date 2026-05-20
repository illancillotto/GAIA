# PROMPT_BACKEND.md

# Prompt Codex — Backend NAS Access Audit

> Regola strutturale obbligatoria
> GAIA usa un backend monolite modulare. Nuovo codice backend va scritto in `backend/app/modules/<modulo>/`.
> Non creare backend separati per modulo salvo worker o servizi tecnici dedicati.

Sviluppa il backend di una piattaforma chiamata **NAS Access Audit Platform**.

## Obiettivo
Realizzare un backend production-ready basato su FastAPI che consenta di:
- autenticare utenti applicativi
- connettersi via SSH a un NAS Synology
- acquisire utenti, gruppi, appartenenze, shared folders e ACL
- salvare snapshot in PostgreSQL
- calcolare i permessi effettivi per utente/cartella
- esporre API REST per frontend e export

---

## Stack obbligatorio
- Python 3.11
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Pydantic v2
- Paramiko
- JWT auth
- Docker

---

## Requisiti architetturali
Crea una struttura modulare e pulita.

Struttura consigliata:

app/
  main.py
  core/
    config.py
    security.py
    database.py
    logging.py
    exceptions.py
  models/
  schemas/
  routers/
  services/
  repositories/
  utils/
  jobs/

tests/

alembic/
Dockerfile
requirements.txt
.env.example

---

## Entità da implementare

### ApplicationUser
Utente applicativo che accede alla piattaforma.
Campi minimi:
- id
- username
- email
- password_hash
- role (admin, reviewer, viewer)
- is_active
- created_at
- updated_at

### NasUser
Utente del NAS.
Campi minimi:
- id
- username
- full_name nullable
- email nullable
- source_uid nullable
- is_active
- last_seen_snapshot_id

### NasGroup
Gruppo del NAS.
Campi minimi:
- id
- name
- description nullable
- last_seen_snapshot_id

### NasUserGroup
Tabella many-to-many tra NasUser e NasGroup.

### Share
Cartella condivisa.
Campi minimi:
- id
- name
- path
- sector nullable
- description nullable
- last_seen_snapshot_id

### RawAclEntry
Salva il dato raw letto dal NAS.
Campi minimi:
- id
- snapshot_id
- share_id
- raw_text
- parser_source
- created_at

### PermissionEntry
Permesso normalizzato.
Campi minimi:
- id
- snapshot_id
- share_id
- subject_type (user/group)
- subject_name
- permission_level
- is_deny
- source_system
- raw_reference nullable

### EffectivePermission
Permesso finale per utente/cartella.
Campi minimi:
- id
- snapshot_id
- nas_user_id
- share_id
- can_read
- can_write
- is_denied
- source_summary
- details_json nullable

### Review
Revisione effettuata da un reviewer.
Campi minimi:
- id
- snapshot_id
- nas_user_id
- share_id
- reviewer_user_id
- decision (approved, revoke, modify_request)
- note
- reviewed_at

### Snapshot
Fotografia di sincronizzazione.
Campi minimi:
- id
- started_at
- completed_at
- status
- checksum nullable
- notes nullable

---

## Funzionalità backend richieste

### 1. Auth
Implementa:
- POST /auth/login
- GET /auth/me

Richieste:
- password hashing sicuro
- JWT access token
- dependency per recuperare utente corrente
- dependency per controllo ruoli

### 2. NAS SSH Connector
Implementa un servizio dedicato che si colleghi via SSH a un NAS Synology.

Deve essere configurabile tramite env:
- NAS_HOST
- NAS_PORT
- NAS_USERNAME
- NAS_PASSWORD
- NAS_PRIVATE_KEY_PATH opzionale
- NAS_TIMEOUT

Implementa funzioni:
- run_command(command: str) -> str
- get_users()
- get_groups()
- get_user_groups()
- get_shared_folders()
- get_acl(path)

Comandi suggeriti:
- cat /etc/passwd
- cat /etc/group
- ls -1 /volume1
- getfacl <path>
- synoacltool -get <path>

Il codice deve:
- gestire timeout
- gestire errori SSH
- loggare in modo chiaro
- restituire dati strutturati

### 3. Parsing
Implementa parser robusti per:
- /etc/passwd
- /etc/group
- output ACL

Conserva sia:
- raw data
- normalized data

Se un parser fallisce su una riga:
- non interrompere tutta la sync
- registra warning
- continua

### 4. Snapshot sync
Implementa:
- POST /sync/run
- GET /sync/history
- GET /sync/history/{snapshot_id}

Flusso richiesto:
1. crea snapshot in stato running
2. acquisisce utenti
3. acquisisce gruppi
4. acquisisce membership
5. acquisisce shares
6. acquisisce ACL
7. salva raw ACL
8. normalizza permission entries
9. calcola effective permissions
10. chiude snapshot in stato completed o failed

### 5. Permission engine
Implementa una funzione di calcolo permessi effettivi.

Input:
- utenti NAS
- gruppi NAS
- membership utenti-gruppi
- permission entries
- share

Regole:
- permessi da gruppo sono ereditati
- permessi diretti all'utente hanno priorità informativa
- deny prevale su allow
- write implica read
- genera source_summary leggibile

Output atteso per ogni combinazione utente-share:
- can_read
- can_write
- is_denied
- source_summary
- details_json

### 6. API di consultazione
Implementa endpoint con filtro e paginazione:

- GET /users
- GET /users/{id}
- GET /groups
- GET /shares
- GET /shares/{id}
- GET /permissions
- GET /effective-permissions
- GET /effective-permissions/by-user/{nas_user_id}
- GET /effective-permissions/by-share/{share_id}
- GET /reviews
- POST /reviews
- PUT /reviews/{id}

Filtri minimi:
- username
- group name
- share name
- sector
- snapshot_id
- can_read
- can_write
- decision

### 7. Export
Implementa:
- GET /exports/effective-permissions.csv
- GET /exports/effective-permissions.xlsx

Requisiti:
- supporto filtro per snapshot e settore
- colonne:
  - username
  - groups
  - share
  - sector
  - can_read
  - can_write
  - is_denied
  - source_summary

### 8. Health e meta
Implementa:
- GET /health
- GET /version

---

## Requisiti non funzionali

### Logging
- logging strutturato
- log per auth
- log per sync
- log per export
- log per errori SSH e parsing

### Error handling
- eccezioni HTTP coerenti
- messaggi chiari
- niente stacktrace esposti al client

### Sicurezza
- password hashate
- JWT secret da env
- CORS configurabile
- niente segreti hardcoded

### Performance
- query paginate
- indici DB sulle colonne chiave
- evitare N+1 query
- servizi separati da router

---

## Database e Alembic
- crea modelli completi
- crea migration iniziale
- crea eventuale seed iniziale di un admin di esempio disattivabile
- aggiungi `.env.example`

---

## Testing
Aggiungi test minimi per:
- login
- parsing passwd/group
- permission engine
- endpoint health

---

## Docker
Crea:
- Dockerfile backend
- comando di avvio chiaro
- supporto a variabili env

---

## Qualità del codice
- type hints
- docstring essenziali
- codice leggibile
- TODO espliciti dove i dettagli ACL Synology reali richiedono adattamento

---

## Output atteso
Restituisci:
- codice completo backend
- migration Alembic
- Dockerfile
- `.env.example`
- README backend con istruzioni avvio locale e Docker
