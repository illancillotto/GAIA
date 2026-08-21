# Addendum per AGENTS.md - Code Complexity Program

Nel pacchetto definitivo questa sezione e gia integrata nel `AGENTS.md` root.
Conservare il file come riferimento e non incollarla una seconda volta. Le
regole GAIA preesistenti, incluse Graphify e coverage, devono restare presenti.

---

## Code complexity program

Per modifiche sotto `backend/app`, `frontend/src` o
`modules/elaborazioni/worker`, leggere prima:

- `skills/gaia-complexity-reduction/SKILL.md` e i riferimenti richiesti;
- `docs/code-quality/README.md`;
- `docs/code-quality/PROGRESS.md`;
- `docs/code-quality/METRICS_AND_BASELINE.md`;
- `docs/code-quality/VALIDATION.md`;
- `docs/code-quality/QUALITY_RATCHET.md`.

Regole:

- preservare comportamento, API, schema dati, auth, transazioni, concorrenza e
  UI salvo richiesta esplicita;
- usare il quality ratchet come modalita predefinita durante gli sviluppi e non
  forzare refactoring non correlati;
- non eseguire refactoring massivi: una sola unita revisionabile per hotspot;
- acquisire metriche prima e dopo;
- il codice legacy sopra soglia puo restare ma non peggiorare;
- nuove violation sopra soglia e nuovi peggioramenti devono fallire;
- il check ordinario della complessita e read-only;
- confrontare la change con la baseline del merge-base prima di consultare o
  aggiornare quella della change;
- aggiornare la baseline solo con comando esplicito dopo il ratchet, senza
  assorbire regressioni, nuove violation o ampliamenti dello scope;
- non usare esclusioni larghe, ignore a livello file o split artificiali;
- mantenere il 100% di coverage dei file runtime modificati secondo la policy
  GAIA;
- preservare modifiche non correlate gia presenti nel working tree;
- aggiornare `docs/code-quality/PROGRESS.md` per tooling e hotspot; registrare
  le evidenze del ratchet ordinario nel riepilogo della change;
- classificare `IMPROVED` solo una riduzione reale; usare
  `REORGANIZED_AND_CHARACTERIZED` per estrazioni metricamente neutre;
- rispettare gli obblighi Graphify gia definiti in questo `AGENTS.md`;
- non creare commit, push, PR o merge senza richiesta esplicita.
- usare la skill direttamente dal repository; non copiarla o installarla nel
  profilo globale Hermes.

Stop condition: fermarsi e chiedere una decisione se il refactoring richiede un
cambio funzionale, se gli invarianti non sono dimostrabili, se il matching della
baseline e ambiguo o se il lavoro supera un singolo hotspot.

---

## Nota Hermes

Non aggiungere un `.hermes.md` solo per questo programma: Hermes gli assegna
priorita superiore a `AGENTS.md`, quindi rischierebbe di nascondere le istruzioni
repo-wide esistenti. L'addendum va fuso nel file autorevole dopo review.
