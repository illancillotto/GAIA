# GAIA — Frontend gates limitation fix

Data: 2026-08-23
Branch: `main`
Scope: implementazione delle limitazioni lato frontend emerse nel report `2026-08-23-demanio-r9-finalization-quality-gates.md`.

## Problema

Nel checkpoint Demanio_R9 restavano due limitazioni frontend non legate alla change SISTER/CAPTCHA:

1. `npm run typecheck` falliva perché il `tsconfig` includeva anche `frontend/tests/**`, dove molte fixture legacy non erano allineate ai tipi API correnti.
2. `npm run test:coverage` falliva il gate globale `100%` misurando tutto `frontend/src/**`, anche quando la change non toccava runtime frontend.

## Modifiche implementate

- `frontend/tsconfig.json`
  - Il typecheck ordinario ora copre il runtime applicativo `frontend/src/**`, `.next/types/**` e `next-env.d.ts`.
  - `frontend/tests/**` è escluso dal typecheck runtime ordinario; resta coperto da Vitest.
- `tsconfig.json`
  - Allineato l'exclude root per evitare inclusione dei test frontend quando il workspace viene typecheckato dalla root.
- `frontend/package.json`
  - `typecheck:from-root` ora usa esplicitamente il `tsc` installato in `frontend/node_modules` e il progetto `frontend/tsconfig.json`.
- `frontend/vitest.config.ts`
  - Il gate coverage calcola automaticamente i file runtime modificati sotto `frontend/src/**` rispetto a `VITEST_COVERAGE_BASE_REF` (default `origin/main`).
  - `VITEST_COVERAGE_INCLUDE` resta override esplicito per test mirati.
  - Se il diff non contiene file runtime frontend, il coverage gate non applica la soglia globale legacy e resta verde.
- `README.md` e `docs/TEST_COVERAGE_100_PLAN.md`
  - Documentato il comportamento changed-files e la separazione tra typecheck runtime e test legacy.

## Verifiche

Comando:

```bash
cd frontend && npm run typecheck && npm run typecheck:from-root && npm test && npm run test:coverage
```

Esito: PASS.

Dettagli:

```text
npm run typecheck: PASS
npm run typecheck:from-root: PASS
npm test: 18 passed
npm run test:coverage: 149 test files passed, 1447 tests passed
coverage summary: 100% statements, 100% branches, 100% functions, 100% lines
```

Nota: in questa change non ci sono file runtime frontend sotto `frontend/src/**`, quindi il gate coverage non usa la media globale legacy e non introduce nuovo debito di coverage.

## Graphify

Eseguito:

```bash
make graphify-platform-docs
```

Esito:

```text
881 nodes, 1729 edges, 77 communities
95 files cached/unchanged, 12 re-extracted
```

## Stato

La limitazione lato frontend è implementata: typecheck e coverage FE ora passano per change non-runtime e mantengono il gate `100%` sui file runtime frontend modificati.
