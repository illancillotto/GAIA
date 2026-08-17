# Hermes Goal - Fase 1

## Quando usarlo

Usare una volta, dalla root del repository GAIA, per costruire audit, tooling,
baseline e report. Il goal deve fermarsi al Checkpoint 1 e non deve rifattorizzare
file applicativi.

## Comando consigliato

Incollare in Hermes come singolo comando:

```text
/goal Leggi integralmente e segui la skill di progetto skills/gaia-complexity-reduction/SKILL.md e i relativi riferimenti, quindi esegui integralmente docs/code-quality/PROMPT.md sul checkout GAIA corrente. Completa soltanto Fase 0 e Fase 1: audit reale, motore AST riproducibile per Python e JS/TS, metriche normalizzate, baseline legacy versionata, eccezioni validate, controllo differenziale, test dello strumento, comandi locali, documentazione e report Checkpoint 1. Prima di editare registra branch, commit, working tree, perimetro e piano in docs/code-quality/PROGRESS.md. Preserva tutte le modifiche non correlate. Non installare o copiare la skill nel profilo globale Hermes. Non eseguire refactoring applicativi, non attivare gate CI bloccanti, non cambiare dipendenze framework, API, database o comportamento. Non creare commit, push o PR. Considera il goal completato solo quando i test dello strumento passano, il check ordinario e read-only, nuove violazioni e peggioramenti sintetici falliscono, la baseline non puo essere rigenerata per accettare regressioni e docs/code-quality/PROGRESS.md contiene evidenze e decisioni aperte. Se una decisione umana e necessaria, usa una stop condition, aggiorna docs/code-quality/PROGRESS.md e pausa il goal.
```

Alternativa: usare `/goal draft` con lo stesso testo per far generare a Hermes un
completion contract strutturato, controllarlo con `/goal show` e poi procedere.

## Gate

Non aggiungere gate che non esistono ancora. Quando Hermes ha creato e verificato
i comandi locali, puo aggiungere nella stessa sessione:

```text
/goal gate add make quality-test
/goal gate add make complexity-check
```

Se i nomi finali sono diversi, usare quelli documentati e realmente esistenti.

## Controllo

Durante l'esecuzione:

```text
/goal status
/goal show
```

In caso di scelta non reversibile o sovrapposizione con modifiche dell'utente:

```text
/goal pause
```

Il report finale deve dichiarare esplicitamente:

```text
CHECKPOINT 1 COMPLETATO - REFACTOR APPLICATIVO NON AVVIATO
```
