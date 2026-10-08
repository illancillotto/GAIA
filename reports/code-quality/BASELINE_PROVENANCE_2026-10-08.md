# GAIA — Baseline provenance 2026-10-08

## Esito

Le 30 divergenze del confronto integrale sono riprodotte su sorgenti già
committati nello snapshot iniziale. Sono 15 aumenti reali di metriche runtime
storici, classificati `REAL_REGRESSION`, e 15 divergenze nei test worker,
classificate `TEST_ONLY_DIVERGENCE`. Nessuna è introdotta dalla campagna corrente.
Non sono errori del parser o valori inventati nella baseline: tutte le 30 metriche
baseline coincidono con l'AST del commit dichiarato come origine e con l'AST
del commit più recente che ha memorizzato la baseline.

Questa classificazione non equivale a un bug funzionale né all'accettazione delle
regressioni storiche. Il ratchet della change e il debito globale restano controlli
distinti. Nessuna baseline, soglia, esclusione, eccezione o sorgente runtime è stata
modificata; nessun comando di baseline update/repair è stato eseguito.

| Classificazione | Finding | Significato |
| --- | ---: | --- |
| REAL_REGRESSION | 15 | Metriche runtime aumentate in commit precedenti alla campagna |
| TEST_ONLY_DIVERGENCE | 15 | Aumenti verificati nel perimetro test worker |
| BASELINE_STALE | 0 | Nessun valore errato rispetto alla sua origine dimostrata |
| LEGACY_DIVERGENCE | 0 | Origine degli aumenti verificata puntualmente |
| UNKNOWN | 0 | Nessun matching ambiguo nei 30 record |

## Snapshot e ownership

- Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261008-baseline`.
- Branch: `refactor/complexity-baseline-provenance`.
- HEAD iniziale e merge-base con main: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Ownership scrittura: esclusivamente questo report.
- Origine finding: `reports/code-quality/complexity-audit-2026-10-08-summary.json`,
  campo `global_compare.findings`, 30 record su 14 percorsi.
- I 14 percorsi sono CLEAN sia nella worktree isolata sia nel checkout principale
  durante questa verifica. Le sole voci iniziali non tracciate nella worktree sono
  i collegamenti locali `backend/.venv` e `frontend/node_modules`; non entrano nel commit.
- `campaign_changed=false` per ogni finding: gli AST HEAD riproducono tutti i valori
  audit, mentre i percorsi non hanno diff locale. Nessun lavoro concorrente copiato.

## Provenance della baseline

La baseline operativa è `config/code-quality/complexity-baseline.json` a
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Il campo `source_commit` contiene
`11ed944a46ebdeb32ad50c14e7fca90b2c55f1fd`; questo commit esiste localmente
ma **non è un antenato di main**. Non deve essere confuso con il merge-base né
usato per attribuire cambiamenti della campagna.

Il commit `11ed944a` e il commit presente nella storia main
`30b3dd7efad7e50c2dba327dc467e0fd267a8388` memorizzano lo stesso blob baseline
(SHA-256 `736edf3cddb0b976c5757df2d56bc0a5e90075ab1f1e61e83a6a2cb963660359`).
L'ultimo commit nella storia main che modifica il file baseline è
`b89e598c4fcfd264ca08a4ee4618f71f160dfcb5`, dopo `30b3dd7e`.

Per ciascuna delle 30 metriche è stato verificato che:

1. il valore registrato a HEAD coincide con l'AST a `11ed944a`;
2. il valore registrato a `b89e598c` coincide con l'AST a `b89e598c`;
3. l'AST a HEAD coincide con il valore attuale riportato dall'audit;
4. un commit successivo alla memorizzazione baseline cambia la metrica;
5. il commit che introduce l'aumento e il commit che produce il valore attuale
   sono identificati misurando sia il commit sia il suo primo parent.

È quindi dimostrato un disallineamento cronologico tra baseline registrata e
sviluppi successivi. Il termine `REAL_REGRESSION` distingue gli aumenti runtime
misurati dall'ipotesi di baseline originariamente errata. La presente attività
è di sola provenance e non autorizza ad assorbire questi aumenti.

## Tutte le 30 divergenze

`Origine aumento` indica l'ultimo passaggio dal valore baseline o inferiore a
un valore superiore nella storia del file che precede la divergenza corrente.
`Valore corrente da` indica il commit che produce il valore osservato a HEAD,
anche quando tale commit riduce una precedente regressione.
Le frecce sono sempre misure AST parent→commit, non inferenze da git blame.
`AST origine` è misurato a `11ed944a`; coincide anche con l'AST a `b89e598c`.
`Current` è misurato a `55a1b1d3` e coincide con l'audit.

| # | File | Callable | Metrica | Baseline | AST origine | Current | Origine aumento, parent→commit | Valore corrente da, parent→commit | Working tree | Campaign changed | Classificazione |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| 1 | `backend/app/modules/wiki/mcps/auth.py` | `verify_token` | loc | 21 | 21 | 22 | `1995a1fc` (21→24) | `32849087` (24→22) | CLEAN | false | REAL_REGRESSION |
| 2 | `backend/app/modules/wiki/mcps/cli.py` | `main` | cyclomatic | 3 | 3 | 4 | `1995a1fc` (3→5) | `32849087` (5→4) | CLEAN | false | REAL_REGRESSION |
| 3 | `backend/app/modules/wiki/mcps/cli.py` | `main` | loc | 22 | 22 | 28 | `1995a1fc` (22→28) | `1995a1fc` (22→28) | CLEAN | false | REAL_REGRESSION |
| 4 | `backend/app/modules/wiki/mcps/data/cli.py` | `main` | loc | 26 | 26 | 29 | `1995a1fc` (26→29) | `1995a1fc` (26→29) | CLEAN | false | REAL_REGRESSION |
| 5 | `backend/app/modules/wiki/mcps/data/server.py` | `create_server` | loc | 28 | 28 | 31 | `1995a1fc` (28→31) | `1995a1fc` (28→31) | CLEAN | false | REAL_REGRESSION |
| 6 | `backend/app/modules/wiki/mcps/data/service.py` | `DataService.__init__` | loc | 7 | 7 | 8 | `1995a1fc` (7→8) | `1995a1fc` (7→8) | CLEAN | false | REAL_REGRESSION |
| 7 | `backend/app/modules/wiki/mcps/data/service.py` | `DataService.__init__` | params | 2 | 2 | 3 | `1995a1fc` (2→3) | `1995a1fc` (2→3) | CLEAN | false | REAL_REGRESSION |
| 8 | `backend/app/modules/wiki/mcps/experiment_cli.py` | `live` | loc | 3 | 3 | 4 | `85b179b0` (3→4) | `85b179b0` (3→4) | CLEAN | false | REAL_REGRESSION |
| 9 | `backend/app/modules/wiki/mcps/experiment_runner.py` | `experiment_manifest` | loc | 29 | 29 | 30 | `1995a1fc` (29→30) | `1995a1fc` (29→30) | CLEAN | false | REAL_REGRESSION |
| 10 | `backend/app/modules/wiki/mcps/http.py` | `create_http_app` | cyclomatic | 1 | 1 | 2 | `1995a1fc` (1→3) | `32849087` (3→2) | CLEAN | false | REAL_REGRESSION |
| 11 | `backend/app/modules/wiki/mcps/http.py` | `create_http_app` | cognitive | 0 | 0 | 1 | `1995a1fc` (0→2) | `32849087` (2→1) | CLEAN | false | REAL_REGRESSION |
| 12 | `backend/app/modules/wiki/mcps/http.py` | `create_http_app` | loc | 44 | 44 | 50 | `1995a1fc` (44→52) | `32849087` (52→50) | CLEAN | false | REAL_REGRESSION |
| 13 | `backend/app/modules/wiki/mcps/http.py` | `create_http_app` | nesting | 0 | 0 | 1 | `1995a1fc` (0→1) | `1995a1fc` (0→1) | CLEAN | false | REAL_REGRESSION |
| 14 | `frontend/src/app/wiki/mcp/page.tsx` | `WikiMCPPreview` | loc | 54 | 54 | 55 | `1995a1fc` (54→55) | `1995a1fc` (54→55) | CLEAN | false | REAL_REGRESSION |
| 15 | `frontend/src/components/ruolo/registered-mails-console.tsx` | `RegisteredMailRow` | loc | 39 | 39 | 40 | `2908e0e1` (39→40) | `2908e0e1` (39→40) | CLEAN | false | REAL_REGRESSION |
| 16 | `modules/elaborazioni/worker/tests/test_sister_browser_reliability.py` | `_Page.__init__` | loc | 11 | 11 | 12 | `47e74500` (11→12) | `47e74500` (11→12) | CLEAN | false | TEST_ONLY_DIVERGENCE |
| 17 | `modules/elaborazioni/worker/tests/test_sister_browser_reliability.py` | `_Page.locator` | cyclomatic | 3 | 3 | 4 | `47e74500` (3→4) | `47e74500` (3→4) | CLEAN | false | TEST_ONLY_DIVERGENCE |
| 18 | `modules/elaborazioni/worker/tests/test_sister_browser_reliability.py` | `_Page.locator` | cognitive | 2 | 2 | 3 | `47e74500` (2→3) | `47e74500` (2→3) | CLEAN | false | TEST_ONLY_DIVERGENCE |
| 19 | `modules/elaborazioni/worker/tests/test_sister_browser_reliability.py` | `_Page.locator` | loc | 6 | 6 | 8 | `47e74500` (6→8) | `47e74500` (6→8) | CLEAN | false | TEST_ONLY_DIVERGENCE |
| 20 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice` | cyclomatic | 6 | 6 | 7 | `47e74500` (6→7) | `47e74500` (6→7) | CLEAN | false | TEST_ONLY_DIVERGENCE |
| 21 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice` | cognitive | 11 | 11 | 16 | `47e74500` (11→16) | `47e74500` (11→16) | CLEAN | false | TEST_ONLY_DIVERGENCE |
| 22 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice` | loc | 35 | 35 | 46 | `47e74500` (35→46) | `47e74500` (35→46) | CLEAN | false | TEST_ONLY_DIVERGENCE |
| 23 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice` | nesting | 3 | 3 | 4 | `47e74500` (3→4) | `47e74500` (3→4) | CLEAN | false | TEST_ONLY_DIVERGENCE |
| 24 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice.scenario` | cyclomatic | 6 | 6 | 7 | `47e74500` (6→7) | `47e74500` (6→7) | CLEAN | false | TEST_ONLY_DIVERGENCE |
| 25 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice.scenario` | cognitive | 11 | 11 | 16 | `47e74500` (11→16) | `47e74500` (11→16) | CLEAN | false | TEST_ONLY_DIVERGENCE |
| 26 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice.scenario` | loc | 33 | 33 | 44 | `47e74500` (33→44) | `47e74500` (33→44) | CLEAN | false | TEST_ONLY_DIVERGENCE |
| 27 | `modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py` | `test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice.scenario` | nesting | 3 | 3 | 4 | `47e74500` (3→4) | `47e74500` (3→4) | CLEAN | false | TEST_ONLY_DIVERGENCE |
| 28 | `modules/elaborazioni/worker/tests/test_worker_repository.py` | `test_document_path_builders_cover_subject_and_immobile_fallbacks` | loc | 28 | 28 | 33 | `7d5aa2db` (28→33) | `7d5aa2db` (28→33) | CLEAN | false | TEST_ONLY_DIVERGENCE |
| 29 | `modules/elaborazioni/worker/tests/test_worker_reliability.py` | `<file>` | loc | 567 | 567 | 584 | `7d5aa2db` (567→584) | `7d5aa2db` (567→584) | CLEAN | false | TEST_ONLY_DIVERGENCE |
| 30 | `modules/elaborazioni/worker/tests/test_worker_repository.py` | `<file>` | loc | 512 | 512 | 534 | `7d5aa2db` (512→534) | `7d5aa2db` (512→534) | CLEAN | false | TEST_ONLY_DIVERGENCE |

