# GAIA GIS Platform - Protocollo UX Territorio

> Versione: 2026-08-31.
> Durata: 45-60 minuti.
> Scopo: validare con utenti finali i flussi Territorio M21-M25 senza usare lo
> smoke automatico come sostituto della prova osservata.

## Obiettivo

La sessione verifica se due utenti reali comprendono e completano i flussi
Territorio senza istruzioni incorporate nel prodotto:

- un operatore non tecnico con ruolo `viewer`;
- un tecnico GIS con ruolo `admin`.

Il facilitatore osserva e prende note. Non insegna il flusso prima del tentativo
e non suggerisce soluzioni finche l'utente non resta bloccato per almeno 60
secondi. Non si aggiunge un onboarding wizard sulla base di impressioni: ogni
intervento UI successivo deve citare evidenze raccolte con questo protocollo.

## Prerequisiti

- Ambiente di validazione separato dalla produzione.
- `GIS_EXTERNAL_LAYERS_ENABLED=true` e
  `GIS_INTERROGAZIONE_ENABLED=true` solo nell'ambiente della sessione.
- Migration schede applicata, cache proxy scrivibile e health verificato.
- Account `viewer` e `admin` con `module_gis`; entrambi devono avere anche il
  modulo Catasto per i percorsi particella.
- Browser desktop supportato, popup e download consentiti per GAIA.
- Una particella campione autorizzata, identificata da ID, comune, foglio e
  mappale.
- Un punto A dentro la particella, con almeno un risultato GAIA e almeno un
  risultato territoriale noto.
- Un punto B per cui una sonda restituisce legittimamente `empty`.
- Una sorgente C resa intenzionalmente non raggiungibile nello staging, oppure
  sostituita da uno stub controllato, per produrre `failed` senza dipendere da
  un disservizio RAS o AdE reale.
- Almeno un layer RAS vettoriale e l'ortofoto autorizzata `1977-1978` visibili
  al viewer.
- Percorso di salvataggio per PDF, stampa e progetto QGIS.

Registrare prima della sessione ID particella, coordinate A/B, layer attesi,
stato health e versione applicativa. Se una fixture non e ripetibile, fermare
la sessione e correggere il setup: non cambiare le risposte attese durante la
prova.

## Ruoli Nella Sessione

| ruolo | responsabilita |
| --- | --- |
| Partecipante viewer | esegue i compiti operativi senza accesso admin |
| Partecipante admin | esegue i compiti tecnici e il download QGIS |
| Facilitatore | legge le consegne, non guida la soluzione |
| Osservatore | registra tempi, errori, richieste di aiuto e citazioni |

Il facilitatore puo essere anche osservatore. Viewer e admin non devono vedere
le risposte attese prima di completare il proprio percorso.

## Scaletta 45-60 Minuti

### 0-5 Minuti - Apertura

1. Spiegare che si sta valutando l'interfaccia, non la competenza dell'utente.
2. Chiedere al partecipante di pensare ad alta voce.
3. Mostrare soltanto la particella e le coordinate delle fixture.
4. Avviare registrazione schermo solo con consenso; in alternativa usare note
   con timestamp.

Domanda iniziale, senza correggere la risposta: "Che differenza ti aspetti tra
un dato GAIA e uno pubblicato dalla Regione o dall'Agenzia delle Entrate?"

### 5-30 Minuti - Percorso Viewer

Accedere come viewer e aprire `/catasto/gis`.

#### Compito V1 - Strati E Attribuzioni, 5 Minuti

Consegna: "Mostrami sulla mappa un distretto pubblicato dalla Regione e dimmi
chi e la fonte. Poi prova ad attivare l'ortofoto storica."

Osservare senza suggerire:

- se trova il pannello `Territorio`;
- se comprende `solo consultazione`;
- se individua fonte e attribuzione;
- se distingue lo strato RAS dal distretto GAIA gia presente;
- se comprende perche il confronto ortofoto non e disponibile con una sola
  annata autorizzata.

