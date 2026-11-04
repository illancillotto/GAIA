# Verifica finale del ciclo Communications — 2026-11-03

## Perimetro e stato

Revisione dei commit 40b324ac, 599e1ccf e a6274cac rispetto a 9676aaa7:
81 file, backend/API/ORM, migrazione, worker, frontend, dipendenza PDF.js,
configurazioni di rilascio e documentazione. Le modifiche Poste precedenti e
il working tree estraneo sono distinti dal ciclo Communications.

Questa chiusura aggiunge solo due test di integrazione, documentazione e la
riproduzione della baseline sul runtime già committato. Nessuna nuova feature,
refactoring applicativo, invio reale, migrazione produzione o deployment.
Alla chiusura del 3 novembre l'istruzione «quando hai finito non deployare»
restava vincolante. Il successivo rilascio autorizzato dall'utente il 4 novembre
è distinto da questa verifica e descritto in
[DEPLOYMENT_REPORT_2026-11-04](DEPLOYMENT_REPORT_2026-11-04.md);
non modifica il risultato del gate qui documentato.

Le verifiche Communications in isolamento sono superate; il gate complessivo
resta FAIL per le prove di regressione generali non interamente verificabili
e per gli errori di setup PG descritti sotto. La verifica non autorizza produzione.

## Architettura e dipendenze verificate

- Backend nel monolite modulare: app/modules/communications; registrazioni in
  app/api/router.py e app/db/base.py. Ruolo conserva eleggibilità, identità,
  pagamenti e sorgente PDF attraverso ruolo_source.py. SMTP/IMAP ignorano le
  regole tributarie. Nessuna formula fiscale o evidenza inCASS modificata.
- Frontend operativo in app/ruolo/tributi/solleciti/{pec,email}; amministrazione
  trasversale in app/gaia/communications, componenti condivisi in
  components/communications. Sessione, RBAC, API client e stile GAIA riusati.
- Worker processo autonomo dello stesso pacchetto backend, senza nuovo broker:
  coda PostgreSQL, mutex account, claim SKIP LOCKED, lease/fencing e heartbeat.
  Il servizio SMTP applicativo preesistente resta distinto: non ha outbox,
  snapshot, account multipli o semantica certificata e non viene duplicato nel
  workflow HTTP di Communications.
- Migrazione 20261103_1200: undici tabelle, seed draft/in pausa, trigger di
  immutabilità, revisione e prenotazione incrociata con Poste. Snapshot BYTEA,
  MIME ed EML privati; il DB non è dichiarato conservazione a norma.
- Unica dipendenza applicativa aggiunta: pdfjs-dist5.4.624 con lockfile, worker
  locale e dipendenze canvas opzionali transitive. Nessuna nuova dipendenza
  Python; pypdf, SQLAlchemy, Alembic ed email-validator erano già disponibili.
  OpenSSL è una dipendenza operativa esplicita del verificatore CMS.

## Matrice funzionalità → comportamento → test

Percorsi backend abbreviati: API=test_outbox_api.py, F=test_faults.py,
T=test_transports_parser.py, W=test_worker_receipts.py, R=test_recovery.py,
PG=test_postgres.py, I=test_final_contracts.py, tutti in
backend/tests/communications. I nomi riportati sono test effettivi, con
parametrizzazioni per canali, errori e configurazioni. UI indica file sotto
frontend/tests/unit/communications. E2E=tests/e2e/communications.spec.ts.

