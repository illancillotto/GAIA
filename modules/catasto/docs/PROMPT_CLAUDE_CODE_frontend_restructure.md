# Prompt operativo — Ristrutturazione frontend GAIA

> Documento storico.
> Il refactor e' stato completato: il frontend condiviso della piattaforma ora vive in `frontend/`.

---

## Stato finale

Il frontend Next.js di GAIA e' stato promosso a livello root del repository:

```text
GAIA/
├── frontend/
├── modules/
│   ├── accessi/
│   │   ├── backend/
│   │   └── docs/
│   ├── network/
│   │   └── docs/
│   ├── inventory/
│   │   └── docs/
│   └── catasto/
│       ├── docs/
│       └── worker/
├── docker-compose.yml
├── docker-compose.override.yml
└── nginx/
```

## Risultato applicativo

- Il frontend condiviso vive in `frontend/`
- Le route Accessi sono sotto `frontend/src/app/accessi/`
- Le pagine di piattaforma root-level restano in:
  - `frontend/src/app/page.tsx`
  - `frontend/src/app/login/page.tsx`
  - `frontend/src/app/network/page.tsx`
  - `frontend/src/app/inventory/page.tsx`
  - `frontend/src/app/catasto/`
- La navigazione e' stata separata in:
  - `frontend/src/components/layout/platform-sidebar.tsx`
  - `frontend/src/components/layout/module-sidebar.tsx`
- `docker-compose.yml`, `docker-compose.override.yml` e la CI puntano a `frontend/`
- Il package frontend e' `gaia-frontend`
- Il vecchio frontend modulo-specifico e' stato rimosso

## Verifiche eseguite

- `npm test` in `frontend/`
- `npm run build` in `frontend/`
- `docker compose up -d --build --force-recreate frontend nginx`
- verifica runtime su `http://localhost:8080`

## Nota per i moduli futuri

Ogni nuovo modulo GAIA deve aggiungere le proprie pagine nel frontend condiviso:

- Accessi: `frontend/src/app/accessi/`
- Rete: `frontend/src/app/network/`
- Inventario: `frontend/src/app/inventory/`
- Catasto: `frontend/src/app/catasto/`
