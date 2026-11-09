# Invio solleciti con Posta Online — 2026-10-28

## Regola

GAIA prepara le bozze di **Raccomandata A/R online** sul conto contrattuale del
Consorzio e poi registra quello che risulta spedito. **INVIA lo preme sempre
l'operatore, a mano, su Poste** (decisione dell'utente del 2026-10-28).

GAIA non chiama mai `inserisciInvii.do`, cioè l'INVIA di Poste:

- non esiste un job, una route o un permesso di invio;
- il worker blocca in rete `inserisciInvii`, `paga`, `carrello`,
  `cancellaArchivio`, `modifica.do` e `hideInvii` in ogni fase, compreso il login;
- c'è un test che lo verifica per ogni fase.

Il contratto `notice_dispatch_contract.py`, pensato per un invio automatico,
resta scollegato. Anche `require_poste_submission_adapter()` continua a
rifiutare ogni invio.

## Procedura operativa

Dal 6 novembre la produzione include una vista iniziale per **anno → account
Poste**, con generazione/recupero da CF/P.IVA e preparazione automatica delle
sole bozze dopo la verifica indirizzi. Procedura, API, limiti e verifiche sono in
[SOLLECITI_WORKSPACE_2026-11-06.md](SOLLECITI_WORKSPACE_2026-11-06.md).
Rilascio coordinato verificato sul CED alle 10:13 CET. La procedura seguente resta disponibile
tramite **Storico lotti di generazione**; INVIA rimane manuale sul portale.

1. Dalla sidebar Ruolo aprire **Invio solleciti** (`/ruolo/tributi/solleciti`).
   Nella scheda «Solleciti generati» aprire un lotto, controllare il PDF con
   **Anteprima avviso** e spuntare **Seleziona per Posta Online**. La selezione
   resta mentre si passa ad altri lotti, fino a 50 solleciti. Scegliere l'account
   Poste da usare, dare un titolo e
   premere **Carica su Poste**: GAIA crea il lotto e apre la scheda «Posta
   Online». In alternativa, nella stessa scheda, «Nuovo lotto» cerca i
   solleciti per nome, codice fiscale o lotto. Il vecchio indirizzo
   `/ruolo/tributi/solleciti/poste` apre direttamente la scheda «Posta Online». GAIA copia il PDF e prende il destinatario dallo
   stesso payload che ha prodotto la lettera: nominativo, indirizzo, CAP,
   comune e provincia.
2. **Verifica indirizzi.** Il worker interroga lo stradario Poste
   (`autocomplete.do`). Accetta un indirizzo solo se via, civico, comune, CAP e
   provincia coincidono con un'unica proposta. In tutti gli altri casi l'avviso
   va in «Indirizzo da rivedere», con le proposte di Poste. Lì l'operatore può
   correggere il destinatario (e GAIA riverifica) oppure usare l'indirizzo
   manuale, che richiede CAP e provincia.
3. **Crea bozze su Poste.** Per ogni avviso il worker:
   - compila «Crea spedizione» con nome `GAIA <numero avviso>`, il PDF, il modulo
     Raccomandata A/R e un solo destinatario;
   - salva lo stato `draft_creating` prima di premere CONTINUA;
   - controlla la bozza in «Verifica e invia».

   Dopo 45 secondi rilegge prezzi e stati. Due bozze fallite di seguito fermano
   il lotto.
4. L'operatore accede con **l'account Poste indicato nel lotto**, apre
   **Verifica e invia** su Posta Online e controlla anteprime,
   destinatari e prezzi. Se tutto è corretto preme **INVIA**.
5. **Controlla Poste.** Il worker rilegge «Verifica e invia» e l'archivio. Per
   ogni bozza che non è più in «Verifica e invia»:
   - **la trova in archivio con il nome GAIA** (una sola spedizione): scarica il
     dettaglio, lo importa tra le raccomandate (`RuoloTributiRegisteredMail`),
     segna l'avviso «Spedito» con il numero di raccomandata e registra un
     tentativo di notifica (`NoticeAttempt`) nel Registro avvisi;
   - **non la trova nell'archivio letto per intero**: l'avviso diventa «Bozza
     scaduta o eliminata» e si può ricreare;
   - **trova più spedizioni con lo stesso nome**: segnala l'anomalia e non
     cambia stato;
   - **non riesce a leggere tutto l'archivio**: non conclude nulla.
6. **Annulla** su un avviso con bozza su Poste richiede l'eliminazione. **Elimina
   bozze annullate** la cancella con l'azione di quella riga (`DeleteInvio(id)`),
   mai con la selezione multipla condivisa del portale, e verifica che sia
   sparita.

La pagina avvisa se in «Verifica e invia» ci sono **bozze che non fanno parte
del lotto**: non è verificato se INVIA spedisca tutte le bozze presenti o solo
quelle selezionate. Segnala anche **bozze doppie**, cioè con lo stesso nome. Le
bozze scadono su Poste dopo 7 giorni, e la pagina mostra la prima scadenza.

## Account Poste e tracciabilità — 2026-11-03

Le credenziali si configurano nella gestione Posta Online esistente. Alla
creazione del lotto è obbligatorio scegliere una credenziale attiva: GAIA
conserva ID, username e nome dell'account e non permette di cambiarlo sul lotto.
La password resta nella gestione credenziali e non compare nelle API dei lotti.
La pagina permette di filtrare i lotti per account; restano i permessi GAIA
esistenti di lettura e gestione, senza introdurre una proprietà privata del lotto.

Ogni verifica indirizzi, caricamento, riconciliazione ed eliminazione usa
esclusivamente l'account associato. Il worker apre una sessione browser separata,
senza riutilizzare cookie o browser CDP condivisi. Un account disattivato, uno
username cambiato o un job incoerente bloccano l'operazione: non si passa a
un'altra credenziale disponibile. Le bozze e l'archivio letti sono quelli
visibili all'account usato su Poste; per vedere le bozze nel portale bisogna
accedere con quell'account. I controlli contro il doppio caricamento dello stesso
avviso restano globali anche fra account diversi.

GAIA distingue il creatore del lotto dall'operatore che avvia il caricamento.
Prima di CONTINUA registra sull'avviso ID e username dell'operatore richiedente
e ID del job. Gli eventi conservano operatore, username al momento dell'evento,
job, stato e data: anche in caso di nuovo tentativo si può ricostruire la storia.
Il dettaglio mostra account, creatore e operatore del caricamento di ogni avviso.
La riconciliazione registra l'operatore che la richiede; questo non identifica
chi ha premuto manualmente INVIA sul portale Poste.
Se l'operatore del caricamento non è più identificabile, il worker blocca
CONTINUA prima di cambiare lo stato dell'avviso.

La migration `20261103_0900`, successiva a `20261028_1500`, aggiunge questi campi
e conserva i lotti storici. Recupera gli username soltanto dagli ID GAIA già
registrati; non deduce account Poste o autore del caricamento. Prima di usare
un lotto storico occorre associargli esplicitamente l'account effettivamente
usato, tramite **Associa account** (permesso di gestione, nessun job in corso).
L'associazione è definitiva e produce un evento di audit.

Per il rilascio occorre distribuire backend, frontend e worker compatibili ed
eseguire la migration prima di riattivare i job. Il rilascio sul CED è stato
completato il 2026-11-03 alle 09:49 CET, release `poste-accounts-20261103`, con
database a `20261103_0900`. Backend, frontend e worker sono sani; le nuove API
sono state verificate con autenticazione e filtro per account. I dati del lotto
storico sono conservati: 1 lotto, 5 avvisi e 39 eventi. È presente una sola
credenziale Poste attiva e il lotto storico resta da associare esplicitamente;
il collaudo sul portale con due account reali resta da eseguire.

Le immagini mantengono configurazione, volumi e sorgenti estranei alla modifica.
Nel worker i moduli condivisi devono essere copiati in `/app/backend/app/`,
mentre nel backend risiedono in `/app/app/`: il pacchetto iniziale del worker è
stato corretto e verificato anche con un import nell'immagine di produzione.
Backup e ricevuta del rilascio sono in
`/opt/gaia/releases/poste-accounts-20261103/`; il ripristino è `rollback.sh`.
Il backend di ripristino include la nuova revisione Alembic, necessaria perché
l'entrypoint esegue `upgrade head`, ma mantiene il codice applicativo precedente.
Il ripristino conserva lo schema additivo e i dati di audit.

Verifica locale della modifica:

- Backend: `pytest tests/ruolo/test_poste_dispatch_*.py`, 75 test superati;
  coverage di righe e branch al 100% sui nove file runtime della modifica.
  Inclusi due account distinti, operatore diverso dal creatore, cambio username,
  credenziale inattiva, job di altro lotto, duplicati tra account, migration
  up/down e conservazione dei dati storici senza attribuzioni dedotte.