## Commit verificati

| Commit | Responsabilità storica | Finding interessati |
| --- | --- | --- |
| `1995a1fc61961e51acf38bbc2137e7788e9a10fc` | Console MCP sintetica e connector OAuth opzionale | 1–7, 9–14 |
| `85b179b059475c7de15bfa7d506bb03e6cc16d7e` | Semplificazione runner e journal MCP | 8 |
| `2908e0e13e23d02eac8818fcf7eef8efa010b76e` | Allegati registered-mail ai documenti Utenze | 15 |
| `47e7450023cd311a260ba2f5975a35772a0fe119` | Province SISTER riusate e recupero sezioni | 16–27 |
| `7d5aa2dba63d2643a7c6e33ec228bceca9ae6e10` | Lookup SISTER e richieste da revisionare | 28–30 |
| `32849087b40684945ce273b1dd999f9e98e9bcbd` | Consolidamento refactoring precedente | Riduce 1, 2, 10–12 senza tornare al valore baseline |

Il commit `32849087` porta `verify_token.loc` 24→22, `main.cyclomatic` 5→4,
`create_http_app.cyclomatic` 3→2, cognitive 2→1 e LOC 52→50. È un miglioramento
storico parziale, non l'origine dell'aumento: il confronto con la baseline
continua a fallire per i residui indicati nella tabella.

