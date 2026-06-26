# Modulo Presenze

## Scopo

Il modulo Presenze supporta consultazione collaboratori, giornate lavorative, organigramma, export HR e gestione operativa di recuperi e banca ore.

## Cosa puo fare l'operatore

- leggere scheda collaboratore e responsabilita
- orientarsi nell'organigramma Presenze
- interpretare dati giornalieri e anomalie
- trovare responsabili e operatori collegati
- verificare saldo banca ore, snapshot delle presenze e rettifiche manuali
- capire se una quota e liquidabile, da mantenere in banca ore o da revisione HR

## Dati o input tipici

- nome collaboratore o ID
- data o periodo
- nodo organigramma o responsabile
- mese o intervallo banca ore
- motivo della liquidazione o rettifica HR

## Pagine principali

- `/presenze/collaboratori`: schede collaboratore
- `/presenze/organigramma`: albero organizzativo Presenze
- `/presenze/banca-ore`: saldo ore, guida liquidazione e workflow HR
- `/presenze/recuperi`: recuperi maturati e fruiti
- `/presenze/export`: export XLSM mensile
- `/presenze/configurazione`: template orari e policy amministrative del modulo
- nella pagina configurazione la policy banca ore espone anche uno storico modifiche con data e operatore

## Regole operative utili

- In banca ore GAIA distingue:
  - quota liquidabile
  - quota che resta in banca ore
  - quota da revisione HR
- La proposta di liquidazione usa il minore tra:
  - saldo banca ore disponibile
  - straordinario del periodo classificato dal motore CCNL
- Se il profilo contrattuale del collaboratore e mancante, o solo derivato quando la policy non lo consente, la quota candidata non viene liquidata automaticamente.
- La policy banca ore puo essere aggiornata dagli admin in `/presenze/configurazione`.

## Prossimi passi

Indica collaboratore, periodo o pagina Presenze e ti guido nella consultazione o nella verifica operativa.
