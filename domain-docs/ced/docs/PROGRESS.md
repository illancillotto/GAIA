# GAIA CED
## Progress

## Stato corrente

- stato generale: `planned`
- implementazione runtime: non iniziata
- documentazione iniziale: completata

## Decisioni gia prese

- `GAIA CED` nasce come contenitore frontend unificato
- nella prima fase non esiste un backend `ced` dedicato
- i backend restano:
  - `accessi` per le superfici NAS
  - `network` per le superfici Rete
- i permessi restano:
  - `module_accessi`
  - `module_rete`

## Checklist esecutiva

### Fase 0 — Documentazione

- [x] PRD `GAIA CED`
- [x] implementation plan
- [x] prompt Codex
- [x] progress file
- [x] aggiornamento docs root

### Fase 1 — Entry point CED

- [ ] creare `frontend/src/app/ced/page.tsx`
- [ ] aggiornare home con tile `GAIA CED`
- [ ] aggiornare login con presentazione `GAIA CED`
- [ ] aggiungere voce `CED` in platform sidebar
- [ ] aggiungere `currentModuleKey = "ced"`
- [ ] introdurre module sidebar `CED`

### Fase 2 — Aree NAS e Rete

- [ ] introdurre `ced/nas/*`
- [ ] introdurre `ced/rete/*`
- [ ] riusare o wrappare le pagine esistenti
- [ ] controllare accessi per area

### Fase 3 — Migrazione navigazione

- [ ] riallineare i link interni a `/ced/...`
- [ ] decidere politica redirect per `/nas-control/*` e `/network/*`
- [ ] aggiornare test frontend

### Fase 4 — Valutazioni future

- [ ] analisi su `module_ced`
- [ ] analisi su nuove `sections` CED
- [ ] decisione su deprecazione nomenclatura legacy

## Open questions

- mantenere per lungo tempo sia `nas-control` sia `ced/nas`, oppure aggiungere redirect presto?
- usare label UI `Rete` o `Network` dentro CED?
- introdurre una dashboard CED ricca fin dalla prima fase o partire con una shell minimale?
- quando pianificare l'eventuale unificazione dei permessi?

## Note operative

- la base documentale e pronta per iniziare nei prossimi giorni
- il perimetro raccomandato per il primo step e solo frontend/navigation
- eventuali cambi backend devono essere oggetto di task separato
