# Invio solleciti con Posta Online — 2026-10-28

## Regola

GAIA prepara le bozze di **Raccomandata A/R online** sul conto contrattuale del
Consorzio e poi registra quello che risulta spedito. **INVIA lo preme sempre
l'operatore, a mano, su Poste** (decisione dell'utente del 2026-10-28).

GAIA non chiama mai `inserisciInvii.do`, cioè l'INVIA di Poste:

- non esiste un job, una route o un permesso di invio;
- il worker blocca in rete `inserisciInvii`, `paga`, `carrello`,
  `cancellaArchivio`, `modifica.do` e `hideInvii` in ogni fase, compreso il login;
- c'è un test che lo verifica per ogni fase.

Il contratto `notice_dispatch_contract.py`, pensato per un invio automatico,
resta scollegato. Anche `require_poste_submission_adapter()` continua a
rifiutare ogni invio.

## Procedura operativa

1. Dalla sidebar Ruolo aprire **Invio solleciti** (`/ruolo/tributi/solleciti`).
   Nella scheda «Solleciti generati» aprire un lotto, controllare il PDF con
   **Anteprima avviso** e spuntare **Seleziona per Posta Online**. La selezione
   resta mentre si passa ad altri lotti, fino a 50 solleciti. Scegliere l'account
   Poste da usare, dare un titolo e
   premere **Carica su Poste**: GAIA crea il lotto e apre la scheda «Posta
   Online». In alternativa, nella stessa scheda, «Nuovo lotto» cerca i
   solleciti per nome, codice fiscale o lotto. Il vecchio indirizzo
   `/ruolo/tributi/solleciti/poste` apre direttamente la scheda «Posta Online». GAIA copia il PDF e prende il destinatario dallo
   stesso payload che ha prodotto la lettera: nominativo, indirizzo, CAP,
   comune e provincia.
2. **Verifica indirizzi.** Il worker interroga lo stradario Poste
   (`autocomplete.do`). Accetta un indirizzo solo se via, civico, comune, CAP e
   provincia coincidono con un'unica proposta. In tutti gli altri casi l'avviso
   va in «Indirizzo da rivedere», con le proposte di Poste. Lì l'operatore può
   correggere il destinatario (e GAIA riverifica) oppure usare l'indirizzo
   manuale, che richiede CAP e provincia.
3. **Crea bozze su Poste.** Per ogni avviso il worker:
   - compila «Crea spedizione» con nome `GAIA <numero avviso>`, il PDF, il modulo
     Raccomandata A/R e un solo destinatario;
   - salva lo stato `draft_creating` prima di premere CONTINUA;
   - controlla la bozza in «Verifica e invia».

   Dopo 45 secondi rilegge prezzi e stati. Due bozze fallite di seguito fermano
   il lotto.
4. L'operatore accede con **l'account Poste indicato nel lotto**, apre
   **Verifica e invia** su Posta Online e controlla anteprime,
   destinatari e prezzi. Se tutto è corretto preme **INVIA**.
5. **Controlla Poste.** Il worker rilegge «Verifica e invia» e l'archivio. Per
   ogni bozza che non è più in «Verifica e invia»:
   - **la trova in archivio con il nome GAIA** (una sola spedizione): scarica il
     dettaglio, lo importa tra le raccomandate (`RuoloTributiRegisteredMail`),
     segna l'avviso «Spedito» con il numero di raccomandata e registra un
     tentativo di notifica (`NoticeAttempt`) nel Registro avvisi;
   - **non la trova nell'archivio letto per intero**: l'avviso diventa «Bozza
     scaduta o eliminata» e si può ricreare;
   - **trova più spedizioni con lo stesso nome**: segnala l'anomalia e non
     cambia stato;
   - **non riesce a leggere tutto l'archivio**: non conclude nulla.
