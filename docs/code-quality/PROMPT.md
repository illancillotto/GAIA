# Prompt master - infrastruttura permanente di controllo complessita GAIA

Agisci come Senior Software Architect e Quality Engineer sul repository GAIA:

`https://github.com/illancillotto/GAIA`

Branch di riferimento: `main`.

## Obiettivo

Implementa un sistema permanente, automatico e misurabile per:

1. individuare gli hotspot di complessita nel codice runtime;
2. impedire nuove regressioni;
3. rendere verificabile la riduzione progressiva del debito legacy;
4. supportare refactoring piccoli, isolati e a comportamento invariato.

Questa prima attivita riguarda audit, metriche, baseline, controllo
differenziale, test dello strumento, comandi locali e documentazione. Non
eseguire un refactoring indiscriminato dei file applicativi.

## Contesto da verificare, non da assumere

GAIA e un monorepo con almeno questi perimetri runtime:

- `backend/app/**/*.py`: FastAPI, SQLAlchemy, Alembic, PostgreSQL;
- `frontend/src/**/*.{js,jsx,ts,tsx}`: Next.js 15, React 18, TypeScript;
- `modules/elaborazioni/worker/**/*.py`: worker separato.

La collocazione canonica del nuovo codice di dominio backend e
`backend/app/modules/<module>`.

Prima di ogni modifica, leggi integralmente e rispetta:

- `AGENTS.md` e gli eventuali `AGENTS.md` annidati;
- `Makefile`;
- `.github/workflows/backend.yml`;
- `.github/workflows/frontend.yml`;
- `backend/requirements.txt` e gli altri file di dipendenze backend;
- `frontend/package.json`, lockfile e configurazione ESLint/TypeScript;
- la documentazione esistente su coverage, Graphify e refactoring;
- `docs/code-quality/README.md`;
- `docs/code-quality/PLAN.md`;
- `docs/code-quality/PROGRESS.md`;
- `docs/code-quality/METRICS_AND_BASELINE.md`;
- `docs/code-quality/VALIDATION.md`.

Non dichiarare l'esistenza di file, workflow, target Make o script senza averli
verificati nel checkout corrente.

## Fase preliminare obbligatoria

Prima di modificare file, registra in `PROGRESS.md`:

1. commit e branch analizzati;
2. stato del working tree e modifiche preesistenti da preservare;
3. struttura reale dei tre perimetri runtime;
4. lint e type-check attuali;
5. workflow CI e script disponibili;
6. comandi test realmente esistenti;
7. dipendenze gia disponibili e gap;
8. perimetro di inclusioni ed esclusioni;
9. architettura proposta del motore;
10. file che saranno creati o modificati.

Se il working tree contiene modifiche non correlate, non sovrascriverle, non
ripristinarle e non includerle nel lavoro. Se una modifica richiesta si
sovrappone a esse, fermati e chiedi indicazioni.

## Perimetro iniziale

Includi automaticamente il codice runtime sotto:

```text
backend/app/**/*.py
frontend/src/**/*.{js,jsx,ts,tsx}
modules/elaborazioni/worker/**/*.py
```

Analizza i test separatamente e in modo non bloccante nella baseline iniziale,
salvo diversa evidenza emersa dall'audit.

Escludi per default:

- dipendenze vendorizzate;
- directory di build, cache e coverage;
- migration Alembic dal gate di complessita funzionale, ma non dal lint di
  sicurezza/sintassi;
- file generati, minificati, fixture, snapshot, asset e dataset;
- documentazione;
- file di configurazione prevalentemente dichiarativi, solo tramite regole
  esplicite e verificabili.

Il gate non deve dipendere da una lista manuale di hotspot. `HOTSPOTS.md` e solo
un seed di verifica.

## Requisiti del motore

Usa parser AST o motori consolidati. Le espressioni regolari possono aiutare la
discovery, ma non sono la fonte autorevole delle metriche.

Supporta almeno:

- Python sincrono e asincrono, funzioni annidate, metodi e decorator;
- JavaScript, JSX, TypeScript e TSX;
- funzioni, metodi, callback, arrow function, componenti React e hook;
- file aggiunti, modificati, rinominati e cancellati;
- merge-base Git e checkout shallow con errore operativo comprensibile.

Preferisci componenti piccoli e sostituibili:

1. adapter per motore Python;
2. adapter per motore JS/TS;
3. normalizzatore verso uno schema comune;
4. comparatore baseline;
5. selettore diff Git;
6. renderer testuale e JSON;
7. CLI con codici di uscita stabili.

