# ARCHITECTURE.md

# GAIA
## Architettura del sistema

> Regola repository
> Il backend GAIA e un monolite modulare. Nuovo codice backend di dominio va creato in `backend/app/modules/<modulo>/`.
> I path legacy fuori da `app/modules/` sono compatibilita temporanea e non sono piu destinazione primaria per nuove feature.

## 1. Scopo

La piattaforma **GAIA** e una web application interna progettata per:

- acquisire dal NAS Synology utenti, gruppi, cartelle condivise e ACL
- calcolare i permessi effettivi per utente e cartella
- consentire consultazione e revisione degli accessi
- supportare i capi servizio nella validazione
- produrre report per audit e bonifica
- monitorare la rete LAN
- gestire un inventario IT condiviso con il monitoraggio di rete
- integrare automazioni catastali dedicate
- governare layer GIS trasversali con PostGIS come fonte ufficiale, QGIS come
  client tecnico e NAS shapefile come backup/export versionato
- gestire anagrafiche soggetti e documenti correlati

Il sistema, nel MVP, è **read-only rispetto al NAS**:
- legge
- analizza
- normalizza
- mostra
- esporta

Non modifica automaticamente i permessi del NAS.

---

## 2. Architettura logica

Il sistema e composto da questi macro-componenti:

### 2.1 Frontend
Interfaccia web per:
- login
- consultazione dashboard
- navigazione utenti/cartelle
- revisione accessi
- export report

Tecnologie:
- Next.js
- React
- TailwindCSS
- TanStack Table

Path repository:
- `frontend/`

---

### 2.2 Backend API
Espone API REST per tutti i moduli applicativi.

Tecnologie:
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- Paramiko
- python-nmap
- APScheduler

Modello architetturale:
- **monolite modulare**
- un solo servizio backend
- un solo database
- moduli logici separati nel codice

Il modulo trasversale `gis` vive in `backend/app/modules/gis` e governa
catalogo, permessi layer, annotazioni, change request, export metadata e audit.
Il catalogo operativo e disponibile in frontend su `/gis/catalogo`, con pannello
permessi per i layer gestibili e pannello annotazioni governate per layer
visibili. Lo stesso catalogo espone il pannello change request per proporre,
revisionare e applicare in modalita no-op modifiche non ancora scritte sui layer
ufficiali. La governance QGIS Desktop e pubblicata da `/gis/qgis/governance`
come policy SQL admin-only per ruoli DB, view read-only e profili edit
controllati. Nel frontend `GIS Platform` e pubblicato in home e nel module
switcher/sidebar come modulo autonomo `gis`; per compatibilita con profili gia
esistenti, il gating UI accetta temporaneamente anche utenti con modulo
`catasto`, mentre le API continuano a filtrare i layer tramite permessi GIS.
Non sostituisce il GIS Catasto esistente: `/catasto/gis` resta il workspace di
dominio per popup, search, WFS AdE, selezioni e logiche Catasto. Il confine
completo e descritto in `docs/GIS_PLATFORM_ARCHITECTURE.md`.

Struttura interna canonica:

```text
backend/app/
  modules/
    core/
    accessi/
    anagrafica/
    utenze/
    network/
    inventory/
    catasto/
    elaborazioni/
    inaz/
    organigramma/
```

Nota:
- la directory fisica del backend e `backend/`
- il backend non rappresenta piu il solo modulo Accessi
- per il dominio anagrafico possono coesistere namespace runtime `anagrafica` e `utenze`

---

### 2.3 Database
Persistenza di:
- utenti applicativi
- utenti NAS
- gruppi NAS
- shared folder
- ACL raw
- permessi normalizzati
- permessi effettivi
- review
- snapshot

Tecnologia:
- PostgreSQL

---

### 2.4 Worker e servizi specializzati

#### NAS Connector
Modulo backend dedicato alla connessione SSH verso il NAS Synology.

Responsabilità:
- esecuzione comandi
- recupero dati raw
- gestione timeout/errori
- parsing output

Canali previsti:
- SSH
- comandi di sistema Synology/Linux

#### Network Scanner
Container separato dedicato alla scansione read-only della LAN.

Responsabilita:
- ping scan
- port scan sugli host attivi
- fallback ARP scan con scapy
- schedulazione periodica

