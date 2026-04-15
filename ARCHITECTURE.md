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
- `catasto-worker`
- `scanner`
- `arp-helper`

---

## 3.2 Ruolo dei servizi

### frontend
Serve la web app e consuma le API del backend.

### backend
Espone API, applica auth condivisa, coordina i moduli e usa router separati per dominio.
All'avvio esegue un bootstrap admin idempotente basato su `BOOTSTRAP_ADMIN_*`
quando la tabella `application_users` e disponibile, cosi lo stack locale
mantiene sempre un utente applicativo iniziale utilizzabile.
All'avvio riallinea anche il catalogo `sections` e i default per ruolo dei moduli
quando la tabella `sections` e disponibile, evitando `403` dovuti a nuove aree
applicative presenti nel codice ma non ancora bootstrapate nel database locale.

Moduli logici attuali:
- `accessi`
- `anagrafica`
- `utenze`
- `inventory`
- `network`
- `catasto`
- `elaborazioni` previsto come modulo operativo dedicato per i workflow esecutivi catastali
- `core`

Stato del refactor:
- `network` gia in struttura canonica sotto `app/modules/network`
- `accessi` gia instradato tramite route canoniche sotto `app/modules/accessi/routes`
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
- il backend non espone piu alias runtime sotto `/catasto`; le route operative canoniche sono solo sotto `/elaborazioni`
- gli helper tecnici condivisi tra dominio `catasto` e runtime `elaborazioni` sono stati spostati in `backend/app/modules/shared/` per evitare dipendenze inverse sul dominio
- per la sync WhiteCompany, il rilancio di una singola entity date-aware riusa il range persistito nell'ultimo `wc_sync_job` se l'utente non passa un nuovo intervallo esplicito
- ogni `wc_sync_job` persiste anche un `report_summary` finale in `params_json` con range usato, totale sorgente, contatori, durata ed eventuale preview errori, riusato dalla UI operativa
- `taken_charge` e `refuels` hanno una precondizione esplicita sulla base mezzi locale: se il run non include `vehicles` e non esistono mezzi gia sincronizzati, `POST /elaborazioni/bonifica/sync/run` rifiuta la richiesta con errore applicativo invece di lanciare import inevitabilmente inconsistenti
- la sync `vehicles` e ora idempotente anche quando il mezzo esiste gia per `plate_number` o `wc_vehicle_id`: il servizio riallinea il record esistente e isola gli errori per-record con savepoint, evitando di lasciare la sessione SQLAlchemy in `PendingRollback`
- la sync `refuels` tollera anche dettagli White orfani o non piu leggibili: se il dettaglio `GET /vehicles/refuel/edit/{id}` risponde errore HTTP perche il mezzo sorgente e stato cancellato, il record viene marcato come non importabile e contato come `skipped`, senza far fallire l'intera entity
- le entity `users` e `consorziati` usano un fetch dettagli White in concorrenza controllata e una soglia stale dedicata (`WC_SYNC_USER_DETAIL_CONCURRENCY`, `WC_SYNC_USER_STALE_JOB_MINUTES`), per evitare falsi `failed` sui job piu voluminosi del workspace `WhiteCompany Sync`
- la dashboard `Operazioni` espone ora ricerca rapida live sui pannelli `mezzi`, `attivita`, `segnalazioni` e `pratiche`: dopo 3 caratteri interroga i list endpoint esistenti con `search`, mostra i primi risultati e supporta match anche sul contenuto testuale (`notes`, `text_note`, `description`, numerazioni e riferimenti principali)
- la vista `/operazioni/mezzi` adotta ora un layout responsive dedicato: desktop con hero metriche e card del parco mezzi, mobile con lista compatta stile mini-app; il CTA di creazione resta solo visuale finche non verra cablato un vero flusso `Nuovo mezzo`
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
