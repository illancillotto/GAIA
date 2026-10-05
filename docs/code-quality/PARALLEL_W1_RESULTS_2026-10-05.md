# W1 — risultati del pilota parallelo

Data: 2026-10-05. **Tre goal chiusi; nessuna seconda ondata avviata.**
Base e merge-base `bfc8e68fd6d4acf373b23b7cc15693c80bd75f18`.
Piano e prerequisiti: `PARALLEL_REDUCTION_PLAN_2026-10-05.md` e
`PARALLEL_W0_READINESS_2026-10-05.md`.

## Ownership e isolamento

Utente ha approvato i tre goal, isolamento e assenza di owner concorrenti.
Agenti hanno lavorato in worktree detached `/tmp/gaia-w1-catasto`,
`/tmp/gaia-w1-utenze`, `/tmp/gaia-w1-organigramma`, senza branch o commit.
Sono stati condivisi soltanto dipendenze installate read-only; niente patch
dirty Wiki/Ruolo/Presenze/SISTER trasferite agli isolati.
Allowlist: due test backend, controller selezione Organigramma e suo test.
Il coordinatore ha revisionato e integrato le patch serialmente con
`apply_patch`, verificando hash originari e HEAD prima dell'integrazione.

Lo scanner ha incontrato il symlink ambiente `frontend/node_modules` come
untracked (`IsADirectoryError`). Dopo stop e approvazione esplicita,
solo i comandi Git degli isolati hanno usato:

```bash
GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.excludesFile \
  GIT_CONFIG_VALUE_0=/tmp/gaia-w1-local-git-excludes
```

Il file locale contiene soltanto `/frontend/node_modules`. Non e una
esclusione runtime/coverage: scope, baseline e tooling versionati invariati.

## Risultati per goal

### W1-A — Catasto test-only

- Modificato solo `backend/tests/test_catasto_anomalie_payloads.py`, +23 righe.
- Nuovo caso VAL-06: entrambe le superfici e indice presenti, imponibile
  registrato nullo; attesi calcolati senza delta e input non modificati.
- Prima/dopo: cinque/sei test; statement 99/99 invariati, branch 50/52 -> 52/52.
  Coverage full-file runtime 100%, zero esclusioni, riprodotta dopo integrazione.
- Runtime `anomalie_payloads.py` invariato: target 30/24/31/2
  (cognitive/cyclomatic/LOC/nesting), file cog sum/max 65/30, cyc 56/24,
  105 LOC e sette callable. Nessuna riduzione runtime dichiarata.
- Esito: prerequisito di caratterizzazione chiuso; refactoring Catasto futuro
  non autorizzato automaticamente.

### W1-B — Utenze audit/caratterizzazione

- Modificato solo `backend/tests/test_anagrafica_parser.py`, +82 righe.
- Cinque -> 22 test: property persona/azienda e casi falsi, input vuoti,
  whitespace/separatori, persona incompleta, nomi completi e non speciali.
- Statement 52/58 -> 56/58; branch 12/16 -> 15/16; zero esclusioni.
  Risultato riprodotto nel checkout integrato; **100% non raggiunto**.
- Runtime `parser_service.py` invariato: target 30/21/79/2, file cognitive
  31/30, cyclomatic 26/21, 110 LOC e cinque callable.
- Residuo: statement 77–78 e branch 76→77, `if not nome`. `_split_tokens`
  conserva soltanto token non vuoti dopo strip; il percorso persona completa
  richiede almeno tre token. `tokens[1:-1]` contiene almeno un token non
  vuoto, senza underscore. Join/replace/strip non puo quindi svuotare il nome
  per input `str` conforme. Il caso incompleto e gia gestito prima.
- Nessun monkeypatch impossibile o esclusione introdotta. Ruff I001
  sull'ordine import del runtime e preesistente e non corretto in questo
  goal test-only; Ruff dei test passa.
- Esito: caratterizzazione completata, futura modifica runtime resta bloccata
  dal gate full-file. Utente ha approvato la rimozione della sola guardia morta
  **come prossimo goal separato**, non eseguito in questa ondata.

### W1-C — selezione Organigramma

- Modificati `frontend/src/features/organigramma/organigramma-selection-controller.ts`
  e `frontend/tests/unit/organigramma-selection-controller.test.ts`.
- Tre casi aggiuntivi passano prima della modifica runtime: toggle calcolato
  sullo snapshot distinto dal `prev` differito, evento mutato dopo la chiamata,
  Shift su elemento selezionato e ordine Set. Nessun test rimosso/indebolito.
- Guardia iniziale per selezione ordinaria e return; ramo modifier/updater
  identico, ora senza livello esterno di nesting. Nessun helper nuovo,
  trasferimento, nuova dipendenza o cambio funzionale.
- Ctrl/Meta/Shift, seed della selezione, toggle snapshot, ordine setter,
  immutabilita e ordine Set preservati. Drag, capture, permessi e altre
  funzioni non modificati. Il commento esistente del seed e solo ricollocato.

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Target cognitive | 23 | 16 |
| Target cyclomatic / LOC / parametri | 12 / 19 / 3 | 12 / 19 / 3 |
| Target nesting | 2 | 1 |
| File cognitive sum / max | 59 / 23 | 52 / 16 |
| File cyclomatic sum / max | 50 / 12 | 50 / 12 |
| File LOC / callable / import | 95 / 13 / 2 | 95 / 13 / 2 |
| Violation callable warning / error | 4 / 0 | 4 / 0 |

