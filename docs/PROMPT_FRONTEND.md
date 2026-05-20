# PROMPT_FRONTEND.md

# Prompt Codex — Frontend NAS Access Audit

> Regola frontend
> Il frontend GAIA resta unico. I moduli applicativi vivono sotto `frontend/src/app/<modulo>/` e devono riflettere i moduli del monolite backend.

Sviluppa il frontend di una piattaforma chiamata **NAS Access Audit Platform**.

## Obiettivo
Realizzare una web app interna per:
- autenticazione utenti applicativi
- consultazione utenti NAS, gruppi, cartelle e permessi effettivi
- navigazione per utente e per cartella
- revisione degli accessi da parte dei capi servizio
- export report

Il frontend deve essere pulito, leggibile, orientato al lavoro d'ufficio e alla revisione amministrativa.

---

## Stack obbligatorio
- Next.js
- React
- TailwindCSS
- TypeScript preferito; se necessario JavaScript ben strutturato
- TanStack Table
- fetch o axios
- gestione auth via JWT

---

## Requisiti architetturali
Crea una struttura ordinata.

Struttura consigliata:

src/
  app/
  components/
  features/
  services/
  hooks/
  lib/
  types/
  utils/

Se usi App Router, organizza bene layout e route.

---

## Requisiti UI/UX

### Stile
- interfaccia professionale
- pulita
- leggibile
- no effetti inutili
- no design “marketing”
- focus su tabelle, filtri, chiarezza

### Layout
Prevedi:
- sidebar
- topbar
- contenuto centrale
- breadcrumb semplice
- badge per ruoli e stati

### Responsive
Deve funzionare bene su desktop.
Mobile non è prioritario, ma non deve rompersi.

---

## Pagine richieste

### 1. Login
Route:
- /login

Funzioni:
- username/email
- password
- submit
- gestione errori
- salvataggio JWT
- redirect a dashboard dopo login

### 2. Dashboard
Route:
- /

Mostra:
- numero utenti NAS
- numero gruppi
- numero shares
- ultimo snapshot
- numero review aperte o presenti
- accessi recenti o attività recenti se disponibili

### 3. Vista utenti
Route:
- /users

Funzioni:
- tabella utenti NAS
- ricerca per username
- filtro per gruppo
- filtro per settore se disponibile
- click su utente per dettaglio

### 4. Dettaglio utente
Route:
- /users/[id]

Mostra:
- dati utente
- gruppi di appartenenza
- cartelle accessibili
- permessi effettivi
- origine del permesso
- eventuale stato review

### 5. Vista cartelle
Route:
- /shares

Funzioni:
- tabella shares
- ricerca per nome cartella
- filtro settore
- click per dettaglio

### 6. Dettaglio cartella
Route:
- /shares/[id]

Mostra:
- nome cartella
- path
- settore
- utenti che vi accedono
- livello accesso
- source summary
- filtri per read/write/denied

### 7. Vista permessi effettivi
Route:
- /effective-permissions

Funzioni:
- tabella generale
- filtri:
  - utente
  - cartella
  - settore
  - read
  - write
  - denied
  - snapshot

### 8. Review area
Route:
- /reviews

Destinata ai reviewer e admin.

Funzioni:
- vedere record review esistenti
- filtrare per settore, utente, cartella, decisione
- creare review
- modificare review
- form con:
  - decision
  - note

### 9. Sync history
Route:
- /sync

Mostra:
- storico snapshot
- stato
- data inizio/fine
- dettaglio snapshot

### 10. Export area
Route:
- /exports

Mostra:
- pulsanti export CSV e XLSX
- filtri esportazione per snapshot e settore

---

## Componenti richiesti

### Layout components
- AppShell
- Sidebar
- Topbar
- PageHeader
- StatCard

### Data components
- DataTable
- FilterBar
- SearchInput
- Badge
- EmptyState
- LoadingState
- ErrorState
- PaginationControls

### Domain components
- UserInfoCard
- GroupListCard
- ShareInfoCard
- EffectivePermissionTable
- ReviewForm
- SnapshotHistoryTable
- ExportPanel

---

## Gestione auth
Implementa:
- salvataggio token
- protezione route private
- redirect a login se token assente o invalido
- fetch `/auth/me` per recupero utente corrente
- visualizzazione ruolo corrente

---

## API integration
Prevedi un layer dedicato per le API.

Endpoints da integrare:
- POST /auth/login
- GET /auth/me
- GET /users
- GET /users/{id}
- GET /groups
- GET /shares
- GET /shares/{id}
- GET /effective-permissions
- GET /effective-permissions/by-user/{id}
- GET /effective-permissions/by-share/{id}
- GET /reviews
- POST /reviews
- PUT /reviews/{id}
- GET /sync/history
- GET /sync/history/{id}
- GET /exports/effective-permissions.csv
- GET /exports/effective-permissions.xlsx

Gestisci:
- loading
- errore
- empty state
- paginazione
- filtri serializzati in query params

---

## Tabelle e filtri
Usa TanStack Table.

Ogni tabella deve supportare almeno:
- ordinamento
- paginazione
- filtro di ricerca
- stato vuoto
- stato caricamento

---

## Requisiti review workflow
Nel dettaglio utente e nel dettaglio cartella, se il ruolo è reviewer o admin, consenti di:
- aprire form review
- selezionare decisione:
  - approved
  - revoke
  - modify_request
- inserire nota
- salvare la review

---

## Requisiti tecnici

### Routing
Usa routing chiaro e leggibile.

### State management
Non introdurre Redux se non necessario.
Preferisci:
- React state
- custom hooks
- eventuale context per auth

### Types
Definisci tipi coerenti per:
- auth
- nas user
- group
- share
- effective permission
- review
- snapshot
- paginated responses

### Error handling
Mostra errori leggibili in UI.

### Accessibilità base
- label sui form
- focus states minimi
- bottoni chiari

---

## Requisiti di qualità
- codice manutenibile
- componenti riutilizzabili
- niente hardcoding di endpoint
- variabili ambiente per base URL API
- niente librerie inutili

---

## Docker
Crea:
- Dockerfile frontend
- configurazione build e avvio
- `.env.example` se necessario

---

## Output atteso
Restituisci:
- codice completo frontend
- componenti principali
- routing
- integrazione API
- gestione auth
- Dockerfile
- README frontend con istruzioni di avvio locale e Docker
