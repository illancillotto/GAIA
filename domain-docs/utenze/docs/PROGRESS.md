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
- aggiornata la navigazione modulo con voci `Dashboard`, `Import dati` (registro Soggetti raggiungibile dalla pagina Import · tab o deeplink `#utenze-soggetti`, creazione utente dalla dashboard)
- pagina `/utenze/import`: layout a tre sezioni (`Anagrafica Excel` · `Archivio NAS` · `Soggetti`); la sezione Soggetti include registro ricercabile, import CSV fisiche, export e creazione utente tramite modal condivisa con la dashboard; la route storica `/utenze/subjects` reindirizza al centro import; dentro Archivio NAS sono inclusi preview/snapshot/aggiornamento massivo/reset, storico REGISTRY con azioni e pannello «Job e storico NAS» (dettaglio job + lista snapshot); hero KPI e pannelli `rounded-[28px]` come workspace elaborazioni
- modulo Ruolo / dettaglio avviso: link soggetto GAIA aggiornati a `/utenze/{subject_id}` (pagina dettaglio soggetto)
- creazione soggetto (`POST /utenze/subjects`): `nas_folder_path` calcolato automaticamente come `{UTENZE_NAS_ARCHIVE_ROOT|ANAGRAFICA_NAS_ARCHIVE_ROOT}/{lettera}/{source_name_raw}` (modulo validazione); campo inviato dal client ignorato; modal senza input manuale; logica condivisa in `backend/app/modules/utenze/services/nas_path_service.py`
- interrogazione ANPR in creazione PF: `POST /utenze/anpr/preview-lookup` (`{ codice_fiscale }`) esegue C030 (+ C004 se id acquisito) senza soggetto in DB; accesso solo `reviewer|admin|super_admin`; stessa gestione errori configurazione PDND della sync soggetto; la modale nuovo utente espone solo «Recupera dati» e non chiede `anpr_id` manuale
- modale dashboard «Nuovo utente»: dialog viewport-safe (`max-h`/`dvh`, overlay scrollabile, contenuto a griglia con area centrale `minmax(0,1fr)` e scroll interno così intestazione/azioni restano raggiungibili)
- `NavItem`: supporto `href` con hash `#...` per stato attivo e prop opzionale `inactiveWhenHash` (pathname match ma hash diverso ⇒ non evidenziata)
- `POST /utenze/import/run-from-subjects`: creazione job REGISTRY in stato `pending` e presa in carico dal worker esterno `modules/elaborazioni/worker/worker.py`; il job non dipende piu dalla sessione web di GAIA e, in caso di restart del worker, le righe `processing` vengono riportate a `pending` per il recupero automatico. `POST /utenze/import/jobs/{id}/resume-registry` rimette in coda i soggetti mancanti sul worker; progresso osservabile via `GET /utenze/import/jobs/{id}`. Il frontend mantiene banner/polling anche in stato `pending`; `_refresh_import_job_status` persiste `created_documents` / `updated_documents` aggregati in `log_json`; restano disponibili `POST /utenze/import/jobs/{id}/abort-registry` e `DELETE /utenze/import/jobs/{id}` (solo REGISTRY, owner o super_admin)
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
- introdotta la tabella `ana_person_snapshots` per la storicizzazione interrogabile dei dati persona
- il dettaglio soggetto ora espone `person_snapshots` oltre ad audit log e documenti
- gli update manuali e gli import CSV/XLSX/NAS salvano uno snapshot del profilo persona precedente quando cambiano i dati
- introdotta la persistenza `ana_payment_notices` per gli avvisi di pagamento recuperati da Capacitas `inCASS`
- aggiunto endpoint soggetto `GET /utenze/subjects/{subject_id}/payment-notices` per mostrare avvisi, stati, dettaglio informativo e PDF associati
- aggiunto workflow `Elaborazioni > Capacitas > inCASS avvisi` con job backend `capacitas_incass_sync_jobs`, recovery worker e monitor frontend dedicato
- il dettaglio soggetto `/utenze/{id}` e la modale soggetto ora mostrano la sezione `inCASS` con residuo, stato avviso, link dettaglio e PDF disponibili
- esteso il workflow `inCASS avvisi` con rubrica recapiti e registro spedizioni: i job possono salvare email/PEC nell'anagrafica, allegare le spedizioni a `ana_payment_notices.raw_detail_json.mailing_list` e scaricare ricevute PEC ObjMan in `ana_documents`/NAS
- validazione live Capacitas inCASS del 2026-07-22 completata sui CF `MDDMGV77A51G113Q` e `FLCBTS63D10D665W`: 38 avvisi sincronizzati, 3 recapiti, 9 spedizioni, 2 ricevute PEC ObjMan scaricate come documenti locali. Il portale richiede paginazione Kendo esplicita (`take/skip/page/pageSize`) sulle griglie rubrica/spedizioni e apertura ObjMan con OTP prima di `get-metadata`; la logica ora gestisce questi vincoli, conserva la PEC come recapito principale persona quando presente e collega i documenti ricevuta solo all'avviso della spedizione corrispondente. Il salvataggio NAS resta condizionato a `ana_subjects.nas_folder_path` valorizzato.
- il dettaglio soggetto Utenze apre in anteprima inline anche i file `.eml` delle ricevute PEC ObjMan salvate in `ana_documents`, mantenendo il download dalla stessa modale.
- la sezione `Documenti associati` del dettaglio soggetto espone una classificazione di lettura derivata, senza modificare il `doc_type` salvato: i documenti vengono ordinati e raggruppati per priorita operativa (`Azioni legali`, `Notifiche e relate`, `Prove invio e PEC`, `Pagamenti e debito`, `Domande utenza irrigua`, `Visure e catasto`, `Pratiche interne`, `Altro da classificare`) usando tipo salvato, filename, estensione e note.
- il sync documentale da archivio NAS soggetti opera in modalita `nas_link`: registra metadati e path NAS in `ana_documents` senza copiare preventivamente i file in `/data/anagrafica/documents`; il recupero locale resta on-demand al download/preview.
- dettaglio soggetto Utenze: la tab `Avvisi di pagamento` mostra ora lo stato pagamento derivato per ogni avviso (`Pagato`, `Parziale`, `Non pagato`) e il riepilogo in scheda soggetto espone una card `Stato pagamenti` accanto al percorso NAS. Corretto il parsing degli importi inCASS con punto decimale e code decimali lunghe, evitando residui totali gonfiati.

