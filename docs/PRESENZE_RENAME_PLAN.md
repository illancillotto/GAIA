# Presenze Rename Plan

Ultimo aggiornamento: `2026-06-25`

## Obiettivo

Rinominare il dominio oggi esposto come `Inaz` verso un naming prodotto coerente:

- `Presenze` come nome di dominio
- `Giornaliere` come etichetta operativa di pagine e funzioni centrali sul cartellino

## Strategia

Il refactor viene separato in tre fasi per contenere il rischio.

### Fase A

Obiettivo:

- rimuovere `Inaz` dalle superfici utente

Perimetro:

- menu, sidebar, breadcrumb
- titoli pagina
- badge, card, metriche, empty state
- messaggi di errore e conferma utente
- label wiki e bootstrap sezioni
- documentazione operativa minima

Vincoli:

- nessun cambio a route, API, DB o tipi runtime

Deliverable:

- UI consistente lato utente
- documentazione di stato e piano aggiornata

Effort stimato:

- `1-2` giorni

Rischio:

- basso

Gate:

- smoke test frontend
- verifica manuale pagine del modulo

### Fase B

Obiettivo:

- introdurre naming tecnico `Presenze` senza rompere la compatibilita esterna

Perimetro frontend:

- componenti e pagine interne del modulo
- helper modulo-specifici
- export compatibili in `types/api.ts`
- wrapper compatibili in `lib/api.ts`

Perimetro backend:

- service e helper interni
- script e documentazione tecnica
- alias progressivi nei layer dove opportuno

Compatibilita da mantenere:

- naming storico nelle tabelle `inaz_*`
- path canonico del repository esterno `presenze-scraper`

Deliverable:

- naming tecnico interno piu pulito
- compatibilita conservata

Effort stimato:

- `4-6` giorni

Rischio:

- medio

Gate:

- test backend modulo
- test frontend
- nessuna migrazione DB richiesta

### Fase C

Obiettivo:

- completare il passaggio dal naming pubblico legacy al naming canonico `Presenze`

Perimetro:

- route legacy -> `/presenze/...`
- tipi legacy -> `Presenze*`
- client API frontend
- schemi e router backend
- eventuali chiavi di sezione e permesso
- eventuali tabelle `inaz_*` -> `presenze_*`

Strategia raccomandata:

1. introdurre doppio supporto temporaneo
2. deployare FE e BE compatibili
3. rimuovere il legacy in una release successiva

Effort stimato:

- `8-12` giorni se include anche rename DB e compatibilita completa

Rischio:

- alto

Gate:

- piano migrazione
- rollout coordinato
- regression test completi

## Backlog operativo

### Blocco A1

- chiudere i testi utente residui nel frontend
- passata finale su wiki hints e testi cross-modulo
- aggiornare documentazione operativa minima

### Blocco A2

- validazione manuale del modulo
- screenshot review o verifica con browser
- commit dedicato Fase A

### Blocco B1

- creare alias `Presenze*` nel frontend
- introdurre wrapper `getPresenze...`, `listPresenze...`, `updatePresenze...`
- mantenere solo compatibilita minima sui naming legacy ancora necessari

Stato:

- `completato`
- alias di tipo e wrapper frontend introdotti
- dashboard, export, sync, collaboratori, dettaglio collaboratore, festivita, settings, anomalie, recuperi, banca ore, giornaliere e configurazione gia migrati al layer `Presenze*`

### Blocco B2

- introdurre naming interno `presenze` in helper e servizi selezionati
- aggiornare test e docs tecniche

### Blocco C1

- disegnare layer di compatibilita API
- decidere la durata della compatibilita legacy lato routing

Stato:

- `completato`
- frontend e backend usano `/presenze/...` come namespace canonico
- gli alias pubblici legacy sono stati rimossi dal runtime
- `app/presenze/*` e la sorgente primaria

### Blocco C2

