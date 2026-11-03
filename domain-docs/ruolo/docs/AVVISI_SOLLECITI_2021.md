# Avvisi e solleciti 2021

Implementazione sul branch `feature/avvisi-solleciti-2021`, base
`686e529ee011487e0764b9f91d023be063dbdf55`, distribuita in produzione il
02/11/2026 alle 15:01 CET su esplicita richiesta successiva dell'utente. Il file di input
rimane esterno al repository; fixture, anteprime e test usano dati sintetici.

## Audit e riuso della pipeline

Il percorso ordinario parte dal wizard `/ruolo/tributi` e da
`solleciti/year-notices-panel.tsx`, passa dalle route Tributi e da
`year_notice_generation.year_status/generate_missing`, quindi dai candidati e
dall'eligibilita in `notice_candidates.py` e `notice_eligibility.py`.
`tributi_repositories._build_effective_tributi_core` riconcilia il read model
inCASS e le policy; `calculate_adjusted_due` usa base 365. Il ramo rateizzato
preserva gli oneri gia inclusi nel residuo. Draft, conferma nel registro e
autorizzazione Posta Online restano responsabilita separate di
`notice_drafts`, `notice_generation`, `notice_register` e `poste_dispatch`.

Il nuovo adapter 2021 osserva il motore esistente e usa
`generate_batch_reminder_pdf`: nessun secondo generatore, nuovo numero GAIA,
modifica del ledger o della policy 2022–2025. Il riepilogo ordinario resta
identico quando manca `campaign_2021_snapshot`. Solo nel percorso approvato
2021 si aggiungono carico, residuo, differenza F-J e totale prima delle spese.
Le righe gia presenti conservano tributi, maggiorazione, interessi e riscossioni
effettive. Il bollettino riceve il saldo scelto piu le sole spese approvate.

## Workflow e contratti

Pagina `/ruolo/tributi/2021`, raggiungibile dal pannello annualita; filtri per
numero/destinatario, digitale, tipo (inclusi rateizzati e parzialmente saldati),
esito e importi. Base API `/ruolo/tributi/campagna-2021`:

| Metodo e percorso | Effetto |
| --- | --- |
| `POST /analisi` | Parser, lettura dati correnti e report; nessuna importazione |
| `POST /importazioni` | Acquisizione esplicita dopo confronto dell'hash del report |
| `GET /` e `GET /{id}` | Elenco snapshot conservati e dettaglio |
| `POST /{id}/approvazioni` | Snapshot contabile con fonte, canale, spese, motivazioni e operatore |
| `POST /approvazioni/{id}/anteprima` | PDF privato marcato BOZZA, idempotente |

Accesso: modulo Ruolo e sezione `ruolo.tributi.view`; acquisizione,
approvazione e anteprima richiedono anche `ruolo.tributi.manage_status`.
Archivio append-only `ruolo_notice_drafts`, sorgenti `campaign_2021_import`,
`campaign_2021_approval`, `campaign_2021_preview`: nessuna migrazione necessaria.
Nessuna scrittura nel registro di documenti, tentativi o notifiche e nessun invio.

Il match usa il numero inCASS testuale esatto e il corrispondente CNC 2021,
mai un fallback per codice fiscale. Numeri assenti/ambigui, identita discordanti,
contabilita incompleta, saldo non esigibile, posizioni sospese/annullate,
partitario assente e storico/STEP non verificati bloccano l'approvazione.
Un CF invalido richiede revisione esplicita; non genera collegamenti ad altri
soggetti, cartelle NAS o accessi al portale.

Gli scarti contabili richiedono una motivazione per ogni voce. La scelta fra
Excel e GAIA e sempre esplicita, come canale e debenza delle spese: nessun
default amministrativo. Una nota dell'operatore non supera un blocco dati o
storico; correggere/riconciliare la fonte nei flussi autorizzati e riacquisire.
La UI mostra separatamente F-J, totale scelto, spese e totale PDF.

Manifest: SHA-256 Excel, parser, codice, parametri, policy, dati/snapshot per
avviso, esiti, operatore e data/ora. L'unicita delle sorgenti protegge anche
richieste concorrenti. Prima dell'approvazione e dell'anteprima si rileggono
contabilita, destinatario, storico, policy, partitario e STEP. Un cambiamento
richiede nuova acquisizione/approvazione; nessun ricalcolo implicito alla data
del prossimo invio. Le bozze gia prodotte restano identiche a parita di input.

## Quadratura dell'input e audit DB del 02/11/2026

