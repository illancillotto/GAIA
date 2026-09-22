# Generazione 2022/2023: Conferma Ed Export

## Stato Al 2026-09-22

Implementate anteprima PDF marcata di ogni documento e preparazione/download
dello ZIP definitivo dopo conferma. L'export conserva i byte originali e
ricontrolla revisione, integrita e numerazione prima del claim auditato.
Il packaging avviene fuori dai lock; un secondo controllo chiude la finestra
concorrente. Retry riusano lo stesso archivio, senza spedire o scrivere sul NAS.

Procedura operatore, requisiti di migration, API e limiti sono descritti in
[Anteprima ed export solleciti](ANTEPRIMA_EXPORT_SOLLECITI.md).
Invio automatico Poste e import operativo STEP restano in standby.

Le sezioni datate 2026-09-21 e successive in questo documento sono evidenze
storiche delle tranche precedenti: i riferimenti a export/anteprima non ancora
disponibili descrivono lo stato di allora.

## Stato Al 2026-09-21

### Verifica UI E Conferma: Incremento Collaudato

La pagina Solleciti ora elenca i lotti, carica il dettaglio e propone la
conferma ai soli operatori con `ruolo.tributi.manage_status`. Gestisce
paginazione, errori e identita del documento; non offre export definitivo.
La conferma ricontrolla identita canonica e prenotazione e acquisisce il fence
prima di leggere eventuali conferme precedenti. Le eccezioni di revisione
producono HTTP 409; protocollo indisponibile produce HTTP 503.

Verifica finale: 376 test backend passati senza skip con PostgreSQL temporaneo
isolato; 25 test frontend passati con coverage statement/branch/function/line al
100%; due smoke test Playwright (desktop 1440px e mobile 390px) passati;
typecheck TypeScript, ESLint mirato, Ruff e `git diff --check` riusciti. Nessuna
migration operativa eseguita. Evidenze: `/tmp/gaia-notice-final-tests.log`,
`/tmp/gaia-notice-final-coverage.json`, `/tmp/gaia-notice-final-typecheck.log`,
`/tmp/gaia-notice-final-eslint.log`.

Il quality ratchet contro `main` passa con `findings: []`; la baseline non e
stata modificata. Le nuove suite coprono API, migration round-trip, concorrenza
PostgreSQL e UI. Coverage backend statement/branch e al 100% su tutti i runtime
introdotti per conferma, revisione, bozze e generazione; coverage frontend e al
100% su statement/branch/function/line. Il cumulativo comprensivo dei moduli
legacy `tributi_repositories.py` e `tributi_notice_registry.py` raggiunge il
99,25%: restano soltanto archi non esercitati, senza righe runtime scoperte e
senza esclusioni aggiunte. E2E Playwright desktop/mobile passa senza overflow o
page error.
Restano fuori scope anteprima privata avanzata, export versionato e invio
Poste/STEP; la conferma non autorizza nessuno di questi effetti.
Le sezioni seguenti conservano le evidenze storiche delle tranche precedenti.

Workflow confermato dall'operatore: **Genera bozza -> Conferma lotto ->
Esporta/invia**. Implementata la prima tranche backend di isolamento delle
bozze. La finalizzazione concorrente **non e implementata**: conferma ed export
restano indisponibili, senza flag che li abiliti. Nessun invio Poste o import
STEP attivato; nessun lock globale durante rendering o rete.

### Terza Tranche: Revisione Collegata Alle Bozze

`notice_draft_inputs.py` collega ora il protocollo ai percorsi reali
`create_generated_reminder` e `create_reminder_batch`, compresi i lotti misti.
La migration `20260921_1900` aggiunge `NoticeDraft.input_basis`, nullable, senza
backfill: le bozze precedenti non ricevono una revisione corrente a posteriori.

- Il decoratore acquisisce epoch/revisione **prima** della lettura dei dati,
  senza lock globale; rinnova gli oggetti gia caricati nell'identity map e
  rimuove solo la cache Tributi delle policy attive, preservando le altre.
