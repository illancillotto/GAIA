# GAIA GIS Platform Milestones

> Data: 2026-07-14.
> Documento operativo per pianificare e verificare il completamento incrementale
> della piattaforma GIS.

## M0 - Fondazione Backend

Stato: completato.

Deliverable:

- modulo `backend/app/modules/gis`;
- migration tabelle GIS;
- router `/gis`;
- catalogo layer;
- permessi layer;
- annotazioni;
- change request;
- export metadata;
- audit log;
- bootstrap Catasto PostGIS/Martin read-only.

Exit criteria:

- `/gis/layers` disponibile;
- Catasto registrato come workspace, senza sostituire `/catasto/gis`;
- default viewer read-only;
- coverage 100% sul perimetro GIS.

## M1 - Catalogo Operativo

Stato: completato.

Obiettivo:

- rendere il catalogo ispezionabile da UI e amministrabile in modo limitato.

Deliverable:

- filtri backend catalogo;
- update metadata admin-only;
- disattivazione/riattivazione layer;
- pagina frontend read-only catalogo GIS;
- link contestuale verso workspace dominio, ad esempio `/catasto/gis`.

Implementato:

- `GET /gis/layers` filtra per `workspace`, `domain_module`, `source_type`, `official_source`, `is_active`;
- `PATCH /gis/layers/{layer_id}/metadata` aggiorna solo metadata descrittivi e scrive audit;
- `POST /gis/layers/{layer_id}/activate` e `/deactivate` governano la visibilita catalogo;
- `/gis/catalogo` espone il catalogo read-only in frontend;
- `/catasto/gis` resta workspace operativo Catasto separato.

Exit criteria:

- utenti vedono layer autorizzati e metadata QGIS/PostGIS/Martin;
- admin puo aggiornare descrizioni/metadata non critici;
- nessuna modifica alle geometrie ufficiali.
- viewer vede solo layer attivi e autorizzati;
- admin puo filtrare e recuperare nel catalogo anche layer inattivi.

## M2 - Permessi Layer Completi

Stato: pianificato.

Obiettivo:

- rendere gestibile l'accesso per ruolo e utente.

Deliverable:

- revoke/delete permission;
- validazione ruoli;
- policy di precedenza role/user;
- audit completo grant/update/revoke;
- UI admin permessi.

Exit criteria:

- permessi verificabili da API e UI;
- viewer non puo annotare/editare;
- editor non puo approvare;
- approver non puo gestire permessi salvo `admin`.

## M3 - Annotazioni Governate

Stato: pianificato.

Obiettivo:

- separare note/segnalazioni dal dato ufficiale.

Deliverable:

- lifecycle annotazioni;
- update/close/reject;
- query per status/feature/layer;
- allegati come riferimenti metadata;
- UI note per layer/feature.

Exit criteria:

- nessuna nota scritta negli shapefile;
- audit per ogni cambio stato;
- annotator puo creare note, viewer solo leggere.

## M4 - Change Request Workflow

Stato: pianificato.

Obiettivo:

- introdurre draft editing prima di aggiornare layer ufficiali.

Deliverable:

- stati estesi change request;
- reject/request changes;
- diff leggibile geometry/attribute;
- validazioni pluggable per dominio;
- apply no-op sicuro per layer Catasto finche non esiste policy dominio.

Exit criteria:

- editor propone;
- approver valida o respinge;
- nessun apply automatico su Catasto senza accordo dominio.

## M5 - Export NAS Reale

Stato: pianificato.

Obiettivo:

- produrre shapefile versionati da PostGIS verso NAS.

Deliverable:

- job export;
- zip shapefile;
- manifest JSON;
- checksum;
- pubblicazione atomica su NAS;
- stato export e audit.

Exit criteria:

- export ripetibile e versionato;
- path NAS e checksum salvati;
- NAS non diventa sorgente operativa.

## M6 - Governance QGIS Desktop

Stato: pianificato.

Obiettivo:

- standardizzare l'uso quotidiano di QGIS.

Deliverable:

- ruoli DB read-only;
- eventuali profili edit controllati;
- runbook QGIS;
- convenzioni layer/workspace;
- istruzioni per connessione PostGIS.

Exit criteria:

- QGIS usa PostGIS o servizi OGC;
- shapefile NAS non vengono editati come dato vivo;
- credenziali e privilegi sono documentati.

## M7 - Decisione OGC

Stato: futuro.

Obiettivo:

- scegliere se introdurre QGIS Server o GeoServer.

Deliverable:

- POC QGIS Server;
- POC GeoServer;
- decision record;
- piano sicurezza/proxy/auth;
- piano rollout o decisione di non introdurre OGC server.

Exit criteria:

- scelta motivata;
- costi operativi e rischi documentati;
- nessun server OGC introdotto senza decisione.

## M8 - Integrazione Multi-Dominio

Stato: futuro.

Obiettivo:

- estendere il catalogo oltre Catasto.

Deliverable:

- onboarding layer per altri domini;
- workspace e naming standard;
- validazioni dominio-specifiche;
- dashboard stato catalogo.

Exit criteria:

- almeno un dominio non Catasto registrato;
- confini dominio/GIS rispettati;
- permessi e audit coerenti.
