# IMPLEMENTATION_PLAN.md

# NAS Access Audit Platform
## Piano di implementazione

> Regola repository
> Backend unico, moduli logici separati. Nuove implementazioni backend vanno in `backend/app/modules/<modulo>/`.

## 1. Obiettivo del progetto

Realizzare una piattaforma web interna per il Consorzio di Bonifica dell'Oristanese che consenta di:

- acquisire dal NAS Synology utenti, gruppi, cartelle condivise e ACL
- calcolare i permessi effettivi di ogni utente sulle cartelle
- visualizzare lo stato degli accessi in modo chiaro
- consentire ai capi servizio di validare i criteri di assegnazione
- produrre report esportabili per audit e bonifica

Il progetto, nella fase iniziale, deve essere esclusivamente di:
- audit
- visualizzazione
- validazione
- reporting

Non deve modificare automaticamente i permessi sul NAS nella prima release.

---

## 2. Obiettivi funzionali MVP

### 2.1 Funzioni incluse
- autenticazione applicativa
- sincronizzazione dati dal NAS via SSH
- acquisizione utenti
- acquisizione gruppi
- acquisizione appartenenze utenti-gruppi
- acquisizione elenco shared folder
- acquisizione ACL delle cartelle condivise
- salvataggio snapshot dei dati
- calcolo permessi effettivi per utente/cartella
- dashboard consultazione
- filtri per utente, gruppo, cartella, settore
- area revisione per capi servizio
- export CSV/XLSX

### 2.2 Funzioni escluse dal MVP
- modifica automatica permessi NAS
- provisioning utenti
- integrazione Active Directory / LDAP
- SSO enterprise
- gestione sottocartelle profonde con navigazione avanzata
- sincronizzazione continua real-time

---

## 3. Architettura tecnica

### Backend
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Paramiko per SSH
- Pydantic v2
- JWT auth

### Frontend
- Next.js
- React
- TailwindCSS
- TanStack Table
- fetch/axios per API client

### DevOps
- Docker
- Docker Compose
- Nginx reverse proxy
- file `.env`
- ambienti separati per sviluppo e produzione

---

## 4. Moduli applicativi

### 4.1 Modulo autenticazione
Gestisce:
- login
- JWT access token
- ruoli applicativi

Ruoli previsti:
- admin
- reviewer
- viewer

### 4.2 Modulo NAS connector
Gestisce:
- connessione SSH al NAS
- esecuzione comandi
- parsing output

### 4.3 Modulo sincronizzazione
Gestisce:
- acquisizione dati dal NAS
- creazione snapshot
- salvataggio dati raw e normalizzati

### 4.4 Modulo permission engine
Gestisce:
- combinazione permessi utente e gruppo
- precedenza deny/allow
- calcolo read/write effettivi
- generazione motivazione del permesso

### 4.5 Modulo review workflow
Gestisce:
- assegnazione ambito settore
- revisione da parte del capo servizio
- decisioni: conferma/revoca/richiesta modifica
- note

### 4.6 Modulo reporting
Gestisce:
- export CSV
- export XLSX
- report per settore
- report per utente
- report per cartella

---

## 5. Modello operativo

### Fase 1 — acquisizione tecnica
L'app esegue il fetch dal NAS e fotografa lo stato attuale.

### Fase 2 — normalizzazione
I dati grezzi vengono convertiti in un modello coerente:
- utenti
- gruppi
- share
- ACL
- permessi effettivi

### Fase 3 — consultazione
Gli amministratori consultano:
- chi accede a cosa
- tramite quale gruppo
- con quale livello

### Fase 4 — validazione
Ogni capo servizio verifica gli accessi del proprio ambito.

### Fase 5 — reporting finale
Viene prodotto un report che evidenzia:
- accessi corretti
- accessi da rimuovere
- anomalie
- richieste di riallineamento

---

## 6. Milestone di implementazione

### Milestone 1 — bootstrap backend
Output attesi:
- struttura FastAPI
- connessione DB
- modelli base
- migration iniziale
- autenticazione JWT

### Milestone 2 — NAS sync
Output attesi:
- servizio SSH funzionante
- recupero utenti
- recupero gruppi
- recupero shared folders
- recupero ACL
- persistenza snapshot

### Milestone 3 — permission engine
Output attesi:
- regole di calcolo permessi effettivi
- popolamento tabella effective_permissions
- endpoint consultazione

### Milestone 4 — frontend dashboard
Output attesi:
- login
- dashboard overview
- vista utenti
- vista cartelle
- filtri
- paginazione

