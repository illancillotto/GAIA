# Prompt 2: Implementazione Integrazione Visure in GAIA

Implementa ora il piano di integrazione visure in GAIA, usando come sorgente di riferimento:
`/home/cbo/CursorProjects/VisureFetcher`

## Contesto

Hai già analizzato GAIA e VisureFetcher.
Ora devi eseguire l'integrazione vera nel progetto GAIA.

## Obiettivo

Integrare nel backend di GAIA il supporto ai due flussi di recupero visure SISTER:

1. recupero per immobile:
   - comune
   - foglio
   - particella
   - eventuale subalterno
2. recupero per soggetto:
   - persona fisica / persona giuridica
   - codice fiscale / partita IVA / CF
   - richiesta attualità / storica

## Vincoli forti

- non copiare VisureFetcher in blocco
- non portare GUI desktop, Tkinter, launcher, .bat o codice UI legacy
- integra la logica dentro l'architettura reale di GAIA
- mantieni separati:
  - logica applicativa
  - adapter/browser SISTER
  - API e job execution
- riusa i pattern di logging, config, dependency injection, job execution e persistenza già esistenti in GAIA quando possibile
- se GAIA ha convenzioni di struttura o naming, rispettale

## Comportamenti obbligatori da preservare

- supporto a entrambi i flussi: immobile e soggetto
- distinzione corretta PF / PNF
- outcome espliciti: `ok`, `fail`, `skip`, `not_found`
- il caso "nessuna corrispondenza" deve essere terminale `not_found`, non retryabile
- i `not_found` devono essere tracciati in modo diagnostico
- retry policy e recovery policy devono essere centralizzate e coerenti
- report finale e artifact diagnostici devono restare disponibili

## Implementazione richiesta

1. crea o aggiorna i moduli backend necessari
2. migra/adatta la logica utile di VisureFetcher
3. integra i due flussi nel service layer di GAIA
4. aggiungi o aggiorna endpoint/hook applicativi minimi per:
   - avvio job visure
   - stato job
   - eventi/log del job
   - report/artifact del job
   - eventuale cancellazione job
5. collega logging, observer, report e artifact
6. fai in modo che i job lunghi non blocchino impropriamente la request HTTP
7. aggiungi test o verifiche minime se coerenti con il progetto

## Ordine di lavoro

Procedi in passi piccoli e concreti:

1. crea i modelli dati / schema layer necessari
2. crea gli outcome e la logica di classificazione errori/retry
3. crea o integra l'orchestratore del job visure
4. integra l'adapter SISTER/browser
5. collega API/job runner
6. collega report/artifact
7. verifica import, compilazione e test minimi

## Criteri di qualità

- niente accoppiamenti inutili col vecchio progetto
- niente stato globale ereditato se evitabile
- moduli chiari e riusabili
- codice coerente con GAIA
- comportamento robusto sui casi terminali e sui retry

## Verifiche obbligatorie

Controlla in particolare:

- flusso immobile
- flusso soggetto PF
- flusso soggetto PNF
- caso `not_found`
- assenza di loop di retry sui `not_found`
- disponibilità di artifact/report per diagnosi

## Output finale richiesto

A fine lavoro mostrami:

1. file creati/modificati
2. architettura finale dell'integrazione
3. come funzionano i due flussi
4. come vengono gestiti retry e `not_found`
5. come recuperare report e artifact
6. eventuali limiti o TODO residui

Procedi direttamente con l'implementazione.
