# IMPLEMENTATION_PLAN.md

# NAS Access Audit Platform
## Piano di implementazione

## Ciclo MCP LAN e PKI — 2026-10-06

Consolidamento live 2026-10-07: completate matrice funzionalita/test,
verifiche failure/edge case, frontend regressione e build isolata.
Chiusura del quality gate globale non completata: lint legacy e finding
ratchet nelle modifiche concorrenti; nessun deploy o commit. Progress:
`domain-docs/mcps/PROGRESS.md`; report:
`domain-docs/mcps/FINAL_VALIDATION_2026-10-07.md`.

Sviluppo successivo 2026-10-07: catalogo live stdio separato con 17 letture
API GAIA, opt-in e fail-closed. Test source-specific, SDK e integrazione
route/JWT/permessi; nessun deploy o attivazione client live. NAS e
Trasparenza richiedono ancora ACL/cataloghi approvati; batch GET con side
effect esclusi. Dettagli: `domain-docs/mcps/LIVE_READS_2026-10-07.md`.

Preparazione successiva completata: release separata sul CED e container
dedicato su loopback, OAuth disattivato e 404 verificati, dataset sintetico
e immagine aggiornata senza sostituire gli hotfix. Test release/OAuth/
connector PASS, incluso TCP; procedura e rollback in
`domain-docs/mcps/LAN_ISOLATED_RELEASE_2026-10-06.md`.

Stato verificato: `domain-docs/mcps/CURRENT_STATUS_2026-10-06.md`.
Implementati gateway HTTP/HTTPS, OAuth/consenso/hardening, installer della
CA dedicata e download condizionali sulla login. Chiave/CSR server creati
sul CED `192.168.1.110`, certificato `gaia.lan` firmato e verificato,
certificati pubblici trasferiti; nessun deploy HTTPS o trust automatico.

Restano rilascio mirato con backup/rollback e hotfix preservati, gestione
Nginx host con sudo, client_id/callback reali approvati, dataset sintetico,
build frontend con asset pubblici e flag coerenti, accettazione
redirect/discovery/401/consenso/tool calling/revoca sul client effettivo.
Firma Authenticode, collaudo nativo e rinnovo leaf prima del 2027-01-04
sono gate operativi. NAS/Trasparenza restano fail-closed; nessun ingresso
Internet per Claude cloud/ChatGPT e autorizzato.

> Regola repository
> Backend unico, moduli logici separati. Nuove implementazioni backend vanno in `backend/app/modules/<modulo>/`.

## Ciclo Dotazioni — 2026-10-01

MVP implementato nel monolite modulare, Inventory invariato. Piano/PROGRESS:
`domain-docs/dotazioni/docs/IMPLEMENTATION_PLAN.md`. Verifica finale e matrice:
`domain-docs/dotazioni/docs/GATE_CLOSURE_2026-10-03.md`: gate della change
isolata PASS, commit autorizzato limitato a Dotazioni. Baseline globale Wiki/MCP
da riconciliare separatamente; nessun deploy.

## Ciclo CED — 2026-10-02

Gestione delegata utenti standard implementata e caratterizzata. Nessuna
migrazione, dipendenza nuova o architettura parallela. Consolidamento finale e
residui: `domain-docs/accessi/docs/CED_USER_MANAGEMENT_VALIDATION.md`.
Chiusura PASS e distribuzione restano subordinate ai controlli effettivi.

## 1. Obiettivo del progetto

Realizzare una piattaforma web interna per il Consorzio di Bonifica dell'Oristanese che consenta di:

- acquisire dal NAS Synology utenti, gruppi, cartelle condivise e ACL
- calcolare i permessi effettivi di ogni utente sulle cartelle
- visualizzare lo stato degli accessi in modo chiaro
- consentire ai capi servizio di validare i criteri di assegnazione
- produrre report esportabili per audit e bonifica

Il progetto, nella fase iniziale, deve essere esclusivamente di:
- audit
- visualizzazione
- validazione
- reporting

