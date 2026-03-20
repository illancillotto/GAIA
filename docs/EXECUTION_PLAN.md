# Execution Plan

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

## Milestone 5. Frontend Applicativo

- login reale contro backend
- stato sessione minimale
- dashboard con dati backend
- viste placeholder sostituite con dati reali per snapshot e utenti

## Milestone 6. Hardening e Runtime

- smoke test compose e health integrati
- CI piu vicina al runtime reale
- script bootstrap admin
- affinamento deployment e note operative

## Ordine di Esecuzione Corrente

1. entrare in Milestone 4 sul permission engine MVP
2. aggiornare `docs/PROGRESS.md` a ogni tranche
3. rieseguire test backend e frontend a ogni milestone
4. mantenere CI allineata ai test reali

## Criteri di Uscita per Ogni Milestone

- codice integrato
- test verdi locali o in CI
- documentazione aggiornata
- progress tracker aggiornato con esito reale
