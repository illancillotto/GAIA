# Audit del checkout — GAIA Communications

## Aggiornamento editor — 12 novembre 2026

`rich_template.py` valida il formato, sostituisce i soli campi testuali ed esegue
l’escaping HTML. Il trasporto costruisce alternative MIME e immagine CID senza
consultare un template modificabile. La bozza conserva il corpo risolto, che
partecipa al digest di approvazione già esistente. Schemi Pydantic validano
creazione template, creazione messaggio e modifica bozza. Nessuna migrazione.
File, verifiche e limiti: [Template grafici e verifica finale](RICH_TEMPLATES_2026-11-12.md). L’audit successivo è storico.


Audit iniziato il 2026-11-03 su `feature/avvisi-solleciti-2021`,
`66b72e517fd2c9513d509001493dc5f77f4493b8`. Nessun accesso al CED,
caselle reali o database di produzione. Le modifiche preesistenti a config,
gitignore e documentazione Elaborazioni/Presenze restano escluse dalla change.

## Componenti verificati

| Responsabilità | Implementazione effettivamente esaminata | Impatto |
| --- | --- | --- |
| Registrazione API | `backend/app/api/router.py`, `app.main:app` | Router trasversale separato; nessuna precedenza Ruolo modificata |
| Identità e RBAC | `app/api/deps.py`: `require_active_user`, `require_module`, `require_section`, `require_admin_user`; `ApplicationUser` | Lettura e gestione Tributi distinte dall'amministrazione dei trasporti |
| ORM/migrazioni | `app/core/database.py`: `Base`, `SessionLocal`; `app/db/base.py`; Alembic `env.py`; head `20261103_0900` | Migrazione successiva, mai applicata automaticamente dal worker |
| Solleciti definitivi | `RuoloTributiReminderBatchItem`, `RuoloTributiNoticeNumber`, `RuoloTributiReminderBatch` in `ruolo/models.py` | UUID della riga sorgente distinto da UUID delle posizioni e numero stampato |
| Identità canonica | `services/tributi_notice_registry.py`: `build_notice_identity_key`, `reserve_notice_number`; `notice_generation._publish` | Usare il documento Registro `gaia_batch_item`/source_key e numero riservato, non CF/anno come chiave |
| Archivio Registro | `notice_register_models.py`: `NoticeDocument`, `NoticePosition`, `NoticeAttempt`, `NoticeEvidence`, `NoticeNotification`, `NoticeAudit` | Evidenze aggiuntive con namespace Communications; originali inCASS immutati |
| Ammissibilità | `services/notice_eligibility.py`: `eligibility`, `_accounting_reasons`, `_history_reasons`; `notice_document_eligibility.document_eligibility` | Saldo, STEP, storico e notifiche incerti bloccano; una generazione non autorizza un invio |
| Dati contabili correnti | `tributi_repositories.get_tributi_avviso` | Rileggere pagamenti, regola corrente, gestione e spedizioni; nessuna nuova formula |
| Prove pregresse | `tributi_notification_evidence.py`: `has_documented_pec_delivery`, `has_documented_mail_receipt` | Accettazione PEC e sola spedizione non equivalgono a consegna |
| Rigenerazione | `services/notice_pdf_regeneration.py`: `regenerate_batch_item`, `ensure_batch_item_document`, `_audit` | Può sovrascrivere sorgenti NAS; incrementa la versione Registro. Il worker Communications non deve chiamarla |
| Lettura file | `poste_dispatch.read_batch_document`, `tributi_repositories.read_remote_reminder_document` | La prima può rigenerare: inadatta al ricontrollo del worker. Lettura diretta della sorgente già definitiva, fail-closed se manca |
| Outbox Poste | `poste_dispatch.create_lot`, `_new_item`, `enqueue_job`; `PosteDispatchItem.active_key/active_source_key` | Unique solo fra lotti Poste; serve coordinamento DB fra canali senza cambiare il workflow manuale INVIA |
| Worker esistente | `modules/elaborazioni/worker/posta_online_queue.py`: `PosteQueue`, lease account; `posta_online_dispatch_runner.py` | Worker browser specializzato. Riutilizzare pattern SQL, non il suo lifecycle o la coda portal |
| Revisione concorrenza | `services/notice_revision.py`: `read_revision`, `lock_revision`; `NoticeGenerationRevision` | Fence esistente PostgreSQL destinato a commit brevi; non tenerlo durante SMTP |
| Credenziali | `core/config.py`: `CREDENTIAL_MASTER_KEY`; servizio globale `services/email.py` | SMTP globale per email applicative, non multi-account e senza outbox. Non riutilizzarne invio HTTP o configurazione globale |
| Recapiti | `utenze/models.py`: `AnagraficaPerson.email`, `AnagraficaCompany.email_pec` | Nessuna PEC generalizzata sulle persone né email ordinaria sulle aziende; niente inferenze da stringhe contenenti “pec” |
| UI operativa | `components/ruolo/solleciti/workspace.tsx`: `SollecitiAccess`, `SollecitiWorkspace`, `GeneratedPanel` | Preservare lotti, rigenerazione, selezione e Posta Online; aggiungere sottoroute nella medesima navigazione |
| Visualizzatore | `solleciti/document-access.tsx`: `useDocumentBlob`, `PdfFrame` | Blob autenticato ma iframe senza prova del rendering multipagina: introdurre renderer PDF verificabile per il compositore |
| Client e stile | `lib/api.ts`, `lib/ruolo-poste-dispatch-api.ts`, `use-session-bootstrap.ts`; classi `btn-*`, pannelli Tailwind | Riutilizzo sessione, client e design; nessun secondo design system |
| Test | `backend/tests/ruolo/poste_dispatch_fixtures.py`, `test_notice_register.py`, `test_poste_dispatch_service.py`; `frontend/vitest.config.ts` | SQLite utile per contratti; lock, leasing e race richiedono PostgreSQL isolato. Coverage full-file richiesta al 100% |

