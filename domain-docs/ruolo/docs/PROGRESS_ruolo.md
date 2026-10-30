# GAIA Ruolo — Progress Tracking v1.0

## Rigenerazione dei PDF dei solleciti — 2026-10-29

- **2026-10-30, Avvisi da sollecitare per anno.** Riquadro guidato in Invio
  solleciti: PDF pronti, non riusciti e da creare per anno, un pulsante che
  crea solo i mancanti e riprova i falliti. In «Lotti generati» ogni avviso
  mostra numero, importo e invio PEC. Nomi lunghi abbreviati o tagliati sul
  bollettino v2 (commit `9cc5999c`). Rilasciato sul CED alle 12:38, release
  `year-notices-20261030-024eeadf`; ripristino
  `/opt/gaia/releases/year-notices-20261030-024eeadf/rollback.sh`.
- **2026-10-30, PDF falliti con SIGTRAP/SIGABRT.** Chromium concorrenti
  esaurivano i 512 processi del container backend. Ora un PDF alla volta, con
  tempo massimo di 90 secondi. Rilasciato alle 11:09 (commit `482af0aa`,
  release `pdf-lock-20261030-482af0aa`, solo backend). Ripristino:
  `/opt/gaia/releases/pdf-lock-20261030-482af0aa/rollback.sh`.
- **Difetto.** «Documento sollecito non trovato» sui lotti generati: i PDF
  fuori dal NAS stavano nel `/tmp` del container e sparivano a ogni rilascio.
- **Correzione.** Archivio permanente `RUOLO_REMINDER_STORAGE_PATH`
  (`/runtime-data/ruolo/solleciti`). Un PDF locale mancante si ricostruisce dai
  dati salvati: anteprima, download e lotto Poste usano la stessa logica.
- **Nuovo.** Riquadro «Rigenera PDF» in Invio solleciti: tutti i lotti o uno,
  «Solo template» o «Ricalcola dati e regole» con lo stesso numero avviso.
  Audit `regenerate_document` nel Registro. Bozze 2022/2023 escluse.
- Dettagli e regole: [RUOLO_RIGENERAZIONE_PDF_2026-10-29.md](RUOLO_RIGENERAZIONE_PDF_2026-10-29.md).
- **Pagina Invio solleciti, dopo il rilascio.** Layout compatto, checkbox
  per lotto nella lista, badge «Inviato via PEC» (spedizione PEC inCASS),
  anteprima aperta di default. I solleciti `failed` si rigenerano da soli
  all'apertura del lotto per chi può modificarli.
  - Rilasciato sul CED il 2026-10-29 alle 17:08 (commit `f73be942`), release
    `solleciti-ui-20261029-f73be942` sopra `pdf-regen-20261029-428aff0d`;
    database invariato a `20261028_1500`.
  - Backend: router attivo più la sola registrazione `batch-overview`, più tre
    file ruolo. Prima del rilascio 85 test superati nell'immagine candidata,
    stessa impronta del filesystem, build frontend riuscita, Compose cambia
    solo l'immagine.
  - Smoke: health OK, home e Invio solleciti HTTP 200, API (anche
    `batch-overview`) senza login 401.
  - Ripristino: `/opt/gaia/releases/solleciti-ui-20261029-f73be942/rollback.sh`.
- **Rilasciato sul CED il 2026-10-29 alle 16:16** (commit `428aff0d`).
  - Release `pdf-regen-20261029-428aff0d`; database invariato a
    `20261028_1500`, nessuna migration.
  - Backend: immagine `invio-solleciti-20261029-76e57300` più i file della
    funzione. Il `router.py` attivo differisce da git: rilasciata la versione
    attiva con le sole due registrazioni nuove. Frontend: sorgenti della release
    precedente più tre file.
  - Prima del rilascio: 78 test backend superati nell'immagine candidata;
    stessa impronta del filesystem; build frontend riuscita; Compose cambia
    solo l'immagine.
  - Smoke: health OK, home e `/ruolo/tributi/solleciti` HTTP 200, API senza
    login 401. Cartella `/opt/gaia/runtime-data/ruolo/solleciti` creata e
    scrivibile dal backend.
  - Ripristino: `/opt/gaia/releases/pdf-regen-20261029-428aff0d/rollback.sh`.


## Pagina «Invio solleciti» — 2026-10-29

- **Una sola pagina.** Solleciti e Invio con Posta Online sono uniti in
  `/ruolo/tributi/solleciti`, voce «Invio solleciti» della sidebar Ruolo
  subito dopo Tributi. Due schede: «Solleciti generati» e «Posta Online».
  `/ruolo/tributi/solleciti/poste` resta valido e apre la seconda scheda.
- **Anteprima avviso.** Per i solleciti generati in PDF il dettaglio lotto
  mostra il PDF reale, lo stesso che verrebbe caricato su Poste. Prima
  l'anteprima c'era solo per le bozze `draft`/`confirmed`, quindi mancava sui
  lotti `generated`.
- **Selezione e caricamento.** «Seleziona per Posta Online» su ogni sollecito
  generato in PDF, solo per chi ha `ruolo.tributi.manage_status`. La selezione
  vale tra lotti diversi, fino a 50. «Carica su Poste» crea il lotto Poste con
  le API esistenti e apre la scheda «Posta Online». Nessuna modifica backend.
- **Verifiche.** 72 test unit sui file toccati e 4 e2e (1440 e 390 px, anche il
  vecchio indirizzo `/poste`); coverage 100% statement e branch sui file
  frontend nuovi o modificati; eslint, tsc e `complexity-ratchet` puliti.
  Suite unit completa: 5369 superati, 2 fallimenti in test non correlati
  (Utenze NAS R22, Catasto GIS) che passano se eseguiti da soli.
- **Rilasciato sul CED il 2026-10-29 alle 12:31**, insieme al box importo del
  2026-10-29 (commit `d86aa857` e `76e57300`).
  - Release `invio-solleciti-20261029-76e57300`; database invariato a
    `20261028_1500`, nessuna migration.
  - Backend appiattito dall'immagine attiva `sync-alerts-20261029-09ec7751`
    (3 layer, stessa configurazione e stessa impronta del filesystem), più i
    due servizi ruolo modificati. Frontend: sorgenti della release precedente
    più i sei file della pagina.
  - Prima del rilascio: 36 test backend superati nell'immagine candidata, con
    PyMuPDF, zxing-cpp e Pillow installati solo in un'immagine di test separata;
    build frontend riuscita; Compose cambia solo l'immagine.
  - Smoke: health OK, home, `/ruolo/tributi/solleciti` e il vecchio `/poste`
    HTTP 200, API senza login 401, altri servizi invariati.
  - Ripristino: `/opt/gaia/releases/invio-solleciti-20261029-76e57300/rollback.sh`.


## Box «Quanto e quando pagare» — 2026-10-29

- L'importo resta su una sola riga: 20pt e `white-space: nowrap`. Prima
  andava a capo dopo `€.` a 26-28pt.
- Avvisi del solo ruolo 2021 con data esplicita: stampano
  `scadenza il gg/mm/aaaa e comunque entro 60 giorni dalla data di notifica`.
  Prima la dicitura era `entro il ...`. Gli altri anni e i campi DOCX non cambiano.
- Test: rendering Chromium con `€. 111.141,88` su una riga dentro il box,
  in entrambe le modalita di scadenza.

## Invio solleciti con Posta Online — 2026-10-28

- **Decisione dell'utente.** INVIA lo preme sempre l'operatore su Poste.
- **Cosa fa GAIA.** Prepara lotti di massimo 50 solleciti generati in PDF:
  - verifica gli indirizzi sullo stradario Poste, con un match esatto su via,
    civico, comune, CAP e provincia;
  - crea le bozze di Raccomandata A/R online in «Verifica e invia»;
  - dall'archivio registra raccomandata, tracking e tentativo nel Registro
    avvisi.
- **Come.** Outbox con migration `20261028_1500`: lotti, avvisi ed eventi
  append-only. I job usano la coda Poste esistente. La guardia di rete del
  worker nega `inserisciInvii` in ogni fase.
- **Nuova interfaccia.** Pagina `/ruolo/tributi/solleciti/poste`, con un link
  dalla pagina Solleciti.
- **Documentazione.** Procedura, stati e limiti in
  [POSTE_INVIO_SOLLECITI_2026-10-28.md](POSTE_INVIO_SOLLECITI_2026-10-28.md).
- **Difetti trovati dai test e corretti:**
  - un `ValueError` del Registro interrompeva la riconciliazione;
  - un PDF alterato fermava l'intero job invece del solo avviso;
  - il runner caricava `tributi_repositories` all'avvio del worker; ora lo
    carica solo quando serve, come l'import Poste esistente.
- **Test nuovi:**

  | Area | Test superati |
  | --- | --- |
  | Backend | 56 |
  | Worker | 47 |
  | Frontend | 18, più l'asserzione del link nella pagina Solleciti |

- **Coverage al 100% di statement e branch** sui runtime nuovi e modificati:
  - backend: 13 file, compresi `db/base.py`, `ruolo/router.py` e
    `notice_dispatch_contract.py`;
  - worker: 3 file nuovi e `posta_online_sync.py`;
  - frontend: 7 file, più `solleciti/workspace.tsx`.
- **Altri gate superati:**
  - `make complexity-ratchet BASE_REF=main` con `findings: []`. Per non far
    crescere le funzioni esistenti, lo smistamento dei job Poste è passato in
    `posta_online_sync._job_runner`;
  - gate di stile Python;
  - ESLint e `tsc`;
  - migration con up/down e confronto modelli;
  - una sola head Alembic.
- **Fix collaterale.** In `tests/test_worker.py` lo stub di `pypdf` era rotto
  su `main` dal commit `b9b0d461`, che importa `pypdf.generic`. Lo stub è stato
  rimosso: nessun file del worker usa `pypdf` e la libreria è nei requisiti del
  backend. Worker: 852 test PASS, uno skip.
- **Suite complete.** Backend: 7.641 PASS, 464 skip, nessun errore.
  Frontend: 5.353 PASS.
- **Problemi preesistenti estranei a questa change:**
  - `tests/test_sister_efficiency.py` non è importabile con `make test-worker`,
    perché manca la root del repository nel PYTHONPATH;
  - nel frontend, `https-access-guide.test.tsx` fallisce per
    `home-sync-alerts`, che fa parte di un lavoro non committato.
- **Ancora da collaudare sul portale reale:**
  - l'indirizzo manuale;
  - `DeleteInvio(id)`;
  - se INVIA spedisca tutte le bozze presenti o solo quelle selezionate.
- **Rilasciato sul CED il 2026-10-29 alle 08:50.**
  - Release `poste-dispatch-20261029-05fa4a86`, database a `20261028_1500`.
  - Immagini `gaia-backend`, `gaia-frontend` ed
    `elaborazioni-worker-poste` con tag `poste-dispatch-20261029-05fa4a86`.
  - Prima del rilascio:
    - 106 test backend e 55 worker superati nelle immagini candidate;
    - build frontend riuscita;
    - Compose cambia solo l'immagine;
    - migration up/down/up provata su una copia dello schema.
  - Smoke dopo il rilascio:
    - health OK, pagina HTTP 200, API senza login HTTP 401;
    - 146 candidati e 0 lotti;
    - nel worker INVIA è bloccato in ogni fase;
    - gli altri servizi sono invariati.
  - Ripristino: `/opt/gaia/releases/poste-dispatch-20261029-05fa4a86/rollback.sh`.
    Se ci sono lotti chiede `FORCE=yes` e li salva prima del downgrade.
  - L'immagine backend era a 127 layer, il limite di overlay. Il rilascio
    `sync-alerts-20261029-09ec7751` l'ha appiattita a 3 layer, con lo stesso
    contenuto: vedi `domain-docs/elaborazioni/docs/SYNC_DASHBOARD.md`.
- **Vincoli del rilascio mirato.** Riguarda backend, frontend ed
  `elaborazioni-worker-poste`, e richiede:
  - `notice_registered_mail_link.py`, usato dalla riconciliazione e mai
    rilasciato;
  - `base.py` e router ruolo attivi più le sole righe nuove, perché le
    versioni attive non hanno il controllo particelle;
  - nel worker Poste, `app/` uguale a quello del backend candidato: la copia
    attuale, del 22 ottobre, non ha i modelli ruolo usati dall'outbox;
  - backend e worker insieme. Il worker attuale tratterebbe un job
    `poste_dispatch_*` come sincronizzazione delle raccomandate.

## Deploy avvisi sul CED — 2026-10-28

- Rilasciata la feature del commit `b7cbc31a` su `gaia.lan` alle 10:43:
  immagini mirate backend/frontend, hotfix e ambiente operativo conservati.
  Schema `20261028_0900`; le cinque regole mantengono date e modalita precedenti.
- Candidato: 277 PASS, uno skip SQLite con equivalente PostgreSQL PASS;
  build produzione e prova migrazioni up/down/up su schema isolato PASS.
  Smoke HTTP/autenticati e stampa sintetica dal backend live PASS;
  verificate tutte le 12.353 credenziali cifrate. Sei CF ambigui sospesi.
- Primo tentativo ripristinato automaticamente per un controllo sui container
  gia fermi; corretto il confronto operativo, secondo rilascio e verifica
  integrita completati. Nessuna regressione applicativa rilevata.
- Backup, rollback, perimetro effettivo e ricevute:
  [rilascio CED](RUOLO_AVVISI_DEPLOY_2026-10-28.md).

## Verifica finale avvisi, accessi e pagatore — 2026-10-28

- Perimetro conclusivo: grafica blu e testi dell'avviso, accessi al portale,
  scadenza fissa dei bollettini v1/v2 insieme al termine di notifica, regole
  persistite e assegnazione del pagatore diverso dall'intestatario. Il modello
  esistente resta selezionabile. Runbook del pagatore:
  `RUOLO_PAGATORE_AVVISO_2026-10-28.md`.
- Corretto un difetto emerso nella verifica: una modifica del pagatore dopo
  la preparazione non invalidava la bozza. La migration `20261028_0900`
  aggiunge trigger PostgreSQL di revisione per insert/update/delete/truncate,
  attivi anche in replica. Test prima rosso e poi verde: la conferma della
  bozza obsoleta viene rifiutata e richiede una nuova preparazione. Verificati
  anche downgrade, compatibilita SQLite e unico head Alembic `20261028_0900`.
- Backend: **1.295 PASS**, di cui 1.293 nel corpus Ruolo e due test STEP
  esistenti sul mantenimento degli avvisi affidati alla riscossione esterna;
  **9 skip SQLite**, tutti con equivalente PostgreSQL eseguito e superato.
  Il corpus Ruolo e suddiviso in quattro gruppi disgiunti; inventario finale
  di 1.302 casi riconciliato con gli XML JUnit. Per i soli sei parametri dei
  workbook non validi e normalizzato l'ID dinamico contenente timestamp ZIP;
  nessun caso e stato eliminato dal confronto.
- Coverage backend combinata **100% statement e branch** su tutti i **25
  runtime** modificati: **3.770 statement, 1.198 branch**, zero righe mancanti
  e zero branch parziali. Restano soltanto le due righe di guardia FK escluse
  gia in HEAD in `tributi_repositories.py`; nessuna nuova esclusione.
  Rimossi gli ignore dal nuovo componente pagatore e dall'ingresso CLI;
  test pertinenti per sessione assente/scaduta, permessi sola lettura e
  comando CSV reale in dry-run con rollback.
