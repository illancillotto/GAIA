# GAIA Docs e Struttura File

## Dove si trovano le docs

La documentazione del progetto e distribuita principalmente in due aree:

1. Root del repository: documentazione generale di piattaforma, architettura e piani.
2. `domain-docs/`: documentazione funzionale per dominio/modulo.

## Documentazione generale in root

- `README.md`: overview del progetto, stack, quick start e riferimenti principali.
- `ARCHITECTURE.md`: architettura generale.
- `PRD.md`: product requirements di livello progetto.
- `IMPLEMENTATION_PLAN.md`: piano di implementazione generale.
- `AGENTS.md`: linee guida operative per agenti/tooling.
- `PROMPT_BACKEND.md`: prompt e istruzioni backend.
- `PROMPT_FRONTEND.md`: prompt e istruzioni frontend.
- `PROMPT_DEVOPS.md`: prompt e istruzioni DevOps.
- `PROMPT_CODEX_permissions.md`: note operative sui permessi per Codex.
- `.github/workflows/`: pipeline CI/CD GitHub Actions.
- `backend/app/MONOLITH_MODULAR.md`: note architetturali sul backend monolite modulare.
- `backend/app/modules/inventory/`: modulo backend Inventory con router, modelli, schemi e servizi applicativi.
- `modules/README.md`: note sulla directory `modules/`.

## Documentazione per dominio

### Indice generale

- `domain-docs/README.md`: convenzioni e ruolo della cartella `domain-docs/`.

### Accessi

- `domain-docs/accessi/README.md` non presente
- `domain-docs/accessi/docs/PRD.md`
- `domain-docs/accessi/docs/ARCHITECTURE.md`
- `domain-docs/accessi/docs/IMPLEMENTATION_PLAN.md`
- `domain-docs/accessi/docs/EXECUTION_PLAN.md`
- `domain-docs/accessi/docs/DEPLOYMENT.md`
- `domain-docs/accessi/docs/PROGRESS.md`
- `domain-docs/accessi/docs/CODEX_PROMPT.md`

### Catasto

- `domain-docs/catasto/README.md` non presente
- `domain-docs/catasto/docs/README.md`
- `domain-docs/catasto/docs/PRD_catasto.md`
- `domain-docs/catasto/docs/CATASTO_CONSORTILE.md`
- `domain-docs/catasto/docs/GAIA_CATASTO_ARCHITECTURE_v1.md`
- `domain-docs/catasto/docs/ELABORAZIONI_REFACTOR_PLAN.md`
- `domain-docs/catasto/docs/SISTER_debug_runbook.md`
- `domain-docs/catasto/docs/archive/PROMPT_CODEX_catasto.md`
- `domain-docs/catasto/docs/archive/PROMPT_CLAUDE_CODE_catasto.md`
- `domain-docs/catasto/docs/archive/PROMPT_CLAUDE_CODE_frontend_restructure.md`

### CED

- `domain-docs/ced/docs/PRD.md`
- `domain-docs/ced/docs/IMPLEMENTATION_PLAN.md`
- `domain-docs/ced/docs/CODEX_PROMPT.md`
- `domain-docs/ced/docs/PROGRESS.md`

### Elaborazioni

- `domain-docs/elaborazioni/README.md`
- `domain-docs/elaborazioni/docs/ELABORAZIONI_REFACTOR_PLAN.md`
- `domain-docs/elaborazioni/docs/SISTER_debug_runbook.md`
- `domain-docs/elaborazioni/capacitas/docs/CAPACITAS_integration.md`
- `domain-docs/elaborazioni/capacitas/docs/CAPACITAS_DATA_RECOVERY.md`
- `domain-docs/elaborazioni/whiteCompany/WHITECOMPANY_integration.md`
- `domain-docs/elaborazioni/GAIA_VISURE_PROMPT_1_ANALISI.md`
- `domain-docs/elaborazioni/GAIA_VISURE_PROMPT_2_IMPLEMENTAZIONE.md`
- `domain-docs/elaborazioni/GAIA_VISURE_PROMPT_3_REVIEW.md`

### Inventory

- `domain-docs/inventory/README.md`
- `domain-docs/inventory/docs/PRD_inventory.md`
- `domain-docs/inventory/docs/PROMPT_CODEX_inventory.md`

### Network

- `domain-docs/network/README.md`
- `domain-docs/network/docs/PRD_network.md`
- `domain-docs/network/docs/PROMPT_CODEX_network.md`

### Utenze

- `domain-docs/utenze/README.md` non presente
- `domain-docs/utenze/docs/PRD_anagrafica.md`
- `domain-docs/utenze/docs/PROMPT_CODEX_anagrafica.md`
- `domain-docs/utenze/docs/EXECUTION_PLAN.md`
- `domain-docs/utenze/docs/PROGRESS.md`

### Operazioni

