# inCASS incrementale: snapshot giornalieri, shadow e active

Introdotto il 2026-11-09. Stato iniziale **off**. Nessuna attivazione sul CED,
nessuna disabilitazione dell'autosync o degli export settimanali.
Audit preliminare: `INCASS_INCREMENTAL_AUDIT_2026-11-09.md`.

## Architettura e confini

Entry point indipendente:
`python -m app.modules.elaborazioni.capacitas.incremental.runner`.
Un singolo download alla volta, slot giornaliero Europe/Rome (default 07),
finestra operativa dell'autosync e credenziale Capacitas dedicata in fascia.
Le istanze incrementali si escludono con un advisory lock PostgreSQL su
connessione dedicata; crash/disconnessione rilasciano il lease. Un job legacy
pending/processing/queued_resume già presente rinvia l'intero tick.

Ricerca avvisi è la sola fonte del diff. Tutti i codici del filtro anno sono
acquisiti, inclusi quelli speciali. Minuta e Registro Bollettini restano
settimanali: non sono equivalenti e Minuta comporta una stored procedure con
polling. Non viene modificato alcun file dell'export storico.

L'acquisizione originale viene salvata con SHA-256 in un volume persistente,
con permessi 0600 e directory 0700, prima di parsing e upload. Il journal
PostgreSQL conserva catalogo atteso, provenienza per anno, hash delle righe,
schema, numero di righe, tentativi e stato. Il diff si calcola nel worker,
senza download da Drive. La promozione richiede anche l'archiviazione su Drive:
se manca, i dati locali restano disponibili, il ciclo resta partial e il
puntatore non avanza. Le operazioni DB di diff, outbox e puntatore sono un
solo commit. Nessuna baseline viene promossa su errore.

Tabelle additive:

| Tabella | Responsabilità |
| --- | --- |
| `incass_incremental_cycles` | snapshot versionato per slot/revisione, originali e righe canoniche, report |
| `incass_incremental_head` | puntatore al ciclo validato e data dell'ultimo audit completo concluso |
| `incass_incremental_changes` | change/job per avviso, old/new, campi cambiati, risultato e dead-letter |

PostgreSQL è preferito ai file JSON per atomicità e recovery transazionale.
Gli originali sono content-addressed nel volume; sono indispensabili insieme
al backup DB. Nessuna retention distruttiva è automatizzata: concordare una
retention tributaria prima di aggiungere pruning, senza eliminare file ancora
referenziati o snapshot necessari ad audit/recovery.

## Installazione senza attivazione

La migration `20261109_1000` è un ramo Alembic additivo dal precedente head
committato `20261103_1200`, con label `incass_incremental`. Le migration
Presenze trovate non committate nel checkout non diventano dipendenze della
feature. Questo comporta più head fino al successivo merge delle migration.
Usare in ambiente candidato `alembic upgrade incass_incremental@head` oppure
`alembic upgrade heads` dopo revisione di **tutti** i rami. Non usare un generico
`upgrade head` con head multipli. Il downgrade del solo ramo elimina le tre
tabelle del journal: esportarne prima le evidenze. Non elimina originali,
Drive o dati tributari eventualmente applicati.

Il file opzionale `compose.incass-incremental.yml` usa il Dockerfile worker
esistente, `.env`, volume `runtime-data` e rete esterna `GAIA_NETWORK_NAME`
(default `gaia_default`). Il profilo non entra nello stack ordinario.
Controllo statico: `docker compose -f compose.incass-incremental.yml config --quiet`.
L'avvio resta un'operazione di rilascio separata, non eseguita da questa change.

## Configurazione

Tutte le variabili seguenti hanno prefisso `INCASS_INCREMENTAL_`.
In CLI esportarle nell'ambiente; Compose le passa da `.env`.

