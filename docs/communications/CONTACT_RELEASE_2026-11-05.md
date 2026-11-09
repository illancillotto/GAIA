# Registro recapiti in produzione — 5 novembre 2026

## Risultato operativo

Rilascio autorizzato dall'utente, concluso alle **08:34:24 CET** sul CED.
Backend e worker Communications healthy. Frontend, worker Posta Online e gli
altri 50 container preservati. I limiti dispositivi della release precedente
sono conservati: il file di autenticazione delle immagini base è immutato.

Dopo classificazione e verifica HTTP autenticata, il filtro Presente restituisce:

| Canale | Righe avviso 2021 | Anagrafiche con recapito risolto |
| --- | ---: | ---: |
| PEC | 47 | 41 |
| Email ordinaria | 1 | 1 |

I precedenti 17 erano righe risolte dal solo `ana_companies.email_pec`.
Il nuovo resolver usa il registro Utenze per persone fisiche e aziende.
I conteggi non attestano eleggibilità, notificazione o raggiungibilità delle
caselle; i lotti possono ripetere gli avvisi.

**Nessun invio eseguito.** Trasporti disabilitati, pausa globale attiva,
zero account, messaggi e job. La disponibilità del registro e della preview
non rappresenta abilitazione delle caselle reali.

## Artefatti e schema

Directory protetta CED:
`/opt/gaia/releases/communications-contacts-20261105-2`.

- Backend: `70672b06113b`; base effettiva `device-limits-20261105`.
- Worker: `2879ad8d18a9`; base effettiva Communications del 4 novembre.
- Migrazione applicata: `20261104_1400`, parent `20261103_1200`.
- Otto file Python per immagine: resolver e admin Communications,
  cinque file del dominio Utenze, registrazione ORM. Aggiunta la migrazione.
- L'integrazione di `app/db/base.py` aggiunge soltanto l'import del nuovo
  modello al file presente in ciascuna immagine. Non copia le registrazioni
  di altri componenti del checkout non ancora rilasciati.
- Confronto integrale sorgenti: 977 file backend e 972 file worker preservati.
- Variabili, mount, entrypoint, utenti, healthcheck, limiti e reti dei due
  servizi invariati. Nessun aggiornamento globale del checkout CED.
- Worker: nuovo `SELECT` sulla sola tabella `ana_electronic_contacts`.
  Verificati sul clone e con la connessione effettiva del worker i divieti
  INSERT, UPDATE e DELETE.

## Dati e audit

Snapshot riacquisito dal CED il 5 novembre. File Excel confrontato con SHA-256
`466db773a49346c6baa5c1122adc20b5d9306effab084bb7d021b99d4183cca3`.

Persistiti **256 record e 256 audit**, in una sola transazione:

| Classificazione | Record |
| --- | ---: |
| PEC attiva documentata | 41 |
| Email attiva documentata | 1 |
| PEC in revisione | 11 |
| Email in revisione | 7 |
| Non classificato / revisione | 195 |
| PEC revocata | 1 |

Il piano validato comprende 252 indirizzi. Altri quattro valori storici
sintatticamente invalidi sono registrati esclusivamente come
`unclassified/review`, fonte `legacy_invalid_quarantine`: la loro presenza
impedisce il fallback sul medesimo valore storico. La quarantena non corregge
l'indirizzo, non lo rende utilizzabile e non modifica l'API pubblica, che
continua a rifiutare tali input con 422. Il servizio interno conserva il valore
per revisione, con audit e riferimento al batch autorizzato.

Il confronto post-rilascio verifica invariati i campi email/PEC originali di
**984 anagrafiche**. Nessuna scrittura su importi tributari, documenti inviati,
evidenze inCASS o prenotazioni Poste. I 14 soggetti discordanti sono sospesi per
revisione, senza sostituzione automatica del loro recapito. Restano 738
anagrafiche senza recapito disponibile nel perimetro consultato.

L'operazione automatizzata usa `changed_by_user_id=NULL`, senza impersonare
un operatore. Provenienza, motivo e `batch contacts-20261105` sono registrati
negli audit. Una classificazione da fonte non è una nuova approvazione umana.

## Verifiche realmente eseguite