- Worker: 21 test del runner superati, coverage di righe e branch al 100% su
  `posta_online_dispatch_runner.py`; inclusi mancata apertura del browser con
  account incoerente e disattivazione di storage state e CDP condivisi.
- Frontend: 89 test nelle quattro suite account, pagina Poste, client API e
  pagina solleciti; coverage statement/branch/funzioni/righe al 100% sui sette
  file runtime interessati. Typecheck ed ESLint mirato superati.
- `make lint-backend BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python`
  superato. Ratchet di complessità contro la baseline del merge-base `main`,
  senza nuove violation o regressioni. La lista dei solleciti candidati ha una
  responsabilità di rendering separata dal form di creazione: `CandidatePicker`
  passa da cognitiva/ciclomatica 13/14 a 10/11, senza cambiare la selezione.
  Non sono stati modificati soglie, esclusioni o motori delle metriche.
- La sincronizzazione globale `make complexity-baseline` è stata rifiutata:
  lo snapshot locale già modificato rispetto a `main` rileva 60 aumenti di
  metriche rispetto al proprio contenuto, pur con ratchet contro `main` verde.
  La baseline preesistente è rimasta invariata; nessun aggiornamento forzato o
  `baseline-repair` è stato applicato. `baseline-verify` non è stato eseguito
  perché la sincronizzazione richiesta prima della verifica non è riuscita.

## Caricamenti concorrenti per account — 2026-11-03

Rilasciato sul CED il 03/11/2026 alle 10:48 CET come `poste-pool-20261103`,
successivamente al rilascio `poste-accounts-20261103`, inizialmente con tre job
contemporanei. Il limite per processo si configura con
`POSTA_ONLINE_MAX_CONCURRENT_ACCOUNTS` (default `3`, intervallo `1–32`), esposto
anche dal servizio Docker Compose `elaborazioni-worker-poste`.

**Configurazione della campagna con cinque credenziali.** Il rilascio operativo
`poste-pool-five-20261103` porta il limite di produzione a `5`, senza modificare
il default del repository o il codice runtime. Ogni account mantiene al massimo
un job attivo; account sospesi, esiti incerti e job esclusivi possono ridurre
il parallelismo effettivo sotto cinque. Aumentare il limite non sblocca questi
casi e non esegue INVIA.

La procedura ferma il controller della campagna, richiede l'arresto del worker
senza timeout di terminazione forzata e attende la conclusione dei job avviati.
Ricrea soltanto `elaborazioni-worker-poste` con la stessa immagine e un override
Compose persistente: unica differenza di configurazione, il limite da `3` a `5`.
Verifica health, limite letto dal runtime e conservazione delle altre risorse,
dei mount e dei container, quindi riavvia il controller. Configurazione precedente,
override di rollback e ricevuta sono nella directory privata della release sul
CED. I limiti del container restano 2 CPU, 3 GiB e 768 PID.

Applicato il 03/11/2026 alle 17:54 CET e verificato alle 17:56 CET. Per fermare
il lotto già avviato senza attendere tutti i suoi avvisi, due elementi ancora
mai sottoposti a CONTINUA sono stati temporaneamente sospesi con audit. Il
controllo di stato prima di CONTINUA ne ha impedito l'invio; i due esiti negativi
consecutivi hanno concluso il vecchio job, il cui fallimento resta nello storico.
Entrambi gli elementi sono stati ripristinati allo stato originale, verificando
hash del PDF, assenza di eventi di invio e identificativi ancora vuoti. Nessuna
modifica agli avvisi già in fase di invio. Questo è un checkpoint operativo
della campagna, non una nuova funzione generale di pausa dei job.

Worker healthy, configurazione runtime a cinque e controller riattivato sono
stati verificati. La ricreazione Compose ha riordinato i bind mount: il controllo
finale confronta il loro contenuto senza attribuire significato all'ordine.
La ricevuta di rilascio documenta anche il riavvio indipendente, durante
l'attesa, del container GaTe Mobile sync, che non è stato ricreato da questa
operazione.

La verifica locale comprende 16 test del pool esistenti e una prova operativa
aggiuntiva con limite configurato a cinque: cinque account lavorano assieme,
il sesto e il secondo job dello stesso account aspettano, tutti i job terminano
e tutti i lease vengono rilasciati.

`posta_online_pool.py` gestisce il pool; `posta_online_queue.py` seleziona i job;
`posta_online_leases.py` mantiene lock di sessione PostgreSQL su connessioni
dedicate per tutta la lavorazione, anche attraverso i commit del job. Due
credenziali con lo stesso username normalizzato (spazi esterni rimossi e
confronto senza distinzione maiuscole/minuscole) condividono il lock. I job
successivi dello stesso account aspettano, mentre altri account avanzano;
questo vale anche con più processi worker collegati allo stesso database.
Il limite numerico è per processo, il lock per account è condiviso nel DB.

### Retry persistenti della campagna — 2026-11-03

Il controller privato della campagna usa la policy versionata
`backend/app/modules/ruolo/services/poste_dispatch_retry.py`. Dopo timeout,
errori di connessione, HTTP 429/5xx o ritorno al modulo di login senza un errore
esplicito delle credenziali, pianifica tentativi senza un limite numerico.

Dal 05/11/2026, per il completamento entro le 07:00, timeout, messaggi «Oops/Ops» e
«Due bozze consecutive non create» usano un recupero rapido su tutti gli
account della campagna. Anche quest'ultimo esito richiede riconciliazione,
prima di proseguire con altri documenti:

| Fallimenti consecutivi | Attesa dopo la fine del job fallito |
| --- | --- |
| 1 | 15–18 secondi |
| 2 | 30–36 secondi |
| 3 e successivi | 60–72 secondi |

Dal 05/11 alle 07:55 CET, il ritorno al modulo di login identificato dal prefisso
esatto `Archivio Poste Online non raggiunto dopo login:` usa invece 60/120/300
secondi, con variazione fino al 20%: evita le precedenti attese di 30–36 minuti.
Resta necessaria una nuova riconciliazione prima del caricamento. Gli errori
espliciti di credenziali, OTP, CAPTCHA e blocco account continuano a richiedere
attenzione; HTTP 429 mantiene la precedenza e il backoff prudente. I cooldown
già pianificati per questa sola casistica sono anticipati conservando tentativo,
job fallito, lotto, stato degli avvisi e sospensioni manuali. Nessun browser del
worker viene interrotto. Policy verificata con 59 test, coverage righe e rami
100%, Ruff e ratchet mirato senza nuove violazioni; ricevuta privata in
`retry-controller/login-redirect-20261105/applied.json`.

Anche gli errori di trasporto `net::ERR_*`, `connection` e `socket` usano il
recupero 15/30/60 secondi: rimangono validi il riconoscimento prioritario di
HTTP 429 e i blocchi per autenticazione esplicita. Verificati 62 test della
policy con coverage righe e rami 100%; ricevuta privata in
`retry-controller/network-retry-20261105/applied.json`.

HTTP 429 mantiene sempre la policy prudente, anche quando il messaggio contiene
anche un timeout. Gli altri errori temporanei mantengono le attese precedenti:

| Fallimenti consecutivi | Attesa dopo la fine del job fallito |
| --- | --- |
| 1 | 2–2,4 minuti |
| 2 | 5–6 minuti |
| 3 | 10–12 minuti |
| 4 | 20–24 minuti |
| 5 e successivi | 30–36 minuti |

La variazione casuale è fino al 20%. Il controller verifica le scadenze ogni
30 secondi; code, fascia oraria della credenziale e lock possono posticipare
l'avvio effettivo. Il successo di un job azzera la progressione. Restano le
attese del client tra richieste e le pause dopo 25 richieste al portale.
Questa è una scelta operativa prudente, non una cadenza certificata da Poste.

Prima del retry del job, il worker prova un recupero locale degli elenchi:
`posta_online_listing_recovery.py` riconosce le pagine «Oops/Ops» e i timeout
di navigazione o di attesa della tabella. Attende 30–40 secondi, oltre al normale
intervallo tra richieste, e riapre una sola volta lo stesso URL GET, preservando
la pagina della paginazione. Il recupero ammette esclusivamente HTTPS sul dominio
del portale e i percorsi `incorso.do` e `archivio.do`; non aggiorna moduli,
CONTINUA, INVIA o pagamenti. Un secondo fallimento termina il job e passa alla
policy persistente. Il successivo job usa un nuovo client/browser e rifà il
login: non tenta di riutilizzare la sessione che ha fallito. Per ciascun job
il runner imposta `storage_state_path=None` e `cdp_url=None`: browser e contesto
nuovi isolano cookie, cache e storage, senza cancellare sessioni degli altri
account o riavviare il worker. Una pagina priva
della tabella non viene mai interpretata come un elenco vuoto.

