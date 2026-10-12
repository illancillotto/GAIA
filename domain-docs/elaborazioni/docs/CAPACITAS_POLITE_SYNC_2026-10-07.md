# Capacitas: sincronizzazione a carico ridotto

## Profilo conservativo preparato l'8 ottobre

`config/capacitas/compose.conservative.yml` imposta almeno 5 secondi dopo
ogni risposta, una richiesta globale alla volta e una sessione irrigue.
Il tetto teorico e dodici richieste al minuto complessive, inclusi login,
redirect e keep-alive, quando tutti i processi condividono la policy.
Le pause dopo errori consecutivi diventano 5, 10, 20, 40 e poi 60 minuti;
un `Retry-After` piu lungo continua a prevalere. Gli heartbeat dei job
restano attivi durante queste pause.

L'autosync irrigue esegue prima un passaggio storico completo (`full-v1`),
anche attraverso cambi di giorno e riavvii. Al primo avvio della nuova logica
un vecchio cursore viene azzerato: i completamenti legacy potevano includere
errori e non provano che tutto lo storico sia stato acquisito. Un chunk con
errori non avanza il cursore e viene riprovato; solo `succeeded` lo avanza.
Dopo il passaggio completo, i cicli giornalieri `recent-v1:DATA` aggiornano
solo l'anno corrente e il precedente (2025 e 2026 oggi), senza cancellare
lo storico. Gli anni sono fissati nel payload del job e ricalcolati per ogni
nuovo chunk nel fuso configurato. Tutte le anagrafiche sono ancora cercate
per rilevare domande nuove, ma i dettagli degli anni precedenti non vengono
scaricati. Un anno mancante o non valido produce un errore, non un successo
silenzioso. I job manuali senza `refresh_years` restano senza filtro.

Applicare questo file come ultimo override, dopo tutti i pin e gli hotfix
esistenti, ai tre servizi. Non eseguire un deploy dal solo Compose base.
Una futura campagna separata deve ricevere gli stessi parametri e il
medesimo mount della policy; l'override riguarda solo i tre servizi elencati.

Il profilo e preparato e validato localmente, non applicato al CED:
la sessione dell'8 ottobre impedisce connessioni SSH (`Operation not permitted`).
Non avviare i recuperi sospesi per applicare questa configurazione.
Le finestre orarie e gli intervalli di refresh restano quelli gia configurati;
le sezioni successive descrivono il profilo precedente e il rilascio del 7 ottobre.

### Verifica locale della nuova logica

152 test mirati superati; statement e branch al 100% sui quattro file runtime
toccati. `make lint-backend` e Compose risolto verificati: intervallo `5`
per tutti e tre i servizi, una sessione irrigue. Ratchet sul perimetro contro
la baseline del merge-base di `origin/main` (`d6c34ba8`) senza finding;
baseline, soglie ed esclusioni non modificate. Metriche cognitive/cyclomatic/LOC:
scheduler `9/9/23 -> 6/7/23`, riconciliazione `18/13/17 -> 16/12/17`,
worker seriale irrigue `30/15/41` invariato; worker parallelo
`10/8/24 -> 12/9/25`, sotto soglia. Restano 11 error-level legacy nel
perimetro, senza incremento. Graphify backend aggiornato; estrazione semantica
docs incompleta per `Connection error` (exit 0 non indica successo).

### Consolidamento verificato del 12 ottobre

La ricevuta precedente descrive la verifica storica dell'8 ottobre; non sostituisce
i gate sul contenuto consolidato. La nuova verifica esegue 147 test, senza skip
o deselezioni: statement e branch al 100% sui quattro file runtime, senza nuove
esclusioni o sostituzioni di primitive Python per fabbricare percorsi.

Il worker inCASS nel runtime condiviso esplicita il contatore dei tentativi e
mantiene la terminazione nei percorsi gia esistenti, evitando l'uscita irraggiungibile
del precedente iteratore. Il test artificioso con `range` vuoto e sostituito dalla
verifica dello stato resume non-dict; un controtest copre tre timeout consecutivi,
pause 2/5 secondi, rollback, commit finale e chiusura di ogni sessione/DB nel medesimo
ordine. Retry, transazioni e cleanup non cambiano.

I controtest HTTP con trasporto sintetico usano parser e scraper reali: il filtro
degli anni precede le richieste dettagli e un anno invalido interrompe quelle
richieste. Nessun portale o database di produzione viene contattato. Il profilo
conservativo resta una configurazione preparata, non un deploy autorizzato da
questo consolidamento. Evidenze e gate di ammissione sono registrati in
`reports/code-quality/IRRIGUE_ADMISSION_2026-10-12.md`; la campagna resta in pausa.

