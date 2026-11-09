# Buono pasto manuale da GATE — 2026-10-01

## Diritto automatico — precisazione del 05/11/2026

Dal 26/08/2026 il personale non turnista ha diritto al buono con ordinario
riconosciuto maggiore di zero e almeno 120 minuti di straordinario riconosciuto
dal calcolo GAIA. Il solo straordinario è escluso dall'automatico anche di
sabato, domenica e festivo; ordinario non attestato non soddisfa il requisito.
Non servono sette ore ordinarie o nove ore nette. La pausa rimane
nel calcolo orario preesistente; il buono non sottrae una seconda mezz'ora.
Un giorno con meno di due ore extra riconosciute resta escluso.

Per turnisti acquaioli/telecontrollo e profili datati Tecnico/Turnista IMPIANTI,
servono almeno 420 minuti effettivi, senza applicare la pausa dei diurni o
richiedere due ore extra. Per il profilo Tecnico/Turnista il requisito segue
il profilo, anche su OPE/SAB e altre giornate fuori dai codici di turno; una
revoca esplicita resta rispettata. Restano i controlli su trasferta/rimborso
vitto, la decorrenza e il massimo di un buono al giorno, anche con concessione
manuale. I valori manuali conservano audit e semantica gia documentati.

API dettaglio/matrice, XLSM e snapshot GATE usano la stessa funzione GAIA e
i minuti ordinari/extra canonici. La modifica GATE rilasciata verifica anche
la presenza di ordinario e la soglia dello straordinario canonico. Un valore
export esplicito, compresi zero e null, prevale sull'importato in GATE. Caso di
regressione: profilo Tecnico/Turnista, SAB, 06:58–10:04,
186 minuti extra: zero buoni.

La release installata della precisazione è
`meal-voucher-ordinary-required-20261105`. Il sabato breve e la domenica con
oltre dodici ore di solo extra sono verificati attraverso dettaglio, matrice,
snapshot ed XLSM; per i turnisti resta la loro regola specifica.

### Storico del ripristino precedente, prima della precisazione — 05/11/2026

Release `meal-voucher-extra-20261105` installata su backend, gate-mobile-sync,
presenze-worker e GATE VPS. Rimossa la verifica aggiuntiva del netto pausa;
conservate le correzioni dei profili turnisti, la loro soglia di sette ore e
il controllo delle trasferte. Cadoni 02/10, Casula 30/08 e Del Vais 28/09 hanno
diritto automatico. Il report precedente e ritirato: 391 giornate non turniste
su 71 collaboratori sono confermate spettanti nella cache attuale; altre tre
del 03/11 hanno dati GAIA nel frattempo aggiornati e ora sotto soglia/non
attestati rispetto alle 394 rivalutate nell'estrazione precedente; restano due giornate turniste dello stesso
collaboratore (una sotto le sette ore, una con timbrature incomplete).
Le 645 giornate turniste gia allineate restano riconosciute. Nessuna scrittura
su ore, timbrature, identita o concessioni manuali.

Regressioni GAIA della versione candidata PASS; modulo modificato 29 statement
e quattro branch al 100%, nessuna esclusione. GATE: 1.806 test e cinque prove
browser PASS, modulo modificato al 100%; typecheck, stile GAIA e ratchet PASS.
Il rilascio mirato e gia autorizzato dall'utente; gate globale GATE ancora FAIL.

### Storico superato: precedente rilascio restrittivo del 05/11/2026

I conteggi delle esclusioni sotto riportati descrivono la regola ritirata e
non devono essere utilizzati per escludere buoni dopo il ripristino.

Release `meal-voucher-net-20261105-1003`, backend e sorgenti dei servizi
`gate-mobile-sync` e `presenze-worker` aggiornati; tutti e tre healthy e con
checksum coincidenti per gli otto file rilasciati. La versione produttiva
XLSM conserva le altre logiche preesistenti: cambia soltanto l'argomento della
funzione del buono. Test della versione candidata superati, con 865 statement
e 306 branch al 100% negli otto runtime modificati, nessuna riga esclusa.
Questo dato non certifica la coverage globale dei repository.

