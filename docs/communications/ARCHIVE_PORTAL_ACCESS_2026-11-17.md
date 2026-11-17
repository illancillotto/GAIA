# Accessi ICATASTO dall’archivio nel corpo email/PEC — 17 novembre 2026

Stato: **rilasciato sul CED il 17/11/2026 alle 13:16:22 CET**. Commit applicativo
`b83c4de1f14eedf6e9a216be94eec253789fa015`, pushato su `chore/split-changes-20261109`.
Codice utenza/PIN integrati nel messaggio quando manca lo snapshot documentale.
PDF e dati operativi invariati; nessun invio reale o abilitazione dei trasporti.

## Contratto implementato

- `template_variables(item, db=...)` usa prima lo snapshot cifrato del documento.
  Solo uno snapshot assente, null o `[]` consente il recupero dall’archivio.
- Il recupero riusa `with_portal_access`: CF valido del destinatario, lookup
  canonico per CF e una sola utenza. Nessuna inferenza da nome, recapito o ID
  appartenenti ad altri namespace. Codice e PIN devono essere numerici ASCII,
  massimo 32 caratteri; la decifratura deve riuscire e gli zeri sono preservati.
- Snapshot presenti ma malformati, multipli o corrotti restano esclusi; non
  vengono sostituiti anche se l’archivio contiene un accesso valido. Utenze
  assenti/multiple, chiave assente o accessi archivio invalidi non producono PIN.
- Anteprima e creazione bozza condividono il resolver, per PEC ed email. Il
  campo privato `portal_access_source` restituisce `document`, `archive` oppure
  `unavailable`; la UI spiega quando i dati arrivano dall’archivio e che il PDF
  allegato resta invariato. Le anteprime precedenti senza il campo restano
  compatibili; cambi di sorgente/template e testo manuale azzerano la nota.
- I blocchi ICATASTO condizionali vengono inclusi solo con entrambi i valori;
  le variabili obbligatorie esterne mantengono il blocco della bozza se assenti.
  La disponibilità degli accessi non cambia le regole di invio o i template.
- La bozza salva il corpo materializzato nel normale archivio privato. Revisione,
  MIME e worker usano il corpo salvato: cambi successivi dell’archivio non
  sostituiscono codice/PIN revisionati. Il corpo resta modificabile secondo il
  flusso esistente, con invalidazione dell’approvazione. Non si aggiorna lo
  storico e non si ricompongono messaggi già creati.
- PDF, hash, percorso, payload documentale, numero e importi restano invariati.
  La revisione PDF esplicita già esistente è una funzione distinta e non viene
  richiamata per integrare il solo messaggio. I consumer del mapper senza
  sessione DB, incluso quel flusso documentale, conservano la semantica precedente.

Il PIN compare solo nei contenuti privati previsti: nessun nuovo campo pubblico,
log/evento o report di credenziali. L’API di anteprima conserva autenticazione,
permesso manage, `Cache-Control: no-store, private` e divieto di scritture.
L’email rimane di cortesia; prenotazioni, pagamenti, Poste e autorizzazioni
individuali mantengono tutti i controlli precedenti.

## Matrice comportamento → prova

| Comportamento | Prova |
| --- | --- |
| Accessi archivio in anteprima, bozza e MIME; PEC/email; testo e blocchi | `test_archive_portal_access.py::test_archive_access_matches_preview_draft_and_mime_without_changing_pdf` |
| Nessuna scrittura nell’anteprima; PDF byte-identico e payload/percorso intatti; nessuna autorizzazione/job implicito o audit di revisione PDF | Stesso test con SQL osservato, record persistiti e allegato MIME |
| Snapshot assente/null/vuoto, precedenza valida, snapshot corrotto/multiplo/malformato | `test_missing_and_empty_document_snapshots_use_archive_without_mutating_source`, `test_existing_snapshot_has_precedence_and_invalid_snapshots_never_fall_back` |
| Nessun accesso, altro CF, CF invalido, ambiguità, codice/PIN invalidi, ciphertext corrotto anche non ASCII, UTF-8 invalido e chiave assente | `test_unusable_archive_access_stays_hidden_or_blocks_required_fields` |
| Omissione condizionale e variabile esterna obbligatoria ancora bloccante, senza bozza parziale | Stesso test attraverso le API reali |
| Modifica archivio dopo la bozza: revisione, approvazione e worker inviano i dati salvati, PDF incluso; entrambi i canali | `test_worker_sends_reviewed_archive_snapshot_even_after_archive_changes` con adapter SMTP sintetico |
| Provenienza, cambi di selezione e testo manuale | Unit `communications/template-composition.test.tsx` |
| Nota operativa, corpo e hash originario nella bozza, nessuna revisione PDF | Unit `communications/workspace.test.tsx`, PEC ed email |
| Browser reale desktop/mobile, anteprima grafica, link, PDF completo, nessun overflow, bozza senza invio/revisione PDF | `communications-archive-access.spec.ts`, due canali × due viewport |
| Snapshot documentali preesistenti, catalogo, grant, concorrenza, invii e ricevute | Suite Communications completa e contratti portale/PostgreSQL esistenti |

