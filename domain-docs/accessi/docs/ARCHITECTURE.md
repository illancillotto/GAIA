# Architettura

> Nota repository
> Il modulo Accessi vive dentro il backend monolite modulare GAIA. Nuovo codice backend Accessi va nel namespace `app/modules/accessi/`.
> Il path fisico del backend condiviso e `backend/`.

## 1. Panoramica

### Gestione delegata utenti GAIA: CED

Il ruolo applicativo `ced` accede a `/gaia/users` senza richiedere il modulo
`accessi`. Non eredita i privilegi di Admin o Super Admin: gestisce soltanto
account con ruolo `viewer`, `reviewer`, `hr_manager` o `operator`, mai il proprio
account o account CED/amministrativi. Admin e Super Admin possono assegnare CED;
solo Super Admin puo assegnare `super_admin`, anche attraverso un aggiornamento.

CED puo creare/modificare account standard, inviare inviti, cambiare il loro
stato e assegnare i moduli `inventario`, `dotazioni`, `gis`, `catasto`, `utenze`,
`operazioni`, `riordino`, `ruolo`, `presenze` e `organigramma`. L'elenco e esplicito:
moduli futuri restano esclusi. Le abilitazioni gia presenti a NAS (`accessi`) e
Rete (`rete`) devono restare invariate. CED non accede direttamente a NAS o Rete,
anche in presenza di flag residui sul suo account.

Gli override di sezione, le credenziali QGIS Desktop e l'eliminazione definitiva
restano alle policy amministrative esistenti. Il catalogo e i permessi risolti
sono consultabili; l'elenco API utenti resta consultabile, mentre l'interfaccia
CED presenta solo gli account standard. La policy condivisa backend vive in
`app/modules/accessi/user_management_policy.py`; copre create, update, inviti
e PATCH moduli. Le API NAS e Network negano esplicitamente l'accesso a CED.
I permessi di sezione CED usano il livello base viewer, senza ereditare HR/admin.

Il campo persistito `application_users.role` e una stringa: l'introduzione di
CED non richiede una migrazione o la creazione automatica di account.

Il commit CED non introduce il modulo Dotazioni, le sue colonne o le sue
route: la voce nella whitelist descrive la delega quando il modulo e
disponibile. L'integrazione Dotazioni e un ciclo separato, non un prerequisito
per gestire gli altri moduli standard.

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
- documentazione in `domain-docs/accessi/docs/` come fonte primaria
- composizione container-first per facilitare ambienti coerenti
- health endpoint dedicato per monitoraggio base

## Cruscotto operatori e Dotazioni — 2026-10-02

`/gaia/users/operatori-cruscotto` consuma Dotazioni tramite `OperatorAssets`.
La scheda usa solo `detail.operator.gaia_user_id` per le custodie e non
interpreta device di rete assegnati come beni fisicamente in consegna.
Mapping assente ed errori Dotazioni restano locali; dominio e permessi sono
nel modulo canonico. Contratto e verifiche in
`domain-docs/dotazioni/docs/CRUSCOTTO_VALIDATION.md`.

## 6. Evoluzioni Previste

- autenticazione JWT e RBAC
- permission engine con snapshot versionati
- export strutturati
- osservabilita applicativa e metriche
- scheduling e retry della live sync via SSH
