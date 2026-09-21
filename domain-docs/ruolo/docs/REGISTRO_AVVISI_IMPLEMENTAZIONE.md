# Registro Avvisi: Implementazione Incrementale

## Stato Al 2026-09-21

Primi quattro blocchi implementati: modello persistente, comandi di dominio,
API protette, pagina operatore `/ruolo/tributi/registro-avvisi` e importazioni
Excel/Poste con anteprima e conferma, riconciliazione manuale Poste e decisioni
auditate sui conflitti. Le migration `20260917_0900`, `20260918_0900` e
`20260918_1500` sono preparate, ma non applicate ai database operativi.
Pagina e backend non sono ancora rilasciati; il collegamento ai flussi di
generazione/invio e in lavorazione e non e pronto per il rilascio.
Nessun dato di produzione modificato.

### Ultimo Incremento: Revisione Acquisita Durante La Generazione

I percorsi reali singolo/lotto acquisiscono ora la revisione prima delle
letture e la conservano nelle bozze; migration `20260921_1900` preparata senza
backfill dei documenti precedenti. Implementato il controllo consultivo backend
di tutto il lotto: revisione/data, completezza, provenienza, payload e hash dei
byte. Se un elemento non e valido, viene respinto il lotto intero.
Nessuna conferma persistente, nuova route pubblica o modifica UI: il controllo
non autorizza export/invio. Template/renderer e numerazione definitiva sono
gate ancora aperti. Dettagli in [Generazione 2022/2023](GENERAZIONE_2022_2023.md).
Repeat: 352 test passati, nessuno skip/xfail, coverage full-file 100% dei
runtime modificati e della migration; lint e ratchet verdi, baseline invariata.

### Incremento Precedente: Revisione Concorrente Dei Dati

Preparata la migration `20260921_1700` e le primitive di revisione dei commit
PostgreSQL: 23 tabelle, inclusi import SQL/COPY e inCASS, revisione atomica con
rollback, controllo dei trigger e lock breve per il futuro comando di conferma.
Il dettaglio e in [Generazione 2022/2023](GENERAZIONE_2022_2023.md).
Nessuna migration operativa applicata. In questa seconda tranche non erano
ancora collegati token alle bozze: **non e un'abilitazione di conferma/export**.
Regressione: 294 test passati senza skip/xfail, coverage full-file 100% dei
runtime toccati e della migration, lint e ratchet verdi con baseline invariata.

### Incremento Precedente: Isolamento Bozze 2022/2023

Workflow bozza/conferma approvato dall'operatore. Implementata la sola prima
tranche backend descritta in [Generazione 2022/2023](GENERAZIONE_2022_2023.md):
artefatti privati SQL e manifest/hash, nessun upload NAS, nessun download finale,
protezione dei lotti misti e dei download legacy con annualita mancanti nel
payload. Migration `20260921_1500` preparata, non applicata in produzione.

I 36 casi concorrenti PostgreSQL ora passano senza xfail grazie alla quarantena
delle bozze, **non** perche sia stata implementata una conferma sicura. I risultati
xfail nelle sezioni di audit seguenti documentano lo stato precedente.
Conferma, invalidazione coordinata, anteprima marcata e UI restano da realizzare;
nessun export o invio viene abilitato. Le altre annualita restano legacy.

### Estensione In Corso: Generazione, Invio E STEP

Richiesta del 2026-09-21: integrare generazione/invio, controllo di ammissibilita,
rettifica delle riconciliazioni e report STEP.

- Rettifica implementata: annullamento auditato e versionato con ritorno di
  invii/evidenze alla scheda Poste, poi eventuale nuova riconciliazione manuale.
  Le modifiche successive e gli import dipendenti bloccano l'annullamento.
- `notice_generation.py` e `notice_eligibility.py` sono una bozza di integrazione
  locale, non ancora pubblicabile. Servizi e repository legacy hanno completato
  il collaudo mirato al 100% statement/branch. Il controllo 2022/2023
  richiede storico collegato/verificato; non rende automaticamente eleggibili
  le posizioni prive di dati. Le altre annualita mantengono per ora le regole
  di generazione precedenti. Nessun controllo di spedizione effettiva e attivo.
- Blocco quality ratchet risolto con la semplificazione locale autorizzata:
  `_collect_reminder_candidates` passa da 141 a 138 LOC, eliminando default NAS
  sovrascritti e l'append ridondante alla lista finale. Filtri, importi e
  ordinamento invariati, nessun helper o aggiornamento baseline `ec5b1375`.
- Repeat Tributi: 108 test passati, statement 1847/1847 e branch 720/720,
  full-file 100%. I tre test 2022/2023 sono riallineati con storico collegato
  e verificato tramite comandi auditati, senza bypass del gate. I nuovi casi
  verificano anche rollback condiviso generazione/registro e blocco se cambia
  la verifica STEP dopo la selezione. Eligibility/generation: 28 test passati
  su SQLite e PostgreSQL, statement 106/106 e branch 46/46, 100%.
- Completate UI/API della verifica consultiva e registrazione auditata dei
  tentativi gia effettuati, incluse scritture concorrenti sul documento.
  Resta il coordinamento concorrente al confine generazione/invio materiale.
  Il test del cambio STEP prima della generazione non prova la serializzazione
  di una modifica simultanea durante la generazione. Nessun invio materiale
  deve essere abilitato sulla sola base di questi test.
- Il codice attuale genera file ma non effettua materialmente spedizioni.
  Il follow-up richiede anche il canale automatico Poste: predisposti contratto
  interno, transizioni e inventario HAR offline. Vedi `POSTE_INVIO_AUTOMATICO.md`.
  Endpoint di scrittura, outbox e adapter non sono ancora integrati: nessun
  nuovo comando o worker puo inviare. Nessuna spedizione reale autorizzata.
