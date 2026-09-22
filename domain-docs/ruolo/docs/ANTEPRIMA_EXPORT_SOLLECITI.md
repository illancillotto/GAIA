# Anteprima E Export Definitivo Dei Solleciti

## Perimetro

Dal 2026-09-22 il workflow dei lotti privati e:

**Genera bozza -> Esamina documento -> Conferma lotto -> Prepara export definitivo -> Scarica ZIP**.

Comprende i lotti 2022/2023 e quelli misti messi integralmente in revisione.
Invio automatico Poste e import operativo STEP restano in standby. Scaricare
uno ZIP non registra una spedizione, una notifica o un affidamento e non
pubblica file sul NAS. I percorsi legacy di download restano chiusi per le
bozze protette.

## Anteprima Documentale

In **Ruolo > Tributi > Solleciti**, aprire un lotto, scegliere **Esamina
documento** e **Carica anteprima PDF**. Il visualizzatore del browser permette
di leggere tutte le pagine; **Apri bozza in una nuova scheda** e disponibile
anche sui dispositivi che non visualizzano PDF incorporati.

- Ogni pagina contiene la dicitura **BOZZA - NON VALIDA PER INVIO**, sia nella
  fascia superiore sia in diagonale. La marcatura e nel PDF, non soltanto nella UI.
- Il documento originale viene letto dallo storage privato SQL, verificato
  tramite SHA-256 e mai restituito direttamente dalla route di anteprima.
- I PDF sono copiati e marcati. I DOCX vengono convertiti con LibreOffice in
  una directory temporanea privata, quindi marcati. Il documento persistito
  non viene modificato e la directory temporanea viene eliminata.
- Limiti: 32 MiB per artefatto originale/conversione e 200 pagine per anteprima.
  PDF cifrati, vuoti, malformati o non convertibili non producono un download
  alternativo dell'originale.
- L'anteprima resta consultabile anche se i dati sono cambiati. E sempre una
  copia di revisione: non certifica l'ammissibilita corrente.

Il permesso richiesto e `ruolo.tributi.view`, oltre all'accesso al modulo.
Le risposte sono `no-store, private`; il browser revoca i blob alla chiusura,
al cambio documento e allo smontaggio del componente.

## Export Definitivo

Solo un operatore con `ruolo.tributi.manage_status` vede **Prepara export
definitivo**, dopo la conferma del lotto. La preparazione consegna gia i byte
al browser; **Scarica ZIP definitivo** salva quella copia sul dispositivo.

Lo ZIP `solleciti-<batch-id>-v1.zip` contiene:

- `avvisi/<draft-id>.pdf` oppure `.docx`: byte esattamente uguali agli originali
  confermati, senza conversione o rigenerazione durante l'export;
- `manifest.json`: versione del formato, lotto, conferma, operatore/data di
  conferma, revisione/data di calcolo, digest di revisione e, per ogni file,
  identificatori, formato, payload e SHA-256;
- `authorizes_dispatch: false`: l'archivio non e un'autorizzazione di invio.

Il formato DOCX segnala il fallback gia avvenuto durante la generazione: non
viene presentato come PDF definitivo. La conversione PDF dell'anteprima non
sostituisce l'originale confermato.

Il backend verifica tutto il lotto, senza export parziali:

1. Acquisisce il protocollo PostgreSQL di revisione prima dei lock sul lotto.
2. Verifica conferma presente, stato, conteggi, origine e completezza delle
   bozze, payload, hash, revisione e data di calcolo corrente.
3. Controlla digest e input della conferma, identita canoniche e numeri
   effettivamente confermati nelle prenotazioni.
4. Prepara lo ZIP fuori dai lock, usando lo snapshot verificato.
5. In una nuova transazione ricontrolla l'intero snapshot sotto il medesimo
   protocollo. Solo allora registra archivio e claim di consegna.
6. Esegue il commit prima di costruire la risposta HTTP con i byte.

Una modifica a pagamenti, notifica, STEP o altra dipendenza prima del claim
blocca la consegna con HTTP 409. Lo stesso accade dopo il cambio della data di
calcolo. Il protocollo assente/incompatibile restituisce 503. Restano i limiti
di revisione gia esistenti: massimo 100 artefatti e 64 MiB complessivi.

