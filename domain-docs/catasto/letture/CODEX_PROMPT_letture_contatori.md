# Codex Prompt — GAIA Catasto: Letture contatori irrigui

> Percorso consigliato: `domain-docs/catasto/docs/CODEX_PROMPT_letture_contatori.md`

## Prompt

Devi implementare nel progetto GAIA la funzionalità **Letture contatori irrigui** nel modulo Catasto.

## Contesto architetturale

GAIA è un monolite modulare:

- backend unico FastAPI;
- database unico PostgreSQL;
- migration Alembic uniche;
- frontend unico Next.js/React/TypeScript/TailwindCSS.

Regole repository:

- nuovo codice backend di dominio in `backend/app/modules/catasto/`;
- frontend in `frontend/src/app/catasto/` e `frontend/src/components/catasto/`;
- documentazione in `domain-docs/catasto/docs/`;
- non creare un backend separato;
- non usare `modules/` per codice applicativo.

## Obiettivo

Implementare import, archiviazione, validazione, consultazione e collegamento alle utenze delle letture contatori irrigui provenienti da file Excel distrettuali.

Ogni file Excel rappresenta un distretto e un anno.

Esempio:

```text
D01-Sinis 2025.xlsx
```

## Logica funzionale

Il nuovo file Excel contiene dati su:

- punto di consegna;
- matricola contatore;
- sigillo;
- tipologia idrante;
- firmware;
- batteria;
- lettura iniziale;
- lettura finale;
- consumo;
- data lettura;
- operatore lettura;
- interventi;
- D.U.I.;
- codice fiscale;
- coltura;
- tariffa;
- fondo chiuso;
- note;
- telefono.

Il campo `COD FISCALE` / `COD. FISC` deve essere normalizzato e usato per agganciare la lettura all'utenza/anagrafica soggetto.

Nel dettaglio utente deve comparire la sezione:

```text
Letture contatori
```

con tutti i punti di consegna collegati al soggetto.

Non usare il campo `ID` Excel come chiave affidabile.

La chiave tecnica della lettura è:

```text
anno + distretto_id + punto_consegna
```

Ogni lettura deve avere `source`, con valori:

```text
excel
mobile
manual
```

Nella prima fase tutte le letture importate hanno `source = excel`.

## Implementazione backend

Crea o integra i seguenti file:

```text
backend/app/modules/catasto/models/meter_reading.py
backend/app/modules/catasto/models/meter_reading_import.py
backend/app/modules/catasto/schemas/meter_reading.py
backend/app/modules/catasto/services/meter_reading_parser.py
backend/app/modules/catasto/services/meter_reading_validation.py
backend/app/modules/catasto/services/meter_reading_import_service.py
backend/app/modules/catasto/services/meter_reading_linker.py
backend/app/modules/catasto/routers/meter_readings.py
```

Se la struttura esistente usa naming differente, adattati alla convenzione già presente nel repository.

## Tabelle

### `catasto_meter_reading_imports`

Campi minimi:

- `id`
- `distretto_id`
- `anno`
- `filename_originale`
- `file_hash`
- `stato`
- `totale_righe`
- `righe_importate`
- `righe_con_warning`
- `righe_scartate`
- `uploaded_by`
- `uploaded_at`
- `processed_at`
- `error_report`

### `catasto_meter_readings`

Campi minimi:

- `id`
- `import_id`
- `distretto_id`
- `anno`
- `row_number`
- `excel_id`
- `punto_consegna`
- `matricola`
- `sigillo`
- `tipologia_idrante`
- `firmware_version`
- `battery_level`
- `lettura_iniziale`
- `lettura_finale`
- `consumo_mc`
- `data_lettura`
- `operatore_lettura`
- `intervento_da_eseguire`
- `intervento_eseguito`
- `operatore_intervento`
- `data_intervento`
- `dui`
- `codice_fiscale`
- `codice_fiscale_normalizzato`
- `utenza_id`
- `coltura`
- `tariffa`
- `fondo_chiuso`
- `telefono`
- `note`
- `validation_status`
- `validation_messages`
- `source`
- `mobile_session_id`
- `gps_lat`
- `gps_lng`
- `photo_url`
- `offline_created_at`
- `synced_at`
- `sync_status`
- `device_id`
- `mobile_operator_id`
- `created_at`
- `updated_at`

Aggiungi vincolo unico:

```sql
UNIQUE (anno, distretto_id, punto_consegna)
```

## Parser Excel

Il parser deve essere tollerante sui nomi colonna.

