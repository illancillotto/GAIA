# Matrice di validazione

I nomi dei comandi sono target locali versionati nel `Makefile`. La Fase 1 li
rende disponibili localmente; la Fase 2 attiva il gate differenziale nei
workflow GitHub Actions dopo approvazione del Checkpoint 1.

## Fase 1

| Area | Verifica | Evidenza richiesta |
| --- | --- | --- |
| Repository | branch, SHA e working tree | output sintetizzato in `PROGRESS.md` |
| Scope | file inclusi/esclusi per runtime | conteggi per backend, frontend e worker |
| Parser | Python e JS/TS realmente parsati | fixture e test verdi |
| Schema | output normalizzato stabile | JSON con `schema_version` |
| Baseline | generazione riproducibile | `make complexity-baseline-verify` |
| Read-only | check non modifica file | confronto `git status` prima/dopo |
| Regressione | nuova violation fallisce | fixture, exit code `1` |
| Legacy | invariato passa, peggiorato fallisce | fixture per entrambi |
| Matching | rename/fingerprint/ambiguita | test, ambiguita con exit code `2` |
| Eccezioni | valida/scaduta/larga | test e messaggi espliciti |
| CLI | codici `0/1/2` | test end-to-end |
| Tooling | lint e test interni | `make quality-test` |
| Applicazione | nessuna nuova failure | compile backend e typecheck frontend registrati |
| Documentazione | comandi e recovery | documenti aggiornati |
| CI | non bloccante in Fase 1 | nessun workflow modificato prima dell'approvazione Checkpoint 1 |

## Comandi di verifica Fase 1

```text
make quality-test
make complexity-report REPORT_JSON=/tmp/gaia-complexity-report.json REPORT_MD=/tmp/gaia-complexity-report.md
make complexity-check
make complexity-changed BASE_REF=origin/main
make complexity-baseline-verify
```

Comandi applicativi/audit usati nel Checkpoint 1:

```text
cd backend && python -m compileall -q app tests
cd frontend && npm run typecheck:from-root
```

Il type-check frontend canonico e `cd frontend && npm run typecheck:from-root`.
Deve uscire `0` e restare read-only rispetto a `git status --porcelain=v1 -uall`.

## Fase 2

| Area | Verifica | Evidenza richiesta |
| --- | --- | --- |
| Checkpoint 1 | ancora valido | matrice Fase 1 rieseguita |
| CI gate | workflow backend/frontend configurati | `.github/workflows/*.yml` richiamano `scripts/complexity_ci_gate.sh` |
| Merge-base PR | base reale disponibile | `fetch-depth: 0`, `BASE_REF=origin/${{ github.base_ref }}` |
| Missing merge-base | errore comprensibile | exit `2` e messaggio `merge-base unavailable` |
| Policy differenziale | legacy invariato passa; peggiorato/nuovo debito fallisce | fixture e `make complexity-ci-gate` |
| Debt laundering | baseline tampering, eccezioni/esclusioni, engine migration non autorizzate falliscono | test del tool |
| Workflow syntax | YAML valido | parser YAML locale o actionlint se disponibile |
| Runtime | nessun refactoring applicativo | diff vuoto sotto runtime applicativo |

## Singolo hotspot

| Gate | Deve dimostrare |
| --- | --- |
| Test di caratterizzazione | comportamento prima e dopo invariato |
| Lint/formatter | nessun nuovo errore nel perimetro |
| Coverage | 100% dei file runtime modificati secondo policy GAIA |
| Complexity check | nessuna nuova violation o peggioramento |
| Metriche prima/dopo | riduzione reale di almeno una metrica primaria |
| Aggregati | debito non spostato in wrapper o file adiacenti |
| Type-check/build | frontend valido se coinvolto |
| Diff review | nessuna modifica opportunistica o file estraneo |
| Progress | evidenze e debito residuo registrati |

## Verifiche manuali obbligatorie

- controllare il diff della baseline;
- controllare che eccezioni nuove siano strette e motivate;
- controllare API/router per ordine e semantica invariati;
- controllare componenti React per effetti e dipendenze hook invariati;
- controllare transazioni, retry e concorrenza nei servizi/worker;
- controllare che i test non siano stati rimossi, saltati o indeboliti;
- controllare eventuali aggiornamenti Graphify richiesti da `AGENTS.md`.

## Reporting delle failure

Separare sempre:

1. failure preesistenti riprodotte sul commit base;
2. flaky riprodotti;
3. failure causate dal diff corrente;
4. verifiche non eseguibili per dipendenze o servizi mancanti.

Una verifica non eseguita non equivale a una verifica superata.

## Definition of done del programma iniziale

La Fase 1 e completa solo se:

- perimetro e tool sono reali e documentati;
- baseline e report sono versionati e riproducibili;
- il controllo differenziale e testato;
- il check e read-only;
- l'update non puo assorbire regressioni;
- i nuovi test passano;
- nessun refactoring applicativo e stato incluso;
- `PROGRESS.md` contiene il Checkpoint 1 e le decisioni da approvare.

La Fase 2 e completa solo se:

- Checkpoint 1 resta valido;
- il gate CI differenziale e integrato in backend/frontend;
- la base PR e calcolata tramite merge-base corretto;
- missing merge-base fallisce con exit `2` e recovery documentata;
- i test anti-laundering restano verdi;
- nessun refactoring applicativo e incluso;
- `PROGRESS.md` e `HOTSPOTS.md` indicano readiness per il primo hotspot.
