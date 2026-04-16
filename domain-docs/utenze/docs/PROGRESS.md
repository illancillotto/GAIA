# Progress

## Stato Modulo

- milestone corrente: `Milestone 8 — Search, Export e Correlazioni`
- stato: `completed`

## Completato

- aggiunto flag `module_anagrafica` al modello `ApplicationUser`
- aggiornati `enabled_modules`, schemi auth/users, repository e bootstrap admin
- aggiunte section key `anagrafica.*` al bootstrap sezioni
- registrato il router modulo in `backend/app/api/router.py`
- introdotta surface minima backend `GET /anagrafica`
- aggiunta pagina frontend `frontend/src/app/anagrafica/page.tsx`
- aggiornata la navigazione globale: home, platform sidebar, module sidebar
- aggiornata la UI di amministrazione utenti GAIA per assegnare il modulo
- aggiornati i test backend principali toccati dalla modifica
- introdotti i modelli ORM `ana_*` del dominio Anagrafica
- aggiunta la migration `20260327_0018_anagrafica_mvp_backend.py`
- registrati i modelli Anagrafica nel bootstrap metadata del backend
- implementati parser cartelle NAS e classificatore documenti pattern-based
- aggiunti test dedicati per modelli, migration, parser e classificazione
- aggiunto connettore preview import NAS riusando il canale SSH/config condiviso del backend
- introdotto endpoint `POST /anagrafica/import/preview` con payload e warning/errori strutturati
- gestita preview read-only per lettera con rilevamento sottocartelle e file non PDF
- aggiunti test service/API con fake connector NAS senza dipendenza da host reale
- introdotto `POST /anagrafica/import/run` con persistenza soggetti, documenti, job e audit log
- implementata idempotenza di import su `nas_folder_path` e `nas_path`
- aggiunti endpoint minimi `GET /anagrafica/import/jobs` e `GET /anagrafica/import/jobs/{id}`
- aggiunti test service/API su re-import senza duplicati e tracking job
- introdotti endpoint CRUD backend per soggetti e documenti
- introdotte lista soggetti con paginazione, filtri e ricerca testuale iniziale
- introdotti endpoint statistiche aggregate e ricerca unificata del dominio
- estesi i test API per create/read/update/deactivate, document patch/delete, search e stats
- frontend Anagrafica collegato alle API reali del backend tramite `frontend/src/lib/api.ts`
- introdotte dashboard modulo, lista soggetti, dettaglio soggetto e wizard import
- aggiornata la navigazione modulo con voci dedicate `Dashboard`, `Soggetti`, `Import archivio`
- aggiornati i tipi frontend per stats, soggetti, documenti, preview import e job
- verifica TypeScript frontend completata con `tsc --noEmit`
- introdotto export backend/frontend in formato CSV e XLSX con riuso dei filtri correnti
- rafforzata la ricerca server-side per token multipli e match anche sui documenti associati
- introdotta correlazione read-only con Catasto tramite `codice_fiscale` nella scheda soggetto
- estesi i test API backend per export e correlazioni Catasto
- eseguito hardening esteso della piattaforma sui moduli collegati
- corretto `network` per compatibilità schema/model su `hostname_source`
- riallineato il bridge `sync` per mantenere compatibile il punto di monkeypatch dei test
- introdotto staging Bonifica Oristanese `bonifica_user_staging` per i consorziati
- aggiunto sync backend `sync_white_consorziati()` con match su `tax` verso `ana_subjects`
- aggiunti endpoint backend `/utenze/bonifica-staging` per lista, dettaglio, approve, reject e bulk-approve
- preservato lo stato `rejected` sui re-sync Bonifica per evitare riaperture automatiche
- rinominata la UX staging da `approva` a `importa in anagrafica` per rendere esplicito il passaggio verso `ana_subjects`
- tracciata l'origine WhiteCompany sui soggetti importati con `ana_subjects.source_system=whitecompany` e `ana_subjects.source_external_id=<wc_id>`

## Verifiche Eseguite

- `npx --prefix /home/cbo/CursorProjects/GAIA/frontend tsc --noEmit -p /home/cbo/CursorProjects/GAIA/frontend/tsconfig.json` ✅
- `python -m compileall /home/cbo/CursorProjects/GAIA/backend/app/modules/anagrafica ...` ✅
- `PYTHONPATH=/home/cbo/CursorProjects/GAIA/backend /home/cbo/CursorProjects/GAIA/.venv/bin/pytest /home/cbo/CursorProjects/GAIA/backend/tests/test_anagrafica_*.py -q` ✅ (`28 passed`)
- `PYTHONPATH=/home/cbo/CursorProjects/GAIA/backend /home/cbo/CursorProjects/GAIA/.venv/bin/pytest ... test_auth.py test_permissions_api.py test_user_management.py test_section_permissions.py test_catasto_api.py test_network_api.py test_sync_api.py test_anagrafica_*.py -q` ✅ (`67 passed`, `1 warning`)
- creato virtualenv locale `.venv` per eseguire test backend senza toccare il Python di sistema
- corretto il service di import NAS:
  - quoting stabile dei path nei comandi `find`
  - separazione tra warning tecnici e casi che richiedono davvero `requires_review`
- `next build` non eseguibile in modo affidabile nel workspace corrente: `.next/` posseduta da `root`

## Prossimo Step

- backend MVP e frontend operativo del modulo Anagrafica completati fino alla milestone 8
- hardening backend del dominio completato sui test dedicati
- prossimo passo utile: test integrati più ampi, prova NAS reale e rifinitura UX sui flussi operativi
