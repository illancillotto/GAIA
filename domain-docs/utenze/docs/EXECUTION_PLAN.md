# Execution Plan

> Regola di esecuzione
> Tutte le nuove implementazioni backend per Anagrafica devono convergere verso `backend/app/modules/anagrafica/`.

## Obiettivo

Guidare l'implementazione di GAIA Anagrafica in milestone verticali, piccole e verificabili, mantenendo allineati backend, frontend, permessi piattaforma, migrazioni, test e documentazione.

## Principi Operativi

- incrementi verticali piccoli ma completi
- ogni milestone chiude codice, test e documentazione essenziale
- il modulo deve essere integrato nella piattaforma GAIA, non solo aggiunto come codice isolato
- privilegiare il riuso di auth, config NAS, database e pattern UI già esistenti
- il NAS resta read-only; eventuale scrittura è solo su DB GAIA e storage locale GAIA

## Milestone 1. Integrazione Piattaforma

### Backend

- aggiungere `module_anagrafica` a `application_users`
- aggiornare `enabled_modules`
- aggiornare schema e route di amministrazione utenti GAIA
- aggiungere section key `anagrafica.*` in `backend/app/scripts/bootstrap_sections.py`
- includere il router del modulo in `backend/app/api/router.py`

### Frontend

- aggiungere Anagrafica alla home moduli
- aggiungere Anagrafica a `PlatformSidebar`
- aggiungere navigation dedicata in `ModuleSidebar`
- aggiornare i tipi condivisi frontend relativi all'utente corrente e agli utenti GAIA

### Test

- test migration per nuovo flag modulo
- test `enabled_modules` aggiornato
- test accesso negato/consentito al modulo

Stato:

- pending

## Milestone 2. Modello Dati e Metadata

### Backend

- introdurre i modelli `ana_subjects`, `ana_persons`, `ana_companies`, `ana_documents`, `ana_import_jobs`, `ana_audit_log`
- definire enum e vincoli principali
- creare migration Alembic dedicata
- registrare i modelli nel bootstrap metadata usato da ORM e Alembic
- predisporre gli indici minimi per ricerca e idempotenza

### Test

- test Alembic upgrade/downgrade
- test vincoli unici su CF/P.IVA
- test creazione record base PF e PG

Stato:

- pending

## Milestone 3. Parser e Classificazione

### Backend

- implementare parser nome cartella per PF, PG e casi `UNKNOWN`
- implementare classificatore documenti pattern-based
- gestire edge case noti dell'archivio reale
- definire payload di preview import

### Test

- test parser con fixture reali e casi degradati
- test classificatore su set minimo di filename rappresentativi

Stato:

- pending

## Milestone 4. Connettore NAS e Preview Import

### Backend

- riusare la configurazione NAS già esistente in `app/core/config.py`
- implementare lettura archivio per lettera con preferenza al canale già supportato dal backend
- produrre preview import senza persistenza
- raccogliere warning ed errori strutturati

### Test

- test unit/service con adapter o mock del connettore NAS
- test preview con cartelle speciali, sottocartelle e file non PDF

Stato:

- pending

## Milestone 5. Commit Import e Idempotenza

### Backend

- implementare `run_import`
- creare/aggiornare soggetti e documenti senza duplicati
- tracciare `ana_import_jobs` con statistiche e log
- definire comportamento di re-import
- aggiungere audit log minimo per import e update principali

### Test

- test re-import senza duplicati
- test soggetti `UNKNOWN`
- test import parziale con warning ed errori

Stato:

- pending

## Milestone 6. API CRUD e Ricerca

### Backend

- implementare endpoint CRUD soggetti
- implementare endpoint documenti e job import
- implementare statistiche aggregate
- introdurre controllo accessi modulo/sezione
- introdurre ricerca testuale iniziale

### Test

- test API per create/read/update/deactivate
- test permessi modulo e sezione
- test paginazione, filtri e ricerca

Stato:

- pending

## Milestone 7. Frontend Operativo

### Frontend

- pagina lista soggetti con filtri e paginazione lato server
- scheda soggetto con dati, documenti e audit log
- wizard import con preview e avvio job
- dashboard sintetica del modulo

### Integrazione

- coerenza con layout, auth flow e componenti condivisi
- wiring API in `frontend/src/lib/api.ts`
- aggiornamento tipi `frontend/src/types/api.ts`

### Test

- smoke test frontend delle route principali
- verifica manuale dei flussi lista, dettaglio e import

Stato:

- pending

## Milestone 8. Search, Export e Correlazioni

### Backend

- full-text search PostgreSQL robusta
- export CSV/XLSX
- correlazione in sola lettura con Catasto
- affinamento audit log e classificazione manuale documenti

### Frontend

- azioni export
- filtri avanzati
- visualizzazione correlazioni con Catasto dove disponibili

### Test

- test export
- test ricerca full-text
- test correlazione senza dipendere da chiamate interne tra moduli

Stato:

- pending

## Ordine di Esecuzione Corrente

1. completare Milestone 1 per rendere Anagrafica un modulo assegnabile e visibile in GAIA
2. chiudere Milestone 2 prima di implementare import e CRUD
3. implementare parser/classificazione prima del connettore NAS definitivo
4. introdurre preview import prima del commit persistente
5. completare backend MVP prima di estendere le pagine frontend
6. rinviare export e correlazioni avanzate dopo il flusso operativo base

## Criteri di Uscita per Ogni Milestone

- codice integrato nel monolite esistente
- test verdi locali per la superficie toccata
- documentazione aggiornata
- nessuna duplicazione evitabile di auth, config o logica già presente
- nessuna regressione dei moduli esistenti

## Rischi Principali

- forte variabilità dei nomi cartella e dei documenti nel NAS reale
- possibile mismatch tra path SMB documentale e canale tecnico realmente usato dal backend
- costo implementativo extra per integrazione modulo/permessi/UI globale
- rischio di ambiguità tra soggetti duplicati, `UNKNOWN` e correlazioni con Catasto

## Note Operative

- usare come sorgenti primarie `domain-docs/anagrafica/docs/PRD_anagrafica.md` e `domain-docs/anagrafica/docs/PROMPT_CODEX_anagrafica.md`
- verificare sempre i pattern reali in `backend/app/modules/accessi/`, `backend/app/modules/catasto/`, `backend/app/modules/network/`
- aggiornare questo piano e aggiungere un `PROGRESS.md` quando parte l'implementazione effettiva
