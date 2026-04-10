# GAIA Operazioni — Segnalazioni Viewer & Import

## Prompt operativo per Cursor / Claude Code

---

## 1. Contesto

Stai lavorando nel repository **GAIA** (`github.com/illancillotto/GAIA`), piattaforma interna del Consorzio di Bonifica dell'Oristanese. Architettura: backend unico FastAPI, frontend unico Next.js, database unico PostgreSQL, monolite modulare.

Il modulo **Operazioni** (`backend/app/modules/operazioni/`) è già implementato con:
- Model SQLAlchemy per `field_report`, `internal_case`, `internal_case_event`, `field_report_category`, `field_report_severity`, `attachment`, ecc.
- API CRUD in `backend/app/modules/operazioni/routes/reports.py` (list, create, get, attachments, cases, events, lookups)
- Frontend in `frontend/src/app/operazioni/segnalazioni/` (lista base e dettaglio)
- 28 tabelle DB, 3 migration applicate, 21 test passanti

**Obiettivo di questo task**: costruire una vista operativa completa per chi verifica le segnalazioni, partendo dai dati attualmente gestiti da un sistema esterno (White Company) che esporta file Excel. L'intervento copre:
1. Endpoint di import Excel → modello GAIA
2. Nuova pagina frontend "Cruscotto Segnalazioni" con quadro operativo immediato
3. Estensioni al modello dati per i campi specifici White non ancora coperti

---

## 2. Analisi dati sorgente (Excel White Company)

### 2.1 Struttura file

Il file Excel ha 21 colonne e una struttura **gerarchica flat**:
- Ogni segnalazione ha un `Codice` numerico univoco
- La riga padre ha `Titolo = "Rottura condotta/Piantone (A-C)"` e contiene i dati principali (stato, segnalatore, area, GPS, responsabili, tempo completamento)
- Le sotto-righe hanno lo stesso `Codice` ma un titolo con suffisso che identifica l'azione:
  - `- Richiesta di intervento`
  - `- Richiesta materiale Magazzino`
  - `- Assegnazione/Riassegnazione incaricato`
  - `- Eseguita riparazione`
  - `- Sopralluogo`
  - `- Contestazione all'utente`
- Le sotto-righe hanno `Stato = null`, `Incarico = "Si"`, e la propria data

### 2.2 Colonne e mapping

| Colonna Excel | Tipo | Mapping GAIA | Note |
|---|---|---|---|
| `Codice` | int | `field_report.external_code` | **NUOVO campo**. ID numerico dal sistema White |
| `Titolo` | str | Parsing: parte base → `field_report_category.name`, suffisso → `internal_case_event.event_type` | Vedi logica sotto |
| `Incarico` | Si/No | Riga padre sempre "No", sotto-azioni sempre "Si" | Discriminante padre/figlio |
| `Note` | str | `field_report.description` (padre) oppure `internal_case_event.note` (figlio) | |
| `Segnalatore` | str | `field_report.reporter_name` | **NUOVO campo** text. Non FK utente perché sono operatori esterni al sistema GAIA |
| `Area` | str | `field_report.area_code` | **NUOVO campo** text. Distretto irriguo (es. "Distr_34_2° Distretto Terralba Lotto Sud") |
| `Data` | str dd/MM/yyyy HH:mm | `field_report.created_at` (padre) / `internal_case_event.event_at` (figlio) | Formato italiano |
| `Pos. sel. lat` | float | `field_report.latitude` | Coordinate GPS segnalazione |
| `Pos. sel. lng` | float | `field_report.longitude` | |
| `Pos. disp. lat/lng` | float | Ignorare | Sempre null nel dataset |
| `Incarichi` | int | `internal_case.total_assignments` | **NUOVO campo** opzionale o calcolato |
| `Incarichi completati` | int | `internal_case.completed_assignments` | **NUOVO campo** opzionale o calcolato |
| `Esito pos.` | int | `internal_case.positive_outcomes` | **NUOVO campo** opzionale |
| `Esito neg.` | int | `internal_case.negative_outcomes` | **NUOVO campo** opzionale |
| `Archiviata` | Si/No | Se "Si" → `internal_case.status = "archived"` | |
| `Data di archiv.` | str | `internal_case.closed_at` se archiviata | |
| `Stato` | str | Mapping: `Completato → resolved`, `In lavorazione → in_progress`, `Non presa in carico → open` | Solo sulla riga padre |
| `Responsabili` | str CSV | `field_report.assigned_responsibles` | **NUOVO campo** text. Lista nomi separati da virgola |
| `Data di complet.` | str | `internal_case.resolved_at` | |
| `Tempo di complet.` | str | `field_report.completion_time_text` | **NUOVO campo** text. Formato "12 ore 46 minuti e 37 secondi" |

