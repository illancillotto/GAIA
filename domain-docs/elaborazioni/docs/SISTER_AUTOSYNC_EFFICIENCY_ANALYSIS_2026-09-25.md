# SISTER: errori, cooldown e piano di efficienza AutoSync

Data: 25 settembre 2026. Stato: analisi e proposta, nessuna modifica runtime.

## Obiettivo e metodo

Aumentare i documenti validi acquisiti per ora di disponibilita del pool,
riducendo tentativi inutili e ritardi evitabili. Conservare correlazione certa,
ownership delle richieste remote, calendari autorizzati e protezioni di sessione.

Analisi del checkout e query PostgreSQL sul CED `gaia.lan`, in transazioni
`READ ONLY`, tra le 08:59 e le 09:03 UTC (10:59-11:03 Europe/Rome).
Configurazione letta dal container `gaia-elaborazioni-worker-visure` tramite
allowlist di sole variabili operative. Nessun login SISTER, riavvio, retry,
modifica DB o configurazione eseguito. Nessun segreto o documento personale
incluso. Gli account sono indicati con pseudonimi derivati dall'ID interno.

Per le metriche principali la finestra e 24/09 ore 09:00 UTC - 25/09 ore
09:00 UTC. Le prime query esplorative usavano le 24 ore precedenti la query;
i conteggi principali riportati sotto coincidono con la finestra fissa.
Lo stato della coda e invece una fotografia, non una coorte di 24 ore.
Il DB locale ha telemetria ferma al 21 agosto ed e escluso dalle conclusioni.

Gli hash di `sister_observability.py`, `sister_recovery_policy.py` e
`sister_worker_reliability.py` coincidono fra checkout e container CED.
Questo controllo non certifica l'identita di tutto il deployment.

## Evidenze operative

Tutti gli eventi nelle 24 ore osservate appartengono a `perpetual_sync`.

| Indicatore | Evidenza | Interpretazione |
| --- | --- | --- |
| Download riusciti | 466 eventi su 466 richieste | Circa 19,4/ora civile; non e il throughput per ora effettivamente disponibile |
| Avvii di esecuzione | 3.005 su 608 richieste | 6,45 avvii per download; rapporto di carico nella finestra, non probabilita di successo |
| Polling | 2.202 eventi su 74 richieste | Circa 29,8 poll per richiesta interessata, con forte ripetizione |
| Durata polling | Media 27,881 secondi; somma 61.395 secondi | 17,05 ore di durata aggregata dei metodi; concorrenza impedisce di leggerle come ore di fermo |
| Login | 2.712 successi, 293 errori su 182 richieste | Il wrapper osserva `ensure_authenticated`: i successi non sono necessariamente nuovi login HTTP |
| Account `dd35d5d6` | 148 errori login, zero download | 50,5% degli errori login; prima priorita diagnostica, non prova da sola di password errata |
| Altri cinque account produttivi | 84, 99, 98, 88 e 97 download | La capacita utile e distribuita; un problema non riguarda necessariamente tutto il portale |
| HTTP error | 440 eventi, tutti HTTP 501 nel campione | 362 risposte osservate e 78 eventi classificati `sister_server_error`; possono rappresentare due osservazioni dello stesso episodio |
| Cooldown credenziale | 563 eventi, attesa residua 1-174 secondi, media 81,4 | Eventi di attesa, non 563 incidenti indipendenti |
| Cooldown server | 78 eventi, 54-180 secondi, media 107,3 | Etichetta storica 500 applicata anche a 501 |

Non sommare durate di login e polling come costo totale indipendente:
possono esserci operazioni annidate e runner paralleli. Non sommare tutti
gli eventi `error` per ottenere il numero di richieste fallite.

Il batch attivo, avviato il 23 settembre alle 05:11 UTC, esponeva 1.280
righe, 1.034 completate e 225 fallite. I contatori batch e lo stato righe
possono differire durante un aggiornamento concorrente.

Le 226 richieste fallite dei batch perpetual creati dal 18 settembre,
nella lettura successiva, sono:

