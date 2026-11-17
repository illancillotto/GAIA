# Navigazione amministrazione Communications — 17 novembre 2026

## Difetto e correzione

Il link dai solleciti PEC/email apriva correttamente `/gaia/communications`,
ma la route mancava dal mapping della shell: il fallback selezionava NAS Control.
Il mapping e l’alias del modulo ora associano la pagina a Ruolo. Sidebar,
indicatore, selettore moduli e navigazione superiore sono coerenti anche dopo
ricaricamento e sul menu mobile. URL e autorizzazioni restano invariati.

## Verifiche

- I test unitari aggiunti falliscono sul codice precedente (tre asserzioni
  di route/sidebar), poi passano con la correzione.
- 149 test unitari di navigazione, shell e Communications superati.
  Suite frontend generale: 5733 test superati nel working tree corrente.
- `navigation.ts`: 100% statement (55/55), branch (54/54), funzioni (26/26),
  righe (53/53). Nessuna esclusione o modifica della strategia coverage.
- ESLint e typecheck superati; warning ESLint legacy fuori dal diff.
- Ratchet sul file contro il merge-base `d7842edf`: zero findings.
  Complessità cognitiva totale 63 → 63, ciclomatica 65 → 65;
  `getCurrentModuleKey` resta cognitive 1, cyclomatic 2, LOC 11.
  File LOC 477 → 478; tre violazioni legacy invariate in `getModuleSections`.
  Nessun refactoring o allargamento di soglie/esclusioni.
- Test browser con API sintetiche e shell completa: ingresso da PEC/email,
  desktop 1440 px/mobile 390 px, ricaricamento e ritorno ai solleciti.
  Quattro nuovi E2E e 19 E2E Communications preesistenti superati sulla candidata,
  zero failure/skipped/flaky. Il nuovo E2E desktop PEC fallisce sul live precedente
  per assenza del modulo Ruolo dopo il clic.
- Build produzione superata, tutte le 196 route preservate; 18 smoke test PASS.
- Graphify frontend e documentazione piattaforma aggiornati; estrazione docs
  `chunk 1/1 done`, nessun chunk semantico fallito.

Comandi: `npm run test:coverage` sui test layout/sidebar/top-navigation,
app-shell e `tests/unit/communications`, con
`VITEST_COVERAGE_INCLUDE=src/components/layout/navigation.ts`;
`npm run lint`; `npm run typecheck`;
`python tools/code_quality/complexity.py ratchet --base-ref d7842edf frontend/src/components/layout/navigation.ts`.

## Rilascio

Commit applicativo `4f1aa776` pubblicato sul branch `chore/split-changes-20261109`.
Frontend attivato su CED alle **08:47:16 CET**, immagine `sha256:0f58c17deec4928f564d44c240c83d86bf80341385ccb2f315aa0636044c4afc`.
Healthcheck superato e build identica alla candidata. Configurazione effettiva
preservata; tutti i 36 altri container invariati, compresi backend e worker.
Controlli HTTP su login, amministrazione, solleciti PEC/email e health API PASS;
API amministrativa non autenticata ancora 401. Nessuna migrazione o invio reale.
Tutti i **23 E2E ripetuti sul live** superati, zero failure/skipped/flaky.
Frontend, backend e worker healthy nella verifica finale.

Sorgente di partenza uguale al frontend del rilascio ICATASTO, con il solo overlay
di `navigation.ts`; non sono state incluse le altre modifiche del working tree.
[Evidenze verificabili](evidence/NAVIGATION_FIX_2026-11-17.json).

## Limiti residui

Il gate del perimetro modificato passa; il repository conserva debito di
complessità e warning legacy. La baseline globale era già stale nel ciclo
ICATASTO: questo fix non la rigenera né assorbe debito non correlato. I test
browser usano dati sintetici; non inviano comunicazioni reali.

Il push segnala otto avvisi dipendenze preesistenti sul branch predefinito
(sette high e uno moderate); nessuna dipendenza modificata da questo fix.
