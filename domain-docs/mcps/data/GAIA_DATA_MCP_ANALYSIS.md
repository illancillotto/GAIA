# GAIA Data MCP — analisi iniziale del runtime

> Stato: pre-analisi. Deve essere completata dal team sul branch/commit usato per l'implementazione.

## Obiettivo

Identificare il sottoinsieme di Catasto, Utenze e Ruolo necessario alla replica sintetica e ai tool MCP.

## Evidenze già presenti nel runtime

### Utenze

Il runtime contiene modelli quali:
- `AnagraficaSubject` → `ana_subjects`;
- `AnagraficaPerson` → `ana_persons`;
- `AnagraficaCompany` → `ana_companies`;
- `AnagraficaDocument` → `ana_documents`.

Il soggetto costituisce un nodo naturale per collegare anagrafica e Ruolo.

La replica sintetica non deve replicare automaticamente ANPR, snapshot, job di import e document classification.

### Ruolo

Il runtime contiene almeno:
- `RuoloAvviso` → `ruolo_avvisi`, con riferimento opzionale a `ana_subjects`;
- `RuoloPartita` → `ruolo_partite`;
- `RuoloParticella` → `ruolo_particelle`;
- strutture di pagamento e stato avviso.

`RuoloParticella` contiene collegamenti verso entità Catasto, confermando l'esistenza di query cross-domain Catasto ↔ Ruolo.

### Catasto

Il registry Catasto espone numerose entità, tra cui:
- `CatDistretto`;
- `CatParticella`;
- `CatIntestatario`;
- `CatUtenzaIrrigua`;
- `CatUtenzaIntestatario`;
- `CatDomandaIrrigua`;
- `CatDomandaIrriguaParticella`.

Nel modello condiviso sono presenti anche `CatComune`, distretti, punti di consegna, dati GIS e altre entità.

Per la tesi va selezionato un sottoinsieme minimo.

## Sottoinsieme candidato

```text
Soggetto
  |
  +--> Utenza irrigua
          |
          +--> Particella
                  |
                  +--> Comune
                  |
                  +--> Distretto

Soggetto
  |
  +--> Avviso di ruolo
          |
          +--> Partita
                  |
                  +--> Particella di ruolo
                          |
                          +--> Particella Catasto

Avviso di ruolo
  |
  +--> Pagamenti / stato
```

## Entità da escludere inizialmente

Salvo necessità sperimentale:
- job di import;
- audit di allineamento;
- snapshot tecnici;
- ANPR;
- Capacitas dettagli operativi;
- code/scheduler;
- GIS complesso e geometrie complete;
- history completa;
- log tecnici;
- workflow di modifica.

## Questioni da verificare

- [ ] relazione canonica Utenze ↔ CatUtenzaIrrigua;
- [ ] chiave di collegamento soggetto ↔ intestatario;
- [ ] relazione effettiva Utenza ↔ Particella;
- [ ] relazione Distretto ↔ Particella/Utenza;
- [ ] modello canonico degli avvisi attualmente usato dal frontend;
- [ ] eventuale prevalenza di `ana_payment_notices` rispetto a tabelle legacy;
- [ ] stato dei read model inCASS;
- [ ] permission scope reali;
- [ ] endpoint già riutilizzabili;
- [ ] query già presenti che possono diventare service MCP.

## Valutazione Operazioni

| Voce | Esito |
|---|---|
| Entità utili | TODO |
| Relazioni con Catasto/Utenze | TODO |
| Query aggiuntive | TODO |
| Tool aggiuntivi | TODO |
| Costo implementativo | TODO |
| Raccomandazione | TODO |

## Decisione metodologica

La replica sintetica non è una copia completa del DB GAIA. È una **replica funzionale minima** finalizzata a testare l'accesso agentico a dati strutturati mantenendo relazioni realistiche.