- La cattura vive soltanto nel contesto della chiamata e della transazione;
  viene rimossa anche dopo errori e ripristinata correttamente in chiamate
  annidate. Dopo commit/rollback o cambio del giorno non puo essere riusata.
- Una sessione con oggetti nuovi, modificati o cancellati non perde modifiche
  per effetto di `expire_all`: non viene catturata alcuna revisione. SQLite o
  protocollo PostgreSQL non disponibile producono ancora bozze private, ma
  senza base verificabile. Errori SQL diversi non sono silenziati.
- Un avviso passato da un'altra sessione o detached non puo ottenere una
  revisione valida: il suo contenuto potrebbe precedere la lettura del token.
- `_persist` salva sul singolo artefatto una copia del token, versione del
  protocollo e data di calcolo. I filtri inviati dal client non forniscono il
  token. Tutti gli elementi dello stesso lotto condividono la cattura iniziale.
- Se un pagamento/notifica/STEP cambia durante il rendering o prima del
  commit, la bozza conserva il token **precedente**, quindi risulta obsoleta:
  nessun aggiornamento automatico al token finale nasconde la variazione.
  Anche eventuali scritture dipendenti della stessa generazione possono
  renderla obsoleta al commit: rigenerare, non correggere il token a mano.

`notice_draft_review.check_generation_inputs` e un controllo backend consultivo
dell'intera generazione, non un comando di conferma. Usa una nuova sessione,
acquisisce prima il fence globale e poi padre/elementi/bozze; verifica presenza,
completezza, provenienza, stato privato, uniformita e attualita della revisione,
data di calcolo, uguaglianza del payload e SHA-256 dei byte effettivi.
Un elemento non valido respinge il lotto intero, senza approvazioni parziali.
Il caricamento dei byte e differito; il controllo rifiuta oltre 100 artefatti o
64 MiB complessivi prima di leggerli per hashing. Sono limiti del controllo,
non ancora limiti di selezione/generazione nella UI legacy.

Il risultato restituisce un digest del contenuto verificato e mantiene
`authorizes_dispatch=False`, `confirmation_available=False`. Il lock termina
con la chiamata: il digest non e una prenotazione e non autorizza un export
successivo. Non sono aggiunte route pubbliche ne modifiche alla UI in questa
tranche. Un lotto respinto resta una bozza privata; non viene cancellato o
pubblicato e non viene simulata una conferma persistente.

Restano da completare la provenienza immutabile dei template/renderer, la
conferma persistente e il claim di export. La numerazione segue ora una
separazione esplicita: ogni bozza calcola e salva `notice_identity_key`, hash
stabile di anno di emissione, codice fiscale normalizzato, annualita e insieme
ordinato degli `avviso_id`. Il campo non dipende da importi, pagamenti,
notifiche o testo del documento e viene riusato nelle rigenerazioni.

Il `notice_number` presente nelle bozze resta per ora il progressivo compatibile
con il flusso legacy e non costituisce ancora il numero ufficiale emesso. La
conferma atomica futura assegnera il numero ufficiale una sola volta, usando
questa identita come chiave idempotente e impedendone il riuso dopo emissione.
Per gli import storici senza `avviso_id`, l'identita dovra includere anche fonte
e riferimento originale normalizzato.

### Quarta Tranche: Conferma Atomica

La migration `20260921_2000` introduce `ruolo_notice_generation_confirmations`.
`POST /ruolo/tributi/solleciti/batches/{id}/confirm` acquisisce il fence della
revisione, blocca lotto e artefatti, ricalcola digest e identita e promuove le
reservation numeriche a `confirmed` nella stessa transazione. Il comando e
idempotente per lotto e tipo (`batch`); una bozza obsoleta, incompleta,
modificata o priva di identita viene respinta senza scritture parziali.

