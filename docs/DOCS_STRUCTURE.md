# GAIA Docs e Struttura File

> Audit documentale: 2026-07-10.
> Questo file e un indice curato delle fonti principali, non la lista completa di
> tutti i Markdown del repository. Al 2026-07-10 i Markdown operativi censiti in
> `docs/`, `domain-docs/` e `modules/` sono circa 200 escludendo `node_modules`,
> `graphify-out` e output generati. Per discovery completa usare `find`/`rg` con
> le esclusioni standard.

## Dove si trovano le docs

La documentazione del progetto e distribuita principalmente in due aree:

1. `docs/`: documentazione generale di piattaforma, architettura e piani.
2. `domain-docs/`: documentazione funzionale per dominio/modulo.

Nella root del repository resta solo `README.md` (entry point del progetto).
Le procedure operative piu usate lato DevOps e dati vivono inoltre nei file `scripts/*.sh`, richiamati dal `README.md`.
In root e presente anche `AGENTS.md` per le regole operative repository-level usate dagli agenti.

## Documentazione generale in docs/

- `docs/ARCHITECTURE.md`: architettura generale.
- `docs/PRD.md`: product requirements di livello progetto.
- `docs/IMPLEMENTATION_PLAN.md`: piano di implementazione generale.
- `docs/TEST_COVERAGE_100_PLAN.md`: policy e piano operativo per portare il codice runtime a coverage totale.
- `docs/AGENTS.md`: linee guida operative per agenti/tooling.
- `docs/PROMPT_BACKEND.md`: prompt e istruzioni backend.
- `docs/PROMPT_FRONTEND.md`: prompt e istruzioni frontend.
- `docs/PROMPT_DEVOPS.md`: prompt e istruzioni DevOps.
- `docs/PROMPT_CODEX_permissions.md`: note operative sui permessi per Codex.
- `docs/SECURITY.md`: note di sicurezza.
- `docs/CATASTO_INDICI_RUOLO_REALE_2026-07-09.md`: intervento su indici Catasto, ruolo reale inCASS e riconciliazione distretti.
- `docs/INCASS_*`: report e runbook operativi sul ripopolamento/materializzazione inCASS.
- `docs/PRESENZE_*`: piani e decisioni storiche sul rename Inaz -> Presenze.
- `docker-compose.local-gateway.yml`: stack Docker dedicato al reverse proxy locale condiviso tra progetti.
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

- `domain-docs/catasto/docs/README.md`
- `domain-docs/catasto/docs/PRD_catasto.md`
- `domain-docs/catasto/docs/CATASTO_CONSORTILE.md`
- `domain-docs/catasto/docs/PUNTI_CONSEGNA_GIS_GATE_2026.md`
- `domain-docs/catasto/letture/README.md`
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
- `domain-docs/elaborazioni/docs/RUOLO_VISURE_AUTOSYNC_PLAN.md`
- `domain-docs/elaborazioni/docs/SISTER_debug_runbook.md`
- `domain-docs/elaborazioni/capacitas/docs/CAPACITAS_integration.md`
- `domain-docs/elaborazioni/capacitas/docs/CAPACITAS_DATA_RECOVERY.md`
- `domain-docs/elaborazioni/sister/SISTER_WORKER_INTEGRATION_REPORT.md`
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

### Presenze

- `domain-docs/presenze/docs/GAIA_GATE_PRESENZE_INTEGRATION_BLUEPRINT.md`
- `domain-docs/presenze/docs/GAIA_PRESENZE_GIORNALIERE_MODULE_SPEC.md`
- `domain-docs/presenze/docs/IMPLEMENTATION_PRESENZE_COLLABORATORI_GIORNALIERE.md`
- `domain-docs/presenze/docs/CCNL_MAJORAZIONI_AUDIT_2026.md`
- `domain-docs/presenze/docs/PROGRESS_PRESENZE.md`
- `domain-docs/presenze/docs/INAZ_FUNZIONI_E_REGOLE.md`
- `domain-docs/presenze/docs/PRESENZE_PROGETTO_DEDICATO_IMPLEMENTATION_PLAN.md`

### Utenze

- `domain-docs/utenze/docs/PRD_anagrafica.md`
- `domain-docs/utenze/docs/PRD_PDND_ANPR_DECESSI.md`
- `domain-docs/utenze/docs/ARCH_PDND_ANPR_DECESSI.md`
- `domain-docs/utenze/docs/CURSOR_PROMPT_PDND_ANPR.md`
- `domain-docs/utenze/docs/PROMPT_CODEX_anagrafica.md`
- `domain-docs/utenze/docs/EXECUTION_PLAN.md`
- `domain-docs/utenze/docs/PROGRESS.md`
- `domain-docs/utenze/docs/PROGRESS_ANPR.md`

