# Catasto Phase Progress

- Data: 2026-04-22
- Scope: verifica stato Fase 1 e avanzamento autonomo verso Fase 5

## Stato sintetico

- Fase 1: completata e verificata su backend, frontend, Postgres/PostGIS e import Capacitas/shapefile
- Fase 2: hardening tecnico gia avanzato con test backend, integrazione shapefile e smoke frontend
- Fase 3: audit/import, reporting batch e permessi workflow anomalie gia presenti
- Fase 4: chiusa in questa tranche
- Fase 5: chiusa con E2E browser dedicato sulla ricerca anagrafica

## Tranche 2026-04-22

### Obiettivo

Portare a stato verde e versionare il blocco `ricerca-anagrafica` del modulo `catasto`, gia presente nel working tree ma non ancora chiuso con test e documentazione.

### Deliverable previsti

- router backend `catasto/anagrafica`
- pagina frontend `/catasto/ricerca-anagrafica`
- componenti frontend dedicati
- client API e tipi TypeScript
- test backend di ricerca singola e massiva
- smoke/frontend coverage minima
- aggiornamento PRD Catasto e indice docs

### Criterio di chiusura

- test backend Catasto verdi
- smoke frontend verdi
- documentazione Catasto aggiornata
- commit separato della tranche Fase 4

### Esito

- backend Catasto: `26 passed`
- frontend smoke: `15 passed`
- documentazione Catasto aggiornata con API e pagina `ricerca-anagrafica`
- tranche pronta per commit separato

## Backlog residuo verso Fase 5

- osservabilita piu ricca per workflow anagrafica/import
- eventuale E2E browser dedicato alla ricerca anagrafica
- affinamento UX stati vuoti/errori/multipli
- eventuale export/reportistica massiva piu strutturata

## Chiusura Fase 5

- E2E Playwright dedicato aggiunto per:
  - ricerca anagrafica singola
  - ricerca anagrafica massiva con export
- test backend Catasto ancora verdi
- smoke frontend ancora verdi
- avanzamento autonomo completato fino a Fase 5 sul perimetro Catasto attualmente in repository