- STEP: nessun report/tracciato disponibile al momento. Richiesto un campione
  o documentazione; nessun parser o connettore del portale implementato senza
  contratto verificabile. Resta utilizzabile la valutazione manuale auditata.
  Predisposto [il piano di implementazione STEP](STEP_IMPORT_IMPLEMENTAZIONE.md),
  senza codice di import o accesso live: campioni, pratiche/eventi, preview,
  collegamenti/anomalie, conflitti e coordinamento con la generazione.

### Follow-Up Generazione 2022/2023 E Piano STEP

Il seguito estende i test a entrambe le annualita e al cambio immediatamente
prima del commit. La matrice PostgreSQL ora comprende 36 casi: **12 passed e
24 xfailed stretti**. Nessuna correzione runtime e stata applicata: gli xfail
restano difetti riproducibili, non verifiche di sicurezza superate. Il precedente
risultato di sei casi durante rendering era relativo alla sola annualita 2022.

Individuato anche il confine storage: il generatore batch scrive/carica sul NAS
prima del commit e usa nomi per CF/annualita. Il rollback del registro non
rimuove quei file e non ripristina eventuali sovrascritture. Nei test non viene
contattato il NAS; questa osservazione deriva dal codice dei writer dei file.

La proposta [Generazione 2022/2023](GENERAZIONE_2022_2023.md) separa bozza privata,
conferma coordinata e successivo export/invio. Serve confermare questo passaggio
operatore prima della modifica di workflow, storage e writer trasversali.
Non vengono introdotti lock globali durante rendering o una rilettura finale
presentata impropriamente come correzione completa.

Evidenze: `/tmp/gaia-generation-step-races.log` e
`/tmp/gaia-generation-step-unmasked.log`. Il repeat senza xfail dei 12 casi
`before_commit` fallisce esclusivamente con `StaleGenerationPublished`.
Regressione mirata: **93 passed, 2 skipped** (race SQLite, eseguite anche su
PostgreSQL); warning JWT delle fixture legacy. Log
`/tmp/gaia-generation-step-regression.log`. Nessun runtime o migration modificato
in questo follow-up; coverage e metriche runtime precedenti non vengono
presentate come nuove misurazioni. Invio automatico Poste e import STEP restano
rinviati e non operativi.

### Verifica Consultiva E Invii Gia Effettuati

Nel dettaglio documento e disponibile **Verifica dati aggiornati** anche per il
viewer. `GET /{document_id}/ammissibilita` restituisce versione documento, ora
della verifica, esito e motivi per ciascuna posizione. Saldo e regole correnti
sono letti dal repository Tributi; storico, notifica, STEP, dati Poste/inCASS e
collegamenti vengono controllati dal servizio centrale. Gli affidamenti STEP
espliciti bloccano anche quando riguardano documenti generati da GAIA.

Il risultato e consultivo: `authorizes_dispatch` e sempre `false`. Non riserva
un invio e non costituisce uno snapshot transazionale di tutta la contabilita.
La UI mostra l'avvertenza anche in assenza di blocchi. La generazione resta
soggetta al proprio controllo e il futuro invio richiedera una verifica
serializzata con tutti i dati rilevanti, non il riuso di questo esito.

`POST /{document_id}/invii` registra esclusivamente un invio **gia effettuato**:
envelope con motivo/versione, canale (`posta`, `pec`, `messo`, `altro`), data e
ora con fuso obbligatorio, tracking facoltativo, riferimento evidenza e conferma
esplicita. Date future, fuso assente, autore/origine inviati dal client e viewer
sono rifiutati. Nessuna API contatta Poste, STEP o un servizio di spedizione.

- Comando disponibile anche su documenti senza collegamenti: uno storico reale
  va registrato anche se non sarebbe oggi ammissibile per un nuovo invio.
- Lock/versione documento serializzano registrazione e correzioni; tentativi
  simultanei con la stessa versione producono un solo salvataggio e un 409.
- Sono respinti duplicati nello stesso documento/canale per tracking oppure,
  in assenza di tracking, per data/ora. `posta` comprende anche le
  `raccomandata` importate da Poste. Non viene dedotta un'identita fra documenti
  diversi; eventi senza tracking alla stessa ora richiedono verifica manuale.
- Tentativo, evidenza originale `invio_registrato`, nuova versione e audit
  sono salvati nella stessa transazione. La notifica torna `da_verificare`;
  la precedente valutazione e la prova rimangono nello storico. Nessun
  perfezionamento o affidamento STEP viene dedotto dal semplice invio.
- Schede riconciliate restano non modificabili; eventuali correzioni degli
  eventi vanno gestite tramite una futura rettifica auditata, non eliminazioni.

Verifiche di questa estensione: backend `160 passed`, sei skip SQLite dei
casi di concorrenza eseguiti invece su PostgreSQL; cinque runtime al 100%
(`278` statement, `54` branch). Integrazione col repository contabile reale:
`15 passed`. Frontend `71 passed`, full-file 100% (`375` statement, `335`
branch, `152` funzioni, `321` righe) inclusi pagina e navigazione.
Playwright `12 passed`, desktop 1440px/mobile 390px e viewer, API simulate;
screenshot `/tmp/gaia-notice-attempt-390.png` verificato. Il primo tentativo
browser ha rilevato un selettore di test troppo restrittivo sul canale,
corretto usando il ruolo combobox; il repeat completo passa.

TypeScript, ESLint mirato, lint-backend e diff check passano. Ratchet contro
`ec5b1375` verde, baseline invariata. Metriche prima/dopo in
`/tmp/gaia-notice-ui-{before,after}.json`: nessuna nuova violation error-level;
nuovi helper/comandi max cyc/cog `7/7`, UI nuova max `6/5`. Resta un warning
LOC `52` sul comando auditato. Nessun nuovo hotspot o riduzione artificiale
del debito dichiarati. Test/log: `/tmp/gaia-notice-ui-backend-repeat.log`,
`/tmp/gaia-notice-ui-final-unit.log`, `/tmp/gaia-notice-ui-e2e-repeat.log`.

