# PROMPT_DEVOPS.md

# Prompt Codex — DevOps e Deployment NAS Access Audit

> Regola piattaforma
> Docker, Compose e deployment devono trattare GAIA come monolite modulare con servizi tecnici separati solo quando necessario: `backend`, `frontend`, `postgres`, `nginx`, `scanner`, `catasto-worker`.

Configura l'infrastruttura DevOps del progetto **NAS Access Audit Platform**.

## Obiettivo
Preparare un setup completo per sviluppo e deployment tramite Docker Compose, con:
- backend FastAPI
- frontend Next.js
- PostgreSQL
- Nginx reverse proxy

Il setup deve essere chiaro, riproducibile e pronto per ambiente interno o VPS privata.

---

## Componenti da includere
- backend
- frontend
- postgres
- nginx

Opzionale ma consigliato:
- pgadmin solo profilo dev opzionale
- script bootstrap database
- healthchecks

---

## Requisiti principali

### 1. Dockerfile backend
Crea un Dockerfile backend che:
- usi Python 3.11 slim
- installi dipendenze in modo pulito
- copi codice applicativo
- esponga porta backend
- avvii FastAPI con comando chiaro
- supporti env variables

### 2. Dockerfile frontend
Crea un Dockerfile frontend che:
- gestisca build Next.js
- separi build e runtime se utile
- esponga porta frontend
- usi env per API base URL

### 3. Docker Compose
Crea un `docker-compose.yml` con:
- service backend
- service frontend
- service postgres
- service nginx

Richieste:
- volumi persistenti per postgres
- network condivisa
- dipendenze tra servizi
- restart policy
- env_file dove opportuno
- healthcheck

### 4. Nginx reverse proxy
Configura Nginx per:
- servire il frontend
- proxy verso backend API su path dedicato, ad esempio `/api/`
- gestire header corretti
- supportare upload/download file export
- timeout ragionevoli

### 5. Environment variables
Crea:
- `.env.example`
- `.env.backend.example`
- `.env.frontend.example`

Variabili attese almeno:
- POSTGRES_DB
- POSTGRES_USER
- POSTGRES_PASSWORD
- DATABASE_URL
- JWT_SECRET_KEY
- JWT_EXPIRE_MINUTES
- NAS_HOST
- NAS_PORT
- NAS_USERNAME
- NAS_PASSWORD
- NAS_PRIVATE_KEY_PATH
- API_BASE_URL
- NEXT_PUBLIC_API_BASE_URL

### 6. Alembic / DB bootstrap
Prevedi flusso di avvio corretto:
- postgres parte
- backend attende disponibilità DB
- migrazioni eseguibili in modo semplice
- documenta comando migrazione

### 7. Healthcheck
Implementa healthcheck per:
- postgres
- backend
- frontend
- nginx se possibile

### 8. Volumi e persistenza
Assicurati di configurare:
- volume persistente postgres
- eventuali volumi per log o file temporanei solo se necessari

### 9. Sicurezza minima
- nessun segreto hardcoded
- `.env.example` senza credenziali reali
- commenti chiari per deployment dietro VPN o LAN interna
- porte esposte solo se necessario

---

## File richiesti

Crea almeno:

- docker-compose.yml
- docker-compose.override.yml opzionale per dev
- backend/Dockerfile
- frontend/Dockerfile
- nginx/nginx.conf
- .env.example
- scripts/wait-for-db.sh opzionale
- README_DEPLOYMENT.md

---

## Requisiti del README_DEPLOYMENT.md

Il file deve spiegare:
- prerequisiti
- struttura servizi
- come copiare i file env
- come avviare in locale
- come buildare
- come eseguire le migrazioni
- come creare eventualmente un admin iniziale
- come accedere all'app
- come leggere i log
- come fermare i container
- come aggiornare i servizi

Includi anche sezione:
- note di produzione
- deployment consigliato dietro VPN o rete interna
- backup volume postgres

---

## Requisiti di qualità
- file chiari
- commenti essenziali
- nomi servizi leggibili
- setup coerente con un ambiente interno amministrativo
- niente dipendenze superflue

---

## Requisiti opzionali ma utili
Se possibile aggiungi:
- profilo compose per sviluppo
- comando Makefile con:
  - up
  - down
  - logs
  - migrate
  - rebuild
- esempio backup DB
- esempio restore DB

---

## Output atteso
Restituisci:
- tutti i file DevOps necessari
- Dockerfile completi
- docker-compose completo
- config Nginx
- file env example
- README_DEPLOYMENT.md
- eventuale Makefile
