---
name: gaia-complexity-reduction
description: Riduce in modo incrementale e verificabile la complessita del monorepo GAIA. Usare per audit AST, baseline, gate differenziali e refactoring behavior-preserving di un singolo hotspot Python, FastAPI, Next.js, React o worker.
version: 1.0.0
author: GAIA maintainers
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [gaia, refactoring, complexity, python, typescript, quality]
---

# GAIA Complexity Reduction

Questa e una skill di progetto versionata nel repository GAIA. Va letta dal
checkout corrente e non installata nel profilo globale Hermes.

## Prima di agire

Lavora dalla root del repository GAIA.

Leggi integralmente:

1. `AGENTS.md` e gli eventuali `AGENTS.md` piu specifici;
2. `docs/code-quality/README.md`;
3. `docs/code-quality/PROGRESS.md`;
4. `docs/code-quality/METRICS_AND_BASELINE.md`;
5. `docs/code-quality/VALIDATION.md`;
6. `references/WORKFLOW.md` e `references/GAIA_CONSTRAINTS.md` di questa skill.

Verifica branch, SHA e working tree. Preserva ogni modifica non correlata.

## Scegli la modalita

### Bootstrap

Se il Checkpoint 1 non e approvato, esegui soltanto audit, tooling, baseline,
test e documentazione seguendo `docs/code-quality/PROMPT.md`. Non rifattorizzare
codice applicativo e non attivare CI bloccante.

### Hotspot

Se il Checkpoint 1 e approvato, tratta un solo hotspot:

1. selezionalo dal report e da `HOTSPOTS.md`;
2. registra invarianti, test, metriche prima e slice in `PROGRESS.md`;
3. aggiungi test di caratterizzazione se necessari;
4. applica la minima estrazione behavior-preserving;
5. esegui verifiche mirate, coverage e complexity check;
6. registra metriche dopo e riduci soltanto il debito eliminato;
7. aggiorna progress e backlog;
8. fermati senza iniziare un secondo hotspot.

## Regole assolute

- Non cambiare API, DB, auth, logica di dominio o comportamento UI per ridurre
  una metrica.
- Non rigenerare la baseline per rendere verde una regressione.
- Non rimuovere o indebolire test.
- Non usare esclusioni larghe o ignore immotivati.
- Non spostare complessita in wrapper, duplicati o file adiacenti.
- Non creare commit, push, PR o merge senza richiesta esplicita.
- Non dichiarare passata una verifica non eseguita.

## Stop condition

Aggiorna `PROGRESS.md` e fermati se invarianti, ownership o comportamento sono
ambigui; se serve un cambio funzionale; se il matching baseline e ambiguo; se
compare una nuova failure; o se la slice supera una singola unita revisionabile.

## Output minimo

Riporta:

- file toccati;
- metriche prima/dopo;
- test e comandi eseguiti;
- coverage dei file runtime modificati;
- diff baseline;
- failure preesistenti e nuove;
- debito residuo;
- prossima azione, senza eseguirla.