### Audit Concorrenza Della Generazione

Il follow-up del 2026-09-21 aggiunge esclusivamente test e documentazione,
senza modificare runtime, migration o dati operativi. La suite
`backend/tests/ruolo/test_notice_generation_concurrency.py` usa PostgreSQL
temporaneo e uno schema distinto per caso. Se manca `GAIA_TEST_POSTGRES_URL`
salta esplicitamente i test; SQLite non sostituisce questa verifica.

Sono verificati avviso singolo e lotto per tre eventi: pagamento integrale,
notifica perfezionata con evidenza e affidamento STEP con riferimento pratica.
Ogni evento usa i comandi reali, con commit in una seconda sessione. Sono
sostituiti solo rendering e destinazioni dei file: selezione, calcoli,
numerazione, registrazione e commit sono reali. Non viene contattato il NAS.

- Evento confermato prima della generazione: **6 passed**, nessun rendering
  e nessun nuovo documento registrato.
- Evento confermato durante il rendering, prima della registrazione e del
  commit del generatore: **6 xfailed**. L'evento rende realmente inammissibile
  la posizione, ma il generatore registra comunque il documento.
- Gli xfail sono stretti (`strict=True`) e ammettono solo l'eccezione dedicata
  `StaleGenerationPublished`: errori SQL, fixture o comandi non sono fallimenti
  attesi. Con `--runxfail -k during` si ottengono **6 failed**, tutti per questa
  specifica condizione. Gli xfail NON costituiscono collaudo della sicurezza.
- Regressione generation/eligibility/lifecycle/integrazione contabile:
  **93 passed**, due skip dei casi concorrenti SQLite eseguiti su PostgreSQL.
  Warning JWT della chiave corta nelle fixture legacy. Nessun runtime toccato:
  non viene dichiarata una nuova misurazione coverage o complessita.

Log in `/tmp/gaia-notice-generation-audit{,-unmasked,-regression}.log`.
Il limite gia dichiarato e ora riproducibile; nessuna garanzia di invio cambia.

**Decisione necessaria prima della correzione trasversale:** distinguere la
bozza generata dal lotto confermato per esportazione/invio. Proposta: produrre
bozze senza autorizzazione alla spedizione, poi confermare un lotto con verifica
aggiornata e coordinata con tutte le scritture rilevanti. Il primo rilascio deve
chiarire se il passaggio successivo e manuale sul portale Poste o automatico;
una conferma locale non rende atomico un invio esterno.

Il protocollo deve includere pagamenti e import contabili, notifica/STEP,
rettifiche e riconciliazioni, nuovi documenti/orfani, dati Poste/inCASS e policy
di calcolo. Il solo lock sul documento o sulle righe esistenti non protegge
inserimenti nuovi. Una rilettura dopo il rendering lascia ancora una finestra
prima del commit; anche il livello SERIALIZABLE da solo non impone che una
transazione concorrente conclusa prima venga ordinata prima del generatore.
Non vengono introdotti lock globali delle tabelle o un protocollo parziale per
far passare i test. Il cambiamento di workflow e il coordinamento dei writer
richiedono una slice separata e una decisione esplicita prima di procedere.

## Ordine Di Implementazione

1. **Base dati e dominio**: documento, posizioni multiple, tentativi, evidenze,
   valutazione notifica, verifica STEP e audit. Implementato nel primo blocco.
2. **API e anomalie**: permessi di lettura/scrittura, lista paginata, dettaglio,
   ricerca candidati e conferma esplicita del collegamento, inserimento e
   correzione storici. Actor ricavato dalla sessione, mai fidato dal payload.
   Implementato nel secondo blocco.
3. **Pagina operativa**: Tutti, Anomalie, Affidamenti, Importazioni; confronto
   candidati, storico modifiche, conflitto di versione e ricaricamento.
   Implementata nel terzo blocco; Importazioni completata nel quarto.
4. **Import Excel e Poste**: anteprima, conservazione file e riga originale,
   deduplica idempotente, correzioni tracciate e riconciliazione prudenziale.
   Implementati caricamento, riconciliazione manuale delle schede Poste e
   risoluzione esplicita dei conflitti. Nessun matching o overwrite automatico.
5. **Integrazione GAIA**: registrazione dei nuovi documenti e degli invii;
   verifica centralizzata dei blocchi anche al momento dell'invio. Nessuna
   nuova campagna automatica 2022/2023 senza approvazione separata.

Ogni blocco deve essere verificato prima di passare al successivo. Il primo
blocco non costituisce un registro gia utilizzabile dall'operatore.

## Terzo Blocco: Pagina Operatore

La navigazione Ruolo include **Registro avvisi**. Le sezioni dichiarative Ruolo
sono isolate in `frontend/src/components/layout/ruolo-navigation.ts`, come gia
avviene per Presenze; i collegamenti precedenti e i controlli di accesso restano
invariati. I componenti della pagina vivono in
`frontend/src/components/ruolo/notice-register/` e riusano il client HTTP GAIA.

- Elenco paginato con viste Tutti, Anomalie e Affidamenti, ricerca e filtri per
  annualita, notifica e STEP. Importazioni ora offre i flussi del quarto blocco;
  nessuna autorizzazione implicita a inviare.
- Inserimento avviso storico, revisione metadati e posizioni, consultazione
  dell'originale non modificabile. Motivo e versione accompagnano le scritture.
- Ricerca candidati della stessa annualita, confronto dei riferimenti,
  selezione manuale e checkbox di conferma obbligatoria prima del collegamento.
  Disponibile anche lo scollegamento motivato.