| Suffisso | Default | Significato |
| --- | --- | --- |
| `MODE` | `off` | `off`, `shadow`, `active` |
| `HOUR` | `7` | ora dello slot Europe/Rome |
| `CREDENTIAL_ID` | assente | obbligatoria fuori off; account dedicato |
| `ROOT` | `/runtime-data/incass-incremental` | volume persistente degli originali |
| `MISSING_FRACTION` | `0.05` | oltre la soglia, snapshot invalido; nessuna cancellazione anche sotto soglia |
| `RETRY_SECONDS` | `3600` | ripresa dell'acquisizione partial |
| `MAX_ATTEMPTS` | `3` | massimo tentativi per slot e per change; i client mantengono i propri retry limitati |
| `MAX_JOBS` | `100` | budget di applicazione per tick e limite dell'allowlist bootstrap |
| `HEADER_MAP` | `{}` | JSON intestazione reale → alias del modello; non approva colonne ignote |
| `EMPTY_YEARS` | `[]` | JSON di codici verificati realmente vuoti; un anno prima popolato non può svuotarsi automaticamente |
| `SAMPLE_SIZE` | `0` | numero di invariati verificati ogni giorno; selezione deterministica e ruotata per ciclo |
| `FULL_AUDIT_DAYS` | `0` | periodicità massima dell'audit completo; scadenza dall'ultimo audit interamente riuscito |
| `SCHEMA_VERIFIED` | `false` | attestazione operatore della validazione dello schema live |
| `COVERAGE_VERIFIED` | `false` | attestazione operatore dei criteri di copertura e rollout sotto elencati |
| `MIN_SHADOW_CYCLES` | `7` | giorni shadow distinti validati prima di active, minimo configurabile 2 |
| `ALLOW_NEW` | `false` | consente materializzazione di avvisi nuovi con ownership certa |
| `BOOTSTRAP_KEYS` | `[]` | JSON allowlist di Avviso da recuperare, anche se invariati; non una scansione globale |

In active schema/coverage attestati, campione positivo e periodicità positiva
sono obbligatori; il worker controlla anche i giorni shadow nel journal.
I default 0 per audit/campioni impediscono una periodicità arbitraria in
produzione: scegliere i valori da esperienza shadow, incidenti e carico reale.
I sette giorni di osservazione sono una soglia iniziale di rollout, non una
prova automatica di completezza.

Drive usa `GOOGLE_DRIVE_REFRESH_TOKEN` e i client OAuth già previsti dal
servizio export (`CAPACITAS_RUOLI_EXPORT_DRIVE_FOLDER_ID` per la radice).
Non passare token su argv, non loggarli e non salvarli nel journal. Gestire
rotazione/revoca con `scripts/google_drive_authorize.py` come nel runbook
`CAPACITAS_RUOLI_EXPORT_DRIVE.md`; archiviare i segreti solo nel canale locale
già autorizzato. In caso di revoca ripristinare il token e riprovare il ciclo,
senza eliminare gli originali acquisiti.

## Validazione e chiavi

`Avviso` è la chiave globale coerente con l'unicità esistente del DB.
Anno, lista e codice fiscale sono attributi: cambiare lista è una variazione
sintetica; cambiare anno/ID/identità genera revisione, senza duplicare l'avviso.
Due occorrenze dello stesso avviso, anche identiche o su anni diversi,
invalidano lo snapshot. I codici ruolo speciali restano stringhe: nessuna
conversione automatica a annualità tributaria ordinaria.

Il parser richiede tutte le colonne scritte dall'upsert canonico: ID, Avviso,
Anno, CodFisc, Denominaz, importi, date, stato, lista e recapito; richiede una
sola worksheet, rifiuta formule/errori, colonne sconosciute e conteggi incoerenti.
Sono ignorate righe interamente vuote, inclusa la riga finale Reso con a-capo.
Date normalizzate a giorno Europe/Rome; importi Decimal a centesimi, separatori
italiani e negativi tra parentesi. Gli identificativi restano stringhe:
un numero Avviso/CF/CAP è ammesso solo con maschera Excel esplicita di zeri.
Notazione scientifica, numeri oltre precisione Excel o zeri irreversibilmente
persi sono anomalie; non si inventano identificativi.