6. **Annulla** su un avviso con bozza su Poste richiede l'eliminazione. **Elimina
   bozze annullate** la cancella con l'azione di quella riga (`DeleteInvio(id)`),
   mai con la selezione multipla condivisa del portale, e verifica che sia
   sparita.

La pagina avvisa se in «Verifica e invia» ci sono **bozze che non fanno parte
del lotto**: non è verificato se INVIA spedisca tutte le bozze presenti o solo
quelle selezionate. Segnala anche **bozze doppie**, cioè con lo stesso nome. Le
bozze scadono su Poste dopo 7 giorni, e la pagina mostra la prima scadenza.

## Account Poste e tracciabilità — 2026-11-03

Le credenziali si configurano nella gestione Posta Online esistente. Alla
creazione del lotto è obbligatorio scegliere una credenziale attiva: GAIA
conserva ID, username e nome dell'account e non permette di cambiarlo sul lotto.
La password resta nella gestione credenziali e non compare nelle API dei lotti.
La pagina permette di filtrare i lotti per account; restano i permessi GAIA
esistenti di lettura e gestione, senza introdurre una proprietà privata del lotto.

Ogni verifica indirizzi, caricamento, riconciliazione ed eliminazione usa
esclusivamente l'account associato. Il worker apre una sessione browser separata,
senza riutilizzare cookie o browser CDP condivisi. Un account disattivato, uno
username cambiato o un job incoerente bloccano l'operazione: non si passa a
un'altra credenziale disponibile. Le bozze e l'archivio letti sono quelli
visibili all'account usato su Poste; per vedere le bozze nel portale bisogna
accedere con quell'account. I controlli contro il doppio caricamento dello stesso
avviso restano globali anche fra account diversi.

GAIA distingue il creatore del lotto dall'operatore che avvia il caricamento.
Prima di CONTINUA registra sull'avviso ID e username dell'operatore richiedente
e ID del job. Gli eventi conservano operatore, username al momento dell'evento,
job, stato e data: anche in caso di nuovo tentativo si può ricostruire la storia.
Il dettaglio mostra account, creatore e operatore del caricamento di ogni avviso.
La riconciliazione registra l'operatore che la richiede; questo non identifica
chi ha premuto manualmente INVIA sul portale Poste.
Se l'operatore del caricamento non è più identificabile, il worker blocca
CONTINUA prima di cambiare lo stato dell'avviso.

La migration `20261103_0900`, successiva a `20261028_1500`, aggiunge questi campi
e conserva i lotti storici. Recupera gli username soltanto dagli ID GAIA già
registrati; non deduce account Poste o autore del caricamento. Prima di usare
un lotto storico occorre associargli esplicitamente l'account effettivamente
usato, tramite **Associa account** (permesso di gestione, nessun job in corso).
L'associazione è definitiva e produce un evento di audit.

Per il rilascio occorre distribuire backend, frontend e worker compatibili ed
eseguire la migration prima di riattivare i job. Il rilascio sul CED è stato
completato il 2026-11-03 alle 09:49 CET, release `poste-accounts-20261103`, con
database a `20261103_0900`. Backend, frontend e worker sono sani; le nuove API
sono state verificate con autenticazione e filtro per account. I dati del lotto
storico sono conservati: 1 lotto, 5 avvisi e 39 eventi. È presente una sola
credenziale Poste attiva e il lotto storico resta da associare esplicitamente;
il collaudo sul portale con due account reali resta da eseguire.

Le immagini mantengono configurazione, volumi e sorgenti estranei alla modifica.
Nel worker i moduli condivisi devono essere copiati in `/app/backend/app/`,
mentre nel backend risiedono in `/app/app/`: il pacchetto iniziale del worker è
stato corretto e verificato anche con un import nell'immagine di produzione.
Backup e ricevuta del rilascio sono in
`/opt/gaia/releases/poste-accounts-20261103/`; il ripristino è `rollback.sh`.
Il backend di ripristino include la nuova revisione Alembic, necessaria perché
l'entrypoint esegue `upgrade head`, ma mantiene il codice applicativo precedente.
Il ripristino conserva lo schema additivo e i dati di audit.

