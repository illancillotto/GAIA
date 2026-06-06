# Product Requirements Document

> Nota repository
> Questo documento descrive il nuovo dominio self-service utente di GAIA.
> Il nome di lavoro del modulo lato runtime e `me`.
> Percorsi canonici target:
> - backend: `backend/app/modules/me/`
> - frontend: `frontend/src/app/me/`

## 1. Visione

GAIA deve esporre a ciascun utente una vista unica e affidabile delle proprie attivita operative, presenze, mezzi utilizzati, km percorsi, segnalazioni aperte o create e dotazioni assegnate.

Il modulo non nasce come semplice pagina profilo, ma come spazio self-service operativo per il lavoratore.

## 2. Problema

Oggi i dati utente esistono gia in GAIA, ma sono frammentati:

- `inaz` contiene giornaliere, timbrature, straordinari, assenze e dettaglio giornata
- `operazioni` contiene attivita, sessioni mezzi, km, carburanti, segnalazioni e pratiche
- `network` contiene dispositivi assegnati all'utente
- alcune viste sono pensate per admin o caposervizio e non per l'utente finale

Questo crea:

- bassa trasparenza per il singolo utente
- difficolta nel ricostruire il proprio lavoro mese per mese
- assenza di un cruscotto personale unico
- sovraccarico amministrativo per richieste informative che potrebbero essere self-service

## 3. Obiettivi MVP

- fornire una dashboard personale unica raggiungibile con route dedicata
- mostrare i dati Inaz del solo utente corrente
- mostrare attivita, km, mezzi usati, segnalazioni e pratiche legate all'utente corrente
- mostrare dotazioni e dispositivi assegnati
- introdurre KPI personali mensili e viste storiche essenziali
- mantenere controlli autorizzativi forti: l'utente vede solo il proprio perimetro

Stato implementazione al 06/06/2026:

- backend `me` attivo e registrato nel router API
- frontend `/me` attivo con tab `Panoramica`, `Presenze`, `Operativita`, `Dotazioni`
- storico rapido disponibile per `mese corrente` e `mese precedente`
- export CSV leggero disponibile per presenze, operativita e dotazioni

## 4. Non Obiettivi MVP

- gestione payroll o cedolini
- modifica massiva di dati Inaz da parte dell'utente
- approvazioni manageriali lato self-service
- esposizione di dati di team o di altri utenti
- scrittura su sistemi esterni Inaz o White Company

## 5. Stakeholder

- operatori sul campo
- impiegati e collaboratori con modulo Inaz
- capiservizio che vogliono ridurre richieste manuali
- amministratori GAIA
- direzione operativa

## 6. Domini Dati Coinvolti

### 6.1 Inaz

Dati gia disponibili e riusabili:

- collaboratore Inaz mappato a `application_users`
- giornaliere con dettaglio giornata
- timbrature
- ore ordinarie
- assenze
- straordinari
- MPE
- richieste e anomalie

Gap attuale:

- per utenti non admin il filtro usa `owner_user_id`, non il mapping `application_user_id`
- questo impedisce una vista self-service coerente

### 6.2 Operazioni

Dati gia disponibili e riusabili:

- attivita con `operator_user_id`
- segnalazioni con `reporter_user_id`
- pratiche assegnate
- sessioni mezzi con `actual_driver_user_id`
- analytics ore e km gia calcolabili

Gap attuale:

- esistono viste amministrative e miniapp personali parziali, ma non un dossier unico per utente
- manca un endpoint aggregato dedicato al profilo utente

### 6.3 Network

Dati gia disponibili e riusabili:

- dispositivi assegnati all'utente
- metadati device
- stato assegnazione

Uso MVP:

- visualizzare le dotazioni digitali personali

## 7. Esperienza Utente Attesa

Il modulo `me` deve essere semplice da capire e diviso in 4 aree principali.

### 7.1 Panoramica

KPI e snapshot del periodo corrente:

- ore lavorate mese
- straordinari mese
- giorni con anomalie
- km percorsi
- mezzi usati
- segnalazioni create
- pratiche assegnate o aperte

### 7.2 Presenze

Vista presenze derivata da `inaz`:

- calendario mensile
- dettaglio giorno
- timbrature
- causali
- straordinari e MPE
- assenze e richieste
- riepilogo mensile

### 7.3 Operativita

Vista operativa derivata da `operazioni`:

- attivita svolte
- tempo per categoria
- mezzi usati
- km percorsi
- segnalazioni effettuate
- pratiche collegate

Stato implementato:

- lista attivita personali
- riepilogo per status e categoria attivita
- lista segnalazioni create
- lista pratiche assegnate
- lista sessioni mezzo con km percorsi

### 7.4 Dotazioni

