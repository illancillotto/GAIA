# Execution Plan

> Regola di esecuzione
> Tutte le nuove implementazioni backend per Accessi devono convergere verso `app/modules/accessi/`.

## Obiettivo

Guidare l'implementazione del progetto in milestone piccole, verificabili e testabili in autonomia, mantenendo allineati codice, documentazione, CI e progress tracking.

## Principi Operativi

- incrementi verticali piccoli ma completi
- ogni milestone chiude codice, test e documentazione
- evitare placeholder inutili quando un modulo puo gia essere reso verificabile
- mantenere il backend come sorgente di verita per dominio e sicurezza

## Milestone 1. Fondazioni Applicative

### Backend

- autenticazione applicativa con JWT
- modello `ApplicationUser`
- endpoint `POST /auth/login`
- endpoint `GET /auth/me`
- utility sicurezza per password hash e token
- migration Alembic per utenti applicativi

Stato:

- completato

### Test

- login valido
- login con credenziali errate
- accesso a `/auth/me` con token valido
- accesso negato senza token
- durata token JWT configurata a 90 minuti tramite `JWT_EXPIRE_MINUTES`

## Milestone 2. Dominio Audit Minimo

- modelli base per `NasUser`, `NasGroup`, `Share`, `Review`
- migration dedicata
- repository e schema Pydantic minimi
- endpoint lettura base per dashboard e liste principali

Stato:

- completato

## Milestone 3. NAS Integration Skeleton

- connector SSH configurabile
- interfaccia service per fetch utenti, gruppi, share e ACL
- parser iniziali con test su fixture statiche
- endpoint o job placeholder per sync

Stato:

- completato

## Milestone 4. Permission Engine MVP

- tabelle per permission entry ed effective permission
- servizio di calcolo con regole minime `allow`, `deny`, `write implies read`
- test unitari su casi principali

Stato:

- completato

## Milestone 5. Frontend Applicativo

- login reale contro backend
- stato sessione minimale
- dashboard con dati backend
- viste placeholder sostituite con dati reali per snapshot e utenti

Stato:

- in progress

Avanzamento attuale:

- login reale completato
- dashboard collegata al backend completata
- viste reali disponibili per utenti NAS, gruppi NAS, share, review, sync ed effective permissions
- preview frontend del permission engine disponibile
- bootstrap admin disponibile per sbloccare il login reale senza seed manuale
- seed iniziale dominio audit disponibile per popolare subito dashboard e liste
- pagina `Sync` collegata a preview e apply persistente su backend
- live apply via SSH disponibile con degradazione controllata in assenza di NAS raggiungibile
- job/script di live sync con retry controllato disponibile
- audit trail persistente delle sync disponibile e visibile in UI/API
- runner schedulato della live sync disponibile con loop configurabile
- backoff configurabile per i retry della live sync disponibile

## Milestone 6. Hardening e Runtime

- smoke test compose e health integrati
- CI piu vicina al runtime reale
- script bootstrap admin
- script bootstrap dominio audit
- sync persistente minimale via payload testuale
- live sync singola via SSH
- retry operativo per live sync
- tracciamento persistente degli esiti di sync
- scheduling operativo minimale via script
- backoff `fixed` o `exponential` configurabile
- affinamento deployment e note operative

## Ordine di Esecuzione Corrente

1. completare Milestone 5 sul frontend applicativo
2. aggiornare `domain-docs/accessi/docs/PROGRESS.md` a ogni tranche
3. rieseguire test backend e frontend a ogni milestone
4. mantenere CI allineata ai test reali
5. consolidare Milestone 6 con smoke check runtime ripetibili e policy retry/backoff robuste

## Criteri di Uscita per Ogni Milestone

- codice integrato
- test verdi locali o in CI
- documentazione aggiornata
- progress tracker aggiornato con esito reale

- [x] Milestone 8 (permessi granulari): backend core completato (migrations, modelli, resolver, route principali, bootstrap script).
