# GAIA — Baseline provenance resume 2026-10-12

## Esito e perimetro

**NO_CHANGE — PROVENANCE_REVALIDATED_STATIC**. I 30 finding storici restano
15 `REAL_REGRESSION` runtime e 15 `TEST_ONLY_DIVERGENCE`, su 14 percorsi.
Tutti i 14 sorgenti sono CLEAN e byte-identici allo snapshot55a, alla nuova
main e alla precedente revalidation R44. Nessun commit successivo allo snapshot
modifica questi percorsi. Le 30 metriche del report completo corrente coincidono
esattamente con quelle conservate nelle prove AST storiche R44.

Questa attività **non esegue nuovi scanner, test, build, ratchet o check globale**.
Non dichiara global PASS e non assorbe debito nella baseline. L'esito terminale0
riguarda esclusivamente la verifica statica di custodia, Git e metriche già
prodotte, non una nuova riproduzione AST storica. Nessun runtime, test,
baseline, matcher, soglia, esclusione o policy è modificato.

## Snapshot e ownership

- Worktree: `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r64-baseline`.
- Branch: `review/complexity-r64-provenance`.
- HEAD e merge-base reale con main: `a51a48dc4caefbdd1aea82fe4d749054b9465970`.
- Snapshot iniziale invariato: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Ownership: solo questo nuovo report ed evidenze esterne `baseline-evidence/`;
  nessun commit o merge dell'agente. Registro prima della delega:
  `docs/code-quality/MULTI_AGENT_OWNERSHIP_RESUME_R64_2026-10-12.md` nel checkout
  d'integrazione.
- Per R64 il ratchet autorevole deve usare **`BASE_REF=main`**, il cui merge-base
  attuale è a51a48dc. Non sostituire55a per ottenere PASS.

## Metodo e custodia

Il record JSON R44 è verificato contro SHA256
`3374f053c9a656e304efdc6ff0a42e204f25eefbf9057fd45944d26fa1c646cc`.
Contiene 30 righe con file, callable o scope file, metrica, baseline, misure AST
all'origine, valore snapshot/current, commit completo e parent dei due passaggi
storici, status, classificazione e hash sorgente. Il report storico originale
è verificato contro `da60f6088d702c8cd53997b22644b843fefbc03abec5554ffac53cbe6422d315`.
Nessuna ricevuta precedente viene riscritta.

Per ogni riga la nuova verifica:

1. confronta bytes del worktree,55a,a51a e main con l'hash sorgente R44;
2. richiede status CLEAN e assenza di commit del path nel range55a..a51a;
3. controlla esistenza, primo parent e ancestry dei commit storici;
4. identifica un solo callable omonimo nel nuovo report completo, oppure legge
   esplicitamente LOC file per i record29/30;
5. confronta il valore corrente con quello R44 senza nuova scansione;
6. controlla gli hash protetti e l'exit0 dell'audit prodotto dal Coordinator.

Il nuovo JSON conserva **tutte le 30 righe**, i campi storici non normalizzati,
status corrente, `changed_since_snapshot=false`, `changed_by_r64=false`, hash
dei 14 sorgenti, commit/hashes protetti e riferimenti delle prove in input.
Finding sovrapposti non sono trattati come problemi indipendenti.

## Baseline e matcher

| File | SHA256 corrente | Differenza rispetto55a |
| --- | --- | --- |
| `config/code-quality/complexity-baseline.json` | `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95` | Nessuna, né byte né commit |
| `tools/code_quality/complexity.py` | `32b117502901ba56f1213b8871a25604c8723b710d45e0855b2da10bc6e251fc` | Due fix tooling autorizzati R16/R39 |
| `tools/code_quality/js_ast_metrics.mjs` | `faf340a36a2a3730d313be34b17a89e1c96c6310084d3b63739e0a3fbf446b8d` | Nessuna |

Matcher originale SHA256:
`315bc71fb48521f0049c968c8c4f262bdbb7077ad091c8f5f991b8088dc065af`.
I due commit successivi sono `269d3f091876a81f6ed6ed2273ae3d301e734160` e
`89bec55d523fb693a7a8bac6519921ca593eda26`; il matcher corrente coincide
esattamente con quello R44, non con il motore originario55a.

Il `source_commit` della baseline resta
`11ed944a46ebdeb32ad50c14e7fca90b2c55f1fd`, non il merge-base main.
L'ultima modifica della baseline nella storia main è
`b89e598c4fcfd264ca08a4ee4618f71f160dfcb5`, precedente55a.
La non-discendenza della source_commit e le misure AST baseline sono prove
storiche R44/originale, non nuove scansioni di questa attività.

## Ambiguità globale separata

Le prove R39/pausa riportano exit2 globale su GAIAusers e una ulteriore
contraddizione di ownership Organigramma. Non sono membri dei30 finding.
Anche questi due file sono byte-identici fra55a e a51a, senza commit nel range.

