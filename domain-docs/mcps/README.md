# GAIA MCPs

## Runtime v1 implementato

Docs e Data MCP sono implementati nel package Wiki, con server stdio/HTTP,
autorizzazione GAIA, corpus congelato, replica sintetica e integrazione agente.
Avvio, contratti, limiti, audit e verifiche: `RUNTIME_AND_VALIDATION.md`.
Test completi: `make test-mcp`; valutazione offline: `make mcp-evaluate`.
Audit finale, matrice funzionalita/test e stato dei gate:
`FINAL_DEVELOPMENT_REVIEW.md`.
Inventario dei freeze tesi e del worktree Wiki mainline, componenti ancora
separati e cinque modifiche pendenti: `CHECKOUT_INVENTORY_2026-10-01.md`.

Recupero selettivo implementato: harness riproducibile Static RAG vs MCP,
scoring strutturato e preview sintetica `/wiki/mcp`, senza modificare i freeze.
Piano/progress/matrice test: `SYNTHETIC_RECOVERY_PLAN.md`.
Evidenze finali e limiti: `SYNTHETIC_RECOVERY_REPORT.md`.
Piano offline: `make mcp-comparison-plan`; prova esterna esplicita:
`make mcp-comparison-live` (solo database sintetico verificato).

Dal 2026-10-01 il gateway `/wiki/mcp/*` usa `gpt-reserve` tramite codex-lb
esclusivamente sulla replica sintetica Data. Docs e escluso lato server dal
catalogo, dai token e dalle invocazioni dell'agente esterno; il server Docs
separato e la chat Wiki legacy restano disponibili. Nessun documento reale
deve essere inviato al modello esterno.

Questa directory raccoglie la documentazione tecnica dei Model Context Protocol (MCP) utilizzati dalla nuova architettura agentica di **GAIA Wiki**.

## Obiettivo

GAIA Wiki ospita l'agente principale della tesi. L'agente costruisce dinamicamente il contesto selezionando fonti eterogenee e invocando strumenti distinti.

Gli MCP non devono diventare agenti autonomi né decidere il routing globale. Devono esporre capability deterministiche, controllabili e misurabili.

## MCP previsti

### `data/` — GAIA Data MCP

Accesso read-only ai dati strutturati.

Perimetro core della tesi:
- Catasto
- Utenze
- Ruolo

Il dominio Operazioni viene analizzato come estensione opzionale e non deve entrare automaticamente nella replica sintetica.

### `docs/` — GAIA Docs MCP

Accesso alla documentazione interna di GAIA tramite un corpus controllato ricavato principalmente da:
- `docs/`
- `domain-docs/`

Il corpus sperimentale non deve coincidere con l'intero indice della Wiki esistente.

## Separazione delle responsabilità

Il diagramma seguente descrive il disegno sperimentale delle fonti. Nel runtime
esterno attuale e abilitato soltanto il ramo Data; Docs richiede un client
interno separato. NAS e Trasparenza non sono tool dell'agente MCP v1.

```text
Utente
  |
  v
GAIA Wiki UI
  |
  v
Agente principale della tesi
  |
  +--> GAIA Docs MCP ------> documentazione interna GAIA
  |
  +--> GAIA Data MCP ------> replica sintetica Catasto/Utenze/Ruolo
  |
  +--> NAS tool/MCP --------> archivio Synology
  |
  +--> Trasparenza tool ----> HyperSIC / Amministrazione Trasparente
```

L'agente principale decide quale fonte interrogare, in quale ordine, con quale budget, se iterare e come assemblare il contesto finale.

## Regole comuni

1. Nessun MCP deve eseguire routing globale fra fonti.
2. Nessun MCP deve chiamare autonomamente un LLM per decidere quale altra fonte usare.
3. Gli output devono includere provenance.
4. Tutti i tool devono avere limiti di output.
5. Tutte le invocazioni devono essere osservabili e misurabili.
6. Il Data MCP è read-only.
7. I dati reali dei consorziati non devono essere usati nei test cloud.
8. La replica sintetica deve essere riproducibile tramite seed.
9. Il corpus Docs usato negli esperimenti deve essere congelato e versionato.
10. Le modifiche che cambiano il comportamento sperimentale devono essere tracciate.
