# GAIA Catasto Docs

## Scopo

Questa cartella contiene la documentazione del dominio `catasto` e i riferimenti collegati al runtime operativo oggi ospitato in `elaborazioni`.

Usare questo indice per capire rapidamente quali file sono:

- operativi
- storici
- file-ponte mantenuti per compatibilita

## Documenti operativi

- `PRD_catasto.md`
  Documento di riferimento per perimetro, architettura, API e stato corrente del dominio `catasto`.
  Include anche la Fase 1 territoriale `cat_*`, la ricerca anagrafica di Fase 4 e il requisito PostGIS.

## Documenti storici

- `archive/PROMPT_CODEX_catasto.md`
  Prompt storico del periodo di transizione `catasto` -> `elaborazioni`.
- `archive/PROMPT_CLAUDE_CODE_catasto.md`
  Prompt storico del periodo di transizione `catasto` -> `elaborazioni`.
- `archive/PROMPT_CLAUDE_CODE_frontend_restructure.md`
  Documento storico. Il refactor frontend descritto e gia stato completato e non va usato come prompt operativo corrente.

## File-ponte per compatibilita

- `ELABORAZIONI_REFACTOR_PLAN.md`
  Rimando compatibile al piano attuale in `domain-docs/elaborazioni/docs/ELABORAZIONI_REFACTOR_PLAN.md`.
- `SISTER_debug_runbook.md`
  Rimando compatibile al runbook tecnico attuale in `domain-docs/elaborazioni/docs/SISTER_debug_runbook.md`.

## Regole pratiche

- Per modifiche a comuni o documenti catastali, partire dal PRD operativo di questa cartella.
- Per il mapping comuni di Catasto, usare sempre il dataset `backend/app/modules/catasto/data/comuni_istat.csv` come sorgente di verita del dominio.
- Non assumere che `cod_comune_capacitas` nel codice Catasto coincida con il codice comune numerico ufficiale ISTAT moderno: e il codice numerico sorgente scambiato da Capacitas.
- Se serve il codice ufficiale, leggerlo esplicitamente dalle colonne dedicate del dataset di riferimento e non ricostruirlo via `CASE` hardcoded.
- La tabella di riferimento `cat_comuni` e la sorgente canonica per i comuni del dominio: contiene `codice_catastale`, `cod_comune_capacitas`, codici ufficiali e metadata amministrativi.
- Nelle tabelle operative preferire `comune_id` come riferimento stabile; mantenere `cod_comune_capacitas` e `codice_catastale` solo come codici sorgente o di tracciabilita quando servono.
- Per modifiche a batch, credenziali, CAPTCHA, richieste singole o avanzamento runtime, verificare sempre anche `domain-docs/elaborazioni/docs/`.
- Non usare i documenti storici come sorgente primaria per implementazioni nuove.
- Se un file viene mantenuto solo per compatibilita, segnalarlo esplicitamente nel blocco iniziale del documento.
- I file-ponte compatibili restano nella root di `docs/`; i documenti storici non piu operativi vanno spostati in `docs/archive/`.
