# Sister: identità della richiesta e confronto prima/dopo

Change: `sister_identity_v1`, aperta il 9 novembre 2026. Stato: **in produzione**
dal 9 novembre alle **11:59:34 italiane** (`2026-11-09T10:59:34.854239641Z`),
con revisione finale basata sull’associazione nativa fra campo e form. Il manifest in
[`evidence/SISTER_IDENTITY_CHANGE_2026-11-09.json`](evidence/SISTER_IDENTITY_CHANGE_2026-11-09.json)
conserva file, hash, verifiche e stato del rilascio. T0 è lo Start del processo
verificato: worker healthy, zero riavvii al controllo iniziale, cinque hash
corrispondenti. Le verifiche sui primi PDF e sugli ID salvati sono conservate nell’evidenza di
rilascio; nessun miglioramento di performance già dichiarato.

## Problema osservato e intervento

Un HTML reale di documento pronto contiene il form POST `VisualizzaDocumentiFB`,
azione `/Visure/ConsultazioneRichieste.do`, hidden `idRichiesta`. La richiesta
GAIA corrispondente non conservava l'ID: l'estrazione precedente cercava negli
URL. Il menu «Richieste» punta invece a `/Servizi/ConsultazioneRichieste.do`;
il vecchio default dell'elenco usava `/Visure/` e produceva una pagina d'errore.

La change acquisisce l'identità dal form prima del download, sia nel flusso
CAPTCHA sia nel flusso diretto e nella risposta «non ancora prodotto». Usa il
callback repository esistente, vincolato al claim corrente. Un download
interrotto può quindi essere ripreso con l'ID già salvato. Un claim scaduto o
rilasciato non può aggiornare la riga.

Il worker preferisce il collegamento elenco presente nel DOM, controllando
origine HTTPS, endpoint e convenzione. Ripara il solo fallback dell'azione
`metodo=lista` da `/Visure/` a `/Servizi/`, anche per URL già persistiti.
L'azione POST del documento conserva `/Visure/`. Una pagina priva dei controlli
`radioCount` viene classificata come errore del servizio prima del matching.

ID discordanti interrompono l'operazione. L'assenza dell'ID resta esplicita;
non autorizza abbinamenti per somiglianza o nuovi invii delle richieste pendenti.
Restano invariati schema DB, credenziale associata, token, numero tentativi,
prima data di invio e budget di 24 ore. Non cambiano concorrenza, cooldown,
allowlist o abilitazioni degli account.

## Registro attività

| Attività | Evidenza / stato |
| --- | --- |
| Audit produzione in sola lettura | HTML documento pronto, URL menu e righe DB confrontati; nessun documento reale scaricato per il test |
| Baseline storica | Finestra UTC `[2026-11-02 08:11:10, 2026-11-09 08:11:10)` |
| Estrazione identità | Nuovo `sister_submission_identity.py`, acquisizione prima di abbandonare la pagina |
| Recupero elenco | Nuovo `sister_pdf_recovery.py`, navigazione osservata e polling limitato |
| Persistenza | Test repository reale SQLite: claim corrente, stale e rilasciato; download interrotto e ripresa |
| Browser | Test Chromium su HTML sanificato con la struttura osservata in produzione |
| Telemetria | Eventi `remote_identity` e `recovery_navigation`, versione nello step `identity_v1` |
| Validazione finale | Risultati e hash nel manifest; log dettagliati nella directory temporanea indicata dal manifest |
| Rilascio / rollback | Eseguito sul solo worker visure; immagine precedente e script di rollback conservati sul server |

## Prima attivazione del 9 novembre

Evidenza completa: [SISTER_IDENTITY_RELEASE_2026-11-09.json](evidence/SISTER_IDENTITY_RELEASE_2026-11-09.json).
Release sul CED: `/opt/gaia/releases/sister-identity-v1-20261109T1040`.

- Test ripetuti prima del rilascio: **216 passati** in 10 processi isolati;
  coverage **100% statement e branch** sui cinque runtime distribuiti.
- Ruff del perimetro, format dei quattro file nuovi e ratchet contro merge-base
  passati. I problemi globali delle modifiche Presenze concorrenti non sono
  inclusi nell'immagine rilasciata.
