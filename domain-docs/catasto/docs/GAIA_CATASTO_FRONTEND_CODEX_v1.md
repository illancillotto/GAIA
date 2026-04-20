# GAIA — Modulo Catasto
## Frontend Implementation Prompt v1 (Fase 1)
### Per Cursor / Claude Code

---

## Contesto

Stai lavorando su **GAIA**, frontend Next.js 14 con App Router.
Repository: `github.com/illancillotto/GAIA`
Frontend path: `frontend/src/app/catasto/`
Documentazione di riferimento: `domain-docs/catasto/docs/GAIA_CATASTO_ARCHITECTURE_v1.md`

Usa i pattern di componenti, hook e chiamate API già presenti nel progetto.
Non modificare layout, navigazione o componenti di altri moduli.
**Non aggiungere ancora MapLibre GL** — viene in Fase 2.

---

## Step F1 — Tipi TypeScript e client API

Crea `frontend/src/types/catasto.ts`:

```typescript
export interface CatDistretto {
  id: string;
  num_distretto: string;
  nome_distretto: string;
  decreto_istitutivo?: string;
  attivo: boolean;
  note?: string;
}

export interface CatDistrettoKpi {
  distretto_id: string;
  anno: number;
  n_particelle: number;
  sup_catastale_totale_mq: number;
  sup_irrigabile_totale_mq: number;
  importo_totale_0648: number;
  importo_totale_0985: number;
  n_consorziati: number;
  n_anomalie_aperte: number;
  n_anomalie_error: number;
}

export interface CatParticella {
  id: string;
  national_code?: string;
  cod_comune_istat: number;
  nome_comune: string;
  foglio: string;
  particella: string;
  subalterno?: string;
  cfm?: string;
  superficie_mq?: number;
  num_distretto?: string;
  nome_distretto?: string;
  fuori_distretto: boolean;
  is_current: boolean;
  suppressed: boolean;
}

export interface CatUtenzeIrrigua {
  id: string;
  anno_campagna: number;
  cco?: string;
  num_distretto?: number;
  nome_distretto_loc?: string;
  nome_comune: string;
  foglio: string;
  particella: string;
  subalterno?: string;
  sup_catastale_mq?: number;
  sup_irrigabile_mq?: number;
  ind_spese_fisse?: number;
  imponibile_sf?: number;
  esente_0648: boolean;
  aliquota_0648?: number;
  importo_0648?: number;
  aliquota_0985?: number;
  importo_0985?: number;
  denominazione?: string;
  codice_fiscale?: string;
  ha_anomalie: boolean;
}

export interface CatAnomalia {
  id: string;
  particella_id?: string;
  utenza_id?: string;
  anno_campagna?: number;
  tipo: string;
  severita: "error" | "warning" | "info";
  descrizione?: string;
  dati_json?: Record<string, unknown>;
  status: "aperta" | "in_revisione" | "chiusa" | "segnalazione_inviata" | "ignorata";
  note_operatore?: string;
  assigned_to?: number;
  created_at: string;
}

export interface CatImportBatch {
  id: string;
  filename: string;
  tipo: string;
  anno_campagna?: number;
  righe_totali: number;
  righe_importate: number;
  righe_anomalie: number;
  status: "processing" | "completed" | "failed" | "replaced";
  report_json?: ImportReport;
  errore?: string;
  created_at: string;
  completed_at?: string;
}

export interface ImportReport {
  anno_campagna: number;
  righe_totali: number;
  righe_importate: number;
  righe_con_anomalie: number;
  anomalie: Record<string, { count: number; severita: string }>;
  preview_anomalie: Array<Record<string, unknown>>;
  distretti_rilevati: number[];
  comuni_rilevati: string[];
}

export type AnomaliaStatus = CatAnomalia["status"];
export type AnomaliaSeverita = CatAnomalia["severita"];
```

Crea `frontend/src/lib/api/catasto.ts` con funzioni per tutti gli endpoint:

