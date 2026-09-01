# Breadcrumb Visure navigabile — verifica e deploy CED

Data: 2026-08-30

## Segnalazione

Nella topbar mobile della pagina Visure compariva:

```text
Visure / Elaborazioni / Visure
```

Il percorso era inoltre testo semplice e non cliccabile.

## Causa

`Topbar` mostrava sempre `pageTitle="Visure"` e aggiungeva successivamente il valore testuale `breadcrumb="Elaborazioni / Visure"`. Il breadcrumb non disponeva di destinazioni strutturate e quindi non generava elementi `<a>`.

## Correzione

È stato introdotto un percorso strutturato per la pagina Visure:

- `Elaborazioni`: link a `/elaborazioni`;
- `Visure`: pagina corrente, non cliccabile, con `aria-current="page"`;
- regione semantica `<nav aria-label="Percorso pagina">`;
- nessuna duplicazione del titolo.

Il comportamento legacy delle altre pagine resta invariato.

## File modificati

Runtime:

- `frontend/src/components/layout/topbar.tsx`;
- `frontend/src/components/app/protected-page.tsx`;
- `frontend/src/app/elaborazioni/visure/page.tsx`.

Test:

- `frontend/tests/unit/app-shell.test.tsx`;
- `frontend/tests/unit/elaborazioni-visure-page.test.tsx`.

## TDD e verifiche

- RED iniziale: mancava la regione di navigazione `Percorso pagina`.
- Test mirati finali: **35/35 PASS**.
- Coverage runtime modificato:
  - statements: **43/43 — 100%**;
  - branches: **64/64 — 100%**;
  - functions: **9/9 — 100%**;
  - lines: **42/42 — 100%**.
- Suite frontend completa: **184/184 file, 1.660/1.660 test PASS**.
- Typecheck TypeScript: **PASS**.
- Build Next.js production: **PASS**, `154/154` pagine generate.
- Harness Quality Code: **46/46 PASS**.
- Complexity ratchet finale: **PASS**, `findings: []`.
- `git diff --check`: **PASS**.

Il primo assetto funzionale era stato bloccato dal ratchet per incremento di metriche in `Topbar`. La resa del percorso è stata quindi isolata in `TopbarPagePath`, senza aggiornare la baseline e senza assorbire regressioni.

## Deploy CED

Deploy chirurgico dei tre file runtime frontend e riavvio del solo servizio `gaia-frontend`.

Backup rollback:

```text
/opt/gaia/backups/hotfixes/20260830-005621-breadcrumb-visure
```

Durante il confronto locale/CED sono state rilevate due differenze preesistenti in `topbar.tsx`, non appartenenti al task:

- dimensione pulsante menu mobile `h-11 w-11` locale contro `h-9 w-9` CED;
- colore breadcrumb legacy `text-gray-600` locale contro `text-gray-400` CED.

Dopo una prima copia, il file CED è stato immediatamente riconciliato preservando i valori live precedenti e mantenendo esclusivamente il delta breadcrumb. Il checksum finale di `topbar.tsx` sul CED è pertanto quello del file riconciliato, non quello del working tree locale.

Checksum finali verificati:

```text
a04687d13d75de5dae7e3318adb236250c3ef470da63aa5ef6cf69d9aa67d275  frontend/src/components/layout/topbar.tsx (CED reconciled)
91258361aadc6d998a391209101b90192b5e419c39c7a600531086595bed9512  frontend/src/components/app/protected-page.tsx
0b3c982e04ae2f7bd9b6e5f0cc9bb21b13522789333b46aa73571a395aec836a  frontend/src/app/elaborazioni/visure/page.tsx
```

## Verifica produzione

- `gaia-frontend`: **healthy**;
- `/elaborazioni/visure`: **HTTP 200**;
- compilazione live route: **PASS**;
- sorgente live:
  - `Percorso pagina`: presente;
  - link generato da `href={item.href}`: presente;
  - `aria-current="page"`: presente;
  - destinazione `/elaborazioni`: presente;
- log recenti: nessun errore di compilazione/runtime sulla route.

## Estensione desktop

Su richiesta successiva è stato reso esplicito anche il comportamento desktop del link antenato:

- link `Elaborazioni` con area interattiva `inline-flex`;
- `pointer-events-auto` e `cursor-pointer` espliciti;
- `md:inline-flex` per il contratto desktop;
- area minima `md:min-h-9` su desktop e `min-h-11` su mobile;
- `relative z-10` per impedire che elementi adiacenti della topbar intercettino il click.

È stato aggiunto un test dedicato con viewport logica desktop `1440 px`. Il test ha prima fallito perché mancavano le garanzie desktop esplicite, quindi è passato dopo il delta minimo.

Verifiche finali dell'estensione:

- test desktop mirato: **1/1 PASS**;
- test correlati: **36/36 PASS**;
- coverage `topbar.tsx`: **100%**;
- suite frontend: **184/184 file, 1.661/1.661 test PASS**;
- typecheck: **PASS**;
- build Next.js: **PASS**, `154/154` pagine;
- complexity ratchet: **PASS**, `findings: []`;
- `git diff --check`: **PASS**.

Deploy chirurgico del solo `topbar.tsx`, preservando le differenze CED già documentate. Backup aggiuntivo:

```text
/opt/gaia/backups/hotfixes/20260830-010930-breadcrumb-desktop/topbar.tsx
```

Checksum CED finale:

```text
2cb0a08bf017965ff8e714c9e72ec0273e8be7239c343ac3ad1d0fd92bc5379f  /opt/gaia/frontend/src/components/layout/topbar.tsx
```

Verifica post-deploy:

- `gaia-frontend`: **healthy**;
- `/elaborazioni/visure`: **HTTP 200**;
- compilazione live: **PASS**;
- classi desktop, pointer events, cursore e destinazione del link: presenti nella sorgente live;
- log route: nessun errore.

## Stato finale

**PASS — breadcrumb Visure navigabile, non duplicato e cliccabile su mobile e desktop, testato e distribuito sul CED.**

Nessun commit, push, pull request o merge eseguito.
