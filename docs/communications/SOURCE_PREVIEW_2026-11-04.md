# Anteprima immediata avviso — 4 novembre 2026

> Stato successivo: registro recapiti pubblicato il 5 novembre 2026, liste PEC 47 / email 1. Vedere [CONTACT_RELEASE_2026-11-05](CONTACT_RELEASE_2026-11-05.md). Le indicazioni «non rilasciato» sotto descrivono il 4 novembre.

## Comportamento e perimetro

Componi e la checkbox selezionano l'avviso nel pannello destro: i campi restano
in alto, il PDF reale viene caricato e renderizzato sotto, prima della creazione
della bozza. Non occorrono account o template per consultare il documento.
Tutte le pagine devono essere renderizzate prima che Crea bozza sia disponibile.
La scelta di un altro avviso azzera campi, hash e disponibilità del comando;
risposte obsolete vengono ignorate e richieste pendenti annullate.

Il GET autenticato `/communications/ruolo/candidates/{identity}/preview`
richiede modulo Ruolo e permesso `ruolo.tributi.view`, documento generated e
annualità esattamente `[2021]`. Applica le verifiche PDF e i limiti esistenti:
32 MiB, 200 pagine. Restituisce PDF, SHA-256 e numero pagine, private/no-store
con nosniff. Non crea messaggi, job o attestazioni di lettura. Errori 404/409/422
e permessi 401/403 sono coperti da test.

`MessageCreate.expected_source_sha256` è opzionale per compatibilità API;
la UI lo trasmette sempre dalla preview completata. Prima dello snapshot il
backend confronta l'hash e valida il PDF. Un cambiamento restituisce 409 senza
creare la bozza. Lo snapshot rimane immutabile; l'approvazione individuale e la
verifica del documento dello snapshot restano obbligatorie nel workflow esistente.
Non viene attribuito valore di approvazione alla semplice consultazione sorgente.

Il viewer esistente riceve un loader di contenuto, mostra tutte le pagine,
zoom, navigazione e apertura blob autenticata. Ogni rendering riceve una copia
per evitare il trasferimento/detach del buffer da parte di PDF.js. La sorgente
usa `canReview=false`: nessuna POST rendered prima della bozza. Il componente
SourcePreviewActions collega la disponibilità del comando all'hash nel modello
di composizione, senza aggiungere argomenti al comando create.

Dipendenza nuova: `@noble/hashes` 2.0.1, versione e lockfile fissati. Il controllo
SHA-256 di preview e snapshot funziona anche su `http://gaia.lan`, dove Web Crypto
può mancare. Nessun hash fittizio o controllo integrità saltato. La preview
rifiuta dimensione/metadati fuori limite prima del calcolo dell'hash.

## Perché compaiono 17 PEC

La verifica CED in sola lettura trova 1.151 righe di lotto 2021 e 17 righe con
PEC, corrispondenti a 13 anagrafiche. La produzione usa ancora il campo legacy
`ana_companies.email_pec`: non è un limite di pagina o del filtro Presente.
La tabella `ana_electronic_contacts` non esiste ancora sul CED.

Il registro classificato per persone/aziende e l'audit sono implementati e
collaudati nel checkout, descritti in CONTACT_CLASSIFICATION_2026-11-04.md.
Il piano propone 41 soggetti con PEC attiva documentata, proiettati su 47 righe
di lotto. Questi conteggi non indicano avvisi eleggibili né PEC già visibili in
produzione. I 14 discordanti restano ai colleghi; indirizzi non classificati,
revocati o ambigui non vengono promossi in base al solo dominio.

Il rilascio dell'anteprima è distinto dalla migrazione/classificazione recapiti:
non modifica anagrafiche, importi, evidenze inCASS o prenotazioni Posta Online.
Il registro e il relativo piano dati restano da pubblicare in modo coordinato.

## Matrice funzionalità → comportamento → test