### 2.3 Statistiche dataset campione

- 212 segnalazioni uniche, 448 righe totali
- 149 segnalazioni con sotto-azioni, 63 senza
- 28 aree/distretti
- 41 segnalatori
- 3 stati: Completato (111), In lavorazione (60), Non presa in carico (41)
- Solo 3 archiviate
- Sotto-azioni: 88 richieste intervento, 83 richieste magazzino, 32 assegnazioni, 31 riparazioni eseguite

---

## 3. Estensioni modello dati

### 3.1 Migration Alembic — nuovi campi su `field_report`

Aggiungi questi campi alla tabella `field_report` **con una nuova migration**:

```python
# Campi per import White Company
external_code = Column(String(50), nullable=True, index=True, unique=True)  # Codice numerico White
reporter_name = Column(String(200), nullable=True)  # Nome segnalatore testuale (non FK)
area_code = Column(String(200), nullable=True, index=True)  # Distretto irriguo
assigned_responsibles = Column(Text, nullable=True)  # CSV nomi responsabili
completion_time_text = Column(String(200), nullable=True)  # "12 ore 46 minuti..."
completion_time_minutes = Column(Integer, nullable=True)  # Valore parsato in minuti per ordinamento/statistiche
source_system = Column(String(50), nullable=True, default='gaia')  # 'white' | 'gaia' per distinguere provenienza
```

### 3.2 Aggiornamenti model SQLAlchemy

File: `backend/app/modules/operazioni/models/reports.py`

Aggiungi i campi mapped al model `FieldReport` esistente. Non rimuovere nulla di esistente.

### 3.3 Nuovi event_type per `internal_case_event`

I suffissi White mappano a questi `event_type`:
- `richiesta_intervento`
- `richiesta_materiale`
- `assegnazione_incaricato`
- `riparazione_eseguita`
- `sopralluogo`
- `contestazione_utente`

Non serve modificare il modello (è già VARCHAR(50)), solo usare questi valori al momento dell'import.

---

## 4. Endpoint import Excel

### 4.1 Nuovo file route

Crea: `backend/app/modules/operazioni/routes/import_reports.py`

### 4.2 Endpoint

```
POST /api/operazioni/reports/import-white
```

- Multipart form-data con campo `file` (xlsx)
- Richiede utente autenticato
- Parsing Excel con `openpyxl` o `pandas`
- Logica di import:

