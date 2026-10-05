# Piano di riduzione estesa con agenti paralleli

Data: 2026-10-05. Stato: **proposta operativa, non esecuzione autorizzata**.
L'utente richiede un piano completo e la valutazione di agenti contemporanei.
Tre agenti hanno svolto analisi read-only; nessuna nuova modifica runtime.

Follow-up: W0 autorizzata ed eseguita, W1 non avviata. Evidenze aggiornate,
coverage full-file e blocchi del pilota in `PARALLEL_W0_READINESS_2026-10-05.md`;
i numeri sotto restano lo snapshot storico della proposta.

## 1. Strategia e vincoli

Ridurre il debito su larga scala attraverso molte piccole slice indipendenti,
non un refactoring massivo o trasversale. Restano autorevoli `AGENTS.md`,
la skill di progetto, `QUALITY_RATCHET.md` e la policy coverage.
Un goal di implementazione tratta **un solo hotspot revisionabile** e si
ferma: una campagna e un backlog di goal, non un permesso a concatenarli.
L'approvazione di un'ondata deve nominare i goal ammessi; la successiva
richiede un checkpoint e una decisione, senza avvio automatico.

Non cambiare API, UI, schema, auth, identita, transazioni, concorrenza,
calcoli o errori per abbassare le metriche. Non aggiungere esclusioni,
wrapper artificiali, duplicazioni, riformattazioni massive o nuove dipendenze.
Nessun commit, branch, push, PR o merge senza richiesta esplicita.
Il piano non modifica policy coverage, configurazioni o gate CI esistenti.

## 2. Snapshot e diagnosi

Snapshot AST fresco su `main@bfc8e68f` con working tree non pulito:

| Misura | Valore |
| --- | ---: |
| File nel corpus | 1603 |
| Callable | 19713 |
| Violazioni assolute | 4741 |
| Error / warning | 2041 / 2700 |
| Violazioni backend / frontend / worker | 2745 / 1775 / 221 |
| Finding contro baseline corrente | 26 |
| Finding ratchet working tree contro HEAD | 8 |

Violazioni assolute e finding differenziali sono cose diverse. I 26 finding
su 11 file includono crescita sotto soglia e legacy oltre baseline; non
equivalgono a 26 error-level nuovi. Gli otto del working tree sono Wiki
auth/CLI/HTTP preesistenti; nessuno nelle slice Docs/Ruolo completate.
I test worker sono ancora inclusi nel corpus complessita: non rimuoverli
per migliorare il totale. Il conteggio non e coverage o numero di bug.

| Recupero differenziale | Finding | Trattamento |
| --- | ---: | --- |
| Wiki backend auth/CLI/HTTP/Data/experiment | 12 | Ownership delle slice aperte prima; non rimuovere audit, scope o parametri richiesti dal contratto |
| Wiki preview / Ruolo registered-mail row frontend | 2 | Crescita LOC da funzionalita: no split cosmetico per ripristinare baseline |
| Worker browser reliability / reused menu tests | 12 | Goal test-only separati; mantenere scenario e assert, perimetro complexity invariato |

Evidenze: `/tmp/gaia-mass-plan-current.{json,md}` e
`/tmp/gaia-mass-plan-comparison.json`. Dati locali non versionati:
rigenerare prima dell'esecuzione, non dipendere dalla persistenza di `/tmp`.
HEAD e working tree cambiano per lavoro esterno: congelare SHA e ownership
all'avvio di ogni ondata, senza reset o incorporazioni silenziose.

Sono fuori assegnazione iniziale tutti i file gia modificati Wiki/Ruolo,
Presenze/GaTe, worker SISTER e i loro test/fixture: serve prima chiarire
ownership e approvazione delle change gia presenti. Non committarle insieme
al piano o usare i loro risultati per attribuire riduzioni a nuovi agenti.

## 3. Obiettivi misurabili

1. Rendere riutilizzabile il processo: perimetri indipendenti, prove
   riproducibili, ownership e integrazione seriale.
2. Recuperare i gate globali senza assorbire regressioni nella baseline.
   Ogni finding ha una decisione: riduzione behavior-preserving, nessuna
   change sicura, oppure decisione separata sul contratto/tooling.
3. Eliminare progressivamente error-level e branching ridondante nei
   hotspot, mantenendo 100% full-file sui runtime modificati.
4. Scalare solo dopo un pilota verificato. Target di pianificazione:
   6-9 slice in 2-3 ondate iniziali; riduzione cognitiva cumulativa del
   15-25% **sul solo paniere pilota**. Non e una promessa sul repository.
