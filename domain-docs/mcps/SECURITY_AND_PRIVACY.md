# Sicurezza e privacy degli MCP GAIA

## Principi

I vincoli di privacy sono requisiti architetturali.

Contratto runtime v1: il gateway Wiki esterno usa solo Data sintetico e
`gpt-reserve` tramite codex-lb. Docs non e configurato nel client del gateway;
discovery e invocazioni sono bloccate prima della connessione, anche se il
modello inventa una chiamata Docs. I token del gateway non contengono
`docs.read`. Il server Docs separato rimane interno e autenticato.
Nessun documento reale viene inviato al provider, neanche tramite Graphify docs.
Le domande di esperimento devono essere sintetiche: non incollare documenti o
dati reali nel testo libero. Il filtro delle fonti non e un classificatore DLP
del testo scritto dall'utente. Le credenziali provider sono solo configurazione
locale ignorata/env, mai corpus, tool output o report.

La preview `/wiki/mcp` elimina l'input libero e gli allegati: solo preset
sintetici. Il runner accetta unicamente la SQLite sintetica verificata e genera
localmente le proprie domande; non accetta corpus Docs o file di query liberi.
L'oracle resta locale. Cataloghi non `data__*` e dataset remoto diverso sono
rigettati prima di inoltrare evidenze. Il journal non contiene token/API key:
solo manifest, messaggi/evidenze sintetici, scoring e tipo dell'eventuale errore.
Il gateway generale non diventa un DLP: il divieto di incollare dati reali
continua a valere per client API diversi dalla preview.

- I dati personali dei consorziati restano on-premise.
- I documenti reali dell'Ente non vengono inviati a servizi cloud.
- Catasto, Ruolo e Utenze usati negli esperimenti cloud sono rappresentati da una replica sintetica.
- I test con baseline commerciali usano solo dati sintetici o completamente anonimizzati.

## GAIA Data MCP

Requisiti:
- read-only;
- query parametrizzate;
- nessun SQL libero esposto al modello;
- validazione input;
- hard cap sui risultati;
- permission scope;
- audit;
- nessun secret negli output;
- nessun dump completo di tabelle;
- logging con minimizzazione dei dati.

Scope iniziali suggeriti:
- `catasto.read`
- `utenze.read`
- `ruolo.read`

## GAIA Docs MCP

Escludere almeno:
- secret;
- `.env`;
- credenziali;
- dump;
- dati personali;
- documenti esplicitamente non indicizzabili.

## Prompt injection nei documenti

Il testo recuperato è dato non attendibile, non istruzione. I documenti non possono autorizzare tool, modificare scope o disabilitare controlli.

## Autorizzazione

Identità e scope devono provenire dal contesto autenticato di GAIA/gateway, non da parametri scelti dal modello.

## Audit

Registrare almeno:
- request ID;
- principal pseudonimizzato;
- tool;
- scope;
- timestamp;
- esito;
- numero record;
- latenza;
- errore;
- versione server.

Non registrare automaticamente l'intero contenuto restituito se contiene informazioni sensibili.

## Separazione dataset

La replica sintetica deve usare database/schema e credenziali separati. Un test automatico deve fallire se un ambiente sperimentale punta a host/schema reali non autorizzati.
