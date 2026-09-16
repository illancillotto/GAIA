# Capi operai: sabati alternati

Il calcolo autorevole e in GAIA. Un calendario individuale assegnato con un
sabato iniziale e ricorrenza ogni due settimane prevale sul calendario generico
1°/3° sabato o catasto/magazzino. L'alternanza prosegue attraverso mesi e anni.
GATE, giornaliere e export ricevono i minuti risultanti dalla stessa classificazione.

## Configurazione in GAIA

Creare template e regole da **Presenze → Configurazione**. Le assegnazioni
utilizzano il modello e le API amministrative gia disponibili:

1. Creare un template per ciascun gruppo, mantenendo le eventuali regole feriali
   del profilo originario.
2. Configurare la regola del sabato con `weekday=5`,
   `recurrence_kind=alternating_weeks`, `interval_weeks=2`, e `anchor_date`
   uguale al primo sabato ordinario confermato. Non mantenere nello stesso
   template le vecchie regole sabato settimanali o 1°/3°: sarebbero altri
   sabati esplicitamente programmati.
3. Impostare la fascia oraria prevista. Eventuali varianti stagionali devono
   condividere lo stesso sabato iniziale, per conservare la fase della rotazione.
   La durata ordinaria resta quella delle regole operai e dei codici estivi,
   non la differenza arbitraria tra inizio e fine del template.
4. Assegnare i template ai collaboratori con la decorrenza confermata, usando
   gli identificativi Presenze verificati. Il riconoscimento non dipende dal nome.
   L'endpoint amministrativo e
   `POST /presenze/collaborators/{collaborator_id}/schedule-assignments`
   (relativo alla base API), con
   `template_id`, `valid_from`, `valid_to` opzionale e `notes`. La selezione nella
   scheda collaboratore puo filtrare i template in base al profilo: questa change
   non amplia quel filtro; per template personalizzati usare l'API amministrativa.

Gruppi confermati e configurati il 16 settembre 2026:

- Gianluca Cauglia / Andrea Mele: primo sabato **12/09/2026**, poi ogni 14 giorni.
- Antonello Zancudi / Enrico Pala: primo sabato **19/09/2026**, poi ogni 14 giorni.

La decorrenza delle quattro assegnazioni e **12/09/2026**, anche per il secondo
gruppo: il 12 deve essere fuori turno per Zancudi e Pala. Le assegnazioni
precedenti restano intatte per lo storico anteriore. Sono usate le relazioni
canoniche gia presenti; nessuna identita viene creata o rimappata.

## Conteggio

- Sabato previsto: ordinario fino al teorico; restano le regole esistenti su
  anticipo, pausa, eccedenze e rettifiche amministrative.
- Sabato fuori turno: teorico zero; con coppie di timbrature complete diurne,
  tutto il lavoro e straordinario. I valori importati non possono ripristinare
  ore ordinarie o sopprimere l'extra calcolato. Le coppie sovrapposte non si
  contano due volte.
- Un codice INAZ feriale o estivo non annulla la rotazione. I codici di riposo
  `SAB` e `RIPTURN` possono usare il sabato individuale esplicitamente assegnato;
  i codici sconosciuti mantengono il comportamento precedente.
- L'assenza nel proprio sabato usa il teorico previsto e le causali consentite.
  Il criterio mensile catasto dei due sabati gia coperti non annulla un turno
  individuale ancora dovuto.
- Festivita e regole `applies_on_holiday` restano esplicite: la ricorrenza da
  sola non trasforma una festivita in giorno feriale.
- Nessuna assegnazione valida o template inattivo/scaduto: regole precedenti.

## Cambi

Per un cambio stabile creare una nuova assegnazione con decorrenza e utilizzare
un template con la nuova data iniziale. Il resolver seleziona l'assegnazione
valida con decorrenza piu recente; quella precedente resta per lo storico. Non
modificare l'ancora di un template gia usato per lo storico: ricalcolerebbe le
vecchie giornaliere. La mancata presenza non sposta mai la rotazione.

Non e introdotta una funzione dedicata agli scambi occasionali. Le rettifiche
amministrative dei minuti restano disponibili, ma non cambiano il calendario.

## Verifica locale

`backend/tests/test_presenze_capi_saturday.py` copre le due fasi, i cambi di
mese/anno, i codici INAZ, decorrenze e storico, festivita, assenze e l'integrazione
tra assegnazioni persistite, classificazione, qualita e valori effettivi export.
La suite di regressione include schedule engine, regole operai, riconoscimento
minuti, festivita e richieste di timbratura in attesa.

### Esito del 16 settembre 2026

Verifica locale ripetuta sulla base `f0024cc2`: **302 test passati**, soglia
`--cov-branch --cov-fail-under=100` superata. Rispetto alla prima verifica
(299 test e 100% delle righe), aggiunti tre casi per coprire anche i rami:
nessuna assegnazione persistita nel primo/secondo sabato e qualita di un
impiegato senza classificazione preliminare. Nessuna modifica runtime
necessaria per completare la copertura.