Non deve modificare automaticamente i permessi sul NAS nella prima release.

---

## 2. Obiettivi funzionali MVP

### 2.1 Funzioni incluse
- autenticazione applicativa
- sincronizzazione dati dal NAS via SSH
- acquisizione utenti
- acquisizione gruppi
- acquisizione appartenenze utenti-gruppi
- acquisizione elenco shared folder
- acquisizione ACL delle cartelle condivise
- salvataggio snapshot dei dati
- calcolo permessi effettivi per utente/cartella
- dashboard consultazione
- filtri per utente, gruppo, cartella, settore
- area revisione per capi servizio
- export CSV/XLSX

### 2.2 Funzioni escluse dal MVP
- modifica automatica permessi NAS
- provisioning utenti
- integrazione Active Directory / LDAP
- SSO enterprise
- gestione sottocartelle profonde con navigazione avanzata
- sincronizzazione continua real-time

---

## 3. Architettura tecnica

### Backend
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Paramiko per SSH
- Pydantic v2
- JWT auth

### Frontend
- Next.js
- React
- TailwindCSS
- TanStack Table
- fetch/axios per API client

### Indicazioni prestazionali correnti
- evitare dashboard che ricavano KPI aggregando nel browser interi dataset mensili
- introdurre endpoint di summary backend per i workspace con metriche aggregate
- preferire griglie "light" con dettaglio lazy invece di payload completi per ogni riga
- per le API lista, esporre flag espliciti come `include_punches` o equivalenti quando sono presenti sotto-collezioni costose

### DevOps
- Docker
- Docker Compose
- Nginx reverse proxy
- file `.env`
- ambienti separati per sviluppo e produzione

---

## 4. Moduli applicativi

### 4.1 Modulo autenticazione
Gestisce:
- login
- JWT access token
- ruoli applicativi

Ruoli previsti:
- admin
- reviewer
- viewer

### 4.2 Modulo NAS connector
Gestisce:
- connessione SSH al NAS
- esecuzione comandi
- parsing output

### 4.3 Modulo sincronizzazione
Gestisce:
- acquisizione dati dal NAS
- creazione snapshot
- salvataggio dati raw e normalizzati

### 4.4 Modulo permission engine
Gestisce:
- combinazione permessi utente e gruppo
- precedenza deny/allow
- calcolo read/write effettivi
- generazione motivazione del permesso

### 4.5 Modulo review workflow
Gestisce:
- assegnazione ambito settore
- revisione da parte del capo servizio
- decisioni: conferma/revoca/richiesta modifica
- note

### 4.6 Modulo reporting
Gestisce:
- export CSV
- export XLSX
- report per settore
- report per utente
- report per cartella

---

## 5. Modello operativo

### Fase 1 — acquisizione tecnica
L'app esegue il fetch dal NAS e fotografa lo stato attuale.

### Fase 2 — normalizzazione
I dati grezzi vengono convertiti in un modello coerente:
- utenti
- gruppi
- share
- ACL
- permessi effettivi

### Fase 3 — consultazione
Gli amministratori consultano:
- chi accede a cosa
- tramite quale gruppo
- con quale livello

### Fase 4 — validazione
Ogni capo servizio verifica gli accessi del proprio ambito.

### Fase 5 — reporting finale
Viene prodotto un report che evidenzia:
- accessi corretti
- accessi da rimuovere
- anomalie
- richieste di riallineamento

---

## 6. Milestone di implementazione

### Milestone 1 — bootstrap backend
Output attesi:
- struttura FastAPI
- connessione DB
- modelli base
- migration iniziale
- autenticazione JWT

### Milestone 2 — NAS sync
Output attesi:
- servizio SSH funzionante
- recupero utenti
- recupero gruppi
- recupero shared folders
- recupero ACL
- persistenza snapshot

### Milestone 3 — permission engine
Output attesi:
- regole di calcolo permessi effettivi
- popolamento tabella effective_permissions
- endpoint consultazione