5. Backlog esteso di 20-30 slice da dimensionare dopo il pilota; non fissare
   una data di eliminazione dei 2041 error legacy senza audit e coverage.

Per slice registrare cog/cyc/LOC/nesting, parametri, violation, sum/max dei
file origine e destinazione, callable e dipendenze, prima/dopo. Attribuire
solo delta del perimetro assegnato. `sum(cyc - 1)` aiuta a distinguere la
base di nuovi callable dal branching, ma non sostituisce il ratchet.
`IMPROVED` richiede riduzione della metrica obiettivo senza trasferimento
del debito; LOC spostate, numero di helper e media coverage non sono KPI.

## 4. Team e isolamento

Disponibili quattro slot: **un coordinatore + fino a tre implementatori**.
Il parallelismo e opportunistico: due agenti sicuri battono tre in conflitto.

| Ruolo | Responsabilita |
| --- | --- |
| Coordinatore | Snapshot, backlog, autorizzazioni, ownership, assegnazioni, review aggregati/invarianti, integrazione, gate cumulativi, checkpoint |
| Implementatore A | Un hotspot backend e test esclusivi |
| Implementatore B | Un hotspot frontend o secondo dominio backend indipendente |
| Implementatore C | Un hotspot worker, oppure terzo dominio isolato; test-only se coverage ancora insufficiente |

Ora nessun worktree o branch viene creato. Per la futura implementazione
preferire worktree isolati a SHA stabile, previa approvazione della relativa
predisposizione. Non nasce automaticamente il permesso di creare branch
o commit. Un worktree da HEAD non contiene le change non committate:
non copiarle o considerarle integrate senza manifest e autorizzazione.
Se si approva isolamento detached senza commit, scambiare patch revisionate;
il coordinatore le integra solo con autorizzazione, una alla volta.
Non usare un checkout condiviso per implementazioni parallele di massa.

Registrare prima di assegnare:

```text
slice_id, goal, owner, base_sha, merge_base_sha, baseline_sha
runtime_files, test_files, fixture_files, allowed_new_files
shared_dependencies, forbidden_files, target_metric, before_metrics
test_commands, coverage_reports, artifacts_prefix, risks, status
```

Ownership esclusiva comprende test/helper/fixture, non solo runtime.
`conftest`, schema/router, export index, client API, config, baseline,
`PROGRESS`, `HOTSPOTS`, documentazione condivisa e grafi: single writer.
Nessuna modifica fuori allowlist; una dipendenza condivisa rende le slice
sequenziali o richiede nuova assegnazione, non un ampliamento spontaneo.
Artefatti, coverage, porte, database/schema di test e profili browser devono
avere namespace distinto per agente. Non usare DB o servizi operativi.

## 5. Ordine delle ondate

### W0 - preparazione e recupero dei gate

- Stabilizzare base e ownership delle change aperte, verificare merge-base
  della futura change; HEAD locale e origin/main non sono intercambiabili.
- Rigenerare report, confronto integrale e inventario coverage reale.
- Classificare i 26 finding, incluso debito worker test e mismatch identitari;
  non promettere di eliminare parametri richiesti da nuovi contratti.
- Eseguire `make quality-test`, verificare ratchet/style e suite dei confini
  che verranno toccati; separare failure note da nuove failure.
- Misurare costi di test, CPU/RAM/browser/DB e portare il parallelismo a 2
  se tre suite pesanti peggiorano stabilita o durata.
- Consegnare registro slice, matrice conflitti e tre proposte di goal.

Uscita W0: assegnazioni approvate e test prima riproducibili. Non richiede
che il debito globale sia gia zero, ma vieta baseline update con gate rossi.
Il recupero dei finding e un binario seriale del coordinatore; la riduzione
dei hotspot indipendenti puo avanzare senza fingere un globale PASS.

### W1 - pilota a basso accoppiamento

Ogni riga e un goal separato, condizionato alla coverage full-file prima:

| Slot | Candidato | Cog/cyc/LOC/nesting | Contratto da caratterizzare |
| --- | --- | --- | --- |
| A | `backend/app/modules/catasto/services/anomalie_payloads.py`: `build_anomalia_payload` | 30/24/31/2 | Missing data, payload, priorita e lookup Catasto |
| B | `backend/app/modules/utenze/services/parser_service.py`: `parse_folder_name` | 30/21/79/2 | Ordine regole parsing, Unicode, nomi/codici mancanti, ambiguities |
| C | `frontend/src/features/organigramma/organigramma-selection-controller.ts`: `handleSchemaCardSelect` | 23/12/19/2 | Selezione, schema, pannelli e ordine callback/state |