## Verifiche Eseguite

- `npx --prefix /home/cbo/CursorProjects/GAIA/frontend tsc --noEmit -p /home/cbo/CursorProjects/GAIA/frontend/tsconfig.json` ✅
- `python -m compileall /home/cbo/CursorProjects/GAIA/backend/app/modules/anagrafica ...` ✅
- `PYTHONPATH=/home/cbo/CursorProjects/GAIA/backend /home/cbo/CursorProjects/GAIA/.venv/bin/pytest /home/cbo/CursorProjects/GAIA/backend/tests/test_anagrafica_*.py -q` ✅ (`28 passed`)
- `PYTHONPATH=/home/cbo/CursorProjects/GAIA/backend /home/cbo/CursorProjects/GAIA/.venv/bin/pytest ... test_auth.py test_permissions_api.py test_user_management.py test_section_permissions.py test_catasto_api.py test_network_api.py test_sync_api.py test_anagrafica_*.py -q` ✅ (`67 passed`, `1 warning`)
- `VITEST_COVERAGE_INCLUDE=src/components/utenze/utenze-payment-notices-section.tsx npm run test:coverage -- --run tests/unit/utenze-payment-notices-section.test.tsx` ✅ (`100%` statements/branches/functions/lines)
- `VITEST_COVERAGE_INCLUDE=src/lib/utenze-payment-notice-detail.ts npm run test:coverage -- --run tests/unit/utenze-payment-notice-detail.test.ts` ✅ (`100%` statements/branches/functions/lines)
- `VITEST_COVERAGE_INCLUDE=src/lib/utenze-payment-notices-summary.ts npm run test:coverage -- --run tests/unit/utenze-payment-notices-summary.test.ts` ✅ (`100%` statements/branches/functions/lines)
- `npm run test:unit -- tests/unit/utenze-payment-notices-summary.test.ts tests/unit/utenze-payment-notice-detail.test.ts tests/unit/utenze-payment-notices-section.test.tsx tests/unit/ruolo-tributi-page.test.tsx tests/unit/ruolo-tributi-detail-page.test.tsx` ✅ (`31 passed`)
- `npm run test:unit -- tests/unit/document-preview.test.ts` ✅ (`3 passed`)
- `VITEST_COVERAGE_INCLUDE=src/lib/document-preview.ts npm run test:coverage -- --run tests/unit/document-preview.test.ts` ✅ (`100%` statements/branches/functions/lines)
- `npm run typecheck` ✅
- `make graphify-frontend`, `make graphify-utenze-code`, `make graphify-utenze-docs` ✅
- creato virtualenv locale `.venv` per eseguire test backend senza toccare il Python di sistema
- corretto il service di import NAS:
  - quoting stabile dei path nei comandi `find`
  - separazione tra warning tecnici e casi che richiedono davvero `requires_review`
- `next build` non eseguibile in modo affidabile nel workspace corrente: `.next/` posseduta da `root`

## Prossimo Step

- backend MVP e frontend operativo del modulo Anagrafica completati fino alla milestone 8
- hardening backend del dominio completato sui test dedicati
- prossimo passo utile: test integrati più ampi, prova NAS reale e rifinitura UX sui flussi operativi
