# Architettura

## Confini

backend/app/modules/communications contiene ORM, API, outbox, registry, policy,
queue, worker, trasporti, parser e proiezione evidenze. ruolo_source.py è il
boundary di dominio: identità, pagamenti, eleggibilità, recapiti e lettura PDF.
SMTP/IMAP non importano regole tributarie. Un nuovo dominio richiede adapter e
policy/RBAC espliciti, non un nome arbitrario nel payload.

FastAPI registra due router sotto /communications, prefisso GAIA esterno /api.
Frontend: sessione, permessi, client e Tailwind/btn esistenti. PDF.js 5.4.624
caricato sul client; worker PDF distribuito localmente nella build.

## Revisione e persistenza

Ogni bozza lega UUID sorgente/documento Registro e numero stampato a versione
account, destinatario, testo, purpose e fingerprint dei dati correnti. Il PDF
viene copiato come BYTEA una volta: preview e MIME leggono questi stessi byte.
Prima di approvare/accodare/inviare: confronto sorgente, revisione Registro,
SHA256 e fingerprint account. Il worker non rigenera.

Le API bloccano la riga messaggio e richiedono expected_version. L'approvazione
lega hash dell'envelope, operatore e versione; Pydantic valida tutti gli otto
controlli. Ogni PDF richiede ricevuta di rendering stesso operatore/versione.
Il browser verifica hash, byte e pagine. L'attestazione client non è una prova
anti-manomissione di lettura umana; la responsabilità sostanziale resta dichiarata.

## Transazioni e duplicati

Unique active_key prenota il numero all'approvazione. Trigger PostgreSQL
coordinano Communications e ruolo_poste_dispatch_items usando advisory lock
transazionale sul numero. Modifica/cancellazione pre-invio libera la
prenotazione; trasmissione/incertezza la mantiene.

Il fence di revisione commit Ruolo protegge il ricontrollo, non l'I/O SMTP.
Il controllo precede il confine persistito sending; una modifica successiva
non può revocare SMTP. Bozze esterne al portale Poste non registrate in GAIA
richiedono coordinamento operativo.

## Worker

Entrypoint autonomo: python -m app.modules.communications.worker.
Code SQL: dispatch_pec, dispatch_email, reconcile_pec, reconcile_email, test.
Mutex PostgreSQL sessionale per account, claim FOR UPDATE SKIP LOCKED, lease,
token di fencing, recovery. Un'operazione per account; nessun failover mittente.

MIME/Message-ID persistiti prima del trasporto. Errori espliciti sicuri: massimo
tre tentativi con backoff. Timeout durante DATA o crash dopo sending: uncertain,
mai retry automatico. Non viene promessa una garanzia exactly-once SMTP.

Pause globale/account sospendono dispatch lasciando acquisire ricevute.
COMMUNICATIONS_TRANSPORT_ENABLED=false impedisce tutte le connessioni.
SIGTERM/SIGINT cooperativi; healthcheck locale per processo e heartbeat DB
distinti dalla salute del provider.

## Ricevute

IMAP INBOX readonly, UIDVALIDITY/UID, BODY.PEEK: nessuna eliminazione. Originale
e cursore committati insieme. Massimo 50 messaggi per batch, 32 MiB ciascuno.
PEC: OpenSSL CMS + CA/pin, XML bounded senza DTD, correlazione Message-ID,
account e destinatario. DSN ordinarie sono evidenze tecniche senza effetti legali.

Snapshot, autorizzazioni, eventi e ricevute append-only tramite trigger.
NoticeAttempt/NoticeEvidence nel namespace gaia_communications, senza mutare
NoticeNotification o inCASS. Il monitor espone code/errori/incerti/non correlati.

## Riscontro di chiusura

Nessun cambiamento architetturale nella verifica finale. Il test
test_real_accounting_payment_blocks_an_already_reviewed_dispatch esercita il
repository contabile reale e la frontiera Ruolo/outbox. La migrazione è ora
misurata nel coverage con roundtrip PostgreSQL e SQLite. Matrice e limiti in
FINAL_REVIEW.md; procedura di baseline in BASELINE_REPAIR.md.
