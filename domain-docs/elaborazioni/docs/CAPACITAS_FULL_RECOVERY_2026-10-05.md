# Recupero Capacitas dall'anagrafica canonica

## Difetto verificato

Il sync inCASS selezionava esclusivamente soggetti già presenti in
`ruolo_avvisi`. CADONI ANTONIO (`CDNNTN55T24F698D`) è presente nell'anagrafica
GAIA ma non aveva avvisi né job. La sorgente restituisce 16 avvisi e due
contesti inVOLTURE. L'assenza del primo avviso impediva ogni sincronizzazione
automatica successiva.

Senza filtro anno, il selettore ora parte da persone e società canoniche,
comprese quelle storiche inattive. Il filtro esplicito anno dell'API harvest
Ruolo conserva il perimetro dei soggetti già a ruolo per quell'anno.
Il completamento recente di una ricerca senza avvisi evita la riaccodatura
continua dello stesso soggetto; gli errori non valgono come scansioni riuscite.

## Identità e dati recuperati

`recovery_identity.py` verifica il tipo anagrafico, la presenza di una sola
persona/società, CF/PIVA normalizzati e ownership univoca anche fra i due tipi.
Duplicati, identità mancanti/ambigue, identificativi invalidi o condivisi sono
elencati in `identity-audit.json`. Non si cercano corrispondenze per nome.
Le società vengono interrogate sia per PIVA sia per CF quando distinti.
Prima di ciascun task si ricontrolla l'identità rispetto al manifest.

Il flag generico `requires_review` non certifica un conflitto d'identità:
gli import NAS/CSV lo usano anche per documenti non PDF, variazioni e decessi.
Resta invariato e viene contato come `review_flagged_eligible` nell'audit,
senza escludere persone/società con identità fiscale canonica verificata.

La campagna comprende:

- inCASS: tutti gli anni e codici restituiti, importi/stati/pagamenti,
  dettagli, partitario, PDF, recapiti, spedizioni e ricevute disponibili;
- inVOLTURE: tutti i contesti trovati per CF/PIVA, anche senza filtro beni,
  storico anagrafico completo, certificati, intestatari e terreni con dettagli;
- domande irrigue: tutte le annualità disponibili e le particelle delle domande;
- Ruolo: testate ordinarie, partite e particelle mancanti dal partitario,
  riconciliazione degli aggregati per tributo con i parser canonici.

I riferimenti ordinari storici di 15 cifre che iniziano con `1` sono ammessi
come quelli con `0`, purché l'anno sia coerente. I ruoli speciali restano nella
sorgente inCASS e non sono convertiti in annualità ordinarie. Il recupero Ruolo
riusa gli helper di `backend/scripts/materialize_ruolo_from_incass.py`, senza
purge, sostituzione degli ID o deduzione di associazioni Poste/notifiche.

PDF mancanti o falliti fanno risultare incompleto il task. Le identità fiscali
della sorgente devono appartenere al soggetto canonico e un avviso già
assegnato a un altro soggetto non viene riassegnato. I certificati vengono
validati prima della persistenza. Domande con anno invalido e contesti
incompleti restano errori espliciti. Le segnalazioni del materializzatore,
comprese partite indisponibili e righe non materializzabili, sono conservate.

## Campagna riprendibile

Il comando è `python -m app.scripts.capacitas_full_recovery` dal backend.
Prima dell'applicazione salvare un backup consistente del database.

```sh
python -m app.scripts.capacitas_full_recovery \
  --output /runtime-data/capacitas-recovery-20261005 \
  --priority-identifier CDNNTN55T24F698D

python -m app.scripts.capacitas_full_recovery \
  --output /runtime-data/capacitas-recovery-20261005 \
  --priority-identifier CDNNTN55T24F698D --apply

python -m app.scripts.capacitas_full_recovery \
  --output /runtime-data/capacitas-recovery-20261005 --status
```

Il primo comando esegue solo audit locale e preparazione del manifest: non
interroga Capacitas e non modifica il database GAIA. `--credential-id` e
`--user-id` identificano credenziale e operatore dell'applicazione; la fascia
oraria della credenziale resta applicata. La campagna esplicita non usa la
policy leggera dell'autosync e richiede un operatore esistente.

`manifest.sqlite` contiene un task per soggetto/fase/contesto, esito, numero di
tentativi, risultato ed errore. Il lock impedisce due processi sullo stesso
manifest. Successi, inclusi risultati vuoti, non vengono ripetuti. Un task
interrotto resta riprendibile; `--retry-failed` ripete soltanto i task falliti.
`--max-tasks` delimita un'esecuzione pilota senza restringere il manifest.
Per riprendere usare la stessa directory. `summary.json` riporta i conteggi
per fase e stato; gli archivi JSON per soggetto conservano le risposte sorgente.
Le scadenze di sessione e gli errori di trasporto hanno retry limitati.
Una campagna con task falliti termina con errore, non con un falso successo.

I job inCASS appartenenti alla campagna hanno `recovery_task_key` nel payload:
il recupero ordinario dopo un riavvio backend non deve prenderne ownership.
Distribuire anche questo controllo nel worker runtime prima di eseguire la
campagna. Non avviare campagne diverse simultaneamente sullo stesso corpus.

## Limiti espliciti

- I record anagrafici bloccati richiedono correzione o revisione canonica; non
  sono esclusioni silenziose né candidati ad associazioni automatiche.
- Lo storico delle società viene archiviato integralmente come risposta
  sorgente; l'importatore storico normalizzato GAIA supporta solo persone.
- `inBOLLETTINI` dispone di configurazione portale, ma non di client/parser o
  modello d'importazione: questa campagna non inventa un'importazione per tale
  applicazione. I PDF degli avvisi disponibili tramite inCASS vengono recuperati.
