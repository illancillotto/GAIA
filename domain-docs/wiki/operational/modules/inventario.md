# Modulo Inventario

## Scopo

Il modulo Inventario centralizza il registro dei beni e degli asset IT del Consorzio e raccoglie le richieste di magazzino sincronizzate dai sistemi di campo. Permette di consultare anagrafica, stato e provenienza delle richieste e di tenere allineato l'inventario con le segnalazioni operative.

## Cosa puo fare l'operatore

- leggere una scheda bene o asset e i suoi dati identificativi
- consultare l'elenco delle richieste di magazzino con ricerca e filtri
- distinguere richieste attive da quelle archiviate
- capire chi ha segnalato o richiesto un intervento e quando
- verificare lo stato di sincronizzazione di una richiesta con il sistema di origine
- trovare un elemento specifico per tipo segnalazione o per richiedente

## Dati o input tipici

- codice o identificativo del bene o asset
- tipo di segnalazione (report_type)
- nominativo di chi segnala o richiede
- data segnalazione o data richiesta
- stato attivo o archiviato della richiesta

## Pagine principali

- `/inventory`: elenco e ricerca delle richieste di magazzino e dei beni collegati

## Regole operative utili

- Le richieste di magazzino arrivano dalla sincronizzazione con il sistema di campo (WhiteCompany): ogni richiesta mantiene il riferimento di origine e la data di ultimo allineamento.
- Una richiesta puo essere attiva o archiviata: le archiviate restano consultabili ma escono dal lavoro corrente.
- La ricerca lavora su tipo segnalazione, segnalante e richiedente.
- L'accesso al modulo richiede il permesso modulo `inventario`.

## Prossimi passi

Indica un bene, un richiedente o un tipo di segnalazione e ti guido nella consultazione o nella verifica operativa dell'Inventario.