| Famiglia del messaggio persistito | Richieste |
| --- | ---: |
| `SISTER login failed` | 168 |
| `Submit visura non avanzato` | 38 |
| Tentativi esauriti | 15 |
| CAPTCHA non risolto | 3 |
| Altri casi | 2 |

Il totale passa da 225 a 226: la coda continua a cambiare durante
l'audit. Non attribuire tutti questi fallimenti alle ultime 24 ore.
Nella prima lettura 197 fallimenti erano privi di `last_error_code`:
la classificazione dipende ancora troppo dal testo del messaggio.

La campagna persistente contieneva 12.571 completate, 3.678 fallite,
406.577 pending e 20 queued. Il pending si ripartisce in 73.719 particelle
a ruolo, 12.349 soggetti a ruolo, 287.387 particelle consortili e 33.122
soggetti anagrafici. Non equivale a lavoro immediatamente eleggibile.

## Calendari e stallo apparente del mattino

Alle 09:00 UTC risultano 19 richieste remote `pending` con retry scaduto
fra 05:25 e 05:35 UTC, legate a cinque account. I rispettivi profili AutoSync
del venerdi prevedono 15:00-07:30 Europe/Rome. Quindi alle 11:00 locali
questi account sono fuori fascia: la scadenza del retry non autorizza il poll.

L'account `dd35d5d6` ha invece fascia 08:00-07:30, che attraversa la notte
e copre 23 ore e 30 minuti. E abilitato sia globalmente sia in AutoSync.
Da verificare con il responsabile se questa estensione sia intenzionale.
Tra 06:00 e 09:00 UTC si osservano 43 errori login, zero poll e zero download.
Il batch non e fermo in senso assoluto: prosegue lavoro senza rendimento.

Il planner risulta abilitato, con entrambe le priorita attive, `batch_size=20`
e ultimo tick persistito alle 08:54:50 UTC. Il singolo snapshot non prova un
arresto dello scheduler. Il codice attuale permette gia refill nello stesso
batch solo sotto condizioni conservative: recuperi certi, retry futuro,
assenza di claim/CAPTCHA e rispetto del cap. I recuperi ormai dovuti e
vincolati ad account fuori fascia meritano una verifica specifica di eleggibilita.

## Mappa delle attese

| Livello / causa | Default checkout | Produzione osservata | Effetto |
| --- | --- | --- | --- |
| Lock/sessione e altri recuperabili | 300 s | 180 s | Sospende la credenziale |
| Retry richiesta recuperabile | 45 s | 27 s | Persistito in `retry_not_before`; da solo non supera il cooldown credenziale |
| Errori server consecutivi | 90, 180, 300 s, cap 300 | 54, 108, 180 s, cap 180 | Backoff per credenziale; richiesta differita per il massimo fra retry base e cooldown |
| Pausa globale runtime batch | 45 s | 27 s | Aperta quando tutte le credenziali considerate sono in cooldown; non e un circuito distribuito persistente |
| Poll recupero remoto | 5 minuti | Codice recovery identico al CED | Stessa richiesta remota, senza nuovo submit |
| Budget richiesta ordinaria | 5 tentativi | 50 tentativi | Non e il budget dei poll remoti; alza molto il possibile lavoro su errori ripetitivi |
| Recupero remoto | 24 ore dal primo invio | Codice recovery identico al CED | Scadenza assoluta, non sospesa dalle fasce; primo invio ignoto richiede revisione |
| Retry campagna perpetual | 15 minuti senza codice; 6 ore con codice | Regola del checkout da verificare nel backend distribuito | Moltiplicatore esponenziale; stop a 3 tentativi, salvo protezione della richiesta originale |
| Retry campagna Ruolo legacy | 5 minuti | Regola del checkout | `blocked_runtime` resta all'operatore; percorso distinto dal perpetual attivo |
| Intervallo fra visure | 5 s | 5 s | Pacing ordinario, non cooldown d'errore |
| CAPTCHA manuale | 300 s | 900 s | Attesa di intervento, non indisponibilita generale del portale |
| Planner / materializzazione | 1 minuto / 15 minuti | Cadenze previste dal sistema | Non confondere attesa scheduler con retry della richiesta |