```typescript
import { apiClient } from "@/lib/api/client"; // usa il client axios/fetch esistente

export const catastoApi = {
  // Distretti
  getDistretti: () => apiClient.get<CatDistretto[]>("/catasto/distretti"),
  getDistretto: (id: string) => apiClient.get<CatDistretto>(`/catasto/distretti/${id}`),
  getDistrettoKpi: (id: string, anno: number) =>
    apiClient.get<CatDistrettoKpi>(`/catasto/distretti/${id}/kpi?anno=${anno}`),

  // Particelle
  getParticelle: (params: Record<string, unknown>) =>
    apiClient.get<{ items: CatParticella[]; total: number }>("/catasto/particelle", { params }),
  getParticella: (id: string) => apiClient.get<CatParticella>(`/catasto/particelle/${id}`),
  getParticellaUtenze: (id: string) =>
    apiClient.get<CatUtenzeIrrigua[]>(`/catasto/particelle/${id}/utenze`),
  getParticellaAnomalie: (id: string) =>
    apiClient.get<CatAnomalia[]>(`/catasto/particelle/${id}/anomalie`),

  // Import
  importCapacitas: (formData: FormData) =>
    apiClient.post<{ batch_id: string }>("/catasto/import/capacitas", formData),
  getImportStatus: (batchId: string) =>
    apiClient.get<CatImportBatch>(`/catasto/import/${batchId}/status`),
  getImportReport: (batchId: string, params?: Record<string, unknown>) =>
    apiClient.get(`/catasto/import/${batchId}/report`, { params }),
  getImportHistory: () => apiClient.get<CatImportBatch[]>("/catasto/import/history"),

  // Anomalie
  getAnomalie: (params: Record<string, unknown>) =>
    apiClient.get<{ items: CatAnomalia[]; total: number }>("/catasto/anomalie", { params }),
  updateAnomalia: (id: string, data: Partial<CatAnomalia>) =>
    apiClient.patch<CatAnomalia>(`/catasto/anomalie/${id}`, data),
};
```

### Acceptance F1
- [ ] Tipi TypeScript senza errori di compilazione
- [ ] `catastoApi` esportato correttamente

---

## Step F2 — Componenti base

Crea `frontend/src/components/catasto/`:

### `AnomaliaStatusBadge.tsx`
Badge colorato per severità anomalia:
- `error` → rosso (usa classi Tailwind `bg-red-100 text-red-800`)
- `warning` → giallo (`bg-yellow-100 text-yellow-800`)
- `info` → blu (`bg-blue-100 text-blue-800`)

### `AnomaliaStatusPill.tsx`
Pill per status workflow:
- `aperta` → arancione
- `in_revisione` → viola
- `chiusa` → grigio
- `segnalazione_inviata` → verde
- `ignorata` → grigio chiaro

### `CfBadge.tsx`
Visualizza un codice fiscale con indicatore di validità:
- Props: `cf: string | null`, `valid: boolean | null`
- Verde con icona checkmark se valid=true
- Rosso con icona X se valid=false
- Grigio se null

### `ImportStatusBadge.tsx`
Badge per status import batch con colori e icone.

### `KpiCard.tsx`
Card riutilizzabile per KPI con:
- Props: `title: string`, `value: string | number`, `subtitle?: string`, `color?: string`, `icon?: ReactNode`
- Design coerente con altri moduli GAIA

### Acceptance F2
- [ ] Componenti renderizzano senza errori
- [ ] Stili Tailwind coerenti con il resto del progetto

---

## Step F3 — Pagina Dashboard `/catasto`

Crea `frontend/src/app/catasto/page.tsx`