- Registrazione evidenze, valutazione notifica e verifica STEP per posizione.
  Le evidenze utilizzabili sono selezionate dall'elenco paginato del documento,
  non tramite inserimento libero di UUID. Timeline paginata per evidenze, invii
  preesistenti e audit.
- Le letture partono solo dopo la risoluzione della sessione e dei permessi.
  Il viewer consulta senza comandi di scrittura; il server resta autoritativo.
  Letture obsolete ignorate/annullate, submit pendenti non duplicabili,
  conflitti di versione segnalati e dettaglio ricaricabile.

### Verifiche Frontend

- Coverage full-file con `VITEST_COVERAGE_INCLUDE` sul package registro, pagina,
  `navigation.ts` e `ruolo-navigation.ts`: 45 test, statement 258/258,
  branch 234/234, funzioni 99/99 e righe 215/215, tutti al 100%.
  Test: `notice-register-page`, `notice-register-lifecycle`,
  `layout-navigation`, `gis-navigation`; repeat del 2026-09-18 conforme.
- Regressione Ruolo/navigation: 138 test passati in 13 file. Playwright:
  `tests/e2e/ruolo-notice-register.spec.ts`, 3 test passati con API simulate,
  desktop 1440px, mobile 390px e viewer; controlli overflow ed errori pagina.
  Screenshot desktop/mobile verificati; non e un collaudo su produzione.
- `npm run typecheck`, ESLint mirato, `git diff --check`: passano.
- Metriche frontend: 15 file inclusi i tipi, 99 callable. Nuovi runtime sotto
  soglia error; massimi cyc/cog 10/9. Le quattro violation error legacy restano
  in `navigation.ts`: LOC file 526 -> 506, `getModuleSections` LOC 292 -> 271,
  cyc/cog 26/49 invariati. L'estrazione dichiarativa e
  `REORGANIZED_AND_CHARACTERIZED`, non riduzione della complessita callable.
- `make complexity-ratchet BASE_REF=ec5b1375
  QUALITY_PYTHON=backend/.venv/bin/python`: passa, nessun finding dopo la
  correzione autorizzata del matcher per duplicati invariati rimossi.
  Evidenze tooling in `docs/code-quality/PROGRESS.md`.
  Baseline, soglie ed esclusioni restano invariate; il debito globale che
  impedisce la sincronizzazione della baseline non viene assorbito.

Nessuna scrittura DB operativa e stata eseguita dal frontend di test.

## Quarto Blocco: Importazioni Excel E Poste

La vista Importazioni consente di caricare XLSX o preparare uno snapshot dei
record `ruolo_tributi_registered_mails` gia presenti in GAIA. Non scarica dati
da Poste o STEP. Anteprima e conferma sono operazioni distinte, entrambe
richiedono `ruolo.tributi.manage_status` oltre al permesso di lettura e al modulo.
Un viewer consulta importazioni, righe e originali senza poter importare.

`ruolo_notice_import_batches` conserva contenuto binario originale, SHA-256,
nome originale (mai usato come percorso), versione parser, autore e conferma.
`ruolo_notice_import_rows` conserva ogni riga operativa, numero di riga,
payload originale e normalizzato, anomalie, fingerprint ed esito. Tutti i dati
vivono nello stesso database, anche gli originali; nessun allegato viene scritto
in directory pubbliche. La crescita dello storage va monitorata dopo il rilascio.

### Tracciato E Deduplica

- XLSX approvato: foglio `Dati`, intestazioni C/D/H/I/U/V/BE verificate, anno
  BE pari a 2022 o 2023. Righe di intestazione/totale/non operative escluse e
  conteggiate. Limiti: 12 MiB compressi, 64 MiB decompressi, 10000 righe,
  128 colonne; tracciati diversi rifiutati, non interpretati per somiglianza.
- Originale binario conserva formule e fogli; il payload di riga usa i valori
  salvati nel file, senza ricalcolare formule o lookup esterni. La correzione
  `29/06/204 -> 29/06/2024` e ora applicata alle date normalizzate I/J/K/L,
  con codice anomalia e originale intatto. Date discordanti/invalide restano
  segnalate; nessuna data o motivazione stabilisce una notifica perfezionata.
- Il documento Excel usa origine `excel_2022_2023` e cumulativo V; riferimenti
  annuali C/D nel namespace `incass`, mai collegati automaticamente a UUID GAIA.
  Numero mancante/non valido genera un identificatore provvisorio deterministico
  e un'anomalia. Riferimenti numerici segnalano il rischio di zeri persi.
- Batch identico per origine/SHA-256 riutilizzato. File binariamente diversi
  con valori uguali mantengono entrambi gli originali ma non duplicano documenti.
  Identita di origine uguale con fingerprint diverso produce `conflict`:
  la riga resta in staging e l'operatore puo confrontare il documento esistente,
  senza sovrascrivere originali, correzioni o valutazioni.
- La conferma ricontrolla gli esiti dentro una transazione. Lock sul batch,
  vincoli univoci e rollback proteggono conferme simultanee, anche da batch
  diversi. Un eventuale 409 richiede ricaricamento/retry; una conferma ripetuta
  di batch gia confermato restituisce lo stesso risultato senza nuovi audit.
- Nessun filtro per pagato/non pagato, SI/da inviare o motivazione. Ogni nuovo
  documento entra con notifica e STEP da verificare. Le evidenze importate non
  vengono scelte automaticamente per una valutazione dell'operatore.

### Poste E Riconciliazione

Lo snapshot JSON conserva tutte le colonne e il raw payload della riga Poste.
Ogni riga produce un documento provvisorio `Poste <UUID sorgente>`, un tentativo
con tracking, data invio e FK alla raccomandata, e un'evidenza da verificare.
Non vengono copiati automaticamente `avviso_id`, `match_status`, annualita
dedotte o soggetto: documento inizialmente senza posizioni, quindi in Anomalie.
L'operatore riconcilia con un documento esistente oppure aggiunge i riferimenti
annuali e usa il collegamento esplicito.