Verifica locale della modifica:

- Backend: `pytest tests/ruolo/test_poste_dispatch_*.py`, 75 test superati;
  coverage di righe e branch al 100% sui nove file runtime della modifica.
  Inclusi due account distinti, operatore diverso dal creatore, cambio username,
  credenziale inattiva, job di altro lotto, duplicati tra account, migration
  up/down e conservazione dei dati storici senza attribuzioni dedotte.
- Worker: 21 test del runner superati, coverage di righe e branch al 100% su
  `posta_online_dispatch_runner.py`; inclusi mancata apertura del browser con
  account incoerente e disattivazione di storage state e CDP condivisi.
- Frontend: 89 test nelle quattro suite account, pagina Poste, client API e
  pagina solleciti; coverage statement/branch/funzioni/righe al 100% sui sette
  file runtime interessati. Typecheck ed ESLint mirato superati.
- `make lint-backend BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python`
  superato. Ratchet di complessità contro la baseline del merge-base `main`,
  senza nuove violation o regressioni. La lista dei solleciti candidati ha una
  responsabilità di rendering separata dal form di creazione: `CandidatePicker`
  passa da cognitiva/ciclomatica 13/14 a 10/11, senza cambiare la selezione.
  Non sono stati modificati soglie, esclusioni o motori delle metriche.
- La sincronizzazione globale `make complexity-baseline` è stata rifiutata:
  lo snapshot locale già modificato rispetto a `main` rileva 60 aumenti di
  metriche rispetto al proprio contenuto, pur con ratchet contro `main` verde.
  La baseline preesistente è rimasta invariata; nessun aggiornamento forzato o
  `baseline-repair` è stato applicato. `baseline-verify` non è stato eseguito
  perché la sincronizzazione richiesta prima della verifica non è riuscita.

## Caricamenti concorrenti per account — 2026-11-03

Rilasciato sul CED il 03/11/2026 alle 10:48 CET come `poste-pool-20261103`,
successivamente al rilascio `poste-accounts-20261103`. Il worker esegue fino a tre job di caricamento contemporanei,
ciascuno con un account Poste diverso. Il limite per processo si configura con
`POSTA_ONLINE_MAX_CONCURRENT_ACCOUNTS` (default `3`, intervallo `1–32`), esposto
anche dal servizio Docker Compose `elaborazioni-worker-poste`.

`posta_online_pool.py` gestisce il pool; `posta_online_queue.py` seleziona i job;
`posta_online_leases.py` mantiene lock di sessione PostgreSQL su connessioni
dedicate per tutta la lavorazione, anche attraverso i commit del job. Due
credenziali con lo stesso username normalizzato (spazi esterni rimossi e
confronto senza distinzione maiuscole/minuscole) condividono il lock. I job
successivi dello stesso account aspettano, mentre altri account avanzano;
questo vale anche con più processi worker collegati allo stesso database.
Il limite numerico è per processo, il lock per account è condiviso nel DB.

I job storici di sincronizzazione e test credenziali mantengono l'accesso
esclusivo al portale: attendono la fine dei caricamenti e, mentre lavorano,
impediscono l'avvio di altre sessioni, preservando storage state e CDP legacy.
I caricamenti continuano a usare browser isolati e la credenziale del lotto,
con la tracciabilità GAIA già prevista. Le fasce orarie e i cooldown restano
applicati. Un errore di un job non annulla le altre lavorazioni. Lo stop
ordinario smette di acquisire job e attende quelli attivi, entro il tempo di
arresto del servizio; dopo l'interruzione del processo, la perdita dei lock
consente il recupero dei job rimasti `processing`, senza azzerare quelli di
altri worker ancora attivi. L'INVIA resta manuale sul portale Poste.

