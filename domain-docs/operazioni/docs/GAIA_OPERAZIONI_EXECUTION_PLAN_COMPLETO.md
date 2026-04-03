# GAIA Operazioni — Execution Plan Completo

## 1. Obiettivo del piano

Questo piano descrive le attività di implementazione del modulo **GAIA Operazioni** per:
- gestione mezzi
- attività operatori
- segnalazioni e pratiche interne
- allegati multimediali
- GPS e consuntivazione
- mini-app operatori

Il piano è coerente con l'architettura GAIA a backend unico, frontend unico e database PostgreSQL condiviso.

---

## 2. Principi di esecuzione

- implementazione incrementale per milestone
- priorità ai workflow core prima delle ottimizzazioni
- nessuna deviazione dall'architettura monolite modulare
- mini-app semplice fin dall'inizio
- audit trail e integrità dati trattati come requisiti core

---

## 3. Milestone

## Milestone 0 — Allineamento e scaffolding

### Obiettivi
- creare il modulo `operazioni`
- allineare docs, schema e naming
- predisporre la base tecnica

### Attività
- creare cartelle backend modulo
- creare cartelle frontend modulo
- registrare router backend
- registrare voci navigazione frontend
- predisporre feature folder frontend
- verificare naming tabella utenti di riferimento
- predisporre cartella docs dominio `domain-docs/operazioni/docs/`

### Deliverable
- scaffolding modulo
- router registrato
- pagine placeholder frontend
- docs dominio iniziali

---

## Milestone 1 — Data layer e API core mezzi

### Obiettivi
- rendere operativa la parte Mezzi

### Attività backend
- implementare model DB mezzi
- implementare migration Alembic
- implementare CRUD mezzi
- implementare assegnazioni storiche
- implementare sessioni utilizzo mezzo
- implementare fuel log
- implementare maintenance

### Attività frontend
- lista mezzi
- dettaglio mezzo
- badge stato
- filtri base
- viste utilizzi/manutenzioni

### Deliverable
- API mezzi complete
- UI mezzi base
- test backend mezzi

---

## Milestone 2 — Attività operatori e approvazione

### Obiettivi
- rendere operativo il ciclo attività

### Attività backend
- implementare catalogo attività
- implementare create/start/stop activity
- implementare approval workflow
- implementare note e legame allegati
- implementare summary GPS attività

### Attività frontend
- lista attività
- dettaglio attività
- approvazioni capo servizio
- filtri per stato/operatore/squadra/mezzo

### Deliverable
- API attività complete
- UI attività desktop
- test start/stop/approve

---

## Milestone 3 — Segnalazioni e pratiche

### Obiettivi
- rendere operativo il workflow segnalazione → pratica

### Attività backend
- create field report
- generazione automatica internal case
- case events
- case assignment
- case status transitions
- close case

### Attività frontend
- lista segnalazioni
- lista pratiche
- dettaglio pratica con timeline eventi
- azioni assegnazione / cambio stato / chiusura

### Deliverable
- API segnalazioni/pratiche complete
- UI pratiche e timeline
- test creazione segnalazione e case

---

## Milestone 4 — Allegati e storage governance

### Obiettivi
- rendere robusta la gestione media

### Attività backend
- metadata allegati
- validazioni mime/size
- quota usage service
- soglie 70/85/95
- endpoint dashboard storage

### Attività frontend
- card storage usage
- pagina storage admin
- preview allegati dove possibile
- errori upload chiari

### Deliverable
- storage governance base
- alert quota visibili
- test quota e attachment metadata

---

## Milestone 5 — Mini-app operatori

### Obiettivi
- fornire interfaccia mobile-first operativa

### Attività frontend
- home mini-app
- nuova attività
- chiusura attività
- nuova segnalazione
- mie attività / mie segnalazioni
- banner stato rete e sync
- bozze locali

### Attività backend
- affinare endpoint per UX mobile
- endpoint liste personali ottimizzati

### Deliverable
- mini-app usabile sul campo
- UX semplificata
- primo supporto offline minimo

---

## Milestone 6 — GPS e consuntivazione

### Obiettivi
- consolidare valore consuntivo del sistema

### Attività backend
- GPS service astratto
- supporto dati GPS da mini-app
- supporto binding futuro provider mezzi
- summary GPS per attività e utilizzi mezzo
- distinzione dichiarato/rilevato/validato

### Attività frontend
- pannelli riepilogo GPS
- vista dati rilevati vs dichiarati
- indicatori anomalie di consuntivazione

### Deliverable
- modello GPS estendibile
- prime viste di consuntivazione

---

## Milestone 7 — Hardening, test e rilascio interno

### Attività
- test di regressione
- test permessi ruolo
- test su rete instabile
- pulizia UI
- revisione logging
- verifica performance query principali
- documentazione finale

### Deliverable
- modulo pronto per rilascio interno pilot
- checklist collaudo
- documentazione aggiornata

---

## 4. Priorità funzionali

### Priorità alta
- mezzi
- attività start/stop
- approvazione
- segnalazione → pratica
- allegati base
- mini-app semplice

### Priorità media
- storage analytics
- GPS summary
- timeline pratica evoluta

### Priorità successiva
- mappe evolute
- analytics avanzati
- integrazione vendor GPS piena

---

## 5. Dipendenze

- autenticazione/autorizzazione GAIA esistente
- tabella utenti applicativi esistente
- eventuale anagrafica squadre o necessità di crearla nel modulo
- storage file server-side disponibile
- definizione percorso file e policy backup
- decisione tecnica su compressione media lato client/server

---

## 6. Rischi principali

### Rischio 1 — Incertezza provider GPS
Mitigazione: adapter astratto, nessun hard coupling.

### Rischio 2 — UX troppo complessa per operatori
Mitigazione: mini-app con tre azioni principali, test sul campo rapidi.

### Rischio 3 — Crescita rapida storage video
Mitigazione: soglie progressive, compressione, monitoraggio dashboard.

### Rischio 4 — Workflow approvativi troppo pesanti
Mitigazione: tenere il ciclo approvativo essenziale nel MVP.

### Rischio 5 — Offline non robusto
Mitigazione: offline minimo e sync semplice, senza logiche distribuite complesse.

---

## 7. Definizione di Done per milestone

Una milestone è completata quando:
- codice backend e frontend è integrato
- test minimi passano
- documentazione è aggiornata
- il progress tracking è aggiornato
- il flusso principale della milestone è dimostrabile end-to-end

---

## 8. Artefatti da mantenere aggiornati

- PRD Operazioni
- DB Schema Operazioni
- API Complete Operazioni
- Prompt Backend
- Prompt Frontend
- Execution Plan
- Progress

---

## 9. Ordine consigliato di sviluppo

1. scaffolding modulo
2. schema DB + migration
3. API mezzi
4. API attività
5. API segnalazioni/pratiche
6. allegati + storage
7. UI desktop
8. mini-app
9. GPS summary
10. hardening e test

---

## 10. Esito atteso

Al termine del piano, GAIA disporrà di un modulo Operazioni capace di supportare in modo auditabile e pratico la gestione dei mezzi, delle attività e delle segnalazioni operative del Consorzio.