- valutare migrazione DB e naming tabelle
- eseguire solo se il valore supera chiaramente il costo

Stato:

- `parzialmente completato`
- la capability utenti e lo storage applicativo usano ormai `module_presenze`
- il rename delle tabelle fisiche `inaz_*` resta rimandato

### Blocco C3

- portare il runtime canonico da chiave modulo `inaz` a `presenze`
- mantenere alias compatibili nei gate applicativi e nei payload sensibili
- aggiornare self-service `/me` e sidebar al naming canonico

Stato:

- `quasi completato`
- `ProtectedPage`, sidebar e module switcher usano ora `presenze` come chiave canonica
- le pagine `app/presenze/*` richiedono ora `requiredModule="presenze"`
- backend e frontend usano `presenze` come chiave canonica
- `frontend/src/types/api.ts` e `frontend/src/lib/api.ts` usano ora `Presenze*` come namespace canonico per recovery, banca ore, festivita, turni, import, sync e credenziali
- il contratto `/me/summary` espone ora `km_from_presenze` come chiave canonica
- i download artefatti della sync usano ora il prefisso file `presenze-sync-*`
- wiki support, capability registry e semantic routing usano ora `presenze` come module key canonica
- catalogo sezioni ACL e resolver permessi usano ora `presenze.*` come chiave canonica
- le response canoniche utenti (`/auth/me`, `/admin/users...`) espongono ora `module_presenze`
- il backend core (`api_router`, `main`, `db/base`, self-service `/me`) importa ora il dominio canonico da `app.modules.presenze.*`
- OpenAPI del router canonico `/presenze` usa ora il tag `presenze`
- anche test backend, script di verifica export e launcher del worker sync sono stati riallineati al namespace canonico `app.modules.presenze.*`
- il frontend runtime canonico non usa piu alias legacy nella navigazione principale, nella shell e nel self-service
- il contratto `/me` non pubblica piu chiavi legacy del modulo
- il package fisico backend e stato invertito: `backend/app/modules/presenze/*` contiene ora la sorgente reale del dominio
- il runtime backend legge e scrive ora `module_presenze` come attributo canonico del modello `ApplicationUser`, con colonna DB gia rinominata
- gli schemi canonici `CurrentUserResponse`, `ApplicationUserResponse` e i tipi TS principali non espongono piu il flag legacy del modulo
- il backend non pubblica piu il flag legacy nel contratto canonico
- gli alias pubblici legacy del modulo sono stati rimossi
- le route frontend legacy del modulo sono state eliminate
- la configurazione runtime adotta ora solo chiavi canoniche `presenze_*`
- le fixture e i test unitari frontend principali usano ormai payload canonici `Presenze`
- la documentazione architetturale e di implementation plan e stata riallineata alle route `/presenze/...`
- il client frontend canonico non esporta piu alias runtime o di tipo legacy dal layer API

Checklist esecutiva dettagliata:

- vedi [docs/PRESENZE_PHASE_C_CHECKLIST.md](/home/cbo/CursorProjects/GAIA/docs/PRESENZE_PHASE_C_CHECKLIST.md:1)
- analisi go/no-go rimozione legacy: [docs/PRESENZE_LEGACY_REMOVAL_GO_NO_GO.md](/home/cbo/CursorProjects/GAIA/docs/PRESENZE_LEGACY_REMOVAL_GO_NO_GO.md:1)

## Decisioni aperte

- usare `Presenze` o `Giornaliere` come label primaria di menu nel lungo periodo
- decidere se il rename debba arrivare anche alle tabelle fisiche `inaz_*`
- consolidare definitivamente il repository esterno `presenze-scraper`

## Raccomandazione

Procedere subito cosi:

1. chiudere la pulizia documentale della Fase C
2. separare il tema "rename prodotto" dal tema "rename storage fisico"
3. consolidare il repository esterno in una change dedicata con impatto deploy verificato