Il controllo salva `retry_wait`, numero del tentativo, job fallito, lotto e
scadenza UTC nel file privato `control.json`. Il nuovo job conserva gli stessi
dati nel payload; ciò permette di recuperare anche un riavvio tra commit DB e
salvataggio del controller. Un retry avvia **riconciliazione sullo stesso
account**, prima di ogni nuovo caricamento. Gli avvisi già sottoposti a
CONTINUA, quelli con esito incerto, gli indirizzi sospesi e i casi eliminati
dai colleghi non vengono rimessi automaticamente in coda per il caricamento.
Una riconciliazione completa che lascia un documento incerto richiede ancora
verifica, invece di autorizzare un nuovo upload.

La disattivazione automatica dopo cinque errori di accesso può essere riaperta
alla scadenza soltanto se contatore, ultimo errore della credenziale e job
fallito coincidono e l'errore è temporaneo. Il contatore e l'errore restano
conservati: nessun successo viene dichiarato prima di una lavorazione riuscita.
OTP/App, CAPTCHA, credenziali esplicitamente rifiutate, blocco dell'account,
HTTP 403 generici ed errori non classificati richiedono attenzione; le sospensioni
manuali vengono mantenute. Il solo errore esatto `Poste Online detail:<ID> HTTP 403`
ammette recupero rapido. Prima di accodare la riconciliazione, il controller verifica
lotto, account e operatore del job fallito e isola il solo avviso attivo con quel
preciso ID Poste in `address_review`, evento `archive_detail_unavailable`.
Conserva PDF, destinatario, indirizzo, precedente verifica e chiavi anti duplicato;
non dichiara l'avviso inviato e non lo rimette in caricamento. Gli altri avvisi
possono continuare. Casi non attribuibili univocamente e stati protetti restano
sospesi per verifica manuale. Gli eventi `credential_transient_retry_enabled`
e `transient_retry_queued` riportano operatore, job e tentativo nell'audit.

Il codice della policy è installato accanto al controller privato nel volume
persistente della campagna; il servizio systemd usa quel percorso. Si riavvia
soltanto il controller, senza interrompere i browser del worker. La modifica
non introduce API generali di retry e non modifica il default dei normali job
Poste fuori da questa campagna. Il limite di cinque account e INVIA manuale
restano invariati.

Il rilascio notturno del 05/11 aggiorna soltanto la copia della policy accanto al
controller privato: nessun riavvio delle sessioni del worker o deploy generale.
Verificati 53 test, coverage righe e rami 100%, Ruff e ratchet mirato contro il
merge-base di `origin/main`, senza modificare baseline o soglie. Ricevuta privata
in `retry-controller/overnight-20261105/applied.json` e sul Desktop in
`Controllo_Poste_2026-11-04/Monitoraggio/Rilascio_notturno_20261105.json`.

Il recupero separato dei fallimenti sicuramente precedenti a CONTINUA usa ora
30/60/120 secondi, variazione deterministica 0,8–1,2 e controllo ogni minuto,
senza limite di tentativi. I guard contro evidenze di submission, modifiche
manuali, indirizzi assenti e avvisi già osservati su Poste restano invariati.
Gli otto test della policy privata passano con coverage righe/rami 100%.
Il piano del recupero include anche i 54 avvisi trasferiti da Cascinu a Serusi;
prima dell'inclusione sono stati confrontati hash PDF, destinatario e indirizzo
con il piano fonte originale.

Alle 00:24 CET del 05/11 sono stati trasferiti a Frau altri 39 avvisi mai
sottoposti a CONTINUA, 13 ciascuno da Salaris, Cascinu e Cadoni. Solo lotti
sorgente senza job attivi; verifica globale senza conflitti, prova con rollback
e commit tramite `cancel_item`, `create_lot` e accettazione degli indirizzi
manuali già verificati. I vecchi lotti mantengono il proprio account; le nuove
copie conservano integralmente PDF e destinatari. Il totale attivo resta 940.
Lotto `997eb12a-8e94-4a06-a2a5-489bc2a611d0`, job bozze `1026`; anche questi
nuovi item entrano nel piano di recupero sicuro. Ricevuta privata in
`redistributions/balance-frau-20261105/applied.json`. I 155 test di regressione
su retry, account, callback, anti duplicati, verifica finale e controller passano.

Rilascio `poste-retry-refresh-20261103` verificato il 03/11/2026 alle 18:19 CET:
worker healthy, hash di tutte le sorgenti controllati e configurazione a cinque
conservata; controller attivo dal volume persistente. Avviate le prime quattro
riconciliazioni sugli account prima sospesi; il quinto account è in attesa della
propria scadenza. I due avvisi fermati temporaneamente per il rilascio sono stati
ripristinati prima della ripresa. Questi dati certificano l'attivazione, non
il successo dei successivi login o il completamento della campagna.
Validazione: 104 test worker e 35 test della policy/controller, copertura righe
e rami al 100% dei tre file runtime toccati, lint e complexity ratchet senza
nuovi finding. Ricevuta in `evidence/POSTE_RETRY_REFRESH_2026-11-03.json`.

I job storici di sincronizzazione e test credenziali mantengono l'accesso
esclusivo al portale: attendono la fine dei caricamenti e, mentre lavorano,
impediscono l'avvio di altre sessioni, preservando storage state e CDP legacy.
I caricamenti continuano a usare browser isolati e la credenziale del lotto,
con la tracciabilità GAIA già prevista. Le fasce orarie e i cooldown restano
applicati. Un errore di un job non annulla le altre lavorazioni. Lo stop
ordinario smette di acquisire job e attende quelli attivi, entro il tempo di
arresto del servizio; dopo l'interruzione del processo, la perdita dei lock
consente il recupero dei job rimasti `processing`, senza azzerare quelli di
altri worker ancora attivi. L'INVIA resta manuale sul portale Poste.

Verifiche finali: 90 test worker superati, inclusi sei casi su PostgreSQL 16
dedicato e isolato. Oltre ai due pool, tre account, username duplicati, riga
occupata e perdita della connessione proprietaria, due thread acquisiscono
realmente nello stesso momento: account diversi partono insieme e username
equivalenti non ricevono ownership duplicate. Coverage righe e branch 100%
su pool, coda, lock, runner del processo, runner dei caricamenti e portale
(537 statement, 128 branch). Altri 31 test del worker generale e 30 di
sincronizzazione/cooldown/parsing passano. Arresto e cancellazione provati
con browser simulati; nessun caricamento reale effettuato dai test.

Ratchet contro la baseline del merge-base `main` senza regressioni:
`run_worker` conserva cognitiva `0`, ciclomatica `1`, LOC `6`; i tre nuovi
file non hanno violation error-level (due warning). La baseline locale
preesistente non viene forzata; resta il limite di sincronizzazione globale
descritto nella verifica del rilascio multiaccount sopra.

### Revisione finale, dipendenze e stato del rilascio

Il 03/11 la verifica finale comprende anche le estensioni precedenti ancora
non committate: 105 test frontend con coverage statement/branch/funzioni/righe
100% sui file interessati, typecheck ed ESLint verdi; coverage righe e branch
100% sui 21 file backend/script interessati (2272 statement, 570 branch).
La suite Ruolo estesa ha individuato un test di rigenerazione PDF rimasto
alla firma precedente di `create_lot`, senza credenziale. Il test ora salva
una credenziale esplicita prima del rollback del lotto e continua a verificare
sia il recupero del documento sia il rifiuto se il NAS non è raggiungibile:
l'intero file passa, 17 test. Le altre 76 verifiche della ripetizione mirata
campagna/script/rigenerazione erano già passate. Nessun assert indebolito.
I test PostgreSQL non pertinenti della suite estesa restano saltati in SQLite;
i sei test di concorrenza citati sopra usano invece un database PostgreSQL reale.
La suite completa degli strumenti di qualità passa: 270 test.

