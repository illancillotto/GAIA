# Analisi Sync Capacitas

## Scopo

Questo documento descrive cosa sincronizza oggi GAIA da Capacitas, in quali tabelle lo salva e con quale logica applicativa.

Il perimetro analizzato riguarda soprattutto:

- sessione e credenziali Capacitas
- sync live `Terreni`
- sync progressiva `Particelle`
- import `Storico Anagrafico`
- collegamento tra dati live Capacitas e dati consortili locali

## File chiave

- [backend/app/services/elaborazioni_capacitas.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas.py:96)
- [backend/app/modules/elaborazioni/capacitas/session.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/elaborazioni/capacitas/session.py:43)
- [backend/app/modules/elaborazioni/capacitas/apps/involture/client.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/elaborazioni/capacitas/apps/involture/client.py:61)
- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:111)
- [backend/app/services/elaborazioni_capacitas_particelle_sync.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_particelle_sync.py:217)
- [backend/app/services/elaborazioni_capacitas_anagrafica_history.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_anagrafica_history.py:258)
- [backend/app/models/catasto_phase1.py](/home/cbo/CursorProjects/GAIA/backend/app/models/catasto_phase1.py:346)
- [backend/app/models/capacitas.py](/home/cbo/CursorProjects/GAIA/backend/app/models/capacitas.py:11)

## Sintesi architetturale

Capacitas non viene usato come sorgente unica del catasto consortile. Il sistema lo usa come sorgente live di arricchimento e di verifica contestuale.

La distinzione principale e questa:

- i dati consortili operativi di base stanno in `cat_utenze_irrigue` e `cat_particelle`
- Capacitas aggiunge snapshot live, relazioni di occupazione, certificati, intestatari e storico persona
- il backend prova a collegare il live al locale senza sostituire automaticamente il master locale

## Credenziali e sessione

### Tabelle coinvolte

- `capacitas_credentials`
- `capacitas_terreni_sync_jobs`
- `capacitas_particelle_sync_jobs`
- `capacitas_anagrafica_history_import_jobs`

Riferimenti:

- [backend/app/models/capacitas.py](/home/cbo/CursorProjects/GAIA/backend/app/models/capacitas.py:11)
- [backend/app/services/elaborazioni_capacitas.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas.py:96)

### Logica

- le password sono cifrate a riposo
- una credenziale puo essere usata solo se `active=true`
- puo essere limitata a una fascia oraria
- se non viene richiesta una credenziale specifica, il backend sceglie la meno usata tra quelle disponibili
- dopo 5 errori consecutivi la credenziale viene disattivata automaticamente

### Sessione SSO

Riferimento:

- [backend/app/modules/elaborazioni/capacitas/session.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/elaborazioni/capacitas/session.py:60)

Passi:

1. login su `sso.servizicapacitas.com`
2. estrazione token di sessione
3. attivazione app, di solito `involture`
4. snapshot cookie app
5. keepalive periodico

Se il token non viene trovato, il login fallisce con diagnostica e artefatti di debug.

## Cosa legge dal live Capacitas

Riferimento:

- [backend/app/modules/elaborazioni/capacitas/apps/involture/client.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/elaborazioni/capacitas/apps/involture/client.py:73)

Le chiamate live principali sono:

- ricerca anagrafica
- lookup frazioni
- lookup sezioni
- lookup fogli
- ricerca terreni
- certificato particella/utenza
- dettaglio terreno
- storico anagrafica
- dettaglio storico anagrafica
- dettaglio anagrafica corrente

Il certificato viene ritentato fino a 3 volte se la risposta e semanticamente invalida o transitoria, con re-login intermedio [client.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/elaborazioni/capacitas/apps/involture/client.py:150).

## Mappa tabella per tabella

### `cat_utenze_irrigue`

Riferimento:

- [backend/app/models/catasto_phase1.py](/home/cbo/CursorProjects/GAIA/backend/app/models/catasto_phase1.py:346)

Ruolo:

- tabella locale operativa delle utenze irrigue
- non viene creata dalla sync live Capacitas
- viene solo usata come target di matching e arricchimento

La sync live la usa per:

- agganciare una riga live a una utenza locale tramite `CCO + comune + frazione + foglio + particella + sub + anno`
- scrivere collegamenti annuali intestatari in `cat_utenza_intestatari`
- collegare occupancies a una utenza locale quando il match e affidabile

### `cat_consorzio_units`

Riferimento:

- [backend/app/models/catasto_phase1.py](/home/cbo/CursorProjects/GAIA/backend/app/models/catasto_phase1.py:433)
- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:1331)

Ruolo:

- rappresenta la “unita consortile” vista dal live Capacitas
- e il ponte tra particella locale e risultati terreni live

Campi importanti:

- `particella_id`
- `comune_id`
- `source_comune_id`
- `source_codice_catastale`
- `source_comune_label`
- `comune_resolution_mode`
- `foglio/particella/subalterno/sezione_catastale`

Logica:

- se esiste gia, viene aggiornata con i riferimenti mancanti
- se non esiste, viene creata
- il sistema mantiene sia il comune sorgente Capacitas sia il comune risolto localmente

### `cat_consorzio_unit_segments`

Riferimento:

- [backend/app/models/catasto_phase1.py](/home/cbo/CursorProjects/GAIA/backend/app/models/catasto_phase1.py:476)
- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:1719)

Ruolo:

- dettaglio segmentato della unit, soprattutto quando il dettaglio terreno espone coordinate di riordino

Logica:

- viene creato solo se il dettaglio terreno contiene `riordino_code`, `riordino_maglia` o `riordino_lotto`
- se mancano, nessun segmento viene creato

### `cat_consorzio_occupancies`

Riferimento:

- [backend/app/models/catasto_phase1.py](/home/cbo/CursorProjects/GAIA/backend/app/models/catasto_phase1.py:504)
- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:1761)

Ruolo:

- rappresenta il fatto che una certa unit e occupata/usata da un certo `CCO` in un certo contesto e periodo

Campi importanti:

- `cco`
- `fra`, `ccs`, `pvc`, `com`
- `utenza_id`
- `valid_from`, `valid_to`
- `is_current`
- `source_type="capacitas_terreni"`

Logica:

- viene creata solo se la riga live ha `CCO`
- viene versionata per anno
- collega, quando possibile, la unit a una `CatUtenzaIrrigua`
- `is_current` deriva da `row_visual_state == "current_black"`

### `cat_capacitas_terreni_rows`

Riferimento:

- [backend/app/models/catasto_phase1.py](/home/cbo/CursorProjects/GAIA/backend/app/models/catasto_phase1.py:542)
- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:151)

Ruolo:

- snapshot raw delle righe tornate dalla ricerca live terreni

Caratteristiche:

- append-only di fatto
- tiene `search_key`, `external_row_id`, `CCO`, contesto territoriale, stato visuale e payload raw
- serve come audit trail e come base di ricostruzione di contesto live

### `cat_capacitas_terreno_details`

Riferimento:

- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:197)

Ruolo:

- snapshot del dettaglio singola riga terreno

Logica:

- opzionale
- viene scaricato solo se `fetch_details=true`

### `cat_capacitas_certificati`

Riferimento:

- [backend/app/models/catasto_phase1.py](/home/cbo/CursorProjects/GAIA/backend/app/models/catasto_phase1.py:575)
- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:230)

Ruolo:

- snapshot del certificato Capacitas per il contesto `CCO/COM/PVC/FRA/CCS`

Logica:

- il certificato non viene identificato dal solo `CCO`
- il backend usa sempre il contesto completo quando disponibile
- se l’ultimo snapshot ha lo stesso contenuto semantico, viene aggiornato e non duplicato
- se il contenuto cambia davvero, viene creato un nuovo snapshot

### `cat_capacitas_intestatari`

Riferimento:

- [backend/app/models/catasto_phase1.py](/home/cbo/CursorProjects/GAIA/backend/app/models/catasto_phase1.py:601)
- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:305)

Ruolo:

- intestatari snapshot letti dal certificato

Logica:

- vengono riscritti a ogni refresh coerente del certificato
- possono avere `subject_id` se il backend e riuscito a riconciliare il soggetto in anagrafica GAIA