La conferma non invia Poste/STEP e non abilita ancora il download definitivo:
crea solo il record auditabile che sara usato dal successivo claim di export.
La cattura della revisione non sostituisce questi gate: nessuna conferma,
pubblicazione nel registro definitivo, scrittura NAS o spedizione viene abilitata.

#### Evidenze Della Terza Tranche

- Repeat autorevole: **352 passed**, nessuno skip/xfail, 341 secondi. Include
  58 test nuovi, i 169 della generazione/bozze/API e i 125 del protocollo DB.
  PostgreSQL 16 temporaneo; nessun dato operativo o NAS reale utilizzato.
- Provati cattura prima delle letture, oggetti ORM e cache obsoleti, avviso
  detached/di altra sessione, sessione con modifiche pendenti, annidamento,
  errori, cambio transazione/giorno e token client ignorato. Pagamento durante
  rendering e prima del commit su singolo/lotto conserva la revisione vecchia.
- Controllo intero lotto misto con variazioni pagamento/notifica/STEP;
  rifiuto di artefatti mancanti/estranei, payload o byte cambiati, stati/path
  non privati, conteggi incoerenti, revisioni difformi e oltre i limiti.
  Il test della bozza vecchia verifica che il controllo non scriva un token.
- Migration SQLite/PostgreSQL round-trip e confronto metadata corrente;
  test PostgreSQL con dati preesistenti dimostra conservazione dei byte e
  `input_basis` nullo dopo upgrade. Head Alembic unico `20260921_1900`.
- Coverage full-file: runtime `2058/2058` statement, `772/772` branch;
  migration `10/10` statement, tutto **100%**, senza nuove esclusioni.
  Report `/tmp/gaia-input-repeat-coverage.json`, log
  `/tmp/gaia-input-repeat-tests.log`. Warning JWT delle fixture legacy.
- Lint backend, formatter nuovi file e diff-check passano. Ratchet globale
  contro merge-base `ec5b1375`: `findings: []`, baseline invariata.
  Metriche `/tmp/gaia-input-basis-{before,after}.json`: repository LOC
  `3641 -> 3644`, somme cyc/cog invariate `1185/1385`; servizio bozze
  LOC `106 -> 108`, modello `36 -> 37`. Rispetto alla baseline autorevole
  non peggiora il debito legacy. Nuovi input/review LOC `56/152`, max cyc
  `10/13` e cog `12/17`: warning visibili, nessuna nuova violation error-level.
- Log ratchet `/tmp/gaia-input-repeat-ratchet.log`; feature ordinaria, nessun
  refactoring o riduzione di debito rivendicati. Nessuna conferma persistente
  o UI collaudata in questa tranche: restano parte dello sviluppo successivo.

### Seconda Tranche: Revisione Dei Commit

Implementata la fondazione del protocollo DB, **non la conferma del lotto**.
Migration `20260921_1700` preparata, non applicata ai database operativi.
Le bozze preesistenti non hanno un token di revisione: non possono essere
rese confermabili assegnando loro la revisione corrente a posteriori.

- `notice_revision_models.py`: singleton con epoch UUID, revisione bigint e
  identificativo transazione. Una nuova installazione della migration cambia
  epoch: un vecchio token non torna valido se il contatore riparte da zero.
- Trigger PostgreSQL `CONSTRAINT ... DEFERRABLE INITIALLY DEFERRED` su
  INSERT/UPDATE/DELETE delle 23 tabelle elencate sotto. Il primo evento al
  commit incrementa la revisione; quelli della stessa transazione non la
  incrementano nuovamente. Rollback e savepoint annullati non la modificano.
  L'assenza del singleton fa fallire il writer, non permette un commit invisibile.
- I trigger coprono ORM, SQL bulk e COPY, anche con
  `session_replication_role=replica` (`ENABLE ALWAYS`). TRUNCATE usa un trigger
  statement-level immediato: essendo manutenzione distruttiva, conserva il lock
  fino al commit. Non usare TRUNCATE o `SET CONSTRAINTS ... IMMEDIATE` durante
  rendering/rete; nessun writer applicativo viene modificato per farlo.