### Milestone 4 — frontend dashboard
Output attesi:
- login
- dashboard overview
- vista utenti
- vista cartelle
- filtri
- paginazione

Nota di evoluzione applicata nel modulo Presenze:
- la dashboard `/presenze` usa ora un endpoint dedicato `/presenze/dashboard/summary` invece di scaricare tutte le giornaliere del mese per calcolare i KPI nel client
- la vista `/presenze/giornaliere` carica la matrice mensile con `include_punches=false` e recupera il dettaglio completo della singola giornata solo all'apertura del pannello
- lo stesso pattern di dettaglio lazy e stato allineato anche alla vista `/presenze/anomalie`

### Milestone 5 — review workflow
Output attesi:
- vista reviewer
- registrazione decisioni
- note
- filtri per settore

### Milestone 6 — export e hardening
Output attesi:
- export CSV/XLSX
- docker compose completo
- reverse proxy
- documentazione deployment

---

## 7. Ordine di sviluppo raccomandato

1. bootstrap repository
2. backend base
3. schema DB e migrazioni
4. auth e RBAC
5. servizio SSH NAS
6. sincronizzazione e snapshot
7. permission engine
8. API pubbliche
9. frontend login e dashboard
10. frontend viste utenti/cartelle
11. frontend review
12. export
13. Docker e Nginx
14. test e rifinitura

---

## 8. Convenzioni di sviluppo

### Backend
- codice modulare
- tipizzazione completa
- validazione con Pydantic
- separazione netta tra:
  - routers
  - services
  - repositories
  - models
  - schemas
- nessuna logica business nei router
- error handling centralizzato
- logging strutturato
- quando una route lista serializza child collections o JSON corposi, prevedere un percorso "light" di default e un opt-in esplicito per il dettaglio

### Frontend
- componenti riutilizzabili
- separazione tra:
  - pages/app routes
  - components
  - services/api
  - hooks
  - types
- evitare logica dispersa
- tabella centralizzata con filtri e paginazione

### DevOps
- immagini Docker chiare e minimali
- hardening DNS Docker host per build deterministici dei container
- rimozione del workaround Compose `build.network: host` dal servizio `frontend` dopo stabilizzazione DNS del daemon
- packaging di deploy con esclusione esplicita di cache, virtualenv, dump e backup locali
- retention automatica degli artefatti di release sul server CED
- runbook speculari per replica DB locale -> CED e CED -> locale
- sync DB slim tabellare dal CED al locale per allineare rapidamente utenze, permessi e metadati operativi senza importare ogni dataset bulk

---

## 9. Evoluzione pianificata — GAIA CED

E' pianificata un'evoluzione di piattaforma per convergere `GAIA NAS Control` e
`GAIA Rete` in un unico entrypoint frontend `GAIA CED`.

Principi guida:

- prima convergenza UI/navigation
- backend invariati nella prima fase
- permessi esistenti `module_accessi` e `module_rete` mantenuti
- eventuale `module_ced` rinviato a fase successiva

Documentazione operativa di riferimento:

- `domain-docs/ced/docs/PRD.md`
- `domain-docs/ced/docs/IMPLEMENTATION_PLAN.md`
- `domain-docs/ced/docs/CODEX_PROMPT.md`
- `domain-docs/ced/docs/PROGRESS.md`
- variabili in `.env`
- nessun segreto hardcoded
- healthcheck dei servizi
- volumi persistenti per PostgreSQL

---

## 9. Regole di business per il permission engine

- i permessi possono derivare da:
  - assegnazione diretta all'utente
  - assegnazione al gruppo
- un utente può appartenere a più gruppi
- deny ha precedenza su allow
- write implica read
- il sistema deve produrre sempre una spiegazione della sorgente:
  - direct:user
  - group:nome_gruppo
  - denied_by:...
  - combined:...

Se l'ACL Synology non è pienamente omogenea, il sistema deve comunque salvare:
- dato raw
- dato normalizzato
- eventuali warning di parsing

---

## 10. Sicurezza