SHA-256 input:
`9a0a5e93ec3fa28ac0dd14124d391c1cfae29dd9f2fe432e190382c9dafd1748`.
942 numeri distinti: 712 ordinari, 230 digitali. Le Note indicano invece
956 (715/241), 34 scarti F-J; la conversazione cita 943. Nel foglio effettivo
gli scarti F-J sono 22. Le Note dicono Carico x 6%, le formule Residuo x 6%.

| Voce | Excel |
| --- | ---: |
| Carico | 321.015,17 |
| Residuo | 313.954,25 |
| Differenza F-J, non incasso verificato | 7.060,92 |
| Maggiorazione | 18.837,30 |
| Interessi | 30.797,60 |
| Totale prima di eventuali spese | 363.589,15 |

Ulteriori anomalie file: 360 somme dei tributi diverse dal carico, 2 CF di un
carattere. Importi calcolati con Decimal e arrotondamento monetario HALF_UP.
Gli interessi Excel usano 5,176%, Euribor 3 mesi, 1369 giorni e base 360;
GAIA usa base 365 e prevede Euribor 6 mesi. La policy 2021 acquisita applica
6%, interessi zero, scadenza configurata 15/12/2026 e numerazione inCASS.
Queste differenze richiedono decisione contabile, non una modifica globale.

Audit sul database tramite transazione `REPEATABLE READ READ ONLY`, verificata
`transaction_read_only=on`. Acquisizione completa 02/11/2026 13:02:01 UTC;
solo letture, nessun aggiornamento dei sistemi produttivi. Risultati:

| Verifica/blocco | Posizioni |
| --- | ---: |
| Match inCASS e Ruolo | 939 |
| Numero inCASS assente | 3 |
| Residuo corrente discordante | 1 |
| Carico Excel/inCASS discordante | 34 |
| Nominativo discordante | 38 |
| Storico precedente verificato insufficiente | 939 |
| Dati di invio inCASS da riconciliare | 939 |
| STEP assegnato o storico ambiguo | 803 |
| Recupero nel registro non liberato | 130 |
| Workflow bloccato o annullamento presente | 23 |
| Saldo non esigibile | 1 |
| Posizioni con importo rateizzato da riconciliare | 23 |
| Generabili senza blocchi o revisioni | 0 |

I conteggi si sovrappongono: non sommarli. Il generico flag di invio inCASS
non dimostra una notifica perfezionata; lo storico deve essere riconciliato
con documenti e riferimenti amministrativi. Le posizioni non reperite non
ricevono importi sostitutivi o collegamenti per CF. I dati nominativi e il
dettaglio per riga sono esclusivamente nell'area privata Desktop/2021 e in
`/tmp/gaia-campaign-2021-20261102`, mai nel repository.

## Validazione e revisione

- Backend: 318 test passati, 3 test PostgreSQL saltati in ambiente SQLite;
  `test_campaign_2021{,_workflow,_pdf}.py` e regressioni di presentazione,
  summary, API Tributi, policy, bollettini, scadenze, destinatari, partitario,
  testi legali, generazione annuale, rigenerazione e TD896. Coverage linee e
  branch 100% su tutti i runtime nuovi/modificati, incluso router e renderer.
- Frontend: `ruolo-campaign-2021.test.tsx` e
  `ruolo-year-notices-panel.test.tsx`: 16 test, coverage 100% di righe, branch,
  funzioni e statement su pagina, client, componenti nuovi e pannello annuale.
  Typecheck, lint mirato Next e ratchet Ruff superati.
- Anteprime sintetiche con/senza interessi: quattro pagine A4; verifica visiva
  delle pagine 1, 2, partitario e bollettino. Pagine 2–4 confrontate con il
  generatore ordinario. Importi/numero approvati verificati nel PDF; nessun
  doppio addebito di spese. Anteprime sempre marcate non valide per invio.
- `make complexity-ratchet`: nessun finding contro il merge-base origin/main.
  Renderer legacy LOC 1772 invariato; `_matched` ciclomatica 15→11 e `_history`
  17→7 durante l'implementazione, nuove responsabilita snapshot partitario e
  verifica delle evidenze incrociate sotto soglia. Nessun hotspot legacy
  rifattorizzato. Baseline sincronizzata solo dopo il ratchet; include anche
  runtime gia committati successivamente alla vecchia fotografia (85 record
  file aggiornati, 65 nuovi; scope/soglie/esclusioni invariati).
  `make complexity-baseline-verify` conferma la riproducibilita della
  fotografia finale. Una prima verifica durante le modifiche agli import
  frontend aveva rilevato drift; ripetuta a sorgenti fermi e passata.