```
Per ogni Codice univoco nel file:
  1. Cerca se esiste già field_report con external_code = Codice
     - Se esiste: SKIP (non sovrascrivere, log come "already_imported")
     - Se non esiste: procedi
  
  2. Identifica la riga padre (Titolo senza " - ")
  
  3. Crea/trova field_report_category dal titolo base
     (es. "Rottura condotta/Piantone (A-C)" → code="rottura_condotta_piantone_ac")
  
  4. Crea field_report:
     - external_code = Codice
     - report_number = "REP-WHITE-{Codice}"
     - title = Titolo base
     - description = Note dalla riga padre
     - reporter_name = Segnalatore
     - area_code = Area
     - latitude/longitude = Pos. sel. lat/lng
     - assigned_responsibles = Responsabili
     - completion_time_text = Tempo di complet.
     - completion_time_minutes = parse("12 ore 46 minuti e 37 secondi") → 766
     - source_system = "white"
     - status = mapping Stato
     - created_at = parse Data (dd/MM/yyyy HH:mm)
     - reporter_user_id = current_user.id (importatore, non il segnalatore reale)
     - category_id = ID della categoria trovata/creata
     - severity_id = usa severità default "normal" (creala se non esiste)
  
  5. Crea internal_case collegato:
     - case_number = "CAS-WHITE-{Codice}"
     - status = mapping (Completato→resolved, In lavorazione→in_progress, Non presa in carico→open)
     - resolved_at = parse "Data di complet." se presente
     - closed_at = parse "Data di archiv." se Archiviata=Si
  
  6. Collega: field_report.internal_case_id = case.id
  
  7. Per ogni sotto-riga dello stesso Codice:
     Crea internal_case_event:
     - event_type = mapping suffisso (vedi 3.3)
     - event_at = parse Data della sotto-riga
     - note = Note della sotto-riga (può essere null)
     - actor_user_id = null
  
  8. Crea evento iniziale "imported" sulla case
```

### 4.3 Response

```json
{
  "imported": 180,
  "skipped": 32,
  "errors": [],
  "categories_created": ["rottura_condotta_piantone_ac"],
  "total_events_created": 236
}
```

### 4.4 Parsing tempo di completamento

```python
import re

def parse_completion_time(text: str) -> int | None:
    """Parse '12 ore 46 minuti e 37 secondi' → minuti totali."""
    if not text:
        return None
    total_minutes = 0
    ore = re.search(r'(\d+)\s+or[ae]', text)
    minuti = re.search(r'(\d+)\s+minut[io]', text)
    secondi = re.search(r'(\d+)\s+second[io]', text)
    if ore:
        total_minutes += int(ore.group(1)) * 60
    if minuti:
        total_minutes += int(minuti.group(1))
    if secondi:
        total_minutes += 1  # arrotonda a 1 minuto se ci sono secondi
    return total_minutes if total_minutes > 0 else None
```

### 4.5 Parsing data italiana

```python
from datetime import datetime

def parse_italian_datetime(text: str) -> datetime | None:
    """Parse 'dd/MM/yyyy HH:mm' → datetime."""
    if not text:
        return None
    try:
        return datetime.strptime(text.strip(), "%d/%m/%Y %H:%M")
    except ValueError:
        return None
```

### 4.6 Registrazione route

In `backend/app/modules/operazioni/router.py`, aggiungi:
```python
from app.modules.operazioni.routes.import_reports import router as import_reports_router
router.include_router(import_reports_router)
```

---

## 5. Frontend — Cruscotto Segnalazioni

### 5.1 Nuova pagina

Crea: `frontend/src/app/operazioni/segnalazioni/cruscotto/page.tsx`

Questa è la pagina principale per chi verifica le segnalazioni. Deve dare un **quadro operativo completo e immediato**.

### 5.2 Layout della pagina

La pagina è divisa in 4 sezioni verticali:

#### Sezione 1: KPI Strip (sempre visibile in alto)

4 card metriche orizzontali:
- **Totale segnalazioni**: conteggio totale
- **Non prese in carico**: conteggio stato `open`, colore rosso/warning, click filtra lista sotto
- **In lavorazione**: conteggio stato `in_progress`, colore azzurro
- **Completate**: conteggio stato `resolved`, colore verde

#### Sezione 2: Filtri e azioni

Barra orizzontale con:
- **Filtro Stato**: dropdown multi-select (Tutte / Non presa in carico / In lavorazione / Completata)
- **Filtro Area**: dropdown con le 28 aree estratte dai dati, con conteggio per area
- **Filtro Segnalatore**: dropdown con ricerca testuale
- **Range date**: date picker from/to
- **Ricerca testo**: su note, codice, segnalatore
- **Toggle vista**: Lista / Mappa
- **Bottone Import**: apre modale per upload Excel White

#### Sezione 3A: Vista Lista (default)

