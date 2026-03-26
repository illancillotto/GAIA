# NAS Access Audit Platform (NAAP)

> Nota repository
> Questo documento descrive il dominio Accessi. Nel repository attuale il backend e condiviso tra moduli ed e organizzato come monolite modulare.

## 1. Overview

### 1.1 Obiettivo
Realizzare una web application interna per il Consorzio di Bonifica dell'Oristanese che consenta:

- Audit completo degli accessi al NAS Synology
- Visualizzazione dei permessi effettivi per utente
- Validazione degli accessi da parte dei capi servizio
- Produzione di report e piano di bonifica

---

### 1.2 Contesto

Attualmente il sistema NAS presenta:

- Permessi assegnati tramite gruppi
- Ereditarietà non tracciata
- Mancanza di visibilità sugli accessi reali
- Assenza di strumenti di audit

Questo comporta:

- Rischio accessi non autorizzati
- Difficoltà di governance
- Impossibilità di validazione organizzativa

---

## 2. Goals

### 2.1 Obiettivi principali

- Centralizzare la visibilità degli accessi
- Determinare i permessi effettivi per ogni utente
- Coinvolgere i capi servizio nella validazione
- Generare report strutturati per bonifica

---

### 2.2 Non Obiettivi (MVP)

- Modifica automatica dei permessi NAS
- Integrazione con Active Directory (fase futura)
- Gestione provisioning utenti

---

## 3. Architettura

### 3.1 Stack Tecnologico

**Backend**
- FastAPI
- SQLAlchemy / SQLModel
- Paramiko (SSH)
- PostgreSQL

**Frontend**
- Next.js
- TailwindCSS
- TanStack Table

**Infrastructure**
- Docker / Docker Compose
- Nginx (reverse proxy)

---

### 3.2 Componenti

- Backend API (FastAPI)
- Frontend Dashboard (Next.js)
- Database (PostgreSQL)
- NAS Connector (SSH)

---

## 4. Funzionalità MVP

### 4.1 Sync NAS

- Estrazione utenti
- Estrazione gruppi
- Mapping utenti-gruppi
- Elenco cartelle condivise
- Lettura ACL

---

### 4.2 Vista Utente

- Elenco gruppi
- Cartelle accessibili
- Permessi effettivi (read/write)
- Origine permesso (gruppo / diretto)

---

### 4.3 Vista Cartella

- Elenco utenti con accesso
- Tipo di accesso
- Fonte del permesso

---

### 4.4 Vista Responsabile Settore

- Utenti del proprio settore
- Accessi correnti
- Azioni:
  - Conferma
  - Revoca
  - Note

---

### 4.5 Export

- CSV
- Excel

---

## 5. Modello Dati

### 5.1 Tabelle principali

#### Users
- id
- username
- email

#### Groups
- id
- name

#### UserGroups
- user_id
- group_id

#### Shares
- id
- name
- path
- settore

#### Permissions
- id
- share_id
- subject_type (user/group)
- subject_name
- level

#### EffectivePermissions
- user_id
- share_id
- read (bool)
- write (bool)
- source

#### Reviews
- id
- user_id
- share_id
- reviewer
- decision
- note
- reviewed_at

#### Snapshots
- id
- created_at
- checksum

---

## 6. Regole di Business

- I permessi derivano da:
  - Utente diretto
  - Gruppi
- I permessi di tipo DENY hanno priorità
- WRITE implica READ
- I permessi effettivi sono calcolati a runtime o su snapshot

---

## 7. API Endpoints

### 7.1 Core

- `POST /auth/login`
- `GET /users`
- `GET /groups`
- `GET /shares`
- `GET /permissions`
- `GET /effective-permissions`
- `POST /reviews`
- `POST /sync`

---

## 8. Workflow

### 8.1 Processo operativo

1. Sync dati dal NAS
2. Creazione snapshot
3. Analisi permessi
4. Validazione capi servizio
5. Generazione report
6. Pianificazione bonifica

---

## 9. Sicurezza

- Autenticazione JWT
- RBAC:
  - Admin
  - Reviewer (capo servizio)
  - Viewer
- Audit log operazioni

---

## 10. UI/UX

### 10.1 Dashboard

- Overview sistema
- Numero utenti
- Numero accessi

### 10.2 Tabelle

- Filtri per:
  - Utente
  - Settore
  - Cartella

---

## 11. Deployment

- Docker Compose
- Backend + Frontend + DB
- Accesso via rete interna o VPN

---

## 12. Roadmap

### Fase 1
- Backend base
- Connessione NAS
- DB

### Fase 2
- API complete
- Frontend base

### Fase 3
- Validazione capi servizio

### Fase 4
- Export e report

---

## 13. Estensioni Future

- Integrazione Active Directory
- Automazione modifica permessi
- Alert accessi anomali
- Versioning completo accessi

---

## 14. Naming Progetto

Nome consigliato:

**NAS Access Audit (NAA)**
oppure  
**CBO Access Governance**

---

## 15. Rischi

- Complessità parsing ACL Synology
- Incoerenza dati legacy
- Resistenza organizzativa al cambiamento

---

## 16. Success Metrics

- % utenti con accessi validati
- riduzione accessi non necessari
- tempo medio audit accessi
- numero anomalie rilevate

---