Layout:
```
┌─────────────────────────────────────────────────────────┐
│  CATASTO — Anagrafica Catastale Irrigua           [Anno] │
├─────────────────────────────────────────────────────────┤
│  [KPI] Particelle  [KPI] Distretti  [KPI] Anomalie aperte│
│        totali            attivi           (error)        │
├─────────────────────────────────────────────────────────┤
│  Ultimo import: R2025-... · 90k righe · 245 anomalie     │
│  [→ Importa nuovo ruolo]  [→ Gestisci anomalie]          │
├─────────────────────────────────────────────────────────┤
│  DISTRETTI                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                 │
│  │ Dist. 26 │ │ Dist. 28 │ │ Dist. 35 │  ...            │
│  │ Sassu    │ │ Terralba │ │ Zinnigas │                  │
│  │ NNN part.│ │ NNN part.│ │ NNN part.│                  │
│  │ NN anom. │ │ NN anom. │ │ NN anom. │                  │
│  └──────────┘ └──────────┘ └──────────┘                 │
└─────────────────────────────────────────────────────────┘
```

Funzionalità:
- Selector anno campagna in header (default: anno corrente)
- KPI strip calcolata sommando KPI di tutti i distretti
- Cards distretti cliccabili → navigano a `/catasto/distretti/{id}`
- Card "ultimo import" con link rapido al wizard
- Skeleton loading state

---

## Step F4 — Wizard Import `/catasto/import`

Crea `frontend/src/app/catasto/import/page.tsx` con wizard 3 step.

### Step 1 — Upload
```
┌─────────────────────────────────────────────────────────┐
│  Import Ruolo Capacitas                                  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │                                                  │   │
│  │   Trascina qui il file .xlsx                     │   │
│  │   oppure [Sfoglia]                               │   │
│  │                                                  │   │
│  │   Nome file atteso: R{ANNO}-{N}-IRR_Particelle   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  Anno campagna: [2025 ▼]                                 │
│                                                          │
│  ☐ Forza reimport (sostituisce import esistente)         │
│                                                          │
│  [Annulla]                          [→ Avvia Import]     │
└─────────────────────────────────────────────────────────┘
```

Validazione client:
- Estensione file deve essere `.xlsx`
- Nome file deve corrispondere a pattern `R\d{4}-\d+-IRR`
- Anno deve essere 2020-2030

### Step 2 — Progresso
Dopo click "Avvia Import":
- Chiama `POST /catasto/import/capacitas` → ottieni `batch_id`
- Polling ogni 2 secondi su `GET /catasto/import/{batch_id}/status`
- Progress bar animata
- Log live:
  ```
  ✓ File ricevuto (90.234 righe)
  ✓ Validazione colonne
  ⟳ Elaborazione: 45.000 / 90.234 (50%)
  ```
- Stop polling quando `status === 'completed' || status === 'failed'`
- Se `failed`: mostra errore in rosso, pulsante "Torna indietro"

### Step 3 — Report anomalie
Visualizza dopo import completato:

```
Import completato ✓
90.234 righe · 89.456 importate · 1.234 con anomalie

ANOMALIE PER TIPO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
● ERROR (2)
  sup_eccede_catastale    45 righe    [Vedi]
  cf_invalido            320 righe    [Vedi]
● WARNING (2)
  cf_mancante            180 righe    [Vedi]
  comune_invalido          5 righe    [Vedi]
● INFO (1)
  particella_assente     700 righe    [Vedi]

[Export report XLSX]   [→ Vai a Gestione Anomalie]
```

Il bottone "Vedi" apre un drawer con tabella delle anomalie del tipo selezionato (prima pagina, 50 righe).

---

## Step F5 — Lista Distretti `/catasto/distretti`

Crea `frontend/src/app/catasto/distretti/page.tsx`

Tabella con colonne:
| N. Distretto | Nome | Comune | Sup. Irrigabile | Importo 0648 | Importo 0985 | Anomalie | Azioni |
|---|---|---|---|---|---|---|---|

- Selector anno in header
- Click su riga → naviga a `/catasto/distretti/{id}`
- Superfici in ettari (da m²: dividi per 10.000, mostra con 2 decimali)
- Importi in € con separatore migliaia
- Badge anomalie: verde=0, giallo=1-10, rosso=>10

---