Tabella con le seguenti colonne, ordinabili:
| Colonna | Contenuto |
|---|---|
| Codice | `external_code` o `report_number` |
| Stato | Badge colorato (rosso=open, azzurro=in_progress, verde=resolved) |
| Titolo / Categoria | Nome categoria segnalazione |
| Area | Distretto irriguo, troncato se lungo |
| Segnalatore | Nome |
| Data | Data creazione, formato dd/MM/yyyy HH:mm |
| Azioni (sotto-azioni) | Conteggio eventi case (es. "4 azioni") con icona expand |
| Tempo | Tempo completamento se presente, altrimenti "—" |
| Responsabili | Primi 2 nomi + badge "+N" se più di 2 |

**Click su riga**: espande inline (accordion) mostrando:
- Note complete della segnalazione
- Timeline delle sotto-azioni con data, tipo evento, nota
- Coordinate GPS come link Google Maps
- Lista completa responsabili

**Paginazione**: 25 per pagina, con navigazione pagine.

#### Sezione 3B: Vista Mappa (alternativa)

Mappa con marker su ogni segnalazione (usa coordinate GPS). Colore marker per stato:
- Rosso: non presa in carico
- Arancione: in lavorazione
- Verde: completata

Click su marker → popup con codice, titolo, stato, segnalatore, data, link a dettaglio.

**Nota implementativa**: la mappa può essere implementata con Leaflet (open source, nessuna API key richiesta) come componente React con `react-leaflet`. Aggiungi al `package.json`: `leaflet` e `react-leaflet`. I tile usano OpenStreetMap. Se Leaflet risulta troppo complesso da integrare nel primo step, la vista mappa può essere differita e la sezione mostra un placeholder "Vista mappa in arrivo".

#### Sezione 4: Statistiche laterali (sidebar opzionale o pannello sotto)

Pannello collassabile con:
- **Top 10 aree** per numero segnalazioni (bar chart orizzontale o lista con barre)
- **Top 10 segnalatori** per numero segnalazioni
- **Distribuzione stati** (donut/pie chart o barre)
- **Tempo medio completamento** per area (solo segnalazioni completate)

I chart possono usare `recharts` (già disponibile nel progetto).

### 5.3 Endpoint backend necessari

Il frontend per il cruscotto ha bisogno di un endpoint dedicato che torni i dati arricchiti. L'endpoint `GET /reports` esistente torna solo `id, report_number, title, status, created_at` — troppo poco.

#### Nuovo endpoint: `GET /api/operazioni/reports/dashboard`

```python
@router.get("/reports/dashboard", response_model=dict)
def reports_dashboard(
    # Stessi filtri di list_reports + filtri nuovi
    status_filter: str | None = None,  # "open,in_progress,resolved" CSV
    area_code: str | None = None,
    reporter_name: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    """Ritorna dati arricchiti per il cruscotto segnalazioni."""
```

Response:
```json
{
  "items": [
    {
      "id": "uuid",
      "external_code": "60067",
      "report_number": "REP-WHITE-60067",
      "title": "Rottura condotta/Piantone (A-C)",
      "description": "Apertura carico 1°vasca...",
      "status": "resolved",
      "area_code": "Distr_34_2° Distretto Terralba Lotto Sud",
      "reporter_name": "Stefano Biancu",
      "latitude": 39.748869,
      "longitude": 8.679270,
      "assigned_responsibles": "Serafino Meloni, Franco Piras, ...",
      "completion_time_text": "12 ore 46 minuti e 37 secondi",
      "completion_time_minutes": 766,
      "created_at": "2026-04-08T18:18:00",
      "resolved_at": "2026-04-09T07:04:00",
      "source_system": "white",
      "case_id": "uuid",
      "case_status": "resolved",
      "events_count": 3,
      "events": [
        {
          "event_type": "richiesta_intervento",
          "event_at": "2026-04-08T18:20:00",
          "note": null
        },
        {
          "event_type": "richiesta_materiale",
          "event_at": "2026-04-08T19:00:00",
          "note": "Tubo DN160"
        }
      ]
    }
  ],
  "total": 212,
  "page": 1,
  "page_size": 25,
  "total_pages": 9,
  "aggregates": {
    "by_status": { "open": 41, "in_progress": 60, "resolved": 111 },
    "by_area": [
      { "area": "Distr_24_Arborea lotto Sud", "count": 63 },
      { "area": "Distr_25_Arborea lotto Nord", "count": 58 }
    ],
    "by_reporter": [
      { "name": "Andrea Madeddu", "count": 48 },
      { "name": "Pietro Spiga", "count": 47 }
    ],
    "avg_completion_minutes": 420,
    "total_with_events": 149,
    "total_without_events": 63
  }
}
```