## Problema e comportamento

Il 7 ottobre il batch particelle 3266 presentava 39 errori su 39 elementi,
con ripetuti errori keep-alive inVOLTURE. La campagna full recovery era ferma
dal 6 ottobre e conservava 10.542 errori discovery per sessione scaduta.
Lo stato `processing` non e sufficiente a dimostrare un sync sano.

Tutti i client creati da `CapacitasSessionManager` usano il trasporto comune
`request_policy.py`, compresi login, redirect, keep-alive e recovery.
Il lock filesystem condiviso consente una sola richiesta HTTP alla volta,
anche fra processi. Dopo il completamento della risposta attende almeno tre
secondi: al massimo circa 20 richieste/minuto, meno con latenze elevate.
La risposta viene letta e chiusa prima di rilasciare il lock. Payload, header,
status e gestione degli errori da parte dei servizi restano preservati.

Timeout, errori di trasporto, HTTP 429/5xx e risposte applicative di sessione
scaduta impongono pause di 60, 120, 240, 480 e poi 900 secondi. `Retry-After`
numerico o in formato HTTP-date puo richiedere una pausa maggiore. Non si
ripete automaticamente una richiesta nel trasporto. Il conteggio errori e
distinto per host, mentre la pausa frena tutte le richieste Capacitas.
Un successo di login, attivazione o keep-alive non azzera gli errori del
servizio; una risposta di lavoro riuscita li azzera. Le ricerche senza
risultati restano risultati validi. Un file policy corrotto blocca l'accesso,
senza ripartire a piena velocita.

I keep-alive passano da 25 a 120 secondi e rispettano lo stesso limite.
Il rinnovo login chiude il client precedente e attende la cancellazione dei
keep-alive per evitare connessioni e task residui.

## Configurazione e continuita

| Variabile | Default |
| --- | --- |
| `CAPACITAS_REQUEST_POLICY_PATH` | `/runtime-data/capacitas/request-policy.json` |
| `CAPACITAS_REQUEST_INTERVAL_SECONDS` | `3` |
| `CAPACITAS_REQUEST_COOLDOWN_SECONDS` | `60` |
| `CAPACITAS_REQUEST_MAX_COOLDOWN_SECONDS` | `900` |
| `ELABORAZIONI_CAPACITAS_PARALLEL_WORKERS` | `1` |

Backend, worker e campagna devono condividere il medesimo filesystem e path
della policy: `/opt/gaia/runtime-data` e gia montato come `/runtime-data` sul CED.
Questa coordinazione riguarda processi sul filesystem condiviso, non server
indipendenti. Il file contiene soltanto tempi e contatori per host, nessuna
credenziale o identita. Non eliminarlo per aggirare una pausa.

Il parallelismo Capacitas e indipendente dal parallelismo registry. Una corsia
domande e una corsia per gli altri job restano disponibili; il trasporto
serializza le richieste delle due corsie. Ogni job attivo riceve un heartbeat
ogni minuto anche durante il cooldown, per non essere scambiato per un worker
bloccato dalla soglia stale di 30 minuti. Gli errori del heartbeat propagano
tramite TaskGroup, invece di lasciare il job senza protezione.

Su successiva richiesta del 7 ottobre, i gate orari irrigue e inCASS vengono
disabilitati: i sync ordinari lavorano 24 ore su 24 quando esiste lavoro
eleggibile. Il tick irrigue resta un minuto e il chunk resta 100 CF. Restano
attivi pacing, cooldown, cicli giornalieri e intervalli di refresh/retry:
esaurire il lavoro eleggibile non causa ricerche continue degli stessi dati.
Cursori, manifest e dati importati restano preservati.
La stima con quattro sessioni riportata nel documento finestre descrive il
profilo precedente: non e una previsione del nuovo throughput. Misurare prima
nuovi batch sani; le pause di servizio prevalgono sul completamento veloce.

## Rollout

Preparare immagini derivate dagli attuali pin `irrigue-windows-20261007`,
copiando soltanto settings, sessione e policy nei tre servizi e runner/gate
nel worker runtime. Aggiungere l'override dopo tutti gli hotfix esistenti;
non ricreare i servizi dal solo Compose base e non aggiornare `latest`.
Attendere il termine dei job attivi prima di ricreare il runtime.
Il full recovery resta fermo: applicare la policy anche al suo backend
montato prima di una futura ripresa, mantenendo il manifest esistente.

Rollback: rimuovere soltanto l'ultimo override e ricreare con tutti gli
override precedenti. Conservare il file policy e non modificare il cursore.