Excel e Poste restano origini distinte: non si fondono sulla base di CF, numero
simile, tracking o flag matched. Il comando auditato descritto sotto trasferisce
invii ed evidenze solo dopo il confronto dell'operatore. I conflitti di import
non vengono marcati risolti automaticamente dopo una modifica del documento.

### Riconciliazione Manuale Poste

- Dalla scheda Poste senza posizioni, ricerca per numero documento, riferimento
  annuale, tracking o CF. La ricerca propone solo documenti non Poste, con
  posizioni e non gia riconciliati. Il CF non costituisce mai una prova di match.
- Il confronto mostra dati correnti, versione, riferimenti annuali e originale.
  Conferma esplicita e motivo sono obbligatori; autore ricavato dalla sessione.
  Il comando controlla sia la versione sorgente sia quella destinazione.
- `POST /ruolo/tributi/registro-avvisi/{document_id}/riconciliazione` riceve
  l'envelope `reason`, `expected_version`, `data` con `target_document_id`,
  `target_version`, `confirmed: true`. Restituisce documento destinazione e
  nuova versione; `resource_id` identifica la scheda sorgente.
- Una sola transazione trasferisce tutti gli invii/evidenze della scheda Poste,
  preservando ID, FK raccomandata e provenance. I lock documento sono acquisiti
  in ordine deterministico. Le FK composite sono scollegate temporaneamente
  dentro la transazione e ripristinate prima del commit.
- Notifica sorgente e destinazione tornano `da_verificare`; anche le verifiche
  STEP delle posizioni destinazione sono invalidate. Le valutazioni precedenti
  restano nello storico audit di entrambi i documenti, con motivo e autore.
- La sorgente non viene eliminata: `reconciled_into_id` punta alla destinazione.
  Originale e audit restano consultabili nella vista **Riconciliati** e nei link
  dei vecchi import. La scheda diventa sola lettura anche lato API. Le viste
  operative Tutti/Anomalie/Affidamenti escludono queste schede archiviate.
- Import successivi conservano la deduplica sulla chiave di origine Poste e
  rimandano alla destinazione. Le righe importate in precedenza mantengono il
  link storico alla sorgente; UI e risoluzione conflitti seguono il rimando.
- `POST /{document_id}/riconciliazione/annulla` permette l'annullamento auditato
  dalla scheda sorgente, con lo stesso envelope di versioni, destinazione,
  motivo e conferma. La UI mostra il confronto corrente prima della decisione.
  Entrambi gli ultimi audit devono identificare la medesima riconciliazione;
  modifiche successive o import che puntano alla destinazione impediscono
  l'annullamento e richiedono una revisione dedicata. Non si ripristinano le
  vecchie valutazioni: notifica e STEP restano da verificare. Per riassegnare
  basta annullare e ripetere la ricerca del documento corretto.
- Il publish dell'import acquisisce il lock sul documento sorgente prima di
  scegliere la destinazione, serializzandosi con l'annullamento. Originali,
  import preesistenti e audit non vengono riscritti. La concorrenza reale
  annullamento/import e verificata su PostgreSQL.
- Schede Poste con posizioni gia presenti sono rifiutate in riconciliazione
  per evitare trasferimenti ambigui di annualita.

### Decisioni Sui Conflitti

Il filtro **Stato conflitti** distingue tutte le righe, conflitti aperti e
risolti (`review=all|open|resolved`). Conteggi batch e `outcome=conflict` restano
l'esito storico dell'import; la decisione e separata in `resolution`.

`POST /importazioni/{batch_id}/righe/{row_id}/risoluzione` usa l'envelope
`reason`, `expected_version`, `data`: `document_id` canonico, `fingerprint`,
`confirmed: true`, `decision`. Sono consentite due decisioni:

- `keep_existing`: mantiene i dati e le valutazioni correnti, chiude il conflitto
  con motivazione; nessun campo o originale viene sovrascritto.
- `register_evidence`: conserva la variante in una nuova evidenza, senza
  sovrascrivere dati o originali, e riapre la verifica notifica. Non assegna STEP.

Per correggere metadati o posizioni, l'operatore usa prima i comandi di correzione
del documento e poi ricarica il confronto. Non esiste un'accettazione automatica
di tutti i valori Excel/Poste. Una decisione non prova notifica o eleggibilita.
Solo righe conflittuali di batch confermati sono risolvibili; fingerprint,
documento e versione sono ricontrollati. Una decisione gia presa non si riscrive.
Lock riga e documento, versionamento e audit impediscono doppie decisioni.
`resolution` conserva autore, data, motivo, scelta, versione, documento ed
eventuale evidenza. Entrambe le decisioni compaiono nello storico del documento.
I viewer possono confrontare e leggere le decisioni, non effettuarle.

### Collaudo Riconciliazione E Conflitti

- Regressione backend Ruolo: `342 passed, 6 skipped` su SQLite e PostgreSQL
  isolato. Gli skip sono esclusivamente i test di concorrenza SQLite; gli stessi
  casi sono eseguiti su PostgreSQL. Test nuovo `test_notice_reconciliation.py`:
  trasferimento con FK attive, rollback dopo trasferimento, blocco scheda
  riconciliata, nuove varianti Poste prima/dopo riconciliazione, autorizzazioni,
  decisioni singole e concorrenti, race fra riconciliazione e risoluzione.
- Coverage backend dei 12 runtime nuovi/modificati: 898 statement e 124 branch,
  100%. Catena migration upgrade/downgrade/upgrade e parita ORM verificate su
  entrambi i database. Nessuna migration su database operativi.