Non aggiungere un nuovo framework o servizio persistente se una CLI locale e
deterministica risolve il problema.

## Toolchain da valutare

Verifica compatibilita e versioni prima di scegliere:

- Python: Ruff per lint e complessita ciclomatica; Complexipy o equivalente
  AST per complessita cognitiva;
- frontend: ESLint CLI con regole core e `eslint-plugin-sonarjs`, o equivalente
  AST compatibile con la versione corrente di Next/TypeScript.

`ruff` risulta gia presente nelle dipendenze backend: non duplicarlo senza
necessita. Non aggiornare Next, React, TypeScript o ESLint come effetto
collaterale dell'attivita, salvo incompatibilita dimostrata e approvata.

Le dipendenze di quality tooling devono essere separate dalle dipendenze runtime
quando possibile e bloccate a versioni riproducibili.

## Metriche minime

Per funzione o callable:

- complessita ciclomatica;
- complessita cognitiva;
- righe effettive;
- profondita massima di annidamento;
- numero di parametri;
- percorso, nome qualificato, tipo e posizione.

Per file:

- righe effettive;
- numero di callable;
- somma e massimo di complessita ciclomatica;
- somma e massimo di complessita cognitiva;
- densita di complessita;
- numero di import o dipendenze;
- per React: dimensione dei componenti e conteggio `useState`, `useEffect` e
  `useReducer`.

Ogni violazione deve indicare percorso, simbolo, riga, metrica, soglia, valore,
baseline, differenza e motivo dello stato.

Applica le soglie e le regole definite in `METRICS_AND_BASELINE.md`.

## Baseline legacy

Crea una baseline numerica versionata, con versione dello schema e dei motori.
La posizione raccomandata e:

```text
config/code-quality/complexity-baseline.json
config/code-quality/complexity-exceptions.json
```

Il formato definitivo puo cambiare dopo l'audit, ma deve essere documentato e
stabile.

Identifica i simboli con matching progressivo:

1. percorso e nome qualificato;
2. rename Git;
3. fingerprint AST o firma strutturale;
4. posizione come informazione secondaria.

Una corrispondenza ambigua e un errore di configurazione, non un motivo per
ignorare il simbolo.

Regole:

1. una violazione legacy registrata puo temporaneamente rimanere;
2. nessuna metrica legacy puo peggiorare;
3. il codice nuovo sopra la soglia di errore fallisce;
4. un simbolo legacy modificato non puo aumentare complessita, righe o nesting;
5. una riduzione deve diminuire il debito registrato;
6. il check ordinario non modifica mai la baseline;
7. l'update e esplicito e produce un diff revisionabile;
8. rigenerare non puo accettare automaticamente nuove regressioni;
9. il confronto con la baseline del branch base deve rilevare debt laundering.

## Comandi target

Esponi, preferibilmente tramite il `Makefile` esistente, comandi equivalenti a:

```text
make lint
make lint-backend
make lint-frontend
make complexity-report
make complexity-check
make complexity-changed BASE_REF=main
make complexity-ratchet BASE_REF=main
make complexity-baseline
make complexity-baseline-verify
make quality-test
```

`complexity-ratchet` e autorevole dopo che la baseline iniziale e stata
integrata nel branch base. Durante la fondazione deve fallire esplicitamente se
la baseline non esiste al merge-base; validare il comportamento anti-regressione
con fixture senza attivare la CI nella stessa change.

Se un nome collide con target esistenti, mantieni la compatibilita e documenta
la scelta. Non modificare il comportamento dei target applicativi esistenti.

Codici di uscita della CLI di complessita:

- `0`: controllo superato;
- `1`: regressioni o violazioni;
- `2`: errore di configurazione o utilizzo.

## Test dello strumento

Copri almeno:

1. codice nuovo sotto soglia;
2. codice nuovo sopra soglia;
3. legacy invariato;
4. legacy migliorato;
5. legacy peggiorato;
6. funzione e file rinominati;
7. file cancellato;
8. Python sync/async e funzione annidata;
9. JSX, TypeScript e TSX;
10. callback anonima e arrow function;
11. componenti e hook React;
12. ternari, logical expression e switch/match;
13. eccezione valida, scaduta e non valida;
14. baseline mancante o corrotta;
15. tentativo di aggiornamento che accetta regressioni;
16. shallow clone e merge-base non disponibile;
17. codici di uscita.

