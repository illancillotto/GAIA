# MCP in produzione — connettore remoto Claude

Riepilogo operativo autorevole: `CURRENT_STATUS_2026-10-06.md`. La nuova
CA dedicata e il certificato server `gaia.lan` sono stati creati, verificati
e i certificati pubblici copiati sul CED `192.168.1.110`; HTTPS non attivato.
Il piano remoto qui sotto rimane storico: nessun ingresso Internet approvato.

Decisione corrente 2026-10-05: **solo LAN `gaia.lan`, Claude Desktop locale
stdio/bridge**, ChatGPT da valutare. Nessun ingresso Internet autorizzato.
Hardening OAuth implementato: `OAUTH_HARDENING_2026-10-05.md`. Certificati CED,
prova Desktop e mapping ACL NAS/catalogo Trasparenza restano prerequisiti.
Il piano remoto e le evidenze seguenti sono cronologia, non rilascio eseguito.

Chiusura corrente: `FINAL_CLOSURE_2026-10-03.md`. Suite completa, coverage,
build locale/standalone e preview browser verificati. Ingresso pubblico,
callbackClaude, hardeningOAuth e gate globale restano residui; flagsfalse.
Le precedenti note build/browser/suite bloccati descrivono gli audit storici.

Verifica finale 2026-10-03: `CONNECTOR_FINAL_REVIEW_2026-10-03.md`.
OAuth/consenso/gateway e budget implementati; gate completo e pubblicazione
restano pendenti. Build non completata, browser/suite socket bloccati e
ratchet globale rosso. Nessuna attivazione autorizzata o effettuata.

Aggiornamento successivo 2026-10-03: implementati pagina consenso GAIA e
[gateway remoto Data-only isolato](CONNECTOR_RUNTIME_2026-10-03.md), con
metadata per issuer/resource con path, audit e budget persistiti per utente.
Feature flag disattivate; niente pubblicazione o prova Claude live. Le note
precedenti sui componenti ancora da implementare restano cronologia di audit.

Aggiornamento 2026-10-03: implementata e verificata la
[fondazione OAuth sul login GAIA](OAUTH_FOUNDATION_2026-10-03.md).
Non e ancora montata/pubblicata: UI consenso, gateway Data-only remoto,
metadata protected-resource, budget per principal e ingresso HTTPS restano
gate obbligatori. Le successive note OAuth non implementato sono storiche.

Aggiornamento 2026-10-02: completato il filtro scope nella discovery del
server Data, anche per client grezzi. Vedi `SERVER_SCOPE_DISCOVERY_2026-10-02.md`.
Le note successive che descrivono questo gap rappresentano l'audit precedente;
OAuth, ingresso pubblico e budget per principal restano da implementare.

Data: 2026-10-02. Stato: piano di produzione, nessun deploy eseguito.
Richiesta corrente: rendere il MCP utilizzabile tramite «Aggiungi connettore
personalizzato» nell'app Claude Desktop. La configurazione stdio e la console
Docker locale gia preparate sono prove di sviluppo, non questo rilascio.
ChatGPT resta una compatibilita successiva; la prima accettazione e Claude.

Installer della CA interna: `CLIENT_CA_INSTALLERS.md`. Preparati EXE Windows
amd64/arm64 e script macOS/Linux, usando solo il certificato pubblico della
CA CBO trovata in `/home/cbo/cbo-internal-ca/certs/CBO-Internal-Root-CA.crt`.
DECISIONE SUCCESSIVA: l'utente richiede una NUOVA CA, con procedura da
concordare con il CED. I pacchetti costruiti con la CA Kiosk sono SOSPESI,
non distribuibili. Il builder ora richiede nome e impronta della nuova CA
e rifiuta quella precedente. La nuova CA non e stata creata implicitamente.
Non sono un deploy MCP e non risolvono l'ingresso remoto Anthropic.