- Immagine `gaia-sister-identity:identity-v1-20261109T1040`, ID
  `sha256:654bb58d80ff63f0e8ef6c47eed634f4c9b7f31f6bca6922d53e210a2fbb9fc8`.
  Confrontati tutti i 3.846 file applicativi iniziali: solo tre file cambiati
  e due aggiunti; `sister_observability.py` invariato.
- Prova isolata sull'immagine finale in rete `none`: import del worker,
  Chromium e acquisizione ID da form di prova superati, Python 3.12.3.
- Arresto graduale con uscita 0. Il primo tentativo ha attivato il rollback
  automatico per un confronto troppo rigido dell'ordine dei mount. Volumi,
  sorgenti e permessi erano identici; corretto il solo controllo operativo e
  ripetuta l'attivazione. Il manifest conserva entrambi i tentativi.
- Processo della prima revisione verificato healthy alle `2026-11-09T10:47:35Z`, zero riavvii,
  hash corretti e ambiente/volumi conservati. Nel primo minuto osservato nessun
  evento identità e nessun PDF: non è ancora un campione utile per il confronto.

Rollback disponibile: eseguire sul CED
`/opt/gaia/releases/sister-identity-v1-20261109T1040/rollback.sh`.
Usa arresto graduale e immagine precedente dedicata
`gaia-sister-identity:rollback-20261109T1040`; non modifica dati o altri servizi.
Non eseguire rimozione degli orphan segnalati da Compose: sono gli altri servizi
GAIA, volutamente esterni al file di rilascio del solo worker.

Aggiunte evidenze allineate alla prima attivazione:
[SISTER_IDENTITY_BEFORE_T0_2026-11-09.json](evidence/SISTER_IDENTITY_BEFORE_T0_2026-11-09.json)
e [SISTER_IDENTITY_AFTER_INITIAL_2026-11-09.json](evidence/SISTER_IDENTITY_AFTER_INITIAL_2026-11-09.json).
La prima contiene i sette giorni pre-T0; la seconda il solo intervallo iniziale.
La baseline storica precedente resta conservata. Il collector read-only sul
server è `collect.py` nella directory di release; conserva la prima baseline
allineata e aggiorna `after_t0_initial.json`. Prima di raccogliere finestre
successive archiviare ogni acquisizione con nome e cutoff distinti, come sotto.

## Revisione finale: associazione nativa fra campo e form

La prima revisione ha scaricato un PDF reale ma ha emesso due eventi
`identity_v1_known/missing` per la stessa richiesta. Il controllo dell'HTML
ha evidenziato markup tabellare malformato: il campo `idRichiesta` si trova
fuori dal sottoalbero DOM del form. Il selettore `form input[...]` lo escludeva.

La revisione finale usa `input.form`, l'associazione nativa gestita dal browser.
I campi privi di form vengono esclusi; sul form associato restano obbligatori
POST ed endpoint HTTPS SISTER ammesso. Non viene ricostruito il legame per
vicinanza nel DOM. Il test Chromium riproduce il caso: vecchio selettore fallisce,
nuovo selettore passa, campo orfano ignorato.

Nuova verifica: **217 test passati**, coverage **100% statement e branch** sui
cinque runtime, Ruff/format e ratchet passati. La nuova immagine cambia solo
`sister_submission_identity.py` rispetto alla prima revisione, su 3.848 file
applicativi confrontati. Import e prova Chromium sull'immagine finale superati
in rete `none`. Ultimo riavvio graduale con uscita 0; ambiente e mount invariati.

Immagine finale: `gaia-sister-identity:identity-v1-form-owner-20261109T1055`, ID
`sha256:68156b4f755b973a8c0e424062dbdcaecf60e05b0794b9849595e6038a4ed720`.
T0 finale: `2026-11-09T10:59:34.854239641Z` (11:59:34 italiane).
Evidenza autorevole:
[SISTER_IDENTITY_FORM_OWNER_RELEASE_2026-11-09.json](evidence/SISTER_IDENTITY_FORM_OWNER_RELEASE_2026-11-09.json).
Il rollback del paragrafo precedente torna all'immagine originale pre modifica.

