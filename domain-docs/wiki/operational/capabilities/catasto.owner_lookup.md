# Capability: catasto.owner_lookup

## Scopo

Guidare la ricerca del proprietario o intestatario di un terreno o di una particella nel contesto Catasto.

## Quando usarla

- l'operatore chiede chi e il proprietario di un terreno
- l'operatore vuole trovare una particella partendo da un intestatario
- l'operatore ha dati catastali minimi e vuole essere guidato nella ricerca

## Input minimi

Una delle seguenti combinazioni:

- comune + foglio + particella
- codice fiscale
- partita IVA
- nominativo

## Input opzionali utili

- subalterno
- sezione
- pagina di partenza (`/catasto/particelle`, `/catasto/gis`)

## Chiarimento da usare se mancano dati

Per aiutarti a trovare il proprietario di un terreno mi servono almeno comune, foglio e particella, oppure un nominativo, codice fiscale o partita IVA.

## Output atteso

- indicazione operativa su come completare la ricerca
- eventuale ricerca live quando gli input minimi sono presenti
- nessun fallback documentale generico

## Errori frequenti

- domanda formulata come richiesta generica senza identificativi
- confusione tra proprietario corrente e storico
- uso di termini non ancorati al Catasto ma con significato simile
