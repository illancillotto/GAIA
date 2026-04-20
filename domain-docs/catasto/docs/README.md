# GAIA Catasto Docs

## Scopo

Questa cartella contiene la documentazione del dominio `catasto` e i riferimenti collegati al runtime operativo oggi ospitato in `elaborazioni`.

Usare questo indice per capire rapidamente quali file sono:

- operativi
- storici
- file-ponte mantenuti per compatibilita

## Documenti operativi

- `PRD_catasto.md`
  Documento di riferimento per perimetro, architettura, API e stato corrente del dominio `catasto` e del runtime collegato.
- `PROMPT_CODEX_catasto.md`
  Prompt operativo per Codex allineato allo split reale tra `catasto` e `elaborazioni`.
- `PROMPT_CLAUDE_CODE_catasto.md`
  Prompt operativo parallelo, utile come istruzione sintetica per agenti e tooling compatibili.

## Documenti storici

- `PROMPT_CLAUDE_CODE_frontend_restructure.md`
  Documento storico. Il refactor frontend descritto e gia stato completato e non va usato come prompt operativo corrente.

## File-ponte per compatibilita

- `ELABORAZIONI_REFACTOR_PLAN.md`
  Rimando compatibile al piano attuale in `domain-docs/elaborazioni/docs/ELABORAZIONI_REFACTOR_PLAN.md`.
- `SISTER_debug_runbook.md`
  Rimando compatibile al runbook tecnico attuale in `domain-docs/elaborazioni/docs/SISTER_debug_runbook.md`.

## Regole pratiche

- Per modifiche a comuni o documenti catastali, partire dai documenti operativi di questa cartella.
- Per modifiche a batch, credenziali, CAPTCHA, richieste singole o avanzamento runtime, verificare sempre anche `domain-docs/elaborazioni/docs/`.
- Non usare i documenti storici come sorgente primaria per implementazioni nuove.
- Se un file viene mantenuto solo per compatibilita, segnalarlo esplicitamente nel blocco iniziale del documento.
