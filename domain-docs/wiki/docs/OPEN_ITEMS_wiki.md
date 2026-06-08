# Wiki Supporto - Open Items

Ultimo aggiornamento: 2026-06-08

## Stato attuale

Il perimetro `Wiki Supporto` e `Wiki Governance` è operativo nella prima versione utile.

Completato:
- `M1` Fondazione Wiki
  - chat documentale
  - live routing
  - guardrail strutturali
  - supporto multilingua pragmatico
- `M2` Supporto strutturato utente/admin
  - `/wiki/support`
  - CTA widget per supporto / problema / funzionalità
  - richieste strutturate
  - inbox admin
  - dettaglio richiesta
  - workflow stati ricco
  - timeline eventi
- `M3` Governance richieste
  - deduplica pragmatica
  - `canonical_request_id`
  - unlink duplicate
  - inbox utente
  - aggiornamenti non letti
  - feedback finale utente
  - reopen request
- `M4.1` Analytics supporto avanzate
  - cluster richieste
  - duplicate pressure
  - coverage gap / guardrail pressure / docs-only pressure
- `M4.2` Product signals
  - insight automatici amministrativi e di prodotto
- `M4.3a` Canonical management avanzato
  - vista famiglia del caso
  - promozione di un nuovo canonico
  - riallineamento duplicati collegati

## Cosa manca davvero

I punti sotto non bloccano l'uso del sistema. Sono il residuo evolutivo per renderlo più maturo e più vicino a una piattaforma di product intelligence.

### 1. Clustering persistito e più sofisticato

Stato attuale:
- esiste clustering pragmatico in analytics
- i cluster non sono ancora entità persistite nel database

Da fare:
- introdurre un identificatore cluster stabile
- mantenere storico cluster nel tempo
- migliorare il raggruppamento oltre il solo `canonical_request_id` o token overlap

Valore:
- trend più affidabili
- minore rumore nei report
- lettura migliore dei bisogni ricorrenti

### 2. Canonical management più forte

Stato attuale:
- si può cambiare il caso canonico
- si possono sganciare duplicati

Da fare:
- cambio canonico guidato con conferma esplicita
- merge logico di una intera family
- eventuale gestione di `case family` come entità dedicata
- storico completo delle decisioni di merge/split del gruppo

Valore:
- backlog più pulito
- famiglie casi più facili da leggere

### 3. Bridge con backlog o ticket esterni

Stato attuale:
- la governance è interna a GAIA

Da fare:
- link a ticket esterni
- campi tipo:
  - `external_ticket_key`
  - `external_ticket_url`
  - `delivery_status`
  - `delivery_notes`
- eventuale sync leggera solo amministrativa

Valore:
- ponte diretto tra segnalazione utente e delivery reale

### 4. Automazioni assistite

Stato attuale:
- triage e assegnazione sono ancora completamente manuali

Da fare:
- suggerimento assegnatario
- suggerimento priorità
- suggerimento severità
- suggerimento duplicate cluster

Vincolo:
- mantenere sempre l'admin come decisore finale

### 5. Notifiche in-app più visibili

Stato attuale:
- esistono aggiornamenti non letti nel supporto utente

Da fare:
- badge numerico di modulo
- entrypoint più esplicito nella navigazione Wiki
- eventuale banner "hai aggiornamenti sul supporto"

### 6. Feedback loop più analitico

Stato attuale:
- esiste feedback utente `helpful/not_helpful`

Da fare:
- distinguere meglio:
  - risolto tecnicamente
  - spiegato correttamente
  - non riproducibile
  - risolto ma non soddisfacente
- usare questi dati nei segnali di prodotto

## Ordine consigliato per ripresa lavori

### Priorità alta
1. bridge backlog esterno
2. clustering persistito

### Priorità media
3. automazioni assistite admin
4. canonical management ancora più forte

### Priorità bassa
5. notifiche in-app più ricche
6. feedback loop analitico esteso

## Prossima milestone consigliata

`M4.3b / M4.4`

Ordine suggerito:
1. backlog bridge
2. cluster persistiti
3. suggerimenti automatici admin

## Note operative

- Il sistema attuale è già abbastanza maturo per essere usato in esercizio controllato.
- Le parti residue sono di qualità, consolidamento e intelligence, non di sopravvivenza del flusso base.
- Prima di integrare backlog esterni conviene mantenere stabile il modello di family canonica già introdotto.
