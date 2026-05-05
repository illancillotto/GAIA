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
  Include anche la Fase 1 territoriale `cat_*`, la ricerca anagrafica fino a Fase 5 e il requisito PostGIS.

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
- Il perimetro oggi chiuso arriva fino alla Fase 5 del dominio Catasto corrente: prima di aprire nuove tranche, verificare il file di avanzamento in `progress/2026-04-22_catasto_phase_progress.md`.
- Per il mapping comuni di Catasto, usare sempre il dataset `backend/app/modules/catasto/data/comuni_istat.csv` come sorgente di verita del dominio.
- Negli shapefile territoriali, trattare `CODI_FISC` come sorgente primaria del codice catastale comune; usare `CFM` e `NATIONALCA` solo come fallback.
- Non assumere che `cod_comune_capacitas` nel codice Catasto coincida con il codice comune numerico ufficiale ISTAT moderno: e il codice numerico sorgente scambiato da Capacitas.
- Se serve il codice ufficiale, leggerlo esplicitamente dalle colonne dedicate del dataset di riferimento e non ricostruirlo via `CASE` hardcoded.
- La tabella di riferimento `cat_comuni` e la sorgente canonica per i comuni del dominio: contiene `codice_catastale`, `cod_comune_capacitas`, codici ufficiali e metadata amministrativi.
- Nelle tabelle operative preferire `comune_id` come riferimento stabile; mantenere `cod_comune_capacitas` e `codice_catastale` solo come codici sorgente o di tracciabilita quando servono.
- Nella ricerca anagrafica particelle/intestatari, i link e gli intestatari Capacitas non vanno risolti con il solo `CCO`: usare sempre anche il contesto `COM/PVC/FRA/CCS` quando disponibile, perche diversi `CCO` risultano riusati su comuni o frazioni diverse.
- Per i sub del Catasto Consorzio, non assumere equivalenza tra maiuscole e minuscole: i valori possono essere inseriti manualmente dagli operatori e vanno trattati come chiavi distinte salvo regole dominio esplicite.
- Nell'export anagrafico delle particelle con sub, i dati storici del sub non sono considerati utili come intestazione corrente. Se un sub non ha un `CCO` corrente proprio ma la particella base ha una posizione corrente affidabile, l'intestatario esportato puo essere derivato dalla particella base e va segnalato esplicitamente nelle note.
- Lo stesso export espone anche `stato_ruolo` e `stato_cnc` letti dallo snapshot certificato Capacitas coerente con il contesto `CCO/COM/PVC/FRA/CCS`; la colonna `note` resta in coda al file.
- Nell'import massivo particelle/intestatari, valori come `27 sez.B` o `23 sez.C svil.A` nel campo foglio vanno normalizzati separando `foglio` e `sezione` prima del lookup.
- Per le anomalie storiche Arborea/Terralba, non forzare alias locali per sezione (`Arborea C -> Terralba B`). Se il match locale non esiste, il fallback corretto e un lookup live Capacitas senza sezione: prima sul comune richiesto, poi sul comune alternativo (`Arborea <-> Terralba`) se il primo non restituisce risultati.
- Per modifiche a batch, credenziali, CAPTCHA, richieste singole o avanzamento runtime, verificare sempre anche `domain-docs/elaborazioni/docs/`.
- Non usare i documenti storici come sorgente primaria per implementazioni nuove.
- Se un file viene mantenuto solo per compatibilita, segnalarlo esplicitamente nel blocco iniziale del documento.
- I file-ponte compatibili restano nella root di `docs/`; i documenti storici non piu operativi vanno spostati in `docs/archive/`.