Nota: il dominio Anagrafica e confluito operativamente in `utenze`. I path
`anagrafica/*` ancora presenti nel frontend sono legacy/redirect o superfici di
compatibilita; il backend canonico e `backend/app/modules/utenze/`.

### Operazioni

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
- `domain-docs/operazioni/docs/GAIA_GATE_MOBILE_SYNC_RUNBOOK.md`
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
- `domain-docs/ruolo/docs/STATISTICHE_ruolo.md`
- `domain-docs/ruolo/docs/RUOLO_DMP_DECOMMISSION_PLAN.md`
- `domain-docs/ruolo/docs/RUOLO_READ_MODEL_AUDIT_2026-06-16.md`
- `domain-docs/ruolo/docs/RUOLO_2025_INCASS_GRIGLIA_PARTITARIO_DIFF_2026-07-10.md`

Nota: diversi documenti Ruolo sono storici. Per lo stato corrente dare priorita
al PRD aggiornato, ai report inCASS recenti e al codice runtime.

### Wiki Agent (Milestone 9)

- `domain-docs/wiki/README.md`
- `domain-docs/wiki/docs/PRD_wiki.md`
- `domain-docs/wiki/docs/IMPLEMENTATION_PLAN_wiki.md`
- `domain-docs/wiki/docs/IMPLEMENTATION_PLAN_wiki_live_agent.md`
- `domain-docs/wiki/docs/GAIA_OPERATIONAL_WIKI_ARCHITECTURE.md`
- `domain-docs/wiki/docs/PROMPT_CODEX_wiki.md`
- `domain-docs/wiki/operational/README.md`
- `domain-docs/wiki/operational/modules/*.md`
- `domain-docs/wiki/operational/pages/*.md`
- `domain-docs/wiki/operational/workflows/*.md`

## Struttura sintetica del repository

```text
GAIA/
├── AGENTS.md               ← regole operative repository-level per agenti/tooling
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
│   │   │   ├── accessi/
│   │   │   ├── catasto/
│   │   │   ├── elaborazioni/
│   │   │   ├── inventory/
│   │   │   ├── network/
│   │   │   ├── operazioni/
│   │   │   ├── organigramma/
│   │   │   ├── presenze/
│   │   │   ├── riordino/
│   │   │   ├── ruolo/
│   │   │   ├── shared/
│   │   │   ├── utenze/
│   │   │   └── wiki/
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
│   ├── organigramma/
│   │   └── docs/
│   ├── presenze/
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
│   │   │   ├── anagrafica/
│   │   │   ├── catasto/
│   │   │   ├── elaborazioni/
│   │   │   ├── inventory/
│   │   │   ├── network/
│   │   │   ├── operazioni/
│   │   │   ├── organigramma/
│   │   │   ├── presenze/
│   │   │   ├── riordino/
│   │   │   ├── ruolo/
│   │   │   ├── utenze/
│   │   │   └── wiki/
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
│   ├── nginx.conf
│   └── local-dev-gateway.conf
├── progress/
├── secrets/
│   └── pdnd/
│       └── .gitkeep
├── scripts/
│   ├── setup-local-domain.sh
│   └── setup-local-dev-gateway.sh
├── AGENTS.md
├── docker-compose.local-gateway.yml
├── README.md
└── docs/
    ├── ARCHITECTURE.md
    ├── DOCS_STRUCTURE.md
    ├── IMPLEMENTATION_PLAN.md
    ├── PRD.md
    ├── PROMPT_BACKEND.md
    ├── PROMPT_CODEX_permissions.md
    ├── PROMPT_DEVOPS.md
    └── PROMPT_FRONTEND.md
```

## Note utili

- Alla root, `tsconfig.json` estende `frontend/tsconfig.json` e include i sorgenti sotto `frontend/`, così TypeScript e gli editor che aprono il repo da `GAIA/` risolvono correttamente moduli e tipi (es. `react`). La cartella `.vscode/` punta il TypeScript SDK a `frontend/node_modules/typescript`.
- La directory piu importante per la documentazione funzionale e `domain-docs/`.
- La documentazione architetturale generale e concentrata in root e in `backend/app/MONOLITH_MODULAR.md`.
- Il dominio anagrafico usa `domain-docs/utenze/` come posizione canonica della documentazione.
- Nel runtime possono coesistere superfici `anagrafica` e `utenze` per compatibilita applicativa.
- La directory `progress/` contiene file di avanzamento tecnico puntuali per tranche di lavoro e non sostituisce PRD, README o documentazione di dominio.
- La directory `secrets/pdnd/` e destinata solo a chiavi locali non versionate usate dal backend in sviluppo, ad esempio `private_key.pem`.