I vincoli non si sommano meccanicamente: l'esecuzione riparte quando sono
soddisfatti retry, cooldown, fascia e lease. Una richiesta dovuta puo quindi
aspettare ore per il calendario. Cooldown e contatori server del runtime batch
sono in memoria; il retry della richiesta e persistito. Un riavvio non e una
strategia di ottimizzazione e non conserva necessariamente tutta la memoria
degli incidenti.

## Classificazione degli errori e criticita

1. **Login/sessione.** Il messaggio esterno `SISTER login failed` avvolge
   eccezioni diverse. La policy recuperabile riconosce tipi e marker specifici;
   non ogni errore avvolto e automaticamente recuperabile. Il rifiuto esplicito
   ha gia isolamento della credenziale nel pool del batch. Servono causa
   strutturata e diagnosi dell'account concentratore prima di cambiare retry.
2. **HTTP 501.** La logica riconosce un caso non bloccante su
   `/portale-rest/rs/initPortale` solo dopo validazione della pagina. La semplice
   presenza di 501 nella telemetria non dimostra indisponibilita del servizio.
   Non ignorare globalmente il 501; distinguere risposta, impatto sul flusso
   e transizione di stato.
3. **Documento non pronto.** Il wrapper telemetry marca qualsiasi eccezione
   del polling come errore. I 2.202 eventi non dimostrano 2.202 guasti HTTP:
   una parte puo essere attesa funzionale. La telemetria attuale non permette
   di quantificare precisamente tale parte.
4. **Submit non avanzato.** Esistono 38 fallimenti nel campione di batch:
   possono coinvolgere validazione form, sezione catastale, navigazione o
   sessione. Consultare artifact e causa originale prima di riprovare.
5. **Correlazione/PDF.** La policy recuperabile comprende timeout,
   `SisterRequestCorrelationError` e documento invalido. Applicare lo stesso
   cooldown credenziale a tutti puo penalizzare account sani per problemi della
   singola richiesta; occorre distinguere errore di account, portale e documento.
6. **Budget non allineati.** 50 tentativi ordinari del worker e massimo 3
   della campagna sono livelli diversi. La campagna usa anche il contatore
   richieste nella riconciliazione: non presumere 50 per 3 tentativi disponibili.
   Verificare la transizione terminale prima di modificare una soglia.

## Interventi proposti, in ordine

| Priorita | Intervento da progettare | Evidenza attesa / criterio di accettazione |
| --- | --- | --- |
| P0 | Diagnosi account `dd35d5d6`: errore radice, pagina finale, profilo, lease, calendario | Causa documentata dei 148 errori; scelta esplicita su fascia 08:00-07:30 e disponibilita; nessuna rotazione automatica delle password |
| P0 | Tassonomia errori e attese | Codici distinti per login rifiutato, sessione occupata, timeout navigazione, validazione form, pending remoto, HTTP bloccante, correlazione e PDF; causa originale conservata |
| P1 | Stato effettivo di eleggibilita | UI/monitor espongono motivo dominante e prossimo istante utile per ciascun runner/richiesta; distinguono fuori fascia da cooldown e portale fermo |
| P1 | Policy di isolamento per account con errori consecutivi | Circuito con pausa e singola prova di recupero, persistito e verificabile; non continuare su nuove righe con lo stesso errore di login; budget scelto su misure |
| P1 | Recupero remoto proporzionato all'eta | Valutare polling adattivo con jitter, cap e priorita prossima alla deadline; diminuire i poll inutili senza peggiorare il tempo di acquisizione o perdere recuperi |
| P1 | Refill consapevole di calendario e richieste vincolate | Verificare il caso 19 recuperi dovuti ma fuori fascia; mantenere cap, lock, precedenza recuperi e assenza di doppio submit; non ampliare implicitamente le fasce |
| P2 | Fine fascia e nuovi invii | Valutare margine prima della chiusura per ridurre invii che restano fermi fino alla fascia successiva; durata ricavata dai tempi reali di disponibilita |
| P2 | Separare budget di invio, autenticazione e recupero | Contatori espliciti; recuperi senza nuovo submit; scadenza 24h immutata salvo decisione funzionale separata |
| P2 | Distribuzione capacita fra fasi | Misurare attesa dei soggetti a ruolo: l'ordine rigido delle particelle puo ritardarli a lungo; qualsiasi quota fra fasi richiede scelta di priorita di business |