Test esistenti di dominio e `organigramma-selection-controller.test.ts`
sono punti di partenza, non prova automatica di coverage 100% corrente.
Se un candidato non consente una riduzione conforme, esito NO_SAFE_CHANGE
e checkpoint; non sostituirlo automaticamente con una change piu ampia.

### W2 - IO controllato e worker indipendente

| Candidato | Cog/cyc/LOC/nesting | Prerequisiti |
| --- | --- | --- |
| `backend/app/modules/riordino/services/export_service.py`: `export_practice_dossier_zip` | 35/17/49/5 | Ordine/naming ZIP, file assenti, errori, ownership DB, API export |
| `frontend/src/features/organigramma/organigramma-viewport-controller.ts`: `handleSchemaPanStart` | 22/11/73/3 | W1 UI integrata; pointer lifecycle, pan/zoom, cleanup, capture |
| `modules/elaborazioni/worker/sister_credential_pool.py`: `run_dynamic_credential_pool` | 27/13/44/3 | Ownership SISTER esterna liberata; cancellation, retry, lease, cleanup |

Worker parte solo dopo audit della dipendenza da file SISTER gia in change;
se non indipendente, C resta test-only o inattivo, senza cercare altro
hotspot arbitrariamente. Graphify puo essere stale su simboli worker:
usarlo per orientamento, verificare sempre AST/sorgenti prima del confine.

### W3 - confini condivisi e domain-risk

Client API `frontend/src/lib/api/core.ts` / `request` (24/20/60/2) in
lane seriale: errori, auth, retry, timeout, abort e consumer trasversali.
Poi singole slice worker `BrowserSession.login` (47/19/56/5),
`execute_visura_flow` (71/30/168/5), PostaOnline browser/persistenza,
in ondate separate e senza login o pool concorrenti sugli stessi file.
Skill di dominio e invarianti DB/concorrenza prima della slice.

### W4 - monoliti, prima caratterizzazione

Non iniziare dai massimi semplicemente perche grandi:

| Confine | Cog/cyc/LOC del callable | Approccio |
| --- | --- | --- |
| Operazioni `fuel_analytics` / `anomalies_analytics` | 366/208/402 e 365/160/388 | Slice disgiunte nel tempo: stesso file, query/calcoli/rounding/finestre |
| Catasto `execute_bulk_search_payload` | 363/68/320 | Job/state, provider, failure per item, transazioni; golden output |
| Presenze `PresenzeGiornalierePage` | 550/457/2275 | Lane protetta: lavoro attivo, mapping e GaTe; test stato/UI prima |
| Elaborazioni `ElaborazioniCapacitasWorkspace` | 472/416/2631 | Confini editor, salvataggio, cache e workflow, uno per goal |
| Utenze `DetailContent` | 391/304/1908 | Hook/effetti/forms, auth e rendering; nessuna estrazione cosmetica |

Per ogni monolite fare un goal test-only se necessario: inventario branch,
fixtures deterministiche, characterization API/DB/UI e full-file coverage.
La sola coverage dell'helper estratto o delle righe cambiate non basta.
La prima slice runtime parte soltanto quando tutti i file toccati sono
copribili al 100%. Rami irraggiungibili non autorizzano ignore o cambio
funzionale; richiedono una decisione separata. Non introdurre mega facade.

## 6. Protocollo obbligatorio di ogni slice

Backlog di riserva, **non assegnazione automatica**: backend
`parse_form_fields` (51/21/36/4), `resolve_header_alias` (50/40/43/2),
`parse_particella_line` (66/25/90/8), `_resolve_peer_label` (56/32/43/4),
`event_detection_tags` (107/39/62/6), `compute_visibility` (102/43/64/6).
Parser economici e autorizzazioni vengono dopo il pilota, con prove di
precedenza/Decimal/scope. Frontend `AnagraficaBulkPanel` (181/155/839/2)
richiede una slice export o storico, non il componente intero. Per worker
PostaOnline isolare `_persist_scrape_payload` (47/45/65/1) dal browser
`scrape_registered_mails` (73/41/80/5): atomicita/checkpoint/resume prima
di qualsiasi semplificazione. Stesso file o fixture = ownership seriale.