L'immagine `gaia-elaborazioni-worker-poste:poste-pool-20261103` è stata prima
preparata sul CED in `/opt/gaia/releases/poste-pool-20261103`, senza riavviare
servizi, poi rilasciata dopo le verifiche. Il runner locale dipende anche da `sister_worker_watchdog.py`, già
versionato ma assente nell'immagine precedente: il primo probe candidato ha
rilevato l'import mancante, risolto includendo questa dipendenza. I suoi 20
test passano con coverage righe/branch 100%. Il pacchetto definitivo contiene
i tre moduli del pool, `worker_runner.py` e il watchdog. Hash di tutte le altre
sorgenti Python invariati, import della candidata e limite `3` verificati,
configurazione conservata salvo la nuova variabile del limite. Nessuna nuova
migrazione. In produzione risultano tre credenziali attive; nessun job attivo
al preflight e il lotto storico richiede ancora associazione esplicita.

La sincronizzazione ordinaria della baseline locale era stata rifiutata con
60 incrementi di metrica, sospendendo commit/push/deploy.
Una seconda verifica ha ricostruito la baseline dal solo codice committato
`686e529e`, in un worktree pulito; `baseline-verify` su quella fotografia passa.
Il confronto delle estensioni correnti con tale fotografia rileva 68 incrementi
su 16 file (51 sul runtime e 17 nei test worker), pur senza nuove violation
error-level. Il gate autorevole sul merge-base di `origin/main` passa perché
la sua fotografia è più vecchia. I risultati sono distinti: il gate verde
non viene presentato come prova che la sincronizzazione sia riuscita.
L'utente ha quindi autorizzato esplicitamente di procedere mantenendo questi
incrementi come debito tecnico tracciato. Il record
`docs/code-quality/debt/POSTE_2026-11-03.json`, ID
`POSTE-20261103-COMPLEXITY`, conserva tutti i 68 confronti prima/dopo, il
perimetro, l'autorizzazione e la revisione prevista entro il 03/12/2026 o alla
prossima modifica dei callable interessati. Nessuna soglia, esclusione o
regola del gate cambia: l'eccezione vale soltanto per gli incrementi elencati.
La sincronizzazione della fotografia finale ha verificato corrispondenza esatta
con questo elenco; `baseline-verify` e ratchet `origin/main` passano. Test e
coverage restano obbligatori. Non si tratta di una deroga per aumenti futuri.

### Rilascio produzione e verifica conclusiva

- Codice committato e pushato nel branch `feature/avvisi-solleciti-2021`, commit
  `a46337a7db3cc95f5e1b431246a950d86b6d3752`. La baseline finale è riproducibile;
  il debito resta nel record esplicito, senza modifica dei gate.
- Alle 10:48:18 CET rilasciato soltanto `gaia-elaborazioni-worker-poste`, immagine
  `gaia-elaborazioni-worker-poste:poste-pool-20261103`. Backend e frontend
  mantengono le immagini del precedente rilascio multiaccount, già attive.
  Gli hotfix e gli altri container del server sono conservati.
- Health worker `healthy`, import runtime PASS e limite effettivo `3`.
  HTTP 200 su `/api/health`, `/login` e `/ruolo/tributi/solleciti/poste`.
  Tutte le sorgenti Python coincidono con la candidata; ambiente, mount,
  limiti, comando e healthcheck coincidono con il precedente container,
  con la sola aggiunta di `POSTA_ONLINE_MAX_CONCURRENT_ACCOUNTS=3`.
- Nessuna migrazione: DB a `20261103_0900`. Tre credenziali attive, zero job
  pendenti/in corso al controllo. Hash delle tabelle lotti, avvisi, eventi e
  job identici prima/dopo; nessun caricamento o invio reale avviato dal deploy.
- Backup delle tabelle Poste in `backup/poste-before.dump`, verificato con
  `pg_restore --list`; rollback pronto in
  `/opt/gaia/releases/poste-pool-20261103/rollback.sh`. Il rollback ripristina
  l'immagine e la configurazione del worker precedente, senza modificare il DB.
- Ricevuta priva di credenziali: `evidence/POSTE_POOL_2026-11-03.json`.
  Configurazioni complete, hash sorgenti e backup restano nella directory
  privata della release sul CED. Manutenzione applicativa sempre disattivata.
- Il push GitHub segnala inoltre quattro alert Dependabot di severità alta
  sul branch predefinito. I manifest delle dipendenze non cambiano in questo
  rilascio; tali alert restano un'attività separata e non sono dichiarati risolti.

| Comportamento | Evidenza pertinente |
| --- | --- |
| Account distinti in parallelo e limite del pool | pool con tre account e quarto in attesa; due pool PostgreSQL |
| Uno stesso username non si sovrappone | credenziali duplicate normalizzate e acquisizioni simultanee PostgreSQL |
| Job occupato non recuperato da un altro worker | lock di sessione, commit intermedi e riga PostgreSQL già bloccata |
| Recovery dopo perdita del proprietario | rilascio della connessione e nuova acquisizione dello stesso job |
| Arresto e cancellazione | completamento del browser attivo e rilascio dei lock anche prima dell'avvio del task |
| Errore isolato | un account fallisce mentre il secondo completa il lavoro |
| Account esplicito e audit | backend multiaccount, richiedente diverso dal creatore, incongruenze respinte prima del browser |
| Indirizzo dell'avviso e PDF | portale comune prima della via e rigenerazione del PDF mancante |

## Stati dell'avviso nel lotto

| Stato | Significato | Uscite |
| --- | --- | --- |
| `address_pending` | da verificare nello stradario | `address_ok`, `address_review` |
| `address_review` | indirizzo da rivedere | correzione → `address_pending`; manuale → `address_ok` |
| `address_ok` | pronto per la bozza | `draft_creating`, `draft_error` |
| `draft_creating` | CONTINUA in corso (salvato prima del clic) | `draft_created`, `draft_priced`, `draft_uncertain` |
| `draft_created` / `draft_priced` | bozza su Poste, in lavorazione o prezzata | `sent`, `draft_missing`, `cancel_requested` |
| `draft_uncertain` | CONTINUA premuto senza bozza visibile | riconciliazione |
| `draft_error` | modulo fallito prima di CONTINUA: nessuna bozza | nuova creazione |
| `draft_missing` | bozza scaduta o eliminata, non spedita | nuova creazione |
| `cancel_requested` | annullato con bozza da eliminare | `cancelled` o `sent` |
| `cancelled` / `sent` | stati finali | — |

Ci sono due vincoli di unicità su `active_key` (nome spedizione) e su
`active_source_key` (sollecito). Un sollecito sta in un solo lotto attivo, e un
sollecito spedito non si può rimettere in un lotto. L'annullamento libera il
sollecito. Il PDF copiato viene cancellato alla spedizione o all'annullamento;
resta il suo SHA-256. Prima del caricamento GAIA ricalcola l'hash: un PDF
alterato non viene caricato.

## Incidente: più avvisi nello stesso documento Poste — 2026-11-03

L'anteprima segnalata per `GAIA 020210000815390` contiene nove pagine:
la cover Poste e gli avvisi `020210000654720` e `020210000815390`.
Il PDF originale del secondo avviso contiene quattro pagine e il solo numero
corretto. La verifica locale dei 712 PDF in `Desktop/PDF_da_inviare/Ordinari`
trova per ciascun file una sola intestazione di avviso e il numero corrispondente
al nome: 691 documenti di quattro pagine, 17 di cinque e quattro di sei.
Questa verifica riguarda l'identità dei documenti, non un nuovo audit degli
importi o degli indirizzi.

**Causa.** La pagina `home.do` esegue `settaDocumenti()` al caricamento:
ripristina gli allegati da `sessionStorage` (`file_0` … `file_4`) e li aggiunge
alla coda `mainDt` e agli input multipart `file0` … `file4`. Aprire direttamente
la pagina non equivale al comando «Crea spedizione»: il relativo handler
azzera le cinque chiavi prima della navigazione. Il worker saltava tale
handler e aggiungeva il nuovo PDF agli allegati ripristinati. Il controllo di
un solo destinatario e del nome della bozza non rilevava la contaminazione.

**Correzione rilasciata.** Prima di compilare un avviso il
worker attende anche l'evento `load`, usa il comando `#crea_spedizione`, attende
il caricamento completo della nuova pagina e verifica che allegati, coda e
testo siano vuoti. Prima di CONTINUA controlla tutti gli input file della pagina:
deve esserci soltanto `file0`, con nome, dimensione e SHA-256 identici ai byte
del PDF sorgente. Controlla anche l'unica scheda visibile, `mainDt.length`,
`indexCount` e l'assenza di testo aggiuntivo. Un'incongruenza interrompe il
caricamento prima di `mark_draft_creating` e CONTINUA. Il reset usa il comando
del portale: non cancella cookie o storage di autenticazione.

La lettura e l'hash degli input avvengono nel browser; non basta verificare
la didascalia dell'allegato. L'attesa fissa dopo la selezione del file è stata
rimossa: `addDocument()` aggiorna sincronicamente la coda; resta il controllo
dei byte dopo l'inserimento del destinatario.