- Frontend: **156 PASS su 16 suite**; coverage **100%** sui **7 runtime
  eseguibili** modificati: **768 statement, 745 branch, 262 funzioni, 695
  righe**. I due file di soli tipi sono verificati dal typecheck.
- `make lint-backend QUALITY_PYTHON=backend/.venv/bin/python BASE_REF=HEAD`,
  lint frontend e TypeScript PASS. Restano warning legacy del lint in altri
  moduli e l'avviso JWT sulla chiave corta dell'ambiente di test; nessuna
  failure nel perimetro verificato.
- Ratchet ordinario contro la baseline immutabile di `9ff86d83` PASS, zero
  finding e nessun nuovo debito. Metriche finali su 34 runtime: 656 callable;
  repository tributi LOC `3625 -> 3619`, cognitive/cyclomatic aggregate
  `1348/1156 -> 1345/1154`; pagina Tributi LOC `2906 -> 2854`, aggregate
  `636/761 -> 636/759`; eligibility LOC `168` invariata, aggregate
  `64/56 -> 62/56`. Il debito legacy resta censito. Baseline circoscritta
  sincronizzata dopo ratchet e verificata con scansione fresca, preservando
  tutti i record estranei e i metadati globali.
- Anteprima PDF 2021 verificata senza modificarla: quattro pagine con dati
  dimostrativi, descrizione Irrighiamo, QR WhatsApp/Irrighiamo e codici di
  pagamento decodificabili; entrambi i tagliandi riportano
  `30/11/2026 - Rata Unica`. Verifica circoscritta alla change, non
  certificazione dell'intero repository.
- Limiti operativi confermati: i sei CF con utenze ambigue restano sospesi;
  il generatore DOCX singolo legacy mantiene il destinatario originale,
  mentre la pagina Tributi applica il pagatore tramite i lotti anche per
  l'anteprima singola. Nessun deploy, push o modifica al database degli uffici
  in questo ciclo. Modifiche locali estranee preservate fuori dal commit.
- Evidenze locali: `/tmp/gaia-avvisi-final-20261028/`, inclusi inventario test,
  report coverage, metriche prima/dopo e hash dei sorgenti verificati.

## Descrizione Irrighiamo Insieme nell'avviso — 2026-10-28

- Nel riquadro accanto al QR: «L'applicazione del Consorzio per segnalare guasti
  o rotture e richiedere l'autorizzazione all'irrigazione.» Segue l'invito a
  inquadrare il QR per accedere. Funzioni verificate sulla pagina pubblica
  `https://login.bonificaoristanese.it/`; nessun cambio al collegamento o al QR.
- **30 test mirati PASS, zero skip**, coverage statement/branch **100%** del
  runtime `notice_branding.py` (`26` statement, `2` branch). Il contratto
  verifica la frase nell'HTML e nel PDF con una, due e cinque annualita.
  Lint backend e ratchet autorevole contro HEAD PASS, nessun finding.
  Metriche invariate: LOC `88`, cognitive/cyclomatic aggregate `2/6`.
  Baseline circoscritta sincronizzata e verificata dopo ratchet, senza
  modificare record o metadati concorrenti.
- Anteprima blu 2021 aggiornata e ispezionata: prima pagina completa, entrambi
  i QR decodificati; pagine 2-4 identiche pixel per pixel alla precedente.
  Documentazione del template e provenienza asset allineate; Graphify codice
  Ruolo/backend e docs Ruolo aggiornati con i target dedicati.
- Evidenze locali: `/tmp/gaia-irrighiamo-description-20261028/`. Nessun
  intervento al database o al server degli uffici.

## Data fissa e Rata Unica nei bollettini — 2026-10-28

- I bollettini v1/v2 stampano `gg/mm/aaaa - Rata Unica` su entrambi i
  tagliandi. Nella modalita a 60 giorni `payment_due_date` resta visibile e
  salvata nelle Regole ruolo; con bollettino abilitato e obbligatoria.
  Salvataggio senza data HTTP 422; regole e snapshot storici senza data
  bloccano la generazione con invito a completare le Regole ruolo.
- Senza bollettino il solo termine relativo resta ammesso. Avviso e campi DOCX
  conservano il termine di notifica; box 2021 con data e termine invariato.
  Il fallback legacy a 30 giorni della modalita a data fissa e conservato.
  Nessuna nuova migration: si usa la colonna gia esistente. Nessun backfill
  automatico della data e nessun intervento al database degli uffici.
- Backend **234 PASS, zero skip**, coverage statement/branch **100%** su 15
  runtime (`1532` statement, `406` branch), zero esclusioni. Test API,
  snapshot, regole storiche, assenza bollettino e entrambi i tagliandi v1/v2,
  con date ISO e italiane. Ruff/formatter, lint backend, ESLint mirato e
  TypeScript PASS. Nessuna failure residua nel perimetro verificato;
  permane l'avviso JWT sulla chiave corta dell'ambiente di test.
- Frontend **72 PASS** su quattro suite, coverage statement/branch/funzioni/righe
  **100%** sui tre runtime del form (`78` statement, `91` branch).
  Test pertinenti per conservazione date, campi annuali e correzione regole
  storiche senza data; nessun test aggiunto per la sola percentuale.
- Anteprima blu 2021 dimostrativa aggiornata: le prime tre pagine sono identiche
  pixel per pixel alla precedente; quarta pagina con `30/11/2026 - Rata Unica`
  su entrambi i tagliandi. Bollettino ispezionato; QR, Code128 e DataMatrix
  decodificati. PDF esistenti e server degli uffici non modificati.
- Ratchet ordinario autorevole contro `9ff86d83` PASS, nessun finding.
  Renderer LOC `1772`, aggregate cognitive/cyclomatic `428/433` invariate;
  repository regole LOC `165`, aggregate `42/50` invariate; v2 LOC `128`,
  aggregate `13/18` invariate. Helper scadenza LOC `98 -> 115`, aggregate
  `14/21 -> 31/33`, massimi `9/7`, nessuna violation. Frontend LOC `52 -> 53`,
  aggregate `8/17 -> 7/16`, nessuna violation. Debito legacy invariato.
  Baseline dei cinque runtime sincronizzata dopo ratchet e verificata con
  scansione fresca; record, ordine e metadati concorrenti preservati.
- Graphify aggiornato tramite i target dedicati codice Ruolo/backend/frontend
  e docs Ruolo/piattaforma. Gli output restano locali e non versionati.
- Evidenze: `/tmp/gaia-bollettino-deadline-20261028/`; verifica circoscritta
  alla change, senza certificare l'intero repository concorrente.

## Avviso 2021, font uniforme e due QR — 2026-10-28

- Box `Quanto e quando pagare` degli avvisi del solo 2021: data esplicita dello
  snapshot in `gg/mm/aaaa`, seguita da `e comunque entro 60 giorni dalla data
  di notifica`. Senza data esplicita, soltanto il termine di notifica, senza
  data derivata dalla generazione. Altre annualita e gruppi multiannualita,
  persistenza delle regole, DOCX e bollettini mantengono il contratto precedente.
- Tutto il testo della prima pagina usa Arial/Helvetica/sans-serif, compresi
  titolo ente e importo. Pesi e dimensioni restano differenziati per gerarchia.
- Footer con due blocchi affiancati e QR originali `18mm`: WhatsApp e Irrighiamo
  Insieme, login `https://login.bonificaoristanese.it/`. Il nuovo PNG e identico
  alla sorgente fornita; nessuna rigenerazione o nuova credenziale applicativa.
- Avvertenza con triangolo vettoriale rosso `#c62828` e punto esclamativo rosso.
  Testo: «In caso di mancato pagamento, il Consorzio di Bonifica dell'Oristanese
  tramite l'agente di riscossione attiverà le procedure di riscossione coattiva
  previste dalla legge.»
- Anteprima blu 2021 aggiornata con dati dimostrativi dichiarati su ogni pagina.
  Prima pagina ispezionata, tutti gli span testuali in Arial; due QR, Code128 e
  DataMatrix decodificati. Pagine 2-4 identiche pixel per pixel alla versione
  blu precedente. Layout verificato con una, due e cinque annualita.
- Ratchet autorevole contro `9ff86d83` PASS, zero finding. Renderer LOC
  `1771 -> 1772`, cognitive/cyclomatic aggregate `428/433` invariate. Branding
  LOC `80 -> 88`, aggregate `2/6` invariate. Gestione termine LOC `88 -> 98`,
  aggregate `9/16 -> 14/21`, massimo `5/5`, nessuna nuova violation. La dicitura
  specifica resta nel rendering della prima pagina, senza aggiungere campi
  inutilizzati ai valori condivisi con DOCX/bollettini. Baseline di tre runtime
  sincronizzata dopo il ratchet e verificata; record estranei e metadati preservati.
- Suite finale aggiornata: **229 PASS, zero skip**, coverage statement/branch
  **100%** su 14 runtime (`1477` statement, `394` branch), zero esclusioni.
  Contratti precedenti del numero immagini e del font aggiornati alle modifiche
  richieste e verificati nella suite completa; nessuna failure residua.
  Ruff/formatter e `make lint-backend` PASS. Test Chromium per famiglia font,
  due QR affiancati e scansionabili, palette e triangolo rosso; date esplicite
  ISO/formato italiano e assenza data per il 2021 in entrambe le modalita.
- Graphify Ruolo/backend codice e Ruolo/piattaforma docs aggiornati con i target
  dedicati, chunk semantici completati senza errori. Gli output restano locali.
- Stato locale, nessun rilascio o nuova scrittura sul database degli uffici.
  I sei CF con utenze ambigue restano sospesi in attesa del riscontro dei colleghi.

## Variante cromatica blu — 2026-10-27

- Palette renderer HTML/Chromium: blu principale `#2b5793`, gradiente titolo
  verso `#3e72b3`, fondi azzurri e bordi coordinati. Anche importo, residuo,
  titolo partitario e tabella comunicazioni seguono il blu. Loghi e QR originali.
- Anteprima separata `output/pdf/avviso-2021-anteprima-blu.pdf`; il PDF verde
  precedente resta disponibile per confronto. Testo e coordinate delle parole
  identici sulle quattro pagine, bollettino identico pixel per pixel. Ispezione
  visiva delle prime tre pagine e decodifica QR WhatsApp/Code128/DataMatrix PASS.
- Test aggiuntivi sui colori effettivi calcolati da Chromium in stampa, per data
  fissa e termine a 60 giorni: colore principale, gradiente, fondi, bordi e icona.
  Testi, regole e geometria restano invariati; nessuna scelta tema aggiunta in UI.
- Suite finale: **223 PASS, zero skip**, coverage statement/branch **100%**
  su 14 runtime (`1469` statement, `390` branch), zero esclusioni.
- Metriche dei quattro runtime immutate. Ratchet autorevole contro `9ff86d83`,
  lint backend/formatter e verifica baseline circoscritta PASS. Stato locale;
  nessun rilascio sul server degli uffici. I sei casi utenza restano sospesi.

## Una coppia per utenza e colonna Interessi condizionale — 2026-10-27

- Regola confermata: un avviso -> un'utenza -> un Codice ditta/PIN. I sei CF
  con due utenze sono sospesi in attesa dei colleghi: messaggio uffici, nessuna
  scelta arbitraria e nessuna stampa multipla. Anche il rendering da snapshot
  storici ambigui usa il fallback senza decifrare le coppie.
- Tabella prima pagina GAIA senza colonna Interessi se tutti gli importi annuali
  visualizzati sono zero; intestazione, colonne, celle e colspan allineati.
  Basta un valore non nullo per mantenerla, anche con negativi o compensazioni.
- Dopo il portale, contatti degli uffici seguiti dalla frase sul sito nello
  stesso paragrafo (`8.5pt`, interlinea `1.12`), per tenere tutto sulla prima pagina.
- Verifica finale: **221 PASS, zero skip**, **100%** statement/branch su 14
  runtime (`1469` statement, `390` branch), zero esclusioni. Ruff/formatter e
  lint backend PASS; ratchet sul merge-base `9ff86d83` senza finding.
  Renderer LOC `1785 -> 1771`, nuovo riepilogo LOC `35`, nessuna nuova violation.
  Baseline di quattro runtime sincronizzata e verificata dopo il ratchet,
  preservando metadati e record concorrenti.
- Anteprima 2021 aggiornata: una coppia dimostrativa, Interessi nascosti, contatti
  e sito presenti; quattro pagine marcate come dimostrative. Prima pagina
  ispezionata, QR WhatsApp/Code128/DataMatrix decodificati, pagine 2-4 identiche.
- Graphify codice Ruolo/backend aggiornato (1333/10568 nodi). Aggiornamento
  documentale tramite i target dedicati; output solo locali.
- Stato locale, nessun rilascio o nuova scrittura sul server. Le sezioni
  successive conservano le evidenze delle iterazioni precedenti; questo
  aggiornamento descrive il contratto finale. Dettagli: [accessi portale](RUOLO_PORTALE_CONTRIBUENTE_ACCESSI_2026-10-27.md)
  e [scadenza dalla notifica](RUOLO_SCADENZA_NOTIFICA_2026-10-27.md).

## Distribuzione verticale avviso — verifica precedente 2026-10-27

- Riquadro termine: `Pagamento entro 60 giorni dalla data di notifica`, senza
  importo duplicato; totale e spese restano nel riepilogo originario.
- Sotto `PER CONSULTARE LA PROPRIA POSIZIONE`, in entrambe le modalita,
  compaiono prima giorni/orari e telefono degli uffici, poi il testo sul sito
  del Consorzio (rettifica finale del ciclo). Nella modalita a 60 giorni lo spazio
  libero viene ripartito tra i blocchi, con distacco minimo `1mm`.
- Test PDF con una, due e cinque annualita verificano ordine, assenza di
  sovrapposizioni e scarto fra i distacchi inferiore a `12pt`. Anteprima 2021
  aggiornata e ispezionata; QR e codici TD896 decodificati. Pagine 2-4
  identiche pixel per pixel rispetto all'anteprima precedente.
- Verifica finale: `209` casi della suite PASS e due contratti aggiornati al
  nuovo testo rieseguiti PASS; coverage cumulativa **100%** sui 13 runtime
  (`1453` statement, `388` branch). Nessuna failure residua. Ruff e
  `make lint-backend` PASS.
- Ratchet autorevole PASS; renderer LOC `1785` invariati, helper `87 -> 88`,
  nessuna nuova violation. Stato locale, nessun nuovo rilascio sul server.

## Termine avviso entro 60 giorni dalla notifica — 2026-10-27

Stato iniziale storico: conservazione data, UI e dicitura bollettini sono
superati dal ciclo del 2026-10-28 descritto in apertura.

- `Regole ruolo` salva `payment_deadline_mode`: data fissa retrocompatibile
  oppure `notification_60_days`. La seconda azzera la data salvata; la scelta
  dell'anno piu recente alimenta lo snapshot e il termine relativo in prima
  pagina, DOCX e bollettini v1/v2. Nessuna data derivata dalla stampa.