Verifiche finali: 90 test worker superati, inclusi sei casi su PostgreSQL 16
dedicato e isolato. Oltre ai due pool, tre account, username duplicati, riga
occupata e perdita della connessione proprietaria, due thread acquisiscono
realmente nello stesso momento: account diversi partono insieme e username
equivalenti non ricevono ownership duplicate. Coverage righe e branch 100%
su pool, coda, lock, runner del processo, runner dei caricamenti e portale
(537 statement, 128 branch). Altri 31 test del worker generale e 30 di
sincronizzazione/cooldown/parsing passano. Arresto e cancellazione provati
con browser simulati; nessun caricamento reale effettuato dai test.

Ratchet contro la baseline del merge-base `main` senza regressioni:
`run_worker` conserva cognitiva `0`, ciclomatica `1`, LOC `6`; i tre nuovi
file non hanno violation error-level (due warning). La baseline locale
preesistente non viene forzata; resta il limite di sincronizzazione globale
descritto nella verifica del rilascio multiaccount sopra.

### Revisione finale, dipendenze e stato del rilascio

Il 03/11 la verifica finale comprende anche le estensioni precedenti ancora
non committate: 105 test frontend con coverage statement/branch/funzioni/righe
100% sui file interessati, typecheck ed ESLint verdi; coverage righe e branch
100% sui 21 file backend/script interessati (2272 statement, 570 branch).
La suite Ruolo estesa ha individuato un test di rigenerazione PDF rimasto
alla firma precedente di `create_lot`, senza credenziale. Il test ora salva
una credenziale esplicita prima del rollback del lotto e continua a verificare
sia il recupero del documento sia il rifiuto se il NAS non è raggiungibile:
l'intero file passa, 17 test. Le altre 76 verifiche della ripetizione mirata
campagna/script/rigenerazione erano già passate. Nessun assert indebolito.
I test PostgreSQL non pertinenti della suite estesa restano saltati in SQLite;
i sei test di concorrenza citati sopra usano invece un database PostgreSQL reale.
La suite completa degli strumenti di qualità passa: 270 test.

L'immagine `gaia-elaborazioni-worker-poste:poste-pool-20261103` è stata prima
preparata sul CED in `/opt/gaia/releases/poste-pool-20261103`, senza riavviare
servizi, poi rilasciata dopo le verifiche. Il runner locale dipende anche da `sister_worker_watchdog.py`, già
versionato ma assente nell'immagine precedente: il primo probe candidato ha
rilevato l'import mancante, risolto includendo questa dipendenza. I suoi 20
test passano con coverage righe/branch 100%. Il pacchetto definitivo contiene
i tre moduli del pool, `worker_runner.py` e il watchdog. Hash di tutte le altre
sorgenti Python invariati, import della candidata e limite `3` verificati,
configurazione conservata salvo la nuova variabile del limite. Nessuna nuova
migrazione. In produzione risultano tre credenziali attive; nessun job attivo
al preflight e il lotto storico richiede ancora associazione esplicita.

La sincronizzazione ordinaria della baseline locale era stata rifiutata con
60 incrementi di metrica, sospendendo commit/push/deploy.
Una seconda verifica ha ricostruito la baseline dal solo codice committato
`686e529e`, in un worktree pulito; `baseline-verify` su quella fotografia passa.
Il confronto delle estensioni correnti con tale fotografia rileva 68 incrementi
su 16 file (51 sul runtime e 17 nei test worker), pur senza nuove violation
error-level. Il gate autorevole sul merge-base di `origin/main` passa perché
la sua fotografia è più vecchia. I risultati sono distinti: il gate verde
non viene presentato come prova che la sincronizzazione sia riuscita.
L'utente ha quindi autorizzato esplicitamente di procedere mantenendo questi
incrementi come debito tecnico tracciato. Il record
`docs/code-quality/debt/POSTE_2026-11-03.json`, ID
`POSTE-20261103-COMPLEXITY`, conserva tutti i 68 confronti prima/dopo, il
perimetro, l'autorizzazione e la revisione prevista entro il 03/12/2026 o alla
prossima modifica dei callable interessati. Nessuna soglia, esclusione o
regola del gate cambia: l'eccezione vale soltanto per gli incrementi elencati.
La sincronizzazione della fotografia finale ha verificato corrispondenza esatta
con questo elenco; `baseline-verify` e ratchet `origin/main` passano. Test e
coverage restano obbligatori. Non si tratta di una deroga per aumenti futuri.