- Grafi codice Ruolo e frontend aggiornati tramite target make dedicati.
  Il grafo frontend supera 5000 nodi: Graphify aggiorna JSON e report e salta
  automaticamente la sola vista HTML.
  Grafi documentali Ruolo e piattaforma aggiornati: `chunk 1/1 done` su
  entrambi, senza warning di fallimento semantico.

Al termine della prima implementazione non era stata eseguita una campagna
produttiva, una conferma definitiva o una validazione normativa. Le operazioni
successivamente autorizzate sono riportate nelle sezioni seguenti. L'audit completo con il read adapter e durato alcuni
minuti; il proxy API configurato ammette 900 secondi. Prima dell'uso operativo
verificare il tempo sul sistema di destinazione e i gate amministrativi.

## File e rollback

Backend: `campaign_2021_schemas.py`, `routes/campaign_2021_routes.py`,
`services/campaign_2021{,_excel,_read_model,_reconciliation,_pdf,_summary}.py`,
registrazione router e chiamata del riepilogo nel renderer condiviso.
Frontend: pagina `tributi/2021`, cartella `components/ruolo/campaign-2021`,
collegamento nel pannello annualita. Test nei percorsi citati sopra.

Il prompt iniziale prevedeva la sola revisione; la successiva richiesta
esplicita dell'utente ha autorizzato il deploy e il controllo dei tre mancanti.
Il rilascio non importa l'Excel e non approva, genera o invia avvisi reali.
Nessun rollback contabile o migrazione necessari. Preservare le modifiche
preesistenti PuntoFisco/configurazione e documenti di altri domini.

## Rilascio produzione del 02/11/2026

Release CED `/opt/gaia/releases/campaign-2021-20261102`, immagini
`gaia-backend:campaign-2021-20261102` e
`gaia-frontend:campaign-2021-20261102`. Aggiornati soltanto backend e frontend;
ambiente, mount, limiti, sorgenti backend estranee e altri container verificati
invariati. Il frontend mantiene le sorgenti della precedente release e aggiunge
la pagina 2021; il renderer conserva anche le dipendenze gia versionate del
layout e dei testi di pagamento.

Sull'immagine candidata: 60 test della campagna, 48 regressioni finali e 6
controlli QR superati. Il primo ambiente delle regressioni mancava di Pillow:
ripetizione finale con immagine QA completa, senza modifiche runtime.
Backend e frontend healthy; HTTP 200 su health, login, Tributi, campagna 2021
e solleciti. Smoke API autenticata 200 e anonima 401; DB in sola lettura,
scadenza policy 15/12/2026 e numerazione inCASS preservate. Generato soltanto
un PDF sintetico BOZZA di quattro pagine, verificati totale e spese.

Manifest di rilascio e hash nel percorso della release. Rollback verificabile
tramite `/opt/gaia/releases/campaign-2021-20261102/rollback.sh`, che ripristina
le immagini precedenti e ricontrolla configurazione, salute e HTTP.

## Verifica dei tre mancanti su Capacitas

Il 02/11/2026, accesso diretto a inCASS con credenziali lette dal DB di
produzione in transazione read-only. Tutti e tre i numeri esatti hanno un solo
risultato Capacitas, con annualita 2021, nominativo e CF corrispondenti all'Excel.
Assenti invece sia da `ana_payment_notices` sia da `ruolo_avvisi` in produzione,
anche dopo ricerca con normalizzazione degli zeri iniziali. L'assenza riguarda
quindi i dati importati in GAIA, non gli avvisi nella fonte Capacitas.

Due posizioni sono non pagate; la terza e rateizzata senza pagamenti, con
carico 281,08 e residuo/importo rateizzato 360,58. Su quest'ultima il carico
Excel 360,58 non coincide con il carico Capacitas: preservare la distinzione
e riconciliare la rateizzazione. Una delle altre posizioni ha CF `M` anche
nella fonte: la revisione dell'identita resta necessaria. Il controllo non
dimostra la causa tecnica dell'omissione dalla sincronizzazione.

Nessuna importazione, modifica anagrafica/contabile, approvazione o invio
eseguiti durante il controllo. Le posizioni restano bloccate nel workflow
finche non sono riconciliati importazione, identita e altri gate previsti.
Dettagli nominativi e numeri esclusivamente nel file privato
`Desktop/2021/Verifica_GAIA_2021/Verifica_Capacitas_3_mancanti.json`.
L'audit ha rispettato il lock, le scadenze e il backoff condivisi Capacitas;
nessuna modifica della configurazione o sospensione degli altri worker.

## Recupero mirato in produzione del 02/11/2026

