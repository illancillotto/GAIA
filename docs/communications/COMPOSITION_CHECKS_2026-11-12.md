# Composizione avvisi 2021 e controlli di invio

La composizione carica automaticamente l'unico template approvato del canale,
compresi oggetto e testo. Il PDF rimane visibile sotto i campi. I dati mancanti
compaiono come `[Da verificare: campo]`; i motivi che impediscono l'invio sono
mostrati separatamente. La consultazione non crea una comunicazione. La creazione
della bozza continua a richiedere tutti i campi del template anche se l'operatore
modifica il testo.

## Numerazione e Poste

La numerazione inCASS 2021 non richiede una prenotazione GAIA. Sono richiesti la
regola inCASS attiva e un solo avviso collegato, con identita, annualita, numero
archiviato e codice CNC coerenti. Le prenotazioni GAIA mantengono il controllo
esistente sullo stato definitivo.

Gli avvisi riconciliati con Poste sono esclusi da PEC/email: si controllano sia
i tentativi del Registro collegati alla stessa posizione sia i dispatch collegati
al documento o al numero, anche dopo il rilascio della prenotazione attiva.
I controlli sullo storico e sull'eleggibilita restano obbligatori.

## Revisione esplicita del PDF

`GET /communications/ruolo/candidates/{identity}/template-preview` restituisce
`subject`, `body`, `source_sha256`, `missing_variables` e `send_blockers`.

`POST /communications/ruolo/candidates/{identity}/complete-portal-snapshot`
richiede `expected_source_sha256` (64 caratteri esadecimali), modulo Ruolo e
permesso `ruolo.tributi.manage_status`. La UI espone **Crea nuova revisione PDF
con credenziali** quando il template richiede utenza/PIN assenti.

L'operazione e limitata ai PDF definitivi 2021 con identita verificata ed esclusione
Poste applicata. Recupera soltanto un account univoco dall'archivio canonico,
conserva il PIN cifrato nel payload e produce un nuovo PDF con il numero e gli
importi salvati. Prima di associarlo verifica numero, totale e credenziali nel
testo del nuovo file. L'originale rimane disponibile nel percorso precedente;
l'audit conserva percorso, payload e hash originali, e il documento incrementa
la versione. Hash cambiato, credenziali assenti/ambigue/non decifrabili, importi
invalidi o PDF non verificabile causano rifiuto. Non avviene alcun invio.

Le versioni dello stesso numero avviso possono avere importi diversi: non si
sostituisce un PDF importato con un altro documento generato. La revisione usa
esclusivamente il payload del documento selezionato, senza ricalcolo contabile.

## Verifica dei dati 2021

Nell'audit iniziale di 1.199 documenti, fra i generati GAIA non riconciliati con
Poste 106 avevano lo snapshot credenziali e 52 non avevano un account canonico
disponibile. Fra gli importati non riconciliati, 401 avevano un account univoco
recuperabile, 126 nessun account e uno un account ambiguo. Gli ulteriori 513
documenti riconciliati con Poste restano esclusi. Questi numeri precedono la
riconciliazione avviata il 12 novembre; non rappresentano un'autorizzazione di invio.

La riconciliazione usa solo job `poste_dispatch_reconcile`: consulta bozze e
archivio Poste e registra spedizioni gia effettuate. Errori o assenza di risultati
non attestano che l'avviso non sia mai stato spedito e non sbloccano lo storico.

## Rilascio e verifica

Attivato in produzione il 12 novembre 2026 alle **12:42 CET**, senza migrazioni:
backend `16b671c26a72`, frontend `9d05c9c19a1b`. Preservati configurazione,
template, 196 route frontend e container dei worker. Trasporti Communications
disabilitati e in pausa; nessuna comunicazione creata o spedita.

Test sul candidato derivato dai sorgenti di produzione: 276 backend con
PostgreSQL reale, 89 frontend, 18 smoke; coverage statement/branch dei runtime
modificati 100%. Typecheck, lint e style gate passati. Dieci E2E sul canary e
dieci sulla produzione, con API sintetiche intercettate, senza failure o skip.
Il ratchet contro `origin/main` mantiene esattamente 17 finding preesistenti,
riprodotti sul sorgente iniziale: nessun finding aggiunto o peggiorato. Baseline
invariata. Grafi codice backend/frontend/Ruolo aggiornati tramite target dedicati.

L'avviso selezionato `020210012992910`, nella versione importata da Excel, ha
ricevuto la revisione esplicita: totale **6.488,37 EUR**, numero e payload
finanziario invariati, utenza/PIN verificati nel PDF e audit registrato. Originale
conservato, documento versione 2. Il template non segnala piu campi mancanti;
il controllo di invio rileva ancora una prenotazione/spedizione su un canale GAIA.

La riconciliazione Poste e indipendente dal rilascio. Alle 12:44 CET, dei 37 job
avviati due risultavano completati (sette spedizioni esistenti registrate), 15
falliti per errori del portale, quattro in elaborazione e 16 in attesa. I job
restano consultabili in Elaborazioni; questi esiti non certificano uno storico
completo. Evidenze operative nel release directory
`/opt/gaia/releases/composition-checks-20261112/POST_RELEASE.json`.
