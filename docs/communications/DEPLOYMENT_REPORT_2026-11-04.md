# Rilascio Communications sul CED — 2026-11-04

## Stato operativo

Rilascio mirato completato il 4 novembre, dopo l'autorizzazione esplicita
«ok rilasciamo invio pec e mail da gaia per gli avvisi», successiva al rinvio.
Migrazione e ruolo worker applicati alle 10:45; backend, frontend e worker
Communications healthy alle 10:46; verifiche conclusive terminate alle 10:48
(Europe/Rome). Le pagine PEC, email e amministrazione sono pubblicate.

Pausa globale attiva e trasporto backend/worker disabilitato: zero account,
zero messaggi e zero job. Prima dell'uso occorrono configurazione delle caselle,
approvazione dei template e collaudo autorizzato dei provider/documenti.
Nessun invio reale è stato eseguito. Posta Online risponde con automatismi
ancora in pausa; gli altri 33 container sono rimasti invariati.

La verifica di sviluppo del 3 novembre resta storica e conserva il proprio
`FINAL QUALITY GATE — FAIL`: il rilascio non trasforma i test generali mancanti
o la failure preesistente di setup PostgreSQL in prove superate.

## Artefatti e preservazione della produzione

- Sorgente Communications: commit base `1d26140c`, ricostruito in checkout
  isolato, con la correzione dei privilegi RBAC del commit `e39cbafc` descritta sotto.
- Le immagini candidate derivano dalle immagini effettive già in produzione,
  preservando le correzioni operative successive alla loro etichetta Git.
- Backend: `gaia-backend:communications-20261104`.
- Backend finale testato dopo il hardening: immagine `5fc895c82eda`.
- Frontend: `gaia-frontend:communications-20261104`.
- Rollback backend: `gaia-backend:communications-20261104-rollback`, codice
  applicativo precedente con sola conoscenza della nuova revisione Alembic.
- Directory protetta CED:
  `/opt/gaia/releases/communications-20261104-1d26140c`.
- Nessun aggiornamento globale del checkout CED, push, merge o riavvio degli
  altri worker eseguito. Le modifiche locali estranee restano escluse.

Il confronto di 1.227 file Python del backend esistente ammette soltanto le
due registrazioni API/ORM modificate, oltre ai 17 file aggiunti. Nessuna
correzione runtime preesistente è stata sostituita. Nel frontend le route
passano da 193 a 196: tre aggiunte e nessuna rimossa.

Il checkout CED precedente è su `main` a `6b61fd27`, con correzioni operative
locali. Il solo HEAD di quel checkout non descrive l'immagine candidata:
la provenienza è data da immagini di base, overlay Communications e manifest
dei file. Un futuro rilascio generico deve prima integrare queste sorgenti e
preservare le correzioni operative, evitando di ricostruire dalla sola vecchia
`main` o di sostituire inconsapevolmente gli artefatti della release.

La configurazione congelata è stata confrontata con i container effettivi:
variabili, volumi, reti, entrypoint, comando, utente effettivo e limiti CPU/RAM
sono preservati. Si aggiunge `COMMUNICATIONS_TRANSPORT_ENABLED=false` al
backend. I file che contengono configurazioni o segreti rimangono sul CED,
protetti e non versionati.

## Verifiche già concluse

