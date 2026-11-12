# Caricamento dei candidati PEC/email — 12 novembre 2026

La pagina dei solleciti eseguiva il caricamento completo di ogni avviso per
mostrare soltanto gli stati di pagamento e notifica. La prima pagina PEC con
25 righe e 230 risultati richiedeva 322 query e circa 15,87 secondi. Una ricerca
avviava inoltre candidati, account e template a ogni carattere digitato.

## Modifica

`communications/candidate_states.py` carica gli stati in blocco per le sole
posizioni della pagina, riutilizzando il calcolo contabile canonico
`_precompute_tributi_effective_cores`. Notifiche e ultime comunicazioni hanno
una query ciascuna. Non vengono caricati dettagli, note e liste di pagamenti
per ogni riga. Posizioni mancanti restano `da_verificare`; gli stati multipli
rimangono ordinati e deduplicati. La ricerca senza risultati evita anche la
query delle righe. Nessun dato viene memorizzato in una cache condivisa.

Il nuovo hook `use-candidates.ts` attende 300 ms dopo l'ultimo carattere della
ricerca, annulla le richieste obsolete e ne ignora eventuali risposte tardive.
Filtri diversi dalla ricerca e paginazione restano immediati. Account e template
si ricaricano all'apertura, al cambio di sessione/permessi e con l'aggiornamento
esplicito, senza dipendere da ricerca o pagina. La disponibilita dell'elenco
non attende questi cataloghi; gli errori restano visibili.

Controlli di creazione, revisione e invio invariati, compresa l'esclusione degli
avvisi riconciliati con Poste. Nessuna migrazione o modifica ai worker.

## Misure e verifiche

Profilazione in sola lettura sul database di produzione:

| Caso | Prima | Dopo |
| --- | ---: | ---: |
| Prima pagina, 25 righe | 322 query / 15,87 s | 9 query / 0,58 s |
| Pagina 1, confronto nella stessa fotografia DB | 10,31 s | 0,44 s |
| Pagina 2, confronto nella stessa fotografia DB | 9,76 s | 0,43 s |

Il confronto usa una transazione `REPEATABLE READ READ ONLY` e verifica
l'uguaglianza completa dei risultati, campo per campo, su 50 righe.

Sul candidato derivato dai sorgenti di produzione sono passati 279 test backend
con PostgreSQL reale, 92 frontend, 18 smoke e 11 E2E con API sintetiche. Coverage
statement/branch al 100% dei due runtime backend e dei tre frontend modificati.
Passati anche due test del calcolo contabile in blocco, typecheck, lint e style
gate. Il ratchet conserva esattamente i 12 rilievi preesistenti del perimetro,
senza nuove regressioni; baseline invariata. Nessun nuovo errore di complessita
(30 callable prima su tre file, 41 dopo su cinque). Grafi codice backend e
frontend aggiornati con pruning dei simboli rimossi.

Le evidenze operative sono conservate nel rilascio
`/opt/gaia/releases/loading-20261112/`: manifest dei cinque runtime, immagini,
test, confronto dei tempi e verifica della configurazione.

## Produzione

Attivato alle **13:14 CET**, backend `e2de3b67a69c` e frontend `9bbfbb86a872`.
Preservati 196 route frontend, configurazione, schema, template e 37 container
estranei al rilascio. Trasporti Communications ancora disabilitati e in pausa.

Misura delle API autenticate effettivamente pubblicate, tutte HTTP 200:

| Richiesta | Risposta | Risultati |
| --- | ---: | ---: |
| Prima pagina PEC | 0,413 s | 25 su 230 |
| Ricerca dello screenshot con filtro PEC | 0,246 s | 0 |
| Seconda pagina PEC | 0,698 s | 25 su 230 |

Sono misure puntuali sul carico corrente, senza includere il download iniziale
del JavaScript della pagina. Il rilascio non crea o spedisce comunicazioni.
