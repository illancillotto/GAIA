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
Firewall di egress ai soli endpoint approvati da applicare nel CED; nessun
Docker socket o credenziale CED al worker.

Verifica finale: npm audit produzione senza vulnerabilità note alla data della
prova, senza equivalenza con un audit formale. Il connector NAS condiviso
mantiene la policy host-key preesistente e legge la sorgente in memoria prima
del controllo32MiB Communications: verificare identità SSH, dimensioni e budget
risorse nel collaudo CED. Nessuna modifica a questo servizio condiviso durante
la chiusura. Matrice dei controlli locali in FINAL_REVIEW.md.