- accesso solo autenticato
- JWT con expiry configurabile
- password hashate
- ruoli applicativi obbligatori
- log di:
  - login
  - sync
  - export
  - review
- accesso consigliato solo da rete interna o VPN

---

## 11. Criteri di accettazione MVP

Il MVP si considera completato quando:

1. un admin può autenticarsi
2. il sistema può sincronizzare dati dal NAS
3. il sistema salva utenti, gruppi, share e ACL
4. il sistema calcola permessi effettivi
5. la UI mostra per ogni utente le cartelle accessibili
6. la UI mostra per ogni cartella gli utenti che accedono
7. un reviewer può registrare una decisione
8. l'app può esportare un report CSV/XLSX
9. tutto è avviabile via Docker Compose

---

## 12. Rischi tecnici

- ACL Synology complesse o non uniformi
- differenze tra `getfacl` e `synoacltool`
- presenza di configurazioni storiche incoerenti
- path cartelle non standard
- gruppi legacy con naming poco leggibile

Mitigazioni:
- salvare output raw dei comandi
- introdurre warning di parsing
- validare progressivamente con dati reali
- partire dalle shared folders di primo livello

---

## 13. Output finali attesi

- repository backend
- repository frontend oppure monorepo
- docker-compose completo
- documentazione `.env.example`
- guida deployment
- guida operativa per audit accessi
- export report per capi servizio

---

## 14. Indicazioni per Codex

Codex deve:
- implementare il progetto per milestone
- mantenere coerenza tra backend e frontend
- evitare feature non richieste
- privilegiare codice chiaro e manutenibile
- documentare i punti critici
- lasciare TODO espliciti dove la logica dipende dall'ambiente Synology reale

---

## 15. Programma scheduler e worker

Il consolidamento operativo di scheduler, code e worker e tracciato nei
documenti dedicati:

- `docs/WORKER_ARCHITECTURE_PLAN.md` per architettura obiettivo, milestone,
  invarianti e rollout;
- `docs/WORKER_ARCHITECTURE_PROGRESS.md` per stato, metriche e gate eseguiti.
- `docs/WORKER_OPERATIONS_RUNBOOK.md` per deploy, osservabilita, tuning e
  rollback dei servizi.

La prima milestone separa tutti gli scheduler dai quattro processi Uvicorn e li
assegna al servizio singleton `platform-scheduler`. Le milestone successive
ottimizzano Ruolo, introducono lease/fencing sulle code persistenti e applicano
isolamento e limiti operativi per famiglia worker. Deploy e restart produzione
non sono impliciti nell'implementazione locale.


## Integrazione GATE completata — 2026-10-01

- [x] Contratto booleano `meal_voucher_manual` in LAN e poll outbound.
- [x] Persistenza con lock, audit idempotente, autore canonico e permessi esistenti.
- [x] Compatibilità KM/reperibilità e conteggio manuale OR automatico.
- [x] Test di comportamento e coverage statement/branch 100% nel perimetro modificato.

Stato operativo, verifiche e residui: `domain-docs/presenze/docs/GATE_MEAL_VOUCHER_ENTRY.md`. Nessuna modifica al frontend GAIA;
il comando mensile è nella console GATE.


## Turnisti GAIA/GATE — ciclo locale 2026-10-03

- [x] Assegnazioni persistenti per giorno/intervallo/mese: acquaiolo, telecontrollo, revoca.
- [x] Teorico locale 420 minuti; buono da almeno 420 minuti ordinari effettivi dal 26/08/2026, senza duplicazione manuale.
- [x] Precedenza GATE, import futuri, API LAN/outbound e controlli di accesso.
- [x] UI giornaliere GAIA, badge e protezione delle assegnazioni GATE.
- [ ] Rilascio autorizzato e collaudo produzione; nessun deploy nel ciclo corrente.

Specifica: `domain-docs/presenze/docs/TURNISTI_GAIA_GATE.md`.
Verifiche, matrice test e residui: `domain-docs/presenze/docs/TURNISTI_COORDINATED_VERIFICATION_2026-10-05.md`.