**Verifiche.** I test unitari coprono reset fallito e contaminazione durante
l'inserimento del destinatario. I test Chromium su una riproduzione HTML
sintetica del ciclo osservato coprono ripristino degli allegati, due avvisi
consecutivi, input nascosti, contenuto differente a parità di nome/dimensione,
scheda, coda, contatore, slot errato e testo aggiuntivo. Un ricevitore HTTP
locale verifica anche i multipart effettivamente trasmessi in due creazioni
consecutive. Non vengono contattati account Poste reali dai test.

Esito finale locale: 84 test worker e 50 test backend superati; coverage
statement/branch al 100% sui tre file del dispatch worker e su
`poste_dispatch_work.py`. `make lint-backend` e il ratchet contro `origin/main`
passano. Nel confronto con HEAD i 17 rilievi del precedente fix di lettura
pagine sono identici a quelli già autorizzati: nessun nuovo incremento sui
callable runtime esistenti, né nuove violazioni error-level. Baseline invariata.
Il dettaglio dei 17 incrementi accettati è versionato in
`docs/code-quality/debt/POSTE_PENDING_2026-11-03.json`.
Graphify del codice worker e della documentazione Ruolo aggiornati.

Rilascio sul CED completato alle 11:19:55 UTC del 03/11/2026, release
`poste-document-isolation-20261103`, commit `66b72e51`. Worker `healthy`,
pool di tre account, smoke HTTP superati e sorgenti verificati contro
l'immagine candidata. Backup delle quattro tabelle Poste e rollback nella
directory privata della release. Dati dispatch, configurazione e container
estranei preservati. Lo snapshot di integrità della procedura legge una riga
alla volta: il primo tentativo, che materializzava tutti i PDF in memoria,
è terminato prima del rilascio; la verifica incrementale è poi passata.

**Stato operativo prima del collaudo.** I caricamenti della campagna restano sospesi; la
cancellazione delle bozze errate è affidata ai colleghi. Questo fix non
cancella bozze, non rimette automaticamente in coda gli avvisi e non preme
INVIA. Il controllo multipart precede CONTINUA e non certifica la successiva
conversione PDF di Poste: prima della ripresa occorre il collaudo
di bozze consecutive con confronto delle anteprime finali ai sorgenti.
Il numero di pagine atteso va ricavato dal relativo sorgente, considerando
la cover e le eventuali pagine aggiunte dal portale.

**Adattamento al menu nascosto.** Il primo collaudo successivo al rilascio
ha fermato due tentativi prima di CONTINUA: `#crea_spedizione` esiste nel DOM
ma è nascosto nel menu, quindi il click Playwright attendeva inutilmente.
Il worker attiva ora il click nativo dello stesso elemento, conservando
l'handler Poste che azzera gli allegati. Sopprime soltanto l'azione predefinita
del collegamento `href="#"`, che altrimenti compete con la navigazione
`home.do` dell'handler. Il test Chromium riproduce sia il menu nascosto sia
il collegamento `#`, oltre al ripristino del documento precedente e al
caricamento consecutivo. I controlli sugli allegati restano prima di CONTINUA.

Verifica dell'adattamento: 84 test worker superati, righe e branch al 100%
sui tre file dispatch (427 statement, 100 branch); Ruff dei tre file toccati
e ratchet contro il merge-base di `origin/main` superati in un worktree
contenente soltanto questo fix. `_open_clean_form` conserva cognitiva 0,
ciclomatica 1 e nesting 0; LOC 6 → 9 per l'attivazione del menu.
Nessuna soglia o baseline modificata. Nel workspace condiviso lint e ratchet
globali rilevano problemi nelle modifiche Communications estranee al rilascio:
queste non sono incluse nell'immagine candidata né dichiarate risolte.
Graphify worker e Ruolo aggiornati, estrazione docs `chunk 1/1 done`.

L'adattamento è stato rilasciato alle 11:47:24 UTC del 03/11/2026 come
`poste-document-menu-20261103`, commit `a2bd56fe`: worker `healthy`, limite
effettivo tre account, import e smoke HTTP superati. L'immagine cambia soltanto
`posta_online_dispatch.py`; hash delle altre sorgenti, configurazione, dati
dispatch e container estranei invariati. Nessuna migrazione. Backup e rollback
sono nella directory privata della release sul CED; ricevuta senza credenziali
in `evidence/POSTE_DOCUMENT_MENU_2026-11-03.json`.

**Collaudo finale e ripresa della campagna.** Il job 93 dell'account Frau ha
creato consecutivamente `020210000458700` e `020210000768890`, bozze
`12276942` e `12276943`, entrambe prezzate. Le anteprime scaricate contengono
cinque pagine ciascuna: copertina Poste e quattro pagine del relativo sorgente,
un solo codice avviso, nessun documento dell'altra utenza. Il testo delle tre
pagine della lettera coincide con l'originale; i bollettini sono stati renderizzati
con Poppler e confrontati visivamente con l'ultima pagina del sorgente.
I render non sono identici pixel per pixel dopo la conversione Poste: non è
stata dichiarata uguaglianza binaria delle anteprime.
Evidenza priva di dati dei destinatari in
`evidence/POSTE_DOCUMENT_CANARY_2026-11-03.json`.

Prima della ripresa sono stati riletti integralmente i tre archivi (1018, 396
e 773 nomi spedizione) e verificata l'assenza di bozze precedenti; gli errori
temporanei «Oops» hanno richiesto ripetizioni delle sole letture. Il caso
`020210000775960` ha superato la compilazione manuale senza cambiare destinatario
né premere CONTINUA. Sono stati ripristinati con audit e hash dei sorgenti 708
avvisi assenti, conservando i due del collaudo: nessun caso residuo nel piano
di ripresa. I due avvisi esteri restano sospesi in attesa degli indirizzi
nazionali verificati già richiesti.

Alle 11:59 UTC il controller privato e il monitor sono stati riattivati per
i tre account, con nuova epoca di job a partire da 94: i fallimenti precedenti
restano nell'audit e non bloccano questo ciclo. Inclusi i cinque avvisi del
lotto pilota eliminati dai colleghi. Verificati tre job contemporaneamente
`processing`, uno per account, e il successivo lotto Salaris `pending`;
nessun INVIA automatico. Lo stato di avanzamento resta nel monitor privato
della campagna; queste evidenze descrivono la ripresa, non il completamento
dei 710 caricamenti nazionali. Sette test del controller confermano la
priorità della riconciliazione, il blocco degli esiti incerti e dei login
falliti, la sospensione degli errori e il filtro dei job della nuova epoca.

Nel primo avanzamento dopo la ripresa sono ricomparsi errori intermittenti
prima di CONTINUA: comando `#crea_spedizione` assente oppure `mainDt` non
definito nella pagina caricata. Il controllo degli allegati ferma il tentativo;
il controller sospende l'avviso con l'errore in audit e procede sugli altri,
senza ripetere automaticamente gli avvisi sospesi. Questi errori di compilazione
restano da riesaminare separatamente e non sono presentati come risolti dal
collaudo delle due anteprime.

## Documenti in attesa di lavorazione e lettura delle pagine — 2026-11-03

Poste può mostrare una spedizione con nome `GAIA <numero avviso>`, stato
«In attesa di lavorazione» e identificativo `-`. La riga è una prova che il
documento è già stato caricato: il parser la conserva con identificativo
`None`, e GAIA registra `draft_created` con lo stato Poste originale.
Non ripete CONTINUA e non la considera assente durante la riconciliazione.
Una lettura successiva aggiorna lo stesso avviso con identificativo numerico
e prezzo, conservando la prima data di osservazione. Il contatore `created`
comprende queste righe; per distinguere le bozze prezzate occorre leggere
gli stati degli avvisi. Una bozza senza identificativo non può essere eliminata:
il comando attende che Poste assegni l'identificativo.

Gli elenchi vengono letti dopo il commit della navigazione e la presenza
della tabella `col_invio_dett`: una pagina di login o errore non vale come
elenco vuoto. La pagina successiva viene aperta tramite l'href del collegamento
`Next`, con protocollo, host e percorso uguali all'elenco richiesto. Link
ripetuti producono un errore; dopo 100 pagine la lettura è incompleta.
Il limite consente anche gli oltre 20 fogli necessari a un account con
235 avvisi e otto righe per pagina. La navigazione non usa il click che sul
portale reale può restare bloccato in attesa del caricamento della pagina.

