# GAIA Operazioni — Prompt Frontend (Production Grade)

## Contesto

Stai lavorando nel frontend condiviso di **GAIA**, applicazione Next.js della piattaforma interna del Consorzio di Bonifica dell'Oristanese.

L'architettura del progetto prevede:
- frontend unico Next.js
- backend unico FastAPI
- modulo di dominio nuovo: `operazioni`
- UI amministrativa desktop + mini-app operatori mobile-first

Il frontend condiviso vive sotto:

`frontend/`

La nuova sezione applicativa deve vivere sotto:

`frontend/src/app/operazioni/`

Non creare frontend separati. Non creare SPA isolate fuori dal progetto. Non introdurre librerie non necessarie.

---

## Obiettivo

Implementare la sezione frontend del modulo **GAIA Operazioni** con:
- area admin/control desktop
- area capo servizio
- mini-app operatori mobile-first/PWA-ready
- schermate per mezzi, attività, segnalazioni/pratiche, storage, dashboard
- integrazione completa con le API backend del dominio

---

## Sorgenti di verità

Usa come riferimento:
- `GAIA_OPERAZIONI_API_COMPLETE.md`
- `GAIA_OPERAZIONI_DB_SCHEMA.md` per capire il dominio
- PRD del modulo Operazioni
- convenzioni UI già presenti negli altri moduli GAIA

Se il repository ha componenti shared, hooks, api client o pattern tabellari già presenti, riusali.

---

## Vincoli UI/UX obbligatori

### Generali
- coerenza visiva con GAIA
- componenti riusabili
- pagine desktop leggibili e operative
- mobile UX estremamente semplice per operatori
- accessibilità di base
- feedback di caricamento/successo/errore chiari

### Mini-app operatori
Target: personale operativo anche di età avanzata.

Quindi:
- pulsanti grandi
- pochi input
- testi chiari
- percorsi brevi
- massimo focus su 3 azioni principali
- stato sincronizzazione sempre visibile
- evitare tabelle dense e schermate affollate

---

## Struttura desiderata

Crea una sezione coerente con questa struttura, adattandola al repository:

```text
frontend/src/app/operazioni/
  page.tsx
  dashboard/
    page.tsx
  mezzi/
    page.tsx
    [id]/page.tsx
    utilizzi/page.tsx
    manutenzioni/page.tsx
  attivita/
    page.tsx
    [id]/page.tsx
    catalogo/page.tsx
    approvazioni/page.tsx
  segnalazioni/
    page.tsx
    [id]/page.tsx
  pratiche/
    page.tsx
    [id]/page.tsx
  storage/
    page.tsx
  miniapp/
    page.tsx
    attivita/nuova/page.tsx
    attivita/chiusura/[id]/page.tsx
    segnalazioni/nuova/page.tsx
    bozze/page.tsx
```

E crea, se utile, feature folder dedicati:

```text
frontend/src/features/operazioni/
  api/
  components/
  hooks/
  schemas/
  utils/
```

---

## Scope funzionale UI

### 1. Dashboard operazioni
Crea dashboard desktop con almeno:
- KPI principali
- attività da approvare
- pratiche aperte / urgenti
- mezzi attualmente in uso
- alert storage
- ultimi eventi operativi

Card suggerite:
- attività aperte oggi
- attività in approvazione
- pratiche aperte
- pratiche urgenti
- mezzi attivi
- quota storage usata

### 2. Mezzi
Pagine richieste:
- lista mezzi
- dettaglio mezzo
- storico assegnazioni
- utilizzi
- carburante
- manutenzioni
- documenti/scadenze se esposti da API

Funzionalità UI:
- filtri per stato/tipo/sede
- ricerca libera
- dettaglio con tab secondarie
- badge stato
- timeline sintetica utilizzi/manutenzioni
- CTA di import transazioni flotte `.xlsx` nella lista mezzi per alimentare i fuel log quando WhiteCompany non espone tutti i campi carburante

### 3. Attività
Pagine richieste:
- lista attività
- dettaglio attività
- approvazioni
- catalogo attività