Su successiva autorizzazione esplicita, nuovo scrape per numero esatto di
tutti e tre gli avvisi, dettaglio e partitario. Nessun PDF collegato nella
fonte. Importati atomicamente tre `ana_payment_notices`, tre avvisi Ruolo,
nove partite e 79 particelle Ruolo, tramite gli helper esistenti. Le
anagrafiche e il Catasto restano invariati; il partitario conserva le
particelle sorgente senza nuovi abbinamenti catastali automatici.

Due destinatari collegati alle anagrafiche esistenti con CF e nominativo
corrispondenti univocamente. La posizione con CF `M` conserva il dato
originale e `subject_id=NULL` sia in inCASS sia in Ruolo: nessun collegamento
ad altri omonimi, nessuna nuova anagrafica con identificativo invalido.
Conservati integralmente carico, residuo, rateizzato, annullato, riscosso,
sgravio e stato della fonte, inclusi gli scarti contabili gia evidenziati.

Prova transazionale con rollback superata prima del commit. Dopo il commit,
verifica da una nuova connessione `REPEATABLE READ READ ONLY`: tre avvisi
univoci, tre header, nove partite e 79 particelle; confronto esatto di raw row,
dettaglio, partitario, destinatari e importi. Il read model della campagna
2021 ora risolve tutti e tre i numeri, senza errori di numero assente.
Rimangono le revisioni di identita, contabilita e storico previste dal flusso.
Nessun avviso approvato, generato o inviato durante il recupero.

Job di importazione dedicato con SHA-256 dello scrape e perimetro dei soli
tre numeri. Artefatti privati, stato prima dell'import, prova con rollback,
manifest del commit e verifica in
`/opt/gaia/releases/campaign-2021-20261102/import-3-notices/`.
Il riepilogo aggiornato e in
`Desktop/2021/Verifica_GAIA_2021/Manifest_importazione_Capacitas_3_avvisi.json`.
Il precedente audit e il CSV di riconciliazione restano fotografie antecedenti
all'importazione; per lo stato del recupero fare riferimento al nuovo manifest.
Nessuna modifica del codice runtime e nessun nuovo deploy necessari.

## PDF finali Excel e controllo conclusivo del 03/11/2026

Le disposizioni successive dell'utente hanno autorizzato la creazione dei PDF
con gli importi Excel e il mantenimento temporaneo degli identificativi fiscali
incongruenti. I PDF finali usano il prospetto ordinario precedente: non riportano
Carico (emesso), Residuo contabile, Differenza F-J o Totale approvato prima delle
spese. Le righe contabili aggiuntive del percorso di anteprima approvata restano
una funzione distinta, attivata da `campaign_2021_snapshot`; il rendering dei
documenti finali Excel è stato eseguito senza tale snapshot. Non si deve usare
la prima versione con queste righe aggiuntive come documento da spedire.

Creati 942 avvisi: 712 ordinari e 230 digitali, con € 11,55 di spese di notifica
su tutti, come espressamente richiesto. Totale prima delle spese € 363.589,15;
spese € 10.880,10; totale con notifica € 374.469,25. Per gli stessi 230 digitali
è disponibile anche la versione PEC senza spese. Il controllo finale Drive
conferma 1172 PDF, hash e dimensioni corrispondenti alle copie locali, nelle
cartelle `Ordinari`, `Digitali_con_spese_Raccomandata` e
`Digitali_senza_spese_PEC`. Il canale va deciso prima del caricamento: le due
versioni digitali sono alternative per lo stesso avviso.

Le correzioni degli indirizzi autorizzate sono state applicate ai dati e ai PDF
interessati; la verifica successiva conferma gli hash di tutti i 1172 documenti
locali, il confronto delle varianti con/senza spese e il controllo CRC dello ZIP
dei 942 avvisi con spese. Manifest nominativi, indirizzi e documenti restano
nell'area privata; non sono inclusi nel repository. La consegna dei PDF non
equivale a una conferma di notifica o a un invio sul portale Poste.

La revisione finale del codice raggiunge coverage righe/branch 100% sui 21 file
backend/script coinvolti nella campagna e nel multiaccount. Il test di
rigenerazione del PDF mancante è stato allineato all'account obbligatorio prima
di creare un lotto, conservando i controlli del caso NAS indisponibile.
Verifiche complete, concorrenza e stato del rilascio del pool Poste sono nel
runbook `POSTE_INVIO_SOLLECITI_2026-10-28.md`: l'immagine è candidata e il rilascio
è autorizzato con gli incrementi di complessità tracciati nel debito tecnico
`POSTE-20261103-COMPLEXITY`. Il
precedente esito di `baseline-verify` della sola campagna non certifica le
estensioni multiaccount successive.
