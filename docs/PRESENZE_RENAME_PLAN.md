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
- verifica manuale pagine `/inaz/*`

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

- route `/inaz/...`
- `module_inaz`
- tipi pubblici legacy `Inaz*`
- tabelle `inaz_*`

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

- eliminare `inaz` anche dal dominio tecnico pubblico

Perimetro:

- route `/inaz/...` -> `/presenze/...`
- tipi `Inaz*` -> `Presenze*`
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
- mantenere export legacy `Inaz*`

Stato:

- `completato`
- alias di tipo e wrapper frontend introdotti
- dashboard, export, sync, collaboratori, dettaglio collaboratore, festivita, settings, anomalie, recuperi, banca ore, giornaliere e configurazione gia migrati al layer `Presenze*`

### Blocco B2

- introdurre naming interno `presenze` in helper e servizi selezionati
- aggiornare test e docs tecniche

### Blocco C1

- disegnare layer di compatibilita API
- decidere se mantenere `/inaz` come alias permanente o temporaneo

Stato:

- `completato` per la prima ondata
- frontend ora preferisce `/presenze/...`
- route legacy `/inaz/...` mantenute come alias compatibili

### Blocco C2

- valutare migrazione DB e naming tabelle
- eseguire solo se il valore supera chiaramente il costo

Stato:

- `rimandato`
- prima ondata chiusa senza rename DB o ACL

Checklist esecutiva dettagliata:

- vedi [docs/PRESENZE_PHASE_C_CHECKLIST.md](/home/cbo/CursorProjects/GAIA/docs/PRESENZE_PHASE_C_CHECKLIST.md:1)

## Decisioni aperte

- usare `Presenze` o `Giornaliere` come label primaria di menu nel lungo periodo
- mantenere `/inaz` come route legacy permanente oppure eliminarla dopo migrazione
- mantenere `module_inaz` come flag storico o introdurre `module_presenze`

## Raccomandazione

Procedere subito cosi:

1. chiudere Fase A
2. aprire Fase B con alias compatibili
3. decidere la Fase C solo dopo avere stabilizzato naming e copertura test