| File runtime | Statement coperti | Rami coperti | Coverage |
| --- | --- | --- | --- |
| `operai_schedule_policy.py` | 46/46 | 18/18 | 100% |
| `operational_quality.py` | 137/137 | 56/56 | 100% |
| `schedule_engine.py` | 303/303 | 94/94 | 100% |
| Totale | 486/486 | 168/168 | 100% |

Per ogni file il report JSON conferma zero righe e zero rami mancanti.
Dati di coverage: `/tmp/gaia-sabati-final-coverage.json`. La regressione estesa
`test_presenze_*` e `test_gate_mobile*` passa; il test PostgreSQL del mapping
Presenze passa (`2 passed`).

Il ratchet Ruff sui quattro file Python della modifica passa, inclusa la
formattazione dei file nuovi. `git diff --check` passa. Il ratchet di complessita
runtime contro la baseline al commit base era gia verde e il repeat modifica
solo test e documentazione. La baseline **globale** resta non sincronizzabile
per debito preesistente esterno alla modifica; nessuna baseline viene riscritta
per assorbirlo. Questi risultati non dichiarano verde l'intero repository.

Graphify viene aggiornato con `make graphify-presenze-code` e
`make graphify-presenze-docs`. Gli artefatti rimangono locali e non versionati.

### Comando riproducibile

Dalla root GAIA, la soglia del 100% si applica a righe e rami decisionali
**di ciascuno dei tre file runtime modificati**, senza esclusioni aggiuntive:

```bash
COVERAGE_FILE=/tmp/gaia-sabati-recheck.coverage backend/.venv/bin/python -m pytest \
  backend/tests/test_presenze_capi_saturday.py \
  backend/tests/test_presenze_schedule_engine.py \
  backend/tests/test_presenze_operai_rules.py \
  backend/tests/test_presenze_operai_daily_policy.py \
  backend/tests/test_presenze_operai_festive.py \
  backend/tests/test_presenze_pending_punch_request.py \
  --cov=app.modules.presenze.services.schedule_engine \
  --cov=app.modules.presenze.services.operational_quality \
  --cov=app.modules.presenze.services.operai_schedule_policy \
  --cov-branch --cov-fail-under=100 --cov-report=term-missing \
  --cov-report=json:/tmp/gaia-sabati-recheck-coverage.json
```

Per ogni file, verificare anche nel report JSON `missing_lines=[]` e
`missing_branches=[]`: la percentuale aggregata non sostituisce questo controllo.

## Attivazione in produzione del 16 settembre 2026

La prima attivazione e avvenuta con l'overlay controllato `capi-20260916` sul
server GAIA CED. I deploy standard successivi hanno rimosso correttamente il
codice non versionato, conservandolo nello stash di sicurezza
`pre-modal-widen-deploy-20260916-f0024cc2`. La change corrente porta gli stessi
tre moduli nel branch `main` e nell'immagine backend standard, eliminando la
dipendenza dall'overlay. Il deploy include solo il perimetro Presenze revisionato.

Creati due template (`OPE_CAPI_A_20260912`, `OPE_CAPI_B_20260919`) e quattro
assegnazioni in un'unica transazione. Le regole feriali/stagionali del template
precedente sono conservate; i sabati 1°/3° sono sostituiti da ricorrenze ogni
14 giorni. Nessuna migrazione schema, modifica delle timbrature o del mapping.

Verifiche: dry-run read-only prima dell'applicazione, 16 combinazioni persona/data
su 12/19/26 settembre e 3 ottobre, qualita operativa e percorso Excel concordi.
Sulle giornaliere reali del 12 settembre, Cauglia e Mele hanno 360 minuti teorici
con stato `ok`; Zancudi e Pala hanno teorico zero senza anomalia di presenza.
Per il 19 settembre i ruoli si invertono; i turni futuri ancora senza timbrature
rimangono `unknown`, senza inventare ore lavorate.

Manifest, backup del codice e della configurazione, report apply/verify e
overlay di rollback: `/opt/gaia/releases/capi-20260916/` sul server sorgente.
Le identita canoniche usate sono 48/151 per il gruppo A e 272/175 per il gruppo B.
Verificata anche la cache del GATE VPS: le otto giornaliere dei quattro
collaboratori per 12/19 settembre sono ricevute alle 10:56:45 UTC e concordano
con GAIA (360 minuti ordinari per Cauglia/Mele il 12; zero ore dovute per il
gruppo opposto; il 19 in turno resta senza ore lavorate finche non timbrato).
Lo snapshot anomalie risulta ricevuto alle 10:57:16 UTC. Il run outbound
`b08beeac-acfa-4f35-92d7-33c9c2605743`, avviato dopo le assegnazioni, e concluso
`succeeded` alle 10:57:29 UTC. Nessuna sync manuale aggiuntiva e stata avviata.