#### Catasto Worker
Container separato per le automazioni browser-based del modulo Catasto.

Responsabilita runtime attuali:
- login, session recovery e navigazione SISTER
- flusso visure per immobile
- flusso visure per soggetto PF/PNF
- gestione CAPTCHA OCR, esterno e manuale
- produzione artifact diagnostici per richiesta
- produzione report batch JSON/Markdown

---

## 3. Architettura fisica

## 3.1 Servizi containerizzati

L’applicazione gira tramite Docker Compose con questi servizi:

- `frontend`
- `backend`
- `postgres`
- `nginx`
- `elaborazioni-worker-visure`
- `elaborazioni-worker-runtime`
- `elaborazioni-worker-autodoc`
- `scanner`
- `arp-helper`

### Flussi operativi CED <-> locale

Per l'ambiente CED il repository adotta come default una strategia Git-based con build remota:

- le modifiche applicative vengono prima committate in locale e pushate sull'upstream della branch corrente
- il deploy applicativo esegue `git pull --ff-only` sul server CED e verifica che lo SHA remoto coincida con lo SHA locale richiesto
- le immagini Docker vengono buildate direttamente sul server CED, riusando la cache remota ed evitando il trasferimento completo delle immagini via SSH/SCP
- il file env runtime remoto viene riallineato a partire dal file locale scelto per il deploy
- lo stack viene rilanciato con `docker compose up -d --no-build` dopo la build remota
- la modalita legacy `DEPLOY_BUILD_MODE=archive` resta disponibile come fallback: build locale, trasferimento artefatti via SSH/SCP, `docker load` remoto e rilancio dello stack

Per il database sono previsti due flussi separati:

- `push-local-db-to-ced.sh`: restore distruttivo del DB locale sul server CED
- `pull-ced-db-to-local.sh`: restore distruttivo del DB CED in locale
- `pull-ced-db-to-local-slim.sh`: sync mirata dal CED al locale solo per tabelle operative cambiate

La sync slim non effettua merge applicativo; il livello di consistenza e tabellare:

- confronto tramite firme lightweight remoto/locale
- dump remoto `data-only` delle tabelle cambiate
- `TRUNCATE ... CASCADE` locale e restore dei soli dati di quelle tabelle

Questo approccio evita di trasferire in locale i dataset bulk piu pesanti quando servono soprattutto:

- utenti e permessi applicativi
- configurazioni credenziali
- job, run, selection e metadati operativi

---

## 3.2 Ruolo dei servizi

### frontend
Serve la web app e consuma le API del backend.
Nel `docker-compose.yml` il build del frontend usa temporaneamente `network: host`
per il solo stage di build, per mitigare errori DNS del builder Docker osservati
su fetch NPM verso `registry.npmjs.org`; a regime il fix va spostato sulla
configurazione DNS del daemon Docker host, cosi da ripristinare un build Compose
portabile senza dipendenze dal networking host.

### backend
Espone API, applica auth condivisa, coordina i moduli e usa router separati per dominio.
All'avvio esegue un bootstrap admin idempotente basato su `BOOTSTRAP_ADMIN_*`
quando la tabella `application_users` e disponibile, cosi lo stack locale
mantiene sempre un utente applicativo iniziale utilizzabile.
All'avvio riallinea anche il catalogo `sections` e i default per ruolo dei moduli
quando la tabella `sections` e disponibile, evitando `403` dovuti a nuove aree
applicative presenti nel codice ma non ancora bootstrapate nel database locale.
I job monitorabili non vengono piu eseguiti nel processo web: le API
creano o riaccodano record persistenti e i container tecnici dedicati
li prelevano dal database, isolando le elaborazioni massive dai worker Uvicorn.
La separazione minima corrente e:

### Presenza utenti GAIA
Per il monitoraggio applicativo degli utenti autenticati e stato introdotto un meccanismo MVP di presenza basato su heartbeat:

- il frontend invia un heartbeat autenticato all'apertura pagina, ai cambi route, su alcune azioni funzionali esplicite e ogni 60 secondi
- il backend aggiorna una singola riga `user_presence` per utente con `last_seen_at`, `last_path`, `last_route_label`, `last_module_key`, `last_action_label`, piccola history di route/azioni recenti e stato visibile/nascosto della scheda
- la home admin espone il widget "attivi negli ultimi 15 minuti"
- la pagina admin `/gaia/users/attivita` mostra elenco utenti recenti, ultimo modulo/pagina visitato e ultima azione applicativa rilevata