## Validazione

Test della policy, delle sessioni e del runner worker con coverage statement
e branch al 100% su tutti i cinque runtime modificati. Le verifiche includono
lock concorrenti, cancellazione, timeout durante la lettura della risposta,
chiusura delle connessioni, backoff persistente, `Retry-After`, sessioni scadute,
risultati vuoti, login e heartbeat durante le pause. Suite di regressione
Capacitas: 262 test senza failure; avvisi JWT/runpy preesistenti. Verifica
finale combinata: 308 test backend (inclusi 46 policy/sessione) e 44 worker,
senza failure o skip; coverage full-file al 100% su tutti i cinque runtime.

Ratchet contro il merge-base `main`/`703f8411`: zero findings, baseline
invariata. Login passa da cognitive/cyclomatic/LOC `7/7/45` a `7/7/37`;
le metriche cognitive/cyclomatic del runner restano invariate. Nessuna nuova
violazione error-level. Ruff mirato e diff-check passano. Il primo lint-backend
globale rileva un import non ordinato nel file concorrente
`backend/tests/test_presenze_personnel_profiles_postgres.py`, estraneo a questa
modifica: non viene corretto nel cambio Capacitas.
Comando autorevole: `backend/.venv/bin/python tools/code_quality/complexity.py
ratchet --base-ref main`; lint completo: `BASE_REF=main make lint-backend
QUALITY_PYTHON=backend/.venv/bin/python`. Il controllo Ruff sui soli file
Capacitas modificati passa senza suppression aggiunte.

Graphify backend e worker aggiornati con pruning tramite i target Make.
Corpus documentale elaborazioni aggiornato con `gpt-reserve`: chunk 1/1
completato senza warning semantici (6.431 token input, 2.559 output).
Le tre immagini isolate `capacitas-polite-20261007` e il Compose completo
superano build, import smoke senza rete e verifica della configurazione.
Due container separati, senza rete esterna e con trasporti mock, condividono
un file di validazione isolato: gli ingressi HTTP sono distanziati di 3,203
secondi, includendo i 0,2 secondi della prima risposta.

## Operazioni CED

Hotfix in `/opt/gaia/hotfixes/capacitas-polite-20261007`. Il backend montato
della campagna recovery riceve anche settings, sessione e policy; gli originali
sono conservati in `originals-recovery`. La campagna resta ferma e il manifest
non viene modificato.

Il batch particelle 3267, con tutti gli elementi falliti, viene arrestato
tramite `cancel_particelle_sync_job`: terminato al confine del settimo elemento,
stato `cancelled`, dati salvati e storico conservati. Il worker riceve un
SIGTERM con attesa indefinita per il termine del batch irrigue 115, senza
SIGKILL. Il Compose completo attiva poi le tre immagini in sequenza, senza
azzerare il cursore.

Rilascio completato alle 18:05 circa del 7 ottobre: backend, scheduler e
runtime usano le immagini `capacitas-polite-20261007` e sono healthy. Il batch
115 termina `succeeded` alle 18:04:36, zero elementi falliti. Il cursore
prosegue normalmente e il nuovo job irrigue 116 parte con una sola sessione;
il job particelle 3268 e in lavorazione. Le prime richieste reali aggiornano
la policy condivisa con contatori errori zero per SSO/inVOLTURE. La credenziale
resta attiva, con zero errori consecutivi. Registry conserva quattro worker.
Il successo finale dei nuovi batch resta da misurare; non viene dedotto dallo
stato `processing` o dalla percentuale parziale mostrata dal servizio.

## Esecuzione continua

Override aggiuntivo `/opt/gaia/hotfixes/capacitas-continuous-20261007/compose.override.yml`,
applicato dopo `capacitas-polite-20261007` su backend, scheduler e runtime:
`CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_WINDOW_ENABLED=false` e
`CAPACITAS_INCASS_AUTOSYNC_WINDOW_ENABLED=false`. Le particelle erano gia
prive di un gate orario e la credenziale 1 consente tutte le ore (`0-23`).
Non occorre cambiare la finestra generale di Elaborazioni o altri servizi.

Il riavvio necessario riaccoda i job interrompibili tramite la recovery
esistente: i dati gia committati e il cursore sono mantenuti. Il blocco
irrigue in corso puo essere riletto; anche durante la ripartenza vale il
medesimo file policy condiviso, quindi non si riparte con un burst HTTP.
Il full recovery separato resta fermo. Rollback degli orari: rimuovere solo
l'override continuous e ricreare i tre servizi con tutti gli override precedenti.