- `notice_revision.py` legge direttamente colonne SQL, senza identity map o
  cache `db.info`. Rifiuta SQLite, autocommit, isolation level diversi da
  READ COMMITTED e installazioni con trigger mancanti/disabilitati/incompatibili.
- `read_revision` non prende lock; il futuro generatore deve acquisire il token
  **prima** di leggere i dati. `lock_revision` acquisisce il singleton fino alla
  fine della transazione e respinge un token diverso. Non e un controllo di
  ammissibilita e non autorizza generazione, download o invio.

La revisione e intenzionalmente globale al perimetro: anche modifiche estranee
alla singola posizione la cambiano. Questo privilegia la sicurezza ma potra
richiedere rigenerazioni superflue. Il lock comune si acquisisce normalmente
alla fine dei writer, non per tutta la durata del loro import/rendering.
Non sono introdotti advisory lock ignorabili dai writer esterni.

| Dipendenza | Tabelle coperte | Writer individuati |
| --- | --- | --- |
| Destinatari/inCASS | `ana_subjects`, `ana_persons`, `ana_companies`, `ana_payment_notices` | repository Ruolo, route Utenze, `elaborazioni_capacitas_incass.py` |
| Posizioni e dettaglio documento | `ruolo_avvisi`, `ruolo_partite`, `ruolo_particelle` | import e rettifiche Ruolo |
| Contabilita | `ruolo_tributi_payments`, `ruolo_tributi_avviso_status`, `ruolo_tributi_special_notices`, `ruolo_tributi_special_allocations` | pagamenti/import/annullamenti e allocazioni Tributi |
| Regole | `ruolo_tributi_year_managers`, `ruolo_tributi_calculation_policies`, `ruolo_tributi_templates` | gestori, policy e template DB |
| Poste | `ruolo_tributi_registered_mails` | import/sync Poste e collegamenti legacy |
| Registro | `ruolo_notice_documents`, `ruolo_notice_positions`, `ruolo_notice_attempts`, `ruolo_notice_evidence`, `ruolo_notice_notifications`, `ruolo_notice_recoveries` | storici, anomalie, notifica/STEP, riconciliazione e undo |
| Import/conflitti | `ruolo_notice_import_batches`, `ruolo_notice_import_rows` | anteprime/conferme Excel/Poste e risoluzioni conflitti |

Le tabelle solo audit/job non sono dipendenze del calcolo. Prenotazioni numeriche,
record legacy di generazione e artefatti non entrano nella revisione globale:
il prossimo comando dovra verificarne separatamente integrita, appartenenza,
immutabilita e unicita. I template su filesystem, la versione del renderer e
la data di calcolo non sono scritture DB: devono essere fissati nel manifest e
verificati esplicitamente. L'inventario non abilita automaticamente futuri writer
su nuove tabelle; vanno aggiunti con migration e test prima di usarli.

#### Confine Ancora Da Implementare

La terza tranche aggiunge token alle nuove bozze; non esistono ancora record di
conferma o claim. Per questi ultimi, uguaglianza epoch/revisione deve essere una condizione
obbligatoria: un commit successivo rende il token inutilizzabile nella stessa
transazione del writer, ma **questa tranche non cambia lo stato delle bozze**.
La UI dovra rappresentare tale invalidazione, non fidarsi del solo stato
`confirmed`. Tutto il lotto deve usare un unico snapshot approvato.

Il comando di conferma dovra usare una connessione/transazione dedicata breve,
senza modifiche pendenti delle dipendenze, acquisendo prima il singleton e
poi eventuali lock di conferma/claim in ordine deterministico. Non riusare
sessioni ORM del rendering. Pubblicare nel registro modifica a sua volta le
dipendenze: la futura implementazione deve dimostrare il proprio ordine di
commit e non creare una conferma che si invalidi da sola.