Vincolo esplicito:
- questa vista rappresenta attivita recente applicativa, non "online reale" in senso websocket o session-presence server-side
- `elaborazioni-worker-visure`: test connessione SISTER, run AdE, bulk search catastali e batch visure
- `elaborazioni-worker-runtime`: job Capacitas e import REGISTRY
- `elaborazioni-worker-autodoc`: sync massiva AUTODOC mezzi

Moduli logici attuali:
- `accessi`
- `anagrafica`
- `utenze`
- `inventory`
- `network`
- `catasto`
- `inaz`
- `organigramma`
- `elaborazioni` previsto come modulo operativo dedicato per i workflow esecutivi catastali
- `core`

Pattern runtime rilevanti introdotti nei moduli operativi:
- le dashboard ad alto volume non devono ricostruire KPI scaricando tutte le righe raw nel browser; devono preferire endpoint di summary lato backend
- le liste mensili di dettaglio devono supportare payload "light" con campi minimi per la griglia e demandare i dettagli pesanti a fetch lazy sul record selezionato
- le route lista che possono includere collezioni figlie, come timbrature o eventi, devono prevedere flag espliciti tipo `include_*` per evitare payload e query inutili

Caso applicato nel modulo `presenze`:
- `/presenze/dashboard/summary` calcola lato backend i KPI del mese usati dalla dashboard `frontend/src/app/presenze/page.tsx`
- `/presenze/giornaliere` supporta `include_punches=false` per il caricamento della matrice mensile
- il dettaglio completo della singola giornata viene caricato on demand tramite `GET /presenze/giornaliere/{record_id}`
- il backend pre-carica le timbrature in bulk solo quando richiesto, evitando query N+1 in serializzazione

Evoluzione pianificata di navigazione:

- `GAIA NAS Control` e `GAIA Rete` convergeranno in un entrypoint frontend comune `GAIA CED`
- nella prima fase `CED` sara un contenitore UI e di navigazione, non un nuovo backend dedicato
- i backend e i permessi restano separati tra `accessi` e `network`

Stato del refactor:
- `network` gia in struttura canonica sotto `app/modules/network`
- `accessi` gia instradato tramite route canoniche sotto `app/modules/accessi/routes`

Regola runtime per job monitorabili:
- tutti i processi lunghi con stato esposto al frontend devono essere implementati preferibilmente tramite coda persistente presa in carico da worker dedicato, o come runtime task tracciati solo quando il carico e compatibile con il processo API
- ogni nuovo worker deve essere dedicato a una sola famiglia di job coerente; non sono ammessi nuovi worker multi-queue che mischiano domini o runtime eterogenei nello stesso loop di polling
- evitare `BackgroundTasks` usati come scheduler principale per job di lunga durata e thread daemon non tracciati, perche dopo restart o riciclo del processo possono lasciare job in stato intermedio senza recovery
- ogni job monitorabile deve prevedere almeno:
  - persistenza progressiva dello stato su DB
  - cleanup degli orfani/stale job dopo restart backend o timeout di inattivita
  - semantica chiara tra interruzione del monitor frontend e prosecuzione del task backend