Snapshot giornaliere e anomalie di agosto–novembre ripubblicati dai builder
GAIA con transazione sorgente read-only: 22.484 giornaliere, otto risposte
HTTP 200. Cache GATE verificata sui quattro mesi e sul record Cauli del
24/10/2026: automatico false, manuale false, conteggio zero. Nessun buono
automatico non turnista privo delle soglie ordinarie/extra nei quattro mesi.
Ciclo outbound riuscito dal 05/11/2026 10:25:03 al 10:29:13 UTC.

File operativi, log, checksum e comandi apply/rollback sono conservati su
`serverCed:/opt/gaia/releases/meal-voucher-net-20261105-1003/`.
`plan.json` contiene i comandi distinti per i tre servizi; gli override dei
worker mantengono `/app` sulla directory backend della nuova release.

Anche GATE VPS è stato aggiornato alla release `meal-voucher-net-20261105-1003`
su autorizzazione esplicita dell'utente al rilascio mirato con coverage globale
GATE FAIL dichiarata. Servizio healthy, health/readiness/console HTTP 200,
otto verifiche sul modulo installato e asset pubblico aggiornato. Le soglie
dei test e la policy globale non sono state modificate.

Audit storico read-only su identico snapshot del database, tra la precedente
immagine GAIA e la nuova: 13.409 giornaliere dal 26/08 al 05/11/2026, 190
collaboratori. Esclusi 396 diritti automatici su 72 collaboratori (395 casi
oltre al Cauli del 24/10), nessun buono manuale coinvolto. Dieci casi richiedono
verifica delle timbrature incomplete/non valide. Ripristinati 645 diritti
automatici GAIA di tecnici turnisti con almeno sette ore effettive. Tutti i
1.041 esiti modificati coincidono con la cache GATE; ore e timbrature invariate.
Il confronto non attesta buoni già erogati o riscossi.

## Inserimento manuale

Il contratto `GatePresenzeDailyRecordPatchRequest` accetta un booleano esplicito
`meal_voucher_manual`. Null, stringhe e numeri sono respinti. Omettere il campo
mantiene il buono precedente. Gli altri campi e permessi restano compatibili.

Sia il poll outbound (`patch_daily_record`) sia la route LAN
`POST /gate/presenze/giornaliere/{id}/patch` usano
`services/gate_daily_record_patch.py`: lock della giornaliera, audit idempotente
con autore canonico e origine `gate_console_mobile`, commit tramite il confine
esistente. Il campo non viene più ignorato con un ACK privo di effetto.
`services/meal_voucher_audit.py` condivide l'aggiornamento di stato e audit;
la web GAIA mantiene l'origine `gaia_web` e la firma del servizio precedente.

L'export e gli snapshot pubblicano il flag canonico. Manuale OR automatico
vale sempre uno per persona/giorno: revocare il manuale conserva l'automatico.
La migration dei campi è `20261001_1400`, già presente nel repository; nessuna
migration aggiunta dal collegamento GATE.

Test: `test_gate_meal_vouchers.py` copre entrambi i trasporti, valori invalidi,
autenticazione/record mancante, persistenza, audit idempotente, rollback,
compatibilità KM/reperibilità e pubblicazione. La regressione di 9 file pytest
passa: 237 test, 2108 statement e 358 branch nei 7 runtime modificati, 100%,
nessuna riga esclusa. Ruff e format check dei moduli nuovi passano. Anche il ratchet completo
contro `f687c213` passa, senza findings. Il dispatch delle appartenenze e
dei supervisori usa una tabella esplicita dopo la validazione; heartbeat e
transazioni mantengono il comportamento precedente. La regressione aggiuntiva
di questi due runtime passa: 60 test, 288 statement e 108 branch, 100%,
nessuna esclusione. Il dizionario delle anomalie usa lo stesso formato
compatto del builder giornaliere; gli alias e il comportamento non cambiano.

Frontend GAIA non modificato in questa integrazione: il comando è nella
console GATE e usa il dialogo mensile esistente. Contratto, uso e matrice test
sono documentati in GATE: `docs/PRESENZE_MEAL_VOUCHER_ENTRY.md`.