Scope o schema diversi dalla baseline richiedono verifica operatore. Non
correggere la baseline con UPDATE manuali per far passare uno snapshot. Per
un cambio legittimo di catalogo/schema serve una procedura di nuova baseline
revisionata, conservando il journal precedente; tale automazione non è inclusa.
Ricerca avvisi non espone nel codice attuale un totale indipendente dalla
lettura del file: conteggio/schema/scope e soglia missing sono controlli, non
una prova assoluta di completezza server. Questa verifica live è obbligatoria
prima dell'attestazione `COVERAGE_VERIFIED`.

## Applicazione e fallback

Il primo snapshot valido costruisce soltanto baseline; l'allowlist bootstrap,
se esplicita, genera unicamente i recuperi selezionati. In shadow le azioni
sono sempre `shadow`, non entrano nel dispatch. Passare ad active non rigioca
automaticamente lo storico shadow: usare una nuova revisione/ciclo ed,
eventualmente, l'allowlist dei soli avvisi con dati mancanti. Rimuovere
`BOOTSTRAP_KEYS` dopo il recupero, per non ripianificarlo ogni giorno.

Le variazioni sintetiche usano parser e `_upsert_payment_notice` correnti,
con conservazione dei payload pesanti. La riconciliazione riusa
`reconcile_subject_ruolo`; non esistono copie della logica tributaria.
Carico, sgravio, annullamento e rateizzazione richiedono recovery prudente.
Riscosso, residuo, stato, date, lista e recapito aggiornano la sintesi; se il
partitario è realmente assente o vuoto, il recovery recupera solo quel preciso
Avviso. I recuperi/audit chiamano dettaglio e partitario per ID, mai
`search_notices` per l'intero soggetto. Se il partitario manca, l'intera
applicazione resta sospesa in dead-letter, senza scritture parziali.

PDF: si conservano documenti e link esistenti e si aggiungono i link del
dettaglio; **nessun download PDF automatico** dal nuovo dispatch. L'eventuale
recupero dei documenti resta ai percorsi canonici esistenti. Il dettaglio nuovo
si fonde con il payload precedente, preservando mailing e partitario non
sostituiti. L'ownership richiede identità fiscale esatta e univoca, validata
dall'auditor canonico: nessun match per nome e nessuna riassegnazione silenziosa.

Ogni change viene applicato insieme alla ricevuta `succeeded` nello stesso
commit. Crash prima del commit annulla entrambi; dopo il commit il replay
non lo seleziona. La riga DB viene bloccata e confrontata con old/new;
una sync ordinaria più recente/divergente blocca il replay, impedendo che una
vecchia coda sovrascriva dati nuovi. Errori di identità e dati vanno in `dead`;
errori transitori restano pending fino al limite. Le anomalie non bloccano
altri avvisi e non espandono la coda in job massivi.

Il fallback resta il normale autosync, che non viene mai disabilitato.
Questo worker non certifica il lease degli scraper legacy non cooperanti:
prima dell'esercizio isolare l'account incrementale e assegnare esplicitamente
credenziali diverse agli altri pool/operatori. Il compose condivide il rate
limiter del runtime, ma il pool export settimanale conserva il proprio file.
Il dispatch ricontrolla i job legacy subito prima dell'upsert, anche dopo
eventuali recuperi pesanti: se un job è partito durante l'acquisizione,
rinvia il change senza consumare tentativi né scrivere dati tributari. Questi
controlli non costituiscono un mutex globale fra tutti i processi legacy.

## Monitoraggio, recovery e rollback

Heartbeat `incass-incremental`; log soltanto stato/categoria errore.
Il report completo vive nel DB, con dati tributari e identificativi: accesso
riservato, non copiarlo in log pubblici. Campi principali: righe per anno,
counts per tipo, planned, campioni/full audit, confronto con sync ordinario,
outbox per stato, completati nel tentativo, latenza e richieste dopo login.
Queste ultime escludono autenticazione e Drive. Le firme pesanti permettono di
segnalare cambiamenti non esposti nell'Excel; non provano una mutazione critica.