| Verifica | Esito osservato |
| --- | --- |
| Test sulla prima immagine backend candidata, dati sintetici | 125 PASS |
| Test sull'immagine backend con privilegi corretti | 132 PASS, zero failure/error/skip |
| Coverage finale sul runtime candidato e migrazione | 1.641/1.641 statement, 336/336 branch; 100%, zero esclusioni |
| Regressione backend generale dopo il hardening, checkout isolato | 8.030 PASS, 472 SKIP, zero failure/error; 1.584 secondi |
| `make lint-backend` dopo il hardening, interprete del progetto | PASS |
| Restore del solo schema reale in PostgreSQL isolato | PASS |
| Migrazione candidata sullo schema isolato, ripetuta | PASS, revisione `20261103_1200` |
| Ruolo worker ristretto, heartbeat e trigger append-only nel clone | PASS |
| API Communications senza autenticazione nel clone | 401 per i tre endpoint verificati |
| Frontend candidato separato: login, amministrazione, PEC ed email | HTTP 200 su quattro pagine |
| PDF.js nell'immagine frontend | 5.4.624, worker locale presente |
| `npm audit --omit=dev` sull'immagine frontend candidata | PASS, zero vulnerabilità note alla verifica |
| Filesystem worker con UID 10001, rete disabilitata | Runtime leggibile, OpenSSL presente, directory segreti/trust accessibili e vuote |
| Immagine di rollback | Import applicazione precedente e riconoscimento della nuova head PASS |
| Backup completo PostgreSQL | PASS, 40.491.259.960 byte, SHA-256 calcolato |
| Verifica indipendente del checksum e ripristino integrale | PASS, intero archivio con `--exit-on-error --single-transaction` |
| Migrazione ripetuta e ruolo ristretto sul database ripristinato integralmente | PASS |
| API autenticate sul clone completo, account/template/messaggi/job/admin/candidati PEC/email | Nove GET, tutti HTTP 200; nessun messaggio creato |
| Migrazione di produzione | PASS, revisione `20261103_1200`, undici tabelle e ruolo worker ristretto |
| Backend/frontend/worker Communications in produzione | Healthy, configurazioni effettive confrontate con i container precedenti |
| API di produzione autenticate / non autenticate | Nove GET HTTP 200 / tre GET HTTP 401 |
| HTTP tramite nginx: health, login, solleciti, Poste, PEC, email, amministrazione | Sette URL HTTP 200 |
| Asset worker PDF.js tramite nginx | HTTP 200, asset locale da 1.002.904 byte |
| Stato operativo di sicurezza | Pausa globale, trasporto false, zero account/messaggi/job, due template draft |
| Altri servizi | 33 container con identità preservata; worker Poste ancora fermo |

I test SMTP/IMAP e le prove documentali sintetiche non verificano caselle,
trust o destinatari reali. Nessuna comunicazione è stata inviata.

La prima prova filesystem ha rilevato directory vuote di segreti/trust
appartenenti all'utente di deploy e inaccessibili al worker. Proprietà e
permessi sono stati corretti a `10001:10001` e `0700`; la prova ripetuta
sull'immagine candidata è passata. Nessun segreto esistente è stato modificato.

I tentativi preparatori non superati restano distinti dalle corse finali:

- La prima corsa backend ha prodotto 124 PASS e una failure per il file
  `worker-grants.sql` assente nel pacchetto di test montato. Ripetuta con
  l'artefatto presente: 125 PASS, senza modifica del runtime candidato.
- I primi due build frontend non disponevano di TypeScript dopo il pruning
  delle dipendenze di sviluppo. Il build definitivo usa `--include=dev` e
  compila senza modificare le sorgenti applicative.
- Il primo restore dello schema ha incontrato il riavvio del server
  temporaneo di inizializzazione PostgreSQL. Ripetuto da database vuoto dopo
  l'avvio definitivo: schema, migrazione e probe superati.
- La prima corsa dei 132 casi non esponeva le migrazioni dell'immagine alla
  cartella dei test: 123 PASS, una failure e otto errori di setup; non superata.
  Il collegamento è stato corretto. La nuova fixture dei grant richiedeva
  inoltre la gestione di SQL multilinea: la corsa successiva aveva 131 PASS e
  una failure di fixture. Corretto e verificato il parser, il test PostgreSQL
  mirato e la corsa finale completa di 132 casi sono passati. Nessuna
  esclusione o modifica del runtime è stata usata per correggere le fixture.

## Correzione dei privilegi prima dell'avvio

Il grant iniziale di lettura sull'intera tabella `application_users` consentiva
anche l'accesso agli hash delle password. Il worker rilegge ora soltanto
`id`, `role`, `is_active` e `module_ruolo`, con `load_only` e caricamenti
impliciti vietati. I grant SQL concedono le stesse quattro colonne.

