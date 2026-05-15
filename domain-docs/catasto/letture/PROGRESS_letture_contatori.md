# Progress — GAIA Catasto: Letture contatori irrigui

> Percorso consigliato: `domain-docs/catasto/docs/PROGRESS_letture_contatori.md`

## Stato generale

Stato: **pianificato**

La funzionalità non risulta ancora implementata nel runtime. Il presente documento traccia le attività necessarie per portare in GAIA la gestione delle letture contatori oggi gestite tramite file Excel distrettuali.

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
| PRD funzionale | completato | documento iniziale predisposto |
| Implementation Plan | completato | documento iniziale predisposto |
| Prompt Codex | completato | pronto per sviluppo |
| Aggiornamento PRD Catasto principale | da fare | aggiungere sezione sintetica |

### Backend

| Attività | Stato | Note |
|---|---|---|
| Analisi struttura Catasto esistente | da fare | verificare modelli e router esistenti |
| Definizione tabelle | pianificato | `catasto_meter_reading_imports`, `catasto_meter_readings` |
| Migration Alembic | da fare | includere vincolo unico |
| Parser Excel | da fare | supporto alias colonne |
| Validatore dati | da fare | errori e warning |
| Linking utenze tramite CF | da fare | usare CF normalizzato |
| API import validate | da fare | validazione senza salvataggio |
| API import definitivo | da fare | modalità import/upsert/replace |
| API lista letture | da fare | con filtri |
| API dettaglio lettura | da fare | singolo record |
| API letture per soggetto | da fare | per dettaglio utenza |
| Test backend | da fare | parser, import, linking |

### Frontend

| Attività | Stato | Note |
|---|---|---|
| API client Catasto letture | da fare | `catasto-meter-readings.ts` |
| Pagina `Contatori irrigui` | da fare | route Catasto |
| Pannello import Excel | da fare | upload + validazione |
| Report anomalie import | da fare | warning/errori |
| Tabella letture | da fare | filtri e paginazione |
| Drawer dettaglio lettura | da fare | dati completi |
| Sidebar Catasto | da fare | aggiungere voce |
| Sezione dettaglio utente | da fare | mostrare letture collegate |
| Test frontend | da fare | smoke + eventuali component test |

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

1. Verificare nel repository i modelli esistenti del dominio Utenze/Anagrafica per individuare il campo CF ufficiale.
2. Creare migration e modelli Catasto.
3. Implementare parser Excel con fixture reale `D01-Sinis 2025.xlsx`.
4. Implementare validazione e report anomalie.
5. Implementare linking utenze.
6. Integrare pagina Catasto e dettaglio utente.
