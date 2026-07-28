# Modulo Ruolo

## Scopo

Il modulo Ruolo supporta consultazione avvisi, particelle collegate, statistiche e workflow di materializzazione ruolo.

## Cosa puo fare l'operatore

- leggere avvisi e contesto tributario
- usare `/ruolo/tributi` per preview template GAIA, wizard batch solleciti con bollettino
  postale e download documenti quando dispone dell'accesso di consultazione tributi
- nei solleciti GAIA il partitario viene stampato prima del bollettino, numerato come
  `Dettaglio partitario allegato - pagina X di N`; il bollettino TD 896 resta l'ultima pagina
- usare `/ruolo/raccomandate` per aprire direttamente la console read-only
  `Raccomandate Poste Online`; l'ingresso `/ruolo/tributi` resta centrato sull'elenco tributi
- capire collegamenti particella-avviso-soggetto
- interpretare statistiche e riepiloghi
- verificare esiti workflow import/materializzazione

## Dati o input tipici

- numero avviso o identificativo
- codice fiscale o soggetto
- comune/foglio/particella per collegamenti catastali
- periodo o anno di riferimento

## Pagine principali

- `/ruolo/avvisi`: avvisi
- `/ruolo/tributi`: console tributi, preview e solleciti
- `/ruolo/raccomandate`: console raccomandate Poste Online
- `/ruolo/particelle`: particelle collegate
- `/ruolo/stats`: statistiche
- `/ruolo/import`: workflow materializzazione

## Prossimi passi

Dimmi avviso, soggetto o particella di interesse e ti oriento nella pagina corretta.
