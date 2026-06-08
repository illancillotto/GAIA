# Progress — GAIA Catasto: Letture contatori irrigui

> Percorso consigliato: `domain-docs/catasto/docs/PROGRESS_letture_contatori.md`

## Stato generale

Stato: **implementazione base completata**

La funzionalità risulta implementata nel runtime Catasto per il perimetro fase 1: validazione/import Excel, persistenza, linking anagrafico, consultazione da Catasto e sezione dedicata nel dettaglio utente.

Aggiornamento operativo `2026-06-08`:

- import annualità `2023` eseguito con esito positivo nel runtime locale;
- flusso import letture irrigue hardenizzato sui casi emersi dai file reali `2023/2024`:
  - esclusione fogli ausiliari/duplicativi (`PIVOT`, `LAVORATE`, `TOTALE`, simili);
  - supporto ai filename composti reali tipo `D29-1_Uras_...`;
  - normalizzazione coerente della `matricola` in upsert;
  - serializzazione sicura di `date` nel payload snapshot;
  - troncamento difensivo dei campi testo bounded;
  - esclusione lato frontend dei file temporanei Excel `~$...`.

## Decisioni approvate

| Decisione | Stato |
|---|---|
| Usare il nuovo file Excel come tracciato di riferimento | approvata |
| Usare `COD FISCALE` / `COD. FISC` per aggancio alle utenze | approvata |
| Non usare `ID` Excel come chiave affidabile | approvata |
| Usare `anno + distretto + punto_consegna` come chiave tecnica | approvata |
| Mostrare le letture nel dettaglio utente | approvata |
| Predisporre il modello per GAIA Mobile | approvata |
| Prima fase basata su import Excel | approvata |

## Attività

### Documentazione

| Attività | Stato | Note |
|---|---|---|
| PRD funzionale | completato | documento operativo disponibile |
| Implementation Plan | completato | piano operativo aggiunto alla cartella letture |
| Prompt Codex | completato | pronto per sviluppo |
| Aggiornamento PRD Catasto principale | completato | riferimento sintetico aggiunto |

### Backend

| Attività | Stato | Note |
|---|---|---|
| Analisi struttura Catasto esistente | completato | allineata a route/models/schemas reali del repository |
| Definizione tabelle | completato | `catasto_meter_reading_imports`, `catasto_meter_readings` |
| Migration Alembic | completato | con vincolo unico e indici principali |
| Parser Excel | completato | supporto alias colonne e header autodetect |
| Hardening parser/import su file reali 2023/2024 | completato | gestione fogli ausiliari, filename composti, matricole placeholder/case-variant, payload JSON con date |
| Validatore dati | completato | errori bloccanti e warning fase 1 |
| Linking utenze tramite CF | completato | linking verso `ana_subjects` via CF normalizzato |
| API import validate | completato | validazione senza salvataggio |
| API import definitivo | completato | modalità `import/upsert/replace` |
| API lista letture | completato | con filtri base e paginazione |
| API dettaglio lettura | completato | singolo record |
| API letture per soggetto | completato | per dettaglio utenza |
| Test backend | completato | parser, import, linking, API principali |

### Frontend

| Attività | Stato | Note |
|---|---|---|
| API client Catasto letture | completato | integrato nel client Catasto esistente |
| Pagina `Contatori irrigui` | completato | route Catasto dedicata |
| Pannello import Excel | completato | upload multiplo, deduzione distretto da filename, validazione + import sequenziale |
| Esclusione file temporanei `~$...` | completato | il frontend li ignora e mostra avviso esplicito all'operatore |
| Report anomalie import | completato | report sintetico preview per-file |
| Tabella letture | completato | filtri base e apertura dettaglio |
| Drawer dettaglio lettura | completato | dati completi e validazione |
| Sidebar Catasto | completato | voce `Contatori irrigui` aggiunta |
| Sezione dettaglio utente | completato | consume API Catasto per soggetto |
| Test frontend | parziale | Playwright `catasto-meter-readings.spec.ts` eseguito con esito positivo nel runtime locale |
| Test backend | parziale nel runtime locale | suite `pytest -k meter_readings` bloccata in collection per dependency mancante `shapely`, non per errore funzionale del flusso letture |

### GAIA Mobile

| Attività | Stato | Note |
|---|---|---|
| Predisposizione campo `source` | pianificato | `excel`, `mobile`, `manual` |
| Predisposizione campi sync | pianificato | non attivare subito |
| Sessioni lettura mobile | futuro | fase successiva |
| Offline mode | futuro | fase successiva |
| Foto/GPS | futuro | fase successiva |

## Rischi tecnici

| Rischio | Impatto | Mitigazione |
|---|---|---|
| Tracciati Excel non uniformi fra distretti | alto | parser con alias e validazione header |
| CF mancanti o anomali | medio | import con warning e lista record non agganciati |
| Utenze duplicate per stesso CF | medio | warning ambiguità e non aggancio automatico |
| Reimport accidentali | medio | file hash + vincolo anno/distretto/punto |
| Uso improprio dell'ID Excel | alto | salvare solo come campo informativo |
| Evoluzione verso mobile | medio | campi `source` e sync già previsti |

## Prossimo step consigliato

1. Eseguire test frontend mirati sulle nuove route Catasto e sulla sezione in `utenze/[id]`.
2. Valutare KPI/dashlet dedicati per consumi e warning in homepage Catasto.
3. Stabilire eventuali regole aggiuntive su replace logico, storicizzazione e reimport duplicati.