Esito **IMPROVED**: -7 cognitive, circa -30% sul target, -12% sul file.
Le quattro warning residue non sono dichiarate eliminate. Il totale
repository non misura questo delta locale e resta sostanzialmente invariato.

Prima 35 test; caratterizzazione e dopo 38 test verdi. Coverage dopo
integrazione: statement 62/62, branch 58/58, funzioni 13/13, linee 50/50,
tutto 100%. Prima branch 57/57: il denominatore cambia con la guardia,
non con nuove esclusioni. ESLint scoped e typecheck integrato PASS.

## Gate completi e interpretazione del matching

Il report parziale del controller produceva sei finding parametri per
matching verso i vecchi callable nel workspace: sorgenti ancora esistenti
erano omesse dal report e apparivano rimosse. Le firme erano invariate
gia prima del refactoring. Stop, diagnosi e verifica read-only sul corpus
**completo** hanno risolto il problema, senza cambiare matcher o baseline.
Non usare lo scan parziale come gate di un precedente split modulare.

- Isolato Organigramma: ratchet CLI completo senza filtri, exit 0,
  baseline del merge-base, nessun finding.
- Checkout integrato: report completo confrontato con baseline del merge-base,
  filtro di valutazione sui sei file W1: exit 0, nessun finding.
- Ratchet del working tree prima dell'integrazione runtime: 11 finding;
  confronto completo dopo: stessi 11, otto Wiki e tre test worker esterni.
  Rispetto a W0 compaiono tre finding da change concorrenti nei test
  `test_worker_reliability.py` e `test_worker_repository.py`, non nelle patch W1.
- Confronto integrale baseline corrente dopo: 29 finding; gate globale
  **ancora rosso**, non considerato sanato da gate scoped.
- Snapshot dopo: 1604 file, 19716 callable, 4742 violation,
  2041 error / 2701 warning. Non attribuire gli aggregati concorrenti a W1.
- `make quality-test`: 169 passed; `make lint-backend` contro base SHA:
  PASS dopo test backend integrati. Whitespace delle patch PASS.
- Baseline, eccezioni, soglie, configurazione coverage e policy CI invariati.
  Nessun baseline update eseguito: il checkout globale resta dirty/rosso.
  Nessun build frontend o test applicativo globale rivendicato.

## Evidenze e riproduzione

Artefatti locali non versionati, da rigenerare se assenti:

- `/tmp/gaia-w1-{before,after}-global.json` e
  `/tmp/gaia-w1-integrated-comparison.json`: scan e confronti autorevoli.
- `/tmp/gaia-w1-organigramma-full-ratchet.json`: gate isolato completo.
- `/tmp/gaia-w1-integrated-{catasto,utenze}.json`: coverage backend;
  report/cache/COVERAGE_FILE distinti, config temporanee senza esclusioni.
- `/tmp/gaia-w1-integrated-organigramma-coverage/coverage-final.json`.
- `/tmp/gaia-w1-quality-tests.log`, `/tmp/gaia-w1-integrated-lint.log`,
  `/tmp/gaia-w1-integrated-typecheck.log`.

Frontend dalla sua directory:

```bash
VITEST_COVERAGE_INCLUDE=src/features/organigramma/organigramma-selection-controller.ts \
  npm run test:unit -- tests/unit/organigramma-selection-controller.test.ts \
  --coverage --coverage.reportsDirectory=/tmp/gaia-w1-integrated-organigramma-coverage --cache=false
npx eslint src/features/organigramma/organigramma-selection-controller.ts \
  tests/unit/organigramma-selection-controller.test.ts
npx tsc -p tsconfig.json --noEmit --incremental \
  --tsBuildInfoFile /tmp/gaia-w1-integrated-organigramma.tsbuildinfo
```

Backend dalla sua directory: `.venv/bin/python -m pytest` sul test assegnato,
`--cov=app.modules.<dominio>.services.<modulo> --cov-branch`, config temporanea
senza esclusioni e report JSON dedicato. Catasto usa `--cov-fail-under=100`;
Utenze e audit con soglia zero, non un gate coverage superato.
Ratchet completo: `python3 tools/code_quality/complexity.py ratchet --base-ref bfc8e68f`
senza path, poi classificare i finding del checkout concorrente.

Graphify frontend aggiornato tramite `make graphify-frontend`: AST 632/632,
nessun cambio topologico, exit 0. Backend runtime invariato, nessuna nuova
relazione dominio introdotta dai test. Docs piattaforma aggiornate tramite
target dedicato, verificando chunk completi e assenza warning semantici.

## Checkpoint successivo

Stop alla fine dei tre goal. Nessuna W2 o sostituzione automatica avviata.
Prossimo goal separato gia approvato: Utenze, rimozione della sola guardia
irraggiungibile con full-file coverage, style ratchet e corpus completo.
Ripetere ownership, hash e gate prima di implementare. Nessun permesso
implicito per altri hotspot, baseline repair, commit o merge.