Indirizzo indicato dall'utente: `https://gaia.lan`, mantenuto come origine
interna GAIA. Route interna proposta: `https://gaia.lan/mcp`, da implementare
e verificare; non e un endpoint gia pubblicato. Il SAN del certificato GAIA
deve includere `gaia.lan`. L'ingresso Internet per il connettore remoto e
ancora da scegliere: il nome `.lan` non e un dominio pubblico e non consente
di ottenere un normale certificato ACME da CA pubblica per questo nome.
Serve un hostname pubblico distinto se si sceglie proxy o tunnel remoto.

## Esito dell'audit HTTPS di gaia-kiosk

Repository esaminato in sola lettura:
`/home/cbo/CursorProjects/gaia-kiosk`, HEAD `0fdb4a8`.
Working tree con modifiche concorrenti conservato, nessuna modifica a Kiosk.
Graphify usato per orientamento locale, senza estrazione semantica esterna.

| Evidenza | Risultato | Implicazione per MCP |
| --- | --- | --- |
| `docs/INTERNAL_TLS_DEPLOYMENT.md` | PKI interna «CBO Internal Root CA», CA separata, CSR sul server, SAN specifici, chiave server 0600 | Riusare la procedura per HTTPS interno GAIA; non copiare chiavi o certificato Kiosk |
| `scripts/tls/ca-sign-csr.sh`, `server-verify.sh`, `server-install.sh`, `server-reload.sh` | Validazione catena/nome/usi/scadenza/chiave, backup e reload dopo `nginx -t` | Riusare i controlli e la procedura di rollback |
| `infra/nginx/nginx.production.conf` | TLS 1.2/1.3, HSTS iniziale 86400, redirect HTTP, certificati montati read-only | Riusare i principi del proxy, senza copiare le route/device Kiosk |
| `docker-compose.production.yml` | Servizi interni isolati; Nginx anche su rete pubblicabile | Applicare l'isolamento al servizio MCP e pubblicare soltanto il proxy |
| `.local-pilot/tls/fullchain.pem` | Subject e issuer `localhost`; SAN `localhost`, `nginx`, `127.0.0.1`; scadenza 2026-10-05 07:15:51 UTC | Certificato autofirmato di laboratorio; non usare in produzione MCP |
| `docs/RELEASE_2026_10_01_CODA.md`, `docs/PROGRESS.md` | Report di HTTPS di produzione verificato con CA interna; SAN solo `gaia-kiosk.lan`, non IP | Report piu recenti dell'introduzione del runbook TLS che dichiara ancora rollout `BLOCKED` |
| Suite `backend/tests/test_internal_tls_scripts.py` | 18 test PASS, OpenSSL reale, copia effimera di script/test in `/tmp` | Verifica automatica della procedura, non verifica attuale del certificato sul server CED |

Log test: `/tmp/gaia-kiosk-tls-audit/tests.log`. Sono generate esclusivamente
CA e chiavi effimere di test; nessuna lettura di chiavi private di produzione.
Il tentativo di leggere il certificato pubblico servito da
`192.168.1.111:443`, SNI `gaia-kiosk.lan`, e fallito prima del collegamento:
`BIO_socket: Operation not permitted`. Log:
`/tmp/gaia-kiosk-tls-audit/live-error.log`. La sessione ha rete ristretta e
approvazioni disabilitate: nessuna verifica live del server e dichiarata PASS.

Il runbook TLS contiene informazioni storiche antecedenti ai rilasci:
non dedurre che la produzione sia priva di HTTPS dal vecchio stato `BLOCKED`,
ne dedurre la validita attuale del certificato dai soli report precedenti.
Prima di qualsiasi modifica sul CED eseguire la verifica live con CA pubblica,
nome corretto, scadenza e configurazione Nginx realmente caricata.

## Due confini HTTPS differenti

1. **GAIA interno**, `gaia.lan` indicato dall'utente: la CA CBO puo essere riutilizzata
   per emettere un nuovo certificato con SAN adeguato. L'installazione della CA
   nei PC gestiti rende attendibile quell'HTTPS per i client interni.
