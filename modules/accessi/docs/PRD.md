# Product Requirements Document

## 1. Visione

NAS Access Audit Platform e una piattaforma interna per governare gli accessi al NAS Synology in modo verificabile, leggibile e compatibile con processi di audit amministrativo.

## 2. Problema

Lo scenario attuale presenta:

- assegnazioni di permessi poco trasparenti
- ereditarieta e deny difficili da ricostruire
- assenza di uno storico di review organizzativa
- reporting frammentato e non standardizzato

## 3. Obiettivi MVP

- acquisire utenti, gruppi, share e ACL dal NAS
- calcolare i permessi effettivi per utente e cartella
- mostrare dashboard e viste di consultazione
- consentire ai reviewer di validare gli accessi
- esportare dati di audit in formati standard

## 4. Non Obiettivi MVP

- modifica automatica dei permessi NAS
- provisioning utenti o gruppi
- integrazione AD/LDAP nella prima release
- sincronizzazione continua near real-time

## 5. Stakeholder

- amministratori IT
- responsabili di settore
- auditor interni
- governance e direzione operativa

## 6. Requisiti Funzionali

### 6.1 Ingestione NAS

- connessione SSH configurabile
- lettura di utenti, gruppi, membership e share
- acquisizione ACL con persistenza raw

### 6.2 Audit e Consultazione

- vista utenti
- vista cartelle condivise
- vista permessi effettivi
- storico snapshot

### 6.3 Workflow Review

- identificazione reviewer
- decisioni di conferma o revoca
- note e tracciamento temporale

### 6.4 Export

- esportazione CSV
- predisposizione XLSX in milestone successive

## 7. Requisiti Non Funzionali

- deployment containerizzato
- separazione chiara frontend/backend/database
- configurazione tramite environment variables
- naming coerente e documentazione leggibile

## 8. KPI Iniziali

- tempo di bootstrap ambiente inferiore a 15 minuti
- endpoint applicativi monitorabili
- workflow locale ripetibile da repository pulito

## 9. Roadmap Sintetica

1. bootstrap repository
2. fondazioni backend e frontend
3. schema dati e sync NAS
4. permission engine
5. review workflow e reporting
