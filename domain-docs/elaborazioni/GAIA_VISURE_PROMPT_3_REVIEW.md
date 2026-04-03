# Prompt 3: Review Finale Integrazione Visure in GAIA

Esegui una review tecnica dell'integrazione della logica visure in GAIA.

Contesto:

- il progetto target è GAIA
- la sorgente funzionale di riferimento è `/home/cbo/CursorProjects/VisureFetcher`
- l'integrazione dei flussi visure è già stata implementata

## Obiettivo della review

Verificare che l'integrazione sia corretta, pulita e coerente con GAIA, con focus su:

- bug funzionali
- regressioni architetturali
- accoppiamenti impropri col vecchio progetto
- gestione sbagliata dei retry
- casi `not_found` trattati male
- assenza o debolezza di artifact/report diagnostici
- rischi operativi nei job lunghi lato FastAPI

## Cosa devi controllare

Controlla in particolare:

1. flusso recupero per immobile
   - input
   - orchestrazione
   - outcome
   - error handling

2. flusso recupero per soggetto
   - distinzione PF / PNF
   - compilazione input soggetto
   - ricerca soggetto
   - apertura visura
   - gestione "nessuna corrispondenza"

3. gestione outcome
   - `ok`
   - `fail`
   - `skip`
   - `not_found`

4. retry policy
   - verifica che i `not_found` non siano retryati
   - verifica che gli errori retryable siano centralizzati e coerenti
   - verifica che non ci siano loop o retry infiniti

5. diagnosi e osservabilità
   - logging strutturato
   - observer/eventi
   - artifact diagnostici
   - report finali

6. qualità integrazione in GAIA
   - coerenza con l'architettura del progetto
   - separazione tra logica applicativa e adapter SISTER/browser
   - assenza di codice desktop/legacy trascinato inutilmente
   - assenza di stato globale fragile

7. API e job execution
   - job lunghi non eseguiti in modo improprio dentro la request
   - endpoint coerenti
   - recupero stato/eventi/report/artifact

## Modalità di risposta

Rispondi in modalità code review.
Metti prima i findings, ordinati per severità, con riferimenti concreti ai file.

Per ogni finding indica:

- severità
- file
- problema
- impatto
- correzione consigliata

Se non trovi problemi rilevanti, dillo esplicitamente.

Dopo i findings, aggiungi solo in modo sintetico:

1. rischi residui
2. gap di test o verifica
3. breve riepilogo dell'architettura risultante

## Vincoli

- non riscrivere tutto
- non dare consigli generici
- basa la review sul codice reale presente in GAIA
- confronta l'integrazione con la logica sorgente di VisureFetcher quando serve