2. **Connettore remoto Claude**: la connessione deve poter arrivare dal servizio
   Claude al MCP. Serve un hostname raggiungibile esternamente e una catena
   TLS verificabile da quel client, normalmente una CA pubblicamente attendibile.
   Installare la CA CBO nel PC che esegue Claude Desktop non installa la CA
   nei server Anthropic e non rende raggiungibile un indirizzo `.lan`.

Per il rilascio si propone un hostname pubblico dedicato su dominio gia
controllato dal CBO, con certificato pubblico e reverse proxy aziendale
oppure tunnel aziendale gia approvato. Nome e infrastruttura sono da
identificare: nessun dominio, URL o credenziale vengono inventati.
Il tunnel deve supportare Streamable HTTP, timeout del tool calling e
autenticazione MCP; una pagina di login interposta dal tunnel non basta.
Non e necessario rendere pubblica tutta l'app GAIA o cambiare l'accesso LAN.

La pagina ufficiale Anthropic del connettore **Messages API**, acquisita nella
sessione precedente, descrive server HTTP pubblici e URL HTTPS:
https://platform.claude.com/docs/en/agents-and-tools/mcp-connector .
Questa fonte non prova da sola tutti i dettagli dell'interfaccia Desktop.
Il tentativo di aggiornare la guida del connettore personalizzato Desktop
e fallito per DNS di sessione. Prima dell'implementazione OAuth ricontrollare
la guida Desktop ufficiale e i redirect/client realmente dichiarati da Claude:
https://support.claude.com/en/articles/11175166-getting-started-with-custom-connectors-using-remote-mcp .
Non presumere callback OAuth o possibilita di aggiungere header personalizzati.

## Topologia proposta

```text
Claude Desktop: connettore remoto
               |
       servizio Claude remoto
               |
      HTTPS pubblico attendibile
               |
 reverse proxy/tunnel CBO dedicato
    |                      |
 /mcp + metadata       OAuth GAIA
    |                  login/consenso
    |                      |
 gateway MCP: utente attivo, scope effettivi, revoca, limiti
               |
    server Data-only su rete interna
      SQLite sintetica verificata RO
      audit separato protetto RW

Console Wiki GAIA interna -> catalogo/dati/audit autorizzati
Docs interno separato     -> nessuna route sul proxy esterno
```

Claude sceglie il proprio modello e chiama i tool MCP. Questo connettore non
deve invocare `/wiki/mcp/chat` o gpt-reserve: quell'endpoint rimane l'agente
GAIA interno via codex-lb. Non occorrono API key codex-lb nel connettore,
nel browser o nel servizio Data. Gli argomenti e i risultati dei tool
esterni restano esclusivamente sul percorso sintetico autorizzato.

## Gap del runtime corrente

| Area | Gia disponibile | Lavoro necessario prima del rilascio |
| --- | --- | --- |
| Protocollo | Streamable HTTP interno `/data/`, stdio locale | Endpoint remoto stabile `/mcp`, verifica compatibilita/versione protocollo Claude |
| HTTPS | Esempio Kiosk per CA interna; MCP locale su HTTP | Hostname pubblico esistente, catena pubblica, ingress e rinnovo automatico |
| Autenticazione | JWT MCP interno 60 s; login GAIA | OAuth per resource server MCP, metadata/discovery, consenso, PKCE, refresh/revoca secondo client reale |
| Catalogo | Gateway Wiki filtra discovery per scope | Il server Data grezzo elenca attualmente tutti i tool: il catalogo del gateway remoto deve filtrare prima di rispondere al client |
| Permessi | Chiamate Data verificano scope | Legame OAuth a utente GAIA reale, verifica stato/moduli/sezioni correnti a ogni invocazione; nessun service account condiviso indiscriminato |
| Host | Allowlist `localhost`, `127.0.0.1`, `gaia-mcp` | Configurare esplicitamente host/origini e proxy fidati; mantenere controllo DNS rebinding, non disattivarlo |
| Privacy | CLI `--data-only`; DB sintetico verificato | Nessun mount Docs, PostgreSQL operativo o NAS nel servizio esposto; nessun fallback a fonti reali |
| Ispezione | `/inspect/*` interno e console GAIA | Non pubblicare `/inspect/*`, console, `/wiki/mcp/token` o API GAIA generiche sul vhost MCP |
| Audit | Principal pseudonimizzato, filtri minimizzati, risposte sintetiche, file 0600, ultimi 1000 eventi | Correlazione client/OAuth e isolamento; definire monitoraggio e conservazione necessari prima del rollout |
| Limiti | Body 64 KiB, cap record, timeout, budget agente GAIA | Rate/concorrenza e limiti per principal del client remoto: i budget dell'agente interno non limitano Claude esterno |
| Packaging | Compose Data-only e lab Docker | Immagine di release riproducibile, dependency check/build completi, healthcheck e deploy senza fixture/account sintetico di login |

