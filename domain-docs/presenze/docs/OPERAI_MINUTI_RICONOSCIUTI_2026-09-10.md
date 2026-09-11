# Minuti riconosciuti nelle giornaliere operai

GAIA distingue le timbrature originali dai minuti riconosciuti. La stessa
classificazione alimenta le giornaliere, le anomalie, i payload GATE e le
categorie dell'export XLSM. Versione delle regole:
`presenze-2026-09-10-operai-minuti-riconosciuti`.

> **Documento storico del rilascio del 10 settembre.** Le regole su precedenza
> del turno assegnato e assenza di inferenza sono state aggiornate l’11 settembre:
> prevale il codice effettivo giornaliero quando attestato; OPE0714 può seguire
> il cambio operativo a 06–13 confermato; sono inclusi i codici estivi/sabato.
> Vedere [la regola corrente](OPERAI_STRAORDINARIO_USCITA_2026-09-11.md), runtime
> `30828445`. I paragrafi di verifica/deploy sotto mantengono la cronologia.

## Regole

- L'anticipo rispetto all'inizio previsto non genera automaticamente ordinario,
  straordinario o notturno. Il dato timbrato originale resta invariato.
- L'inizio deriva prima dalla regola assegnata alla giornata, anche stagionale,
  poi dalle definizioni nominali dei codici INAZ supportati. Non viene dedotto
  dalla prima timbratura. La durata standard resta quella del gruppo operaio,
  inclusi i diversi teorici del sabato.
- Si completano prima le ore standard; i minuti ulteriori vengono riconosciuti
  solo da 15 minuti in su, conteggiandoli poi al minuto. Non si arrotonda a
  quarti interi: fine standard 14:00, uscita 14:20 vale 20 minuti.
- Il notturno mattutino riguarda la presenza 05:30–06:00 del turno delle 05:30,
  mai i minuti precedenti. Un turno delle 06:00 timbrato alle 05:47 non produce
  13 minuti di notturno.
- La pausa occupa i 30 minuti successivi al completamento delle ore standard.
  Se la pausa è già timbrata, non viene sottratta due volte. Un ritardo sposta
  il completamento delle ore; l'anticipo escluso non lo anticipa.
- Impiegati e percorsi non riconducibili ai turni diurni supportati mantengono
  il trattamento preesistente. Il nuovo calcolo non inventa turni per codici
  sconosciuti e non converte le coppie incomplete o notturne in coppie diurne.

### Attivazione della pausa: decisione definitiva

Il responsabile ha confermato la soglia fissa delle **16:00 incluse**, anche
per chi termina il turno alle 14:00. Non è una soglia relativa alla durata
del prolungamento. Prima delle 16:00 non si applica una detrazione automatica;
le pause effettivamente timbrate restano comunque escluse dal lavoro.
La fascia non retribuita resta nei 30 minuti successivi al completamento delle
ore standard; si esclude solo la presenza in tale fascia, senza doppia detrazione.
Se le ore standard non sono completate, non si sottrae pausa dall'ordinario.

| Uscita | Extra con fine standard 13:00 | Extra con fine standard 14:00 |
| --- | ---: | ---: |
| 14:20 | 80 minuti | 20 minuti |
| 15:00 | 120 minuti | 60 minuti |
| 15:59 | 179 minuti | 119 minuti |
| 16:00 | 150 minuti | 90 minuti |
| 16:01 | 151 minuti | 91 minuti |
| 17:00 | 210 minuti | 150 minuti |

Gli esempi assumono presenza continua, ore standard completate alla fine turno
indicata e nessuna rettifica. Il salto alle 16:00 deriva dalla detrazione completa
della mezz'ora alla soglia inclusa. La decisione sostituisce le ipotesi precedenti
oltre 30 minuti e l'esempio intermedio delle 15:00 con pausa.

## Rettifiche e coerenza

Gli override amministrativi esistenti restano il percorso per rettificare i
minuti: `override_mpe_minutes`, anche zero, sostituisce l'extra calcolato;
`override_straordinario_minutes` aggiunge l'extra esplicitamente rettificato.
I valori STR/MPE grezzi importati non possono ripristinare minuti esclusi.
Una richiesta INAZ accolta non viene interpretata automaticamente come
un'autorizzazione all'ingresso anticipato.