- `accessi` con entrypoint canonici di modulo per route, modelli, schemi e servizi
- `inventory` presente nel monolite condiviso come modulo dedicato
- il dominio anagrafico espone ancora superfici `anagrafica` e `utenze` per compatibilita
- `catasto` con route implementation canonica e surface di modulo
- `elaborazioni` introdotto come nuovo namespace di transizione per i workflow runtime
- `catasto` mantiene progressivamente le sole superfici di dominio, documenti e provider
- `elaborazioni` centralizza batch, richieste singole, credenziali runtime, CAPTCHA e WebSocket operativi
- il runtime `elaborazioni` supporta richieste visure tipizzate `immobile` e `soggetto`
- il runtime distingue esiti terminali `completed`, `failed`, `skipped` e `not_found`
- il service layer operativo associato al dominio catastale sta convergendo su moduli `app/services/elaborazioni_*` con shim legacy `catasto_*`
- il frontend sta convergendo su route canoniche `frontend/src/app/elaborazioni/*` per la parte operativa, lasciando `catasto` come area dati e provider
- per evitare refactor distruttivi su DB e payload, il linguaggio del modulo runtime usa alias `Elaborazione*` sopra i model e gli schema legacy `catasto_*`
- lo stesso criterio e applicato al layer UI con namespace dedicato `frontend/src/components/elaborazioni/*`
- il dettaglio batch runtime, i componenti UI di base e i workspace operativi principali sono ora implementati direttamente sotto `elaborazioni`
- standard UI: le modal di primo livello che aprono workspace o schede complete devono usare un formato largo condiviso (`z-[70]`, overlay `bg-black/45` con `backdrop-blur-sm`, container `max-w-[min(1600px,98vw)]`, `max-h-[95vh]`, `rounded-[28px]`, bordo chiaro e canvas interno `bg-[#f4f7f5]`) per mantenere coerenza cross-modulo tra `utenze`, `catasto`, `ruolo` ed `elaborazioni`
- il dominio `utenze` usa anche un job schedulato ANPR con stato persistito su DB (`anpr_job_runs`, `anpr_check_log`): la coda e filtrata sui soli soggetti `a ruolo` dell'anno operativo, con hard cap giornaliero da `.env`, retry dei `not_found_anpr` governato da configurazione temporale e KPI sintetici esposti nella dashboard utenze
- il monitor operativo di questo job vive anche nel modulo `elaborazioni` tramite route dedicata frontend `/elaborazioni/anpr` e summary backend `/elaborazioni/utenze-anpr/summary`, cosi il tracciamento esecutivo resta nel workspace dei job; il summary espone sia le ultime esecuzioni dettagliabili sia i totali storici delle operazioni ANPR
- il backend non espone piu alias runtime sotto `/catasto`; le route operative canoniche sono solo sotto `/elaborazioni`
- gli helper tecnici condivisi tra dominio `catasto` e runtime `elaborazioni` sono stati spostati in `backend/app/modules/shared/` per evitare dipendenze inverse sul dominio
- per la sync WhiteCompany, il rilancio di una singola entity date-aware riusa il range persistito nell'ultimo `wc_sync_job` se l'utente non passa un nuovo intervallo esplicito
- ogni `wc_sync_job` persiste anche un `report_summary` finale in `params_json` con range usato, totale sorgente, contatori, durata ed eventuale preview errori, riusato dalla UI operativa
- `taken_charge` e `refuels` hanno una precondizione esplicita sulla base mezzi locale: se il run non include `vehicles` e non esistono mezzi gia sincronizzati, `POST /elaborazioni/bonifica/sync/run` rifiuta la richiesta con errore applicativo invece di lanciare import inevitabilmente inconsistenti
- la sync `vehicles` e ora idempotente anche quando il mezzo esiste gia per `plate_number` o `wc_vehicle_id`: il servizio riallinea il record esistente e isola gli errori per-record con savepoint, evitando di lasciare la sessione SQLAlchemy in `PendingRollback`
- la sync `refuels` usa ora una risoluzione per-mezzo: parte dai mezzi locali, interroga `GET /vehicles/search` per ottenere l'id White da passare come `filter_code[]` e legge la datatable filtrata del registro rifornimenti, evitando il fetch massivo di dettagli `edit/{id}` che mandava il job in stale
- la sync `refuels` WhiteCompany salva ora gli eventi operativi in `wc_refuel_event` anche quando il provider non espone `liters/total_cost/station_name`; i dettagli economici restano completati dall'import Excel `Transazioni flotte`, che usa `Identificativo -> fuel_card.codice` e la storia `fuel_card_assignment_history` per riconciliare carta, operatore e rifornimento WhiteCompany senza assumere che la carta resti sempre allo stesso driver
- le entity `users` e `consorziati` usano un fetch dettagli White in concorrenza controllata e una soglia stale dedicata (`WC_SYNC_USER_DETAIL_CONCURRENCY`, `WC_SYNC_USER_STALE_JOB_MINUTES`), per evitare falsi `failed` sui job piu voluminosi del workspace `WhiteCompany Sync`; il runtime utenti e ora role-based: `users` interroga solo i ruoli WhiteCompany configurati (`WC_SYNC_USERS_ROLE_IDS`) invece del full scan globale, `consorziati` usa il ruolo dedicato (`WC_SYNC_CONSORZIATI_ROLE_ID`), con deduplica per `wc_id`, tuning di default a `16` richieste dettaglio concorrenti, stale timeout `360` minuti e delay ridotti (`WC_SYNC_REQUEST_DELAY_MS=100`, `WC_SYNC_DETAIL_DELAY_MS=25`) per gestire meglio i volumi >10k utenti
- i job `wc_sync_job` rimasti `running` dopo un restart del backend vengono marcati automaticamente come `failed` alla prima lettura di `sync/status` o a un nuovo `sync/run`, con dettaglio esplicito di job orfano, cosi il workspace frontend riabilita subito l'azione `Rilancia` senza attendere la soglia stale
- la dashboard `Operazioni` espone ora ricerca rapida live sui pannelli `mezzi`, `attivita`, `segnalazioni` e `pratiche`: dopo 3 caratteri interroga i list endpoint esistenti con `search`, mostra i primi risultati e supporta match anche sul contenuto testuale (`notes`, `text_note`, `description`, numerazioni e riferimenti principali)
- la vista `/operazioni/mezzi` adotta ora un layout responsive dedicato: desktop con hero metriche e card del parco mezzi, mobile con lista compatta stile mini-app; il CTA di creazione resta solo visuale finche non verra cablato un vero flusso `Nuovo mezzo`
- la hero di `/operazioni/mezzi` ospita anche il CTA `Importa transazioni flotte`, che apre la modale di upload `.xlsx` per completare i `vehicle_fuel_log` da file Excel quando WhiteCompany non espone i dettagli economici del rifornimento
- il workspace `/elaborazioni` ospita anche il pannello operativo `AUTODOC mezzi`: legge l'ultimo job `autodoc_vehicle_details`, lo inserisce nel riepilogo `Operazioni in corso` quando e `queued/running` e permette il lancio delle modalita `sync completa` o `solo URL noti` senza uscire dal dashboard elaborazioni
- roadmap piattaforma: e pianificata la convergenza delle superfici frontend `nas-control` e `network` nel nuovo namespace `ced`, con target `/ced/nas/*` e `/ced/rete/*`, lasciando inizialmente invariati router backend, modelli permessi e cataloghi sezione
- refactor pianificato: `catasto` evolve verso aggregazione dati, `elaborazioni` diventa il modulo runtime per batch, CAPTCHA, worker orchestration e stato avanzamento