Vista asset personali:

- dispositivi assegnati
- eventuali dati mezzo correntemente assegnato
- riferimenti operativi utili

Stato implementato:

- dispositivi `network` assegnati all'utente
- assegnazioni mezzi provenienti da `operazioni`

## 8. Requisiti Funzionali

### 8.1 Accesso al modulo

- il modulo deve essere disponibile solo a utenti autenticati attivi
- il modulo deve essere governato da un nuovo flag modulo applicativo dedicato oppure da abilitazione esplicita del modulo `me`
- l'utente vede solo il proprio profilo

### 8.2 Dashboard personale

- vista iniziale con KPI del mese corrente
- widget eventi recenti:
  - ultime timbrature/giornate anomale
  - ultime attivita
  - ultime segnalazioni
- cambio periodo rapido: mese corrente, mese precedente

### 8.3 Presenze Inaz

- elenco o calendario delle giornaliere del periodo
- dettaglio singola giornata
- esposizione di:
  - entrate/uscite
  - ore teoriche
  - ore ordinarie
  - assenze
  - straordinari
  - MPE
  - richieste
  - anomalie
- riepilogo periodo per:
  - totale ordinarie
  - totale straordinari
  - totale assenze
  - giorni lavorati
  - giorni con anomalie

### 8.4 Operativita personale

- elenco attivita filtrato sull'utente corrente
- riepilogo ore da attivita
- elenco mezzi usati nel periodo
- totale km percorsi
- elenco segnalazioni create
- elenco pratiche assegnate o originate da sue segnalazioni

### 8.5 Dotazioni personali

- elenco dispositivi assegnati
- stato assegnazione
- dati minimi del device

### 8.6 Export

MVP opzionale ma raccomandato:

- export riepilogo periodo almeno in CSV
- disponibile per:
  - presenze
  - operativita personale
  - dotazioni

Roadmap successiva:

- valutare export PDF o XLSX server-side

## 9. Requisiti Autorizzativi

### 9.1 Regola base

Tutti gli endpoint self-service devono essere derivati dal `current_user.id`.

Lato backend non devono accettare un `user_id` arbitrario passato dal client per accedere ai dati personali.

### 9.2 Inaz

La vista self-service deve filtrare per `application_user_id == current_user.id`.

Gli endpoint admin esistenti possono restare separati e piu ampi.

### 9.3 Operazioni

La vista self-service deve usare:

- `operator_user_id == current_user.id` per attivita
- `reporter_user_id == current_user.id` per segnalazioni
- `assigned_to_user_id == current_user.id` per pratiche assegnate
- `actual_driver_user_id == current_user.id` o fallback coerente per sessioni mezzo

### 9.4 Network

La vista self-service deve usare:

- `assigned_user_id == current_user.id`

## 10. Requisiti Non Funzionali

- risposta dashboard sotto 2 secondi su dataset ordinario
- endpoint aggregati paginati dove necessario
- riuso massimo delle logiche dominio gia esistenti
- nessuna duplicazione inutile di dati
- audit chiaro per eventuali override o export

## 11. KPI di Prodotto

- riduzione richieste manuali a HR o amministrazione su straordinari e presenze
- aumento utilizzo delle viste self-service
- diminuzione accessi admin per consultazioni individuali
- correttezza mapping utente tra Inaz e Operazioni

## 12. Rischi

- mapping Inaz incompleto o incoerente su parte dei collaboratori
- sessioni mezzi legacy non sempre collegate a `actual_driver_user_id`
- differenza tra ore Inaz e ore Operazioni che puo generare dubbi utente

## 13. Note Implementative Correnti

Endpoint attivi al 06/06/2026:

- `GET /me`
- `GET /me/summary`
- `GET /me/inaz`
- `GET /me/inaz/daily-records`
- `GET /me/inaz/daily-records/{record_id}`
- `GET /me/inaz/summary`
- `GET /me/operazioni/summary`
- `GET /me/operazioni/activities`
- `GET /me/operazioni/reports`
- `GET /me/operazioni/cases`
- `GET /me/operazioni/vehicle-sessions`
- `GET /me/assets/devices`
- `GET /me/assets/vehicle-assignments`

Scelte deliberate:

- nessun `user_id` passato dal client per interrogazioni self-service
- aggregazioni backend guidate da `current_user.id`
- frontend con export CSV client-side per ridurre complessita iniziale
- performance se la dashboard interroga troppe fonti senza aggregazione dedicata

## 13. Roadmap Sintetica

1. fondazioni backend self-service
2. correzione perimetro autorizzativo Inaz
3. API aggregate personali
4. dashboard frontend `/me`
5. tab Presenze
6. tab Operativita
7. tab Dotazioni
8. export e rifiniture