Controllo sul traffico reale fino alle **12:06:58 italiane**: due navigazioni
elenco riuscite su richieste pregresse; zero errori di navigazione e zero
conflitti di ID nei nuovi eventi. In questa finestra non si è ancora verificato
un nuovo download o un passaggio di acquisizione dell'identità. **La conferma
ID → riga DB → PDF su un nuovo documento resta pendente**, distinta dai test
Chromium già passati. Il worker resta healthy e senza riavvii.
Snapshot: [SISTER_IDENTITY_AFTER_FORM_OWNER_2026-11-09.json](evidence/SISTER_IDENTITY_AFTER_FORM_OWNER_2026-11-09.json).

Per il confronto conservare come prima i sette giorni terminati alla prima
attivazione (`10:46:39Z`) e come dopo i sette giorni che iniziano a T0 finale
(`10:59:34Z`). La fase intermedia è una transizione da escludere dal confronto
principale; i due intervalli mantengono durata di sette giorni. Entrambe le
revisioni e il rollback operativo restano nel registro. I conteggi dei due
eventi di ID mancante nella transizione non misurano due richieste distinte.

## Baseline conservata

La prima acquisizione è conservata in
[`SISTER_IDENTITY_BEFORE_2026-11-09.json`](evidence/SISTER_IDENTITY_BEFORE_2026-11-09.json).
La baseline da usare per i confronti è
[`SISTER_IDENTITY_BEFORE_V2_2026-11-09.json`](evidence/SISTER_IDENTITY_BEFORE_V2_2026-11-09.json),
riestratta sulla stessa finestra con la query finale schema 2. La prima non è
stata riscritta. Schema 2 distingue acquisizione dell'ID dalla sua presenza
nella riga DB al momento del report e associa le durate al `run_id`.

| Metrica, sette giorni | Prima |
| --- | ---: |
| Eventi download riuscito / richieste PDF distinte | 1.441 / 1.441 |
| PDF per ora di calendario | 8,58 |
| Eventi di polling / richieste distinte in polling | 4.229 / 14 |
| Retry per errore di correlazione | 4.223 |
| Avvii browser | 4.723 |
| Durata esecuzioni riuscite p50 / p95 | 45,4 s / 252,4 s |

Gli account `62a686a7` e `73fb2ea0` producono rispettivamente 786 e 655 PDF.
Gli altri tre account osservati producono zero PDF e totalizzano 361 errori
di autenticazione/abilitazione. Le configurazioni presenti nei JSON sono
fotografie all'acquisizione, non ricostruzioni storiche. Gli errori di
abilitazione richiedono un intervento distinto, per non confondere gli effetti.

## Raccolta ripetibile

Query autorevole: [`scripts/sql/sister_identity_metrics.sql`](../../../scripts/sql/sister_identity_metrics.sql).
È una transazione `READ ONLY`, con timeout di 30 secondi, ed emette un JSON.
Sul server, dalla directory che contiene la query, per esempio:

```bash
docker exec -i gaia-postgres sh -c 'exec psql -X -qAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v user_id=1 -v window_start="$1" -v window_end="$2"' sh \
  '2026-11-02T08:11:10+00:00' '2026-11-09T08:11:10+00:00' \
  < scripts/sql/sister_identity_metrics.sql > sister-metrics.json
sha256sum scripts/sql/sister_identity_metrics.sql
```

Per ogni acquisizione conservare JSON, hash della query, intervallo UTC
semiaperto, hash dei cinque file distribuiti, identificativo immagine/container,
T0 e cambi di configurazione nel periodo. Usare la stessa query per prima e
dopo. Non sostituire i vecchi file: aggiungere evidenze datate. Esportare prima
della retention della telemetria. Non includere credenziali, HTML o codici fiscali.

## Protocollo di rilascio

1. Verificare test, coverage dei cinque runtime, Ruff e ratchet contro
   merge-base; conservare risultati nel manifest. Nessun commit/push implicito.
2. Preparare un'immagine selettiva a partire dall'esatto runtime attualmente
   distribuito, applicando solo i cinque file del manifest. Conservare immagine
   precedente e hash per rollback. Il checkout contiene modifiche concorrenti:
   non fare un rebuild indiscriminato. In particolare `sister_observability.py`
   locale differisce già da produzione e non appartiene a questa change.
