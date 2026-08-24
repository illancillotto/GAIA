# Pagina Catasto Particelle

## Scopo

La pagina `/catasto/particelle` consente consultazione e ricerca delle particelle catastali correnti.

## Cosa puo chiedere l'operatore

- come leggere una particella
- come filtrare per comune, foglio o particella
- come cercare per intestatario
- come capire se una particella ha anagrafica o anomalie collegate

## Collegamento da documenti Catasto

Nel viewer `/catasto/documents/{id}` il riferimento catastale del documento e cliccabile quando sono disponibili comune, foglio e particella.
Il click cerca la particella corrente e apre il dettaglio in modale solo se il riferimento e risolto in modo univoco; in caso di riferimento incompleto, non trovato o ambiguo resta nel viewer e mostra un messaggio operativo.

## Dati utili per ricerche operative

- `comune`
- `codice_catastale`
- `foglio`
- `particella`
- `intestatario`
- `codice_fiscale`

## Collegamenti

- capability `catasto.owner_lookup`
- capability `catasto.particella_lookup`
- workflow `catasto_owner_search`
