# ARCHITECTURE.md

# CBO NAS Access Audit
## Architettura del sistema

## 1. Scopo

La piattaforma **CBO NAS Access Audit** è una web application interna progettata per:

- acquisire dal NAS Synology utenti, gruppi, cartelle condivise e ACL
- calcolare i permessi effettivi per utente e cartella
- consentire consultazione e revisione degli accessi
- supportare i capi servizio nella validazione
- produrre report per audit e bonifica

Il sistema, nel MVP, è **read-only rispetto al NAS**:
- legge
- analizza
- normalizza
- mostra
- esporta

Non modifica automaticamente i permessi del NAS.

---

## 2. Architettura logica

Il sistema è composto da 4 macro-componenti:

### 2.1 Frontend
Interfaccia web per:
- login
- consultazione dashboard
- navigazione utenti/cartelle
- revisione accessi
- export report

Tecnologie:
- Next.js
- React
- TailwindCSS
- TanStack Table

Path repository:
- `frontend/`

---

### 2.2 Backend API
Espone API REST per:
- autenticazione
- sincronizzazione NAS
- consultazione entità
- calcolo e lettura permessi effettivi
- gestione review
- export

Tecnologie:
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- Paramiko

---

### 2.3 Database
Persistenza di:
- utenti applicativi
- utenti NAS
- gruppi NAS
- shared folder
- ACL raw
- permessi normalizzati
- permessi effettivi
- review
- snapshot

Tecnologia:
- PostgreSQL

---

### 2.4 NAS Connector
Modulo backend dedicato alla connessione SSH verso il NAS Synology.

Responsabilità:
- esecuzione comandi
- recupero dati raw
- gestione timeout/errori
- parsing output

Canali previsti:
- SSH
- comandi di sistema Synology/Linux

---

## 3. Architettura fisica

## 3.1 Servizi containerizzati

L’applicazione gira tramite Docker Compose con questi servizi:

- `frontend`
- `backend`
- `postgres`
- `nginx`
- `catasto-worker`

---

## 3.2 Ruolo dei servizi

### frontend
Serve la web app e consuma le API del backend.

### backend
Espone API, esegue sync, calcola permessi, genera export.

### postgres
Salva i dati persistenti della piattaforma.

### nginx
Fa da reverse proxy:
- instrada traffico frontend
- proxy API backend
- gestisce headers e timeouts

---

## 4. Flusso dati principale

## 4.1 Sync NAS

1. l’admin avvia una sincronizzazione
2. il backend crea uno snapshot
3. il NAS connector si collega via SSH
4. esegue comandi per utenti, gruppi, membership, shared folders, ACL
5. salva il dato raw
6. normalizza il dato
7. calcola i permessi effettivi
8. chiude lo snapshot

---

## 4.2 Consultazione

1. l’utente applicativo effettua login
2. il frontend richiama le API
3. il backend legge dal database
4. la UI mostra dati filtrabili e paginati

---

## 4.3 Review

1. il reviewer consulta i permessi del proprio ambito
2. seleziona utente/cartella
3. inserisce decisione e nota
4. il backend salva la review
5. il sistema mantiene lo storico decisionale

---

## 4.4 Export

1. l’utente applicativo seleziona filtri
2. il frontend richiama endpoint export
3. il backend genera CSV/XLSX
4. il file viene scaricato

---

## 5. Modello di dominio

## 5.1 Entità applicative

### ApplicationUser
Utenti che accedono alla piattaforma.

Ruoli:
- admin
- reviewer
- viewer

---

## 5.2 Entità NAS

### NasUser
Utente presente sul NAS.

### NasGroup
Gruppo presente sul NAS.

### NasUserGroup
Relazione utente-gruppo.

### Share
Cartella condivisa del NAS.

---

## 5.3 Entità di audit

### Snapshot
Fotografia di una sincronizzazione.

### RawAclEntry
Contiene il testo raw delle ACL recuperate dal NAS.

### PermissionEntry
Permesso normalizzato derivato dal parsing ACL.

### EffectivePermission
Permesso finale calcolato per utente-cartella.

### Review
Decisione di validazione registrata da un reviewer/admin.

---

## 6. Regole di business

## 6.1 Origine dei permessi
I permessi possono derivare da:
- assegnazione diretta all’utente
- assegnazione ai gruppi di appartenenza

---

## 6.2 Priorità
Ordine logico di priorità:
1. deny
2. allow diretto utente
3. allow da gruppo

---

## 6.3 Regole di semplificazione MVP
Per il MVP:
- `write` implica `read`
- il sistema deve produrre una `source_summary`
- il sistema deve salvare `details_json` per debugging
- se l’ACL non è perfettamente interpretabile, salvare warning ma non interrompere tutta la sync

---

## 7. Sicurezza applicativa

## 7.1 Access control
L’accesso alla piattaforma è consentito solo ad utenti autenticati.

Ruoli:
- **admin**: pieno accesso
- **reviewer**: consultazione + review
- **viewer**: sola consultazione

---

## 7.2 Autenticazione
Metodo:
- login con username/email e password
- JWT access token

---

## 7.3 Sicurezza operativa
Linee guida:
- accesso consigliato solo da LAN o VPN
- nessun segreto nel codice
- password hashate
- env separati
- logging delle operazioni critiche

---

## 8. Logging e osservabilità

Eventi da loggare:
- login riusciti/falliti
- avvio sync
- esito sync
- parsing warning
- export
- review create/aggiornate
- errori SSH
- errori applicativi

---

## 9. Scelte architetturali principali

## 9.1 Monorepo
Scelta:
- backend e frontend nello stesso repository

Motivazioni:
- maggiore coerenza
- documentazione unica
- docker compose centrale
- avvio più semplice del MVP

---

## 9.2 Snapshot-based audit
Scelta:
- lavorare su snapshot e non su sola lettura volatile

Motivazioni:
- confrontabilità nel tempo
- reporting storico
- revisione riferita a una fotografia precisa

---

## 9.3 Read-only NAS nel MVP
Scelta:
- nessuna modifica automatica dei permessi

Motivazioni:
- ridurre rischio operativo
- evitare danni su ambiente legacy
- favorire prima la comprensione e la validazione

---

## 10. Limiti del MVP

- non gestisce provisioning utenti
- non modifica ACL sul NAS
- non integra Active Directory
- non garantisce pieno supporto a tutte le casistiche ACL complesse Synology senza adattamento sul campo
- non include workflow approvativo enterprise avanzato

---

## 11. Evoluzioni future

Possibili estensioni:
- proposta automatica di bonifica accessi
- applicazione controllata delle modifiche
- integrazione LDAP/AD
- audit automatici schedulati
- notifiche anomalie
- diff tra snapshot
- dashboard compliance per settore

---

## 12. Diagramma testuale ad alto livello

    ```text
    [ Browser Utente ]
            |
            v
    [ Frontend Next.js ]
            |
            v
    [ Nginx Reverse Proxy ]
            |
            +-----------------------> [ Backend FastAPI ] -----------------------> [ PostgreSQL ]
                                            |
                                            |
                                            v
                                    [ NAS Connector via SSH ]
                                            |
                                            v
                                    [ Synology NAS ]

13. Repository structure
    GAIA/
    ├── README.md
    ├── docker-compose.yml
    ├── docker-compose.override.yml
    ├── modules/
    │   ├── accessi/
    │   │   ├── backend/
    │   │   ├── frontend/
    │   │   └── docs/
    │   ├── network/
    │   └── inventory/
    ├── nginx/
    ├── scripts/
    └── .github/
