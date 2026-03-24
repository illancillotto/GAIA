# Prompt Codex

> Documento storico del modulo Accessi. Il frontend condiviso della piattaforma ora vive in `frontend/`.

## 1. Scopo

Questa base documenta le convenzioni da mantenere durante lo sviluppo assistito per il progetto NAS Access Audit Platform.

## 2. Obiettivi per le Iterazioni Future

- preservare struttura modulare backend e frontend
- evitare hardcode di credenziali o endpoint sensibili
- preferire modifiche incrementali con test mirati
- mantenere naming enterprise coerente

## 3. Regole di Implementazione

- backend: nuove feature dentro moduli dedicati in `modules/accessi/backend/app`
- frontend: route e componenti in `frontend/src`
- devops: compose e Dockerfile come fonte principale di esecuzione
- docs: aggiornare sempre i file in `modules/accessi/docs/` quando cambia il perimetro

## 4. Prompt Operativo Consigliato

```text
Lavora all'interno del repository NAS Access Audit Platform mantenendo naming coerente,
boilerplate minimo, modularita chiara e documentazione aggiornata. Ogni nuova feature
deve includere impatto su backend, frontend, devops e docs solo se realmente necessario.
```

## 5. Checklist per Nuove Feature

- endpoint e schema dati identificati
- route frontend e stato UX chiariti
- variabili ambiente documentate
- aggiornamento documentazione effettuato