1. Leggere istruzioni/skill locali, registry, base e Graphify del corpus.
2. Confermare hash dei file assegnati, metriche prima e invarianti.
3. Eseguire caratterizzazione sul runtime originale, documentare failure.
4. Applicare il minimo refactor; no upgrade, fix di dominio o cleanup esterno.
5. Ripetere test, coverage full-file e lint/typecheck pertinenti.
6. Misurare dopo su origine **e tutti gli helper nuovi**, senza amputare
   il report al solo callable. Zero nuova violation/regressione.
7. Ratchet contro baseline del merge-base autorevole, diff e review.
8. Consegnare patch/evidenze al coordinatore, classificare e fermarsi.

Per backend/worker: statement e branch 100%; frontend: statement, branch,
funzioni e linee 100% per ciascun runtime nuovo/modificato. Riportare
denominatori, exclusions e branch parziali; nessuna media compensativa.

Comandi guida, adattati al perimetro e al checkout autorizzato:

```bash
python3 tools/code_quality/complexity.py report PATH_ORIGINE PATH_HELPER --json /tmp/SLICE-before.json --markdown /tmp/SLICE-before.md
python3 tools/code_quality/complexity.py ratchet --base-ref BASE_REF PATH_ORIGINE PATH_HELPER
make lint-backend BASE_REF=BASE_REF QUALITY_PYTHON=backend/.venv/bin/python
make quality-test
git diff --check
```

Usare `COVERAGE_FILE` e report univoci. Frontend: Vitest mirato con
`VITEST_COVERAGE_INCLUDE` per tutti i runtime toccati, ESLint e typecheck.
Worker: suite e interprete del modulo verificati in W0; DB/schema/porte
isolati, nessuna collisione con browser attivi. Non inventare un unico
comando pytest backend valido per tutti i worker.

## 7. Integrazione e controllo globale

Tre livelli, nessun PASS locale sostituisce quelli successivi:

- **Slice:** metriche, test, coverage e ratchet mirati; review indipendente
  del coordinatore senza alterare l'ownership di altri agenti.
- **Ondata:** applicazione autorizzata una patch alla volta, controllo
  dipendenze e hash, suite comuni, coverage cumulativa, ratchet di tutti
  i percorsi. Se due patch cambiano comportamento integrate, fermarsi.
- **Globale:** report completo e confronti non troncati, quality-test,
  style, suite pertinenti e sequenza CI esistente. Non dichiarare globale
  verde con 26 finding o failure inspiegate rimaste.

Congelare la base prima del gate e ricontrollare HEAD/file hash dopo:
un commit esterno o un file cambiato invalida solo le evidenze interessate,
da rieseguire dopo riesame; niente rebase/reset/commit implicito.
Le suite pesanti e i build sono serializzati o limitati in concurrency.

Baseline: un solo writer, comando esplicito **solo dopo ratchet autorevole
PASS**, diff revisionato e baseline-verify. I delta ammessi sincronizzano
debito eliminato o nuovo codice sotto soglia, non nuove violation/scope.
Se il gate globale non passa, baseline resta invariata; non rendere verde
il pilota rigenerandola. Nessun agente scrive baseline o eccezioni da solo.

Graphify: coordinatore single writer per corpus, target make dedicati nel
checkout integrato; force-pruning patch prima del force per simboli rimossi.
Docs con key valida, completamento chunk e assenza semantic failure;
exit 0 da solo non e successo. Se manca key, codice aggiornato e limite
docs esplicito. Grafi ignorati, mai committati. Non usare root grezza.

## 8. Checkpoint e stop

Fine goal: scheda con outcome IMPROVED / REORGANIZED_AND_CHARACTERIZED /
NO_SAFE_CHANGE / BLOCKED, metriche, test, coverage, diff, residui e next
candidate non eseguito. Coordinatore aggiorna PROGRESS/HOTSPOTS una volta
per ondata, attribuendo separatamente delta esterni.

Fermare la slice per: invarianti/ownership o matching baseline ambigui,
nuova failure non spiegata, necessaria modifica funzionale, coverage non
dimostrabile, nuovo debito, goal oltre un hotspot, conflitto con lavoro
esterno. Isolare il problema, non cancellare file o prove altrui.

Fine W1: calibrare throughput reale, costo characterization e suite,
percentuale IMPROVED e collisioni. Scalare solo se ownership, coverage,
integrazione e gate hanno retto; nessuna promessa che tre agenti = 3x.
Prima azione proposta: **approvare W0 e predisposizione isolata**, poi
approvare i tre goal W1 sulla base del manifest definitivo. Questo piano
non avvia implementazione, branch, commit o deployment.