Il caricamento della campagna può usare più lotti da 50 dello stesso gruppo.
La procedura operativa mantiene una sola operazione per account, riconcilia
gli esiti incerti prima di proseguire e sospende i casi non confermati.
Il controller privato della campagna e il monitor non sono nuove API o un
servizio generale di GAIA. HTTP 403 sul servizio CAP e timeout/login restano
errori da verificare; non autorizzano modifiche agli indirizzi né retry ciechi.

## Recupero dei mancanti della campagna 2021 — 2026-11-04

La verifica operativa confronta i 942 PDF definitivi del Desktop (712 ordinari,
230 digitali con spese) con i 940 avvisi nazionali nei lotti e i due esteri
sospesi. Tutti i 940 hash degli allegati coincidono con gli originali. Il conteggio
dei caricamenti comprende `draft_created` e `draft_priced`; `sent` resta distinto.
`address_ok` indica un avviso pronto, non un caricamento completato.

Su richiesta dell'operatore sono stati riabilitati con audit 330 avvisi falliti
prima di CONTINUA, senza alcun evento di invio del documento, osservazione di
bozza o spedizione. Per altri 37 casi è stata richiesta una nuova lettura di
bozze e archivio completo. Queste operazioni documentano una ripresa, non il
completamento della campagna. Otto avvisi senza indirizzo completo, i due esteri
e i tre casi esclusi esplicitamente dall'operatore restano sospesi. Un nono
caso senza indirizzo ha una bozza preesistente, già contrassegnata nell'audit
come da non inviare: compare separatamente nel report privato e non deve essere
confuso con una bozza pronta per la spedizione.

Il servizio privato `gaia-poste-presubmit-recovery-20261104.service` affianca il
controller della campagna, senza cambiare API GAIA o configurazione del worker:

- rivede ogni 60 secondi soltanto fallimenti temporanei precedenti a CONTINUA;
- applica attese di 2, 5, 10, 20 e poi 30 minuti dalla nuova failure, con una
  variazione deterministica di ±20%, senza riabilitare un tentativo già rilasciato;
- verifica destinatario, account, hash e contenuto dell'allegato originali,
  validità dell'indirizzo, assenza di identificativi e di eventi di submission,
  osservazione, spedizione, correzione manuale o cancellazione;
- lascia terminare i job attivi del lotto e rispetta le sospensioni degli account;
- rimette in coda un avviso mancante del perimetro nazionale solo con un nuovo
  `draft_missing` prodotto da un job `reconcile` concluso con successo dopo la
  richiesta di verifica della campagna del 04/11 alle 05:25 UTC. Un'eventuale
  richiesta più recente sul singolo avviso prevale su quella generale. Lotto
  e account del job devono coincidere con quelli del documento. La prova deve
  seguire una lettura completa anche dell'archivio, non essere già consumata
  e non avere successive azioni di invio o modifica manuale.

Le transizioni passano dai servizi esistenti, sotto lo stesso advisory lock
usato dal controller, e registrano attore, tentativo e prova nell'audit. Le
operazioni di recupero non premono INVIA. Un successivo errore del portale non
è presentato come caricamento riuscito.

Il controller privato è stato corretto per una sospensione obsoleta: quando un
lotto aveva un timeout e un altro lotto dello stesso account aveva poi successo,
il retry sceglie ora il job fallito che coincide esattamente con il motivo della
sospensione tecnica. Le sospensioni manuali restano protette. Il rilascio del
04/11 alle 06:53 CET ha riavviato soltanto il controller; backup, script e ricevute
sono nel volume privato della campagna, nelle directory `retry-controller/` e
`recovery-20261104/`.

Il controllo periodico seleziona solo metadati dei casi sospesi e usa lock
`SKIP LOCKED` per non attendere righe già lavorate. Il PDF viene letto solo
per verificare l'integrità di un candidato effettivamente riabilitabile; anche
il controller differisce la lettura degli allegati durante i conteggi. Il
servizio di recupero ha una unit systemd utente persistente.

Validazione operativa: 28 test e 10 sottocasi sulle policy di attesa, le prove di
assenza, il riferimento del timeout e il controller con schema SQLite reale.
Non si tratta di una nuova certificazione di coverage dell'intero worker.
Le prove isolate sul portale non hanno premuto CONTINUA: hanno riscontrato pagine
«Oops..Something went wrong» e ritorni al login prima dell'inizializzazione del
modulo. Nessuna modifica degli indirizzi è stata introdotta per superare questi
errori. Il report nominativo dei mancanti resta sul Desktop e nel volume privato;
non viene versionato nel repository. Ricevuta tecnica priva di dati dei
destinatari in `evidence/POSTE_RECOVERY_2026-11-04.json`.

## Controllo duplicati tra account — 2026-11-04

Rilasciato in produzione il 2026-11-04 alle 11:11 UTC insieme al secondo
controllo finale. Backend e worker includono entrambi il nuovo servizio
`services/poste_dispatch_duplicates.py`. Non sono richieste migrazioni.
Ricevuta e limiti operativi nella sezione di rilascio seguente.

Le chiavi univoche globali `active_key` (nome avviso) e `active_source_key`
(sollecito sorgente) impediscono già prenotazioni concorrenti su account diversi.
L'avviso spedito conserva le chiavi; un annullamento confermato le libera.
Il nuovo controllo non usa codice fiscale o destinatario come identità: avvisi
con numeri diversi per la stessa persona restano distinti. Una rigenerazione
in un altro batch non elude la chiave sul numero avviso.

`GET /ruolo/tributi/poste-dispatch/duplicates` usa gli stessi permessi di lettura
del modulo e restituisce:

- `findings` e `total`: gruppi in conflitto per numero avviso o sollecito
  sorgente, con motivi `multiple_active_items`, `cross_account_conflict` e/o
  `multiple_portal_drafts`. Lo stesso caso può comparire per entrambe le chiavi;
- riferimenti di lotto, elemento, account, identificativo Poste, job e operatore
  GAIA del caricamento, quando disponibili; nessuna password o contenuto PDF;
- `accounts`: timestamp dell'ultima lettura delle bozze, disponibilità di uno
  snapshot completo, freschezza e verifica per ciascuno username;
- `coverage_complete`: tutti gli account censiti hanno uno snapshot completo
  delle bozze datato al massimo 30 minuti e non nel futuro. Non significa
  assenza di conflitti: occorre leggere anche `findings`.

Ogni lettura completa delle bozze salva anche `portal_snapshot.drafts`, con
nomi e identificativi, compresi quelli ancora nulli. Per ciascuno username,
normalizzato per maiuscole e spazi esterni, viene usato un solo snapshot: il
più recente fra tutti i suoi lotti. Non si sommano le stesse bozze osservate
da lotti diversi, né l'elemento GAIA e la sua corrispondente riga Poste. Più
righe del portale con lo stesso nome restano distinte anche senza identificativo.
Le credenziali disattivate e gli esiti incerti/spediti nell'outbox restano nel
controllo. Gli elementi annullati non costituiscono nuove prenotazioni, ma una
bozza ancora osservata sul portale rimane una prova da verificare.

Gli snapshot precedenti contengono soltanto `foreign_drafts`: queste prove
positive possono evidenziare un conflitto, ma non certificano una lettura
completa per il nuovo report. Una nuova riconciliazione del relativo account
aggiorna il quadro. Il report è di sola lettura e non accede al portale.

Prima di CONTINUA, `mark_draft_creating` verifica nuovamente i conflitti
nell'inventario globale e la coerenza di entrambe le chiavi di prenotazione.
Un conflitto blocca l'avviso in `address_review`, conserva i riferimenti
nell'evento `duplicate_upload_blocked` con attore/job e imposta
`no_automatic_retry`. La callback impedisce CONTINUA; la successiva gestione
del mancato invio preserva la sospensione. Il controllo non cancella bozze,
non modifica indirizzi/PDF e non preme INVIA. Una prova positiva datata resta
prudenzialmente bloccante finché una lettura successiva non la sostituisce.

Il report confronta nomi GAIA e dati già osservati. Non certifica in tempo reale
le sessioni degli altri account, caricamenti manuali con nomi arbitrari o
spedizioni non ancora importate dall'archivio. `coverage_complete` riguarda
le bozze, non una scansione completa di tutti gli archivi. Anche un report
senza conflitti non autorizza retry ciechi di esiti incerti: prima si riconcilia.
Le prenotazioni globali proteggono la concorrenza dei caricamenti GAIA;
operazioni manuali esterne diventano visibili alla successiva lettura dell'account.