**Nota**: le aggregazioni `by_area`, `by_reporter`, `avg_completion_minutes` sono calcolate **sull'intero dataset filtrato** (non solo sulla pagina corrente). Per efficienza, se il dataset è piccolo (<5000 record) si possono calcolare in-query. Se cresce, valuta una cache o un endpoint separato `/reports/dashboard/stats`.

### 5.4 Endpoint import (frontend)

Aggiungi al client API frontend (`frontend/src/features/operazioni/api/client.ts`):

```typescript
export async function importWhiteReports(file: File): Promise<{
  imported: number;
  skipped: number;
  errors: string[];
  categories_created: string[];
  total_events_created: number;
}> {
  const formData = new FormData();
  formData.append("file", file);
  // usa lo stesso pattern di upload allegati già presente nel modulo
  const res = await fetch(`${API_BASE}/operazioni/reports/import-white`, {
    method: "POST",
    headers: { Authorization: `Bearer ${getToken()}` },
    body: formData,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
```

### 5.5 Componente modale Import

Crea un componente modale `ImportWhiteModal` in `frontend/src/components/operazioni/import-white-modal.tsx`:
- Drag & drop o file picker per xlsx
- Bottone "Importa"
- Progress/spinner durante upload
- Al termine: mostra riepilogo (importate, saltate, errori)
- Bottone "Chiudi" che triggera refresh della lista

### 5.6 Navigazione

Aggiungi link al cruscotto nella sidebar/navigazione di operazioni:
- Label: "Cruscotto Segnalazioni"
- Path: `/operazioni/segnalazioni/cruscotto`
- Icona: usa un'icona dashboard/chart già disponibile nel progetto

Il cruscotto deve essere raggiungibile anche dalla pagina `/operazioni/segnalazioni/` esistente (aggiungi un bottone/link "Apri cruscotto" in alto).

---

## 6. Vincoli di implementazione

1. **Non modificare** i model/route/pagine esistenti se non per aggiungere campi o link. Le pagine `/operazioni/segnalazioni/` e `/operazioni/segnalazioni/[id]/` devono continuare a funzionare.
2. **Usa i pattern esistenti**: guarda come sono fatte le altre pagine operazioni (collection-layout, hero, metric strip, ecc.). Il cruscotto riusa gli stessi componenti shared.
3. **Migration Alembic**: una sola migration per i nuovi campi. Naming: `add_white_import_fields_to_field_report`.
4. **Test**: aggiungi almeno:
   - Test import endpoint con file xlsx mock (usa `openpyxl` per creare un xlsx in-memory nel test)
   - Test parsing tempo completamento
   - Test parsing data italiana
   - Test dashboard endpoint con filtri
5. **Nessun nuovo servizio/microservizio**. Tutto resta nel monolite modulare.
6. **Nessun refactor** delle route esistenti. Il nuovo endpoint `/reports/dashboard` si aggiunge, non sostituisce `/reports`.
7. **`reporter_name` e `area_code` sono testo libero**, non FK. I segnalatori White non sono utenti GAIA. Le aree irrigue potranno diventare una lookup table in futuro, ma per MVP restano testo.

---

## 7. Sequenza di implementazione

