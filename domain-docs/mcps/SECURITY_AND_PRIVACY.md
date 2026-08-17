# Sicurezza e privacy degli MCP GAIA

## Principi

I vincoli di privacy sono requisiti architetturali.

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