### Rilascio produzione e verifica conclusiva

- Codice committato e pushato nel branch `feature/avvisi-solleciti-2021`, commit
  `a46337a7db3cc95f5e1b431246a950d86b6d3752`. La baseline finale è riproducibile;
  il debito resta nel record esplicito, senza modifica dei gate.
- Alle 10:48:18 CET rilasciato soltanto `gaia-elaborazioni-worker-poste`, immagine
  `gaia-elaborazioni-worker-poste:poste-pool-20261103`. Backend e frontend
  mantengono le immagini del precedente rilascio multiaccount, già attive.
  Gli hotfix e gli altri container del server sono conservati.
- Health worker `healthy`, import runtime PASS e limite effettivo `3`.
  HTTP 200 su `/api/health`, `/login` e `/ruolo/tributi/solleciti/poste`.
  Tutte le sorgenti Python coincidono con la candidata; ambiente, mount,
  limiti, comando e healthcheck coincidono con il precedente container,
  con la sola aggiunta di `POSTA_ONLINE_MAX_CONCURRENT_ACCOUNTS=3`.
- Nessuna migrazione: DB a `20261103_0900`. Tre credenziali attive, zero job
  pendenti/in corso al controllo. Hash delle tabelle lotti, avvisi, eventi e
  job identici prima/dopo; nessun caricamento o invio reale avviato dal deploy.
- Backup delle tabelle Poste in `backup/poste-before.dump`, verificato con
  `pg_restore --list`; rollback pronto in
  `/opt/gaia/releases/poste-pool-20261103/rollback.sh`. Il rollback ripristina
  l'immagine e la configurazione del worker precedente, senza modificare il DB.
- Ricevuta priva di credenziali: `evidence/POSTE_POOL_2026-11-03.json`.
  Configurazioni complete, hash sorgenti e backup restano nella directory
  privata della release sul CED. Manutenzione applicativa sempre disattivata.
- Il push GitHub segnala inoltre quattro alert Dependabot di severità alta
  sul branch predefinito. I manifest delle dipendenze non cambiano in questo
  rilascio; tali alert restano un'attività separata e non sono dichiarati risolti.

| Comportamento | Evidenza pertinente |
| --- | --- |
| Account distinti in parallelo e limite del pool | pool con tre account e quarto in attesa; due pool PostgreSQL |
| Uno stesso username non si sovrappone | credenziali duplicate normalizzate e acquisizioni simultanee PostgreSQL |
| Job occupato non recuperato da un altro worker | lock di sessione, commit intermedi e riga PostgreSQL già bloccata |
| Recovery dopo perdita del proprietario | rilascio della connessione e nuova acquisizione dello stesso job |
| Arresto e cancellazione | completamento del browser attivo e rilascio dei lock anche prima dell'avvio del task |
| Errore isolato | un account fallisce mentre il secondo completa il lavoro |
| Account esplicito e audit | backend multiaccount, richiedente diverso dal creatore, incongruenze respinte prima del browser |
| Indirizzo dell'avviso e PDF | portale comune prima della via e rigenerazione del PDF mancante |

## Stati dell'avviso nel lotto