I campi effettivi esposti dalle API sono coerenti con la classificazione.
Il payload GATE usa i totali canonici e non il maggiore fra importato e
ricalcolato. Un totale canonico zero resta zero. Le categorie festive e
notturne rimangono disgiunte e quadrano ai totali dell'export.

Le giornate ND e le anomalie identitarie, incluso il caso Conti della
trascrizione, richiedono una diagnosi individuale e non sono risolte da questa
modifica. L'aggiornamento non valida automaticamente giornate né corregge dati
INAZ, identità, KM o reperibilità.

## Implementazione

- `services/operai_recognized_minutes.py`: calcolo puro su intervalli, senza
  duplicazioni quando le coppie si sovrappongono.
- `services/operai_daily_policy.py`: turni nominali, pausa e precedenza delle
  rettifiche; conserva separati minuti grezzi e riconosciuti.
- `services/operational_quality.py` e `services/schedule_engine.py`: totali,
  stato operativo, ripartizione feriale/festiva/notturna. La qualità operativa
  riusa il calcolo con il turno assegnato, senza un secondo turno nominale.
- `router/helpers/daily_records.py` e `router/routes/collaborators_daily.py`:
  dettaglio, matrice e valori dell'elenco anomalie.
- `services/gate_mobile_payloads.py` e `gate_router.py`: contratto GATE,
  versione delle regole e valori canonici condivisi dai due trasporti.

## Verifica e rilascio

Checkout isolato `GAIA-presenze-minuti-riconosciuti`, branch
`fix/presenze-operai-minuti-riconosciuti`, base `396c975a`.
Le verifiche locali coprono soglie, ritardi, anticipo, notturno, pause già
registrate, override, impiegati, festività, serializzazione e XLSM. Le evidenze
finali sono riportate nel riepilogo della modifica; nessuna verifica locale
costituisce prova di avvenuto aggiornamento della produzione.

La soglia di attivazione della pausa è definita. Prima del rilascio occorre
concordare il mese/perimetro e distribuire GAIA. Poi acquisire uno snapshot
aggiornato e confrontare giornate rappresentative e totali su GATE/Excel.
Non è necessario introdurre un secondo calcolo retributivo in GATE.

### Evidenze precedenti alla precisazione definitiva delle 16:00

- Regressione GAIA: 380 test passati; dopo l'ultimo caso notturno aggiunto e
  la preservazione della precedenza impiegati, ripetuti 84 test contratto/nucleo,
  tutti passati. Nessuna failure residua nelle suite eseguite.
- Coverage statement dei runtime modificati: 1.494/1.494, 100% su tutti gli otto
  file. Dati combinati delle suite pertinenti, senza esclusioni o soglie ridotte.
- GATE: 18 test passati (export XLSM e decisione operativa), TypeScript riuscito.
- Ruff check dei runtime/test toccati e format-check dei file nuovi passati.
- Ratchet mirato contro il merge-base `origin/main` (`9debc990`) passato,
  `findings: []`. Le nuove funzioni restano sotto soglia error; il debito
  legacy resta visibile. Il confronto usa la baseline autorevole, non una
  baseline riscritta nella modifica.
- Metriche iniziali dei due motori: 28 callable, 19 violation, 9 error.
  Motori più nuovo nucleo/policy: nessun nuovo errore, riduzione degli errori
  legacy nel calcolo operativo tramite separazione di teorico, stato e note.
  La funzione pubblica originaria conserva la firma per i chiamanti esistenti.
- Mappe codice GAIA Presenze e GATE aggiornate; artefatti locali non versionati.
- L'aggiornamento globale della baseline, tentato dopo il ratchet della modifica,
  è stato respinto per regressioni preesistenti esterne al perimetro (fra cui
  callback della pagina collaboratori Presenze). Baseline e relative esclusioni
  sono rimaste invariate; il gate mirato verde non equivale a baseline globale
  riallineata.

### Aggiornamento definitivo: pausa alle 16:00 incluse

- Cambiata solo la policy runtime `operai_daily_policy.py`: attivazione fissa
  alle 16:00 invece della precedente ipotesi relativa di 30 minuti. La fascia
  della pausa rimane dopo il monte ore standard, senza duplicare pause timbrate.