Il risparmio `hypothetical_full_refresh_requests_avoided` è un confronto con
due richieste per ogni invariato (dettaglio+partitario), non il risparmio
misurato sull'autosync attuale: il suo default light evita già entrambe.
Per il risparmio reale raccogliere contatori e durata del flusso ordinario
nella stessa finestra e con lo stesso perimetro, includendo costo export,
login, retry, campioni e audit; non attribuire un risparmio live alle fixture.

Query operative prive di payload personali:

```sql
SELECT id, status, attempts, acquired_at FROM incass_incremental_cycles ORDER BY id DESC;
SELECT cycle_id, kind, action, status, count(*) FROM incass_incremental_changes
GROUP BY cycle_id, kind, action, status ORDER BY cycle_id DESC;
SELECT * FROM incass_incremental_head;
```

Ogni ciclo ha ID slot/revisione (`AAAA-MM-GGTHH-NNNN`), acquisizione immutabile
per quella revisione e artefatti `originals/<sha>.xlsx`. Drive usa cartelle
`incremental-<cycle_id>` sotto la radice configurata e nomi contenenti lo SHA.
Retry dopo crash riusa originali/file già caricati. Il manifest Drive attesta
`archived_pending_validation`: lo stato validato autorevole è nel DB, non
nel manifest precedente al commit.

- `partial`: ritentativo automatico dopo RETRY_SECONDS, fino al limite, senza
  riscaricare gli anni acquisiti. Ripristinare Drive/rete se necessario.
- `invalid`: niente nuovo tentativo automatico sugli stessi byte. Diagnosticare
  lo schema/conteggio/identità. Dopo correzione usare `--once --revision N`
  maggiore della revisione precedente per acquisire nuovi originali; non
  sovrascrivere le evidenze. Una diversa mode nello stesso ciclo è rifiutata.
- `failed`: esaurito il budget di tentativi del ciclo; acquisizione e puntatore
  restano separati. Correggere il problema e usare una nuova revisione verificata.
- `dead`: verificare la causa e la fonte in accesso riservato. Preferire un
  nuovo change tramite allowlist dopo soluzione della causa; mai azzerare
  ricevute succeeded o riaprire indiscriminatamente tutta la coda.
- Snapshot vecchio: non può avanzare il puntatore rispetto a uno più recente.
- Stop/rollback: MODE=off e arresto del solo servizio opzionale. L'outbox
  resta consultabile e l'autosync continua. Per annullare dati già applicati
  serve una riconciliazione autorizzata coi servizi canonici; il downgrade
  del journal non è un rollback tributario.

## Promozione shadow → active

Prima di firmare schema/coverage:

1. Validare live a basso carico intestazioni, tipi e conteggi per anni ordinari
   e speciali, vuoti, liste, rateizzazioni e avvisi non riconciliati; verificare
   che export Ricerca non applichi filtri/troncamenti impliciti.
2. Raccogliere almeno MIN_SHADOW_CYCLES giorni distinti validati e risolvere
   tutte le anomalie critiche. Verificare campioni anche di invariati con
   partitario/particelle, inclusi riordini; zero omissioni critiche osservate.
3. Confrontare saldi, stati, partite/particelle e documenti con il processo
   corrente; misurare falsi positivi/negativi su un campione adjudicato, non
   sulle sole righe raw del DB. Provare recovery e crash nell'ambiente candidato.
4. Misurare richieste/tempi e scegliere campione, audit, budget e credenziali
   secondo i risultati. L'audit completo resta dovuto finché tutti i suoi
   change non risultano succeeded.
5. Attivare un canary active con budget basso e ALLOW_NEW=false; bootstrap
   soltanto su allowlist verificata. Mantenere autosync e fallback, monitorare
   dead-letter e riconciliazioni prima di estendere.

Nessuna di queste verifiche live è stata eseguita durante l'implementazione.