I 1000 eventi correnti sono uno storico di analisi, non un registro di audit
illimitato. Se e richiesta conservazione maggiore, introdurre un archivio
protetto prima del rilascio e testare la policy; non allargare i log stderr
con contenuti, token o credenziali.

## Tranche operative

### 1. Inventario CED e scelta ingresso

- Identificare hostname pubblico controllato, DNS, reverse proxy/tunnel
  esistente, destinazione interna e responsabile certificato/rinnovo.
- Verificare vhost GAIA effettivo, porte, rete Compose, immagini e permessi
  sul server CED in sola lettura; nessun riavvio o modifica alla PKI Kiosk.
- Verificare accesso diretto e accesso da fuori LAN all'ingresso scelto.
- Registrare SAN, issuer, scadenza, catena e renewal del certificato pubblico.
- Se si aggiunge anche HTTPS interno GAIA, usare nuova CSR/chiave per il nome
  GAIA e la CA CBO; non riemettere o sostituire il certificato Kiosk.

**Uscita:** topologia nominata e route esatte approvate, con hostname reale;
nessun endpoint anonimo o documento reale esposto.

### 2. Autenticazione del connettore

- Confermare requisiti OAuth del client Claude Desktop corrente.
- Preferire authorization server aziendale gia disponibile e compatibile;
  se manca, implementare il flusso nel modulo Wiki/Accessi con login GAIA.
  Il login Google gia presente e un login federato, non un authorization
  server MCP automaticamente riusabile.
- Pubblicare metadata resource/authorization secondo versione MCP scelta;
  `WWW-Authenticate` deve indicare il resource server correttamente.
- Authorization code + PKCE, consenso Data sintetici, redirect esatti
  allowlisted; associare l'utente GAIA e consentire solo scope autorizzati.
- Audience/resource vincolati al MCP; access e refresh token separati,
  scadenza, rotazione/revoca e verifica utente attivo.
- Supportare la registrazione client richiesta dal client realmente usato;
  non introdurre dynamic registration aperta senza verificarne la necessita.
- Nessun `docs.read` o `mcp.audit.read` al client esterno. Refresh e consenso
  non possono ripristinare un dominio revocato.

**Uscita:** login/consenso da Claude e isolamento di due utenti verificati,
revoca effettiva, zero segreti nel connettore/browser/log.

### 3. Gateway remoto Data-only

- Esporre solo `/mcp` e metadata/route OAuth necessarie sul vhost dedicato.
- Tradurre l'identita autenticata in principal GAIA e scope correnti;
  discovery e chiamate filtrate lato server, anche per tool inventati.
- Conservare contratti query, input strict, UUID, cap, provenance e paginazione.
- Bloccare `/docs`, `/inspect`, endpoint chat/token e accesso a API operative
  dal vhost MCP, anche con path codificati o bearer interno.
- Aggiungere limiti per principal e proteggere proxy headers, host e origini.
- Mantenere Docs separato e chat Wiki legacy; nessuna modifica di dominio
  Utenze/Catasto/Ruolo per questa integrazione.

**Uscita:** Inspector/SDK remoto vede soltanto tool autorizzati e sintetici;
il servizio Data non ha accesso a corpus Docs o database operativo.

### 4. Release, ingress e console

- Build di release del backend/servizio MCP e frontend; non usare immagine,
  proxy, fixture Auth o processi Next.js `/tmp` del lab in produzione.
