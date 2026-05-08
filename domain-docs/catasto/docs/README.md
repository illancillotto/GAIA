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
- La stessa regola vale per la sync `Terreni`, per la sync singola/progressiva delle particelle e per i refetch certificati: quando GAIA collega snapshot/intestatari Capacitas a `cat_utenze_irrigue`, il perimetro minimo di sicurezza e `CCO + COM + FRA`; se il frontend prova ad aprire `rptCertificato` con un `CCO` localmente ambiguo senza contesto sufficiente, il backend deve rispondere con conflitto esplicito invece di scegliere un certificato arbitrario.
- Per i sub del Catasto Consorzio, non assumere equivalenza tra maiuscole e minuscole: i valori possono essere inseriti manualmente dagli operatori e vanno trattati come chiavi distinte salvo regole dominio esplicite.
- Nell'aggiornamento distretti da Excel della pagina `catasto/import`, il lookup verso `cat_particelle` ignora volutamente `SUB`: il file puo contenere subalterni, ma `cat_particelle` viene trattata come anagrafica canonica della particella base, senza moltiplicare record distinti per subalterno in questo flusso.
- Nello stesso flusso `Aggiorna distretti`, alcuni valori `COMUNE` del tracciato sorgente rappresentano alias territoriali che implicano anche la sezione catastale. Mapping oggi supportati: `ORISTANO*ORISTANO -> Oristano/A`, `DONIGALA FENUGHEDU*ORISTANO -> Oristano/B`, `MASSAMA*ORISTANO -> Oristano/C`, `NURAXINIEDDU*ORISTANO -> Oristano/D`, `SILI'*ORISTANO -> Oristano/E`, `CABRAS -> Cabras/A`, `SOLANAS*CABRAS -> Cabras/B`, `OLLASTRA SIMAXIS -> Simaxis/A`, `SAN VERO CONGIUS*SIMAXIS -> Simaxis/B`, `SIMAXIS*SIMAXIS -> Simaxis/A`, `SAN NICOLO ARCIDANO -> San Nicolo d'Arcidano`.
- Nelle superfici frontend del batch `Distretti Excel`, i codici tecnici backend (`ALREADY_ALIGNED`, `MATCHED`, `NOT_FOUND`, `COMUNE_NOT_FOUND`, `INVALID_ROW`, `DUPLICATE_CONFLICT`) non devono essere mostrati tali e quali agli operatori. Regola stabile: backend espone codici/esiti canonici per API e test, frontend li traduce sempre in etichette parlanti e descrizioni brevi orientate all'utente.
- Nell'export anagrafico delle particelle con sub, i dati storici del sub non sono considerati utili come intestazione corrente. Se un sub non ha un `CCO` corrente proprio ma la particella base ha una posizione corrente affidabile, l'intestatario esportato puo essere derivato dalla particella base e va segnalato esplicitamente nelle note.
- Lo stesso export espone anche `stato_ruolo` e `stato_cnc` letti dallo snapshot certificato Capacitas coerente con il contesto `CCO/COM/PVC/FRA/CCS`; la colonna `note` resta in coda al file.
- Nell'import massivo particelle/intestatari, valori come `27 sez.B` o `23 sez.C svil.A` nel campo foglio vanno normalizzati separando `foglio` e `sezione` prima del lookup.
- Per le anomalie storiche Arborea/Terralba, non forzare alias locali per sezione (`Arborea C -> Terralba B`). Se il match locale non esiste, il fallback corretto e un lookup live Capacitas senza sezione: prima sul comune richiesto, poi sul comune alternativo (`Arborea <-> Terralba`) se il primo non restituisce risultati.
- Nella pagina `catasto/particelle`, il toggle "Solo particelle con anagrafica" deve essere attivo di default e applicare un filtro backend reale sulla presenza di almeno una `CatUtenzaIrrigua` collegata alla particella. Se l'utente effettua una ricerca puntuale per `foglio + particella`, la riga va comunque restituita anche senza anagrafica e il frontend deve evidenziare esplicitamente lo stato `Senza anagrafica`.
- Nella stessa pagina `catasto/particelle`, il filtro `Codice fiscale / Intestatario` deve eseguire una ricerca parziale unificata sui campi dell'utenza irrigua (`cat_utenze_irrigue.codice_fiscale`, `denominazione`) e sugli intestatari annuali collegati (`cat_utenza_intestatari.codice_fiscale`, `partita_iva`, `denominazione`), cosi da trovare anche prefissi come le prime lettere del codice fiscale.
- Nella pagina `catasto/particelle` il toggle "Visualizza solo particelle a ruolo" deve applicare un filtro backend reale, non un filtro locale sul dataset gia caricato: la sorgente canonica e la presenza di almeno una riga in `ruolo_particelle` con `catasto_parcel_id = cat_particelle.id`.
- Nell'elaborazione massiva `catasto/elaborazioni-massive`, per il tracciato `Comune/Foglio/Particella/Intestatari` il campo `comune` deve accettare tre forme equivalenti: nome comune, `cod_comune_capacitas` numerico oppure codice catastale/Belfiore (es. `A357`).
- Nella pagina `catasto/gis`, i controlli di `Archivio layer salvati` per riempimento e opacita devono riflettere prima di tutto lo stato reale del layer gia caricato in mappa; se l'utente li usa su un layer non ancora caricato, il frontend deve caricare automaticamente quel layer in mappa applicando subito il valore scelto.
- Nella `Vista estesa` di `catasto/gis` i controlli operativi devono stare in una sidebar destra dedicata, cosi la mappa conserva piu altezza utile sul comprensorio verticale: il menu `Layer visibili` deve restare disponibile con gli stessi toggle di distretti, particelle, riempimento e highlight della sidebar standard, mentre `Disegna area` va spostato fuori dall'header dentro la stessa sidebar.
- Per modifiche a batch, credenziali, CAPTCHA, richieste singole o avanzamento runtime, verificare sempre anche `domain-docs/elaborazioni/docs/`.
- Non usare i documenti storici come sorgente primaria per implementazioni nuove.
- Se un file viene mantenuto solo per compatibilita, segnalarlo esplicitamente nel blocco iniziale del documento.
- I file-ponte compatibili restano nella root di `docs/`; i documenti storici non piu operativi vanno spostati in `docs/archive/`.