- Prima del portale: termine di pagamento, rinvio dei sabati/festivi e avvertenza sugli
  interessi. Sopra WhatsApp: intimazione adattata al Consorzio con icona blu.
  Blocchi e CSS compatti sono limitati alla modalita a 60 giorni. Il motore
  degli interessi e le decorrenze amministrative restano invariati.
- Backend **211 PASS, zero skip**, **100%** statement/branch sui 13 runtime
  misurati (`1454` statement, `388` branch). Frontend **71 PASS**, **100%**
  statement/branch/funzioni/righe sui tre runtime interessati. Typecheck,
  Ruff/format e lint backend PASS; lint frontend PASS con avvisi in altri file.
- Anteprima 2021 con dati dimostrativi dichiarati su tutte le quattro pagine;
  prima pagina e comunicazioni ispezionate. QR WhatsApp, Code 128 e Data Matrix
  decodificati dal PDF finale. Test di impaginazione con una, due e cinque
  annualita, nomi lunghi, residui e una coppia per utenza e fallback per snapshot ambigui PASS.
- Ratchet contro il merge-base `9ff86d83`: zero finding. Renderer LOC
  `1775 -> 1785`, sotto `1788` del merge-base; cognitive/cyclomatic aggregati
  `429/434` invariati. Helper backend e componente scadenza sotto soglia.
  Sincronizzazione baseline circoscritta al perimetro, senza assorbire i
  record estranei o certificare la baseline globale.
- Graphify codice Ruolo/backend/frontend e docs Ruolo/piattaforma aggiornati;
  chunk semantici completati senza errori. JSON/report dei corpus backend e
  frontend correnti, nuova visualizzazione HTML omessa per il limite di nodi.
- Migration `20261027_1300` e applicazione **non rilasciate**. Nessuna modifica
  al server degli uffici in questo ciclo; resta alla revisione `20261027_1100`.
  Dettagli e limiti: [scadenza dalla notifica](RUOLO_SCADENZA_NOTIFICA_2026-10-27.md).

## Grafica avviso e accessi personali al portale — 2026-10-27

- Prima pagina GAIA: loghi CBO Pantone/ANBI, frase sulla diversa dilazione nel
  blocco importo/scadenza, `effettuato anche mediante`, intestatario
  `Consorzio di Bonifica dell'Oristanese - Riscossione quote associative`,
  spese di notifica senza codice `SN01`. Comunicazioni: testo integrale sui
  piani già sottoscritti dopo le dilazioni e prima della scadenza, anche nel fallback.
- Prima del testo informativo sul sito compare `PER CONSULTARE LA PROPRIA POSIZIONE`,
  percorso sito/Cartella contribuenza e una coppia Codice ditta/PIN per utenza
  del destinatario. Senza dati o con utenze ambigue invita a contattare gli uffici. Eliminati il QR
  portale e «Apri il canale WhatsApp»; restano QR WhatsApp `18mm`, descrizione
  del canale e privacy con margine `1.5mm`.
- Importazione Excel in `ruolo_taxpayer_portal_access`: PIN cifrati Fernet,
  matching esatto per codice fiscale, zeri conservati, validazione prima della
  scrittura, conflitti bloccanti, upsert transazionale/idempotente. Snapshot
  con PIN ancora cifrati, acquisiti dopo la riassegnazione del pagatore.
  Runbook e stato: [accessi portale](RUOLO_PORTALE_CONTRIBUENTE_ACCESSI_2026-10-27.md).
- DB degli uffici `serverCed`: 12.353 accessi per 12.347 codici fiscali,
  sei con due coppie; 12.339 codici fiscali hanno già avvisi, otto conservati
  per avvisi futuri. Confronto completo con decifratura: zero differenze.
  Ripetizione: 12.353 invariati, zero scritture; 176.114 avvisi invariati.
  Applicate le due migration additive fino a `20261027_1100`, con backup
  preventivo di schema e metadati versione/revisione. I due trigger sono ALWAYS.
- Verifica finale: **202 test PASS, zero skip**, 100% statement e branch su
  nove runtime (`1181` statement, `350` branch). Include API, importazione,
  cifratura, snapshot e pagatore diverso, migration/trigger PostgreSQL reali,
  template, testi amministrativi e bollettini v1/v2. Nessuna esclusione aggiunta.
- Stampa Chromium 2021, due e cinque annualità, una coppia per utenza e fallback per snapshot ambigui:
  prima pagina completa, QR decodificato dal PDF a 144 dpi, privacy ravvicinata,
  comunicazioni sulla seconda pagina e bollettino dopo il partitario.
  Anteprima 2021 aggiornata con dati dimostrativi dichiarati su ogni pagina,
  delibere `89/2022` e `106/2022`; prima pagina e comunicazioni ispezionate.
- Ruff, formatter dei file nuovi e `make lint-backend` PASS. Ratchet autorevole
  contro HEAD/merge-base `9ff86d83`: zero finding. Renderer LOC `1771 -> 1775`
  rispetto alla precedente grafica, ancora sotto `1788` del merge-base;
  cognitive `429` e cyclomatic `434` invariati. Branding LOC `57 -> 80`,
  cognitive `0 -> 2`, cyclomatic `3 -> 6`, sotto soglia. Nuovo importatore:
  LOC `98`, cognitive max `18`, cyclomatic max `13`, nessuna nuova violation
  error-level; warning dichiarati, nessun refactoring estraneo.
- Baseline sincronizzata soltanto sui nove runtime dopo il ratchet; proiezione
  del perimetro verificata con scansione fresca. Preservati gli altri 20.729
  record callable e le altre modifiche concorrenti. Nessuna certificazione
  della baseline globale su un working tree con altri sviluppi in corso.
- Limiti: dati importati sul server; nuova grafica e aggancio alla generazione
  pronti nel checkout, senza sostituire il backend attivo con modifiche
  concorrenti. Rilascio applicativo ancora necessario. Nessun test di stampa
  fisica o login con credenziali reali. La pagina informativa WhatsApp restituisce
  403: la descrizione è limitata alle comunicazioni del Consorzio.

## Bollettino versione 2 selezionabile nelle regole — 2026-10-26

- Implementazione nel repository, rilascio e migrazione sul database
  dell'istanza non eseguiti. La migration `20261026_0900` aggiunge
  `bollettino_version` con default `v1`; API ammette soltanto `v1`/`v2`.
  Il selettore si trova in `Gestisci regole calcolo`, accanto a causale ed
  esercizio. Scelta persistente anche dopo riapertura e negli avvisi su piu
  anni: prevale la regola dell'anno piu recente. Il flag di esclusione del
  bollettino mantiene la precedenza sulla versione.
- Nuovo renderer `services/bollettino_v2.py`, base grafica sanitizzata
  `assets/bollettino-v2-base.svg` con provenienza in `bollettino-v2-base.md`:
  riproduce il riferimento Poste fornito dall'utente. Testi, loghi, conto,
  IBAN e autorizzazione originali fissi; dati del versante, importi, scadenza
  e codici rigenerati dall'avviso. Il PDF con i dati del contribuente di
  esempio non e versionato. `notice_html_pdf.py` isola la conversione
  Chromium e ripristina soltanto per v2 i box esatti `595 x 841 pt`, senza
  ridimensionare la grafica. V1 mantiene l'HTML identico byte per byte a
  `HEAD`, anche per snapshot senza campo versione; invariati prima pagina,
  partitario e contratti TD 896.
- Test finali: 139 test backend PASS nella suite API/notice-print/v2 e
  integrazione; statement e branch `100%` sui sei runtime Python modificati
  (1130 statement, 306 branch), nessun test saltato. Migrazione misurata
  separatamente: 1 test PASS, `100%` dei 10 statement, nessun branch.
  Le integrazioni verificano regola API -> payload di generazione -> snapshot
  batch, conservazione del documento dopo cambio regola, stampa reale
  Chromium v1/v2, pagine precedenti uguali, nominativo completo con caratteri
  speciali, box esatti e decodifica coerente Code 128/Data Matrix.
  Test del renderer coprono anche dati mancanti, font ridotto e rifiuto di
  nomi oltre lo spazio disponibile, attraverso il comportamento di stampa.
  Frontend: 66 test PASS
  (`ruolo-tributi-page.test.tsx`, `ruolo-bollettino-version.test.tsx`),
  statement/branch/funzioni/linee `100%` sui tre runtime TSX/TS modificati.
  `make lint-backend QUALITY_PYTHON=backend/.venv/bin/python BASE_REF=main`,
  ESLint mirato e `npm run typecheck` PASS. Migration upgrade/downgrade e
  default sulle regole esistenti verificati su SQLite; `alembic heads`
  restituisce `20261026_0900`.
  Build frontend di produzione PASS nel checkout isolato della feature;
  restano warning ESLint su file invariati, nessun warning sui file runtime
  della feature. I 270 test degli strumenti code quality sono PASS.
  Ulteriori 41 test di regressione PASS su testi legali, sovrapposizioni dei
  gestori annualita e policy dei non notificati: 180 test backend complessivi.
- Ratchet ordinario contro il merge-base `main`: nessuna nuova violation.
  Servizio legacy LOC `1814 -> 1788`, somma cognitive `430 -> 429`, somma
  cyclomatic `436 -> 434`; il convertitore estratto conserva comportamento
  v1 e aggiunge la calibrazione v2. Nuovi moduli: massimi cognitive `6` e
  `2`, cyclomatic `7` e `3`, nessuna violation. Nessuna soglia, esclusione
  o gate modificato; preservate le modifiche ANPR e la baseline gia presenti
  nel working tree.
  Baseline della feature sincronizzata soltanto sui 10 file runtime (incluso
  il tipo TS). Il controllo finale in checkout isolato ha confermato che la
  riparazione gia presente localmente riproduce il codice a HEAD, salvo i
  record ANPR: recupero del codice gia committato separato dalla feature,
  senza includere le modifiche ANPR nel commit.
  `make complexity-baseline-verify QUALITY_PYTHON=.venv/bin/python` PASS,
  baseline riproducibile. Per la sincronizzazione usare Python `3.14.4`
  dell'ambiente `.venv`, come la baseline locale; Python `3.12` produce
  fingerprint AST diversi anche sui sorgenti invariati.
- Generata e ispezionata un'anteprima con dati sintetici, anche dentro
  l'avviso completo: box v2 esatti e font incorporati OCR-B/Courier New.
  Lettura con zxing-cpp a 216 dpi: Code 128 e Data Matrix restituiscono lo
  stesso payload TD 896 di 50 cifre. Aggiornati i grafi con i target Make
  Ruolo, backend, frontend e documentazione di dominio. Il manuale distingue
  la geometria v2 dal verificatore geometrico esistente, dedicato a v1.
  Aggiornato anche il grafo documentazione piattaforma: entrambi i target
  semantici riportano `chunk 1/1 done`, senza chunk falliti.
- Per rieseguire la stampa reale servono Chromium, PyMuPDF, Pillow e zxing-cpp;
  `PLAYWRIGHT_CHROMIUM_EXECUTABLE` indica il binario. Il test segnala uno skip
  se queste dipendenze non sono disponibili (la CI corrente non installa
  Chromium). La misura locale finale le include tutte. La migrazione e stata
  verificata su SQLite, non applicata al PostgreSQL dell'istanza; stampa
  fisica e rilascio restano attivita operative successive.

## Regole ruolo: bollettino e data di pagamento; 2021 condiviso con STEP — 2026-10-23

