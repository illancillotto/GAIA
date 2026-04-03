# Prompt 1: Analisi e Piano Integrazione Visure in GAIA

Nel workspace attuale stai lavorando sul progetto GAIA.

Devi analizzare come integrare in GAIA la logica di recupero visure catastali prendendo come riferimento il progetto sorgente:
`/home/cbo/CursorProjects/VisureFetcher`

## Obiettivo dell'analisi

Capire come integrare in GAIA i due flussi SISTER:

1. recupero visura per immobile:
   - comune
   - foglio
   - particella
   - eventuale subalterno
   - tipo catasto se previsto
2. recupero visura per soggetto:
   - persona fisica / persona giuridica
   - codice fiscale / partita IVA / CF soggetto
   - tipo richiesta: attualità / storica

Questa fase è solo di analisi e pianificazione.
Non implementare ancora modifiche strutturali importanti.
Puoi al massimo fare micro-modifiche innocue solo se indispensabili per ispezionare meglio il progetto, ma l'obiettivo principale è produrre un piano tecnico preciso.

## Vincoli

- non copiare VisureFetcher integralmente
- non portare dentro GAIA la GUI desktop, Tkinter, .bat, launcher o codice UI legacy
- non creare un sottoprogetto parallelo dentro GAIA
- devi adattare la logica di VisureFetcher all'architettura di GAIA
- devi distinguere chiaramente:
  - logica applicativa / dominio
  - adapter browser/SISTER
  - API / job runner / persistenza / logging
- se trovi codice duplicato o varianti multiple nel sorgente, individua quale sia la base migliore da migrare
- concentrati soprattutto sul backend di GAIA, non sul frontend React salvo interfacce minime

## Cosa devi analizzare in VisureFetcher

Individua i moduli rilevanti per:

- parsing input
- classificazione tipo soggetto PF / PNF
- orchestrazione del flusso visure
- ricerca per immobile
- ricerca per soggetto
- gestione outcome: `ok`, `fail`, `skip`, `not_found`
- gestione casi "nessuna corrispondenza"
- retry policy e recovery policy
- error classification
- observer/eventi
- artifact diagnostici
- report finale json/md

## Cosa devi analizzare in GAIA

Individua:

- struttura backend
- struttura frontend
- modelli / schema layer
- servizi applicativi
- job runner / background execution
- API layer
- logging / observability
- storage di file/artifact/report
- eventuali convenzioni architetturali da rispettare

## Output richiesto

Voglio un piano concreto e operativo, non generico.

Dammi:

1. i file/moduli di GAIA che intendi toccare o creare
2. i file/moduli di VisureFetcher che useresti come sorgente logica
3. la struttura target proposta dentro GAIA
4. come pensi di rappresentare i due flussi:
   - immobile
   - soggetto PF/PNF
5. come pensi di gestire:
   - retry
   - `not_found`
   - artifact diagnostici
   - report
   - job lunghi lato FastAPI
6. i principali rischi di integrazione
7. una sequenza di implementazione in passi piccoli e sicuri

## Importante

Prima esplora davvero il codice di GAIA e quello di VisureFetcher.
Non limitarti a una proposta teorica.
Voglio riferimenti concreti ai file reali del repository.

Alla fine fermati dopo il piano.
Non procedere ancora con l'implementazione completa.