| Controllo | Esito |
| --- | --- |
| Suite Communications checkout, con PostgreSQL locale isolato | 177 PASS, zero skip; nove prove PostgreSQL |
| Copertura nove file runtime/migrazione del registro | 407/407 statement e 72/72 branch, zero esclusioni |
| Suite nell'immagine candidata, rete disabilitata | 168 PASS, nove PG skip già eseguiti localmente |
| Suite recapiti con due casi ulteriori di quarantena | 38 PASS, incluse persone e aziende |
| Ratchet completo contro `origin/main` | PASS, zero finding |
| Ruff e `make lint-backend` con interprete del virtualenv | PASS, formattazione dei due test corretta |
| Build immagini backend e worker | PASS, derivate dalle immagini in uso, senza rete |
| Backup schema completo e dati delle tabelle coinvolte | Ripristino in clone isolato PASS |
| Migrazione sul clone, trigger ALWAYS e privilegi worker | PASS |
| HTTP attraverso nginx | Quattro pagine 200, due API anonime 401 |
| GET autenticati backend | Otto endpoint 200, più recapiti admin per persona e azienda |
| Liste backend | PEC 47, email 1; nessun recapito vuoto nelle righe filtrate |
| PDF reale autenticato | Quattro pagine, 742.984 byte, identità dei byte e SHA-256 |
| Connessione worker ristretta | Legge 256 recapiti, resolver funzionante, nessun privilegio di scrittura |
| Report Excel | Conteggi, zeri iniziali, formule, filtri, campi compilabili e rendering verificati |
| Graphify | Backend e Utenze aggiornati con Make; piattaforma docs `chunk 1/1 done`, nessuna semantic failure |

I due nuovi casi verificano che la quarantena preservi il valore storico,
lo escluda dalle liste, registri l'audit e non consenta attivazione tramite
API. Le 38 prove comprendono 36 già presenti nelle 177: sono **179 casi
distinti**, non una nuova esecuzione integrale di 179 casi.

Frontend invariato: nessun nuovo build, type-check o E2E frontend in questo
rilascio. Le verifiche precedenti della preview restano nel report del 4
novembre. Non sono stati ripetuti la regressione generale backend/GIS o i
test con provider reali; il gate generale storico non viene riclassificato.
Due warning runpy preesistenti nella suite completa; la corsa mirata usa
chiavi JWT sintetiche e segnala la loro lunghezza, senza credenziali reali.

## Tentativi preparatori e correzioni

La prima candidata non è stata attivata: la copia integrale della
registrazione ORM importava un modello assente in produzione. Corretto
con integrazione minima sui due file effettivamente in uso.

Primi restore del clone interrotti dalla fase di inizializzazione PostgreSQL
o dalla presenza dello schema PostGIS `topology`: corretti readiness TCP e
preparazione del solo clone. Primo comando Alembic offline senza chiave JWT
sintetica respinto prima di modificare il clone; aggiunta la variabile richiesta.
Primi test dell'immagine privi dei mount delle migrazioni/grant falliti,
poi rieseguiti con il pacchetto completo. Nessuna fixture o prova indebolita.

Le prime due classificazioni hanno annullato integralmente la transazione
perché i quattro valori invalidi sopravvivevano al fallback legacy come email.
La transazione definitiva include la quarantena e verifica 41 PEC / una email
prima del commit. Nessuna scrittura parziale dei tentativi respinti.

Il primo probe worker tramite `docker cp` è stato rifiutato dal filesystem
read-only: il controllo è passato tramite stdin senza allentare i privilegi.
Primo lint generale con interprete esterno al virtualenv non eseguito;
successivo lint ha richiesto formattazione dei due test della change.
I log originali restano nelle evidenze, separati dalle prove conclusive.

## Backup e rollback

Backup nuovi: schema completo 1.285.036 byte e dati delle tabelle coinvolte
14.875.051 byte, checksum e ripristino verificati. Non è un nuovo backup
integrale degli 84 GB del database. Le copie con dati reali restano sul CED,
in directory protetta; nessun artefatto con PII è versionato.

Per rollback applicativo usare il `rollback.json` congelato della release
soltanto per backend e Communications worker; verificare di non sovrascrivere
un rilascio successivo e ricaricare nginx. Lasciare tabella, classificazioni e
audit: il vecchio resolver ignora la tabella. Non eseguire downgrade distruttivi
o ripristini globali del database come semplice rollback applicativo.

## Report per l'ufficio e residui

Report privato, non versionato:
`/home/cbo/Desktop/2021/outputs/gaia-pec-20261105/Report_controllo_PEC_GAIA_2021_20261105.xlsx`.

Tre schede: Riepilogo, Discordanti (14 soggetti / 23 recapiti), Altri controlli
(191 recapiti). Totale 214 recapiti non attivi da esaminare. Campi gialli:
recapito confermato, canale, fonte/data, esito e note. Gli indirizzi senza tipo
documentato non vengono descritti come caselle sicuramente errate. Nessuna
email è stata inviata alla collega.

Restano revisione ufficio dei 14 discordanti, dei quattro valori invalidi,
della revoca e dei recapiti senza classificazione; verifica dei due avvisi Excel
non collegati e della riga senza anagrafica. Configurazione caselle, trust,
template approvati e collaudo autorizzato restano necessari per gli invii reali.

Evidenze locali: `/tmp/gaia-contact-release-20261105/`.
Nessun nuovo commit, push o modifica di baseline in questa sessione.
Working tree preesistente preservato; nessun file PII, report Excel, archivio
di deploy o grafo generato aggiunto al versionamento. Rimossi i soli file
temporanei di questa manutenzione dal container backend dopo le verifiche.