| Funzionalità | Comportamento osservabile richiesto | Test pertinente |
| --- | --- | --- |
| Registrazione monolite | Router e modelli presenti senza sostituire route esistenti | API::test_application_registers_communications_without_changing_existing_routes; suite backend generale |
| RBAC operatore | Lettore non modifica; utente inattivo/senza modulo o permesso respinto | API::test_operator_mutations_require_real_rbac; test_all_writes_reject_viewer_and_no_module_reads; UI workspace::checks session, module and read permissions |
| Account e routing | Esplicito autorizzato, default modulo, default canale; assenza/disabilitazione bloccante | API::test_multiaccount_routing_admin_and_no_secret_exposure; test_duplicate_authorizations_and_account_change_block |
| Configurazione account | TLS/auth/host/header validati; credenziali mai in HTTP | T::test_account_schema_rejects_headers_and_invalid_configuration; API::test_multiaccount_routing_admin_and_no_secret_exposure; UI admin::creates, edits and versions accounts |
| Secret store | Solo file esterno bounded senza traversal/symlink | T::test_secret_store_only_uses_external_files |
| Template | Versioni nuove, seed draft, approvazione esplicita, niente interprete o variabili ignote | API::test_templates_are_versions_and_proposals_require_approval; R::test_source_render_and_draft_edges; UI admin::creates a fresh version and approves only draft templates |
| Identità Ruolo | UUID sorgente/Registro e numero definitivo coerenti; niente associazione per nome | F::test_source_identity_files_history_and_contacts; test_invalid_canonical_source_or_poste_reservation_blocks; test_linked_contacts_are_not_inferred_from_names |
| Annualità/eleggibilità | Solo2021/generated; pagamenti, storico/notifiche/STEP e prenotazioni impediscono invio | API::test_changed_source_is_blocked_before_dispatch; F::test_invalid_canonical_source_or_poste_reservation_blocks; test_direct_eligibility_get_is_not_an_authorization |
| Integrazione contabile reale | Default2021 STEP blocca; override sintetico esplicito GAIA consente review; pagamento persistito dopo review blocca dispatch e non crea job | I::test_real_accounting_payment_blocks_an_already_reviewed_dispatch |
| Elenco candidati | Query, lotto, contatti, stati, date, account e paginazione applicati sul server | F::test_filters_current_states_pagination_and_empty_results; UI workspace::uses server-side filters/pagination |
| PDF sorgente | Assente/corrotto/cifrato/vuoto/eccessivo respinto; errore NAS sanitizzato | T::test_pdf_limits_corrupt_encrypted_empty_and_multipage; F::test_unavailable_nas_pdf_is_a_sanitized_conflict; test_source_identity_files_history_and_contacts |
| Snapshot immutabile | Byte/hash/dimensione verificati; rigenerazione o metadati cambiati invalidano invio | F::test_snapshot_integrity_and_size_fail_closed; test_source_row_metadata_changes_invalidate_approval; API::test_changed_source_is_blocked_before_dispatch; PG::test_immutable_snapshots_and_append_only_audit |
| Viewer reale | Tutte le pagine, hash/byte, navigazione, zoom/fit, fullscreen, blob autenticato; rendering fallito impedisce conferma | UI api::checks SHA256, size, review proof and authentication; pdf-renderer::renders every page / rejects missing canvas; pdf-viewer::renders all pages before acknowledging review; quattro E2E |
| Revisione PDF | Attestazione stesso operatore/allegato/versione; lettore non attesta; risposte tardive ignorate | API::test_checklist_render_scope_and_stale_versions_are_enforced; UI pdf-viewer::read-only preview never attests / does not enable send after unmount |
| Allegati | Limiti10PDF/32 MiB/200 pagine e MIME; aggiunta invalida review | F::test_additional_multipage_attachment_invalidates_review; test_snapshot_integrity_and_size_fail_closed; UI composer::invalidates checks on edits |
| Checklist | Otto conferme, versione corrente e PDF integrale obbligatori anche via API | API::test_checklist_render_scope_and_stale_versions_are_enforced; UI composer::requires complete PDF rendering plus eight checks |
| Mutazioni bozza/account | Modifiche envelope invalidano autorizzazione e liberano solo prenotazione pre-invio | API::test_edits_invalidate_approval_and_free_snapshot; test_duplicate_authorizations_and_account_change_block |
| Accodamento | HTTP non invia; POST idempotente; replay non crea altro lavoro | API::test_complete_preview_approval_queue_and_replay; F::test_invalid_transitions_and_no_authorization; E2E |
| Annullamento | Solo prima di effetto irreversibile; failed sicuro revisionabile; uncertain non liberato | R::test_preflight_failure_can_be_cancelled_and_revised_without_smtp; test_cancel_never_releases_a_message_with_uncertain_transport_evidence |
| Migrazione PG | Schema ORM equivalente, seed sicuri, upgrade/downgrade/upgrade vuoto | PG::test_migration_schema_seed_and_roundtrip; test_migration_upgrade_downgrade_upgrade_empty |
| Migrazione DB test | SQLite roundtrip conserva tabelle parent e ricrea undici tabelle/seed draft | I::test_sqlite_migration_roundtrip_preserves_parents_and_seeds_only_drafts |
| Prenotazione Poste | Gara cross-channel lascia una sola prenotazione | PG::test_cross_channel_race_has_exactly_one_reservation; regressione worker Posta Online |
| Concorrenza worker | Mutex sessionale, due istanze, claim/fence e lease reali PG | PG::test_mutex_is_session_scoped_released_on_error_and_not_shared; test_two_worker_instances_cannot_claim_the_same_account_at_once; test_source_fence_and_job_claim_are_real_postgresql |
| Trasporto snapshot | MIME persistito; allegato byte-identico alla preview per PEC/email | W::test_worker_transports_exact_snapshot_and_no_legal_notification |
| Failure SMTP | Rifiuto esplicito distinto da timeout DATA; massimo tre retry sicuri | T::test_smtp_failure_boundary; test_explicit_smtp_negative_responses_are_known; W::test_outcomes_have_safe_retry_semantics; test_repeated_explicit_rejection_becomes_terminal |
| Crash/recovery | Dopo sending stato uncertain, tentativo/Registro coerenti, nessun reinvio | W::test_crash_after_boundary_is_uncertain_without_resending; R::test_unexpected_error_recovers_the_correct_boundary; test_recover_pending_cancelled_non_message_and_missing_control |
| Pause/rate/RBAC prima SMTP | Global/account/transport false, revoca approvatore e limite orario rispettati | R::test_prepare_rechecks_authority_pause_and_rate; W::test_tick_disabled_pauses_account_and_heartbeat_independent |
| Adapter TLS/auth | TLS implicito/STARTTLS con password/OAuth2; errori chiudono connessione | T::test_smtp_tls_auth_and_success_without_test_message; test_starttls_failure_closes_connection; test_imap_tls_readonly_and_peek_uidvalidity; test_imap_connection_failure_closes |
| IMAP | INBOX readonly/PEEK, UIDVALIDITY, originali e cursore coerenti; errori/size limitati, nessuna cancellazione | W::test_connection_test_and_reconciliation_are_queued_and_archived; T::test_imap_mailbox_failures_preserve_mailbox; test_imap_size_and_payload_bounds |
| PEC trust/parser | CMS sintetico firmato verificato realmente; CA/pin mancanti/errati, XML invalido/DTD e formati ignoti fail-closed | T::test_signed_pec_verifies_real_synthetic_cms; test_cms_errors_fail_closed; test_bad_pec_xml_has_no_delivery_effect; test_unclassified_pec_and_dsn_branches |
| PEC correlazione | Message-ID/account/recapito, fuori ordine, deduplica, nessuna alterazione inCASS/notifica legale | W::test_signed_receipts_correlate_out_of_order_deduplicate_and_preserve_legal_state; test_receipt_unverified_wrong_recipient_and_unknown_id_do_not_deliver |
| Email | Submitted non è consegna PEC; bounce/DSN solo evidenza tecnica | W::test_dsn_bounce_and_delivery_are_not_pec; test_worker_transports_exact_snapshot_and_no_legal_notification; UI composer::email courtesy warning |
| Lifecycle/health | SIGINT/SIGTERM cooperativi, marker assente/scaduto, heartbeat distinto dal provider | R::test_loop_handles_both_stop_signals_without_network; test_process_health_marker_missing_current_stale_and_cli; UI admin::distinguishes worker liveness, transport enablement and provider state |
| UI errori e audit | Errori visibili, permessi, storico, EML autenticato, cleanup delle risposte tardive | UI admin/workspace/composer/pdf-viewer: test error/load/unmount; API::test_missing_resources_invalid_headers_and_unknown_fields |
| Coesistenza Solleciti | Generati/Posta Online preservati; navigazione PEC/email accessibile | UI workspace::keeps generated/Posta Online tab actions and both channel routes accessible; notice-solleciti-page.test.tsx; regressioni backend/frontend/worker |
| Configurazione deployment | Compose risolubile senza avvio; grant riferiti a tabelle esistenti | API::test_worker_grants_refer_only_to_real_tables; docker compose config --quiet con valori sintetici |

