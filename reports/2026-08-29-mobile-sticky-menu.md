# GAIA — menu mobile persistente durante lo scroll

**Data:** 2026-08-29  
**Stato:** PASS — implementato, verificato e distribuito su `serverCed`

## Richiesta

Mantenere disponibile il pulsante di apertura della navigazione mobile anche dopo aver scrollato la pagina.

## Diagnosi

Il topbar GAIA era già configurato correttamente con:

```text
sticky top-0
```

Il pulsante mobile era già contenuto nel topbar e nascosto correttamente da breakpoint desktop tramite `md:hidden`.

La persistenza veniva però ostacolata dall'antenato principale dell'app shell:

```text
overflow-x-hidden
```

Un overflow non `visible` può creare un nuovo scroll container e impedire a un discendente `position: sticky` di ancorarsi alla viewport che effettivamente scorre.

Il cerchio nero con la lettera `N` visibile nello screenshot non è il menu GAIA: è l'indicatore di sviluppo di Next.js presente perché il frontend CED è eseguito con `next dev`.

## Correzione

File runtime:

```text
frontend/src/components/layout/app-shell.tsx
```

Modifica delimitata:

```diff
-overflow-x-hidden
+overflow-x-clip
```

`overflow-x-clip` continua a impedire overflow orizzontale visibile, ma non crea lo scroll container che interferisce con il topbar sticky.

Nessuna modifica alla navigazione desktop, al drawer, alle API o al backend.

## Test regressivo

File:

```text
frontend/tests/unit/app-shell.test.tsx
```

Il test verifica che:

- la shell usi `overflow-x-clip`;
- `overflow-x-hidden` non venga reintrodotto;
- il pulsante `Apri navigazione` resti dentro un header `sticky top-0`;
- l'apertura del drawer continui a funzionare.

TDD:

```text
RED: 1 failed, 12 passed
GREEN: 13 passed
```

## Gate

```text
Coverage app-shell.tsx + topbar.tsx: 100% statement/branch/functions/lines
Suite frontend completa: 184 file, 1656 test PASS
TypeScript typecheck: PASS
Complexity check: findings=[]
Complexity ratchet origin/main: findings=[]
git diff --check: PASS
Docker/Next.js production build: PASS
```

La build mantiene warning legacy non correlati già presenti; nessuna nuova failure.

## Deploy produzione

Il file live è stato confrontato con quello locale prima della copia: la sola differenza era `overflow-x-hidden → overflow-x-clip`.

Distribuito esclusivamente:

```text
/opt/gaia/frontend/src/components/layout/app-shell.tsx
```

È stato riavviato soltanto `gaia-frontend`.

Verifica immediata:

```text
gaia-frontend: healthy
GET /elaborazioni: HTTP 200
Errori TypeError/compilazione nei log recenti: nessuno
SHA256: 243460d111445e19e1c8003c033965e829827894be2ca138988e9eea7cb11430
```

Backup rollback:

```text
/opt/gaia/backups/hotfixes/2026-08-29-mobile-sticky-menu/app-shell.tsx.bak-20260829-211420
```

Il CED continua a eseguire il frontend con bind mount e `next dev`; questa configurazione non è stata modificata nello scope del fix.