- Aggiunti casi 15:59, 16:00 e 16:01 per fine turno 13:00/14:00, turno 05:30,
  pausa timbrata prima delle 16:00, ore standard incomplete e completamento
  tardivo vicino alla mezzanotte. Aggiornata la precedente aspettativa di pausa
  alle 14:00 nel test del turno OPE0613: ora 60 extra, senza detrazione.
- Verifica finale: 176 test GAIA su policy/nucleo, motore, categorie INAZ e
  payload GATE; 13 test API GATE; 18 test GATE su XLSM e decisione operativa,
  tutti passati.
- Coverage della policy: 100% statement e branch (56 statement, 20 branch).
- Metriche `_lunch_intervals` invariate: cognitive 6, cyclomatic 6, LOC 12,
  nesting 1. Ratchet contro `origin/main`: nessun finding. Nessuna nuova
  violazione; baseline non modificata. Ruff check e format-check superati.
- Nessun rilascio, ricalcolo di produzione, sync correttiva o commit eseguito.

### Verifica completa richiesta prima del deploy

- Suite completa pertinente: **396 test passati**. Nuova raccolta coverage
  senza riutilizzo dei dati di esecuzioni precedenti: **1.494/1.494 statement,
  100% per ciascuno degli otto file runtime modificati**.
- Nucleo e policy: **61 test passati**, **100% statement e branch** su entrambi
  i moduli nuovi (94 statement, 26 branch).
- GATE: **18 test passati**; compilatore XLSM al 100% di statement (394), branch
  (260), funzioni (85) e righe (334); TypeScript passato.
- Ruff e format-check dei file nuovi passati; ratchet degli otto runtime
  contro il merge-base di origin/main senza finding. Baseline invariata.
- Deploy e commit autorizzati dall'utente. Rilascio mirato: backend GAIA sul
  proprio server, processo outbound e worker Presenze coerenti; GATE sul VPS.
  La verifica degli hash sul server conferma che i file da aggiornare
  corrispondono alla base attesa, senza drift da sovrascrivere.

### Rilascio del 10 settembre 2026

- Runtime committato in `5383e495f7d38625a18b6f6d4258e2db48803d11`.
- API GAIA aggiornata preservando bind e configurazione; outbound distribuito
  con immagine `gaia-backend:presenze-5383e495`. Nove hash verificati per
  processo, health e API rules/months HTTP 200 con la nuova versione.
- GATE VPS distribuito dal commit `4debb6e`; console e gateway HTTP 200.
- Cicli outbound dopo il rilascio riusciti (10:10:12–10:12:36 e
  10:15:03–10:17:43 UTC). Nuova versione ricevuta per gennaio–settembre.
- Confronto completo agosto: 5.859 giornaliere GAIA/GATE, zero differenze
  sui totali e sulle sette categorie canoniche; nessun record mancante.
- Worker importazioni: cambio automatico completato alla prima finestra senza
  job running, senza interrompere i job INAZ già attivi. Il marker
  `worker-deployed-at.txt` registra `2026-09-10T12:04:03Z`; il log termina con
  `WORKER_DEPLOYED_AND_VERIFIED`, il container è healthy e i nove hash runtime
  coincidono.
- Backup, manifest, overlay compose e rollback sono conservati nella medesima
  directory release. Nessuna riscrittura delle timbrature originali.
- Smoke XLSM sul VPS: 143 giornaliere coerenti di agosto, 10 collaboratori,
  otto categorie identiche ai payload nel dettaglio e nel riepilogo; macro VBA
  preservate e ricalcolo Excel abilitato. Verifica campionaria, distinta dalla
  revisione amministrativa delle giornate.

### Integrazione in main e deploy standard dell'11 settembre 2026

- Hotfix revisionato e integrato in `main` dal merge `f44460b6`; ratchet senza
  finding, otto file runtime al 100% (`1.494/1.494` statement) e i due moduli
  nuovi al 100% anche sui branch (`94` statement, `26` branch).
- Release CED standard `20260911-075930-f44460b6`: checkout pulito sullo SHA
  atteso, build remota completata, maintenance disabilitata e smoke HTTP su
  `gaia.lan` riusciti. Backend, frontend, Postgres, Martin, worker Presenze e
  connector GaTe risultano healthy; gli hash Presenze nell'immagine backend
  coincidono `9/9` con il checkout versionato.