| Stato | Significato | Uscite |
| --- | --- | --- |
| `address_pending` | da verificare nello stradario | `address_ok`, `address_review` |
| `address_review` | indirizzo da rivedere | correzione → `address_pending`; manuale → `address_ok` |
| `address_ok` | pronto per la bozza | `draft_creating`, `draft_error` |
| `draft_creating` | CONTINUA in corso (salvato prima del clic) | `draft_created`, `draft_priced`, `draft_uncertain` |
| `draft_created` / `draft_priced` | bozza su Poste, in lavorazione o prezzata | `sent`, `draft_missing`, `cancel_requested` |
| `draft_uncertain` | CONTINUA premuto senza bozza visibile | riconciliazione |
| `draft_error` | modulo fallito prima di CONTINUA: nessuna bozza | nuova creazione |
| `draft_missing` | bozza scaduta o eliminata, non spedita | nuova creazione |
| `cancel_requested` | annullato con bozza da eliminare | `cancelled` o `sent` |
| `cancelled` / `sent` | stati finali | — |

Ci sono due vincoli di unicità su `active_key` (nome spedizione) e su
`active_source_key` (sollecito). Un sollecito sta in un solo lotto attivo, e un
sollecito spedito non si può rimettere in un lotto. L'annullamento libera il
sollecito. Il PDF copiato viene cancellato alla spedizione o all'annullamento;
resta il suo SHA-256. Prima del caricamento GAIA ricalcola l'hash: un PDF
alterato non viene caricato.

## Componenti

- Backend `backend/app/modules/ruolo/`:
  - `poste_dispatch_models.py`: lotti, avvisi, eventi append-only; migration
    `20261028_1500`;
  - `poste_dispatch_schemas.py`, `routes/poste_dispatch_routes.py`;
  - `services/poste_dispatch.py`: comandi dell'operatore;
  - `services/poste_dispatch_state.py`: transizioni e audit;
  - `services/poste_dispatch_work.py`: esiti riportati dal worker;
  - `services/poste_dispatch_reconcile.py`: archivio e Registro;
  - `services/poste_dispatch_recipient.py`, `services/poste_dispatch_address.py`;
  - `services/poste_dispatch_views.py`.
- API `/ruolo/tributi/poste-dispatch`. La lettura richiede `ruolo.tributi.view`;
  i comandi richiedono `ruolo.tributi.manage_status`, lo stesso permesso di
  conferma ed export:

  | Metodo | Percorso | Uso |
  | --- | --- | --- |
  | GET | `/candidates` | solleciti generati in PDF e non in un lotto attivo |
  | GET | `/accounts` | account selezionabili, senza password |
  | GET, POST | `/lots` | elenco filtrabile con `credential_id`; creazione con `credential_id` obbligatorio |
  | GET | `/lots/{id}` | dettaglio del lotto |
  | PUT | `/lots/{id}/account` | associazione definitiva dell'account a un lotto storico |
  | POST | `/lots/{id}/jobs` | operazioni sul portale: `addresses`, `drafts`, `reconcile`, `delete` |
  | PUT | `/lots/{id}/items/{item}/recipient` | correzione del destinatario |
  | POST | `/lots/{id}/items/{item}/manual-address` | indirizzo manuale |
  | POST | `/lots/{id}/items/{item}/cancel` | annullamento |
  | GET | `/lots/{id}/items/{item}/document` | PDF copiato nel lotto |
- Worker `modules/elaborazioni/worker/`:
  - `posta_online_dispatch_portal.py`: guardia di rete e parsing;
  - `posta_online_dispatch.py`: azioni del browser;
  - `posta_online_dispatch_runner.py`: i quattro job.

  I job usano la coda esistente `posta_online_registered_mail_sync_jobs` con
  le modalità `poste_dispatch_*`, smistate da `posta_online_sync._job_runner`.
  Il pool permette account distinti in parallelo e serializza i job dello
  stesso account, mantenendo le fasce orarie. Si può avere un solo job attivo
  per lotto. Un job interrotto viene ripreso dopo aver acquisito il lock
  dell'account: rilegge «Verifica e invia» prima di agire e non ripete CONTINUA
  sugli avvisi in `draft_creating`.