## Test aggiunti e valore della prova

Test nuovi in test_final_contracts.py: roundtrip SQLite reale e interazione con
get_tributi_avviso reale, senza mock dei pagamenti/eleggibilità. Il primo copre
la compatibilità del database di test e due branch effettivamente mancanti
nella migrazione; il secondo chiude un confine prima simulato nei test API.
Nessun test o esclusione esistente rimosso; nessuna modifica runtime necessaria.

## Coverage finale

- Backend/API/ORM/migrazione:125 PASS,1639/1639 statement,336/336 branch,
  zero righe o branch mancanti, zero righe escluse,18 file nel report.
- Frontend:89 PASS,548/548 statement,355/355 branch,204/204 funzioni,
  378/378 righe,18 file; include workspace Solleciti legacy modificato.
- Tipi TypeScript puri e __init__.py di sola docstring non hanno istruzioni
  runtime; la loro verifica pertinente è type-check/import. Le esclusioni
  globali preesistenti non sono state allargate. File test e documenti non sono
  denominatore del runtime; Alembic è stato aggiunto esplicitamente alla misura.
- Verificato l'elenco dei file dei report contro il diff, oltre alla percentuale.

## Code quality e rischi architetturali

Scanner sul manifest runtime completo37 file/339 callable:0 error-level,51 warning. Massimo
cyclomatic 14 (Worker._prepare e useSolleciti), massimo cognitive 20 nel
workspace legacy; _positions19, _recipient_report17, Worker._prepare16.
I warning rappresentano debito visibile sotto la soglia error, non vengono
eliminati tramite wrapper, ignore o split metrici. Nessun refactoring avviato.