- `domain-docs/operazioni/README.md` non presente
- `domain-docs/operazioni/docs/GAIA_OPERAZIONI_PRD_COMPLETO.md`
- `domain-docs/operazioni/docs/GAIA_OPERAZIONI_EXECUTION_PLAN_COMPLETO.md`
- `domain-docs/operazioni/docs/GAIA_OPERAZIONI_DB_SCHEMA.md`
- `domain-docs/operazioni/docs/GAIA_OPERAZIONI_PROGRESS.md`
- `domain-docs/operazioni/docs/GAIA_OPERAZIONI_API_COMPLETE.md`
- `domain-docs/operazioni/docs/GAIA_OPERAZIONI_PROMPT_BACKEND.md`
- `domain-docs/operazioni/docs/GAIA_OPERAZIONI_PROMPT_FRONTEND.md`
- `domain-docs/operazioni/docs/PROMPT_SEGNALAZIONI_VIEWER.md`
- `domain-docs/operazioni/docs/GAIA_MOBILE_PRD.md`
- `domain-docs/operazioni/docs/GAIA_MOBILE_ARCHITECTURE.md`
- `domain-docs/operazioni/docs/GAIA_MOBILE_EXECUTION_PLAN.md`
- `domain-docs/operazioni/docs/GAIA_MOBILE_SYNC_PROTOCOL.md`
- `domain-docs/operazioni/docs/GAIA_MOBILE_CODEX_PROMPT.md`
- `domain-docs/operazioni/docs/GAIA_MOBILE_REUSE_STRATEGY.md`

### Riordino

- `domain-docs/riordino/docs/PRD_riordino_v2.md`
- `domain-docs/riordino/docs/ARCHITECTURE_riordino_v2.md`
- `domain-docs/riordino/docs/EXECUTION_PLAN_riordino_v2.md`
- `domain-docs/riordino/docs/PROMPT_CODEX_riordino_backend_v2.md`
- `domain-docs/riordino/docs/PROMPT_CODEX_riordino_frontend_v2.md`
- `domain-docs/riordino/docs/PROMPT_CODEX_riordino_fullstack_v2.md`
- `domain-docs/riordino/docs/PROGRESS_riordino_v2.md`

### Ruolo

- `domain-docs/ruolo/docs/PRD_ruolo.md`
- `domain-docs/ruolo/docs/EXECUTION_PLAN_ruolo.md`
- `domain-docs/ruolo/docs/PROGRESS_ruolo.md`
- `domain-docs/ruolo/docs/PROMPT_CODEX_ruolo.md`

## Struttura sintetica del repository

```text
GAIA/
├── .github/
│   └── workflows/
├── .vscode/
│   └── settings.json
├── tsconfig.json
├── backend/
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── jobs/
│   │   ├── models/
│   │   ├── modules/
│   │   │   ├── catasto/
│   │   │   │   ├── models/
│   │   │   │   ├── routes/
│   │   │   │   └── services/
│   │   │   ├── elaborazioni/
│   │   │   ├── inventory/
│   │   │   ├── operazioni/
│   │   │   ├── riordino/
│   │   │   └── shared/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── scripts/
│   │   ├── services/
│   │   └── utils/
│   ├── scripts/
│   └── tests/
│       └── riordino/
├── domain-docs/
│   ├── accessi/
│   │   ├── docs/
│   │   └── frontend/
│   ├── ced/
│   │   └── docs/
│   ├── catasto/
│   │   └── docs/
│   ├── elaborazioni/
│   │   ├── capacitas/
│   │   │   └── docs/
│   │   ├── whiteCompany/
│   │   └── docs/
│   ├── inventory/
│   │   ├── docs/
│   │   └── frontend/
│   ├── network/
│   │   └── docs/
│   ├── operazioni/
│   │   └── docs/
│   ├── riordino/
│   │   └── docs/
│   ├── ruolo/
│   │   └── docs/
│   └── utenze/
│       └── docs/
├── frontend/
│   ├── playwright.config.ts
│   ├── public/
│   ├── scripts/
│   ├── src/
│   │   ├── app/
│   │   │   ├── catasto/
│   │   │   ├── elaborazioni/
│   │   │   ├── operazioni/
│   │   │   ├── ruolo/
│   │   │   └── riordino/
│   │   ├── components/
│   │   │   ├── catasto/
│   │   │   ├── operazioni/
│   │   │   ├── ruolo/
│   │   │   └── riordino/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── services/
│   │   ├── types/
│   │   └── utils/
│   └── tests/
│       ├── e2e/
├── modules/
│   └── elaborazioni/
│       └── worker/
├── nginx/
├── progress/
├── secrets/
│   └── pdnd/
│       └── .gitkeep
├── scripts/
├── AGENTS.md
├── ARCHITECTURE.md
├── IMPLEMENTATION_PLAN.md
├── PRD.md
├── PROMPT_BACKEND.md
├── PROMPT_CODEX_permissions.md
├── PROMPT_DEVOPS.md
├── PROMPT_FRONTEND.md
├── README.md
└── DOCS_STRUCTURE.md
```

## Note utili

- Alla root, `tsconfig.json` estende `frontend/tsconfig.json` e include i sorgenti sotto `frontend/`, così TypeScript e gli editor che aprono il repo da `GAIA/` risolvono correttamente moduli e tipi (es. `react`). La cartella `.vscode/` punta il TypeScript SDK a `frontend/node_modules/typescript`.
- La directory piu importante per la documentazione funzionale e `domain-docs/`.
- La documentazione architetturale generale e concentrata in root e in `backend/app/MONOLITH_MODULAR.md`.
- Il dominio anagrafico usa `domain-docs/utenze/` come posizione canonica della documentazione.
- Nel runtime possono coesistere superfici `anagrafica` e `utenze` per compatibilita applicativa.
- La directory `progress/` contiene file di avanzamento tecnico puntuali per tranche di lavoro e non sostituisce PRD, README o documentazione di dominio.
- La directory `secrets/pdnd/` e destinata solo a chiavi locali non versionate usate dal backend in sviluppo, ad esempio `private_key.pem`.
