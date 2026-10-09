# Giornaliere: modello di presentazione operativo R6

Il modello locale `frontend/src/app/presenze/giornaliere/daily-cell-model.ts`
possiede due proiezioni pure della presentazione giornaliera, senza conoscere
API, stato React, autorizzazioni di dominio o salvataggi.

- `dailyCellIndicators` produce soltanto gli indicatori presenti, nell'ordine
  extra, KM, trasferta, reperibilità, autorizzazione oppure richiesta. L'icona
  autorizzata prevale su quella di richiesta. Classi e simboli restano invariati.
- `kmInputPresentation` consolida il valore iniziale e il flag disabled dei due
  input KM, in matrice e nel modale collaboratore. Riceve il permesso già deciso
  dalla pagina: il permesso globale della matrice non viene sostituito dal
  permesso per record del modale.

Il valore KM presente include zero, negativo e NaN; null produce il valore
iniziale vuoto. Una bozza vuota resta una bozza, non ricade sul valore salvato.
Extra e trasferta richiedono strettamente un valore maggiore di zero; la
trasferta montana mantiene la sua condizione alternativa. Reperibilità è
presente per qualunque unità diversa da `none`, indipendentemente dalla quantità.

La pagina mantiene gli stessi input uncontrolled e gli stessi nodi durante
modifica e salvataggio, i loro eventi e le chiamate API. Non cambiano hook,
dipendenze, cache, polling, mapping identità, calcoli, permessi o navigazione.
Il contenitore degli indicatori rimane presente anche senza indicatori.

La slice è limitata a questa responsabilità. Cognitive principale 437→420;
somma pagina e modello 1273→1230, cyclomatic 1350→1319. Il nuovo modello non
ha finding. Il componente principale rimane estremo: non è una chiusura del
debito Presenze o della campagna.

Evidenze e matrice dei test:
`reports/code-quality/SLICE_R6_PRESENZE_DAILY_2026-10-09.md`.