Funzionalità UI:
- filtro per stato, data, operatore, squadra, mezzo
- dettaglio con dati dichiarati e dati GPS distinti
- approvazione/rifiuto con motivazione
- evidenza attività incomplete o anomalie

### 4. Segnalazioni e pratiche
Pagine richieste:
- lista segnalazioni
- dettaglio segnalazione
- lista pratiche
- dettaglio pratica

Funzionalità UI:
- filtri per severity, stato, categoria, assegnatario
- cronologia eventi pratica
- allegati preview se supportata
- assegnazione pratica
- cambio stato pratica
- chiusura pratica

### 5. Storage
Pagina admin con:
- quota usata
- soglia warning
- breakdown per tipo file e periodo
- elenco ultimi allegati pesanti
- alert stato 70/85/95%

### 6. Mini-app operatori
Home con tre azioni principali:
- Avvia attività
- Chiudi attività
- Nuova segnalazione

Schermate richieste:
- nuova attività
- chiusura attività aperta
- nuova segnalazione
- bozze/sincronizzazione
- mie attività recenti
- mie segnalazioni recenti

Vincoli UX:
- un’azione per schermata
- minimizzare digitazione manuale
- categorie/select predefiniti
- note audio e testo semplici
- stato GPS e stato rete sempre visibili
- messaggio evidente “inviato” / “in attesa di invio”

---

## Integrazione API

Usa gli endpoint definiti nel file API completo.

Implementa client API/frontend service per:
- vehicles
- assignments
- usage sessions
- fuel logs
- maintenance
- activity catalog
- activities
- approvals
- reports
- cases
- case events
- attachments
- storage/dashboard

Gestisci:
- loading
- errori
- empty state
- retry dove opportuno

---

## Offline minimo / PWA-ready

Non implementare un offline complesso enterprise se non richiesto dal repository, ma prepara una base seria per mini-app.

Richiesto:
- bozza locale per nuova attività
- bozza locale per nuova segnalazione
- coda invii pendenti
- indicatore stato connessione
- retry manuale/automatico semplice

Preferenze tecniche:
- IndexedDB o storage equivalente
- separazione chiara tra dati server e bozze locali
- non perdere i dati inseriti se la rete cade a metà

Mostra sempre:
- `Bozza locale`
- `In attesa di sincronizzazione`
- `Sincronizzato`
- `Errore di invio`

---

## Componenti richiesti

Crea componenti riusabili, ad esempio:
- `OperationStatCard`
- `StatusBadge`
- `SeverityBadge`
- `VehicleStatusBadge`
- `StorageUsageCard`
- `SyncStatusBanner`
- `MiniAppActionCard`
- `CaseTimeline`
- `AttachmentPreviewList`
- `GpsSummaryPanel`
- `ApprovalActionBar`

---

## Stato e filtri

Usa enum/frontend constants allineate alle API per:
- activity status
- case status
- report severity
- vehicle status
- storage alert status

Tutte le label devono essere user friendly in italiano.

---

## Error handling e feedback

Implementa pattern coerenti per:
- validazione form
- errore upload allegato
- errore geolocalizzazione
- errore sincronizzazione offline
- errore permessi/autorizzazione

Per le azioni critiche usa conferme dove utile, ma non bloccare inutilmente la mini-app con troppe modali.

---

## Qualità del codice

Richiesto:
- componenti piccoli e riusabili
- hooks dedicati per dominio
- tipi coerenti
- niente logica API sparsa nelle pagine
- niente schermate monolitiche difficili da mantenere
- naming chiaro in italiano o inglese coerente col progetto

---

## Output richiesto

Produci:
1. route app pages del modulo Operazioni
2. componenti condivisi del dominio
3. hooks/API client
4. schermate mini-app mobile-first
5. eventuale setup base PWA/offline se già presente nel progetto
6. breve nota su file creati e punti da rifinire

---

## Criteri di qualità finale

Il frontend deve risultare:
- coerente con GAIA
- immediatamente usabile lato admin
- molto semplice lato operatore
- pronto per aggancio al backend reale
- predisposto a crescita futura senza refactor massivo