Sei nuovi casi verificano operatore autorizzato, permesso revocato, modulo
assente, utente inattivo/assente e super amministratore senza flag individuale.
La settima prova applica l'intero file dei grant su PostgreSQL sintetico:
il controllo RBAC funziona e la lettura di password/recapiti è negata,
incluso un `SELECT password_hash` realmente respinto con SQLSTATE `42501`.
Nessuna API, migrazione, regola tributaria o comportamento UI è stato aggiunto.

Ruff lint/format sui tre file Python interessati PASS. Il ratchet contro il
merge-base di `main` passa. La baseline è stata aggiornata tramite il comando
ordinario in checkout isolato e verificata come riproducibile: cambia soltanto
la voce del worker. Nessuna soglia o esclusione modificata. Warning nel file
5→2, error-level 0→0; `_prepare` passa da Cyc14/Cog16/LOC50 a 9/10/43 e
il guard RBAC ha 8/9/21. La somma Cyc/Cog del file cresce 58/64→61/67 per la
responsabilità di sicurezza esplicita: non viene dichiarata una campagna di
riduzione della complessità o un risultato `IMPROVED`.

La regressione backend generale con questa correzione è conclusa nel checkout
isolato: 8.502 casi raccolti, 8.030 PASS, 472 SKIP, zero failure/error in
1.584 secondi. Gli skip PostgreSQL/GIS e le prove generali residue non sono
conteggiati come superati; il gate storico resta distinto da questa corsa.
JUnit e log sono conservati localmente in `/tmp/gaia-comm-rbac-full.xml` e
`/tmp/gaia-comm-rbac-full.log`; le prove dedicate sull'immagine sono nella
directory protetta CED `runtime-test-results-rbac/` della release.

`make lint-backend` è passato nel checkout isolato con il virtualenv del
progetto nel `PATH`. Il primo avvio con l'interprete di sistema era terminato
per assenza di Ruff, prima dei controlli: errore di ambiente corretto senza
modificare codice o configurazione del gate.

## Backup e condizioni di attivazione

Backup completo PostgreSQL in formato custom, checksum SHA-256 e ripristino
integrale con `--exit-on-error --single-transaction` precedono la migrazione.
Il database di verifica non espone porte e usa rete Docker `none`.
I dati del clone sono sul filesystem separato
`/mnt/gaia-archive/communications-restore-20261104`, evitando di saturare il
filesystem della produzione. L'archivio con dati reali resta sul CED.

Checksum dell'archivio completo:
`5faad4f467a8315c9cd25d31a2329cfab027d1bf9ffa7a28e712cbfb7ded6041`.

Il primo restore integrale è stato interrotto deliberatamente prima del commit
per ridurre il costo delle scritture WAL nel clone. Il tentativo definitivo
riparte dal database vuoto e dall'intero archivio, con `wal_level=minimal`,
replica disabilitata e `fsync=on`. Sono impostazioni del solo clone di verifica;
la configurazione del PostgreSQL di produzione resta invariata. Un tentativo
interrotto non viene conteggiato come restore superato.

Lo script operativo richiede il marker di restore integrale, migrazione
idempotente e RBAC verificati. Controlla inoltre che i container applicativi
non siano cambiati dalla preparazione e che il worker Poste resti fermo.
Una failure arresta i passaggi successivi; non autorizza replay automatici.

I marker `FULL_RESTORE_OK`, `FULL_RESTORE_MIGRATION_ROLE_OK` e
`CLONE_AUTH_API_OK` sono presenti. Il precedente blocco
`DEPLOYMENT_DEFERRED_BY_USER` è stato archiviato soltanto dopo la nuova
autorizzazione, registrata in `USER_AUTHORIZED_TARGETED_RELEASE`.
Prima dell'attivazione sono stati ricontrollati container, immagini, schema,
configurazioni e sorgenti effettive. Il backup completo verificato aveva circa
106 minuti; dimensione e artefatti immutati, schema ancora alla revisione
`20261103_0900`. È stato inoltre creato `backup/schema-preactivation.dump`
(1.245.404 byte). Il rollback applicativo conserva il database, senza riportare
i dati dei servizi attivi all'ora del backup.

