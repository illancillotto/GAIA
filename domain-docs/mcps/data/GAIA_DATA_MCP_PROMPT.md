# Prompt operativo — progettazione GAIA Data MCP

## Obiettivo

Progettare e implementare il **GAIA Data MCP** per l'agente principale di GAIA Wiki.

Il contributo della tesi riguarda la selezione dinamica delle fonti e la costruzione del contesto. Il Data MCP deve rimanere un adapter deterministico della fonte strutturata.

## Repository

Analizzare il runtime corrente del repository GAIA.

Perimetro prioritario:
- `backend/app/modules/catasto/`
- `backend/app/modules/utenze/`
- `backend/app/modules/ruolo/`

Analizzare anche le dipendenze canoniche esterne ai moduli, ad esempio modelli condivisi richiamati dal registry Catasto.

## Fase 1 — fotografia del runtime reale

Ricostruire:
- modelli SQLAlchemy;
- tabelle;
- PK/FK;
- relazioni;
- indici;
- read model;
- repository/service;
- route;
- schema Pydantic;
- permission scope;
- query cross-domain.

Non assumere che la documentazione sia aggiornata.

In caso di divergenza fra codice e docs:
1. descrivere la divergenza;
2. indicare il runtime corrente;
3. evitare correzioni non richieste.

Aggiornare `GAIA_DATA_MCP_ANALYSIS.md`.

## Fase 2 — replica sintetica

Usare `GAIA_DATA_MCP_SYNTHETIC_SCHEMA.md` come proposta iniziale, ma validarla contro il runtime.

La replica deve:
- preservare le relazioni utili;
- eliminare complessità non necessarie;
- usare solo dati sintetici;
- supportare un seed deterministico;
- essere separata dai dati reali;
- consentire query single-hop e multi-hop.

## Fase 3 — tool catalog

Validare e aggiornare `GAIA_DATA_MCP_TOOLS.md`.

Regole:
- no `execute_sql`;
- no mega-tool che restituisce l'intero contesto;
- tool piccoli e semantici;
- output compatti;
- hard limit;
- provenance;
- permission scope;
- errori tipizzati.

## Fase 4 — Operazioni

Analizzare il modulo Operazioni solo per decidere se un sottoinsieme minimo aggiunge casi sperimentali di valore.

Produrre una sezione con:
- entità candidate;
- relazioni con Catasto/Utenze;
- nuovi scenari resi possibili;
- tool aggiuntivi;
- stima della complessità;
- raccomandazione include/escludi.

Non implementare Operazioni senza approvazione.

## Fase 5 — implementazione

Implementare solo dopo approvazione di:
- analisi;
- schema sintetico;
- catalogo tool;
- piano test.

## Vincoli

- read-only;
- nessun dato reale nei test cloud;
- nessun routing verso altre fonti;
- nessun LLM interno necessario per decidere le query;
- logging e metriche compatibili con `../OBSERVABILITY_AND_EVALUATION.md`;
- sicurezza compatibile con `../SECURITY_AND_PRIVACY.md`.

## Definition of Done

Il Data MCP è completato quando:
- gira in locale e nell'ambiente GAIA previsto;
- espone il catalogo tool approvato;
- passa test unitari, integrazione e sicurezza;
- usa dataset sintetico riproducibile;
- restituisce provenance;
- produce telemetria;
- non consente scritture;
- è utilizzabile da GAIA Wiki Agent senza conoscenza SQL.