- Artifact sintetico congelato con hash/versione, mount read-only; audit
  separato scrivibile solo all'UID corretto, segreti fuori dal repository.
- Certificati montati read-only; chiavi CA mai sul server applicativo.
- Config Nginx/tunnel con body cap, rate limit, timeout compatibile con MCP,
  buffering/streaming verificati; nessun fallback alla route `/` di GAIA.
- Healthcheck, monitoraggio 401/403/5xx, scadenza TLS, spazio audit e rinnovi.
- Console dati/richieste/log integrata nella Wiki di produzione con i
  permessi GAIA, senza esporla automaticamente sul vhost MCP pubblico.
- Registrare configurazione e immagini precedenti per rollback; non avviare
  migrazioni/bootstrap di moduli estranei presenti nel working tree.

**Uscita:** release e diff revisionabili, gate mirati verdi, piano di rollback
verificato in staging. Deploy operativo solo dopo richiesta esplicita.

### 5. Collaudo dal vero connettore Claude

- Aprire «Aggiungi connettore personalizzato», inserire l'URL **reale** HTTPS
  `/mcp`, completare login/consenso e verificare catalogo autorizzato.
- Ricerca sintetica presente, assente, omonimi e multi-hop; confrontare
  UUID/evidenze con ground truth locale non inviato al modello.
- Verificare richieste/tool/filtri/risultati/provenance nella console GAIA.
- Revocare un dominio all'utente di collaudo: nuove discovery/invocazioni
  devono negarlo; disattivazione e revoca connector/token devono bloccare.
- Provare tool Docs inventati, accesso incrociato utenti, input invalidi e
  superamento limiti; nessun contenuto Docs deve raggiungere Claude.
- Riavviare MCP e verificare audit/persistenza; provare rinnovo TLS e rollback.
- Distinguere test simulati, SDK live e chiamate reali del modello Claude.
  Il timeout CLI Claude precedente non e una prova connettore riuscita.

**Uscita:** connettore Claude funzionante in produzione, console coerente,
evidenze minimizzate e nessun documento/dato reale inviato all'esterno.

## Gate e rollback

Per ogni tranche runtime: coverage statement/branch 100% dei file modificati,
Ruff e formatter dovuti, ratchet contro baseline merge-base, test Wiki legacy,
Compose/dependency/build check e Graphify tramite target Make codice.
Frontend: coverage 100%, typecheck/lint e browser E2E della console.
Nessuna estrazione Graphify docs remota: violerebbe il vincolo documenti reali.
I gate globali gia rossi per modifiche estranee non vengono assorbiti nella
baseline ne dichiarati PASS; isolare la release MCP e rendere espliciti gli
eventuali blocchi prima del deploy.

Rollback: disabilitare solo il vhost/route MCP remoto e revocare client/token;
ripristinare immagini e config precedenti. Preservare l'audit, il dataset
sintetico e i servizi Wiki/Docs/Kiosk esistenti. Nessun restore distruttivo
del database GAIA e nessun rollback della CA Kiosk per questa change.

## Decisione ancora necessaria

L'utente ha indicato `https://gaia.lan`: accettato come origine interna.
Per completare il connettore remoto serve ancora scegliere fra hostname
Internet controllato dal CBO con proxy dedicato, oppure tunnel gestito con
hostname pubblico. La scelta e stata presentata all'utente; nel frattempo
audit e piano sono completi. Un rilascio solo su HTTPS interno puo servire
client LAN ma non supera l'accettazione del connettore remoto Claude.
Non pubblicare un URL di esempio come se fosse operativo. HTTPS interno CBO
resta riusabile, ma non sostituisce raggiungibilita e trust TLS del remoto.
Sviluppo live 2026-10-07: `LIVE_READS_2026-10-07.md` documenta il catalogo
stdio implementato e separato dal connector OAuth sintetico. Le letture
live non vengono abilitate dal piano di rilascio: restano necessari HTTPS
CED verificato, sessione utente, allowlist e approvazione perimetro dati.
NAS/Trasparenza e batch GET con side effect non sono esposti.