| Path | Identità storica in discussione | Classificazione attuale |
| --- | --- | --- |
| `frontend/src/app/gaia/users/page.tsx` | `useEffect[0]<callback>`, riga314; raw owner317/mapped259 | UNKNOWN — ownership non dimostrata, introduzione non attribuita |
| `frontend/src/features/organigramma/organigramma-workspace.tsx` | callback riga2064; raw owner2489/mapped2627 | UNKNOWN — ownership non dimostrata, introduzione non attribuita |

Non si inferiscono valori baseline/current o commit introduttori per tali
identità ambigue. I numeri di riga sono quelli del replay storico, non una
nuova esecuzione del matcher. Il check globale attuale è **NOT_RUN** da questo
agente; il report AST completo non certifica il confronto globale. L'exit2
storico resta non risolto, distinto dal FAIL30 originario e dal gate change.

## R64 Bonifica: intersezione e stato iniziale

Ownership runtime R64: `backend/app/services/elaborazioni_bonifica_sync.py` e
un solo test nuovo. Nessuna intersezione con i14 percorsi storici né con i due
percorsi ambigui. Il solo commit sul runtime nel range55a..a51a è
`949bdf6676c3f8a33b258994c4840df00daab4a8`, prerequisito R40 ammesso di
eliminazione della guardia date irraggiungibile. Nessun candidato R35/R43/R63
viene importato o ammesso da questa verifica.

Dal nuovo report a51a: `_run_bonifica_sync_background` cognitive269,
cyclomatic47, LOC232, nesting13, params3; file LOC738, cognitive_sum422,
cyclomatic_sum181. Sono metriche before, non riduzioni R64. Il runtime R64
deve superare i propri test/coverage100, review e ratchet prima dell'ammissione;
la non-intersezione storica da sola non equivale a PASS.

## Audit corrente e gate

Audit completo Coordinator:1680 file,20357 callable,1920 error,2736 warning,
4656 finding sovrapposti; zero parse/exception errors. Source_commit a51a48dc,
Python3.12.3 e Node24.14.0; report corrente SHA256
`6416fda75d916c7d77834d0f3289869a94694af237b47b45ad988a78f6ffa945`.
Il differente perimetro rispetto1665/20261 iniziali non è di per sé prova
di riduzione né di regressione: nessun delta globale è certificato qui.

- Script statico custodia/storia/metriche: **PASS, exit0**,30/30 righe e14/14 path.
- `git diff --check`: **PASS, exit0**, per lo stato tracked. Il solo nuovo
  report è untracked: `git diff --no-index --check /dev/null <report>` produce
  exit1 per il contenuto aggiunto, senza diagnostica whitespace; non viene
  confuso con un ratchet o con un gate runtime.
- Nuovi test/coverage runtime: **NOT_RUN, non pertinenti all'agente documentale**.
- `make complexity-ratchet BASE_REF=main`: **NOT_RUN da questo agente**.
- `make complexity-check`: **NOT_RUN**; stato storico FAIL/exit2 non sanato.
- Nessuna baseline inflation o modifica soglie/esclusioni/policy.
- Nessun aggiornamento Graphify eseguito: token pesante riservato all'autore;
  nessuna responsabilità runtime cambia qui. Il Coordinator gestisce l'eventuale
  aggiornamento documentale insieme alla pubblicazione R64.

## Handoff e riproducibilità

Directory privata durevole:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/baseline-evidence`.

- `static-records.json`, SHA256
  `3a567a9be77227c42f8abb5dabb3c4a25945c88f8d3e7966d8b5724fb7a73cad`.
- `static-revalidate.py`, SHA256
  `33c1990532ef08185fa9c1c4c5cb537a9f4c180deb042f1b002f777d5f7bb004`.
- `static.log`, SHA256
  `4085976f471231e83dac60cd26ffa3948713238a2547f6a209df2af16094af41`.
- `static.exit`, SHA256
  `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa`.
- Copie immutabili degli input storici e manifest SHA256 nella stessa directory;
  report completo e audit.argv/log/exit restano nella root evidence resume.

Il replay statico richiede Git objects, JSON storico e audit corrente esatti;
lo script usa creazione esclusiva del nuovo JSON e non sovrascrive prove.
Per rieseguire usare nuovi percorsi di output, senza riscrivere le ricevute.
Per riproduzione AST storica completa seguire il report R44 separatamente e
ottenere il token pesante; non è stato eseguito qui.

Prossime decisioni: verifiche R64 assegnate, mantenere global ambiguity in
attività separata; non modificare baseline o matcher per sbloccare R64.
Goal globale ACTIVE/INCOMPLETE; nessuna certificazione delle suite finali,
dei449 skip backend, dei gap worker o E2E deriva da questo rapporto.