Controllo AST Python135 funzioni: nessun corpo identico di almeno8 statement.
È una ricerca di duplicazioni esatte, non una prova generale di equivalenza
semantica. Review mirata dei confini HTTP/outbox/domain/transport e dei hook UI:
nessun servizio concorrente con la stessa ownership o codice fittizio trovato.
Ruff/ESLint verificano import/variabili inutilizzati; copertura e chiamanti
verificati supportano la review dead-code senza pretendere una prova formale.

npm audit --omit=dev:0vulnerabilità note nel lockfile di produzione alla verifica.
Non è una prova generale di assenza di vulnerabilità. TypeScript passa tsc; non sono stati introdotti any o disabilitazioni lint.
Il backend segue lo stile dinamico SQLAlchemy/FastAPI esistente: non viene
presentato come verificato da un nuovo gate mypy, assente nel perimetro.
Errori di rete normalizzati, secret esterni, documenti autenticati/no-store,
CMS fail-closed e RBAC verificati da test. DSN non certificate restano
potenzialmente falsificabili e non producono effetti giuridici.

La lettura contabile è volutamente accoppiata ai repository Ruolo attraverso
un solo adapter; una modifica futura dei contratti Ruolo richiederà la stessa
prova d'integrazione. Un'operazione per account e cursore IMAP fermo su EML
oltre32 MiB restano limiti dichiarati della v1. La lettura remota riusa il
connector NAS esistente: il limite PDF è verificato dopo il download in memoria
e la policy SSH host-key del connector resta quella preesistente. Il collaudo
CED deve includere dimensioni delle sorgenti, risorse HTTP/worker e identità
SSH; questi aspetti condivisi non sono stati rifattorizzati nella chiusura.

## Baseline e verifiche generali