Stato operativo: rilasciato il 2026-10-01. Immagine
`gaia-backend:meal-voucher-ffa557fe`, sorgenti dello stesso commit in
`/opt/gaia/releases/meal-voucher-ffa557fe/backend` per il bind `/app`.
Migration `20261001_1400` applicata. Backup della tabella modificata
`presenze_daily_records` verificato con `pg_restore --list` (289 MB), file
`/opt/gaia/releases/meal-voucher-ffa557fe/presenze-daily-records-pre-deploy.dump`.
Il tentativo di backup integrale, interrotto per gli archivi Catasto, non è
considerato un backup; il dump incompleto è stato rimosso.

Solo backend e `gate-mobile-sync` ricreati, entrambi healthy; gli altri servizi
conservano gli ID precedenti. Checkout remoto e hotfix preservati, checksum
Compose invariati. L'override operativo aggiunto è
`/opt/gaia/docker-compose.meal-voucher.yml`: mantenerlo nei comandi Compose,
insieme a `docker-compose.override.yml` per backend e a
`docker-compose.team-delete.yml` per sync. Non sostituire il bind della release
con quello del checkout remoto durante le operazioni successive.

GATE VPS è alla release `105d9a5`, console
https://static.186.92.233.167.clients.your-server.de/admin .
Schema runtime, colonne e snapshot LAN verificati; settembre contiene 5670
giornaliere con booleano manuale. Lo stesso campo è arrivato nella cache GATE
e un record rappresentativo coincide in lettura. Il ciclo outbound post-deploy è riuscito: avvio 14:52:28 UTC,
conclusione 14:55:30 UTC, senza errore. I 502 del riavvio VPS sono transitori.
Il collaudo operativo su una persona/giornata reale resta separato.


FINAL QUALITY GATE — PASS
# Aggiornamento locale 09/11/2026: prerequisito di presenza

Il candidato locale richiede almeno una timbratura persistita di entrata o
uscita per KM positivi e buono manuale attivo. L'assenza completa di timbrature,
anche con ore contabili o AG, causa HTTP 422 prima delle modifiche.
Righe con entrata e uscita entrambe nulle non attestano presenza.

Controllo condiviso fra web GAIA, route GATE LAN e worker outbound; viene
acquisito il lock della giornaliera. Zero/null KM e buono manuale false sono
sempre rimovibili entro i permessi dell'operatore. Non è previsto alcun
azzeramento retroattivo; la reperibilità resta indipendente dalle timbrature.
Una presenza parziale consente i KM senza soglia di sette ore. La timbratura
incompleta richiede verifica prima del buono manuale e non attribuisce alcun
diritto automatico. Le regole automatiche restano quelle già concordate.

Correzione Loi 14/10/2026: OPE0613 giornaliero prevale sul diverso calendario
generale OPE0714_1E3SAB nei giorni feriali anche se manca il dettaglio INAZ. Con 05:51–13:03 il
calcolo di regressione passa da 363 ordinari/57 mancanti a 420/0. Gli inizi
personalizzati dello stesso codice e i codici non riconosciuti conservano il
comportamento precedente. Nessuna attribuzione implicita di profilo turnista.

Test: `test_presenze_manual_presence.py` (web/LAN/outbound, cancellazione,
patch combinate, orari parziali), `test_presenze_operai_daily_policy.py`
(regressione e controprova uscita anticipata), test React del buono manuale.
Rilascio in attesa dei gate completi: non assumere che il comportamento sia
già presente in produzione. Nessuna migrazione del database.

Ricontrollo finale del candidato del 9 novembre: suite estesa su copia congelata,
1.458 test passati e 2 saltati; sette file backend modificati al 100% di righe e
branch. Le controprove ripristinano il difetto di Loi soltanto su copie di test:
363 anziché 420 minuti, e falliscono come atteso. Sul candidato le stesse prove
passano. Il rilascio resta non effettuato per i gate GATE e di complessità ancora
non soddisfatti; questi risultati non sono una certificazione globale.

Il commit isolato su `fix/presenze-presence-guard-20261109` conserva le regole
automatiche versionate a HEAD: i cambi paralleli non sono inclusi. Controlli
sul contenuto selezionato dall'indice Git: 134 test backend e 13 test frontend
passati. Le misure estese sopra riguardano il checkout completo. Il push del
branch non rappresenta un rilascio e non chiude i gate ancora falliti.
