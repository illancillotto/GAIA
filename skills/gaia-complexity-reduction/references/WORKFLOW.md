# Workflow operativo

## Bootstrap

1. Audit del checkout.
2. Definizione scope e schema metriche.
3. Implementazione adapter AST.
4. Baseline ed eccezioni.
5. Diff checker.
6. Fixture e test.
7. Target locali.
8. Report e documentazione.
9. Checkpoint 1 e stop.

## Singolo hotspot

1. Selezione evidence-based.
2. Invarianti e caratterizzazione.
3. Metriche prima.
4. Slice minima.
5. Refactoring.
6. Test mirati e coverage.
7. Metriche dopo e aggregati.
8. Baseline ridotta.
9. Progress aggiornato.
10. Stop.

## Pattern preferiti

- estrarre funzioni pure da handler complessi;
- separare parsing/validazione, orchestration e side effect;
- introdurre oggetti valore solo se riducono branching e chiariscono invarianti;
- separare componenti React per responsabilita e proprieta, non per LOC;
- spostare stato correlato in reducer quando riduce transizioni incoerenti;
- isolare query da mapping e logica di dominio;
- mantenere adapter sottili ai confini FastAPI, database e API frontend.

## Pattern vietati

- helper generici senza ownership;
- funzioni wrapper usate soltanto per abbassare una soglia;
- duplicazione tra file;
- nuove astrazioni prima dei test di caratterizzazione;
- rinomina massiva nello stesso diff;
- refactoring e upgrade dipendenze insieme;
- aggiornamento baseline prima di verificare le metriche dopo.