Non proporre come primo passo un'ulteriore riduzione generalizzata dei cooldown:
in produzione sono gia ridotti del 40% rispetto ai default principali, mentre
il budget ordinario e dieci volte il default. La priorita e evitare lavoro
improduttivo e identificare le cause, poi calibrare le durate.

## Misurazione e rollout da definire

- Baseline di almeno 7 giorni comprendente fasce diurne/notturne: PDF validi
  e richieste uniche, esiti terminali, poll per documento, autentiche nuove
  sessioni per documento, p50/p95 fra primo invio e download, errori per account.
- Denominatore operativo: ore-account disponibili secondo fascia e lease,
  non solo 24 ore civili. Separare salute del portale, disponibilita del pool
  e tempo speso a recuperare richieste gia inviate.
- Registrare inizio/fine e causa delle attese. I residui ripetuti di cooldown
  non vanno sommati per misurare il tempo perso; ricostruire intervalli e unioni.
- Prima sperimentazione limitata a un cambiamento di policy per volta,
  mantenendo un periodo comparabile. Obiettivo candidato: -30% poll per PDF
  con throughput per ora-account non inferiore alla baseline e p95 entro +10%.
  Sono soglie proposte, non risultati raggiunti o SLA approvati.
- Vincoli di accettazione: zero reinvii di richieste remote note, zero download
  associati per somiglianza, zero violazioni di lease/calendario/ownership,
  nessuna crescita dei casi scaduti senza spiegazione.
- Interrompere l'esperimento e ripristinare la policy precedente se peggiorano
  lock/sessioni, deadline mancate o integrita documentale. Conservare richieste
  e scadenze originali durante il rollback.

## Fonti e prossima decisione

Fonti dati: `sister_portal_events`, `catasto_batches`,
`catasto_visure_requests`, `catasto_perpetual_sync_items`,
`catasto_ruolo_autosync_config` e flag attivo di `catasto_credentials`.
Finestre e filtri sono esplicitati sopra per ripetere le aggregazioni.

Riferimenti runtime:

- `modules/elaborazioni/worker/worker.py`: configurazione, `_SisterBatchRuntime`,
  `_defer_recoverable_error`, `_register_server_error`, `_wait_for_runtime_window`.
- `modules/elaborazioni/worker/sister_worker_reliability.py`:
  `is_recoverable_credential_error`, coordinatore retry e claim.
- `modules/elaborazioni/worker/sister_recovery_policy.py` e
  `backend/app/modules/elaborazioni/sister_recovery_contract.py`: budget e deadline.
- `modules/elaborazioni/worker/sister_observability.py`: wrapper eventi e durate.
- `modules/elaborazioni/worker/sister_browser_reliability.py`: valutazione 5xx/501.
- `modules/elaborazioni/worker/sister_credential_pool.py`: lease e quarantena.
- `backend/app/services/elaborazioni_perpetual_sync.py` e
  `elaborazioni_ruolo_autosync.py`: riconciliazione, budget, refill e calendari.

Documenti collegati: [sincronizzazione continua](CATASTO_CONTINUOUS_SYNC.md),
[runbook SISTER](SISTER_debug_runbook.md),
[audit stallo del 6 settembre](SISTER_DOWNLOAD_STALL_DEBUG_2026-09-06.md).
L'audit storico descrive problemi successivamente corretti: non e prova che
quei difetti siano ancora presenti oggi.

Prossima decisione proposta: validare diagnosi e calendario dell'account con
zero resa, quindi definire tassonomia e metriche prima di intervenire su
cooldown e frequenza del polling. Restano da analizzare gli artifact degli
errori login/submit, le lease live e l'effettiva distribuzione dei tempi di
produzione remota. Questo documento non autorizza automaticamente cambi di
configurazione o comportamento.