### `cat_utenza_intestatari`

Riferimento:

- [backend/app/models/catasto_phase1.py](/home/cbo/CursorProjects/GAIA/backend/app/models/catasto_phase1.py:629)
- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:340)

Ruolo:

- materializzazione annuale del rapporto tra utenza locale e intestatario Capacitas

Logica:

- se lo storico e disponibile, usa la riga di storico per l’anno corretto
- se non lo trova, usa il dato corrente dell’intestatario come fallback
- non spalma gli intestatari su piu utenze se il contesto non identifica un target univoco

## Flusso end-to-end di una particella

### 1. Input

La richiesta parte da:

- sync diretta `terreni`
- batch `terreni`
- sync progressiva `particelle`
- resolver live usato da ricerche/anagrafiche bulk

La richiesta minima contiene:

- comune oppure frazione esplicita
- sezione
- foglio
- particella
- sub opzionale

### 2. Risoluzione frazione

Riferimento:

- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:1257)

Logica:

- cerca le frazioni compatibili col comune
- applica hint per `comune + sezione`
- applica override noti di dominio, come `Terralba/B -> Arborea`
- se piu frazioni risultano valide, fa una ricerca di probe
- se piu frazioni producono risultati reali, il caso e marcato come ambiguo e fermato

### 3. Ricerca terreni live

Riferimento:

- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:111)

Logica:

- esegue `search_terreni`
- se non trova nulla con la sezione, ritenta con sezione vuota
- se non trova nulla del tutto, alza errore

### 4. Risoluzione unit e match col locale

Riferimenti:

- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:1331)
- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:1950)

Logica:

- prova a trovare la particella locale col comune sorgente
- se non la trova, in alcuni casi prova lo swap Arborea/Terralba
- crea o aggiorna `cat_consorzio_units`

### 5. Segmento di riordino

Se il dettaglio terreno contiene metadati di riordino:

- crea o riusa `cat_consorzio_unit_segments`

Se no:

- nessun segmento

### 6. Occupancy

Riferimento:

- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:1761)

Logica:

- crea una occupancy per `unit + segment + CCO + anno`
- prova a collegarla alla `CatUtenzaIrrigua` locale compatibile
- se non trova anno esatto, usa fallback sulla piu recente con stessa geografia

### 7. Snapshot riga terreno

Sempre:

- salva una riga in `cat_capacitas_terreni_rows`

### 8. Certificato

Se la riga live ha contesto completo:

- scarica il certificato
- normalizza il contesto
- aggiorna o crea `cat_capacitas_certificati`

### 9. Intestatari e anagrafica

Riferimenti:

- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:305)
- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:340)

Logica:

- salva gli intestatari snapshot del certificato
- cerca lo storico anagrafico per `IDXANA`
- riconcilia o crea `AnagraficaSubject` e `AnagraficaPerson`
- scrive i link annuali `cat_utenza_intestatari`

## Sync batch terreni

Riferimenti:

- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:387)
- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:1664)

Comportamento:

- processa piu item
- puo usare una policy di throttle e parallelismo
- il parallelismo massimo effettivo e 2 worker
- puo essere rilanciato in job persistito
- traccia progresso item per item

Il job batch terreni e la pipeline piu “grezza”: sincronizza item espliciti richiesti dall’operatore o da altri servizi.

## Sync progressiva particelle

Riferimenti:

- [backend/app/services/elaborazioni_capacitas_particelle_sync.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_particelle_sync.py:217)
- [backend/app/services/elaborazioni_capacitas_particelle_sync.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_particelle_sync.py:314)

Scopo:

- prendere le particelle del catalogo locale e verificare/arricchirle progressivamente via Capacitas

Selezione:

- solo particelle correnti
- non soppresse
- priorita a quelle mai sincronizzate o piu vecchie
- opzionalmente solo quelle “due” oltre una certa finestra temporale

Esiti possibili sulla particella:

- `synced`
- `skipped`
- `failed`
- `anomalia`

Metadati scritti su `cat_particelle`:

- `capacitas_last_sync_at`
- `capacitas_last_sync_status`
- `capacitas_last_sync_error`
- `capacitas_last_sync_job_id`
- eventuale `capacitas_anomaly_type`
- eventuale `capacitas_anomaly_data`

Caso speciale:

- se la particella risulta valida in piu frazioni, viene marcata come anomalia `frazione_ambigua`

## Import storico anagrafico

Riferimenti:

- [backend/app/services/elaborazioni_capacitas_anagrafica_history.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_anagrafica_history.py:258)
- [backend/app/services/elaborazioni_capacitas_anagrafica_history.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_anagrafica_history.py:467)

Scopo:

- arricchire l’anagrafica centrale con lo storico persona proveniente da Capacitas

Input:

- `subject_id` locale oppure `idxana`

Logica:

- se manca `idxana`, prova a ricavarlo da `subject.source_external_id`
- se ancora manca, prova a ricavarlo cercando per codice fiscale su Capacitas
- scarica tutto lo storico
- per ogni riga di storico scarica il dettaglio
- salva snapshot storici come source snapshots della persona

Questo flusso e piu anagrafico che catastale. Non serve a creare occupancies o unit.

## Decisioni di matching piu importanti

### 1. Il contesto del certificato non e il solo CCO

Il sistema tratta come chiave sicura:

- `CCO + COM + PVC + FRA + CCS`

Il solo `CCO` non e considerato abbastanza affidabile per identificare univocamente intestatari e stato certificato.

### 2. La sync live non sostituisce il master locale

Il live arricchisce:

- non riscrive `cat_utenze_irrigue`
- non riscrive automaticamente `cat_particelle`

### 3. Ambiguita frazioni: stop, non scelta arbitraria

Se piu frazioni restituiscono risultati reali:

- il sistema si ferma
- espone anomalia
- non forza un match

### 4. Matching utenza locale: anno esatto prima, fallback recente dopo

Riferimento:

- [backend/app/services/elaborazioni_capacitas_terreni.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:1874)

Ordine:

- prima stessa annualita
- poi stessa geografia con annualita piu recente

### 5. Intestatari annuali: solo se il target utenza e sufficientemente chiaro

Se un certificato puo riferirsi a piu utenze locali compatibili:

- il backend evita di assegnare automaticamente gli intestatari a tutte

## Limiti e rischi attuali

### Rischio 1: dipendenza dal comportamento live di Capacitas

La pipeline dipende da:

- HTML/JSON non ufficiali
- decoder custom
- selector e payload applicativi di Capacitas

Una modifica lato portale puo rompere il recupero.

### Rischio 2: mismatch tra comune sorgente e comune locale

Il codice gestisce alcuni casi noti, ma la risoluzione resta euristica in certe zone, soprattutto su casi storici o alias territoriali.

### Rischio 3: parziale dipendenza dal contesto certificato

Se una riga live non espone tutto il contesto utile, il backend deve essere conservativo. Questo evita errori, ma puo lasciare dati vuoti dove l’operatore si aspetta un intestatario.

### Rischio 4: allineamento storico persona non sempre completo

Se manca `IDXANA` e la ricerca per CF non restituisce un match affidabile:

- il backend non puo importare correttamente lo storico

## Risposta sintetica alla domanda “cosa stiamo sincronizzando?”

Stiamo sincronizzando da Capacitas:

- risultati live di ricerca terreni
- dettagli terreno
- contesti certificato
- certificati
- intestatari del certificato
- storico anagrafico delle persone
- relazioni tra unit consortili, occupazioni live e utenze locali

Non stiamo sincronizzando da Capacitas come sorgente primaria:

- il catalogo base delle utenze irrigue
- il catalogo base delle particelle locali
- la geometria catastale ufficiale del dominio

## Risposta sintetica alla domanda “con quale logica?”

La logica e:

- usare Capacitas come fonte live di verifica e arricchimento
- salvare snapshot tracciabili
- collegare il live al locale solo quando il match e sufficientemente affidabile
- fermarsi davanti alle ambiguita di frazione o contesto
- usare il certificato come sorgente autoritativa per intestatari e stati
- usare lo storico anagrafico per consolidare i soggetti persona in GAIA