I test usano esclusivamente dati sintetici. SQLAlchemy/API, renderer e MIME
sono reali; solo rete SMTP e perimetri contabili preesistenti sono isolati.
Nessun login al portale o collaudo SMTP/PEC reale è stato eseguito.

## Verifiche finali

Tutte le prove applicative del perimetro passano sul checkout isolato di HEAD
iniziale più questa modifica. I 12 file runtime/test coincidono byte per byte
con quelli del working tree condiviso. Le suite isolate usano dati e credenziali sintetici.

| Controllo | Esito |
| --- | --- |
| Backend Communications completo + portale + PostgreSQL temporaneo dedicato | 397 PASS, zero failure/error/skip |
| Coverage dei tre file backend interi | 100%: 227 statement e 66 branch; zero missing, branch parziali o righe escluse |
| Unit frontend Communications | 112 PASS |
| Coverage dei tre file frontend interi | 100%: 108 statement, 78 branch, 52 funzioni, 67 righe |
| Regressione frontend completa isolata | 5.740 PASS, 370 file |
| E2E Communications sulla build finale di produzione | 29 PASS, zero failure/skip/flaky; quattro nuovi casi archivio |
| Tooling code quality | 270 PASS |
| Lint backend finale, Ruff file del perimetro e formato nuovo test | PASS; il ratchet backend completo comprende 249 file al momento della corsa |
| Typecheck e build produzione finale | PASS |
| Lint frontend | PASS con 35 warning legacy, nessun nuovo warning del perimetro |
| Smoke frontend | 18 PASS |
| Whitespace/diff | PASS |
| Ratchet autorevole del perimetro contro origin/main | FAIL: gli stessi 10 finding del commit iniziale; zero nuovi finding |
| Riproducibilità baseline corrente, senza sincronizzazione | FAIL: `baseline_reproducible_ignoring_timestamp_commit=false` (CLI 1, target Make 2) |

Screenshot desktop/mobile ispezionati: nota archivio leggibile, anteprima
ICATASTO e link presenti, PDF completo e nessun overflow orizzontale. I
runtime finali sono congelati nel manifest e i report restano nella directory
privata `/tmp/gaia-communication-archive-20261117/`. Evidenza versionata priva
di dati personali: [ARCHIVE_PORTAL_ACCESS_2026-11-17.json](evidence/ARCHIVE_PORTAL_ACCESS_2026-11-17.json).

La prima invocazione coverage backend usava nomi di modulo con slash e non
raccoglieva dati: tutti i 391 test passavano, ma quel risultato non certifica
la coverage. La misura è stata corretta con moduli Python puntati e ripetuta
sul codice finale, incluso il caso di ciphertext non ASCII. Nei primi E2E
il nuovo selettore intercettava anche editor nascosti; poi l’osservazione delle
scritture comprendeva l’heartbeat di presenza indipendente. Corretto il solo
test per osservare l’anteprima visibile e le mutazioni Communications. La
corsa finale completa passa senza modifiche applicative per adattarsi al test.
I warning JWT con chiave sintetica corta, runpy dei test CLI e jsdom sulla
navigazione appartengono ai contratti preesistenti; nessuna failure è nascosta.

## Complessità e baseline

Metriche acquisite prima delle modifiche e dopo, senza cambiare soglie, scope,
esclusioni o baseline. È una feature ordinaria, non un hotspot dichiarato
`IMPROVED`.

| Runtime | Max cognitiva/ciclomatica prima → dopo | LOC effettive prima → dopo |
| --- | --- | --- |
| `notice_communication_fields.py` | 15/13 → 15/13 | 65 → 81 |
| `template_composition.py` | 5/5 → 5/5 | 33 → 35 |
| `outbox.py` | 13/11 → 13/11 | 277 → 277 |
| `use-template-composition.ts` | 14/14 → 14/14 | 47 → 47 |
| `workspace-controls.tsx` | 14/14 → 14/14 | 73 → 75 |
| `portal-access-note.tsx` | nuovo, 1/2 | nuovo, 3 |

Nuovi helper `_communication_payload` e `portal_access_source`: 9/8 e 5/5,
senza violation. Perimetro: 70 → 73 callable; zero error, nove warning invariati.
Nessuna metrica di callable preesistente peggiora.