Le fixture del motore devono essere piccole e sintetiche. Non duplicare grandi
porzioni di codice GAIA nei test.

## CI e rollout

Fase 1:

- tutti i controlli devono essere eseguibili localmente;
- genera report e baseline;
- aggiungi test dello strumento;
- non rendere ancora bloccanti i workflow GitHub Actions;
- documenta l'integrazione proposta per entrambi i workflow esistenti.

Fase 2, solo dopo approvazione del Checkpoint 1:

- aggiungi il controllo differenziale ai workflow backend e frontend;
- usa la base reale della pull request e un `fetch-depth` adeguato;
- evita installazioni e build duplicate;
- rendi bloccanti solo nuove violazioni e peggioramenti;
- lascia il report completo come artifact o summary quando disponibile.

Non modificare branch protection, secrets o impostazioni GitHub.

## Vincoli funzionali

Non modificare, salvo specifica approvazione del singolo refactoring:

- contratti REST, payload, status code e semantica degli errori;
- schema PostgreSQL, migration e significato dei dati;
- autenticazione, autorizzazione e permessi;
- ordinamento e precedenza delle route;
- logica Catasto, Utenze, Ruolo, Presenze, GIS e Operazioni;
- calcoli tributari, contabili, catastali o irrigui;
- retry, timeout, polling, transazioni e concorrenza;
- rendering e comportamento osservabile della UI;
- Graphify, corpus Wiki o indicizzazione, salvo aggiornamento documentale
  richiesto dalle regole esistenti.

## Coverage e verifica

- Mantieni la policy GAIA di copertura al 100% dei file runtime modificati.
- Non cancellare, saltare o rinominare test per ottenere verde.
- Se esistono failure preesistenti, riproducile e separale dalle nuove failure.
- Esegui test mirati prima della suite piu ampia.
- Per frontend, esegui lint, type-check, test pertinenti e build quando il
  perimetro lo richiede.
- Per backend/worker, esegui compile/lint e test pertinenti al perimetro.

## Output del Checkpoint 1

Prima di qualsiasi refactoring applicativo crea o aggiorna:

- `docs/code-quality/PROGRESS.md`;
- documentazione utente dei comandi;
- baseline ed eccezioni versionate;
- report completo JSON e sintesi Markdown;
- test dello strumento;
- proposta di diff CI non attivata o documentazione equivalente.

Mostra:

1. file creati e modificati;
2. architettura implementata;
3. comandi realmente disponibili;
4. numero di file e callable analizzati per perimetro;
5. distribuzione delle metriche;
6. hotspot verificati;
7. baseline iniziale ed eccezioni;
8. esempio di report;
9. risultati dei test dello strumento;
10. risultati lint/type-check/test/build eseguiti;
11. failure preesistenti;
12. limiti e decisioni ancora aperte.

Fermati al Checkpoint 1. Non avviare un refactoring di hotspot e non attivare
gate CI bloccanti nello stesso goal.

## Divieti anti-gaming

Non ridurre artificialmente le metriche tramite:

- rinomina o spostamento per perdere il matching della baseline;
- wrapper o funzioni banali che spostano la complessita senza migliorarla;
- duplicazione del codice;
- esclusioni larghe;
- `noqa`, `eslint-disable` o ignore a livello file privi di motivazione;
- rigenerazione della baseline dopo una regressione;
- rimozione di test o riduzione del perimetro analizzato.

Confronta anche somma, massimo, densita e numero di violazioni nei file toccati.
Segnala split sospetti; rendili bloccanti solo se l'euristica e coperta da test e
non produce falsi positivi dimostrati.

## Modalita di esecuzione

Lavora per blocchi verificabili:

1. audit;
2. design del motore;
3. implementazione adapter e schema comune;
4. baseline ed eccezioni;
5. controllo differenziale;
6. test;
7. comandi locali;
8. documentazione;
9. verifica finale;
10. Checkpoint 1.

Aggiorna `PROGRESS.md` dopo ogni blocco. Non creare commit, push, pull request o
merge salvo richiesta esplicita.

Non dichiarare completata la Fase 1 se:

- i test dello strumento falliscono;
- il report non deriva da parser AST o motori equivalenti;
- il check ordinario modifica la baseline;
- il controllo differenziale non rileva nuove violazioni o peggioramenti;
- l'update della baseline puo accettare regressioni senza errore;
- il perimetro runtime non e documentato e verificato;
- sono state introdotte nuove failure applicative.