| Funzionalità | Comportamento verificato | Test |
| --- | --- | --- |
| GET preview | PDF reale senza account, nessuna bozza/review/job | test_immediate_preview_is_read_only_and_needs_no_account |
| Snapshot | Byte preview e allegato bozza identici | test_preview_bytes_become_identical_immutable_draft_snapshot |
| Documento cambiato | 409, nessuna scrittura messaggio | test_changed_pdf_rejects_draft_without_side_effects |
| Dati invalidi | PDF mancante/invalido, pending, anno diverso | test_missing_invalid_or_nondefinitive_pdf_has_actionable_error |
| RBAC e input | View ammesso, no modulo/sezione/inattivo negati; UUID/hash invalidi | test_preview_permissions_and_missing_identity |
| Integrità client | Auth/no-store, SHA-256 reale senza Web Crypto, pagine/dimensioni, errore rete | source-preview-api.test.ts |
| Lifecycle UI | Loading, rendering completo, retry, errori, abort e risposte obsolete | source-preview.test.tsx |
| Comandi | Componi e checkbox mostrano preview e bloccano bozza fino al rendering | workspace.test.tsx |
| Rendering | Loader sorgente, copia buffer su zoom, nessuna attestazione; navigazione ed errori | pdf-viewer.test.tsx, renderer.test.ts |
| Flusso completo | 3 canvas prima della bozza da entrambi i percorsi; hash comando, checklist, approvazione/invio simulato | communications.spec.ts, PEC/email × desktop/mobile |

## Verifiche e stato operativo

Le evidenze complete sono in `/tmp/gaia-compose-preview-20261104/`, senza PII
nel repository. Primo tentativo PG fallito per URI psycopg2 non installato:
corretto a psycopg3 già richiesto dal progetto, senza aggiungere dipendenze.
Primo build Docker con FROM sha256 non valido fallito prima di qualsiasi
attivazione; ripetuto con tag locale dell'immagine esatta. I log sono conservati.
Un test del limite 32 MiB ha evidenziato il costo di calcolare l'hash prima del
rifiuto: ora i limiti vengono verificati prima, senza allargare timeout o limiti.

Il primo tentativo di sincronizzazione baseline ha rifiutato incrementi LOC,
parametri e complessità della preview. La responsabilità di validazione PDF e
il componente disponibilità/comando sono stati consolidati; nessuna soglia,
esclusione o baseline aggiornata per assorbire regressioni.

| Controllo finale | Esito realmente eseguito |
| --- | --- |
| Suite Communications con registro contatti nel checkout | 177 PASS, zero skip, 9 PostgreSQL reali |
| Pacchetto preview isolato, senza registro contatti | 140 PASS, zero skip, 8 PostgreSQL reali |
| Immagine backend candidata, rete disabilitata | 132 PASS, 8 PG skip: gli stessi 8 eseguiti sopra su PostgreSQL locale |
| Coverage 13 file backend/migrazione del checkout | 818/818 statement, 142/142 branch, nessuna esclusione |
| Coverage 4 file backend del rilascio preview | 411/411 statement, 70/70 branch, nessuna esclusione |
| Test frontend mirati | 54 PASS; 8 file runtime: 229 statement, 144 branch, 73 funzioni, 146 linee, 100% |
| Regressione frontend completa | 351 file, 5.490 test PASS |
| Smoke / type-check / lint del runtime modificato | 18 PASS / PASS / PASS |
| Build pulita locale e immagine CED | PASS; 196 route esistenti preservate |
| E2E Chromium, PEC/email desktop/mobile, API simulate | 4 PASS sulla candidata CED, 4 PASS attraverso nginx di produzione |
| PDF reale 2021 in produzione, GET autenticato | PASS, 4 pagine e 741.710 byte; confronto byte e SHA-256, nessuna attestazione |
| Ratchet completo contro origin/main | PASS, zero finding, baseline del merge-base immutata |
| Baseline candidata, aggiornamento ordinario e riproducibilità | PASS nel checkout isolato del rilascio |
| npm audit --omit=dev | Zero vulnerabilità alla verifica |
| Graphify codice | Backend e frontend aggiornati con target Make; grafi non versionati |
| Graphify documentazione | chunk 1/1 done, zero semantic failure; refresh finale dopo report |