| Controllo realmente eseguito | Esito |
| --- | --- |
| Backend generale, pytest tests -ra e JUnit | 8022 PASS,471 SKIP,2748 warning,1437.14s; exit0, failure/error0 |
| Regressione PG supplementare,38 file in processi isolati | 428 PASS,9 SKIP intenzionali SQLite,0failure/error; tutti gli exit0 |
| Regressione PG collettiva supplementare | Interrotta:34 PASS,41 errori di setup preesistenti,exit2; confronto sul commit iniziale conferma errore |
| Communications dedicato, PG abilitato, due nuovi test inclusi | 125 PASS,0 SKIP; coverage 100% |
| Frontend unit completo | 349 file/5468 PASS, exit0 |
| Frontend mirato con coverage | 89 PASS,100% in tutte le metriche |
| npm test | 18 PASS,0 SKIP |
| npm run build:clean | PASS, build169 pagine; warning legacy fuori dal diff |
| npm run typecheck | PASS |
| ESLint sul runtime frontend toccato | PASS, nessun warning/errore |
| make lint-backend BASE_REF=main e Ruff/format test nuovo | PASS |
| Chromium PEC/email1440/390px sull'ultima build pulita | 4 PASS,9.2s |
| Worker Posta Online, processi isolati | 166 PASS/12 file, incluse6 provePG |
| Strumenti code-quality | 270 PASS |
| Ratchet merge-base main prima/dopo repair | PASS, findings[] |
| baseline-verify isolato e canonico | PASS, riproducibile true |
| Compose overlay config --quiet sintetico | PASS; nessun avvio/deployment |
| npm audit --omit=dev | PASS,0vulnerabilità note |
| Integrità del codice verificato | Hash dei38 file runtime/migrazione invariati durante la chiusura |

La suite generale aveva raccolto i 123 casi Communications precedenti prima
che fossero aggiunti i due nuovi test: questi sono inclusi e passati nella
corsa dedicata 125 PASS. I conteggi delle corse non vanno sommati come test unici.

Gli471skip generali comprendono460 casi senza URL PostgreSQL configurata,
9 varianti SQLite che saltano intenzionalmente prove di concorrenza PG e2 prove
GIS (OSGeo/pyproj assenti, verificato anche nel virtualenv). Le7 prove PG
Communications sono passate nella corsa dedicata. La successiva corsa isolata
per file recupera ulteriori prove: vedere il dettaglio supplementare sotto.
Gli skip non vengono dichiarati PASS; le varianti SQLite senza row lock non
sono usate per simulare concorrenza PG. Motivi esatti aggregati da JUnit in
/tmp/gaia-comm-close-skip-summary.json.

Warning backend: chiave JWT sintetica dei fixture e runpy dei test CLI,
più warning legacy dell'intera suite. Build: warning React/unused/img in file
fuori dal diff, verificati rispetto al manifest. La corsa frontend mirata non
ha warning applicativi; i messaggi JSDOM di navigazione della suite globale
riguardano il simulatore browser e non sono errori del prodotto.

Baseline riparata in commit separato d826c904. Nessun error-level aggiunto,
nessun codice Poste modificato. I51 warning nello scope restano debito tecnico
visibile, senza nuove esclusioni o refactoring di metriche.

La riparazione usa esclusivamente la procedura documentata in
../code-quality/QUALITY_RATCHET.md, sezione «Riparazione baseline stale su HEAD»:
worktree isolato a6274cac senza modifiche runtime, scope/engines invariati,
confronto semantico con la riproduzione nel checkout canonico. Non usa la
baseline modificata per autorizzare la change: il ratchet resta contro main.

## Regressione PostgreSQL supplementare

La corsa generale8022 PASS/471 SKIP è stata integrata attivando tre variabili
DB esclusivamente sul container PostgreSQL sintetico. Selezionati437 casi
prima saltati. La corsa collettiva è stata interrotta con SIGINT dopo75 casi:
34 PASS,41 errori di setup,0failure,exit2. Nessun risultato verde attribuito alla
corsa interrotta; i test non raggiunti restano da verificare nella stessa corsa.

Tutti i41 errori riportano AttributeError in
app/models/catasto_phase1.py:28: GeometryCompat.load_dialect_impl riceve
dialect=None durante l'ispezione GeoAlchemy prima di creare lo schema.
Il controllo minimo dotazioni/test_postgres.py +
ruolo/test_notice_confirmation_migration.py riproduce lo stesso errore,
senza raccogliere i test Communications. Ripetuto nel worktree detached del
commit di partenza9676aaa7: stesso errore/exit1. I due file runtime/fixture
interessati sono invariati nel ciclo; è una failure preesistente sensibile
alla composizione/import order della suite, non attribuita al nuovo runtime.
La migrazione conferma passa da sola (2 casi parametrizzati SQLite/PG).