## Fonti documentali confrontate

Esaminate le sezioni operative e i riferimenti al codice di
`POSTE_INVIO_SOLLECITI_2026-10-28.md` (aggiornamenti account 03/11),
`RUOLO_RIGENERAZIONE_PDF_2026-10-29.md` (aggiornamenti 30/10),
`ANTEPRIMA_EXPORT_SOLLECITI.md`, `TRIBUTI_RULE_BLOCKS_2026-10-19.md`,
`VERIFICA_FINALE_AVVISI_2021_2026-10-21.md`,
`REGISTRO_AVVISI_IMPLEMENTAZIONE.md`. Le dichiarazioni di collaudo/rilascio
storiche non costituiscono verifiche di questa change. Graphify interrogato con
`make graphify-ruolo-query Q='solleciti definitivi PDF pagamenti notifiche poste dispatch registro avvisi'`;
simboli importanti verificati direttamente nei sorgenti.

## Decisioni e rischi di regressione

1. Solo righe definitive PDF, esattamente annualità 2021, registrate e con
   identità coerente. Un documento misto non passa per il solo contenere 2021.
2. Snapshot binari nel DB protetto, coerenti con il pattern dei draft esistenti:
   backup transazionale, hash, limiti di byte/pagine, nessun URL pubblico.
3. Ricontrollo di versione Registro, payload, recapiti, dati contabili e byte
   sorgente prima del confine `sending`. Dopo tale confine una crash recovery
   produce `uncertain`, mai un retry automatico SMTP.
4. Prenotazione globale al momento dell'approvazione e coordinamento DB con
   Poste. La presenza di bozze portale esterne a GAIA resta una dipendenza
   operativa: non può essere esclusa leggendo soltanto il DB.
5. Comunicazioni ordinarie solo cortesia, senza mutare `NoticeNotification`.
   Ricevute PEC archiviate e collegate come evidenze tecniche; perfezionamento
   giuridico sempre nel workflow Registro approvato dall'ufficio.
6. Parsing PEC separato dalla verifica CMS e dalla correlazione. Senza trust
   store del gestore la ricevuta resta non verificata e non prova consegna.
7. Password/token soltanto in file secret esterni montati al worker; nelle
   tabelle solo riferimenti. Nessuna credenziale reale necessaria ai test.
8. Default trasporto chiuso, controlli di pausa globali e per account.
   Configurare un account non autorizza un collaudo su casella reale.

## Limite dell'audit

Nessun inventario di avvisi di produzione è stato eseguito. L'audit identifica
le condizioni verificabili dal software, non certifica che un particolare
sollecito 2021 sia oggi inviabile o che un recapito abbia valore legale.

## Riscontro finale

Registrazione effettiva dei due router e degli undici modelli verificata da
test di integrazione import. La migrazione è confrontata con metadata ORM
su PostgreSQL isolato; mutex, claim e prenotazione cross-channel verificati
anche con thread concorrenti. Il nuovo adapter usa i recapiti canonici
già presenti o l'inserimento esplicito con dichiarazione operatore; non
introduce mapping per nome. Frontend reale renderizza tutte le pagine PDF.js
prima della conferma. Test e limiti sono in TEST_REPORT.md.

La lettura remota PDF riutilizza nas_connector.get_nas_client, configurato da
NAS_HOST/NAS_PORT/NAS_USERNAME/NAS_PRIVATE_KEY_PATH. L'overlay consente questi
riferimenti senza incorporarvi segreti; permessi/key NAS readonly e accesso
effettivo CED restano da collaudare. Nessun nuovo comportamento di scrittura NAS.

## Controllo dei privilegi prima del rilascio — 2026-11-04

Il controllo dell'approvatore leggeva l'intero modello `ApplicationUser`,
che comprende anche `password_hash`, username e recapiti. L'analisi di
`permission_resolver.can_access_section` e `ApplicationUser.enabled_modules`
conferma che per questa responsabilità servono soltanto ID, ruolo, stato attivo
e flag Ruolo. `communications.worker._authorize_operator` usa ora una query
limitata a queste colonne con caricamenti impliciti vietati; i grant sono
coerenti con la query. Revoca, utente assente/inattivo e semantica dei super
amministratori mantengono il comportamento precedente. Nessuna modifica alle
API, alle formule, agli stati o alle transazioni del dispatch.