- Frontend: 63 test mirati, full-file sul package registro, pagina e navigazione,
  statement 357/357, branch 316/316, funzioni 141/141, righe 304/304: 100%.
  Regressione Ruolo/navigation: 156 test in 15 file. Nuovo test
  `notice-reconciliation.test.tsx` per confronto, versioni, viewer, errori,
  paginazione candidati, decisioni e filtri aperti/risolti.
- Browser Chromium: 8 test con API simulate, desktop 1440px e mobile 390px,
  checkbox e motivo obbligatori, payload e versioni verificati, navigazione
  dalla sorgente alla destinazione, conflitti aperti/risolti, viewer senza
  comandi. Nessun overflow o errore pagina; screenshot confronto/decisione
  verificati. Non costituisce collaudo su `gaia.lan`.
- TypeScript, ESLint mirato e `make lint-backend BASE_REF=ec5b1375
  QUALITY_PYTHON=backend/.venv/bin/python` passano.
- Ratchet ordinario, non refactoring hotspot: prima/dopo verde contro merge-base
  `ec5b1375`, `findings: []`; baseline, soglie ed esclusioni invariate. Nuovi
  servizi riconciliazione/conflitti: max cyc/cog rispettivamente 14/15 e 10/10;
  nuovi componenti UI max 5/4. Nessuna nuova violation error-level.
- Metriche delle responsabilita ampliate: `notice_import.py` LOC 90 -> 94,
  max cyc/cog 7/11 -> 8/12; `document-detail.tsx` LOC 49 -> 53, max cyc/cog
  6/5 -> 12/11; `import-detail.tsx` LOC 53 -> 60, max cyc/cog 7/6 -> 10/9.
  Sono ampliamenti funzionali sotto soglia, non riduzioni di complessita.
  Il debito globale della baseline resta separato da questa feature.

Evidenze locali: `/tmp/gaia-reconcile-*`. Il primo avvio PostgreSQL dei test
usava un driver psycopg2 non installato; il repeat usa il psycopg3 del progetto
ed e passato. Il server Next di test segnala cache webpack non scrivibile ma
compila e supera gli E2E; non sono stati cambiati permessi o rimossi file utente.

### API Import

Prefisso `/ruolo/tributi/registro-avvisi/importazioni`, registrato prima della
route dinamica `/{document_id}`. Tutti gli endpoint sono protetti.

| Metodo | Percorso relativo | Operazione |
| --- | --- | --- |
| GET | radice | Storico batch paginato |
| POST | `/excel` | Upload multipart `file`, staging e anteprima |
| POST | `/poste` | Snapshot DB Poste, staging e anteprima |
| GET | `/{batch_id}` | Stato e conteggi batch |
| GET | `/{batch_id}/righe` | Righe, originali, anomalie ed esiti paginati |
| GET | `/{batch_id}/originale` | Download autenticato originale, no-store |
| POST | `/{batch_id}/conferma` | `confirmed: true`, `digest`, `reason` obbligatori |
| POST | `/{batch_id}/righe/{row_id}/risoluzione` | Decisione motivata e versionata sul conflitto |

### Collaudo Del Quarto Blocco

- Entrambi gli Excel reali letti e importati in uno schema PostgreSQL temporaneo
  isolato, poi eliminato. Primo file: 4543 documenti, 6499 posizioni; secondo
  file: 4543 duplicati, nessun nuovo documento. Conferme circa 15s e 5s in locale;
  il flusso e sincrono e non e un job riprendibile dopo interruzione del processo.
- Rettifica dell'analisi iniziale: i file disponibili al 2026-09-18 contengono
  6499 riferimenti annuali distinti, non 6498. Nessun riferimento duplicato o con
  prefisso annuale discordante; 22 righe non operative escluse oltre all'header.
- Test backend verificano SQLite/PostgreSQL, permessi, spoofing autore,
  deduplica/confitti, originali, rollback anche al commit, due tipi di conferma
  concorrente e migration upgrade/downgrade/upgrade con parita ORM.
  I test concorrenti sono saltati soltanto su SQLite, eseguiti su PostgreSQL.
- Frontend: 54 test mirati, coverage 100% su 318 statement, 271 branch,
  123 funzioni e 269 righe, includendo tutti i runtime registro e navigation.
  Regressione estesa: 147 test in 14 file. Cinque E2E Chromium passati con API
  simulate, desktop 1440px/mobile 390px, checkbox richiesta, viewer e assenza
  di overflow/errori pagina. Screenshot verificati.
- Typecheck (ripetuto dopo generazione dei tipi Next), ESLint e lint-backend
  passano; baseline di complessita invariata. I nuovi runtime sono sotto soglia
  error; max cyc/cog backend 12/15 e frontend import 7/6. Workspace LOC 45 -> 44,
  massimi cyc/cog 10/9 invariati. Nessun refactoring hotspot aggiuntivo.

Rilascio, applicazione delle migration e conferma import sul database operativo
restano operazioni separate. Nessuna nuova campagna 2022/2023 e stata abilitata.

## Modello Del Primo Blocco

- `ruolo_notice_documents`: identita di origine separata dalla numerazione,
  metadati correggibili, originale JSON conservato e versione concorrente.
- `ruolo_notice_positions`: riferimenti annuali con namespace esplicito,
  `avviso_id` facoltativo e collegamento molti-a-uno verso il documento.
- `ruolo_notice_attempts`: singoli invii e riferimenti alle righe Poste gia
  importate; generazione e invio non sono prove di notifica.
- `ruolo_notice_evidence`: eventi/evidenze originali, anche senza tentativo;
  il database impedisce riferimenti a tentativi di altri documenti.
- `ruolo_notice_notifications`: valutazione corrente distinta dalle evidenze;
  una notifica perfezionata richiede data ed evidenza dello stesso documento.
- `ruolo_notice_recoveries`: verifica STEP corrente per posizione, con pratica,
  data della verifica, riferimento documentale e importo facoltativo. Non e
  un movimento contabile. Le revisioni sono conservate nell'audit.