Metriche finali del pacchetto: 12 file runtime, 114 callable, zero violation
error-level. Restano 12 warning preesistenti; massimo Cyc11/Cog14 nel caricamento
PDF, invariato. Nessuna nuova violazione sopra soglia, nessun refactoring esteso.

La baseline generata del rilascio rimane nelle evidenze isolate: differisce dalla
baseline canonica anche su cinque file già committati Presenze/Me, estranei a
questa correzione. Non è stata copiata integralmente nel working tree e non sono
state assorbite modifiche estranee. Il ratchet completo usa comunque la baseline
immutabile del merge-base e passa. Il primo tentativo baseline con incrementi
preview è conservato separatamente e non è stato approvato.

La suite backend generale/GIS storica non è stata rieseguita: il FAIL generale
in FINAL_REVIEW non viene convertito in PASS da queste prove mirate. Restano
i warning runpy dei test worker/health e i warning frontend legacy fuori dal
runtime toccato; nessun warning lint nei file modificati.

## Pubblicazione

Patch pubblicata sul CED alle **16:32:01 CET**, directory protetta
`/opt/gaia/releases/communications-source-preview-20261104-2`.
Backend `92ad33914150`, frontend `f30cb0d7371d`; derivati dalle immagini realmente
in uso. Confronto integrale del codice backend: solo tre file modificati e il
nuovo source_preview.py; 976 file Python preservati. Nessun aggiornamento checkout
CED, migrazione, modifica recapiti/tributi/evidenze o restart dei worker.

Il primo tentativo è stato annullato automaticamente dal guard di configurazione:
Compose ha riordinato la lista Binds. Il rollback ha ripristinato le immagini
precedenti, entrambe healthy. Verificati opzioni e mount effettivi identici,
variabili identiche; il confronto del secondo tentativo normalizza soltanto
l'ordine della lista, preservandone tutti i valori, duplicati e opzioni. Le prove
e il marker ROLLED_BACK del primo tentativo restano nella directory senza -2.

Il secondo tentativo ha preservato configurazioni effettive e identità di tutti
i 50 container estranei; sei pagine HTTP200 e tre API anonime HTTP401; BUILD_ID
identico alla candidata collaudata. Stato DB prima/dopo invariato: revisione
20261103_1200, zero account/messaggi/job, pausa globale true, tabella recapiti
classificati assente. Trasporti backend/worker disabilitati. Nessun invio reale.

Rollback della sola patch: usare rollback.json della directory -2 con Compose
--project-directory /opt/gaia, --no-deps --no-build --pull never, servizi backend
frontend, poi health e nginx -t/reload. Verificare prima che i container siano
ancora quelli di questa release: non ripristinare immagini sopra rilasci successivi
altrui. Non usare --remove-orphans.

## Working tree e residui

Nessun commit/push/merge in questa unità; il rilascio è identificato da immagini,
commit base 2115dd7b, manifest SHA-256 dei 14 file del pacchetto (inclusi package e
lockfile) e prove congelate. Modifiche preesistenti Poste/Presenze/config preservate.
Log, coverage, build e materiale di test rimangono in /tmp o directory protette
CED; nessun grafo o dato personale versionato.

Il registro recapiti, la migrazione 20261104_1400 e il piano di classificazione
restano **non pubblicati**: 17 righe PEC visibili sono tuttora il conteggio legacy.
I 47 risultati del piano sono soltanto una proiezione, da riacquisire prima
dell'applicazione. I 14 discordanti richiedono revisione dei colleghi. Restano
configurazione account, approvazione template e collaudo autorizzato dei provider;
le prove qui descritte non certificano caselle reali o effetti di notifica legale.

Quality gate della correzione preview e del suo rilascio: **PASS**.