### Milestone 5 — review workflow
Output attesi:
- vista reviewer
- registrazione decisioni
- note
- filtri per settore

### Milestone 6 — export e hardening
Output attesi:
- export CSV/XLSX
- docker compose completo
- reverse proxy
- documentazione deployment

---

## 7. Ordine di sviluppo raccomandato

1. bootstrap repository
2. backend base
3. schema DB e migrazioni
4. auth e RBAC
5. servizio SSH NAS
6. sincronizzazione e snapshot
7. permission engine
8. API pubbliche
9. frontend login e dashboard
10. frontend viste utenti/cartelle
11. frontend review
12. export
13. Docker e Nginx
14. test e rifinitura

---

## 8. Convenzioni di sviluppo

### Backend
- codice modulare
- tipizzazione completa
- validazione con Pydantic
- separazione netta tra:
  - routers
  - services
  - repositories
  - models
  - schemas
- nessuna logica business nei router
- error handling centralizzato
- logging strutturato

### Frontend
- componenti riutilizzabili
- separazione tra:
  - pages/app routes
  - components
  - services/api
  - hooks
  - types
- evitare logica dispersa
- tabella centralizzata con filtri e paginazione

### DevOps
- immagini Docker chiare e minimali
- hardening DNS Docker host per build deterministici dei container
- rimozione del workaround Compose `build.network: host` dal servizio `frontend` dopo stabilizzazione DNS del daemon

---

## 9. Evoluzione pianificata — GAIA CED

E' pianificata un'evoluzione di piattaforma per convergere `GAIA NAS Control` e
`GAIA Rete` in un unico entrypoint frontend `GAIA CED`.

Principi guida:

- prima convergenza UI/navigation
- backend invariati nella prima fase
- permessi esistenti `module_accessi` e `module_rete` mantenuti
- eventuale `module_ced` rinviato a fase successiva

Documentazione operativa di riferimento:

- `domain-docs/ced/docs/PRD.md`
- `domain-docs/ced/docs/IMPLEMENTATION_PLAN.md`
- `domain-docs/ced/docs/CODEX_PROMPT.md`
- `domain-docs/ced/docs/PROGRESS.md`
- variabili in `.env`
- nessun segreto hardcoded
- healthcheck dei servizi
- volumi persistenti per PostgreSQL

---

## 9. Regole di business per il permission engine

- i permessi possono derivare da:
  - assegnazione diretta all'utente
  - assegnazione al gruppo
- un utente può appartenere a più gruppi
- deny ha precedenza su allow
- write implica read
- il sistema deve produrre sempre una spiegazione della sorgente:
  - direct:user
  - group:nome_gruppo
  - denied_by:...
  - combined:...

Se l'ACL Synology non è pienamente omogenea, il sistema deve comunque salvare:
- dato raw
- dato normalizzato
- eventuali warning di parsing

---

## 10. Sicurezza

- accesso solo autenticato
- JWT con expiry configurabile
- password hashate
- ruoli applicativi obbligatori
- log di:
  - login
  - sync
  - export
  - review
- accesso consigliato solo da rete interna o VPN

---

## 11. Criteri di accettazione MVP

Il MVP si considera completato quando:

1. un admin può autenticarsi
2. il sistema può sincronizzare dati dal NAS
3. il sistema salva utenti, gruppi, share e ACL
4. il sistema calcola permessi effettivi
5. la UI mostra per ogni utente le cartelle accessibili
6. la UI mostra per ogni cartella gli utenti che accedono
7. un reviewer può registrare una decisione
8. l'app può esportare un report CSV/XLSX
9. tutto è avviabile via Docker Compose

---

## 12. Rischi tecnici

- ACL Synology complesse o non uniformi
- differenze tra `getfacl` e `synoacltool`
- presenza di configurazioni storiche incoerenti
- path cartelle non standard
- gruppi legacy con naming poco leggibile

Mitigazioni:
- salvare output raw dei comandi
- introdurre warning di parsing
- validare progressivamente con dati reali
- partire dalle shared folders di primo livello

---

## 13. Output finali attesi

- repository backend
- repository frontend oppure monorepo
- docker-compose completo
- documentazione `.env.example`
- guida deployment
- guida operativa per audit accessi
- export report per capi servizio

---

## 14. Indicazioni per Codex

Codex deve:
- implementare il progetto per milestone
- mantenere coerenza tra backend e frontend
- evitare feature non richieste
- privilegiare codice chiaro e manutenibile
- documentare i punti critici
- lasciare TODO espliciti dove la logica dipende dall'ambiente Synology reale