## Step F6 — Dettaglio Distretto `/catasto/distretti/[id]`

Crea `frontend/src/app/catasto/distretti/[id]/page.tsx`

Layout:
```
← Distretti

DISTRETTO N. 26 — SASSU (ARBOREA)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Anno: 2025 ▼]

[KPI] N. particelle  [KPI] Sup. irrigabile  [KPI] Importo tot.  [KPI] Anomalie
      1.234                 2.456 ha               €45.678             23

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Particelle] [Anomalie] [Import history]

Tab Particelle:
  Filtri: [Cerca CF / denominazione] [☑ Solo anomalie] [Comune ▼] [Subalterno]
  
  Tabella: Foglio | Particella | Sub | Comune | Proprietario | CF | Sup.Cat | Sup.Irr | Importo | Status
  Click riga → /catasto/particelle/{id}
```

---

## Step F7 — Scheda Particella `/catasto/particelle/[id]`

Crea `frontend/src/app/catasto/particelle/[id]/page.tsx`

Layout a 2 colonne:

```
← Distretto N. 26

PARTICELLA 1/25 — ARBOREA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────────────┐ ┌─────────────────────────────┐
│ DATI CATASTALI      │ │ ANOMALIE                    │
│ Comune: ARBOREA     │ │ ● CF invalido (error)       │
│ Foglio: 1           │ │   FNDGPP6... → checksum err │
│ Particella: 25      │ │   [Ignora] [Verifica Sister]│
│ Sub: —              │ │                             │
│ Superficie: 1,68 ha │ │ ○ Nessuna altra anomalia    │
│ CFM: A357-1-25      │ │                             │
│ Distretto: 26       │ └─────────────────────────────┘
│ FD: No              │
└─────────────────────┘

STORICO TRIBUTI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Anno | Proprietario | CF | Sup.Irr | Ind.SF | Imp.0648 | Imp.0985
2025 | Fiandri G.   | ✓  | 1.68 ha | 1.2    | €61.45   | €43.88
2024 | ...
```

---

## Step F8 — Lista Anomalie `/catasto/anomalie`

Crea `frontend/src/app/catasto/anomalie/page.tsx`

```
GESTIONE ANOMALIE

Filtri: [Tipo ▼] [Severità ▼] [Anno ▼] [Distretto ▼] [Status ▼] [Assegnato a ▼]

Stats: 320 error · 185 warning · 700 info

Tabella:
Tipo | Severità | Anno | Distretto | CF | Denominazione | Foglio/Part. | Status | Assegnato | Azioni

Azioni su riga:
- [Chiudi] [Ignora] [Assegna a me] [Note]
- Click riga → modal dettaglio

Modal dettaglio anomalia:
- Dati tecnici dal campo dati_json
- Area testo per note_operatore
- Selector assegnazione
- Bottoni cambio status
```

Azioni bulk (checkbox multipli selezionati):
- Chiudi selezionate
- Assegna a [utente]
- Ignora selezionate

---

## Step F9 — Layout e navigazione

Crea `frontend/src/app/catasto/layout.tsx`:
- Sidebar o breadcrumb con link: Dashboard | Distretti | Particelle | Anomalie | Import
- Coerente con il layout degli altri moduli GAIA

Aggiungi voce `Catasto` al menu principale di navigazione GAIA (file da individuare nel progetto).

---

## Regole generali frontend

- Usa `@tanstack/react-table` per tutte le tabelle con più di 5 colonne
- Usa `react-hook-form` per tutti i form
- Skeleton loader su ogni pagina che fa fetch async
- Error boundary su ogni route page
- Superfici sempre visualizzate in ettari (m² / 10.000) con 2 decimali
- Importi sempre in € con `Intl.NumberFormat('it-IT', {style:'currency', currency:'EUR'})`
- Date in formato `DD/MM/YYYY`
- Non hard-codare URL API: usa costanti o la funzione `apiClient` esistente
- Tutti i componenti in TypeScript strict, zero `any`