### postgres
Salva i dati persistenti della piattaforma.

### nginx
Fa da reverse proxy:
- instrada traffico frontend
- proxy API backend
- gestisce headers e timeouts

### scanner
Esegue la scansione LAN del modulo GAIA Rete e persiste snapshot, dispositivi e alert.

### arp-helper
Servizio tecnico host-side di supporto al modulo Rete per recuperare informazioni
ARP quando i container non vedono direttamente la neighbor table dell'host.

---

## 4. Flusso dati principale

## 4.1 Sync NAS

1. l’admin avvia una sincronizzazione
2. il backend crea uno snapshot
3. il NAS connector si collega via SSH
4. esegue comandi per utenti, gruppi, membership, shared folders, ACL
5. salva il dato raw
6. normalizza il dato
7. calcola i permessi effettivi
8. chiude lo snapshot

---

## 4.2 Consultazione

1. l’utente applicativo effettua login
2. il frontend richiama le API
3. il backend legge dal database
4. la UI mostra dati filtrabili e paginati

---

## 4.3 Review

1. il reviewer consulta i permessi del proprio ambito
2. seleziona utente/cartella
3. inserisce decisione e nota
4. il backend salva la review
5. il sistema mantiene lo storico decisionale

---

## 4.4 Export

1. l’utente applicativo seleziona filtri
2. il frontend richiama endpoint export
3. il backend genera CSV/XLSX
4. il file viene scaricato

---

## 5. Modello di dominio

## 5.1 Entità applicative

### ApplicationUser
Utenti che accedono alla piattaforma.

Ruoli:
- admin
- reviewer
- viewer

---

## 5.2 Entità NAS

### NasUser
Utente presente sul NAS.

### NasGroup
Gruppo presente sul NAS.