Validazione: suite backend Poste con test specifici su bozze senza ID,
snapshot obsoleti/parziali, account disattivati, duplicati legacy e avvisi già
spediti; test concorrenti su PostgreSQL locale isolato (stesso sorgente,
rigenerazione dello stesso avviso, avvisi distinti). Copertura di righe e rami
al 100% dei tre file runtime modificati, più regressione del worker. Evidenza
tecnica in `evidence/POSTE_DUPLICATES_2026-11-04.json`.

La semplificazione successiva elimina la seconda diramazione sulla decisione
duplicati: `mark_draft_creating` conserva i controlli di account, modalità e
operatore; `allow_upload` sceglie e registra una sola transizione, di avvio
oppure di sospensione, nella stessa transazione. Lo snapshot riusa un unico
predicato SQL di lotto per leggere sia gli elementi negli stati interessati,
sia i nomi di tutti gli elementi: un avviso ancora pronto non viene classificato
come estraneo. Rimangono due query distinte e non vengono letti i PDF.

I quattro incrementi della prima versione sono eliminati: il chiamante torna
a ciclomatica 4 e cognitiva 3, con LOC 21→14; lo snapshot passa da LOC 40 a 33.
La funzione che sceglie l'esito mantiene ciclomatica 8 e cognitiva 8. Sul
perimetro dei tre file, le somme delle metriche callable scendono da
120→119 (ciclomatica), 107→106 (cognitiva) e 427→420 (LOC). Non sono stati
aggiunti wrapper, rinominati simboli o modificate soglie/esclusioni.
Il ratchet completo contro `origin/main` e la sincronizzazione ordinaria su
una copia privata completa della baseline passano senza deroghe. Anche
`baseline-verify` sulla copia privata conferma la riproducibilità. Il confronto
conserva le identità dei simboli che una scansione parziale non includerebbe.
Durante il refactoring baseline del repository e produzione sono rimaste
invariate; non è richiesta la deroga proposta per la prima versione.

## Secondo controllo finale di tutti gli account — 2026-11-04

Rilasciato insieme a backend e worker il 2026-11-04 alle 11:11 UTC. La verifica
è richiesta separatamente dopo il rilascio e non riattiva i job messi in pausa.
Questo passaggio si richiede esplicitamente a caricamenti conclusi: non parte
automaticamente dalla conclusione del singolo lotto.

`POST /ruolo/tributi/poste-dispatch/final-checks`, con permesso
`ruolo.tributi.manage_status`, congela il manifest degli account e degli avvisi
già caricati, con esito incerto o spediti. Crea un job di sola lettura per ogni
account disponibile, accorpando credenziali con lo stesso username normalizzato.
Richieste simultanee vengono serializzate tramite lock del lotto comune:
finché esistono job Poste `pending`, `queued_resume` o `processing`, una nuova
richiesta restituisce 409. Anche un job sospeso in `queued_resume` deve quindi
essere concluso o fermato definitivamente prima di richiedere il controllo;
non si deve riattivarlo soltanto per superare questa condizione.

Ogni job usa il login e il lease esclusivo per username già implementati nel
worker. Rilegge tutte le pagine di **Verifica e invia** e dell'**archivio**;
salva una prova dedicata con intervallo di lettura, identificativo esecuzione,
job, account e operatore GAIA richiedente. Non crea o cancella bozze, non cambia
gli stati degli avvisi e non preme INVIA. Timeout, errori di login e paginazioni
incomplete non producono una prova di successo. Account inattivi, storici senza
credenziale o senza lotto utilizzabile restano esplicitamente non verificabili.

`GET /ruolo/tributi/poste-dispatch/final-checks/{check_id}`, con i normali
permessi di lettura del modulo, confronta esclusivamente le prove di quella
esecuzione e restituisce:

- `accounts`: esito e prova di ogni account, inclusi quelli mancanti o falliti;
- `duplicates`: occorrenze dello stesso nome avviso GAIA, con account,
  identificativi Poste, fonte bozze/archivio e indicatore `cross_account`;
- `missing` e `misplaced`: avvisi attesi assenti oppure presenti soltanto
  su un account diverso da quello assegnato;
- `invalidations`: ripartenza/creazione di operazioni Poste, modifiche agli
  avvisi/lotti registrate nell'audit o variazioni del perimetro account;
- `complete`: tutte le letture sono riuscite, coerenti con manifest e job,
  datate al massimo 30 minuti, senza invalidazioni.

Lo stesso identificativo Poste osservato nelle bozze e poi nell'archivio dello
stesso account viene contato una volta. Identificativi uguali su account diversi
restano occorrenze distinte; due bozze senza identificativo restano due righe.
I nomi esterni al prefisso GAIA vengono conteggiati in `unmatched_rows`.

Lo stato `verified_no_duplicates` richiede completezza e assenza di duplicati,
mancanti e account errati. `duplicates_found` segnala un conflitto anche quando
il controllo è incompleto: leggere sempre anche `complete`. `needs_review`
indica avvisi mancanti o su account diverso; `incomplete` impedisce di considerare
il controllo concluso. Non vengono cancellati automaticamente i duplicati.

Le letture avvengono in intervalli distinti per account: il rapporto documenta
quanto osservato, non una transazione atomica del portale. Durante il passaggio
finale devono restare fermi i caricamenti e le modifiche manuali; quelle esterne
a GAIA non sono rilevabili prima della successiva lettura. Il confronto usa il
nome avviso GAIA, non il contenuto dei PDF o nomi arbitrari di spedizioni manuali.
Le prove storiche restano consultabili, ma dopo 30 minuti l'esito di completezza
scade e occorre una nuova esecuzione per verificare lo stato attuale.

Servizi: `poste_dispatch_final_check.py` (manifest e prove),
`poste_dispatch_final_report.py` (rapporto), worker `posta_online_final_check.py`.
Nessuna migrazione: utilizza job esistenti ed eventi append-only dedicati.
Evidenza di validazione: `evidence/POSTE_FINAL_CHECK_2026-11-04.json`.

Validazione finale: 183 test backend, 169 test unitari worker, 6 casi concorrenti
worker su PostgreSQL locale isolato e 10 test browser HTML superati. Quattro
casi concorrenti PostgreSQL sono inclusi nei 183 backend, compresa la doppia
richiesta simultanea del controllo finale. Coverage righe/rami 100% sui sette
runtime backend e quattro worker verificati, zero nuove esclusioni. Lint,
formattazione e ratchet completo contro il merge-base di `origin/main` passano;
i tre nuovi runtime hanno zero finding error e quattro warning. Sincronizzazione
e `baseline-verify` passano su copia privata completa della baseline, senza
modificare quella del repository. I test browser richiedono un processo separato
dalla suite client legacy, che sostituisce globalmente Playwright durante la
collection: il tentativo combinato fallito è conservato nell'evidenza.

## Rilascio anti duplicati e verifica in produzione — 2026-11-04

Rilascio selettivo completato alle 11:11 UTC: immagini
`gaia-backend:antiduplicati-20261104` e
`gaia-elaborazioni-worker-poste:antiduplicati-20261104`, ricavate dalle immagini
in uso. Sei file backend e due file worker aggiornati; gli stessi sei file
backend sono presenti anche nell'immagine worker. Confrontati gli hash di
tutte le sorgenti Python: nessuna differenza fuori dal manifest. Conservati
ambiente, comandi, mount, risorse e limite di cinque account contemporanei;
nessuna nuova migrazione. Le altre immagini di servizio restano fuori dal
rilascio, comprese quelle delle comunicazioni.

Prima dell'aggiornamento sono stati fermati controller e timer di recupero;
i job già avviati sono terminati e il worker è uscito con codice zero.
Il primo tentativo è stato ripristinato automaticamente perché Compose
proponeva `unless-stopped` mentre il worker aveva `restart=no`. Entrambi gli
overlay, rilascio e rollback, ora preservano esplicitamente la politica
effettiva. Il secondo tentativo ha superato healthcheck e confronto completo
della configurazione. Ripetuti 183 test backend: coverage righe/rami 100%
dei sei file distribuiti, 636 statement e 166 branch.

La verifica indipendente è stata richiesta come `porcu.alessandro` dopo il
rilascio, con i caricamenti fermi. Frau resta esclusa per istruzione esplicita
dell'operatore: credenziale inattiva e account in standby. L'esecuzione censisce
comunque l'account come non verificato; anche con quattro letture riuscite non
può certificare l'intero insieme delle credenziali. Scanu Beniamino resta
rinviato e il controllo non avvia cancellazioni o ricaricamenti.

Ricevuta tecnica, identificativo della verifica e stato aggiornato:
`evidence/POSTE_ANTIDUPLICATI_RELEASE_2026-11-04.json`. Le prove nominative
complete restano nel volume runtime privato e nella cartella del controllo
sul Desktop; non vengono versionate nel repository.

