# Cronologia scansioni condivisa Network — 2026-11-17

Esito **IMPROVED**: quattro mapping identici condividono un solo serializer,
con un Error eliminato, Warning invariati e minore complessita aggregata.
La responsabilita riguarda esclusivamente i sette campi della scan history
nei tre helper router devices, tracking e inference.

## Modifica e invarianti

`_serialize_scan_history(items)` in helpers/devices.py produce la stessa lista
ordinata di dizionari: scan_id, observed_at, status, hostname, ip_address,
mac_address, open_ports. Lo usano device, soggetto tracciato e i due percorsi
inferred. Il confine condiviso evita divergenze fra le quattro rappresentazioni.

- Il fallback `scan_history or []` resta soltanto nel chiamante device; gli
  altri non accettano silenziosamente None. Nessuna truthiness aggiunta.
- Le due query inferred mantengono posto, argomenti e limit=8. Gli altri
  chiamanti mantengono le letture precedenti del contesto e del modello.
- Una sola iterazione, stesso ordine righe e getter, duplicati e ordine chiavi;
  nessun ordinamento, deduplica, materializzazione anticipata o cache.
- I valori non vengono convertiti o copiati: open_ports e observed_at mantengono
  i riferimenti. Gli errori interrompono gli stessi getter e la stessa iterazione.

Espandendo la comprehension del mapper nelle quattro chiamate, tutte le
funzioni preesistenti dei tre moduli hanno AST identico all'originale. Gli
altri nodi modulo restano invariati, salvo gli import necessari per il riuso.
Nessuna modifica ad API, schema, auth, transazioni o logica inferenziale.

## Metriche

| Aggregato dei tre file | Prima | Dopo |
| --- | ---: | ---: |
| Cognitiva | 373 | 364 |
| Ciclomatica | 290 | 287 |
| Callable | 40 | 41 |
| Decisioni (somma cyclomatic meno 1) | 250 | 246 |
| LOC | 1.029 | 1.005 |
| Error | 9 | 8 |
| Warning | 5 | 5 |

Il motore include il corpo annidato ensure_candidate anche nel padre. Escludendo
la seconda registrazione per misurare owner disgiunti, cognitiva 336→330 e
decisioni 227→224: il miglioramento resta dimostrato senza doppio conteggio.
Le comprehension fisiche passano da quattro a una.

| Callable | Cognitive/cyclomatic/LOC/nesting prima | Dopo |
| --- | --- | --- |
| Device serializer | 7/8/55/0 | 6/7/44/0 |
| Tracked serializer | 7/8/39/0 | 6/7/28/0 |
| Inferred principale | 106/61/275/4 | 103/60/264/4 |
| ensure_candidate | 37/24/121/2 | 34/23/110/2 |
| Inferred ARP | 27/15/98/3 | 25/14/87/3 |
| Nuovo mapper | — | 1/2/13/0 |

Il mapper ha un parametro ed e sotto tutte le soglie. Il Warning LOC del
serializer device scompare; la ciclomatica inferred ARP scende da Error a
Warning, lasciando il totale Warning invariato. Nessun debito trasferito al
nuovo helper. I finding legacy nell'inferenza restano visibili.

## Validazione

Artefatti `/tmp/gaia-network-scan-history-refactor-20261117/`.

- Intera suite Network: 1.104 test PASS prima e dopo, zero failure/error/skip;
  comprende 24 nuovi casi in `test_network_scan_history_serialization.py`.
  Nessun test esistente modificato o indebolito, nessuna nuova failure applicativa.
- Tre runtime full-file statement/branch 100%: prima 456/456 statement e
  182/182 branch, dopo 459/459 e 182/182. Per-file dopo: devices 87/28,
  tracking 221/80, inference 151/74. Zero esclusioni, missing o branch parziali.
- 4.000 scenari differenziali sui quattro punti d'uso: mapping, ordine chiavi/
  righe/getter, query/parametri/limit, truthiness, stato iteratori e errori.
  La prova AST verifica il resto delle funzioni, comprese quelle inferenziali.
- Sei mutanti in memoria respinti senza collection error/skip: campo omesso
  (8 failure), righe invertite (2), copia ports (2), ordine campi alterato (12),
  None accettato dal mapper (1), consumo anticipato dell'iterabile (16).
- Ruff runtime/test, format-check nuovo test, lint-backend 260 file e
  diff-check PASS. Ratchet scoped origin/main PASS prima/dopo, merge-base
  `686e529ee011487e0764b9f91d023be063dbdf55`.
- Globale exit 2 per la stessa ambiguita Tributi useEffect[0]<callback>, dieci
  candidati. Il blocco precede la slice; audit peer HEAD Tributi PASS/WIP exit 2.
  Nessun PASS globale, baseline sync o baseline-verify dichiarato.
- Report completi isolati 1.963 file: callable 22.645→22.646, Error
  1.892→1.891, Warning 2.945 invariati. Cambiano solo i tre helper autorizzati,
  zero parse/exception error. Before identico al completo finale telemetry.
- Baseline/scope/soglie/eccezioni/matcher e report condivisi intatti; WIP
  estranei e altre slice Network preservati. Candidati uguali ai byte finali.
- Graphify Network Make: 494 nodi/1.236 archi. Aggiornamento platform docs e
  verifica chunk/warning nel checkpoint finale; nessun graphify-out versionato.

Comandi principali dalla root:

```bash
COVERAGE_FILE=/tmp/gaia-network-scan-history-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-scan-history-refactor-20261117/test-after.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network*.py --junitxml=/tmp/gaia-network-scan-history-refactor-20261117/tests-after.xml
COVERAGE_FILE=/tmp/gaia-network-scan-history-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/devices.py,*/network/router/helpers/tracking.py,*/network/router/helpers/inference.py' -o /tmp/gaia-network-scan-history-refactor-20261117/coverage-after.json --fail-under=100
python /tmp/gaia-network-scan-history-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-scan-history-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/devices.py backend/app/modules/network/router/helpers/tracking.py backend/app/modules/network/router/helpers/inference.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-patch-openai-base-url
make graphify-platform-docs
```

## Stato

HEAD iniziale `743b21c132b19c82d1201f93b59a541a3b28269a`. Singola responsabilita
conclusa; nessun secondo hotspot, commit/push/PR/merge/deploy. Coordinamento peer
chiuso, audit precedente storico; nessun messaggio ordinario al thread inattivo.

Dalla ripresa: 28 slice migliorative, −27 Error, −28 Warning e −190 cognitiva
aggregata del tool. Snapshot attuale 1.891 Error/2.945 Warning; goal generale
attivo. Prossima azione review e nuova selezione alla continuazione.
