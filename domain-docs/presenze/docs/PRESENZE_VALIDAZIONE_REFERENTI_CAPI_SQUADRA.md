# Presenze - Documento di validazione regole giornaliere

Data: 2026-07-14

## A chi e rivolto

Questo documento e pensato per:

- referenti del modulo Presenze
- capi squadra
- responsabili che ogni giorno leggono e verificano le giornaliere

## Obiettivo

Vogliamo confermare insieme le regole che GAIA deve usare per:

- capire quando una giornaliera e regolare
- capire quando una giornaliera va solo controllata
- capire quando una giornaliera va corretta subito
- bloccare l'export mensile solo nei casi davvero critici

Il punto non e descrivere il software, ma verificare se le regole operative sono corrette rispetto al lavoro reale.

## Tre esiti possibili per una giornaliera

Proposta attuale:

- `OK`
  - la giornata risulta coerente e non richiede interventi
- `Da verificare`
  - la giornata non e grave, ma va controllata da un responsabile
- `Correggere subito`
  - la giornata ha un problema operativo e va sistemata prima dell'export

## Regola generale

Una giornata deve finire in anomalia quando succede almeno una di queste cose:

- mancano timbrature importanti
- le ore lavorate non coprono il teorico previsto
- c'e una causale non coerente o insufficiente a coprire la giornata
- il dettaglio Inaz segnala un'anomalia tecnica
- risultano extra molto alti che richiedono controllo

## Regola sugli extra oltre 3 ore

Proposta attuale:

- fino a `3 ore` di extra nella giornata, la giornata non entra in anomalia solo per questo motivo
- oltre `3 ore`, la giornata va in `Da verificare`

Significato pratico:

- non la consideriamo subito sbagliata
- chiediamo pero un controllo del responsabile

## Quando una giornata va in "Correggere subito"

Proposta attuale:

- mancano minuti rispetto al teorico e la giornata non e coperta correttamente
- mancano timbrature essenziali
- c'e una incoerenza sostanziale tra timbrature, causale e ore attese

Effetto operativo:

- questa giornata blocca il lavoro di chiusura
- questa giornata deve bloccare anche l'export mensile

## Quando una giornata va in "Da verificare"

Proposta attuale:

- extra oltre `3 ore`
- anomalia tecnica Inaz, ma senza veri buchi operativi
- caso leggibile da GAIA ma che richiede conferma umana

Effetto operativo:

- la giornata resta visibile nella coda anomalie
- il responsabile la controlla e decide se e corretta oppure se va sistemata

## Regole per gli operai

Per gli operai vogliamo usare regole piu aderenti all'organizzazione reale del lavoro.

### Gruppi operai previsti

Proposta attuale:

- gruppo `agrario`
- gruppo `catasto_magazzino`

### Orario teorico proposto

Nei giorni feriali:

- `7 ore` per entrambi i gruppi

Il sabato:

- `agrario`: lavora il `1` e `3` sabato del mese, con teorico `6 ore e 30`
- `catasto_magazzino`: lavora a sabati alternati, con teorico `6 ore`

## Regola sui sabati non previsti

Proposta attuale:

- se un sabato non e previsto per quel gruppo, il teorico della giornata vale `0`
- quindi quel sabato non deve creare automaticamente ore mancanti

Per il gruppo `catasto_magazzino`, oggi la proposta e:

- se nel mese risultano gia coperti due sabati lavorati o giustificati, gli altri sabati non devono produrre debito orario

## Ferie e permessi per gli operai

Proposta attuale:

- `ferie` e `permesso` possono coprire il teorico della giornata
- se coprono correttamente la giornata, la giornaliera puo chiudersi in `OK`

Questo vale anche per il sabato previsto.

## Richiesta INAZ accolta

Proposta attuale:

- una richiesta Inaz con stato `ACC` non basta da sola a rendere regolare una giornata

Esempio:

- se una richiesta sistema una timbratura mancante ma alla fine lascia un extra troppo alto o una giornata non coerente, la giornata non deve passare automaticamente in `OK`

## Regole per gli impiegati

Nota:

- nel sistema tecnico oggi questi casi sono chiamati `non operai`
- in questo documento li chiamiamo `impiegati`

Proposta attuale:

- per gli impiegati, se Inaz segnala un'anomalia tecnica ma GAIA riesce comunque a ricostruire bene la giornata, il caso puo chiudersi in `OK`

Questo vale solo se insieme risultano veri questi punti:

- c'e una richiesta Inaz accolta (`ACC`)
- ci sono timbrature sufficienti
- la giornata ricostruita e coerente

In pratica:

- non vogliamo lasciare in anomalia giornate che sono corrette dal punto di vista operativo ma che Inaz segnala ancora in modo tecnico

## Anomalie tecniche Inaz

Proposta attuale:

- se Inaz segnala un'anomalia tecnica, ma la giornata e comunque chiara e coerente, il caso va in `Da verificare`
- se invece oltre all'anomalia tecnica mancano anche ore, timbrature o coperture, il caso va in `Correggere subito`

## Regola di blocco export

Proposta attuale:

- l'export mensile deve essere bloccato solo dalle giornate in `Correggere subito`
- le giornate in `Da verificare` devono restare visibili, ma non bloccare da sole l'export

## Esempi semplici

### Esempio 1

Operaio con giornata feriale da `7 ore`, timbrature complete e `2 ore` di extra.

Esito proposto:

- `OK`

### Esempio 2

Operaio con giornata feriale da `7 ore`, timbrature complete e `4 ore` di extra.

Esito proposto:

- `Da verificare`

### Esempio 3

Operaio con sabato non previsto dal gruppo.

Esito proposto:

- non deve generare automaticamente ore mancanti

### Esempio 4

Operaio con sabato previsto, ma coperto da ferie o permesso.

Esito proposto:

- `OK`, se la causale copre correttamente la giornata

### Esempio 5

Impiegato con anomalia tecnica Inaz, richiesta `ACC` e giornata ricostruita correttamente.

Esito proposto:

- `OK`

### Esempio 6

Giornata con timbratura mancante e ore non coperte.

Esito proposto:

- `Correggere subito`

## Punti da confermare

Chiediamo validazione esplicita su questi punti:

1. La soglia `3 ore` per mandare una giornata in `Da verificare` e corretta?
2. Per gli operai, il teorico `7 ore` nei feriali e corretto?
3. Per il gruppo `agrario`, il `1` e `3` sabato del mese con `6h30` e corretto?
4. Per il gruppo `catasto_magazzino`, la logica dei sabati alternati con `6h` e corretta?
5. Ferie e permessi devono coprire completamente il sabato previsto?
6. Una richiesta Inaz `ACC` deve restare insufficiente da sola a chiudere automaticamente una giornata operaia?
7. Per gli impiegati, e corretto chiudere in `OK` le anomalie solo tecniche quando la giornata e ricostruita bene?
8. E corretto che solo i casi `Correggere subito` blocchino l'export?

## Modalita di risposta consigliata

Per velocizzare la validazione, ogni referente o capo squadra puo rispondere cosi:

- `Confermo tutto`
- oppure `Confermo con modifiche`, indicando punto per punto cosa cambiare

Formato suggerito:

- punto `1`: confermo / non confermo
- punto `2`: confermo / non confermo
- punto `3`: confermo / non confermo

## Nota finale

Se dai riscontri emerge che una regola non riflette il lavoro reale, aggiorneremo prima il documento condiviso e poi la logica in GAIA.