Domanda di controllo: "Se il confine RAS e quello GAIA non coincidono, quale
useresti per una pratica interna e perche?"

Risposta attesa: GAIA resta autorevole per il dato operativo interno; RAS e un
confronto informativo. Una risposta diversa e un finding, non va corretta prima
della registrazione.

#### Compito V2 - Interrogazione A Tre Livelli, 7 Minuti

Consegna: "Interroga il punto A e spiegami, con parole tue, cosa arriva da
GAIA, dal Catasto ufficiale e dal Territorio."

Registrare:

- tempo per trovare `Interroga punto` e capire che serve un clic in mappa;
- ordine con cui legge `GAIA`, `Catasto ufficiale`, `Territorio`;
- capacita di associare ogni risultato alla sua attribuzione;
- eventuale interpretazione della scheda come certificazione.

Non chiedere di confrontare valori tecnici non presenti nelle fixture.

#### Compito V3 - Vuoto E Non Disponibile, 5 Minuti

1. Interrogare il punto B e chiedere: "Cosa significa Nessun risultato?"
2. Interrogare la fixture C e chiedere: "Cosa significa Sorgente non
   raggiungibile?"
3. Chiedere: "In quale dei due casi concluderesti che il vincolo o l'oggetto non
   esiste?"

Risposta attesa:

- `empty` significa che la sorgente ha risposto senza elementi nel punto/raggio;
- `failed` o `unreachable` significa che non e possibile concludere nulla
  sull'assenza del dato.

Registrare come finding critico qualsiasi equivalenza tra non raggiungibile e
assenza del vincolo.

#### Compito V4 - Scheda Da Mappa E Anagrafica, 5 Minuti

Consegna:

1. "Genera la scheda della particella dal pannello di interrogazione e scarica
   il PDF."
2. "Apri la stessa particella dalla sua anagrafica e genera una nuova scheda
   senza tornare in mappa."

Nel PDF chiedere al viewer di trovare e spiegare il disclaimer. Domanda
obbligatoria: "Useresti questo documento come CDU o certificato?"

Risposta attesa: no; e una scheda istruttoria che fotografa fonti, esclusioni e
stato della consultazione.

#### Compito V5 - Misura E Stampa, 3 Minuti

Consegna: "Misura una distanza riconoscibile sulla mappa e prepara una stampa
che mostri gli strati attivi e le attribuzioni."

Verificare che l'utente distingua la misura geodetica da una superficie
catastale certificata e che controlli scala, legenda e attribuzioni nella
stampa.

### 30-45 Minuti - Percorso Admin Tecnico

Accedere come admin. Riutilizzare la stessa particella e gli stessi layer.

#### Compito A1 - Governance Dei Layer Esterni, 5 Minuti

Consegna: "Hai trovato un errore nel layer RAS. Mostra come proporresti la
correzione."

Non deve esistere un percorso di change request o editing sul layer esterno.
Registrare se l'admin:

- cerca comunque una change request sul layer RAS;
- comprende che la correzione va indirizzata al titolare della sorgente;
- distingue una nota istruttoria GAIA da una modifica al dato remoto.

Un controllo nascosto solo in UI non e prova sufficiente: il facilitatore deve
annotare il modello mentale espresso dall'admin.

#### Compito A2 - Distretto RAS Contro Distretto GAIA, 4 Minuti

Consegna: "I due confini non coincidono. Dimmi quale dato governa l'istruttoria
GAIA, quale useresti come confronto e come segnaleresti la discrepanza."

La risposta attesa mantiene GAIA autorevole per il dominio interno e RAS come
fonte esterna informativa. Non accettare una scelta basata solo sul colore o
sull'ordine di disegno.

#### Compito A3 - QGIS Read-Only, 6 Minuti

1. Aprire `/gis/strumenti`.
2. Scaricare il progetto QGIS.
3. Verificare che il file abbia nome riconoscibile.
4. Spiegare come autenticare QGIS e perche i layer esterni passano dal proxy
   GAIA.
5. Confermare che QGIS Server e i layer esterni restano read-only, senza WFS-T.

