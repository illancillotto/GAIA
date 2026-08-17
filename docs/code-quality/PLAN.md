# Piano di riduzione della complessita

## Obiettivo di programma

Ridurre progressivamente il debito di complessita di GAIA senza cambiare il
comportamento del prodotto, mantenendo ogni modifica piccola, misurata e
revisionabile.

## Fase 0 - Audit e contratto

Deliverable:

- inventario reale di runtime, test, tool e workflow;
- snapshot di branch, commit e working tree;
- inclusioni/esclusioni motivate;
- architettura proposta;
- lista file da modificare.

Exit criteria:

- nessuna assunzione non verificata;
- modifiche preesistenti identificate e preservate;
- comandi test correnti riprodotti o failure preesistenti documentate.

## Fase 1 - Tooling, baseline e report

Deliverable:

- motore AST Python e JS/TS normalizzato;
- CLI deterministica con codici `0/1/2`;
- baseline ed eccezioni versionate;
- report JSON e sintesi leggibile;
- controllo differenziale;
- test dello strumento;
- target Make locali;
- documentazione operativa;
- proposta CI non bloccante.

Exit criteria:

- test del motore verdi;
- baseline riproducibile;
- check read-only;
- regressioni sintetiche correttamente bloccate;
- Checkpoint 1 scritto in `PROGRESS.md`.

Decisione richiesta:

- approvazione della baseline;
- approvazione delle soglie;
- approvazione delle eccezioni;
- autorizzazione ad attivare gate CI differenziali.

## Fase 2 - Gate differenziale

Prerequisito: Checkpoint 1 approvato.

Deliverable:

- integrazione coerente nei workflow backend e frontend;
- base PR/merge-base corretta;
- report CI;
- nessun blocco per debito legacy invariato;
- blocco per codice nuovo sopra soglia o debito peggiorato.

Exit criteria:

- prove su fixture e branch di test;
- nessun raddoppio inutile di installazioni/build;
- documentazione di recovery per shallow clone e baseline conflict.

## Fase 3 - Refactoring incrementale

Ogni goal tratta un solo hotspot e produce una unita da pull request.

Ciclo:

1. selezionare il candidato da dati, rischio e frequenza di modifica;
2. definire invarianti e test di caratterizzazione;
3. acquisire metriche prima;
4. progettare la minima estrazione utile;
5. implementare senza cambiare contratti;
6. eseguire test mirati e coverage dei file modificati;
7. acquisire metriche dopo;
8. aggiornare baseline solo per rimuovere debito;
9. aggiornare `PROGRESS.md` e `HOTSPOTS.md`;
10. fermarsi.

Exit criteria per iterazione:

- nessuna nuova failure;
- copertura richiesta rispettata;
- almeno una metrica primaria ridotta;
- nessuna metrica primaria peggiorata senza motivazione approvata;
- diff limitato e leggibile;
- un solo hotspot chiuso o ridotto.

## Fase 4 - Consolidamento

Quando almeno cinque iterazioni sono concluse:

- valutare falsi positivi e costo operativo;
- calibrare soglie usando i dati, non sensazioni;
- eliminare eccezioni scadute;
- misurare trend per modulo;
- decidere se estendere il gate ai test;
- decidere se aggiungere controllo di dipendenze/coupling.

## Priorita

Il ranking non usa solo LOC. Punteggio suggerito:

```text
priority = severity * 4 + change_frequency * 3 + defect_risk * 3
           + domain_criticality * 2 + testability
```

Valori da 0 a 5 per fattore. La severita deriva da complessita cognitiva,
ciclomatica, nesting e densita. La frequenza di modifica deriva dalla storia Git.

## Limiti di una iterazione

- un hotspot primario;
- un modulo applicativo;
- nessuna migration;
- nessun cambio di API;
- nessun upgrade framework;
- nessun refactoring opportunistico non necessario;
- massimo una decisione architetturale nuova, documentata.

Se il lavoro supera questi limiti, dividerlo nel backlog e completare soltanto la
prima slice autonoma.
