# Prompt Codex — Frontend modulo GAIA Riordino v2

Lavora nel frontend condiviso di GAIA rispettando queste regole:

- frontend unico Next.js
- nuovo codice SOLO in `frontend/src/app/riordino/` e `frontend/src/components/riordino/`
- UI coerente con gli altri moduli GAIA
- niente app separata
- usa componenti, pattern e convenzioni già presenti nel progetto

## Documenti di riferimento obbligatori
Prima di scrivere codice, leggi:
- `domain-docs/riordino/docs/PRD_riordino_v2.md` — sezioni 13, 14
- `domain-docs/riordino/docs/ARCHITECTURE_riordino_v2.md` — sezione 4 (struttura frontend)
- Pattern e componenti degli altri moduli GAIA come riferimento stile

## Struttura file

```
frontend/src/app/riordino/
├── page.tsx                       # dashboard modulo
├── layout.tsx                     # layout con nav modulo
├── pratiche/
│   ├── page.tsx                   # lista pratiche
│   └── [id]/
│       └── page.tsx               # workspace pratica
└── configurazione/
    └── page.tsx                   # admin config

frontend/src/components/riordino/
├── dashboard/
│   └── DashboardCards.tsx
├── practice-list/
│   ├── PracticeTable.tsx
│   └── PracticeFilters.tsx
├── practice-detail/
│   ├── PracticeHeader.tsx
│   └── PracticeWorkspace.tsx
├── workflow/
│   ├── WorkflowStepper.tsx        # stepper visuale fasi/step
│   ├── StepCard.tsx               # dettaglio singolo step con azioni
│   └── StepDecisionForm.tsx       # form esito step decisionale
├── appeals/
│   └── AppealPanel.tsx            # lista/crea/risolvi ricorsi
├── issues/
│   └── IssuePanel.tsx             # lista/crea/chiudi issue
├── documents/
│   └── DocumentPanel.tsx          # lista/upload/download documenti
├── gis/
│   └── GisPanel.tsx               # lista/crea link GIS
├── timeline/
│   └── TimelinePanel.tsx          # eventi cronologici
├── notifications/
│   └── NotificationBell.tsx       # icona + dropdown notifiche
└── shared/
    ├── StatusBadge.tsx            # badge colore per status
    └── ConfirmDialog.tsx          # dialog conferma azioni distruttive
```

## API client

Crea un typed client in `frontend/src/lib/riordino-api.ts` con tutte le chiamate API dal PRD v2 sezione 14. Usa lo stesso pattern degli altri moduli GAIA (Bearer token, `lib/api.ts` base).

Tipi TypeScript per tutte le entità in `frontend/src/types/riordino.ts`:
- `Practice`, `Phase`, `Step`, `Task`, `Appeal`, `Issue`, `Document`, `ParcelLink`, `PartyLink`, `GisLink`, `Event`, `Notification`
- Enum: `PracticeStatus`, `PhaseStatus`, `StepStatus`, `IssueSeverity`, `AppealStatus`

## Schermate

### 1. Dashboard `/riordino`
`DashboardCards` con dati da `GET /api/riordino/dashboard`:
- Pratiche aperte (totale)
- Pratiche Fase 1 / Fase 2
- Pratiche bloccate
- Issue blocking aperte
- Ultimi 10 eventi (mini-timeline)

### 2. Lista pratiche `/riordino/pratiche`
`PracticeTable` + `PracticeFilters`:
- Colonne: codice, titolo, comune, maglia/lotto, fase, stato, responsabile, data apertura
- Filtri: stato, fase, comune, responsabile, periodo, presenza anomalie
- Ricerca testo su codice/titolo
- Paginazione server-side
- Click riga → workspace pratica

### 3. Workspace pratica `/riordino/pratiche/[id]`
Layout a pannelli (tab o colonne):

**PracticeHeader** (sempre visibile):
- Codice, titolo, stato badge, fase badge, owner
- Comune / Maglia / Lotto
- CTA principali: avanza step, skip, cambia stato pratica
- Indicatore scadenze imminenti

**WorkflowStepper**:
- Vista compatta di tutti gli step della fase corrente
- Colori: verde=done, blu=in_progress, grigio=todo, giallo=blocked, barrato=skipped
- Click su step → espande StepCard

**StepCard** (espandibile):
- Titolo, stato, responsabile, date
- Se decisionale: `StepDecisionForm` con select outcome + notes
- Se requires_document: indicatore doc presente/mancante
- Checklist items (se presenti)
- Azione: "Completa step", "Blocca", "Riapri"

**Tab/Pannelli secondari**:
- **Ricorsi** (solo se Fase 1): `AppealPanel` con lista, form creazione, azione risoluzione
- **Issue**: `IssuePanel` con lista filtrata per severità, form creazione, chiusura
- **Documenti**: `DocumentPanel` con lista per fase/step, upload drag-and-drop, download, delete
- **Soggetti/Particelle**: lista read-only con link a modulo utenze
- **GIS**: `GisPanel` con lista link manuali, form creazione
- **Timeline**: `TimelinePanel` con eventi ordinati desc, filtrabili per tipo

### 4. Configurazione `/riordino/configurazione`
Solo ruolo admin:
- CRUD step templates (tabella editabile)
- CRUD document types
- CRUD issue types

## UX specifiche

### Status badge colori
| Status | Colore |
|--------|--------|
| draft | grigio |
| open / in_progress / todo | blu |
| blocked | arancione |
| done / completed | verde |
| skipped | grigio chiaro barrato |
| archived | grigio scuro |
| issue blocking | rosso |
| issue high | arancione |

### Scadenze
- Se scadenza < 7gg: badge rosso "Scadenza imminente" nel header pratica
- Se scadenza < 30gg: badge giallo "In scadenza"

### Loading/error/empty states
- Skeleton loader per tabelle e pannelli
- Toast per errori API
- Empty state con CTA per pannelli vuoti (es. "Nessun ricorso. Aggiungi ricorso")
- Optimistic locking: se 409 Conflict, mostra dialog "Dati modificati da altro utente, ricaricare?"

### Conferme
- Dialog conferma per: skip step, delete pratica, delete documento, archive pratica, chiusura fase
- Nessuna conferma per: advance step (azione frequente)

## Output atteso
- Route frontend funzionanti
- Componenti tipizzati e riusabili
- UI coerente con GAIA
- Flusso pratico usabile da operatori reali
- `npm run lint` e `npx tsc --noEmit` verdi
