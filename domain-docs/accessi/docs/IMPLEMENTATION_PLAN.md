# Piano Implementazione

> Regola di implementazione
> Il codice legacy fuori da `app/modules/` va trattato come compatibilita. Nuove feature Accessi vanno nel namespace modulare canonico.

## 1. Obiettivo Operativo

### Ciclo CED — 2026-10-02

- [x] Policy backend centralizzata per gestione utenti standard e moduli delegabili.
- [x] Blocco NAS/Rete, ruoli privilegiati, account CED e proprie abilitazioni.
- [x] Integrazione pagina Utenti GAIA e navigazione, senza abilitare NAS Control.
- [x] Test di API, persistenza, failure path, autorizzazione e regressione UI.
- [x] Contratto tecnico e matrice di validazione documentati.
- [ ] Chiusura del gate globale: vedere i controlli e i residui effettivi in
  `CED_USER_MANAGEMENT_VALIDATION.md`; nessun PASS implicito.
- [ ] Deploy e verifica operativa su `gaia.lan`, fuori dal ciclo locale.

Creare una base di progetto ordinata e avviabile, pronta per uno sviluppo incrementale dei moduli di audit NAS, review e reporting.

## 2. Fasi

### Fase 1. Bootstrap Repository

- convenzioni root e file di progetto
- README, env example e Makefile
- struttura backend, frontend e docs

### Fase 2. Fondazioni Backend

- FastAPI con routing modulare
- configurazione centralizzata
- integrazione SQLAlchemy e Alembic
- smoke test applicativo

### Fase 3. Fondazioni Frontend

- Next.js con App Router
- layout base enterprise
- home iniziale e login placeholder
- struttura modulare `src/`

### Fase 4. DevOps Locale

- Dockerfile dedicati
- Compose per backend, frontend, postgres e nginx
- script di supporto per shell e migrazioni

### Fase 5. CI Iniziale

- build frontend
- lint/test placeholder backend
- verifica automatica su push e pull request

## 3. Sequenza Raccomandata

1. definire modello dati minimo e migrazione iniziale
2. aggiungere autenticazione applicativa
3. introdurre connector NAS
4. sviluppare viste dati e review
5. rafforzare osservabilita e sicurezza

## 4. Deliverable Correnti

- backend avviabile con `/health`
- frontend buildabile con route base
- compose completo per ambiente locale
- documentazione base di prodotto e deployment

## 5. Rischi Iniziali

- dipendenza da comandi specifici del NAS Synology
- definizione dettagliata del permission engine
- integrazione futura con identita enterprise

## 6. Prossimi Passi

- aggiungere modelli dominio principali
- definire auth JWT e ruoli applicativi
- introdurre snapshot e sync NAS reali
- creare dashboard con dati mockati e poi reali
