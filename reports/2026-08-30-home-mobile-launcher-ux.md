# Report — Home GAIA: launcher moduli mobile compatto

**Data verifica:** 2026-08-30 11:39 CEST  
**Ambito:** `frontend/src/app/page.tsx` (`/`).

## Obiettivo

Ridurre la lunghezza percepita della home su telefono, mantenendo subito disponibili ricerca e primi moduli operativi, senza alterare il layout desktop.

## Intervento eseguito

- Ridotto lo spazio iniziale mobile:
  - hero da minimo `58vh` a `42vh` sotto `md`;
  - margini/padding mobile ridotti;
  - titolo GAIA ridotto da `text-7xl` a `text-5xl` sotto `sm`.
- Trasformato il launcher in una griglia **a due colonne** su telefono.
- Compattate le card su mobile:
  - padding, icona, badge e titoli ridotti;
  - descrizione limitata a due righe;
  - desktop invariato a partire dal breakpoint `md`.
- Il launcher visualizza inizialmente i primi **6 moduli** su mobile; gli altri restano raggiungibili dal comando espandibile **“Mostra altri N moduli”**.
- Il pulsante diventa **“Mostra meno moduli”** dopo l'espansione. Su desktop tutti i moduli restano sempre visibili.
- Estratta la responsabilità di rendering della card nel componente locale `HomeModuleCard`, per mantenere verde il quality ratchet.

## Impatto misurabile da layout

| Aspetto | Prima | Dopo |
| --- | --- | --- |
| Launcher mobile | una colonna | due colonne |
| Moduli iniziali con profilo completo (14 moduli) | 14 | 6 |
| Righe iniziali con 14 moduli | 14 | 3 |
| Hero minimo mobile | 58vh | 42vh |
| Accesso agli altri moduli | scroll lungo | pulsante esplicito “Mostra altri” |
| Desktop | griglia 3 colonne | invariato, tutti i moduli visibili |

## File modificati

- `frontend/src/app/page.tsx`
- `frontend/tests/unit/home-page-presence-widget.test.tsx`

## Verifiche eseguite

| Verifica | Esito |
| --- | --- |
| RED → GREEN test launcher compatto/espandibile | PASS |
| Test unitari home | PASS — 22 test |
| Coverage mirata `src/app/page.tsx` | PASS — 100% statement, branch, funzioni e linee |
| TypeScript `tsc -p tsconfig.json --noEmit` | PASS |
| Build production Next.js | PASS |
| `make complexity-ratchet BASE_REF=main` | PASS — `findings: []` |
| `git diff --check` | PASS |
| `make graphify-frontend` | PASS — 5.537 nodi, 13.691 archi, 210 community |

## Deploy locale e verifica runtime

- Eseguito build dell'immagine `gaia-frontend` con `docker compose build frontend`: **PASS**.
- Riavviato in locale il servizio frontend con `docker compose up -d --force-recreate frontend`.
  - Per le dipendenze Compose sono stati ricreati anche `gaia-backend` e il job di inizializzazione QGIS; nessun servizio esterno è stato coinvolto.
- Stato finale Docker: `gaia-frontend` **healthy**, `gaia-backend` **healthy**, `gaia-nginx` e `gaia-qgis-server` **healthy**.
- Verifiche HTTP dopo il deploy:
  - `http://127.0.0.1:3000/` → **200**;
  - `http://127.0.0.1:8080/` → **200**;
  - `http://127.0.0.1:8000/health` → **200**;
  - meta viewport presente sulla pagina pubblica.
- Rilanciati dopo il deploy i test home: **22 PASS**; coverage `src/app/page.tsx` ancora **100%** (135/135 statement, 161/161 branch, 28/28 funzioni, 127/127 linee).

## Deploy produzione CED

**Autorizzazione:** esplicita di Ale il 2026-08-30.

È stata pubblicata **solo** la modifica runtime della home:

- file copiato: `/opt/gaia/frontend/src/app/page.tsx` su `serverCed` (`192.168.1.110`);
- non sono stati copiati test, report, né altri file del checkout locale sporco;
- checksum file locale e CED dopo la copia: `0103ef41e21295f69500cee5ede0cacbd3a5cf39729f5b0021968eef79f3765b`;
- backup pre-deploy: `/opt/gaia/backups/hotfixes/2026-08-30-home-mobile-launcher-ux/page.tsx.predeploy`;
- checksum backup pre-deploy: `4911661aa23009b40d1f96f8b26fafdee33947de3ef23d9c765ce2ae32e0edef`;
- riavviato esclusivamente `gaia-frontend`;
- `gaia-frontend` post-deploy: **healthy**;
- smoke HTTP dal CED: frontend `:3000/` **200**, nginx `:8080/` **200**;
- verifica dall'host locale verso `http://192.168.1.110:8080/`: **HTTP 200**;
- log post-restart: frontend Next pronto e route `/` compilata senza errori runtime o build.

Il checkout CED ora mostra `frontend/src/app/page.tsx` modificato rispetto a Git, in modo intenzionale per questo hotfix chirurgico. Non sono stati creati commit o push.

## Limiti noti

- La build completa emette warning ESLint preesistenti in file estranei alla home; non blocca la build e non ne sono stati introdotti dalla change.
- Non è stata eseguita una prova browser autenticata a `390×844`: il test Playwright esistente richiede credenziali amministrative e la sessione browser pilotabile non era disponibile. La regressione funzionale è coperta da unit test e il runtime locale/produzione è healthy.
- Il checkout locale e quello CED contengono modifiche concorrenti; sono state lasciate inalterate. La pubblicazione è stata limitata al solo file `frontend/src/app/page.tsx` con backup reversibile.

## Prossimo passo consigliato

Con una sessione già autenticata, fare il controllo reale a `390×844`: home iniziale, apertura/chiusura di “Mostra altri”, tap sulla sesta card e verifica che a desktop (`1440×900`) l'intero catalogo resti visibile.
