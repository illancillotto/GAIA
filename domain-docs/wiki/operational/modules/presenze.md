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
- API amministrativa `/presenze/configuration/operai-rules`: configurazione persistente delle regole operaie

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
- Per i collaboratori operai e disponibile l'attributo persistente `operai_group`, modificabile dagli admin nel profilo contrattuale.
- I gruppi supportati sono `agrario` e `catasto_magazzino`.
- Le regole operaie non sono piu hardcoded: sono salvate in `presenze_operai_rule_configs` e inizializzate con default applicativi se la tabella e vuota.
- Il gruppo `agrario` lavora il 1 e 3 sabato del mese; il sabato previsto vale `6h30`.
- Il gruppo `catasto_magazzino` lavora a sabati alternati; il bootstrap corrente usa 2 e 4 sabato del mese, con sabato previsto da `6h`, ma la sequenza resta configurabile.
- I sabati non previsti dal gruppo hanno teorico `0` e vengono evidenziati come non previsti se arrivano timbrature o richieste.
- Ferie e permessi che coprono un sabato previsto sono considerati copertura valida del teorico operaio e possono chiudere la giornata in `ok` se non restano minuti mancanti.
- `OPE0714_1E3SAB`, `OP_5.3_12.3`, `OPESAB` e `OSAB5.3_12.3` condividono la stessa logica di risoluzione operaia; cambiano i minuti nominali risolti dalla regola del gruppo.
- Se `operai_group` non e ancora valorizzato, GAIA usa un fallback legacy sui codici operai storici per non perdere la classificazione durante la bonifica anagrafica.
- Una richiesta INAZ `ACC` che completa una timbratura mancante non rende automaticamente la giornata regolare: se genera MPE oltre la soglia giornaliera configurata, la qualita operativa resta bloccante.

## Prossimi passi

Indica collaboratore, periodo o pagina Presenze e ti guido nella consultazione o nella verifica operativa.
