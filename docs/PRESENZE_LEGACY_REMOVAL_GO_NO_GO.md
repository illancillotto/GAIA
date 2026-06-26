# Presenze Legacy Removal Go-No-Go

Ultimo aggiornamento: `2026-06-25`

## Decisione

Stato attuale: `GO` per considerare chiuso il rename applicativo `Inaz -> Presenze`.

Stato attuale: `NO-GO` solo per accorpare nello stesso blocco anche:

- rename fisico tabelle `inaz_*`
- riscrittura migration history
- consolidamento definitivo del repository esterno `presenze-scraper`

## Sintesi

Il runtime canonico del prodotto e ormai `Presenze`.

Evidenze consolidate:

- frontend canonico sotto `app/presenze/*`
- backend canonico sotto `app.modules.presenze.*`
- route pubbliche canoniche sotto `/presenze/...`
- self-service canonico sotto `/me/presenze/...`
- payload utenti canonici con `module_presenze`
- nessun package runtime legacy del modulo

Il residuo rimasto non blocca la chiusura del rename prodotto, perche e confinato a:

- storage storico
- documentazione di archivio
- path reali verso il tool esterno

## Residuo legittimo

### Storage e history

- migration Alembic che introducono o rinominano colonne legacy
- tabelle fisiche `inaz_*`

### Integrazione esterna

- default config verso `/home/cbo/CursorProjects/presenze-scraper`
- mount Docker verso `/home/cbo/CursorProjects/presenze-scraper`

### Documentazione storica

- memo di audit, backlog o review che descrivono la transizione

## Cosa non e piu un problema runtime

- route frontend legacy del modulo
- router backend legacy del modulo
- import applicativi dal package legacy del modulo
- payload canonici utente basati sul flag legacy del modulo
- alias pubblici del modulo come superficie corrente

## Conclusione operativa

Il rename prodotto puo essere dichiarato sostanzialmente completato quando:

- i residui documentali non correnti sono archiviati o chiaramente marcati come storici
- il codice runtime non reintroduce naming legacy

Non serve forzare nello stesso step il rename dello storage fisico o del repo esterno: aumenterebbe il rischio senza aggiungere valore immediato al modulo.
