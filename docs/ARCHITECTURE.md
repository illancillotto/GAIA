# Architettura

## 1. Panoramica

L'architettura adotta una separazione netta tra frontend, backend API, database relazionale e reverse proxy. Il design e pensato per un contesto enterprise interno con esposizione controllata su rete privata o VPN.

## 2. Componenti

### 2.1 Frontend

- Next.js App Router
- interfaccia operator-friendly
- consumo API backend tramite URL configurabile

### 2.2 Backend

- FastAPI come layer API
- moduli predisposti per auth, sync NAS, review, reporting
- SQLAlchemy per accesso dati
- Alembic per versionamento schema

### 2.3 Database

- PostgreSQL come persistenza principale
- volumi dedicati per durabilita dei dati

### 2.4 Reverse Proxy

- Nginx come punto di ingresso
- instradamento `/api/` verso backend
- traffico web verso frontend

## 3. Moduli Backend Predisposti

- `app/api`: router e endpoint
- `app/core`: config, logging, database
- `app/models`: modelli ORM
- `app/schemas`: DTO e payload API
- `app/services`: logica applicativa
- `app/repositories`: accesso ai dati
- `app/jobs`: processi asincroni e sync schedulati

## 4. Flusso Principale

1. il frontend richiama Nginx
2. Nginx instrada il traffico UI al frontend e le API al backend
3. il backend usa PostgreSQL per snapshot, review e metadati NAS
4. il backend puo interrogare il NAS via SSH per costruire payload di sync persistenti
5. i job backend possono riusare la live sync con retry controllato e target scriptabile
6. ogni sync puo essere tracciata in audit trail persistente con esito, tentativi e snapshot associato

## 5. Decisioni Architetturali Iniziali

- bootstrap leggero per ridurre boilerplate non necessario
- documentazione in `docs/` come fonte primaria
- composizione container-first per facilitare ambienti coerenti
- health endpoint dedicato per monitoraggio base

## 6. Evoluzioni Previste

- autenticazione JWT e RBAC
- permission engine con snapshot versionati
- export strutturati
- osservabilita applicativa e metriche
- scheduling e retry della live sync via SSH