Per il file test `test_worker_repository.py` esiste anche un aumento storico
512→521 a `c4a9556d2b910db7c48006a118c100bf5b005fc5`, seguito da un ritorno
521→512 a `5915305dc703911557d18409dc208b8aa290e71b`.
L'aumento **corrente** 512→534 è quindi attribuito a `7d5aa2db`, non al primo
aumento successivamente annullato. Questo esempio mostra perché il solo blame
o il primo commit che oltrepassa la baseline non basta.

## Metodo e limiti

Sono usati i motori AST del checkout autorevole: Python stdlib AST e helper
Babel `tools/code_quality/js_ast_metrics.mjs`. Python 3.12.3 e Node v24.14.0
coincidono con le runtime registrate nella baseline. Le funzioni della scansione
Python sono importate senza importare i moduli applicativi né avviare database,
connector o servizi esterni. Le sorgenti storiche sono lette con `git show` e
misurate in memoria o in file temporanei.

Per ogni percorso si usa `git log HEAD -- <path>`, misurando tutti i commit
elencati e i relativi primi parent. Non sono presenti rename o ambiguità di
nome nei 30 record analizzati. Non viene modificato il matcher per rendere
verde il check. La scansione storica usa il motore attuale fissato a main,
per confrontare tutte le revisioni con la stessa semantica; non pretende che
gli aumenti dimostrino cambiamenti funzionali o bug.

Le metriche dei callable Python includono anche AST annidati. I record del
test SISTER e della relativa `scenario` descrivono rami sovrapposti: sono
8 finding di metrica, **non 8 problemi indipendenti**. Analogamente LOC file
e LOC callable non devono essere sommati come debito indipendente.

Non sono state eseguite suite applicative perché nessun runtime o test è stato
modificato. Coverage dei runtime non pertinente a questa attività documentale.
Il grafo applicativo non cambia; non serve un aggiornamento Graphify.

## Gate riprodotti

Il target `make complexity-check` riproduce esattamente i 30 finding dell'audit:
il comando scanner esce 1 e Make restituisce 2 per il fallimento atteso del
confronto integrale. La scansione del solo checkout committed conta 1662 file,
20257 callable, 1956 error e 2758 warning: le differenze nei conteggi file/callable
rispetto all'audit dirty non sono riduzioni della campagna; il totale 4714 finding
e la lista delle 30 divergenze restano identici.

`make complexity-ratchet BASE_REF=main` è stato tentato ma non completa il gate
in questa worktree: il matcher chiama `read_bytes()` sul collegamento locale
non tracciato `backend/.venv` e solleva `IsADirectoryError`. Make restituisce 2.
È una limitazione ambientale della worktree predisposta per gli agenti, non una
nuova regressione runtime; non viene dichiarato PASS, né modificato il tooling
per nasconderla. Il ratchet locale PASS/0 dell'audit iniziale resta evidenza
separata. Il Coordinator deve ripetere il gate d'integrazione con dipendenze
locali che non entrino nella lista dei file non tracciati.

