# Workflow operativo

## Ratchet ordinario

1. Diff dal merge-base e perimetro runtime.
2. Invarianti, test e metriche prima.
3. Feature o fix richiesto.
4. Una eventuale semplificazione nella stessa responsabilita.
5. Test, coverage, lint/typecheck e metriche dopo.
6. Confronto con la baseline del merge-base.
7. Sincronizzazione e verifica della baseline corrente.
8. Graphify se richiesto dalla modifica.

Il ciclo termina quando la change non peggiora. Non aprire automaticamente un
hotspot adiacente.

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

La baseline puo essere ridotta soltanto dopo il ratchet. Una estrazione che
sposta violation o lascia invariata la metrica obiettivo viene registrata come
`REORGANIZED_AND_CHARACTERIZED` e non abilita un'altra slice.

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
- refactoring non correlato aggiunto a una feature solo per migliorare il
  conteggio globale;
- confronto esclusivo con la baseline della change invece che con il
  merge-base.