3. Attendere il termine delle esecuzioni in corso e le normali condizioni di
   riavvio del worker; non interrompere un invio remoto per accelerare il deploy.
   Distribuire il solo servizio visure con la procedura operativa del progetto.
4. Verificare hash nel container avviato, stato processo e primo evento
   `identity_v1`. Registrare ora UTC di attivazione e di prima evidenza come
   tempi distinti. T0 è l'attivazione del nuovo processo verificato.
5. Controllare che un nuovo PDF abbia ID nella riga richiesta e che una ripresa
   utilizzi la stessa credenziale e lo stesso ID senza nuovo invio. Non forzare
   un CAPTCHA, un errore o una richiesta fatturabile come prova.
6. In caso di regressione comprovata, tornare all'immagine precedente e
   registrare Trollback. Nessuna cancellazione degli ID già acquisiti o reset
   dei pending: il DB resta compatibile con il codice precedente.

## Valutazioni dopo T0

Le verifiche seguenti sono una checklist operativa, non task schedulati.

| Scadenza | Controllo |
| --- | --- |
| T0 + 1 ora | Worker sano, eventi presenti, ID coerenti, errori/conflict esaminati singolarmente |
| T0 + 24 ore | Prima finestra completa, campione e distribuzione per account, errori pagina e retry |
| T0 + 72 ore | Conferma andamento; separare richieste pregresse senza ID e nuove richieste |
| T0 + 7 giorni | Confronto principale di pari durata e composizione; conclusione documentata |

Per le finestre brevi estrarre anche un intervallo pre-T0 di pari durata e,
quando possibile, con le stesse fasce di operatività degli account. Per il
confronto principale usare la baseline pre prima attivazione e
`[T0 finale,T0 finale+7d)`, escludendo la transizione descritta sopra. Se nel mezzo cambia query o configurazione, riestrarre
entrambi i periodi oppure dichiarare il confronto non omogeneo.

Metriche primarie, per account e aggregate:

- PDF distinti / ore di calendario; riportare anche orari effettivi di
  disponibilità degli account, se ricostruibili, senza inventare ore attive.
- Retry di correlazione e avvii browser ogni 100 PDF; denominatore zero produce
  «non valutabile», non zero. Eventi di polling / richieste in polling misura
  il carico di recupero; non equivale a una durata.
- Richieste con identità acquisita / richieste osservate; assenze e conflitti
  separati. `captured` significa evidenza DOM/URL e passaggio alla gestione dello stato, non
  garanzia di callback o commit: un claim stale può rifiutare la scrittura.
- `identity_present_at_report_requests` verifica separatamente il DB attuale;
  non prova la presenza storica al tempo dell'evento. I contatori di outcome
  distinti possono sovrapporsi per richiesta: non sommarli come denominatore.
- Durata p50/p95 delle sole esecuzioni riuscite, con dimensione campione.
  Non include attesa in coda o autenticazione prima del claim; non rappresenta
  il tempo totale dalla creazione al PDF.

Criteri iniziali: nessun PDF attribuito alla richiesta sbagliata, nessun
aggiornamento da claim stale, nessun reset del budget. Ogni conflitto va
analizzato; un conflitto correttamente bloccato non implica da solo rollback.
Dopo almeno 100 PDF post-T0 sugli stessi account produttivi, obiettivo di
riduzione dei retry di correlazione per 100 PDF di almeno il 50%, senza calo
del throughput oltre il 10% o crescita del p95 oltre il 20%. Sono soglie di
revisione, non risultati promessi né un test causale automatico.

Separare l'eventuale beneficio sulle nuove richieste da quello sulle vecchie:
gli ID mai registrati non possono essere ricreati dalla pagina d'errore. La
baseline precedente ha zero eventi identità perché non strumentata, non perché
le identità fossero tutte presenti. Annotare indisponibilità Sister, calendario,
abilitazioni, mix soggetto/immobile, CAPTCHA e modifiche concorrenti prima di
attribuire variazioni alla change.