Per distinguere le prove di dominio dal problema di composizione, i437 casi
sono stati inoltre lanciati in38 processi separati per file:428 PASS,9 SKIP,
0failure/error, tutti gli exit0. Le9 varianti SQLite saltano intenzionalmente
la concorrenza; le corrispondenti varianti PG passano. Nessun test o runtime
condiviso modificato per ottenere questi risultati.
I32 test legacy che richiedono schema pubblico operativo/PostGIS già migrato e
i2 test GIS con dipendenze OS assenti restano fuori da questa corsa isolata;
non sono considerati superati. Nessuna migrazione su un database reale.

Evidenze: /tmp/gaia-comm-close-extra-pg.{log,xml},
/tmp/gaia-comm-close-pg-order-control.log,
/tmp/gaia-comm-close-pg-baseline-control.log,
/tmp/gaia-comm-close-pg-isolated-summary.json e log/JUnit per file.

## Limiti e attività residue

Nessuna casella reale, trust provider reale, NAS CED, restore o carico di
produzione verificato: fuori dal collaudo locale autorizzato e vincolati a
OPEN_DECISIONS/DEPLOYMENT_PLAN. Non sono presentati come PASS provider.
Restano necessari testi/recapiti/policy del procedimento e conservazione
approvati dall'ente. Nessuna equivalenza automatica fra SMTP e notifica legale.

## Evidenze locali

Log e report /tmp/gaia-comm-close-*; i valori aggregati e le limitazioni sono
conservati qui, i log temporanei non costituiscono archivio permanente.
I primi tentativi con il container PG precedente non più esistente e con un
filtro coverage UI malformato sono stati scartati; non sono risultati verdi.
Le corse finali usano il nuovo DB sintetico e il manifest completo dei18 file UI.

## Graphify e working tree

Backend, frontend e Ruolo aggiornati solo tramite target Make. Frontend
rigenerato con --force dopo la patch di pruning:7113 nodi/16965 edge, rimosse
le vecchie definizioni estratte dal workspace. JSON/report aggiornati;
graph.html non rigenerato perché supera il limite preesistente5000 nodi.
Tutti i15 file backend Communications con codice e17 file frontend propri
sono presenti nel grafo; il workspace legacy e i registri restano nel corpus.
Nessun simbolo/route sorgente eliminato durante questa verifica finale.
Documenti Ruolo e piattaforma: chunk 1/1 done, nessun semantic failed.
Il primo refresh piattaforma ha prodotto3344 nodi/7561 edge; le modifiche
conclusive sono indicizzate nuovamente tramite lo stesso target Make.

Working tree estraneo preservato: .codex/config.toml, .gitignore,
CAPACITAS_FULL_RECOVERY_2026-10-05.md, CAPACITAS_POLITE_SYNC_2026-10-07.md,
SISTER_debug_runbook.md e tre file non tracciati CAPACITAS_RIPRESA_2026-10-27.md,
SISTER_STATO_2026-10-27.md, INAZ_RIPRESA_2026-10-28.md. Nessuno incluso nei commit.
File del ciclo limitati a test nuovo e documentazione; baseline già versionata
separatamente. Log e coverage restano in /tmp; container PostgreSQL sintetico rimosso,
server Next di prova chiuso e due worktree tecnici creati dalla verifica rimossi.
Nessun graphify-out o altro artefatto generato da committare.

## Documentazione allineata

Aggiornati README, PRD/ARCHITECTURE/IMPLEMENTATION_PLAN/DOCS_STRUCTURE di
piattaforma; PRD, API, architettura, piano, decisioni, changelog e test report
Communications; nota di dominio Ruolo. Nuovi FINAL_REVIEW, PROGRESS e
BASELINE_REPAIR. Il precedente FAIL baseline è conservato come storico,
con rimando alla riparazione realmente eseguita e non presentato come corrente.

## Conclusione

FINAL QUALITY GATE — FAIL

Il perimetro runtime Communications raggiunge il 100% di coverage e supera i
propri controlli. Il PASS complessivo richiesto non è dimostrabile: permangono
prove generali non verificate e un errore di setup della corsa PostgreSQL
collettiva. Gli esiti verdi delle corse isolate e il confronto col commit di partenza
sono registrati nella sezione di regressione supplementare. Nessun nuovo
refactoring fuori scope viene usato per mascherare il limite.
Nessun deployment o messaggio reale eseguito.
