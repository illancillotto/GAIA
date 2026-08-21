---
name: gaia-complexity-reduction
description: Applica il quality ratchet agli sviluppi GAIA e guida refactoring behavior-preserving di un singolo hotspot quando esplicitamente richiesto.
version: 2.0.0
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
6. `docs/code-quality/QUALITY_RATCHET.md`;
7. `references/WORKFLOW.md` e `references/GAIA_CONSTRAINTS.md` di questa skill.

Verifica branch, SHA e working tree. Preserva ogni modifica non correlata.

## Scegli la modalita

### Ratchet ordinario - default

Usa questa modalita durante feature, fix e manutenzione:

1. calcola il perimetro dal merge-base e acquisisci le metriche prima;
2. identifica invarianti, test e coverage della responsabilita modificata;
3. implementa lo sviluppo richiesto senza peggiorare il debito legacy;
4. valuta una sola semplificazione locale, senza ampliare lo scope;
5. esegui metriche dopo, test, coverage e `complexity-ratchet`;
6. sincronizza la baseline soltanto dopo che il confronto con il merge-base e
   passato, poi esegui `baseline-verify`;
7. registra l'evidenza nel riepilogo della change. Aggiorna `PROGRESS.md` solo
   se cambia il programma, il tooling o una iterazione hotspot.

Il ratchet ordinario richiede non-regressione, non una riduzione forzata.

### Fondazione

Se il Checkpoint 1 non e approvato, esegui soltanto audit, tooling, baseline,
test e documentazione seguendo `docs/code-quality/PROMPT.md`. Non rifattorizzare
codice applicativo e non attivare CI bloccante.

### Hotspot dedicato - solo su richiesta

Se il Checkpoint 1 e approvato, tratta un solo hotspot:

1. selezionalo dal report e da `HOTSPOTS.md`;
2. registra invarianti, test, metriche prima e slice in `PROGRESS.md`;
3. aggiungi test di caratterizzazione se necessari;
4. applica la minima estrazione behavior-preserving;
5. esegui verifiche mirate, coverage e complexity ratchet contro il merge-base;
6. registra metriche dopo e verifica che la metrica obiettivo sia realmente
   diminuita senza spostare il debito;
7. aggiorna progress e backlog;
8. fermati senza iniziare un secondo hotspot.

## Regole assolute

- Non cambiare API, DB, auth, logica di dominio o comportamento UI per ridurre
  una metrica.
- Non rigenerare la baseline per rendere verde una regressione.
- Non rimuovere o indebolire test.
- Non usare esclusioni larghe o ignore immotivati.
- Non spostare complessita in wrapper, duplicati o file adiacenti.
- Non classificare come riduzione una estrazione che lascia invariata la
  metrica obiettivo o trasferisce violation.
- Non confrontare una change soltanto con la baseline modificata nella stessa
  change: il ratchet autorevole usa la baseline del merge-base.
- Non creare commit, push, PR o merge senza richiesta esplicita.
- Non dichiarare passata una verifica non eseguita.

## Stop condition

Aggiorna `PROGRESS.md` per gli hotspot e fermati se invarianti, ownership o
comportamento sono ambigui; se serve un cambio funzionale; se il matching
baseline e ambiguo; se compare una nuova failure; se la metrica obiettivo non
puo essere dimostrata; o se la slice supera una singola unita revisionabile.

## Output minimo

Riporta:

- file toccati;
- metriche prima/dopo;
- test e comandi eseguiti;
- coverage dei file runtime modificati;
- diff baseline;
- failure preesistenti e nuove;
- debito residuo;
- classificazione `IMPROVED`, `REORGANIZED_AND_CHARACTERIZED`,
  `NO_SAFE_CHANGE` o `BLOCKED` per gli hotspot;
- prossima azione, senza eseguirla.