Il solo database Docker di verifica resta arrestato, con volume ripristinato,
backup e prove preservati. I container applicativi sono stati sostituiti usando
la configurazione congelata, con `up -d --no-deps --no-build` sui soli servizi
backend/frontend, poi Communications worker. Eseguiti `nginx -t` e reload DNS;
nessun `down`, riavvio globale o attivazione del worker Poste.

Il primo tentativo si è fermato prima della migrazione perché Docker aveva
restituito i dieci mount backend in un ordine diverso. Il confronto di tutti
i campi, ordinati per destinazione univoca, ha confermato configurazioni
identiche; corretto il solo controllo operativo e ripetuta l'attivazione.
Anche il controllo successivo delle porte è stato precisato: l'immagine eredita
il metadato `EXPOSE 8000`, ma `PortBindings` è vuoto e non esistono porte
pubblicate. Nessuna modifica al runtime o alle sue protezioni per superare
questi controlli.

Verifica della disponibilità attuale: backend/frontend healthy; HTTP 200 per
`/api/health`, `/login`, `/ruolo/tributi/solleciti`. Tre GET autenticati Posta
Online per account, lotti e candidati hanno restituito 200. Nessun job avviato,
nessuna bozza caricata sul portale e nessun invio effettuato da questi controlli.

## Stato verificato dopo il rilascio

- Undici tabelle Communications e revisione `20261103_1200`.
- Pausa globale attiva, trasporto backend/worker disabilitato, zero account.
- Due template in bozza; nessun job o messaggio reale creato dal collaudo.
- Worker dedicato con ruolo DB ristretto, UID 10001, filesystem readonly,
  nessun socket Docker e heartbeat recente.
- Controlli HTTP autenticati limitati a GET; nessuna modifica tributaria.
- Posta Online non viene riavviata automaticamente.

Le prove sono conservate nella directory protetta della release:
`post-release-probe.log`, `postactivation-config-proof.json`,
`production-http-proof.json`, `production-pdfjs-asset-proof.json` e i marker
`PRODUCTION_ACTIVATED`, `PRODUCTION_READONLY_PROBES_OK`, `RELEASE_VERIFIED`.

Pagine operative pubblicate:

- `/ruolo/tributi/solleciti/pec`;
- `/ruolo/tributi/solleciti/email`;
- `/gaia/communications`, amministrazione per gli utenti autorizzati.

## Residui e sicurezza

Restano separatamente autorizzati: configurazione delle caselle, verifica dei
mount e dell'accesso NAS del worker, trust PEC, testi e policy dell'ufficio,
prove provider reali, carico e attivazione dei trasporti. Le prove generali
residue sono descritte in [FINAL_REVIEW](FINAL_REVIEW.md).

Durante la preparazione un precedente output di tool ha mostrato vecchi file
di deploy contenenti credenziali di produzione. L'incidente è stato segnalato
all'utente; i valori non sono riportati nei documenti. La rotazione coordinata
delle credenziali esposte resta necessaria e non viene eseguita implicitamente
durante questo rilascio.

## Aggiornamento frontend sidebar alle 11:50 CET

Il rilascio successivo autorizzato sostituisce il solo frontend con la sidebar
PEC/email, immagine `6218c83aa7da`, runtime `9ee72287`. Backend, worker, schema
e trasporti preservati; Posta Online era già attivo al nuovo preflight e resta
in esecuzione. Le immagini e gli stati iniziali riportati sopra restano la
fotografia del primo rilascio. [Report corrente e rollback della sola UI](SIDEBAR_RELEASE_2026-11-04.md).

## Filtri iniziali per recapito alle 12:13 CET

Aggiornato il solo frontend per preselezionare Presente sul rispettivo canale
PEC/email, immagine `1318fd5bdc5c`, runtime `2df77b43`. Rilascio concorrente
backend/Poste concluso prima del secondo tentativo; nuove versioni preservate.
[Report corrente, controlli e rollback UI](CONTACT_FILTERS_2026-11-04.md).
