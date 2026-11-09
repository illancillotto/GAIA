# Sicurezza

RBAC GAIA separa lettura, gestione Tributi e amministrazione provider. Account
filtrati per canale/modulo/utenti; worker ricontrolla approvatore attivo e
autorizzato. Routing: esplicito, default Ruolo, default canale; niente failover.

Secret reference senza traversal; password/token solo da file readonly esterno,
senza symlink e bounded. Nessun segreto provider nel DB, nessuna cifratura con
chiave nel DB. Secret store e rinnovo OAuth2 gestiti dall'operatore autorizzato.
API admin restituisce il riferimento, mai contenuto dei secret.

SMTP/IMAP TLS implicito o STARTTLS obbligatorio con verifica certificati.
Errori normalizzati; testo delle eccezioni non persistito. Eventi senza
credenziali/corpo completo. Destinatario singolo validato, niente header injection,
CC/CCN o HTML; template senza espressioni/include/attributi eseguibili.

Preview/originali autenticati, no-store/nosniff, nessun URL pubblico. Byte,
pagine e pixel bounded. Approvazione hash/versione/checklist; lock, idempotenza
e fencing contro concorrenza/replay. La ricevuta client di rendering non
certifica il comportamento umano: dichiarazione individuale distinta.

CMS con CA esplicita e pin SHA256 del certificato firmatario approvato.
Senza trust nessuna consegna certificata. XML senza DTD, correlazione tecnica
non basata sull'oggetto. DSN ordinarie potenzialmente falsificabili, senza
effetti giuridici. Conservare originali non verificati.

Backup DB include snapshot, MIME, EML, eventi e Registro; trust/secret separati.
L'ente definisce conservazione/accessi/export e distruzione; nessuna scadenza
legale o cancellazione automatica. Il DB privato non è presentato come sistema
di conservazione a norma già accreditato.

Overlay worker: UID10001, root filesystem readonly, cap_drop ALL,
no-new-privileges, limiti CPU/memoria/PID, secret solo al worker, nessuna porta.
SQL allowlist senza DDL/DELETE/UPDATE tributi; validare dipendenze sul rilascio.
La lettura di `application_users` è limitata a `id`, `role`, `is_active` e
`module_ruolo`. Il controllo dell'approvatore nel worker usa `load_only` con
`raiseload=True`: password, username e recapiti non vengono caricati e non
sono concessi al ruolo DB del worker. I super amministratori mantengono la
precedente semantica di accesso ai moduli anche senza flag individuale.
Firewall di egress ai soli endpoint approvati da applicare nel CED; nessun
Docker socket o credenziale CED al worker.

Verifica finale: npm audit produzione senza vulnerabilità note alla data della
prova, senza equivalenza con un audit formale. Il connector NAS condiviso
mantiene la policy host-key preesistente e legge la sorgente in memoria prima
del controllo32MiB Communications: verificare identità SSH, dimensioni e budget
risorse nel collaudo CED. Nessuna modifica a questo servizio condiviso durante
la chiusura. Matrice dei controlli locali in FINAL_REVIEW.md.

Nel successivo rilascio del 4 novembre i file di configurazione e backup
restano protetti sul CED; non stampare `docker inspect`, Compose risolti o
override completi, perché possono contenere segreti. Un output preparatorio
ha esposto credenziali dei vecchi override: incidente segnalato e rotazione
coordinata ancora da completare, come registrato in OPEN_DECISIONS e nel
[report operativo](DEPLOYMENT_REPORT_2026-11-04.md). Nessun valore è incluso
nei documenti o nei commit.

## Registro recapiti tipizzati (checkout 04/11/2026)

La classificazione richiede amministratore attivo, modulo Ruolo e vista Tributi;
non è disponibile a chi può solo comporre. API versionata, lock dell'anagrafica,
FK/check e audit before/after nella stessa transazione. Le fonti sono riferimenti
a verifiche amministrative, non una certificazione automatica di titolarità.
Nessuna verifica SMTP o invio è stata effettuata. Report 2021 con dati personali
conservato fuori dal repository. I dati legacy misti richiedono backfill esplicito:
la migrazione non trasforma email in PEC. CONTACT_CLASSIFICATION_2026-11-04.md.