Il controllo del catalogo non e una difesa contro un amministratore DB che
riscrive funzioni, disabilita trigger dopo il controllo o altera la revisione.
Prima del rilascio servono privilegi separati migration/runtime, audit dei
permessi, prove di carico dei trigger deferred su import reali e limiti di
timeout. Non attribuire alle primitive garanzie contro DDL privilegiato o
atomicita con NAS/Poste. Conferma, export e invio restano chiusi.

#### Evidenze Della Seconda Tranche

- Repeat finale: **294 passed**, nessuno skip/xfail, in 259 secondi. Comprende
  125 test nuovi e i 169 di regressione API, generazione, bozze e concorrenza.
  PostgreSQL 16 temporaneo, schema isolato per test, nessun database operativo.
- 92 combinazioni tabella/operazione SQL, COPY/replica, bulk con un solo
  incremento per transazione, rollback/savepoint, singleton mancante, trigger
  disabilitati, autocommit anche engine-level e isolation level non supportati.
- Interleaving deterministici tramite worker e verifica `pg_blocking_pids`,
  incluse catene di attesa: due writer, writer precedente con commit/rollback,
  scrittura durante la fase senza lock e timeout con rollback. Nessun sleep
  usato per ordinare i commit. Writer reali pagamento/notifica/STEP su entrambi
  gli anni; ulteriori casi di pagamento parziale, orfano, inCASS, policy e unlink.
  Questi test verificano le primitive, **non una conferma end-to-end**.
- Round-trip migration SQLite (solo metadata) e PostgreSQL, confronto metadata,
  vincoli e nuova epoch dopo reinstallazione. Alembic ha un solo head
  `20260921_1700`; non e stato eseguito alcun upgrade operativo.
- Coverage Python full-file: runtime `95/95` statement e `12/12` branch;
  migration `27/27` statement e `8/8` branch, tutto **100%**, senza esclusioni.
  Il PL/pgSQL e verificato dai test PostgreSQL, non da coverage.py.
- `make lint-backend BASE_REF=ec5b1375 QUALITY_PYTHON=backend/.venv/bin/python`,
  formatter nuovi file, diff-check e ratchet globale sullo stesso merge-base:
  passano, `findings: []`. Baseline invariata. `db/base.py` LOC `358 -> 359`;
  nuovo modello LOC15, servizio LOC97, max cyc/cog `9/9`, nessuna violation.
  Feature ordinaria, nessun refactoring o riduzione di debito rivendicati.
- Log `/tmp/gaia-revision-final-tests.log`, coverage
  `/tmp/gaia-revision-final-coverage.json`, metriche
  `/tmp/gaia-revision-{before,after}.json`, ratchet
  `/tmp/gaia-revision-final-ratchet.log`. Warning JWT delle fixture legacy.

### Prima Tranche: Bozze Private

- `notice_draft_models.py` e migration `20260921_1500`: artefatto binario privato
  nel database, manifest del payload, SHA-256 dei byte, origine/record/lotto,
  operatore e timestamp. Unicita origine/record e stato `review_required`.
  Migration preparata, non applicata ai database operativi.
- `notice_drafts.py`: rendering in directory temporanea 0700, lettura limitata
  a 32 MiB, rifiuto file vuoti e symlink, cleanup anche su errore. Persistenza
  SQL nella stessa transazione dei record legacy: nessun orfano su NAS dopo
  rollback. La capienza DB/backup e i limiti per lotto vanno dimensionati prima
  del rilascio; questa scelta non introduce un archivio pubblico di file.
- Singolo 2022/2023 salvato come `draft`, senza path/download e senza pubblicare
  documento/evidenza nel registro definitivo. La provenienza della generazione
  resta nella riga privata con attore, manifest e artefatto.
- Un lotto con almeno una posizione 2022/2023 tratta **tutti** gli elementi come
  bozze, anche con `preview_only` e senza cartella NAS. Il flag interno e
  ricalcolato dal server: il client non puo disabilitarlo nei filtri.
