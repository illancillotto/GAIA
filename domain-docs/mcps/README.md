# GAIA MCPs

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