`ruolo_notice_generation_exports` conserva un solo archivio per conferma,
con vincolo univoco; il servizio non lo sovrascrive. Retry concorrenti riusano
gli stessi byte. `ruolo_notice_export_claims` registra operatore e timestamp
di ogni consegna autorizzata, compresi i retry. Un claim prova l'autorizzazione
e il tentativo di consegna, non il completamento del salvataggio sul dispositivo.

`ruolo_notice_export_identities` assegna ogni identita canonica a un solo
archivio. Una rigenerazione puo sostituire una conferma non ancora esportata;
non puo emettere di nuovo lo stesso avviso da un altro lotto dopo un export.
In quel caso il messaggio richiede una rettifica esplicita: il workflow di
rettifica di documenti gia consegnati non e introdotto da questa funzionalita.

Ogni nuova richiesta ricontrolla la revisione anche se lo ZIP esiste gia.
Un cambiamento successivo al claim non puo revocare i byte gia consegnati:
l'archivio rimane per audit e nuove richieste obsolete vengono bloccate.
Non viene promesso rollback di file gia scaricati.

## API

| Metodo | Route relativa a `/ruolo/tributi/solleciti/batches` | Permesso |
| --- | --- | --- |
| GET | `/{batch_id}/items/{item_id}/preview` | `ruolo.tributi.view` |
| POST | `/{batch_id}/export` | `ruolo.tributi.manage_status` |

La prima restituisce un PDF marcato; la seconda uno ZIP. Entrambe richiedono
autenticazione e modulo Ruolo. Non ci sono URL pubblici, token in query string
o chiamate a provider esterni. Un GET sull'export non crea claim.

## Installazione

- Applicare la migration `20260922_1000_notice_generation_exports.py` prima di
  utilizzare l'export. La catena segue `20260922_0900`, gia presente nel
  commit `f44f38e8` per Presenze, mantenendo una sola head Alembic.
- PostgreSQL deve avere il protocollo di revisione `20260921_1700` integro;
  SQLite non puo autorizzare l'export.
- LibreOffice e richiesto solo per le anteprime DOCX, ed e gia incluso nel
  Dockerfile backend. Un'installazione priva del convertitore restituisce un
  errore esplicito, senza esporre il DOCX originale come anteprima.
- Archivi e bozze occupano storage SQL; dimensionare database e backup. Questa
  funzionalita non introduce una copia NAS o un job di pulizia degli archivi.

Nessuna migrazione o operazione su dati operativi viene eseguita dal collaudo
automatico: si usano schemi PostgreSQL temporanei e documenti sintetici.

## Collaudo Operatore

1. Usare un lotto piccolo con PDF e un lotto generato con fallback DOCX.
   Aprire tutte le anteprime e verificare destinatario, annualita, importi,
   numero e contenuto delle pagine. Anche il PDF aperto separatamente deve
   riportare la marcatura su ogni pagina.
2. Confermare un lotto valido, preparare e scaricare lo ZIP. Verificare che
   contenga tutti gli avvisi e il manifest e che gli originali siano leggibili.
3. Ripetere la preparazione: stesso contenuto archivio, nessun duplicato di
   emissione e un nuovo evento di consegna nell'audit.
4. Su un diverso lotto confermato, registrare un pagamento o una modifica
   documentata a notifica/STEP, poi tentare l'export: deve essere rifiutato
   chiedendo una nuova generazione, senza ZIP parziale.
5. Ripetere con un utente in sola lettura: anteprime consultabili, nessun
   comando di conferma/export. Provare anche accesso senza modulo/permesso.
6. Ripetere su desktop e telefono. Sul telefono usare il collegamento alla
   nuova scheda se il browser non supporta il visualizzatore incorporato.

## Evidenze Tecniche

Suite dedicate: `test_notice_export.py`, `test_notice_preview.py`,
`test_notice_document_api.py`, `test_notice_export_migration.py`,
`notice-document-access.test.tsx` e `ruolo-solleciti.spec.ts`.
La regressione include conferma, input delle bozze e migration precedenti.
Le prove concorrenti usano PostgreSQL reale; il browser usa API simulate.

