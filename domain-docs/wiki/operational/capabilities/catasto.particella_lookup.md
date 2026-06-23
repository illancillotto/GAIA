# Capability: catasto.particella_lookup

## Scopo

Recuperare il dettaglio live di una particella quando e disponibile un UUID valido.

## Input minimi

- UUID particella

## Output atteso

- comune o codice catastale
- foglio
- particella
- subalterno se presente
- distretto
- presenza o assenza di anagrafica collegata

## Chiarimento da usare se manca l'UUID

Per cercare una particella Catasto in questo flusso devo ricevere un UUID valido.

## Note

Questa capability e distinta dalla ricerca proprietario: se l'utente non ha l'UUID ma ha comune/foglio/particella, il task corretto non e `particella_lookup` ma `owner_lookup` o una ricerca guidata di particella.