- Lotto con bozze: `review_required`, elementi `draft`, `items_generated=0`:
  il contatore continua a contare documenti definitivi, non le bozze. Un lotto
  tutto fallito resta `failed`. Il dettaglio espone il motivo dell'indisponibilita.
- La prenotazione numerica legacy resta persistente con stato `draft`; non viene
  pubblicata come `generated`. Non cambia la chiave legacy di riuso numero per
  identita: la semantica di emissione/revisione definitiva appartiene alla
  tranche di conferma. Un numero su una bozza privata non e un avviso emesso.
- Download legacy 2022/2023 bloccato anche per file precedentemente generati e
  payload con anno mancante/discordante: controllo aggiuntivo sugli avvisi
  collegati. I file vecchi non vengono cancellati dal filesystem/NAS e non si
  puo revocare una copia gia ottenuta fuori da GAIA.

Non ci sono route che restituiscano i byte delle bozze. Non sono ancora
implementati anteprima marcata, revisione UI, conferma, invalidazione coordinata
o export. La UI legacy non e stata adattata in questa tranche e il workflow
completo **non e pronto al rilascio**. Le altre annualita mantengono generazione
e download legacy; nessuna spedizione viene effettuata.

## Problema Del Flusso Precedente

- `create_generated_reminder` controlla l'ammissibilita prima del rendering.
- `create_reminder_batch` seleziona e prepara gli elementi prima di generarli.
- `notice_generation._publish` registra documenti/posizioni/evidenze/audit,
  ma non coordina il commit con le scritture che cambiano l'ammissibilita.
- `_generate_and_store_batch_reminder_pdf` e il fallback DOCX scrivono il file
  locale oppure lo caricano sul NAS **prima del commit SQL**. Il nome batch
  deriva da CF/annualita e non identifica una revisione immutabile.
- Un rollback SQL non rimuove il file gia caricato e non ripristina un file
  eventualmente sovrascritto. La sola atomicita del registro non basta.

Una rilettura dopo il rendering lascia aperta la finestra prima del commit.
Lock di righe esistenti non impediscono nuovi pagamenti, documenti o orfani;
SERIALIZABLE da solo non impone l'ordine cronologico di commit richiesto.
Un advisory lock usato soltanto dal generatore non coordina gli altri writer.

## Workflow Confermato

1. **Selezione:** mostrare candidati 2022/2023 con saldo e motivi di blocco.
   Il controllo resta consultivo: nessuna autorizzazione all'invio.
2. **Bozza:** acquisire un perimetro esplicito di posizioni, payload e versioni;
   generare in storage privato e immutabile, non nella cartella finale NAS.
   L'anteprima deve essere marcata come bozza, senza un documento finale
   scaricabile attraverso route legacy o percorsi pubblici.
3. **Conferma:** in transazione breve, verificare perimetro, artefatto, versioni,
   saldo/importi, storico, notifica, STEP, orfani e policy con il protocollo
   condiviso dei writer. Non fare rendering, upload o rete sotto questi lock.
4. **Esito:** se i dati sono cambiati, invalidare la bozza e richiedere nuova
   generazione; non aggiornare soltanto il saldo nel DB lasciando il vecchio PDF.
   Se ammessa, registrare manifest/versione/hash e conferma auditata.
5. **Export/invio:** verificare che la conferma sia ancora utilizzabile al
   momento del claim. Download/upload e invio non sono la stessa operazione.
   Le variazioni successive al claim richiedono gestione esplicita, non rollback.

Conferma distinta anche per il singolo avviso, come lotto di un elemento.
Un lotto misto che comprende 2022/2023 deve passare per il nuovo workflow nel
suo insieme, senza permettere che una posizione sfugga al controllo.
Se cambia un elemento, proposta iniziale: respingere l'intera conferma con
motivi per posizione, evitando di esportare un sottoinsieme non approvato.

