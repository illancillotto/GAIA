# Modulo Catasto

## Scopo

Il modulo Catasto supporta consultazione e ricerca di particelle, intestatari, anomalie, distretti, GIS e dati collegati al perimetro consortile.

## Tipi di richieste supportate dal Wiki

- capire cosa mostra una pagina Catasto
- orientarsi tra particelle, GIS, anomalie e import
- spiegare workflow o metriche del modulo
- guidare ricerche operative di particelle o proprietari

## Capability operative iniziali

- `catasto.owner_lookup`
- `catasto.particella_lookup`

## Pagine operative principali

- `/catasto/particelle`: consultazione e ricerca particelle
- `/catasto/gis`: mappa e selezione territoriale
- `/catasto/letture-contatori`: letture contatori irrigui
- `/catasto/anomalie`: anomalie catastali da gestire
- `/catasto/distretti`: perimetro distrettuale

## Workflow collegati

- ricerca proprietario terreno: `catasto_owner_search`
- consultazione lettura contatore: pagina `catasto__letture_contatori`

## Input frequentemente richiesti

- comune
- foglio
- particella
- subalterno
- nominativo
- codice fiscale
- partita IVA
- UUID particella

## Errori frequenti

- richiesta di proprietario senza comune/foglio/particella e senza identificativi alternativi
- richiesta generica non ancorata a una pagina o a un'entita
- confusione tra consultazione documentale e ricerca live
