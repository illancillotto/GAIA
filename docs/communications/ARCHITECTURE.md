# Architettura

## Template grafici — 12 novembre 2026

Il formato `GAIA-BLOCKS/1` nel campo `body` esistente rappresenta da 1 a 60
blocchi. `rich_template.py` possiede validazione, compilazione per campo e resa
MIME; `policy.render_template` resta il renderer letterale dei testi semplici.
Registry, anteprima e outbox usano il renderer compatibile. Gli adapter non
eseguono HTML dell’operatore: l’HTML è generato con escaping da blocchi consentiti.
Il worker allega il PNG ufficiale come parte related CID e mantiene il PDF
come allegato separato; il MIME finale è archiviato prima del trasporto.

Frontend: `TemplateAuthoring` gestisce form/catalogo; `TemplateEditor` e
`TemplateBlockEditor` modificano il documento; `TemplatePreview` usa elementi
React senza HTML libero. `MessageBodyEditor` conserva il testo compatto per i
vecchi modelli e pannelli apribili per i grafici, lasciando il PDF sotto i campi.
Nessuna nuova dipendenza o schema DB. Contratto e diagramma del flusso: [Template grafici e verifica finale](RICH_TEMPLATES_2026-11-12.md).


## Confini

Il catalogo amministrativo dei modelli (`communications/template_catalog.json`)
fornisce solo proposte modificabili e descrizioni delle variabili. Il mapping
dei dati è nel dominio Ruolo (`services/notice_communication_fields.py`), con
riuso delle funzioni del PDF per totale, termine e accessi. L'outbox conserva
il corpo risolto (testo semplice o documento a blocchi versionato); nessuna logica tributaria negli adapter. Versioni, approvazioni,
snapshot e trasporti restano quelli esistenti. Dettagli e limite sui vecchi
documenti senza accessi: [modelli ufficio](OFFICE_TEMPLATES_2026-11-07.md).

backend/app/modules/communications contiene ORM, API, outbox, registry, policy,
queue, worker, trasporti, parser e proiezione evidenze. ruolo_source.py è il
boundary di dominio: identità, pagamenti, eleggibilità, recapiti e lettura PDF.
SMTP/IMAP non importano regole tributarie. Un nuovo dominio richiede adapter e
policy/RBAC espliciti, non un nome arbitrario nel payload.

FastAPI registra due router sotto /communications, prefisso GAIA esterno /api.
Frontend: sessione, permessi, client e Tailwind/btn esistenti. PDF.js 5.4.624
caricato sul client; worker PDF distribuito localmente nella build.

## Workspace PEC/email

`workspace.tsx` mantiene filtri comuni e due colonne da breakpoint xl:
elenco più stretto (`0.85fr`) e composizione più ampia (`2fr`), allineati in alto. `use-workspace.ts` svuota la
composizione precedente al cambio avviso. `composer.tsx` inserisce il viewer
come slot di `ComposerForm`, fra campi e checklist. API, snapshot, permessi e
workflow di autorizzazione restano quelli esistenti; nessuna nuova dipendenza.
La versione mobile dispone elenco e composizione verticalmente.

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

## Recapiti condivisi con Utenze (implementazione 04/11/2026 non rilasciata)

`ana_electronic_contacts` appartiene al dominio Utenze e usa il soggetto canonico.
Communications riusa `contact_columns/contact_values` per i due canali, persone
fisiche incluse. Provenienza/versione/stato separano PEC, email e sconosciuti;
i trigger partecipano al fence della revisione documentale. Non è una seconda
anagrafica né una prova di validità giuridica del recapito. La migrazione non
classifica automaticamente dati legacy. Vedi CONTACT_CLASSIFICATION_2026-11-04.md.

## Anteprima immediata — 4 novembre 2026

Il GET sorgente autenticato è read-only e separato dalla creazione/approvazione della bozza. SourcePreview usa il viewer esistente con loader del contenuto e senza attestazioni; SourcePreviewActions conserva l’hash nel modello di composizione.

Dettagli: [SOURCE_PREVIEW_2026-11-04](SOURCE_PREVIEW_2026-11-04.md).
