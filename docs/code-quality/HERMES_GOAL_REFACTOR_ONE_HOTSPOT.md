# Hermes Goal - un hotspot

## Prerequisiti

- Checkpoint 1 approvato.
- Baseline e check differenziale presenti e verdi.
- Hotspot selezionato da report AST e registrato in `HOTSPOTS.md`.
- Test di caratterizzazione esistenti o aggiungibili senza cambiare il dominio.
- Working tree controllato.

## Comando generico

Sostituire `<HOTSPOT>` e `<MODULO>` prima di incollare:

```text
/goal Riduci in modo misurabile la complessita di un solo hotspot GAIA: <HOTSPOT>, modulo <MODULO>. Leggi integralmente e segui la skill di progetto skills/gaia-complexity-reduction/SKILL.md e i relativi riferimenti. Leggi docs/code-quality/README.md, docs/code-quality/PLAN.md, docs/code-quality/PROGRESS.md, docs/code-quality/METRICS_AND_BASELINE.md, docs/code-quality/VALIDATION.md e docs/code-quality/HOTSPOTS.md. Prima di modificare codice, registra in docs/code-quality/PROGRESS.md invarianti, test di caratterizzazione, metriche prima, slice minima e file previsti. Mantieni invariati API, payload, database, auth, semantica di dominio, transazioni, concorrenza e comportamento UI. Preserva modifiche non correlate. Non installare o copiare la skill nel profilo globale Hermes. Implementa una sola unita revisionabile e non passare a un secondo hotspot. Esegui lint e test mirati, copertura al 100% dei file runtime modificati, complexity check, type-check/build quando applicabile e diff review. Il goal e completo solo se almeno una metrica primaria dell'hotspot diminuisce, nessuna metrica primaria o aggregata peggiora, non compaiono nuove violation o failure, la baseline si riduce soltanto del debito realmente rimosso e docs/code-quality/PROGRESS.md e docs/code-quality/HOTSPOTS.md riportano evidenze prima/dopo. Non creare commit, push o PR salvo richiesta esplicita. Se gli invarianti sono ambigui o il refactoring richiede un cambio funzionale, aggiorna docs/code-quality/PROGRESS.md e pausa.
```

## Gate consigliati

Usare solo target esistenti e gia verificati:

```text
/goal gate add make quality-test
/goal gate add make complexity-check
```

Aggiungere inoltre il comando di test mirato del modulo. Evitare la suite globale
come unico gate: un test mirato produce evidenza piu utile e distingue meglio le
failure preesistenti.

## Definition of done del singolo goal

- un hotspot soltanto;
- invarianti espliciti;
- metriche prima/dopo registrate;
- test di caratterizzazione verdi;
- coverage richiesta rispettata;
- nessun contratto funzionale modificato;
- baseline ridotta, mai allargata;
- progress e backlog aggiornati;
- debito residuo dichiarato;
- nessun secondo refactoring iniziato.