### NasUserGroup
Relazione utente-gruppo.

### Share
Cartella condivisa del NAS.

---

## 5.3 Entità di audit

### Snapshot
Fotografia di una sincronizzazione.

### RawAclEntry
Contiene il testo raw delle ACL recuperate dal NAS.

### PermissionEntry
Permesso normalizzato derivato dal parsing ACL.

### EffectivePermission
Permesso finale calcolato per utente-cartella.

### Review
Decisione di validazione registrata da un reviewer/admin.

### NetworkScan
Snapshot di rete generato dal modulo GAIA Rete.

### NetworkDevice
Dispositivo rilevato in scansione LAN.

### NetworkAlert
Evento operativo generato da variazioni o anomalie di rete.

### FloorPlan
Planimetria associata a sede/piano.

---

## 6. Regole di business

## 6.1 Origine dei permessi
I permessi possono derivare da:
- assegnazione diretta all’utente
- assegnazione ai gruppi di appartenenza

---

## 6.2 Priorità
Ordine logico di priorità:
1. deny
2. allow diretto utente
3. allow da gruppo

---

## 6.3 Regole di semplificazione MVP
Per il MVP:
- `write` implica `read`
- il sistema deve produrre una `source_summary`
- il sistema deve salvare `details_json` per debugging
- se l’ACL non è perfettamente interpretabile, salvare warning ma non interrompere tutta la sync

---

## 7. Sicurezza applicativa

## 7.1 Access control
L’accesso alla piattaforma è consentito solo ad utenti autenticati.

Ruoli:
- **admin**: pieno accesso
- **reviewer**: consultazione + review
- **viewer**: sola consultazione

---

## 7.2 Autenticazione
Metodo:
- login con username/email e password
- JWT access token

---

## 7.3 Sicurezza operativa
Linee guida:
- accesso consigliato solo da LAN o VPN
- nessun segreto nel codice
- password hashate
- env separati
- logging delle operazioni critiche

---

## 8. Logging e osservabilità

Eventi da loggare:
- login riusciti/falliti
- avvio sync
- esito sync
- parsing warning
- export
- review create/aggiornate
- errori SSH
- errori applicativi

---

## 9. Scelte architetturali principali

## 9.1 Monorepo
Scelta:
- backend e frontend nello stesso repository

Motivazioni:
- maggiore coerenza
- documentazione unica
- docker compose centrale
- avvio più semplice del MVP

---

## 9.2 Snapshot-based audit
Scelta:
- lavorare su snapshot e non su sola lettura volatile

Motivazioni:
- confrontabilità nel tempo
- reporting storico
- revisione riferita a una fotografia precisa

---

## 9.3 Read-only NAS nel MVP
Scelta:
- nessuna modifica automatica dei permessi

Motivazioni:
- ridurre rischio operativo
- evitare danni su ambiente legacy
- favorire prima la comprensione e la validazione

---

## 10. Limiti del MVP

- non gestisce provisioning utenti
- non modifica ACL sul NAS
- non integra Active Directory
- non garantisce pieno supporto a tutte le casistiche ACL complesse Synology senza adattamento sul campo
- non include workflow approvativo enterprise avanzato

---

## 11. Evoluzioni future

Possibili estensioni:
- proposta automatica di bonifica accessi
- applicazione controllata delle modifiche
- integrazione LDAP/AD
- audit automatici schedulati
- notifiche anomalie
- diff tra snapshot
- dashboard compliance per settore

---

## 12. Diagramma testuale ad alto livello

    ```text
    [ Browser Utente ]
            |
            v
    [ Frontend Next.js ]
            |
            v
    [ Nginx Reverse Proxy ]
            |
            +-----------------------> [ Backend FastAPI ] -----------------------> [ PostgreSQL ]
                                            |
                                            |
                                            v
                                    [ NAS Connector via SSH ]
                                            |
                                            v
                                    [ Synology NAS ]

13. Repository structure
    GAIA/
    ├── README.md
    ├── docker-compose.yml
    ├── docker-compose.override.yml
    ├── modules/
    │   ├── accessi/
    │   │   ├── backend/
    │   │   ├── frontend/
    │   │   └── docs/
    │   ├── network/
    │   └── inventory/
    ├── nginx/
    ├── scripts/
    └── .github/