- `ruolo_notice_audit`: autore, motivo, versione, valori precedenti/successivi.

La valutazione STEP corrente non rappresenta ancora un estratto analitico delle
pratiche STEP: eventuali piu pratiche contemporanee sulla stessa posizione e i
campi dei report saranno modellati dopo averne ricevuto un campione reale.
Non viene ipotizzato un connettore dal solo accesso al portale.

I modelli vivono in `backend/app/modules/ruolo/notice_register_models.py`, i
contratti in `notice_register_schemas.py`, i comandi in
`services/notice_register.py`. Il preesistente `tributi_notice_registry.py`
continua a gestire soltanto numerazione e prenotazioni GAIA, senza modifiche.

## Invarianti

- Nessun comando crea debiti o pagamenti e nessun import autorizza invii.
- Un documento puo essere registrato anche senza posizioni; verra presentato
  tra le anomalie. Una posizione senza `avviso_id` resta da collegare.
- I riferimenti esterni restano stringhe con gli zeri iniziali. `source_notice_id`,
  `codice_cnc` e UUID GAIA non sono namespace intercambiabili.
- Il collegamento manuale verifica esistenza, annualita e assenza di duplicati
  nel documento. Il motivo obbligatorio registra la decisione dell'operatore;
  non viene eseguito matching automatico per CF o contribuente/anno.
- Cambiare o rimuovere un collegamento rimette in verifica la notifica del
  documento e STEP sulla posizione modificata, conservando le precedenti
  valutazioni nell'audit. Il ricollegamento esplicito rende reversibile la
  correzione, senza ripristinare automaticamente una vecchia valutazione.
- Nuovi storici: notifica e STEP `da_verificare`, non `non_affidato_verificato`.
- `Servizio erogato`, una data Excel e l'esistenza di un invio non producono
  automaticamente una notifica perfezionata.
- Notifica perfezionata non implica affidamento STEP, neppure sulla base
  dell'indicazione statistica del 90%.
- I comandi richiedono autore, motivo e versione attesa; serializzano le
  modifiche sul documento con row lock e controllo di versione. Commit e
  rollback appartengono al chiamante, cosi dati e audit restano atomici.
- Nel secondo blocco gli endpoint applicano `ruolo.tributi.view` per la lettura
  e anche `ruolo.tributi.manage_status` per tutte le scritture. Il modulo Ruolo
  deve essere abilitato e l'utente attivo; sono rispettati gli override dei
  permessi individuali e di ruolo.

## Regole Import E Invii Successivi

Importare tutte le righe 2022/2023, anche pagate o dubbie. I due Excel analizzati
hanno valori identici: non devono generare due registri sovrapposti. Il numero
cumulativo della colonna V identifica il documento, C/D le posizioni annuali.
Deduplica da definire su identita di origine e contenuto, non sul solo nome file.

La correzione approvata `29/06/204 -> 29/06/2024` e applicata dal parser con
originale conservato e traccia della normalizzazione nel quarto blocco.
Date discordanti e motivazioni ambigue restano da verificare;
`non notificato` non puo essere riconosciuto cercando la sottostringa `notificato`.

Il saldo corrente va letto dalle posizioni contabili, non dai lookup S/T del
file. Prima dell'invio futuro occorre rivalutare tutte le posizioni coinvolte:
saldo, anomalie, STEP incerto/attivo, notifica e invii pendenti. I dati ancora
incerti restano esclusi. Un sollecito successivo e un'operazione distinta dalla
campagna per avvisi mai notificati.

## Verifiche Del Primo Blocco

La suite `backend/tests/ruolo/test_notice_register.py` verifica creazione senza
debiti, correzioni con originale conservato, documenti cumulativi, collegamenti
reversibili, isolamento delle evidenze, STEP indipendente, rollback, concorrenza
PostgreSQL e ciclo migration upgrade/downgrade/upgrade con confronto ORM/schema.
PostgreSQL viene eseguito su un container temporaneo dedicato, non su GAIA.

Il comando pytest usa `GAIA_TEST_POSTGRES_URL` verso un database di test e
misura i tre nuovi runtime e `app.db.base`, con `--cov-branch` e
`--cov-fail-under=100`. Senza URL vengono saltati esplicitamente i casi PostgreSQL;
il caso di concorrenza non viene sostituito da un test SQLite.

Risultati del primo blocco sul checkout `main@ec5b1375`:

- Suite nuova: 48 test passati, un solo skip SQLite del caso concorrente;
  tutti i casi PostgreSQL eseguiti. Coverage full-file: 302/302 statement e
  54/54 branch, 100% sui quattro runtime nuovi/modificati.
- Regressione `backend/tests/ruolo`: 215 passati e lo stesso singolo skip;
  warning della chiave JWT corta nelle fixture legacy, non nel nuovo servizio.
- Alembic: unico head `20260917_0900`; ciclo upgrade/downgrade/upgrade e
  confronto migration/metadata passati su entrambi i database di test.
- `make lint-backend BASE_REF=ec5b1375 QUALITY_PYTHON=backend/.venv/bin/python`
  passa, incluso format check dei file nuovi. `git diff --check` passa.
- `make complexity-ratchet BASE_REF=ec5b1375 QUALITY_PYTHON=backend/.venv/bin/python`
  passa contro la baseline del merge-base: nessun finding.
- Metriche: i tre nuovi file non esistevano; ora hanno rispettivamente LOC
  173 (modelli), 74 (contratti), 260 (servizio). Ciclomatica/cognitiva massima
  9/13 nei contratti e 6/8 nel servizio. `db/base.py`: LOC 352 -> 356,
  nessun callable. Zero error-level, due warning sulle firme a cinque parametri.
- `make complexity-baseline` rifiuta la sincronizzazione per il debito globale
  preesistente, fra cui `elaborazioni/capacitas_routes.py`. Baseline, soglie ed
  esclusioni non sono state modificate per assorbirlo.
