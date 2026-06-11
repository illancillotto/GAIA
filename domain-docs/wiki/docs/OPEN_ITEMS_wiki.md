# Wiki Supporto - Open Items

Ultimo aggiornamento: 2026-06-11

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
- esiste ora una base manuale per collegare richiesta e delivery:
  - `external_ticket_key`
  - `external_ticket_url`
  - `delivery_status`
  - `delivery_notes`
- la inbox admin supporta già:
  - filtri `delivery` e `ticket`
  - export CSV delle richieste con ticket nel filtro corrente
- le analytics supporto leggono già:
  - `linked_ticket_requests`
  - `delivery_started_requests`
  - `released_requests`
  - `wont_do_requests`
  - `top_delivery_statuses`
  - filtri per `delivery_status` e `ticket_linked`

Da fare:
- consolidare convenzioni operative del bridge
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
1. clustering persistito
2. sync o convenzioni più forti sul bridge backlog esterno
3. automazioni assistite admin

### Priorità media
4. canonical management ancora più forte

### Priorità bassa
5. notifiche in-app più ricche
6. feedback loop analitico esteso

## Prossima milestone consigliata

`M6` maturazione intelligence e bridge delivery

Documento di riferimento:
- `domain-docs/wiki/docs/M5_CONSOLIDATION_wiki.md`

Ordine suggerito:
1. cluster persistiti
2. convenzioni o sync bridge delivery
3. suggerimenti automatici admin
4. feedback loop più ricco

## Note operative

- Il sistema attuale è già abbastanza maturo per essere usato in esercizio controllato.
- Le parti residue sono di qualità, consolidamento e intelligence, non di sopravvivenza del flusso base.
- Il prossimo rischio principale non è la mancanza di feature, ma la crescita di complessità in pochi file e pochi flow centrali.
- `M5.1`, `M5.2` e una prima tranche reale di `M5.3` sono già presenti nel codice.
- Il rischio principale ora si sposta da performance/struttura a persistenza dei cluster e maturazione del bridge delivery.