Il ratchet autorevole usa `origin/main`, merge-base
`686e529ee011487e0764b9f91d023be063dbdf55`. Restituisce **10 finding preesistenti**
nei callable `authorization` e `cancel` di `outbox.py`, entrambi invariati nel
ciclo. La stessa invocazione su un worktree pulito di HEAD iniziale
`8f65d353c7ecbf9d055dcecd564b617c6278cf6e` produce gli stessi identici finding.
Il confronto dimostra assenza di nuovi finding, **non un PASS del gate**.
Nessuna sincronizzazione della baseline può essere usata per assorbirli. Il primo tentativo diagnostico di `baseline-verify` globale era terminato con exit 143, senza risultato. La verifica finale completa restituisce `baseline_reproducible_ignoring_timestamp_commit=false` (CLI 1, target Make 2). La baseline corrente non è sincronizzata: dopo il ratchet negativo non è stato eseguito alcun aggiornamento per assorbirne i finding.
Le modifiche concorrenti Network/Tributi e i loro report/baseline sono preservati.

## Graphify finale

Aggiornati con i soli target Make dedicati:
`graphify-ruolo-code`, `graphify-backend`, `graphify-frontend`,
`graphify-ruolo-docs` e `graphify-platform-docs`.
La patch locale `OPENAI_BASE_URL` è applicata; il target backend applica anche
la patch di pruning prevista dal repository. Nessun grafo viene versionato.

Le estrazioni docs usano il modello operativo `gpt-6-luna`: entrambe
completano `chunk 1/1 done`, senza semantic chunk falliti. Ruolo docs:
2.645 nodi/4.780 archi; piattaforma docs: 4.365 nodi/9.318 archi nella corsa
finale iniziale. Le query confermano `portal_access_source`,
`_communication_payload` e la nuova nota di architettura. I grafi codice
backend/frontend omettono soltanto l’HTML oltre 5.000 nodi, secondo il limite
ordinario del tool; JSON e report sono aggiornati.

## Stato operativo e limiti

La versione CED comprende il recupero degli accessi dall’archivio. Il controllo
autenticato in sola lettura sull’avviso oggetto della richiesta conferma
codice/PIN disponibili nel corpo dell’anteprima, provenienza `archive`, PDF
byte-identico, payload/percorso originali e blocchi di spedizione preservati.
Non vengono riportate credenziali o dati personali nelle evidenze versionate.

L’accesso univoco non rimuove prenotazioni o stati di spedizione dell’avviso;
la gestione del Registro rimane necessaria. I conteggi storici del 7 novembre
non sono un censimento corrente degli accessi o degli avvisi eleggibili.

Resta aperto il debito di qualità preesistente: dieci finding identici alla
base e baseline non riproducibile. Non sono emersi nuovi finding o peggioramenti;
il gate formale non viene dichiarato verde e la baseline non è stata aggiornata.
Il rilascio richiesto nel seguito del 17 novembre è limitato ai tre servizi
Communications e mantiene i trasporti disabilitati.

## Verifica delle immagini candidate

Rilascio mirato preparato dalle tre immagini CED attive, preservando sorgenti
e route estranei al perimetro. Backend e worker candidati passano ciascuno
397 test con PostgreSQL sintetico temporaneo, zero failure/error/skip e
coverage 100% dei tre file completi (227 statement, 66 branch).
Il frontend candidato passa tutti i 29 E2E Communications, desktop/mobile.
Configurazioni effettive e immagini precedenti sono conservate per rollback.
L’attivazione è stata eseguita dopo il commit e il push del codice verificato.

## Verifica del rilascio CED

Attivazione completata il 17/11/2026 alle 13:16:22 CET, dal commit `b83c4de1f14eedf6e9a216be94eec253789fa015`.
Release remota: `/opt/gaia/releases/archive-portal-access-20261117`.
Backend, frontend e worker sono healthy sulle immagini identificate
nell’evidenza JSON. Configurazioni effettive, altri container, schema DB,
versioni dei template, catalogo e conteggi Communications risultano preservati.
Il BUILD_ID frontend coincide con quello della candidata collaudata.

I dieci controlli HTTP post-deploy passano: pagine e health 200; endpoint
amministrativi protetti 401 senza autenticazione. I 29 E2E Communications
passano anche sulla build servita dal CED (dati e API sintetici intercettati,
zero failure/skip). La verifica autenticata del caso reale è esclusivamente
in lettura. Nessun messaggio, job o autorizzazione è stato creato; nessuna
migrazione, modifica di credenziali, rigenerazione PDF o invio SMTP/PEC reale.
Monitor ancora `paused=true`, `transport_enabled=false`. Immagini/configurazioni
precedenti e procedura di rollback restano nella directory privata di release.