Nessuna divergenza globale viene trasformata in finding della campagna; se una
slice tocca in futuro uno di questi callable dovrà considerare esplicitamente
la provenance e il ratchet.

## Evidenze locali e integrità

- Script storico read-only: `/tmp/gaia-baseline-provenance.py`.
- Evidenza completa con timeline e valori baseline per ogni commit:
  `/tmp/gaia-baseline-provenance-2026-10-08.json`.
- Log ratchet: `/tmp/gaia-baseline-provenance-ratchet-2026-10-08.log`.
- Log confronto integrale: `/tmp/gaia-baseline-provenance-check-2026-10-08.log`.
- SHA-256 baseline a HEAD:
  `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
- SHA-256 scanner Python:
  `315bc71fb48521f0049c968c8c4f262bdbb7077ad091c8f5f991b8088dc065af`.
- SHA-256 helper Babel:
  `faf340a36a2a3730d313be34b17a89e1c96c6310084d3b63739e0a3fbf446b8d`.

Le evidenze numeriche essenziali sono persistenti nella tabella, indipendentemente
dalla permanenza dei file temporanei.

## Riproduzione

Preflight, baseline e storia:

```bash
git status --short
git rev-parse HEAD
git merge-base HEAD main
git show 55a1b1d3:config/code-quality/complexity-baseline.json | jq '{source_commit, generated_at, engines}'
git merge-base --is-ancestor 11ed944a 55a1b1d3
git show 11ed944a:config/code-quality/complexity-baseline.json | sha256sum
git show 30b3dd7e:config/code-quality/complexity-baseline.json | sha256sum
git log --format='%H %s' 55a1b1d3 -- config/code-quality/complexity-baseline.json
python3 /tmp/gaia-baseline-provenance.py "$PWD" \
  /home/cbo/CursorProjects/GAIA/reports/code-quality/complexity-audit-2026-10-08-summary.json \
  /tmp/gaia-baseline-provenance-reproduced.json
make complexity-ratchet BASE_REF=main
make complexity-check
```

L'exit 1 di `merge-base --is-ancestor` è l'evidenza della non-discendenza di
`11ed944a`, non un errore di esecuzione. Il seguente snippet rende indipendente
la riproduzione delle misure dalla disponibilità dello script temporaneo.
Ripetere per i path/commit nella tabella; misurare `<commit>^` e `<commit>`.

```bash
python3 - 1995a1fc backend/app/modules/wiki/mcps/http.py <<'PY'
import ast
import dataclasses
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

commit, source_path = sys.argv[1:]
root = Path.cwd()
spec = importlib.util.spec_from_file_location("quality", root / "tools/code_quality/complexity.py")
quality = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = quality
spec.loader.exec_module(quality)
for revision in [f"{commit}^", commit, "11ed944a", "b89e598c", "55a1b1d3"]:
    source = subprocess.check_output(["git", "show", f"{revision}:{source_path}"], text=True)
    if source_path.endswith(".py"):
        visitor = quality.PyVisitor(root / source_path, source)
        visitor.visit(ast.parse(source))
        payload = {
            "callables": [dataclasses.asdict(item) for item in visitor.callables],
            "file_metrics": {"loc": quality.effective_loc(source.splitlines(), 1, len(source.splitlines()))},
        }
    else:
        with tempfile.NamedTemporaryFile(mode="w", suffix=Path(source_path).suffix) as handle:
            handle.write(source)
            handle.flush()
            payload = json.loads(subprocess.check_output(
                ["node", str(quality.JS_AST_HELPER), handle.name], text=True
            ))
    print(json.dumps({"revision": revision, "path": source_path, **payload}))
PY
```

Non usare `complexity-baseline`, `baseline-repair` o modifiche alle soglie.
Una futura riconciliazione della baseline richiede un'attività distinta,
ownership esplicita, review della provenance e approvazione del relativo scope.