L'apertura effettiva in QGIS puo essere eseguita dopo la sessione se la
postazione non e configurata, ma il download deve completarsi durante la prova.

### 45-55 Minuti - Debrief

Porre a entrambi, separatamente:

1. "Quale passaggio ti ha fatto dubitare di piu?"
2. "Dove hai cercato per primo lo strato, l'interrogazione e la scheda?"
3. "Come distingui adesso dato GAIA, Catasto ufficiale e dato Territorio?"
4. "In quali casi non prenderesti una decisione perche una sorgente e giu?"
5. "Che valore legale attribuisci alla scheda territoriale?"

Non proporre soluzioni UI durante il debrief. Raccogliere prima il linguaggio
spontaneo usato dai partecipanti.

### 55-60 Minuti - Chiusura Opzionale

Rileggere i finding principali, chiedere conferma delle citazioni e assegnare
un owner per gli impedimenti di ambiente o dati. Non aprire direttamente una
feature: classificare prima le evidenze.

## Scheda Di Raccolta

Per ogni compito registrare:

| campo | valore |
| --- | --- |
| Sessione / data / versione | |
| Ruolo e familiarita GIS | viewer/admin; bassa/media/alta |
| Compito | V1-V5 oppure A1-A3 |
| Esito | completato / completato con aiuto / non completato |
| Tempo | mm:ss |
| Aiuti del facilitatore | numero e testo |
| Primo punto di esitazione | elemento e timestamp |
| Errore osservato | azione concreta, non interpretazione |
| Citazione utente | parole testuali |
| Severita | critica / alta / media / bassa |
| Evidenza | screenshot, registrazione o nota |

Tag obbligatori per i tre rischi centrali:

- `RAS_CR_CONFUSION`: tenta di modificare o aprire CR sul layer RAS;
- `DISTRETTO_AUTHORITY_CONFUSION`: scambia RAS per dato operativo GAIA;
- `SCHEDA_DISCLAIMER_CONFUSION`: interpreta la scheda come CDU/certificato.

## Criteri Di Esito

La sessione non e un voto aggregato. Sono gate separati:

- entrambi distinguono `empty` da `failed/unreachable` senza aiuto;
- entrambi identificano i tre livelli dell'interrogazione;
- il viewer genera le due schede e comprende il disclaimer;
- il viewer completa misura e stampa con attribuzioni;
- l'admin non tenta editing o CR sul layer RAS dopo aver letto la policy;
- l'admin distingue distretto RAS e GAIA per autorevolezza;
- l'admin scarica il progetto QGIS e ne descrive il confine read-only.

Una confusione su assenza/non raggiungibilita, autorevolezza o valore legale e
un finding critico e blocca l'enablement in esercizio. Errori di scoperta o copy
vanno classificati con tempo e frequenza prima di progettare una soluzione.

## Output Della Sessione

Produrre un report breve con:

- setup e fixture usate;
- matrice compiti per partecipante;
- finding ordinati per severita con evidenze;
- problemi di ambiente separati dai problemi UX;
- decisione `GO`, `GO_CON_CORREZIONI` o `NO_GO` per l'enablement;
- owner e scadenza per ogni correzione.

Lo smoke Playwright `tests/e2e/gis-territorio.spec.ts` verifica solo che i
percorsi tecnici principali restino collegati con sorgenti mockate. Non misura
comprensione, linguaggio, autorevolezza percepita o valore del disclaimer e non
chiude la validazione utenti finali.

## Esecuzione Smoke Opzionale

Con frontend raggiungibile all'URL Playwright configurato:

```bash
cd frontend
PLAYWRIGHT_GIS_TERRITORIO_ENABLED=true \
  npm run test:e2e -- tests/e2e/gis-territorio.spec.ts --project=chromium
```

Il test effettua login mock con `module_gis`, simula i flag Territorio attivi e
intercetta catalogo, proxy, interrogazione, scheda e QGIS. Non contatta RAS o
AdE e resta saltato quando il flag Playwright non e impostato.