- Frontend:
  - pagina «Invio solleciti» `src/app/ruolo/tributi/solleciti/page.tsx`, con
    le schede «Solleciti generati» e «Posta Online»; `poste/page.tsx` apre la
    seconda;
  - componenti in `src/components/ruolo/poste-dispatch/` (pannello lotti) e
    `src/components/ruolo/solleciti/` (anteprima PDF e selezione,
    `poste-selection.tsx`);
  - client `src/lib/ruolo-poste-dispatch-api.ts`;
  - voce «Invio solleciti» nella sidebar Ruolo, subito dopo Tributi.

## Scelte predefinite e limiti

- **Codice fiscale non compilato.** GAIA non usa ritiro digitale né avviso di
  ricevimento digitale.
- **Opzioni di stampa del portale.** Colore e fronte/retro restano quelli
  predefiniti di Poste: vanno controllati nell'anteprima e nel prezzo prima di
  INVIA. Il lotto lo registra in `postal_options.portal_defaults`.
- **Bollettino TD 896.** Resta da avere da Poste la conferma che accetta il
  bollettino stampato da loro, ed eventualmente a colori.
- **Solo lotti generati.** Entrano solo i solleciti dei lotti «generated» con
  PDF definitivo, che sono quelli usati in produzione. Le bozze private
  2022/2023 confermate passano ancora dall'export ZIP: il manifest dell'export
  dichiara `authorizes_dispatch: false`.
- **Limiti di Poste.** PDF fino a 7 MB, un destinatario per bozza, nome
  spedizione `GAIA <numero avviso>` di massimo 40 caratteri.
- **Collaudato sul portale reale:**
  - creazione ed eliminazione di una bozza con indirizzo dello stradario
    (bozza 12269236, prova del 2026-10-28);
  - lettura dell'archivio e del dettaglio.
- **Non ancora collaudato sul portale reale:**
  - l'**indirizzo manuale**, con i selettori presi dagli script del portale;
  - la cancellazione con `DeleteInvio(id)`.

  Il primo lotto va seguito sul portale.
- **Prima di usare il primo lotto vero.** L'operatore verifica con due bozze di
  prova se INVIA spedisce tutto «Verifica e invia» o solo le bozze selezionate.
- **Rilasciato sul CED il 2026-10-29** (release
  `poste-dispatch-20261029-05fa4a86`, database a `20261028_1500`).
  - Backend, frontend e worker Poste sono stati rilasciati insieme, perché il
    worker precedente non riconosceva i job `poste_dispatch_*`.
  - Il worker usa lo stesso `app/` del backend.
  - Verifiche, ripristino e vincoli sono in `PROGRESS_ruolo.md`, alla voce
    del 2026-10-28.

## Verifiche

- **Backend.** Test in `backend/tests/ruolo/test_poste_dispatch_*.py`:
  servizi, transizioni, riconciliazione reale con il Registro (tentativo e
  tracking), API, permessi, migration up/down. È incluso il caso che ha trovato
  un difetto: un `ValueError` del Registro interrompeva la riconciliazione, e
  ora viene riportato sull'avviso.
- **Worker.** Test in `tests/test_posta_online_dispatch*.py`:
  - guardia per ogni fase;
  - parsing della pagina reale di «Verifica e invia»;
  - azioni del browser con pagina finta;
  - runner: creazione unica, esito incerto, fermata dopo due errori, archivio
    incompleto, cancellazione.
- **Frontend.** `tests/unit/ruolo-poste-dispatch-*.test.ts(x)`,
  `tests/unit/notice-solleciti-page.test.tsx` (anteprima, selezione tra lotti,
  caricamento, errori, limite di 50, permessi) e l'e2e
  `tests/e2e/ruolo-invio-solleciti.spec.ts` a 1440 e 390 px.
- **Coverage e complessità.** Il 100% su runtime nuovi e modificati e i
  risultati dei gate sono riportati in `PROGRESS_ruolo.md`, alla voce del
  2026-10-28.