- `Regola ruolo` ha due nuove scelte (migration `20261023_0900`):
  `print_bollettino` ("Stampa bollettino postale", default si: le regole
  esistenti restano con bollettino) e `payment_due_date` ("Pagamento avviso
  entro"), la data di `QUANTO E QUANDO PAGARE` e della scadenza sul
  bollettino, distinta dalla scadenza del pagamento bonario. Senza data resta
  il fallback di 30 giorni dalla generazione.
- Avvisi su piu annualita: il bollettino si stampa solo se tutte le regole
  degli anni coinvolti lo prevedono (un anno senza regola non lo esclude); data
  di pagamento, causale ed esercizio vengono dalla regola dell'anno piu
  recente. Senza bollettino il PDF salta la pagina TD 896 (restano bonifico e
  pagoPA).
- Stessa annualita in piu gestori (sovrapposizione gia ammessa da `48291081`):
  per il 2021 condiviso da `STEP - Agenzia recupero crediti` (2018-2021) e
  `Consorzio/GAIA` (dal 2021) la divisione e per avviso. Fuori dal registro
  2022-2023, un avviso con documenti STEP collegati (`step_ruolo_links`
  `linked`) resta a STEP e non e sollecitabile da GAIA, salvo che STEP lo
  dimostri `revocato` (stessa regola `desired_recovery` della proiezione nel
  registro); gli avvisi senza documenti STEP passano a GAIA con la regola 2021.
- Completato 2026-10-23 08:52: rilascio in produzione
  (`/opt/gaia/releases/ruolo-regole-20261023/`), overlay di
  `deps-python-20261022`/`deps-frontend-20261022` con lo stack tributi di
  `main` (`48291081` sovrapposizioni e 2021, `74d6a7d4` + `37a83db2` pagina
  legale, `b56d8eb2` impostazioni TD 896) e questa change. Candidato: 231 test
  tributi/STEP nell'immagine, migration up/down/up su copia dello schema di
  produzione, build frontend. Backup mirato (tabelle regole e gestori, schema,
  `.env`) in `/opt/gaia/backups/pre-ruolo-regole-20261023*`;
  `TD896_SAMPLE_MODE=true` (campionatura: il bollettino stampa il segnaposto
  `AUT.DB/SISB/XXXXX`, da sostituire con `TD896_PRINT_AUTHORIZATION` prima
  dell'invio ai contribuenti). Migration `20261023_0900` applicata (4/4 regole
  con bollettino), backend e frontend healthy, altri container invariati.
  Misura: 6.651 avvisi restano a STEP (2.811 del 2021). Rollback:
  `rollback.sh` nella cartella del rilascio (downgrade con l'immagine nuova
  prima di riavviare la vecchia, che esegue `alembic upgrade heads`).
- Residuo: in `Gestori annualita tributo` estendere `Consorzio/GAIA` al 2021
  (o aggiungere un gestore GAIA 2021) e creare la regola 2021 con le sue date;
  `db/base.py` e il controllo particelle di `main` restano fuori dal rilascio.

## Bollettino TD 896 pronto per campionatura Poste — 2026-10-22

- Nome del versante (`eseguito da`) stampato per intero, senza troncamento
  `...`. Posizioni e `max-height` dei riquadri invariati; se nome e indirizzo
  non entrano nella ricevuta di versamento il font del blocco nome scende per
  gradi (`payer-fit-1..3`: 7.5, 6.75, 6pt). La stima usa l'avanzamento OCR-B
  monospazio (0.723em, misurato sul PDF) con 0.3mm di margine; oltre i 6pt
  viene loggato un warning con il numero avviso, senza troncare. Durante la
  verifica e emerso che col vecchio layout l'ultima riga di un indirizzo lungo
  veniva tagliata dall'`overflow: hidden`: ora il campione Su Campu chiude a
  50.2mm su 52mm.
- Codice autorizzativo stampa in proprio non piu hardcoded: `Settings`
  `TD896_SAMPLE_MODE` (default false) e `TD896_PRINT_AUTHORIZATION`. In
  campionatura si stampa `AUT.DB/SISB/XXXXX DEL XX/XX/XXXX`; in produzione un
  codice vuoto o con `X` fa fallire il bollettino con `Codice autorizzazione
  Poste TD 896 non configurato`. Variabili documentate in `.env.example`.
  Attenzione al deploy: senza una delle due configurazioni i solleciti GAIA con
  bollettino risultano `failed`.
- Causale: rimosso il fallback `digits[6:9]` del numero avviso. Senza
  `bollettino_causale` in `Regola ruolo` (o `payment_reason_code`/`causale` nel
  payload) la riga `Causale` non viene stampata.
- Rimossa la riga statica vuota `Altre modalita:` dalle modalita di pagamento.
- Esercizio (solo verifica): `2626` sui campioni deriva dal fallback
  `td896_esercizio` su `notice_emission_year` (commit `bc6fda82`); le due
  `Regola ruolo` 2024 e 2025 nel DB locale non valorizzano
  `bollettino_esercizio`. Aggiunto test che documenta il comportamento.
- Avvisi con 3+ annualita: gia risolto da `43489c4c` (solo prima e ultima
  annualita nel numero avviso). Analisi read-only sul DB locale: una sola
  prenotazione (12 cifre), nessun batch item. Nessuna modifica a
  `build_notice_number` in attesa della scelta sulle opzioni proposte.
- Nuovo `scripts/ruolo/verify_td896_pdf.py` (dipendenze di sviluppo in
  `scripts/ruolo/requirements-verify-td896.txt`): controlli OK/KO di formato,
  modulo, divisione, codeline e mod 93, Code 128 e Data Matrix 16x48 a 600 dpi,
  importo, IBAN, font OCR B, nome non troncato, codice AUT. Documentato nel
  manuale di verifica. Esito sui 5 campioni (Rossi, Piras, Su Campu, Melis,
  Sanna): tutti OK, AUT `CAMPIONATURA`.
- Test dello script: `tests/ruolo/test_verify_td896_pdf.py` (28 test, fixture
  PDF sintetica Su Campu), `make test-verify-td896` con coverage 100%
  statement `189/189` e branch `60/60`; dipendenze di sviluppo fissate
  (`pymupdf==2.0`, `zxing-cpp==3.1.1`) e installate nel job CI `backend.yml`,
  che esegue lo stesso target.

## Comunicazioni per il Contribuente per annualita — 2026-10-22

- Completato: la pagina 2 dell'avviso GAIA non stampa piu le delibere fisse
  2022-2023 del template DOCX. `tributi_legal_text.py` ricostruisce, dagli anni
  inclusi nell'avviso, il paragrafo "Informazioni sul tributo" (una delibera di
  emissione e una di approvazione per anno, con data albo), la delibera di
  dilazione e di riscossione coattiva (approvazione dell'anno piu recente), la
  conferma dei minimi (emissione dell'anno piu recente) e l'anno di bilancio.
- Delibere configurate in `ROLE_YEAR_RESOLUTIONS` per 2021-2025, ricavate dal
  template (2023) e dagli avvisi emessi 2021, 2022, 2024, 2025. Per 2021 e 2022
  si stampa anche la nota sul rimborso tributi 2017 (CdA 42/2020), una sola
  volta anche negli avvisi pluriennali.
- Impaginazione: corpo del testo legale 7.75pt (prima 8.75pt), spazio fra
  paragrafi .8mm (prima .08mm). Uno script
  eseguito da Chromium prima del print-to-pdf sceglie l'interlinea massima
  (1.05-1.8) che riempie la pagina 2 lasciando testo e firma sulla stessa
  pagina; se non basta l'interlinea minima riduce il corpo (fino al 70%).
  Firma alzata e spostata a sinistra (bottom 12mm, right 25mm; spazio
  riservato sotto il testo 24mm) con nota centrata sotto la firma. Verificate
  con Chromium tutte le 31 combinazioni di anni 2021-2025: corpo 100% per
  2023-2025 singoli, minimo 96,5% nel caso 2021-2025.
- Dilazione: le tre righe di fasce sono sostituite da una tabella ordinata per
  importo crescente (`INSTALLMENT_TIERS`: <100 nessuna, 2, 4, 6, 12, 18 rate);
  un template senza l'elenco atteso blocca la generazione. Le fasce riportano
  1.000,00 euro sia nel limite superiore dei 6 rate sia in quello inferiore dei
  12 rate, come nella delibera: da chiarire con gli uffici.
- Fail-closed: un anno senza delibere configurate (es. 2026) o un template
  privo dei paragrafi attesi blocca la generazione invece di stampare delibere
  di altri anni. Per un nuovo ruolo aggiungere la riga in `ROLE_YEAR_RESOLUTIONS`.
- Corretto: data albo della CdA 131/2023 (ruolo 2022) e 16.10.2023, come
  nell'avviso 2022 emesso; il template DOCX riportava erroneamente 16.10.2022.
- Test: `backend/tests/ruolo/test_tributi_legal_text.py`; suite `tests/ruolo`
  verde, coverage 100% su `tributi_legal_text.py` e `tributi_reminder_service.py`.

## STEP: collegamento avvisi e stato registro automatico — 2026-10-21

- Completato: i documenti STEP (riscossione coattiva 2018-2021, sync in
  `elaborazioni`) sono collegati a `ruolo_avvisi` solo per `codice_cnc`
  univoco, convertito nel formato GAIA (`01.` + prime 14 cifre STEP,
  `gaia_codice_cnc`, correzione del 2026-10-22); anomalie
  `not_found`/`ambiguous`/`unrecognized` visibili in `/elaborazioni/step`.
- Completato: la valutazione STEP del registro (`ruolo_notice_recoveries`) e
  aggiornata automaticamente dopo ogni sync/import/relink tramite
  `assess_recovery` con audit (`affidato`, `revocato`, `chiuso`); decisioni
  dell'operatore preservate, `non_affidato_verificato` mai dedotto.
- Completato: riquadro "Riscossione coattiva STEP" nel dettaglio avviso
  `/ruolo/avvisi/{id}`.
- Completato 2026-10-22: backend e archivio STEP in produzione; tasso di
  collegamento misurato (7.070 avvisi collegati, 2.997 del 2021; 201
  `not_found`, 36 `unrecognized`). Proiezione nel registro non pubblicata:
  l'anteprima con autore `admin` interessa 0 posizioni (registro solo
  2022-2023).
- Completato 2026-10-22: frontend e worker STEP in produzione
  (`step-frontend-20261022`, `step-worker-20261022`).
- Residuo: anteprima/conferma operatore per singola pratica STEP; credenziale
  STEP e primo `sync`; pubblicazione del registro quando conterra avvisi
  collegati.
- Dettagli: `domain-docs/elaborazioni/docs/STEP_SYNC.md`,
  `STEP_IMPORT_IMPLEMENTAZIONE.md`.

## Gestori sovrapposti e recupero avvisi 2021 — 2026-10-21

- Implementazione locale completata: regola 2021 sovrapposta a STEP, priorita
  deterministica, minimo 2021 condiviso da backend e wizard. Nessuna migration,
  nuova dipendenza o modifica dei permessi. La selezione dei non notificati
  riusa `only_unnotified`; i tentativi senza consegna non provano una notifica.
- Consolidamento con test di autorizzazione delle tre mutazioni, rollback,
  persistenza tra sessioni, cancellazione e ripristino STEP, gestione esterna
  ancora esclusa. Nuovo test PostgreSQL reale in schema temporaneo PASS.
- Suite Ruolo completa con PostgreSQL: 1162 PASS, nove skip SQLite, una failure
  nell'assert della head Alembic per la nuova migration STEP concorrente.
  Coverage repository Tributi: 1822 statement e 694 branch, 100% entrambi.
- Frontend: 5269 unit test e 18 smoke PASS; pagina Tributi al 100% su statement,
  branch, funzioni e linee. Sei E2E Chromium PASS a 1440/390 px, compresi errore
  di salvataggio, retry, periodo 2021 e regressioni delle preview 2022.
- La ripetizione della suite completa da lockfile ha 5268 PASS e un timeout
  di 5000 ms in Utenze, fuori scope. Rerun isolato Utenze + Tributi: 84 PASS,
  coverage Tributi ancora 100%. Il gate completo fallito resta registrato.
- Build pulita isolata da `npm ci`: Next 15.5.27, 163/163 pagine PASS.
  L'installazione locale precedente aveva Next 15.5.25: non e stata modificata.
- Ratchet mirato contro HEAD PASS; quello autorevole contro `origin/main`
  riproduce due finding preesistenti. Baseline, soglie ed esclusioni invariati.
  Audit dipendenze di produzione: due segnalazioni high e tre moderate legacy.
  Gate complessivo non superato anche per le due failure delle suite complete;
  nessun commit o rilascio incluso.
- Evidenze, matrice funzionalita/test, integrazioni e residui nel
  [report finale](VERIFICA_FINALE_AVVISI_2021_2026-10-21.md).

## Riemissione numeri avviso oltre 15 cifre — 2026-10-21

- Segnalazione da produzione: preview dell'avviso 2022 di una societa agricola
  con piu annualita raggruppate per regola -> `Il numero avviso non puo superare
  15 cifre per il TD 896`. Causa: backend di produzione ancora su `b2fa9ee0`,
  precedente alla regola prima/ultima annualita (`43489c4c`).
- Il preview prenota il numero prima di generare il PDF: dopo il fallimento la
  prenotazione resta in `generation_failed` con il numero lungo e viene riusata
  ai tentativi successivi, quindi il solo rilascio non bastava.
- `reserve_notice_number` ora riscrive con il formato nuovo le prenotazioni oltre
  15 cifre senza documento (`reserved`, `generation_failed`), mantenendo id,
  stato e progressivo; le `generated` restano invariate.
- Test: riemissione per `reserved`/`generation_failed`, nessuna modifica per
  `generated`; suite Ruolo PASS, coverage 100% su `tributi_notice_registry.py`,
  style e complexity ratchet senza finding.
- Verifica read-only in produzione prima del rilascio: unica prenotazione oltre
  15 cifre `120262223242500103` (`generation_failed`, annualita 2022-2025, la
  societa segnalata); nessun numero lungo in stato `generated`.
- Rilasciato `f7346bf2` con overlay backend isolato
  `gaia-backend:td896-notice-20261021` (base `tributi-history-20261019` + i tre
  file `tributi_notice_registry.py`, `tributi_reminder_service.py`, `td896.py`,
  identici in produzione a `b2fa9ee0` prima del rilascio). Test nell'immagine
  candidata con PostgreSQL isolato: 134 PASS. Health ok, hash runtime
  verificati, altri container invariati; rollback in
  `/opt/gaia/releases/td896-notice-20261021/rollback.sh`.

## Bollettini TD 896 e numeri avviso multi-annualita — 2026-10-20

- Corretto il numero avviso con tre o piu annualita: prima arrivava a 16-18
  cifre, oltre il limite di 15 del codice cliente TD 896, e il bollettino non
  veniva generato. Ora dalla terza annualita il suffisso riporta solo la prima
  e l'ultima (es. `2022-2025` -> `12026222500001`, 14 cifre). Numeri con una o
  due annualita invariati; univocita garantita da anno emissione + progressivo.
- Le prenotazioni gia salvate non vengono riscritte: eventuali numeri storici
  oltre 15 cifre in `ruolo_tributi_notice_numbers` vanno verificati sul DB di
  produzione e riemessi a parte (non verificabile dall'ambiente di sviluppo).
- Allineato il layout della ricevuta di accredito alle `Caratteristiche del
  bollettino` Ed. 2020: codeline sulla griglia a decimi di pollice ancorata a
  destra, conto/importo a `34.5mm`/`116mm`, intestazione a `24.1mm` senza
  sovrapposizioni con `eseguito da`. Dettagli in
  `RUOLO_TRIBUTI_TEMPLATE_GAIA_2026-07-23.md`.
- Verifica su PDF generati: delimitatori della codeline nel 4°, 10°, 25° e 43°
  decimo, Code 128 e Data Matrix decodificati (zxing) uguali al payload di 50
  cifre, nessun testo sovrapposto. Preparati 5 campioni per la richiesta di
  autorizzazione Poste alla stampa in proprio.
- Il codice di autorizzazione stampato diventa il segnaposto
  `AUT.DB/SISB/XXXXX DEL XX/XX/2026` (prima `AUT.DB/SISB/36211 DEL 5/9/2012`,
  non valido per il nuovo layout): va sostituito con il codice che Poste
  rilascera per la stampa in proprio in PDF.
- Dopo la revisione interna dei campioni: riquadro bollo della ricevuta di
  versamento ridotto a `33.2mm` per liberare la zona di rispetto del Data Matrix
  (`2.14mm` misurati, minimo `1.875mm`); `Esercizio` automatico ora pari
  all'anno di emissione (`2626`), secondo la convenzione Capacitas degli avvisi
  accorpati, invece dell'annualita piu alta (`2525`); aggiunte sopra il
  bollettino le istruzioni di stampa PDF raccomandate da Poste. Rimosso il
  wrapper `.bollettino-landscape`, che duplicava il box di `.bollettino-sheet`.
- Confronto puntuale con gli Allegati 4 e 8 del manuale Poste: corretti logo
  beneficiario (`7.6` -> `5.5mm` dall'alto), codice cliente sull'accredito
  (`43.1` -> `42mm`), caselle IBAN (`17.1` -> `16.6mm`, target `16.5mm`) e
  mezzeria della codeline (`8.25` -> `8.5mm`). Rigenerati i 5 campioni con il
  segnaposto di autorizzazione: codeline, barcode e Data Matrix invariati e
  decodificati.
- Test: suite Ruolo PASS; coverage 100% su `tributi_notice_registry.py`,
  `tributi_reminder_service.py` e `td896.py`; style e complexity ratchet senza
  finding; grafo `ruolo-code` aggiornato.

## Anteprima PDF bozze da Elenco Tributi — 2026-10-19

- Collegato il comando rapido `Avviso sollecito` all'anteprima privata gia
  disponibile: gli elementi `draft` usano la route autenticata PDF marcato,
  non il download legacy. Supportati 2022/2023 e lotti misti protetti.
- Finestra con dicitura `BOZZA - NON VALIDA PER INVIO` e filename `bozza-...pdf`;
  nessuna conferma, export definitivo, invio o modifica allo storico.
- Errori di anteprima restano espliciti, senza fallback agli originali.
  Generazione e download legacy delle altre annualita invariati.
- Superato il limite della sola mancata apertura PDF segnalato nella sezione
  precedente: si tratta di copia marcata, non di avviso definitivo.
- Collaudo: 62 test frontend con coverage full-file dei due runtime al 100%
  (655 statement, 637 branch); 18 smoke; build, typecheck e lint mirato PASS.
  Un warning hook preesistente nella pagina rimane invariato.
- 67 test backend PASS nell'immagine operativa con PostgreSQL isolato,
  inclusi generazione-bozza-anteprima 2022/2023 senza storico verificato,
  originali privati, permessi/errori e conversione LibreOffice reale.
  Servizio preview preesistente al 100% (70 statement, 14 branch).
- Chromium: 4 scenari desktop/mobile PASS, incluso visualizzatore PDF nativo,
  filename bozza, errore senza fallback, regressione scrollbar/date.
  Primo tentativo browser corretto solo nella fixture: inizializzazione token
  limitata al frame principale, non al visualizzatore PDF di Chromium.
- Ratchet contro `7435d3f1` PASS, nessun finding; orchestrazione anteprima
  cognitive/cyclomatic 20/14 -> 11/10, nuovo loader 9/9, sotto soglia.
  Baseline sincronizzata dopo ratchet e verifica riproducibilita PASS;
  nessuna esclusione o soglia ampliata. Grafo frontend e docs aggiornati.
- Commit `59ad5357` rilasciato con immagine frontend isolata
  `gaia-frontend:tributi-preview-20261019`; sorgenti runtime verificati tramite
  hash, dipendenze installate coerenti con il lockfile. HTTP/assets e health
  backend PASS; backend e altri container invariati, nessuna migration.
- Regressione Solleciti standalone: altri 2 scenari Chromium PASS. Sul frontend
  pubblicato `gaia.lan`, ripetuti i 2 scenari bozza desktop/mobile con API
  simulate: PASS, senza generare avvisi o modificare dati operativi.

## Generazione senza storico verificato — 2026-10-19

- Su autorizzazione operativa, il gate Tributi 2022/2023 ammette il solo
  motivo `storico_non_verificato`, anche per pagamenti parziali. Il registro
  continua a segnalarlo: nessuna evidenza storica viene creata o alterata.
- Tutti gli altri blocchi restano attivi, incluse notifiche documentate,
  STEP, invii da riconciliare, anomalie e vincoli contabili/regole applicabili.
- 56 test eligibility/generation PASS su SQLite e PostgreSQL isolato usando
  l'immagine candidata. Runtime modificato full-file 75 statement e 38 branch
  al 100%. Regressione Tributi API/checkbox non notificati: 130 test PASS.
- Lint e complexity ratchet contro `82530422` PASS; `generation_allowed`
  invariato a cognitive 2, cyclomatic 3, LOC 6. Baseline sincronizzata dopo
  il ratchet e verifica riproducibilita PASS; nessuna soglia modificata.
- Graphify codice aggiornato senza cambi di topologia; grafo documentazione
  aggiornato con estrazione semantica completata, senza chunk falliti.
- Limite preesistente confermato anche sul runtime operativo: 2022/2023
  producono bozze private; conferma/export e PDF scaricabile non sono abilitati
  da questo intervento. La selezionabilita non equivale a disponibilita PDF.
- Commit runtime `b2fa9ee0` rilasciato con overlay backend isolato; health e
  hash runtime verificati, altri container invariati. Verifica read-only sui
  primi 25 tributi 2022: 18 selezionabili (inclusa la riga segnalata), 7 ancora
  bloccati dagli altri controlli. Migration invariata a `20261019_1400`.

## Formato italiano date regole — 2026-10-19

- Campi comuni e per anno in `gg/mm/aaaa` con calendario, indipendenti dalla
  lingua del browser. Riepiloghi con anno a quattro cifre. Date impossibili,
  parziali e anni a due cifre impediscono il salvataggio; API sempre ISO.
- 69 test unitari/integrati e 18 smoke PASS. Tre file runtime interessati al
  100% statement (681/681), branch (651/651), funzioni e linee, senza esclusioni
  aggiunte. Test coprono anni bisestili, date invalide, cancellazione, reset,
  calendario, creazione e modifica con payload ISO comune e annuale.
- Due test Chromium desktop/mobile (1440/390 px), locale `en-US`, PASS:
  formato visualizzato, validazione, calendario e POST con date ISO.
  Typecheck, lint e build produzione PASS, salvo warning hook preesistenti.
- Ratchet contro `b1b15013` senza finding; baseline sincronizzata e verificata.
  `CalculationPoliciesPanel`: cognitiva/ciclomatica 23/24 invariate,
  LOC 257 -> 251. Graphify frontend e documentazione Ruolo aggiornati.
- Rilasciato `dd5a2429`: frontend `tributi-italian-dates-20261019` healthy su
  `gaia.lan`. Smoke HTTP/asset e due prove browser ripetute sul sito pubblicato
  con API simulate PASS; nessuna scrittura dei dati live. Backend e altri
  container invariati. Rollback in `/opt/gaia/releases/tributi-italian-dates-20261019`.

## Scorrimento anteprima regole — 2026-10-19

- Rimosso il limite di tre schede: tutte le regole attive sono ordinate per
  anno, consultabili orizzontalmente anche da tastiera. Gestione fuori dall'area
  scorrevole; stesse schede per amministratori e utenti in sola lettura.
- 57 test del componente PASS, coverage full-file `page.tsx` 100% statement,
  branch, funzioni e linee; 18 smoke PASS. Due test browser Chromium a 1440 e
  390 px verificano overflow interno, ultima scheda raggiungibile, freccia
  destra e comando gestione stabile/funzionante. Nessuna scrittura API live.
- Typecheck, lint e build produzione PASS (warning hook preesistenti).
  Ratchet contro `f0e066e0` senza finding, baseline sincronizzata/verificata.
  `CalculationPoliciesPanel`: cognitiva 24 -> 23, ciclomatica 25 -> 24,
  LOC 258 -> 257. Nessun cambio a backend, regole o dati.
- Rilasciato `cb4814d9` su `gaia.lan`, immagine frontend
  `gaia-frontend:tributi-rule-scroll-20261019`. Smoke HTTP/asset PASS;
  entrambi i test browser ripetuti sul frontend pubblicato con API simulate
  PASS. Backend e altri container invariati; rollback frontend predisposto in
  `/opt/gaia/releases/tributi-rule-scroll-20261019`.

## Regole annuali e non notificati — 2026-10-19

- Implementazione di blocchi visuali con regole annuali indipendenti:
  maggiorazione/interessi/entrambi, tassi, date e checkbox non notificati.
- Scope basato su consegna PEC o ricezione raccomandata documentata; preservati
  regole esistenti, formule e decorrenze storiche. Nessun dato operativo creato.
- Rilasciato `c58250bb` su `gaia.lan`: backend/frontend healthy, ramo Alembic
  isolato `20261019_1400`, hotfix live e due regole esistenti preservati.
  Backup e rollback compatibile verificati; altri servizi permanenti invariati.
- 132 test backend e 5249 frontend piu 18 smoke PASS; coverage runtime toccato
  100%. Immagine candidata: 130 test API PASS e migration PostgreSQL verificata.
- Contratti, test e limiti: [TRIBUTI_RULE_BLOCKS_2026-10-19.md](TRIBUTI_RULE_BLOCKS_2026-10-19.md).

## Pulsanti annuali Consorzio/GAIA — 2026-10-19

- Nel periodo Consorzio/GAIA, `Elenco tributi` espone 2022, 2023, 2024,
  2025 e `Tutti gli anni`, oltre al campo anno. Selezione accessibile e
  sincronizzata con URL, lista e KPI; filtro saldo preservato.
- Negli altri periodi i pulsanti non compaiono. Restano disponibili il campo
  manuale e il reset anno al cambio gestore.
- Rilasciato `320f1b86` su `gaia.lan`: frontend healthy, smoke pagina/asset/API
  PASS, nessun altro container ricreato. 5246 test frontend e 18 smoke PASS;
  coverage del file runtime modificato 100%, ratchet senza finding.
- Evidenze del ciclo e rilascio in
  [TRIBUTI_FILTERS_VALIDATION_2026-10-19.md](TRIBUTI_FILTERS_VALIDATION_2026-10-19.md).

## Filtri tributi per saldo e annualita — 2026-10-19

- `Elenco tributi` raggruppa i tre periodi gestori, anno tributario e filtro
  `Solo non pagati (anche parziali)`. Sono inclusi anche i saldi da verificare.
- Cambiare periodo azzera l'anno; attivare il filtro saldo azzera lo stato
  pagamento puntuale. Lista, paginazione e KPI usano gli stessi filtri URL.
- Test UI per tutti i periodi e API con stati misti; recupero separato della
  baseline e riallineamento delle dipendenze frontend per `npm ci` riproducibile.
- Evidenze, limiti e stato rilascio:
  [TRIBUTI_FILTERS_VALIDATION_2026-10-19.md](TRIBUTI_FILTERS_VALIDATION_2026-10-19.md).
- Deploy frontend `837ae49c` completato su `gaia.lan`: healthy e smoke
  pagina/asset/API verdi, altri container invariati. Suite finale 5241 test
  frontend, 18 smoke, 9 API e 270 tooling; coverage runtime modificato 100%.

## Controllo storico particelle — 2026-10-06

- Confronto geometrico persistente per singola pratica su layer poligonali
  PostGIS autorizzati: unione distretti senza FD, selezione comune esplicita,
  insediamenti preliminari; superficie/percentuale/hash salvati come evidenza.
  Nessuna modifica automatica al ruolo o alle geometrie operative. Attivazione
  subordinata alla pubblicazione del layer NAS; integrazione WFS RAS separata.
- 68 test backend e 28 frontend, coverage runtime 100%; SQL esercitato su
  PostGIS reale con sole tabelle temporanee e rollback. Specifica e limiti in
  [CONTROLLO_GEOMETRICO.md](CONTROLLO_GEOMETRICO.md).

- Estensione successiva concordata: periodo 2011–2025, terminologia particella
  catastale, proposte solo con presenza storica documentata. Le particelle
  storiche interferenti con centri abitati restano in istruttoria; nessuna
  esclusione o reinserimento automatico. Conferme in zone FD/FD_1–FD_7 bloccate.
- 52 test backend e 27 frontend, coverage runtime 100%; ratchet completo
  contro HEAD senza finding, 27 warning invariati e zero error-level.
  Dati 2011–2019 verificati in sola lettura, senza attestazioni automatiche,
  reimport o ricalcolo operativo. Fonti territoriali ancora da integrare.
- Estesa `/ruolo/particelle` con storico 2020–2025, corrente 2025 concordato,
  avvisi CF anomali, pratiche persistenti, visure esistenti e coda proposte.
- Conservazione dati originali, attestazioni di completezza, evidenze,
  matching manuale, audit, idempotenza e controllo versioni/concorrenza.
- Nessuna modifica automatica di anagrafiche o ruoli. Perimetro territoriale,
  regole tributarie e destinazione di formazione ruolo restano da definire;
  parser soggetto limitato a un riferimento. Non e una ricerca esaustiva.
- 43 test backend e 27 frontend verdi, coverage 100% statement/branch nel
  perimetro runtime del ciclo; Ruff, ESLint e typecheck verdi. Migration
  verificata tramite roundtrip/schema e SQL Alembic, non applicata in produzione.
- Specifica e limiti: [CONTROLLO_PARTICELLE.md](CONTROLLO_PARTICELLE.md).

> Stato documento: archivio storico di delivery.
> Traccia milestone e test anche del vecchio import file-based, oggi rimosso dal runtime.
> Per lo stato corrente del dominio fare riferimento al codice attivo e al PRD Ruolo aggiornato.

## Stato generale

- Modulo: Ruolo
- Stato complessivo: **documento archiviato; implementazione storica completata M1–M5**
- Owner: TBD
- Ultimo aggiornamento: 2026-09-24

---

## Aggiornamento operativo 2026-09-24 - contatori globali raccomandate

- La console `/ruolo/raccomandate` mostra `Associati totali` e `Anomalie totali` sull'intero archivio, indipendentemente da pagina, ricerca e filtri. Il riquadro `Risultati` continua invece a indicare il totale filtrato della lista.
- `GET /ruolo/tributi/raccomandate/summary` restituisce `total`, `associated` e `anomalies`. E associata solo una raccomandata con `avviso_id` valorizzato, `match_status=matched` e `anomaly_key` nullo; ogni altro record conta come anomalia. L'endpoint resta protetto dai permessi di consultazione del modulo Ruolo.
- I contatori vengono ricaricati dopo una modifica manuale dell'associazione. La query e di sola lettura e non modifica il matching degli avvisi.
- Verifica sul database CED prima del deploy: `total=2307`, `associated=113`, `anomalies=2194`.

---

## Aggiornamento operativo 2026-09-22 - raccomandate nel dettaglio soggetto

- `GET /ruolo/soggetti/{subject_id}/avvisi` espone ora per ogni ruolo gli stessi riepiloghi di
  consegna digitale/PEC e raccomandata gia disponibili nell'elenco avvisi Ruolo.
- Nel dettaglio `/utenze/{id}`, la tab `Avvisi di pagamento` presenta la raccomandata come canale
  di notifica del ruolo associato, non come record anagrafico indipendente: la catena canonica
  resta `raccomandata -> ruolo_avvisi.id -> ruolo_avvisi.subject_id`.
- Ogni card ruolo mostra data, stato e tracking della raccomandata associata, oltre al riepilogo
  PEC quando presente; il dettaglio ruolo resta il punto di accesso allo storico completo.
- Quality gate mirato: backend route `129/129` statement e `14/14` branch; frontend runtime
  eseguibile `389/389` statement, `402/402` branch, `85/85` funzioni e `305/305` linee.

---

## Aggiornamento operativo 2026-09-22 - matching manuale raccomandate

- La console `/ruolo/raccomandate` consente agli utenti con section key
  `ruolo.tributi.manage_status` di aprire dalla colonna `Matching` una modal per cercare un
  avviso, riconoscere i candidati automatici, associare/cambiare l'avviso oppure rimuovere
  esplicitamente l'associazione. Gli utenti con il solo permesso `ruolo.tributi.view` mantengono
  la consultazione read-only.
- Il comando usa `PATCH /ruolo/tributi/raccomandate/{mail_id}/association` con payload
  `{ "avviso_id": UUID | null }`; raccomandata o avviso inesistenti restituiscono `404` e il
  backend registra operatore e timestamp dell'azione.
- L'override e conservato in `raw_payload_json.manual_association` senza migrazione DB. Un
  `avviso_id` nullo rappresenta una disassociazione manuale persistente, non la riattivazione del
  matching automatico.
- L'associazione manuale prevale sui successivi re-import Poste Online. Se l'avviso collegato non
  e piu disponibile il record resta fail-closed come non associato; i candidati automatici restano
  nel payload per supportare la revisione operativa.
- Quality gate: suite backend Ruolo interessata `112 passed`, statement e branch coverage
  `100%` sui runtime backend modificati; suite frontend correlata `19 passed`, statement
  `147/147`, branch `132/132`, funzioni `56/56` e linee `131/131`. TypeScript, ESLint, Ruff,
  formatter e `git diff --check` passano. Il complexity ratchet non riporta finding nel perimetro
  Ruolo/frontend della change.
- Grafi codice Ruolo e frontend aggiornati; il grafo documentale Ruolo viene riallineato con il
  presente aggiornamento.

---

## Aggiornamento operativo 2026-08-26

- Corretto un bug di escaping HTML nell'avviso/sollecito e nel bollettino TD 896: indirizzi e nominativi provenienti dall'import esterno `incass` potevano arrivare con entità HTML non decodificate (es. `S&#39;APPADROXIU` invece di `S'APPADROXIU`), che venivano poi stampate letteralmente nel PDF perché il renderer si limita a fare escaping in uscita, mai unescape a monte.
- `_value()` in `tributi_reminder_service.py` applica ora `html.unescape()` prima di ogni `html.escape()` a valle: normalizza `Denominazione`, `INDIRIZZO`, `INDIRIZZO_SPEDIZIONE`, `CodFiscale` e gli altri campi testuali condivisi da avviso PDF/DOCX e bollettino, senza impatto sui valori privi di entità.
- Aggiunta regressione dedicata `test_tributi_reminder_field_values_decode_html_entities_from_source_address`, che copre sia l'indirizzo (`S&#39;APPADROXIU`) sia nome/cognome (`D&#39;Aloia Rossi &amp; Figli`), verificata contro il fix (fallisce senza, passa con).
- Validata la change con `pytest tests/ruolo/test_tributi_api.py --cov=app.modules.ruolo.services.tributi_reminder_service --cov-report=term-missing --cov-fail-under=100 -q` nel venv del progetto: `819/819` statement coperti (`100%`), suite `tests/ruolo/` interamente verde.
- Individuata la causa radice: `app/services/elaborazioni_capacitas_incass.py` scriveva `denominazione`/`indirizzo`/`citta` provenienti dall'API `incass` (`CapacitasInCassNoticeRow`) su `AnagraficaPaymentNotice` senza mai decodificare le entità HTML; da lì il testo sporco si propagava anche a schermate `/ruolo/tributi`, `/ruolo/avvisi/[id]` ed export CSV, non solo al PDF.
- Aggiunto `_decode_incass_text()` in `elaborazioni_capacitas_incass.py`, applicato a `display_name`/`denominazione`, `citta` e ai componenti di `_join_address()` (indirizzo, civico, subcivico): le nuove sincronizzazioni `incass` arrivano ora già pulite in `AnagraficaPaymentNotice`, senza bisogno di normalizzare in ogni consumatore a valle. Il fix di difesa in `tributi_reminder_service.py` resta invariato. Scope limitato all'ingestione su richiesta esplicita: nessun backfill dei record già presenti in DB, nessuna modifica a frontend/export CSV.
- Aggiunta regressione `_join_address` con entità HTML e nuovo test `test_upsert_payment_notice_decodes_html_entities_from_incass_row` in `tests/test_elaborazioni_capacitas.py`, verificato contro il fix (fallisce senza, passa con).
- Validata la change con `pytest tests/test_elaborazioni_capacitas.py --cov=app.services.elaborazioni_capacitas_incass --cov-report=term-missing -q` nel venv del progetto: `624/624` statement coperti (`100%`).
- Grafo codice Ruolo aggiornato con `make graphify-ruolo-code`.

---

## Aggiornamento operativo 2026-08-24

- Estese le `Regole ruolo` con causale a tre cifre ed esercizio a quattro cifre opzionali per il bollettino TD 896.
- I valori seguono la policy dell'annualita piu recente del sollecito; in loro assenza restano invariati i fallback automatici da numero avviso e annualita.
- Allineati contratti API, persistenza, form `/ruolo/tributi`, payload batch e renderer GAIA; la migration `20260824_0900` mantiene un'unica catena Alembic.
- Isolati CRUD e schemi delle policy in `tributi_policy_repository.py` e `tributi_policy_schemas.py`; il frontend separa stato/normalizzazione del form e campi bollettino dalla pagina legacy, mantenendo invariati gli import pubblici.
- Quality ratchet contro la base del worktree senza finding; coverage completo dei file runtime modificati: backend `4701/4701` statement e frontend `712/712` statement, `702/702` branch, `234/234` funzioni e `644/644` linee.
- Adeguato il TD 896 al modello CH8/Bis Poste: ultima pagina A4 landscape nativa, modulo `297 x 102 mm` senza scaling, OCR-B incorporato, codici ottici a dimensione nominale, aree bollo `55 x 34 mm`, zona cliente accredito riservata al solo versante e colori nero/grigio 20%.
- Verifica renderer TD 896: `1034/1034` statement e `336/336` branch coperti (`100%`); PDF reale a 300 dpi con `OCRB-Regular` incorporato, Code 128 circa `92,79 x 11,60 mm` e Data Matrix utile circa `45,04 x 15,07 mm`, entrambi decodificati sul medesimo payload di 50 cifre. Complexity ratchet senza finding e grafi Ruolo code/docs aggiornati.

---

## Aggiornamento operativo 2026-08-20

- Corretto il bollettino TD 896 degli avvisi GAIA: codeline, Code 128-C e Data Matrix ora derivano da un unico payload validato con importo dell'avviso, conto postale e tipo documento `896`.
- Ripristinato il codice cliente postale a 18 cifre, distinto dal numero avviso visibile e dotato di controcodice modulo 93.
- Sostituiti l'asset Data Matrix statico e il fallback grafico non decodificabile con un encoder ECC 200 rettangolare `16 x 48`, verificato mediante decoder ZXing indipendente.
- Aggiunto `MANUALE_VERIFICA_BOLLETTINI_TD896.md` con controlli visivi e scansione dei codici ottici.
- Test dei file runtime modificati: coverage `100%`. Servizio prima/dopo: LOC `1851 -> 1811`, CC max `22 -> 16`, cognitiva max `38 -> 17`; il nuovo modulo TD 896 ha CC max `9`, cognitiva max `12` e nessuna violazione error-level.

---

## Milestone

| Milestone | Stato | Note |
|-----------|-------|------|
| M0 Analisi e design | ✅ done | PRD v1, Execution Plan v1, Prompt Codex prodotti |
| M1 Fondazione backend | ✅ done | Migration, modelli, enums, parser (23 test), import service |
| M2 API e query layer | ✅ done | Repository, schemas, route import + query, router.py |
| M3 Bootstrap e integrazione | ✅ done | Section keys, flag module_ruolo, router registrato in api/router.py |
| M4 Frontend | ✅ done | Dashboard, avvisi, dettaglio, stats, import, widget soggetto |
| M5 Hardening | ✅ completo | Permessi require_module attivi; test API, parser/import realistici e catasto parcels coperti |

---

## Aggiornamenti recenti

### 2026-08-10
- Migliorata la resa mobile della lista `/ruolo/tributi`: i pulsanti `Dettaglio`, `Dettaglio soggetto` e `Avviso sollecito` restano allineati sulla stessa riga nella card.
- Ridotto lo zoom della preview PDF degli avvisi sollecito nelle viewport mobili sotto `640px`, mantenendo invariata la resa desktop.
- Validata la change con coverage `100%` su `frontend/src/app/ruolo/tributi/page.tsx` tramite `frontend/tests/unit/ruolo-tributi-page.test.tsx`.
- Formalizzata la policy `audit_only` per i ruoli speciali Capacitas/InCASS: `2525`, `2626`, `7700`, `7890` e `99xx` restano fuori dal calcolo ordinario di saldo, morosita e annualita.
- Gli special notices espongono stato operativo normalizzato (`cancelled`, `partially_cancelled`, `paid`, `partial`, `open`, `to_review`), flag `is_cancelled` e `importo_annullato`.
- Aggiunti filtri API su `/ruolo/tributi/special-notices` per `operational_status` e `is_cancelled`, utili per isolare accorpati annullati o ancora attivi.
- Documentazione operativa aggiunta in `domain-docs/ruolo/docs/RUOLO_TRIBUTI_RUOLI_SPECIALI_CAPACITAS_2026-08-10.md`.
- Validata la change con coverage `100%` su `tributi_repositories.py`, `tributi_routes.py`, `schemas.py` e `capacitas_role_codes.py`.

### 2026-08-07
- Corretto il riferimento visibile del bollettino TD 896 nei solleciti tributi: ora coincide con il `notice_number` GAIA, senza prefissi, padding o controcodici aggiuntivi.
- Il padding a lunghezza pari resta limitato al payload barcode Code 128-C quando necessario e non viene mostrato all'utente come numero di riferimento.
- Documentata la derivazione del campo `Esercizio`: per avvisi multi-annualita usa l'anno piu alto del payload e duplica il suffisso a due cifre, per esempio `2025 -> 2525`.
- Validata la change con coverage `100%` su `backend/app/modules/ruolo/services/tributi_reminder_service.py`.

### 2026-08-06
- Estesa la logica interessi delle `Regole ruolo`: il tasso effettivo usato dal saldo e `Euribor medio 6 mesi + tasso da delibera`.
- Aggiunto recupero automatico Euribor 6M dal Data Portal BCE per anno policy, con salvataggio di valore, periodo, URL sorgente e timestamp di recupero.
- La modal `Regole ruolo` espone i campi separati `% Euribor medio 6 mesi` e `% tasso da delibera`, il pulsante `Recupera da BCE` e il link di verifica del dato BCE.
- Aggiunta migration `20260730_1100_ruolo_tributi_euribor_interest_rate` e servizio backend `app.modules.ruolo.services.euribor`.
- Validata la change con test mirati backend/frontend e coverage `100%` sui file runtime modificati.

### 2026-08-05
- Implementata la logica operativa `Regole ruolo` per solleciti multi-annualita: un range come `2024-2025` viene salvato come policy annuali distinte per supportare scadenza bonaria e fallback interessi diversi per ruolo.
- Le policy annuali generate dallo stesso nome base vengono raggruppate in preview: cliccando `Avviso sollecito` sul 2024 o sul 2025, il backend espande il gruppo e produce un solo avviso con entrambe le annualita.
- La preview rapida riusa il `notice_number` quando CF/P.IVA, annualita e avvisi inclusi coincidono, evitando numeri diversi per lo stesso avviso logico.
- Gli avvisi con importi effettivi da inCASS rateizzazione/residuo mantengono `calculation_policy_id` e `calculation_policy_name`, quindi restano sollecitabili quando coperti da Regola ruolo attiva.
- Documentazione operativa aggiunta in `domain-docs/ruolo/docs/RUOLO_TRIBUTI_REGOLE_RUOLO_SOLLECITI_2026-08-05.md`.
- Validata la change con coverage mirata al `100%` su `backend/app/modules/ruolo/tributi_repositories.py`, `backend/app/modules/ruolo/services/tributi_reminder_service.py` e `frontend/src/app/ruolo/tributi/page.tsx`.

### 2026-08-04
- Corretto il collo di bottiglia backend della lista `/ruolo/tributi` quando `Solo scoperti` (`open_only=true`) o i filtri `payment_status` richiedevano il calcolo dello stato effettivo: il repository non materializza piu il dettaglio completo su tutto il dataset filtrato prima della paginazione.
- `GET /ruolo/tributi/avvisi` pre-carica ora in batch notice inCASS, date notifica PEC/raccomandata e policy per annualita, applica i filtri effettivi sul perimetro bulk e costruisce `_row_to_tributi_item` solo per le righe della pagina corrente.
- `GET /ruolo/tributi/summary` riusa lo stesso precompute bulk per evitare full-scan N+1 sul read-model operativo e ridurre il rischio di `Gateway Time-out` sul perimetro GAIA dal 2022 in poi.
- Aggiunta regressione backend dedicata per verificare che con `open_only=true` la pagina costruisca item solo per il `page_size` richiesto.
- Validata la change con `pytest tests/ruolo/test_tributi_api.py --cov=app.modules.ruolo.tributi_repositories --cov-report=term-missing --cov-fail-under=100 -q`, coverage `100%` su `backend/app/modules/ruolo/tributi_repositories.py`.

### 2026-08-03
- Corretto `/ruolo/tributi` nella sezione `Avvisi e saldo pagamento`: il pulsante `Avviso sollecito` viene esposto solo per le annualita con sollecito GAIA attivo (`reminder_enabled=true`).
- La preview rapida da riga usa esclusivamente l'`anno_tributario` dell'avviso cliccato, senza riusare il range default del wizard batch.
- Corretto il calcolo degli avvisi inCASS non rateizzati: `importo_residuo` ora guida saldo e stato pagamento anche quando `importo_rateizzato=0`, riallineando `Pagato`, `Parzialmente pagato` e `Non pagato` alla posizione CapaciTas.
- Validata la change con coverage mirata al `100%` su `backend/app/modules/ruolo/tributi_repositories.py`, `backend/app/modules/ruolo/routes/tributi_routes.py` e `frontend/src/app/ruolo/tributi/page.tsx`.

### 2026-07-30
- In `/ruolo/tributi` le `Regole ruolo` e i `Gestori annualita tributo` restano visibili agli utenti con accesso di consultazione, evitando errori operativi su sola lettura.
- Le azioni di gestione delle regole (`Gestisci regole`, `Gestisci regole calcolo` e relative modali CRUD) sono disabilitate per utenti non `admin`/`super_admin`; il fallback in caso di sessione non verificabile resta read-only.
- Validata la change frontend con test unitari dedicati e coverage mirata al `100%` su `frontend/src/app/ruolo/tributi/page.tsx`.

## Checklist tecnica

### M0 — Analisi
- [x] PRD v1 prodotto
- [x] Execution Plan v1 prodotto
- [x] Prompt Codex prodotto
- [x] Formato file `.dmp` analizzato (sample 2 partite)
- [x] Modello dati definito (4 tabelle `ruolo_*` + `catasto_parcels`)
- [x] Logica temporale particelle definita (`valid_from`/`valid_to`)
- [x] Pattern job asincrono definito (su modello `wc_sync_job`)
- [x] Integrazione con `ana_subjects` via CF/PIVA definita
- [x] Unità SUP.CATA. verificata con dominio — **are** (1 ara = 100 mq)
- [x] Dipendenza `pypdf==5.4.0` aggiunta in requirements

### M1 — Fondazione backend
- [x] Migration Alembic creata e applicata (`20260416_0048_add_ruolo_module.py`)
  - [x] `ruolo_import_jobs`
  - [x] `ruolo_avvisi`
  - [x] `ruolo_partite`
  - [x] `ruolo_particelle`
  - [x] `catasto_parcels`
- [x] Modelli ORM in `backend/app/modules/ruolo/models.py`
- [x] Modello `CatastoParcel` aggiunto in `backend/app/models/catasto.py`
- [x] Enumerazioni in `ruolo/enums.py`
- [x] Parser `ruolo/services/parser.py`
  - [x] Split partite per marcatore `<inizio>` / `<-fine->`
  - [x] Estrazione codice CNC
  - [x] Parse riga N2 (CF/PIVA + extra)
  - [x] Parse nominativo, domicilio, residenza
  - [x] Parse partite catastali (codice, comune, tributi)
  - [x] Parse co-intestati (opzionale)
  - [x] Parse righe particelle positional (con gestione subalterni letterali)
  - [x] Parse righe N4 (totali + codice utenza)
  - [x] Fault-tolerance: errore per-partita senza interruzione
- [x] Test unitari parser — **23 test, tutti passanti** (`backend/tests/ruolo/test_parser.py`)
- [x] Import service `ruolo/services/import_service.py`
  - [x] Background task con sessione DB indipendente
  - [x] Estrazione testo da PDF (+ fallback `.dmp` grezzo)
  - [x] Loop import con contatori
  - [x] Upsert avvisi idempotente
  - [x] Risoluzione soggetto via CF/PIVA
  - [x] Upsert `catasto_parcels` con logica temporale
  - [x] Gestione `SubjectNotFound` → skipped
  - [x] Finalizzazione job (status, contatori, error_detail, finished_at)

### M2 — API e query layer
- [x] Schemas Pydantic in `ruolo/schemas.py`
- [x] Repository in `ruolo/repositories.py`
- [x] `ruolo/routes/import_routes.py`
  - [x] `GET /ruolo/import/jobs`
  - [x] `GET /ruolo/import/jobs/{job_id}`
- [x] `ruolo/routes/query_routes.py`
  - [x] `GET /ruolo/avvisi`
  - [x] `GET /ruolo/avvisi/export` (CSV)
  - [x] `GET /ruolo/avvisi/{avviso_id}`
  - [x] `GET /ruolo/soggetti/{subject_id}/avvisi`
  - [x] `GET /ruolo/soggetti/{subject_id}/terreni-colture` — riepilogo read-only terreni/colture a ruolo con GeoJSON opzionale on-demand
  - [x] `GET /ruolo/particelle`
  - [x] `GET /ruolo/stats`
  - [x] `GET /ruolo/stats/comuni`
  - [x] `GET /catasto/parcels`
  - [x] `GET /catasto/parcels/{parcel_id}/history`
- [x] `ruolo/router.py` — aggregazione router con prefisso `/ruolo`

### M3 — Bootstrap e integrazione
- [x] `ruolo/bootstrap.py` con 4 section keys
- [x] Flag `module_ruolo` su `ApplicationUser` (ORM + enabled_modules)
- [x] `CurrentUser` e `ApplicationUser` TypeScript aggiornati con `module_ruolo`
- [x] `backend/app/scripts/bootstrap_sections.py` aggiornato
- [x] Router registrato in `backend/app/api/router.py`
- [x] Navigazione frontend aggiornata (platform-sidebar, module-sidebar, sidebar)
- [x] Integrazione scheda soggetto anagrafica
  - [x] Endpoint `GET /ruolo/soggetti/{subject_id}/avvisi` accessibile
  - [x] Componente `RuoloAvvisiSection` nella pagina soggetti utenze
  - [x] Link da avviso → dettaglio funzionante

### M4 — Frontend
- [x] `frontend/src/types/ruolo.ts`
- [x] `frontend/src/lib/ruolo-api.ts`
- [x] `frontend/src/components/ruolo/module-page.tsx`
- [x] Layout modulo `frontend/src/app/ruolo/layout.tsx`
- [x] `/ruolo` — dashboard con stats per anno + ultimi job
- [x] `/ruolo` — CTA stato vuoto apre import in modale con fallback `Apri pagina`
- [x] `/ruolo` — dashboard riallineata al pattern UI/UX dei moduli maturi (hero workspace, KPI, action cards, pannelli)
- [x] `/ruolo/import` — upload + lista job + polling automatico, riallineata al pattern UI/UX dei moduli maturi
- [x] `/ruolo/avvisi` — lista con filtri URL-driven + paginazione, riallineata al pattern UI/UX dei moduli maturi
- [x] `/ruolo/avvisi` — ricerca unificata live (`q`) con debounce, soglia minima 3 caratteri, toggle `Solo avvisi non collegati` inline e dettaglio avviso in modale embedded
- [x] `/ruolo/avvisi/[id]` — dettaglio completo con partite espandibili, riallineato al pattern UI/UX dei moduli maturi
- [x] `/ruolo/particelle` — vista dedicata al dataset storico `ruolo_particelle`, con filtri ruolo, stato di collegamento a `cat_particelle` e classificazione AdE
- [x] `/ruolo/stats` — statistiche per anno e per comune interattive, riallineate al pattern UI/UX dei moduli maturi
- [x] `/ruolo` — controllo economico `ruolo vs Capacitas` con KPI, mismatch per CF/P.IVA, breakdown per comune ed export CSV
- [x] `/ruolo/controlli-capacitas` — console dedicata di supervisione con drilldown verso avvisi per `codice_fiscale` e `comune`
- [x] Integrazione scheda soggetto `RuoloAvvisiSection`, riallineata al pattern UI/UX del modulo con hero compatta, mini-stat e CTA coerenti
- [x] Nessun errore lint (`ReadLints` verde)

### M5 — Hardening
- [x] `backend/tests/ruolo/test_parser.py` — **23 test passanti**
- [x] Permessi `require_module("ruolo")` applicati su tutti gli endpoint
- [x] Fix permessi admin esistenti: migration di backfill `module_ruolo` per account `admin` / `super_admin` creati prima del modulo
- [x] Export CSV `GET /ruolo/avvisi/export` implementato
- [x] Compatibilità Pydantic v2/UUID sugli endpoint `GET /ruolo/import/jobs`, `GET /ruolo/import/jobs/{job_id}` e sui response model `ruolo/schemas.py`
  - Fixato il mismatch tra UUID ORM nativi e campi `str` nei model di risposta, mantenendo serializzazione JSON string verso il frontend
  - Aggiunto test API dedicato `backend/tests/ruolo/test_api.py`
- [x] Allineamento parser/import ai file DMP reali 2025 di Capacitàs
  - Lo split delle `Partita CNC` ora supporta sia il primo header con prefisso `<qm500>--` sia i blocchi successivi con header `---------Partita CNC ...`
  - Normalizzato `catasto_comuni.codice_sister` composito (es. `F272#MOGORO#0#0`) al codice catastale corto usabile in `catasto_parcels.comune_codice`
  - Normalizzati i comuni di partita catastale da DMP: rimozione quote tra parentesi e alias storici (`SILI'*ORISTANO`, `OLLASTRA SIMAXIS`, `SAN NICOLO ARCIDANO`)
  - Hardening del parser particelle: le righe legenda/header (`DOM.=DOMANDA IRRIGUA`, `FOG.=FOGLIO CATASTALE`, `CONSUMI DA CONTATORE`, separatori) non possono alimentare `catasto_parcels`
  - Risoluzione comune solo con match esatto case-insensitive; eliminato il fallback parziale `ILIKE '%nome%'` per evitare casi come `ARBOREA` risolto in `PALMAS ARBOREA`
  - Fallback risoluzione codice comune da `cat_particelle` quando `catasto_comuni` non contiene il comune ma la particella GAIA esiste in modo univoco
  - Aggiunti test `backend/tests/ruolo/test_parser.py` e `backend/tests/ruolo/test_import_helpers.py`
- [x] Report job Ruolo persistito e consultabile da UI
  - `params_json` del job contiene `report_summary` e `report_preview` con motivazioni dei casi `skipped` / `error`
  - In `/ruolo/import` ogni card job espone una modale “Apri report” con riepilogo e dettaglio operativo
  - Semantica esplicitata: `records_skipped` = avvisi importati ma non collegati a un soggetto in Anagrafica
- [x] Collegamento risolto `ruolo_particelle -> cat_particelle`
  - Aggiunta FK nullable `cat_particella_id` verso `cat_particelle.id`
  - L'import ruolo valorizza la FK solo per match univoci su codice catastale, foglio, particella e subalterno
  - Se il ruolo ha un subalterno ma `cat_particelle` ha solo la particella base, il match e consentito solo se la base e univoca e viene marcato `base_without_sub`
  - Aggiunto script `backend/scripts/backfill_ruolo_cat_particella_id.py` per allineare i dati gia importati
  - Aggiunto script `backend/scripts/repair_ruolo_catasto_parcels.py` per normalizzare dati gia importati, ricostruire `catasto_parcels` mancanti e rimuovere orfani sporchi con foglio/particella non numerici
  - Bonifica locale 2026-05-13: `catasto_parcel_not_resolved` ridotti da 4.099 a 3; eliminati 536 `catasto_parcels` orfani sporchi; export aggiornato in `exports/report_backfill_ruolo_cat_particella.md`
  - Bonifica mismatch comune 2026-05-13: riparate 5.520 righe con codice comune errato; 5.234 sono diventate collegate a `cat_particelle`; non collegate residue ridotte a 2.583
  - Estesa al Ruolo la regola storica gia usata da sync Terreni Capacitas per lo scambio Arborea/Terralba: se la particella non esiste sul comune sorgente, il resolver prova l'altro comune della coppia e marca il match con `swapped_arborea_terralba`; recuperate 249 righe ulteriori, non collegate residue a 2.334
  - Allineata la risoluzione Ruolo delle frazioni catastali di Oristano alla logica Capacitas/Agenzia: `SILI -> sezione E`, `NURAXINIEDDU -> D`, `MASSAMA -> C`, `DONIGALA -> B`. Il repair `--repair-oristano-frazione-sections` ricalcola anche righe gia collegate per evitare match permissivi su solo `G113 + foglio + particella`.
- [x] `backend/tests/ruolo/test_import.py` — import service, report job, skipped/error preview
- [x] `backend/tests/ruolo/test_api.py` — filtro unificato `GET /ruolo/avvisi?q=...` su nominativo, CF, comune, anno e codice utenza
- [x] `backend/tests/ruolo/test_api.py` — controllo `ruolo vs Capacitas` (riepilogo, comuni, export) coperto anche sui casi PostgreSQL con `nome_comune` valorizzato
- [x] `backend/tests/ruolo/test_catasto_parcels.py` — logica temporale `catasto_parcels`
- [x] `backend/tests/ruolo/test_import_integration.py` — smoke `integration-light` su blocchi DMP 2025 realistici con parser reale, merge duplicati, skipped report e filtro sezioni `CONSUMI`
- [x] `frontend/tests/e2e/ruolo-avvisi.spec.ts` — soglia minima 3 caratteri, debounce live search e apertura modale dettaglio
- [x] `frontend/tests/unit/ruolo-pages.test.tsx` — dashboard e console `controlli-capacitas` coperte su export, drilldown ed empty state
- [ ] Import completo file Ruolo 2024 (~9.810 partite) su dati reali (pendente)

---

## Decisioni aperte

| # | Decisione | Stato | Note |
|---|-----------|-------|------|
| D1 | Unità colonna `SUP.CATA.` | **✅ CHIUSA** | Are (1 ara = 100 mq = 0,01 ha). Colonne: `sup_catastale_are` (valore letto) + `sup_catastale_ha` (are / 100). |
| D2 | Libreria estrazione testo PDF (`pypdf` vs `pdfminer.six`) | Aperta | Verificare quale è già in requirements; se nessuna, aggiungere `pypdf` |
| D6 | Campo `1.679.520` riga N4 | **✅ CHIUSA** | Significato non determinato. Salvare as-is in `n4_campo_sconosciuto` (VARCHAR 30, nullable). Analisi futura. |
| D3 | Significato campi `00000000 00 N` riga N2 | Aperta | Conservati in `n2_extra_raw`; analisi futura |
| D4 | Co-intestati come FK in MVP vs testo libero | **Deciso: testo libero** | Post-MVP collegare come FK verso `ana_subjects` |
| D5 | Blocco automatico re-import anno già presente | **Deciso: avvertimento senza blocco** | L'operatore vede warning, non viene bloccato |

---

## Change log

### 2026-07-28
- Arricchita la lista `/ruolo/avvisi`: le righe non mostrano piu il codice utenza e pubblicano badge separati per notifica `Digitale/PEC` e `Raccomandata`, entrambi visibili quando le due sorgenti risultano agganciate allo stesso avviso.
- Il backend `GET /ruolo/avvisi` espone un riepilogo notifica opzionale caricato in batch: delivery PEC da `inCASS` (`mailing_list`) e raccomandate abbinate da Poste Online (`ruolo_tributi_registered_mails`), evitando query per singola riga.
- Coperti i casi con PEC+racc., avviso senza notifiche, payload inCASS malformati, preferred notice non corrispondente e scelta della raccomandata piu recente.
- Validato il perimetro modificato con coverage `100%`:
  backend changed-line coverage su `repositories.py`, `query_routes.py`, `schemas.py`;
  frontend coverage 100% su `frontend/src/app/ruolo/avvisi/page.tsx` e `frontend/src/lib/ruolo-avvisi-notifications.ts`.
- Aggiunta nel dettaglio tributo (`/ruolo/tributi/[avvisoId]`) e nella modal `Dettaglio tributo` della lista `/ruolo/tributi` l'azione `Accoda sync inCASS`.
- L'azione accoda una sincronizzazione puntuale sul soggetto GAIA collegato all'avviso tramite `POST /elaborazioni/capacitas/incass/avvisi/jobs`, con `subject_ids` valorizzato, `include_details=true`, `include_partitario=true`, mailing escluso e `continue_on_error=true`.
- Se l'avviso non espone `subject_id`, la UI mostra un errore operativo e non invia job inCASS.
- Validato il perimetro frontend modificato con test unitari dedicati e coverage 100% su `frontend/src/app/ruolo/tributi/page.tsx` e `frontend/src/app/ruolo/tributi/[avvisoId]/page.tsx`.
- Aggiornato il renderer PDF del template GAIA: il partitario viene ripulito anche dalle azioni UI finali `Chiudi`/`Scarica`, ogni pagina del partitario stampa `Dettaglio partitario allegato - pagina X di N` e il bollettino TD 896 viene unito come ultima pagina dopo il partitario.
- Il renderer mantiene tre job Chromium separati (`avviso/comunicazioni`, `partitario`, `bollettino`) e merge finale con `pypdf`, cosi partitari lunghi non ridimensionano il bollettino.
- Estesa la copertura regressione su `tributi_reminder_service.py` con gate coverage 100% e aggiornato il grafo codice Ruolo.
- La prima pagina del template GAIA espone ora `Numero avviso` nella tabella riepilogo per ogni
  riga annuale `Ruolo {anno}`, usando il `codice_cnc` dell'avviso corrispondente; coperti sia
  renderer HTML/PDF sia tabella DOCX stabile.
- Per avvisi rateizzati, `Dettaglio tributo` e la sezione `Avvisi di pagamento` del soggetto espongono il riepilogo inCASS (`importo_rateizzato`, carico, riscosso, residuo) e calcolano il costo rateizzazione come differenza positiva fra rateizzato e carico.
- Nei solleciti/preview GAIA il totale da mettere in avviso usa l'emesso rateizzato inCASS piu il versato dell'utenza e include anche la quota raccomandata (`11,55` euro) nel bollettino.
- La scadenza rata del bollettino GAIA usa la data esplicita se presente; in assenza di scadenza, il fallback e `generated_at + 30 giorni` dalla creazione della preview.
- Estesa la policy di calcolo tributi con `interest_start_mode`: `fixed_date` mantiene la decorrenza fissa, mentre `notification_date` usa per gli interessi la data invio/accettazione PEC da inCASS o la data ricezione/consegna raccomandata dal payload Poste Online; `interest_from` resta data minima/fallback.
- Aggiunta migration `20260728_1120_ruolo_tributi_interest_start_mode` per persistere la modalita di decorrenza interessi sulle policy di maggiorazione.
- Aggiunta la scadenza del pagamento bonario (`bonario_due_date`) sulle regole di calcolo ruolo: la data amministrativa resta esplicita e la decorrenza tecnica della maggiorazione (`surcharge_from`) viene derivata automaticamente dal giorno successivo.
- Aggiunta UI/UX dedicata in `/ruolo/tributi` per gestire le `Regole ruolo`: annualita, scadenza pagamento bonario, percentuale maggiorazione ruolo, percentuale interessi annui, fallback/minimo interessi e scelta decorrenza da notifica.
- In creazione, una nuova `Regola ruolo` con range annualita chiuso multi-anno viene espansa dalla UI in una policy distinta per ogni annualita, consentendo scadenze bonarie diverse per `2024`, `2025` e anni successivi senza modificare il motore backend di calcolo per singola annualita.
- Il dettaglio tributo espone ora `Decorrenza interessi` e `Sorgente decorrenza` per rendere verificabile il calcolo operativo su singolo avviso.

### 2026-07-27
- Aggiunto endpoint read-only `GET /ruolo/soggetti/{subject_id}/terreni-colture`: aggrega le particelle gia presenti a ruolo per soggetto e anno, con default sull'anno piu recente disponibile.
- La risposta espone totali, breakdown per coltura/comune/distretto, preview particelle, warning di mapping catastale e `geojson` opzionale solo con `include_geojson=true`; non avvia sync, non modifica importi e non scrive dati.
- Coperti i casi API su anno default, anno esplicito, payload vuoto e caricamento GeoJSON on-demand in `backend/tests/ruolo/test_api.py`.
- Rafforzato il flusso `Raccomandate Poste Online`: il parser HTML legge il valore esplicito di `<label>Stato</label>` evitando che footer, script o banner cookie finiscano in `status_label`; il limite DB resta una difesa finale.
- L'import raccomandate usa savepoint per riga, quindi un record sporco o un errore SQL non manda piu in rollback l'intero job e viene registrato come anomalia di import.
- Il worker Posta Online salva checkpoint di scraping su `/data/catasto/debug/posta-online-resume` e mantiene `result_json.resume_state`; un rerun dopo scrape completato riusa il payload locale senza rientrare su Poste e l'upsert evita duplicazioni.
- Validata la change Posta Online con coverage mirata al `100%` su:
  `backend/app/modules/ruolo/tributi_repositories.py`,
  `modules/elaborazioni/worker/posta_online_client.py`,
  `modules/elaborazioni/worker/posta_online_sync.py`.
- Riallineati i permessi del workflow solleciti tributi al comportamento operativo richiesto: gli utenti con accesso `ruolo.tributi.view` possono aprire la preview `Avviso sollecito`, usare il wizard batch e scaricare i documenti generati senza incorrere nel `403 Section access denied` del backend.
- Mantenuta la separazione dei permessi mutativi: pagamenti, stati e note restano protetti dalle rispettive section key dedicate.
- Validata la change con coverage mirata al `100%` sui file runtime toccati:
  `backend/app/modules/ruolo/routes/tributi_routes.py`,
  `frontend/src/app/ruolo/tributi/page.tsx`,
  `frontend/src/app/ruolo/tributi/solleciti/page.tsx`.
- Corretto il default operativo dei solleciti batch: il wizard `Genera PDF nel NAS` e il
  fallback backend usano ora il template GAIA `__gaia_proposal__`, quindi il PDF generato
  contiene avviso, bollettino postale TD 896 e partitario. Il DOCX legacy resta disponibile
  solo se un chiamante passa un path esplicito.
- Verificato sul server CED che il renderer produce un PDF di 4 pagine con bollettino a pagina 3.
- Validata la change con coverage mirata al `100%` su:
  `backend/app/modules/ruolo/tributi_repositories.py`,
  `frontend/src/app/ruolo/tributi/page.tsx`.
- Separata definitivamente la console `Raccomandate Poste Online` dalla pagina Tributi:
  `/ruolo/tributi` resta dedicata all'elenco tributi e ai solleciti, mentre la sidebar apre
  le raccomandate su `/ruolo/raccomandate`.
- Aggiunti test frontend di regressione per verificare che `/ruolo/tributi` non contenga piu
  la console Raccomandate e che la sidebar mantenga attive route distinte.
- Corretto il renderer PDF del template GAIA per partitari reali lunghi: Chromium genera ora
  avviso/comunicazioni/bollettino e partitario in PDF separati, poi il backend li unisce con
  `pypdf`, evitando che il partitario faccia ridurre o spostare il bollettino.
- Validato localmente il caso `00050540384_avviso_sollecito_2024-2025`: bollettino a pagina 3,
  partitario da pagina 4, dimensione piena allineata al riferimento
  `/tmp/gaia_sollecito_bollettino_896_prova.pdf`.
- Validata la change renderer con coverage mirata al `100%` su
  `backend/app/modules/ruolo/services/tributi_reminder_service.py`.

### 2026-07-24
- Predisposta la console read-only `Raccomandate Poste Online` per controllare matching e anomalie degli invii importati da Poste; la route frontend operativa corrente e `/ruolo/raccomandate`.
- Aggiunto in sidebar Ruolo il link diretto `Raccomandate` verso `/ruolo/raccomandate`.
- La console usa `GET /ruolo/tributi/raccomandate` con filtri su ricerca libera, `match_status`, `recovery_status`, `anomalies_only` e paginazione; la vista iniziale mostra solo le anomalie operative.
- Confermata la semantica di matching: Poste Online non espone identificativi GAIA di avviso/utenza, quindi l'associazione resta backend-only e indiziaria; il frontend mostra score, motivo, stato recupero e link all'avviso quando il backend ha prodotto un match.
- Il perimetro frontend modificato e coperto con test unitari dedicati e coverage 100% su `registered-mails-console.tsx` e `ruolo-api.ts`.
- Validata in locale la sync Poste Online con job limitato (`max_pages=1`, `max_details=1`, senza contatti): login headless, archivio e dettaglio sono stati letti correttamente; corretto il fallback di persistenza troncando i campi Poste indicizzati ai limiti DB e preservando il raw payload completo.

### 2026-07-23
- Corretto il flusso `Avviso sollecito` in `/ruolo/tributi`: la modale di preview si apre immediatamente al click con stato di caricamento e mostra gli errori di generazione nella stessa superficie, evitando che l'utente resti senza feedback mentre vengono creati i PDF.
- Reso robusto il renderer PDF del template GAIA: il backend ora trova Chromium anche nella cache Playwright del container Docker, oltre a binari di sistema e snap.
- Corretto il comportamento dell'autosync inCASS: i job automatici `Avvisi pagamenti` ora eseguono un refresh leggero di stato sugli avvisi gia sincronizzati, senza riscaricare dettaglio/partitario e senza riscrivere gli importi contabili.
- I nuovi avvisi intercettati durante l'autosync restano invece arricchibili con dettaglio e partitario tramite flag dedicati, cosi il monitor periodico aggiorna pagato/rateizzato/parziale e cattura novita senza rieseguire una sincronizzazione completa di tutti i ruoli.
- Limitato l'autosync automatico Ruolo/inCASS alla finestra notturna configurabile `20:00-06:00 Europe/Rome`: scheduler e worker saltano i job automatici fuori fascia, mentre le sync manuali restano disponibili.
- Ottimizzata la lettura dei recapiti mailing lato tributi: su PostgreSQL il summary legge solo `raw_detail_json.mailing_list`, evitando di materializzare l'intero JSON pesante del partitario.
- Validato il perimetro runtime modificato con coverage mirata al 100% su config, modelli payload inCASS, scheduler autosync, servizio inCASS e repository tributi.

### 2026-07-11
- Riallineate le `ruolo_particelle` 2019-2024 su locale e server CED con `scripts/materialize_ruolo_from_incass.py --replace-year --reparse-partitario`.
- Creati backup mirati pre-apply delle tabelle `ruolo_avvisi`, `ruolo_partite`, `ruolo_particelle`, `ruolo_import_jobs` e `catasto_parcels`.
- Conteggi finali allineati locale/server: 2019=17065, 2020=20226, 2021=24390, 2022=93540, 2023=95062, 2024=96684.
- Verifiche qualità post-run: `sup_irrigata_ha > 1000 = 0` e `distretto NULL/0/2019 = 0` per tutte le annualità 2019-2024.
- Dettaglio operativo in `domain-docs/ruolo/docs/RUOLO_PARTICELLE_RIALLINEAMENTO_2019_2024_2026-07-11.md`.

### 2026-04-16
- PRD v1, Execution Plan v1, Prompt Codex e Progress v1 prodotti.
- Formato file `.dmp` analizzato su sample Ruolo 2024 (2 partite CNC).
- Modello dati definito: 4 tabelle `ruolo_*` + `catasto_parcels` con logica temporale.
- Decisione architetturale: `ruolo` modulo autonomo (non sub-modulo di `utenze`).
- Decisione: co-intestati come testo libero nel MVP.
- Decisione: avvertimento (non blocco) su re-import anno già presente.
- Punto aperto D1 (unità superfici) identificato come prerequisito critico per M1.

### 2026-04-16 (aggiornamento)
- D1 chiusa: SUP.CATA. confermata in are. Colonne DB: `sup_catastale_are` + `sup_catastale_ha`.
- Aggiornati PRD, Execution Plan e Prompt Codex con unità corretta.

### 2026-04-16 (implementazione M1–M5)
- M1 completata: migration applicata, modelli ORM, enums, parser con 14 test unitari, import service asincrono.
- M2 completata: schemas Pydantic, repository, 10 endpoint REST (import + query + export CSV + catasto parcels).
- M3 completata: bootstrap section keys, flag `module_ruolo` su ApplicationUser, router registrato.
- M4 completata: 6 pagine frontend (`/ruolo`, `/ruolo/avvisi`, `/ruolo/avvisi/[id]`, `/ruolo/particelle`, `/ruolo/stats`, `/ruolo/import`), widget soggetto, navigazione aggiornata.
- M5 parziale: permessi `require_module` attivi; test di integrazione API pendenti.

### 2026-04-17
- Allineata anche l'integrazione embedded `RuoloAvvisiSection` nella scheda soggetto del dominio utenze, con visual language coerente al workspace `ruolo` e CTA operative uniformate.
- Ridotta l'altezza della hero di `/ruolo/import` quando aperta in modale (`embedded=1`), per migliorare leggibilità e densità del workspace rapido.
- Compattata anche la KPI row del workspace rapido `/ruolo/import` in modalità embedded, con gap e tile più bassi per aumentare spazio utile sopra il fold.
- `/ruolo/import` ora prova a rilevare automaticamente l'anno tributario dal file selezionato (contenuto PDF/testo o filename) e consente comunque override manuale.
- Euristica anno `ruolo` resa deterministica: priorità a filename `R2024...`, poi pattern `Partita CNC 01.02021000039305` da cui viene estratto `2021`, infine fallback testuali.
- Aumentato il limite upload Nginx del progetto per supportare file `ruolo` fino a 128 MB senza errore `413 Request Entity Too Large`.

### 2026-05-15
- `GET /ruolo/avvisi` e `GET /ruolo/avvisi/export` supportano ora il parametro `q`, con matching su `codice_cnc`, `nominativo_raw`, `codice_fiscale_raw`, `codice_utenza`, `anno_tributario` e `comune_nome` delle partite collegate.
- `/ruolo/avvisi` e stata riallineata alla UX di `utenze`: campo singolo di ricerca, stato iniziale “Ricerca pronta”, avvio automatico dopo 3 caratteri, debounce client-side e aggiornamento URL con `router.replace` per evitare raffiche di chiamate.
- Le card avviso aprono una modale con iframe embedded del dettaglio; `/ruolo/avvisi/[id]` nasconde il top header quando riceve `?embedded=1`.
- Aggiunti test backend sul filtro `q` e test Playwright sul comportamento live search + apertura modale.

### 2026-05-18
- Aggiunta la page frontend `/ruolo/particelle` come vista del dataset storico `ruolo_particelle`, non limitata a `cat_particelle`.
- Esteso `GET /ruolo/particelle` con comune di partita, stato di match verso `cat_particelle` e classificazione/stato scansione AdE.
- La dashboard `Ruolo`, la sidebar modulo e la ricerca globale ora espongono il nuovo accesso rapido alle particelle a ruolo.
- La dashboard `Ruolo` separa ora gli `avvisi non collegati` dai `non collegati a catasto` e dai casi `soppresse AdE`, eliminando l'indicatore ambiguo precedente.
- `/ruolo/particelle` supporta ora apertura riga in modale con dettaglio storico e link al Catasto quando il match esiste.
- Il workspace `/ruolo/particelle` riusa la section permission `ruolo.avvisi` per evitare blocchi operativi su ambienti dove non sia stato riallineato il catalogo sezioni.

### 2026-06-15
- Aggiunto il controllo economico `ruolo vs Capacitas` sulla dashboard `/ruolo`, con KPI, delta aggregati `0648/0985`, mismatch per `CF/P.IVA`, breakdown per comune ed export CSV.
- Introdotta la console dedicata `/ruolo/controlli-capacitas`, collegata dalla navigazione di modulo e pensata come workspace operativo per responsabile e supervisione.
- Estesa `/ruolo/avvisi` con supporto ai drilldown URL-driven su `codice_fiscale` e `comune`, così i mismatch del controllo Capacitas aprono direttamente la lista di lavoro coerente.
- Hardening backend sulle query aggregate PostgreSQL: corretto il riuso delle espressioni `coalesce(...)` in `GET /ruolo/stats/analytics` e `GET /ruolo/stats/capacitas-check/comuni`, eliminando i `500 Internal Server Error` dovuti a `GroupingError`.
- Rafforzata la copertura test backend/frontend sul perimetro `controlli-capacitas`, inclusi drilldown, export e caso di stato vuoto.

### 2026-06-16
- Promossa la console `/ruolo/calcolo-gaia` a vista operativa principale del modulo per il calcolo del ruolo, lasciando `/ruolo/controlli-capacitas` come `Audit Capacitas` tecnico.
- Il payload backend `GET /ruolo/stats/calcolo-gaia` e ora autosufficiente: include valori `Ruolo`, `GAIA`, `Excel`, stato confronto e diagnosi per soggetto, senza dipendere dal dataset mismatch di `capacitas-check`.
- Corretto un rischio funzionale della prima implementazione frontend: soggetti presenti nel ruolo ma fuori dal top mismatch o sotto soglia potevano apparire come “senza confronto ruolo”; ora la console usa solo il payload dedicato `calcolo-gaia`.
- Esteso anche l'export CSV `calcolo-gaia` per scrivere direttamente i valori ruolo e la diagnosi derivati dal medesimo endpoint, mantenendo coerenza tra UI ed export.
- Aggiornata la copertura con test backend sul payload `calcolo-gaia` arricchito e test frontend dedicato alla nuova console con apertura modale del dettaglio calcolo.

### 2026-07-08
- Chiarita in UI e documentazione la separazione delle tre sorgenti economiche: `Ruolo inCASS` dal partitario del ruolo pubblicato, `Excel Capacitas` dal file importato nel batch attivo, `Calcolo GAIA` da imponibile e aliquote Capacitas.
- Il breakdown per comune di `capacitas-check/comuni` normalizza frazioni e alias territoriali prima del confronto (`FRAZIONE*COMUNE -> COMUNE`, `SILI -> ORISTANO`, `SAN NICOLO D'ARCIDANO -> SAN NICOLO ARCIDANO`) ed espone le denominazioni sorgenti aggregate.
- Aggiunta l'anteprima delle righe Excel Capacitas nel drilldown `Apri calcolo`, con importi originali, campi sorgente e segnali di anomalia.
- Verifiche eseguite: `backend/tests/ruolo/test_api.py`, `frontend/tests/unit/ruolo-pages.test.tsx`, lint frontend mirato e controllo coverage puntuale sulle linee runtime modificate.