La numerazione rimane server-side con vincoli di unicita. Se il numero deve
comparire nella bozza, riservarlo in modo persistente e auditare l'abbandono;
non riciclare implicitamente numeri gia presenti in artefatti. Decidere la
semantica della prenotazione prima di modificare la tabella legacy.

## Storage E Stati

Stati proposti della generazione: `draft`, `rendering`, `review_required`,
`confirmed`, `invalidated`, `failed`, `cancelled`. Sono distinti dagli stati di
spedizione descritti in `POSTE_INVIO_AUTOMATICO.md` e da notifica/STEP.

Il manifest deve fissare lotto/revisione, posizioni, payload, versione template,
data calcolo, numero prenotato e hash degli artefatti. Il controllo va fatto sui
byte effettivi; un hash fornito dal browser non prova l'identita del documento.

Storage privato per artefatto/revisione, senza sovrascrittura. Gli artefatti
non referenziati dopo un crash vanno raccolti con un job di cleanup e retention,
non cancellando percorsi arbitrari dal payload. Il commit deve riferire un file
gia persistito e verificato; un file orfano non deve essere accessibile come
avviso finale. Permessi e route download devono rispettare questo confine.

Una futura copia sul NAS richiede un job recuperabile con destinazione
revisionata/hash e stato di pubblicazione distinto. SQL e NAS non condividono
una transazione: errore upload o commit non deve produrre falsi esiti positivi.

## Perimetro Di Coordinamento

Inventario iniziale, da completare con tutti i call site prima dell'attivazione:

| Responsabilita | Superfici gia individuate |
| --- | --- |
| Contabilita | Pagamenti/import, annullamenti, status e allocazioni in `tributi_repositories.py` |
| Avvisi e destinatari | Import/rettifiche `RuoloAvviso`, soggetti, CF e annualita |
| Policy | Gestori annualita, regole/importi/date in repository Tributi e `tributi_policy_repository.py` |
| Registro | Storici, collegamenti, evidenze, notifica e STEP in `notice_register.py` |
| Invii | `notice_attempts.py`, import Poste e raccomandate legacy |
| Riconciliazioni | Import, conflitti, riconciliazione e annullamento relativi servizi `notice_*` |
| inCASS | Writer di `AnagraficaPaymentNotice`, inclusi aggiornamenti/import fuori Ruolo |
| Futuro STEP | Publisher pratiche/eventi e collegamenti descritti nel piano STEP |

Il protocollo deve proteggere anche inserimenti e spostamenti di perimetro:
nuovi orfani con CF compatibile bloccano; un collegamento cambiato coinvolge
origine e destinazione; policy comuni possono coinvolgere piu annualita.
Le chiavi di invalidazione non costituiscono regole di matching automatico.

Occorre definire un ordine unico dei lock e revisioni monotone delle dipendenze,
con aggiornamento nella stessa transazione dei writer. Valutare enforcement DB
per includere bulk SQL/import e non affidarsi soltanto a convenzioni ORM.
La conferma deve osservare dati e revisioni coerenti, non snapshot misti o valori
obsoleti nell'identity map/cache `db.info`. Qualsiasi percorso non censito lascia
il gate di rilascio chiuso. Timeout/deadlock: errore esplicito e rollback,
nessun retry di operazioni esterne.

L'invariante da dimostrare e: un cambiamento rilevante committato prima della
conferma impedisce una conferma obsoleta; una modifica successiva invalida una
conferma non ancora utilizzata nella stessa transazione del writer.
Non promettere che un file gia scaricato o un invio remoto gia accettato possano
essere revocati atomicamente dal database GAIA.

## Tranche Revisionabili

1. Passaggio bozza/conferma approvato; completare la semantica di emissione e
   revisione dei numeri nella tranche di conferma.
2. Persistenza privata e generazione senza export implementate nelle route
   esistenti protette; download legacy protetti. Anteprima marcata ancora da fare.
3. Implementare il protocollo di conferma e tutti i writer censiti, verificando
   un perimetro alla volta ma senza abilitare conferma/export parzialmente.