Verifica finale 2026-09-22:

- Backend: **172 test passati**, senza skip/xfail, PostgreSQL 16 temporaneo;
  incluso smoke DOCX con LibreOffice reale e round-trip delle migration.
  Coverage full-file dei sei runtime coinvolti: **385/385 statement e 86/86
  branch (100%)**. Log `/tmp/gaia-notice-export-coverage-tests.log`, report
  `/tmp/gaia-notice-export-coverage.json`.
- Frontend: **33 test passati**, coverage dei due runtime **108/108 statement,
  109/109 branch, 33/33 funzioni, 81/81 righe (100%)**. Report in
  `/tmp/gaia-notice-export-frontend-coverage`.
- Browser: **2 test passati** a 1440px e 390px, con Chromium completo per
  verificare anche il visualizzatore PDF nativo, oltre al download e agli
  errori. Nessun overflow o errore di pagina. Il PDF sintetico e marcato;
  screenshot `/tmp/gaia-solleciti-preview-*.png`.
- Typecheck TypeScript, ESLint mirato, Ruff check/format dei nuovi file,
  `make lint-backend` e `git diff --check` passati. Unica head Alembic
  `20260922_1000`. Le fixture JWT legacy producono warning sulla chiave breve.
- Quality ratchet sugli otto runtime contro `main@f2fdcabc`: `findings: []`.
  Massimi legacy cyclomatic/cognitive invariati: `notice_draft_review.py`
  **13/17 -> 13/17**, workspace Solleciti **14/20 -> 14/20**; LOC workspace
  **125 -> 123**. Nuovi servizi: export max **11/14**, preview **7/7**;
  nuove route **5/7**, nuova UI **6/6**. Nessun errore di complessita;
  restano 13 warning sul perimetro complessivo. Report prima/dopo in
  `/tmp/gaia-notice-export-{before,after}.json`.
- Baseline versionata ed esclusioni invariate per preservare le modifiche
  Presenze concorrenti. Snapshot finale dei soli otto runtime riproducibile
  con `baseline-verify` in `/tmp/gaia-notice-export-release-baseline.json`;
  non sostituisce il ratchet autorevole sul merge-base.
- Grafi Ruolo/backend/frontend e documentazione di dominio aggiornati con i
  target Make. Estratti semantici docs completati, senza chunk falliti.

Ripetizione del collaudo del 2026-09-22 sul working tree corrente:

- Backend: **172 test passati**, senza skip/xfail; riconfermato il **100% su
  ciascuno dei sei file runtime**, con 385 statement e 86 branch coperti.
  Log `/tmp/gaia-notice-validation-backend.log`, report
  `/tmp/gaia-notice-validation-coverage.json`.
- Regressione frontend estesa a otto suite: **88 test passati**; riconfermato
  il **100% su entrambi i file runtime** (108 statement, 109 branch,
  33 funzioni e 81 righe). Report
  `/tmp/gaia-notice-validation-frontend-coverage`.
- Browser: **2 test passati**, desktop e mobile; log
  `/tmp/gaia-notice-validation-playwright.log`. Typecheck, ESLint mirato e
  `make lint-backend` con il virtualenv backend nel PATH passati.
- La copertura dichiarata riguarda i file runtime modificati per anteprima
  ed export, non l'intero repository. Nessun deploy o migrazione operativa;
  invio automatico Poste e import operativo STEP restano in standby.

## Preparazione Rilascio

Il commit base e ora `f44f38e8`. Il deploy di main comprende quindi anche
l'aggiornamento Presenze gia committato: non e un rilascio isolato di Ruolo.
Prima del deploy verificare il backup PostgreSQL e lo stato pulito del
checkout remoto. L'entrypoint backend applica le migration all'avvio;
la revisione attesa dopo il rilascio e `20260922_1000`.

Le verifiche locali non sostituiscono gli smoke sul server: controllare
health backend/frontend, revisione Alembic e disponibilita delle nuove route.
Non creare export definitivi su dati operativi come semplice smoke test,
perche registrano identita emesse e claim di consegna.