Esito della prima verifica dopo il rilascio: tutti e quattro i job richiesti
sono riusciti. Lette 258 bozze e 3.110 righe di archivio: Salaris 80/1.089,
Cascinu 0/918, Serusi 93/964 e Cadoni 85/139. Nessun gruppo duplicato e nessun
avviso presente soltanto su un account diverso da quello previsto. Restano
cinque avvisi attesi non ritrovati nei quattro account, quattro dei quali già
con esito incerto nell'outbox. I riferimenti sono nel rapporto privato; nessun
ricaricamento automatico è stato avviato. Caricamenti e recuperi restano in
pausa per approfondire i mancanti. Il rapporto conserva `complete=false` e
`status=incomplete` per l'esclusione di Frau: questi risultati non certificano
l'assenza di duplicati sull'account escluso.

Ripresa autorizzata dall'operatore alle 11:41 UTC: controller riattivato e
quattro job di riconciliazione accodati per Salaris, Cascinu, Serusi e Cadoni,
prima delle successive bozze. I cinque mancanti sono stati messi singolarmente
in `address_review`, con evento `final_check_missing_held`, riferimento alla
verifica e `no_automatic_retry=true`; conservati PDF, indirizzi e identificativi
precedenti. Frau resta inattiva e in standby, Scanu resta rinviato. Riattivato
soltanto il recupero sicuro degli errori precedenti a qualsiasi submission;
il vecchio servizio di recupero delle assenze resta spento. Il worker torna
alla politica `unless-stopped` per la prosecuzione autonoma della campagna.
La verifica appena salvata resta una prova storica: la ripresa invalida
correttamente la sua certificazione dello stato attuale.

## Componenti

- Backend `backend/app/modules/ruolo/`:
  - `poste_dispatch_models.py`: lotti, avvisi, eventi append-only; migration
    `20261028_1500`;
  - `poste_dispatch_schemas.py`, `routes/poste_dispatch_routes.py`;
  - `services/poste_dispatch.py`: comandi dell'operatore;
  - `services/poste_dispatch_state.py`: transizioni e audit;
  - `services/poste_dispatch_work.py`: esiti riportati dal worker;
  - `services/poste_dispatch_reconcile.py`: archivio e Registro;
  - `services/poste_dispatch_recipient.py`, `services/poste_dispatch_address.py`;
  - `services/poste_dispatch_views.py`.
- API `/ruolo/tributi/poste-dispatch`. La lettura richiede `ruolo.tributi.view`;
  i comandi richiedono `ruolo.tributi.manage_status`, lo stesso permesso di
  conferma ed export:

  | Metodo | Percorso | Uso |
  | --- | --- | --- |
  | GET | `/candidates` | solleciti generati in PDF e non in un lotto attivo |
  | GET | `/accounts` | account selezionabili, senza password |
  | GET, POST | `/lots` | elenco filtrabile con `credential_id`; creazione con `credential_id` obbligatorio |
  | GET | `/lots/{id}` | dettaglio del lotto |
  | PUT | `/lots/{id}/account` | associazione definitiva dell'account a un lotto storico |
  | POST | `/lots/{id}/jobs` | operazioni sul portale: `addresses`, `drafts`, `reconcile`, `delete` |
  | PUT | `/lots/{id}/items/{item}/recipient` | correzione del destinatario |
  | POST | `/lots/{id}/items/{item}/manual-address` | indirizzo manuale |
  | POST | `/lots/{id}/items/{item}/cancel` | annullamento |
  | GET | `/lots/{id}/items/{item}/document` | PDF copiato nel lotto |
- Worker `modules/elaborazioni/worker/`:
  - `posta_online_dispatch_portal.py`: guardia di rete e parsing;
  - `posta_online_dispatch.py`: azioni del browser;
  - `posta_online_dispatch_runner.py`: i quattro job.

  I job usano la coda esistente `posta_online_registered_mail_sync_jobs` con
  le modalità `poste_dispatch_*`, smistate da `posta_online_sync._job_runner`.
  Il pool permette account distinti in parallelo e serializza i job dello
  stesso account, mantenendo le fasce orarie. Si può avere un solo job attivo
  per lotto. Un job interrotto viene ripreso dopo aver acquisito il lock
  dell'account: rilegge «Verifica e invia» prima di agire e non ripete CONTINUA
  sugli avvisi in `draft_creating`.
- Frontend:
  - pagina «Invio solleciti» `src/app/ruolo/tributi/solleciti/page.tsx`, con
    le schede «Solleciti generati» e «Posta Online»; `poste/page.tsx` apre la
    seconda;
  - componenti in `src/components/ruolo/poste-dispatch/` (pannello lotti) e
    `src/components/ruolo/solleciti/` (anteprima PDF e selezione,
    `poste-selection.tsx`);
  - client `src/lib/ruolo-poste-dispatch-api.ts`;
  - voce «Invio solleciti» nella sidebar Ruolo, subito dopo Tributi.

## Scelte predefinite e limiti

- **Codice fiscale non compilato.** GAIA non usa ritiro digitale né avviso di
  ricevimento digitale.
- **Opzioni di stampa del portale.** Colore e fronte/retro restano quelli
  predefiniti di Poste: vanno controllati nell'anteprima e nel prezzo prima di
  INVIA. Il lotto lo registra in `postal_options.portal_defaults`.
- **Bollettino TD 896.** Resta da avere da Poste la conferma che accetta il
  bollettino stampato da loro, ed eventualmente a colori.
- **Solo lotti generati.** Entrano solo i solleciti dei lotti «generated» con
  PDF definitivo, che sono quelli usati in produzione. Le bozze private
  2022/2023 confermate passano ancora dall'export ZIP: il manifest dell'export
  dichiara `authorizes_dispatch: false`.
- **Limiti di Poste.** PDF fino a 7 MB, un destinatario per bozza, nome
  spedizione `GAIA <numero avviso>` di massimo 40 caratteri.
- **Collaudato sul portale reale:**
  - creazione ed eliminazione di una bozza con indirizzo dello stradario
    (bozza 12269236, prova del 2026-10-28);
  - lettura dell'archivio e del dettaglio.
  - indirizzo manuale con comune prima della via e CAP dell'avviso
    (pilota del 2026-11-02, completato con riconciliazione il 2026-11-03).
- **Non ancora collaudato sul portale reale:**
  - la cancellazione con `DeleteInvio(id)`.

  Il primo lotto va seguito sul portale.
- **Prima di usare il primo lotto vero.** L'operatore verifica con due bozze di
  prova se INVIA spedisce tutto «Verifica e invia» o solo le bozze selezionate.
- **Rilasciato sul CED il 2026-10-29** (release
  `poste-dispatch-20261029-05fa4a86`, database a `20261028_1500`).
  - Backend, frontend e worker Poste sono stati rilasciati insieme, perché il
    worker precedente non riconosceva i job `poste_dispatch_*`.
  - Il worker usa lo stesso `app/` del backend.
  - Verifiche, ripristino e vincoli sono in `PROGRESS_ruolo.md`, alla voce
    del 2026-10-28.

## Verifiche

Dal 2026-11-05 il dettaglio dei solleciti generati mostra anche lo storico Poste
persistito (ID, date, codice raccomandata e account), comprese le copie dello
stesso numero avviso in altri lotti. Vedi
[contratto, test e rilascio](SOLLECITI_POSTE_HISTORY_2026-11-05.md).

- **Backend.** Test in `backend/tests/ruolo/test_poste_dispatch_*.py`:
  servizi, transizioni, riconciliazione reale con il Registro (tentativo e
  tracking), API, permessi, migration up/down. È incluso il caso che ha trovato
  un difetto: un `ValueError` del Registro interrompeva la riconciliazione, e
  ora viene riportato sull'avviso.
- **Worker.** Test in `tests/test_posta_online_dispatch*.py`:
  - guardia per ogni fase;
  - parsing della pagina reale di «Verifica e invia»;
  - azioni del browser con pagina finta;
  - runner: creazione unica, esito incerto, fermata dopo due errori, archivio
    incompleto, cancellazione.
- **Frontend.** `tests/unit/ruolo-poste-dispatch-*.test.ts(x)`,
  `tests/unit/notice-solleciti-page.test.tsx` (anteprima, selezione tra lotti,
  caricamento, errori, limite di 50, permessi) e l'e2e
  `tests/e2e/ruolo-invio-solleciti.spec.ts` a 1440 e 390 px.
- **Coverage e complessità.** Il 100% su runtime nuovi e modificati e i
  risultati dei gate sono riportati in `PROGRESS_ruolo.md`, alla voce del
  2026-10-28.
