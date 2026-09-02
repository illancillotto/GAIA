# Matrice di validazione

I nomi dei comandi sono target desiderati. Durante l'audit Hermes deve verificare
quelli esistenti e implementare/documentare quelli mancanti senza rompere il
Makefile corrente.

## Fase 1

| Area | Verifica | Evidenza richiesta |
| --- | --- | --- |
| Repository | branch, SHA e working tree | output sintetizzato in `PROGRESS.md` |
| Scope | file inclusi/esclusi per runtime | conteggi per backend, frontend e worker |
| Parser | Python e JS/TS realmente parsati | fixture e test verdi |
| Schema | output normalizzato stabile | JSON con `schema_version` |
| Baseline | generazione riproducibile | due generazioni identiche salvo timestamp normalizzato |
| Read-only | check non modifica file | working tree invariato dopo il check |
| Regressione | nuova violation fallisce | fixture, exit code `1` |
| Legacy | invariato passa, peggiorato fallisce | fixture per entrambi |
| Matching | rename/fingerprint/ambiguita | test, ambiguita con exit code `2` |
| Eccezioni | valida/scaduta/larga | test e messaggi espliciti |
| CLI | codici `0/1/2` | test end-to-end |
| Tooling | lint e test interni | `make quality-test` o equivalente |
| Applicazione | nessuna nuova failure | test mirati e confronto baseline |
| Documentazione | comandi e recovery | documenti aggiornati |
| CI | proposta non bloccante | diff o piano esplicito |

`make quality-test` deve eseguire tutti i file sotto `tests/code_quality`, non
un sottoinsieme nominato manualmente.

## Ratchet ordinario

| Gate | Deve dimostrare |
| --- | --- |
| Merge-base | commit base e baseline versionata disponibili |
| Baseline autorevole | confronto con la baseline del merge-base |
| Baseline corrente | riproducibile dopo la sincronizzazione |
| Codice nuovo | nessuna nuova violation error-level |
| Legacy | nessuna metrica callable o file gia in debito peggiorata |
| Coverage | policy GAIA rispettata sui file runtime modificati |
| Style | file Python toccati conformi a `docs/CODE_STYLE.md` e `make style-ratchet` |
| Scope | nessun ampliamento silenzioso delle esclusioni |

## Singolo hotspot

| Gate | Deve dimostrare |
| --- | --- |
| Test di caratterizzazione | comportamento prima e dopo invariato |
| Lint/formatter | `make lint-backend` / `make lint-frontend` verdi nel perimetro; nessun nuovo errore di stile |
| Coverage | 100% dei file runtime modificati secondo policy GAIA |
| Complexity check | nessuna nuova violation o peggioramento |
| Metriche prima/dopo | riduzione reale di almeno una metrica primaria |
| Aggregati | debito non spostato in wrapper o file adiacenti |
| Type-check/build | frontend valido se coinvolto |
| Diff review | nessuna modifica opportunistica o file estraneo |
| Progress | evidenze e debito residuo registrati |

## Sequenza di verifica suggerita

```text
make quality-test
make complexity-report
make complexity-check
make complexity-ratchet BASE_REF=main
make complexity-baseline-verify
```

Aggiungere poi i comandi applicativi realmente pertinenti. Non usare questa
sequenza come prova che i target esistono prima di averli implementati.

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
- una regressione coordinata con una nuova baseline viene bloccata usando la
  baseline del merge-base;
- le soglie file-level sono applicate e testate;
- il check e read-only;
- l'update non puo assorbire regressioni;
- i nuovi test passano;
- nessun refactoring applicativo e stato incluso;
- `PROGRESS.md` contiene il Checkpoint 1 e le decisioni da approvare.

Il gate CI diventa bloccante solo in una change successiva al merge della
fondazione, quando la baseline esiste gia nel branch di destinazione.

La Fase 2 e completa solo se:

- un workflow code-quality dedicato usa `fetch-depth: 0`;
- PR e push usano rispettivamente il base SHA e `github.event.before`;
- tutta `tests/code_quality` viene eseguita in CI;
- il dependency graph Babel e disponibile allo scanner;
- `complexity-ci-gate` passa realmente contro una baseline al merge-base;
- backend, frontend e worker non vengono modificati dalla change di attivazione.