- Grafi Ruolo codice, backend e documentazione aggiornati. Il target Ruolo docs
  non applica ancora `GRAPHIFY_DOC_MODEL` alla variabile letta da Graphify:
  per il refresh viene esplicitato `GRAPHIFY_OPENAI_MODEL=gpt-reserve` dopo il
  caricamento di `.env.graphify`, senza modificare credenziali o Makefile.

## Secondo Blocco: API E Anomalie

Prefisso `/ruolo/tributi/registro-avvisi`. La registrazione dei router legacy
resta invariata; le nuove route sono aggiunte alla fine del router Ruolo.

| Metodo | Percorso relativo | Operazione |
| --- | --- | --- |
| GET / POST | radice | Elenco paginato / registrazione documento storico |
| GET / PUT | `/{document_id}` | Dettaglio / revisione metadati |
| POST | `/{document_id}/posizioni` | Aggiunta riferimento annuale |
| PUT | `/{document_id}/posizioni/{position_id}` | Correzione riferimento annuale |
| GET | `/{document_id}/posizioni/{position_id}/candidati` | Ricerca avvisi della stessa annualita |
| PUT | `/{document_id}/posizioni/{position_id}/collegamento` | Collegamento o scollegamento esplicito |
| GET / POST | `/{document_id}/evidenze` | Elenco / registrazione evidenza manuale |
| GET | `/{document_id}/invii` | Elenco tentativi esistenti |
| GET | `/{document_id}/storico` | Audit paginato, versione decrescente |
| PUT | `/{document_id}/notifica` | Valutazione notifica |
| PUT | `/{document_id}/posizioni/{position_id}/step` | Valutazione STEP per posizione |

Ogni scrittura riceve `data`, `reason` e `expected_version`. I campi estranei
sono rifiutati; `actor_id` e la provenienza delle nuove evidenze manuali sono
assegnati dal server. La risposta contiene `document_id`, `resource_id` e la
versione dopo l'operazione. Errori: `401/403` accesso negato, `404` risorsa
assente/non appartenente al documento, `409` versione obsoleta o duplicato,
`422` dati incoerenti. Gli errori SQL non vengono esposti e le scritture fallite
annullano dati e audit insieme, anche se il fallimento avviene al commit.

Un collegamento richiede `confirmed: true`; `avviso_id: null` scollega senza
eliminare il riferimento annuale. La revisione della posizione elimina il vecchio
collegamento, rimette notifica e STEP in verifica e registra prima/dopo. La
revisione dei metadati o l'aggiunta di una posizione rimette in verifica la
notifica: una valutazione precedente non si trasferisce automaticamente a un
documento corretto. Correzioni identiche ai valori correnti non aggiungono
revisioni; i comandi di valutazione restano comunque decisioni esplicite.

Lista: `view=tutti|anomalie|affidamenti`, `q`, `tax_year`,
`notification_state`, `recovery_state`, `page`, `page_size` (massimo 100).
`q` cerca numero documento, CF, riferimento annuale e tracking. I caratteri
SQL LIKE sono trattati letteralmente. Annualita e filtro STEP devono riguardare
la **stessa posizione**, non due posizioni diverse del medesimo cumulativo.

Anomalie correnti: `posizioni_assenti`, `collegamenti_mancanti`,
`collegamenti_discordanti` (annualita/CF non corrispondenti),
`notifica_da_verificare`, `step_da_verificare`. Gli stati tecnici mancanti sono
letti prudentemente come da verificare; un totale paginato usa gli stessi
filtri della lista. Le anomalie specifiche delle righe Excel/Poste saranno
aggiunte con gli import, non simulate in questa fase.

Ricerca candidati: testo obbligatorio di almeno tre caratteri, paginazione,
codice CNC, CF, nominativo o UUID esatto; risultati limitati all'annualita della
posizione. La risposta mostra dati identificativi, importo originario (non saldo
attuale) ed eventuale collegamento gia presente nel documento. Nessun candidato
viene selezionato automaticamente. Non esiste ancora una correlazione certa
Incass -> UUID Ruolo: un riferimento Incass non viene equiparato a un CNC.

### Evidenze Di Verifica

- Suite dominio + API su SQLite/PostgreSQL: 100 test passati, un solo skip
  della concorrenza SQLite, eseguita realmente su PostgreSQL. Coverage degli
  otto runtime: 641/641 statement e 78/78 branch, 100%, senza esclusioni.
- Autenticazione JWT reale nei test API, permessi del database reali; solo
  `get_db` e sostituito con sessioni nel database temporaneo. Verificati viewer
  su tutte le scritture, modulo disabilitato, utente inattivo, override negato,
  spoofing autore/provenienza, ownership, rollback al commit, filtri combinati.
- Runtime nuovi: `notice_register_api_schemas.py` LOC 122,
  `notice_register_queries.py` LOC 291, route LOC 183. Servizio LOC 260 -> 322,
  massimi cyc/cog invariati 6/8; schemi dominio LOC 74 -> 82, massimi 9/13
  invariati. Router principale LOC 9 -> 12 e nessun callable.
- Perimetro cumulativo: zero error-level, sei warning non bloccanti;
  `make lint-backend BASE_REF=ec5b1375` e `complexity-ratchet` con il venv
  passano. Baseline, scope e soglie non modificati. Resta il limite globale
  della sincronizzazione baseline gia documentato nel primo blocco.

Prossimo blocco: pagina operativa del registro, form manuali e workflow anomalie.
Ancora esclusi import Excel/Poste, inserimento automatico dei nuovi avvisi GAIA,
nuove campagne di invio e parser/connettore STEP. Il GET invii e pronto a leggere
tentativi, ma il comando manuale di inserimento invio non fa parte di questo blocco.