- La scansione di tutta l'anagrafica può durare più giorni. Preparazione,
  avvio e completamento sono stati distinti e devono essere riportati come tali.

## Validazione

La suite mirata include `test_capacitas_full_recovery.py`,
`test_elaborazioni_capacitas.py`, `ruolo/test_incass_read_model.py`,
`test_incass_autosync_scheduler.py` e `test_incass_job_list_serialization.py`.
La misura deve usare un `COVERAGE_FILE` isolato, statement e branch, e tutte
le otto unità runtime nuove/modificate. Ratchet contro il merge-base e Ruff
restano gate distinti. Non modificare baseline, scope o soglie per assorbire
regressioni e non distribuire le altre modifiche presenti nel working tree.

## Evidenze operative del 5 ottobre 2026

Il dry-run sulla produzione ha preparato 33.100 soggetti eleggibili e 66.200
task iniziali, senza modificare GAIA. 10.780 soggetti eleggibili conservano
il flag generico di review. L'audit blocca 4.297 soggetti: 4.268 identità
mancanti/ambigue, 18 identificativi invalidi, 8 ownership multiple e 3 duplicati.

La verifica in sola lettura di CADONI conferma 16 avvisi e due certificati
con identità fiscale verificata, rispettivamente due e quattro intestatari.
I contesti CCO `000000055` e `000000056` restituiscono zero terreni correnti
e rispettivamente 21 e 24 domande irrigue. Questi conteggi descrivono la
sorgente, non un'importazione già conclusa.

La suite finale misura il 100% di statement e branch sulle otto unità
runtime: 1.195 statement e 386 branch. Ruff scoped, formatting dei nuovi
file e `git diff --check` sono verdi. Il ratchet della change non committata
contro il merge-base di `HEAD` restituisce `findings: []`, senza cambiare
baseline. Il confronto con `origin/main`, più vecchio della change, segnala
il precedente intervento su `list_incass_sync_jobs`, non modificato da
questa implementazione. Il lint globale è limitato da due file Presenze
estranei alla change che richiedono formatting.

Lo snapshot runtime isolato è preparato in
`/opt/gaia/hotfixes/capacitas-full-recovery-20261005/backend`, con una nuova
immagine worker derivata dall'immagine attiva. Il manifest e gli archivi
vivono in `/opt/gaia/runtime-data/capacitas-recovery-20261005`.
Prima di applicare occorre verificare il completamento di `gaia-before.dump`
e distribuire il controllo di ownership dei job nel worker runtime.

Il backup completo è terminato correttamente (circa 27 GiB); `pg_restore -l`
legge il relativo indice di 2.949 righe. Il fix è stato distribuito soltanto
nelle otto unità runtime. Nel frattempo un deployment indipendente ha
introdotto il runner irrigue parallelo: le nuove immagini derivano dalle
immagini effettivamente attive, preservando quel runner e la sua command.
Backend riavviato e healthy; il filesystem del worker contiene il controllo
ownership per i successivi riavvii, senza interrompere i job attivi. Le due
immagini hotfix sono configurate nell'override irrigue esistente, con copia
di rollback in `hotfixes/capacitas-full-recovery-20261005/originals`.

Il pilota ha importato in GAIA i 16 avvisi CADONI (15 testate ordinarie),
due certificati, 45 domande irrigue e 190 particelle delle domande. Il
materializzatore Ruolo ha creato 14 partite e 26 particelle. Uno storico
anagrafico è importato; il secondo restituisce dati fiscali e anagrafici
vuoti: resta archiviato e fallito esplicitamente, senza associazioni inferite.
La sorgente non restituisce link PDF per questi avvisi.

La campagna completa è avviata nel container `gaia-capacitas-full-recovery`,
con manifest persistente, retry dei fallimenti e restart `on-failure:3`.
Non è conclusa. Un watchdog arresta la campagna se lo spazio libero scende
sotto 12 GiB, lasciandola riprendibile. I log Docker sono limitati a tre
file da 10 MB. Durante l'esecuzione il lock protegge il comando; per monitorare
usare `docker logs --tail 20 gaia-capacitas-full-recovery` oppure una query
in sola lettura del manifest SQLite. Il comando CLI `--status` è disponibile
fra le esecuzioni. Nessun commit o push è stato eseguito.

La prima scansione estesa ha rilevato un ulteriore difetto: il parser
testuale dei terreni nel certificato collassa le colonne vuote, interpretando
la superficie come subalterno. Il recupero usa ora il dettaglio autorevole
del terreno identificato dal suo UUID sorgente per foglio, particella e
subalterno, prima di salvare il certificato e generare i task. Nessuna
deduzione tramite nome o numeri catastali ambigui. Un dettaglio incompleto
resta un errore esplicito. I certificati canonici sono già recuperati nella
fase dedicata: la ricerca di un terreno importa righe e dettagli, senza
attribuire al soggetto i certificati di tutti i proprietari storici della
stessa particella. L'errore del batch viene conservato nel manifest.

La campagna è stata fermata per applicare e testare questa correzione.
I 182 task terreni errati, tutti falliti, sono archiviati in
`terreni-task-repair.json` e nel backup `manifest-before-terreni-fix.sqlite`;
vengono rigenerati dai certificati, senza rimuovere task riusciti o dati GAIA.
Un pilota su un ulteriore soggetto ha confermato il recupero riuscito del
terreno con subalterno assente. La copertura branch/statement dei due moduli
corretti è nuovamente al 100%, e il ratchet scoped resta senza findings.
Il pilota successivo conferma anche il recupero del terreno sul soggetto
che aveva generato i 182 task errati; la campagna completa è stata ripresa
con il codice corretto e con il watchdog disco nuovamente attivo.