### Step 1: Migration e model
- Crea migration Alembic con i nuovi campi
- Aggiorna model `FieldReport` in `models/reports.py`
- Verifica: `alembic upgrade head` senza errori

### Step 2: Parser e import endpoint
- Crea `routes/import_reports.py` con parsing Excel e logica import
- Crea helper functions per parsing date e tempo
- Registra route nel router
- Verifica: test unitari del parser + test endpoint import con xlsx mock

### Step 3: Endpoint dashboard
- Aggiungi `GET /reports/dashboard` in `routes/reports.py` (o file separato `routes/reports_dashboard.py`)
- Implementa filtri, paginazione, aggregazioni
- Verifica: test endpoint con diversi filtri

### Step 4: Frontend client API
- Aggiungi `getReportsDashboard()` e `importWhiteReports()` in `features/operazioni/api/client.ts`

### Step 5: Pagina cruscotto
- Crea `frontend/src/app/operazioni/segnalazioni/cruscotto/page.tsx`
- Implementa KPI strip, filtri, tabella con accordion
- Implementa modale import
- Aggiungi navigazione

### Step 6: Vista mappa (opzionale, può essere step separato)
- Installa `leaflet` + `react-leaflet`
- Implementa toggle lista/mappa
- Marker colorati per stato

### Step 7: Statistiche
- Pannello con chart (recharts) per distribuzione aree, segnalatori, stati
- Tempo medio completamento

---

## 8. File da creare/modificare

### Nuovi file
```
backend/alembic/versions/xxxx_add_white_import_fields_to_field_report.py
backend/app/modules/operazioni/routes/import_reports.py
backend/app/modules/operazioni/services/import_white.py  (opzionale: logica import separata)
backend/app/modules/operazioni/services/parsing.py  (helpers parse_completion_time, parse_italian_datetime)
backend/tests/test_import_white.py
frontend/src/app/operazioni/segnalazioni/cruscotto/page.tsx
frontend/src/components/operazioni/import-white-modal.tsx
```

### File da modificare
```
backend/app/modules/operazioni/models/reports.py  → aggiungi campi
backend/app/modules/operazioni/routes/reports.py  → aggiungi endpoint dashboard
backend/app/modules/operazioni/router.py  → registra import_reports_router
frontend/src/features/operazioni/api/client.ts  → aggiungi getReportsDashboard(), importWhiteReports()
frontend/src/app/operazioni/segnalazioni/page.tsx  → link al cruscotto
```

---

## 9. Documenti di riferimento

Consulta prima di iniziare:
- `backend/app/modules/operazioni/models/reports.py` — model correnti
- `backend/app/modules/operazioni/routes/reports.py` — route correnti
- `frontend/src/app/operazioni/segnalazioni/page.tsx` — pagina lista corrente
- `frontend/src/app/operazioni/segnalazioni/[id]/page.tsx` — pagina dettaglio corrente
- `frontend/src/components/operazioni/collection-layout.tsx` — componenti UI condivisi
- `domain-docs/operazioni/docs/GAIA_OPERAZIONI_DB_SCHEMA.md` — schema DB completo
- `domain-docs/operazioni/docs/GAIA_OPERAZIONI_API_COMPLETE.md` — API reference
- `backend/tests/test_operazioni_api.py` — test esistenti (usa come riferimento per pattern)

---

## 10. Criteri di accettazione

- [ ] Migration applicabile senza errori su DB esistente
- [ ] Import di un file Excel White crea segnalazioni con case e eventi corretti
- [ ] Import idempotente: re-import dello stesso file non duplica dati
- [ ] Cruscotto mostra KPI, lista filtrabile, dettaglio espandibile
- [ ] Filtri per stato, area, segnalatore, date, testo funzionanti
- [ ] Tempi di completamento parsati e ordinabili
- [ ] Navigazione fluida cruscotto ↔ lista esistente ↔ dettaglio
- [ ] Test backend passano tutti (vecchi + nuovi)
- [ ] `npm run lint` e `npx tsc --noEmit` senza errori frontend
- [ ] Nessun breaking change su pagine/API esistenti