4. Integrare UI di revisione/conferma/invalidation e download controllato;
   mantenere invio Poste disabilitato fino alla relativa implementazione.

Non applicare lock globali durante rendering o rete come correzione rapida.
Non dichiarare conclusa la generazione sicura dopo la sola tranche bozze.

## Verifiche Richieste

La suite PostgreSQL `test_notice_generation_concurrency.py` verifica entrambe
le annualita e tre fasi: prima della generazione, durante rendering e dopo
persistenza prima del commit. Usa pagamenti, notifica e STEP reali; simula solo
rendering/destinazioni, senza NAS operativo. **36 passed senza xfail** dopo la
tranche bozze: nessuna pubblicazione definitiva, bozze private ammesse soltanto
negli interleaving durante/dopo rendering. Non prova il futuro protocollo di
conferma e non rende automaticamente attuale il contenuto della bozza.

Alla correzione aggiungere: pagamento parziale che modifica il PDF pur lasciando
saldo positivo, nuovi orfani, import Poste/inCASS, cambio policy, riconciliazione,
due generatori sullo stesso perimetro e conflitti a ogni confine di conferma.
Per writer serializzati usare worker/eventi deterministici, non sleep o callback
sincroni che attendono un lock trattenuto dal generatore.

Testare crash rendering/storage/commit, numero riservato, file non accessibili
prima della conferma, nessuna sovrascrittura, invalidazione e tentativi di bypass
via API/download legacy. Test API/UI desktop/mobile/viewer, coverage full-file
100%, ratchet/lint e grafi aggiornati sono gate separati dal test concorrente.

### Evidenze Della Prima Tranche

- Repeat finale: **169 passed**, nessuno skip/xfail, inclusi 36 casi concorrenti
  PostgreSQL e migration upgrade/downgrade con confronto metadata PostgreSQL.
  Verificati fallback DOCX, errori rendering, limiti artefatto, hash/provenienza,
  rollback comune, lotti misti/preview, flag client non autoritativo e download
  legacy con payload incompleto. Nessun accesso NAS o dati operativi.
- Coverage full-file dei cinque runtime toccati: **2016/2016 statement,
  750/750 branch, 100%**, senza nuove esclusioni. Comprende `db/base.py`, modello,
  servizio bozze, generazione e intero repository Tributi. Configurazione isolata
  `coverage --rcfile=/dev/null --branch`, nessuna modifica ai gate repository.
- Lint mirato, formatter dei nuovi file, `make lint-backend BASE_REF=ec5b1375`
  e `git diff --check` passano. Warning JWT delle fixture legacy, non runtime.
- Ratchet mirato e globale contro merge-base `ec5b1375`: passano, `findings: []`.
  Baseline invariata. Repository LOC `3656 -> 3641`, sum cyc `1195 -> 1185`, sum
  cog `1398 -> 1385`; generation LOC `99 -> 102`. Nuovo servizio bozze LOC106,
  max cyc13/cog14, nessuna violation error-level; modello LOC36 dichiarativo.
  Non si rivendica un refactoring di complessita: e una feature con debito legacy
  non peggiorato e download consolidati nella responsabilita di pubblicazione.
- Log `/tmp/gaia-draft-final-tests.log`, report
  `/tmp/gaia-draft-final-coverage.json`, metriche `/tmp/gaia-draft-{before,after}.json`
  e ratchet `/tmp/gaia-draft-{ratchet,global-ratchet}.log`.

Questi risultati non sostituiscono i test ancora necessari per conferma,
invalidation, UI e rilascio. Nessuna migrazione operativa o spedizione eseguita.

## Collegamenti

- [Registro avvisi](REGISTRO_AVVISI_IMPLEMENTAZIONE.md)
- [Import STEP futuro](STEP_IMPORT_IMPLEMENTAZIONE.md)
- [Invio automatico Poste futuro](POSTE_INVIO_AUTOMATICO.md)