Alias da gestire:

| Colonna Excel | Campo interno |
|---|---|
| `ID` | `excel_id` |
| `PUNTO_CONS` / `PUNTO DI CONSEGNA` | `punto_consegna` |
| `COD_CONT` / `MATRIC.` | `matricola` |
| `SIGILLO` | `sigillo` |
| `TIPOLOGIA` / `TIPOLOGIA IDRANTE` | `tipologia_idrante` |
| `LETTURA FINALE 2024` / `lettura iniziale 2025` | `lettura_iniziale` |
| `LETTURA FINALE 2025` | `lettura_finale` |
| `TOTALE m3 2025` / `consumo 2025 tot. M3` | `consumo_mc` |
| `DATA LETTURA` | `data_lettura` |
| `OPERATORE LETTURA` | `operatore_lettura` |
| `INTERVENTO DA ESEGUIRE` | `intervento_da_eseguire` |
| `INTERVENTO ESEGUITO` | `intervento_eseguito` |
| `OPERATORE INTERVENTO` | `operatore_intervento` |
| `DATA INTERVENTO` | `data_intervento` |
| `TITOLARE DUI 2025` / `D.U.I.` | `dui` |
| `COD. FISC` / `COD FISCALE` | `codice_fiscale` |
| `COLTURA` | `coltura` |
| `TARIFFA` | `tariffa` |
| `FONDO CHIUSO` | `fondo_chiuso` |
| `NOTE` | `note` |
| `TELEFONO` | `telefono` |

## Validazioni

Errori bloccanti:

- punto consegna mancante;
- anno mancante;
- distretto mancante e non deducibile;
- duplicato nello stesso file sulla chiave anno/distretto/punto.

Warning:

- CF mancante;
- CF anomalo;
- utenza non trovata;
- più utenze con stesso CF;
- telefono anomalo;
- consumo incoerente;
- lettura finale minore della iniziale;
- intervento da eseguire valorizzato;
- batteria bassa.

## API backend

Implementa endpoint:

```http
POST /api/catasto/meter-readings/import/validate
POST /api/catasto/meter-readings/import
GET  /api/catasto/meter-readings/imports
GET  /api/catasto/meter-readings/imports/{import_id}
GET  /api/catasto/meter-readings
GET  /api/catasto/meter-readings/{id}
GET  /api/catasto/meter-readings/by-subject/{subject_id}
```

Query params per lista:

- `anno`
- `distretto_id`
- `codice_fiscale`
- `punto_consegna`
- `matricola`
- `utenza_id`
- `has_warnings`
- `intervento_da_eseguire`
- `source`
- `page`
- `page_size`

## Implementazione frontend

Crea pagina:

```text
frontend/src/app/catasto/letture-contatori/page.tsx
frontend/src/app/catasto/letture-contatori/import/page.tsx
```

Componenti:

```text
frontend/src/components/catasto/meter-readings-table.tsx
frontend/src/components/catasto/meter-reading-import-panel.tsx
frontend/src/components/catasto/meter-reading-import-report.tsx
frontend/src/components/catasto/meter-reading-detail-drawer.tsx
```

API client:

```text
frontend/src/lib/api/catasto-meter-readings.ts
```

Aggiorna sidebar Catasto con:

```text
Catasto -> Contatori irrigui
```

Nel dettaglio utente integra una sezione:

```text
Letture contatori
```

## Test richiesti

Backend:

- parser Excel;
- alias colonne;
- normalizzazione CF;
- validazione anomalie;
- import validate only;
- import upsert;
- linking utenze;
- API lista e dettaglio.

Frontend:

- render pagina letture;
- upload panel;
- tabella con filtri;
- dettaglio lettura;
- sezione letture nel dettaglio utente.

## Documentazione

Aggiorna o crea:

```text
domain-docs/catasto/docs/PRD_letture_contatori.md
domain-docs/catasto/docs/IMPLEMENTATION_PLAN_letture_contatori.md
domain-docs/catasto/docs/PROGRESS_letture_contatori.md
```

Aggiorna anche `PRD_catasto.md` con un breve riferimento alla nuova sottofunzione.

## Vincoli finali

- Non duplicare il dominio Utenze.
- Mantenere Catasto come proprietario delle letture.
- Il dettaglio utente deve solo consumare l'API Catasto.
- Non usare `ID` Excel come chiave primaria.
- Usare `anno + distretto + punto_consegna` come riferimento tecnico.
- Predisporre il modello dati per GAIA Mobile ma non implementare la mobile app in questa fase.
