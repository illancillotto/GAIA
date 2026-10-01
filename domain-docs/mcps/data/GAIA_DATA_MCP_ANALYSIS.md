# GAIA Data MCP — analisi iniziale del runtime

> Stato: audit runtime completato su commit base `6b61fd27`, v1 implementata.

## Decisioni verificate per la v1

- `CatUtenzaIntestatario` in `backend/app/models/catasto_phase1.py` lega
  esplicitamente `cat_utenze_irrigue` e `ana_subjects` tramite FK; non inferire
  il legame dai nomi o dal legacy `cat_intestatari`.
- `CatUtenzaIrrigua` contiene annualita, comune e FK particella; la replica
  esplicita le relazioni M:N con validita annuale per i casi sperimentali.
- `CatParticella` ha `comune_id`, riferimenti catastali, superficie mq e
  `num_distretto`; il distretto operativo e un'entita distinta con geometria
  propria. Replica senza geometrie, con FK distretto sintetico esplicita.
- `RuoloAvviso`/`RuoloPartita`/`RuoloParticella` sono il read model consultato
  dalle route `/ruolo/avvisi`; `RuoloParticella.cat_particella_id` e una FK
  reale. Le righe sintetiche comprimono partita/particella conservando il link.
- `RuoloTributiPayment.avviso_id` e `RuoloTributiAvvisoStatus.avviso_id` legano
  pagamenti/stati al ruolo. `ana_payment_notices` e una superficie distinta
  inCASS/avvisi speciali, non sostituisce automaticamente il ruolo consultato.
- Le query live dei repository e le route legacy hanno payload, permessi e
  dipendenze operative ampi: non sono riutilizzate dalla replica isolata.
  Il service v1 implementa le stesse responsabilita minime con query fisse.
- Moduli canonici `utenze`, `catasto`, `ruolo`; permission resolver GAIA
  controlla anche le sezioni. La v1 aggiunge scope read-only al gateway,
  non tratta i flag presenti in un argomento del modello come autorizzazioni.

Divergenze: proposta originale in ettari vs runtime mq; nomi `syn_*` vs
tabelle semplici del DB sintetico isolato; migration PostgreSQL sperimentale
storica senza tutte le FK/status richieste vs nuovo schema locale completo.
La v1 conserva il monolite e isola fisicamente il DB di esperimento, senza
connessione o credenziali operative. Test automatici negano URL/DB reali.

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

- [x] relazione canonica Utenze ↔ CatUtenzaIrrigua;
- [x] chiave di collegamento soggetto ↔ intestatario;
- [x] relazione effettiva Utenza ↔ Particella;
- [x] relazione Distretto ↔ Particella/Utenza;
- [x] modello canonico degli avvisi attualmente usato dal frontend;
- [x] eventuale prevalenza di `ana_payment_notices` rispetto a tabelle legacy;
- [x] stato dei read model inCASS;
- [x] permission scope reali;
- [x] endpoint già riutilizzabili;
- [x] query già presenti che possono diventare service MCP.

## Valutazione Operazioni

| Voce | Esito |
|---|---|
| Entità utili | `operator_activity`, `field_report` |
| Relazioni con Catasto/Utenze | FK correnti verso utenti, team, veicoli/GPS; nessuna FK diretta particella nelle entita esaminate |
| Query aggiuntive | Attivita/segnalazioni territoriali, richiedono matching spaziale e policy personale |
| Tool aggiuntivi | Eventuale ricerca attivita/segnalazioni, fuori catalogo core |
| Costo implementativo | Alto rispetto al core: GIS, personale, allegati e ulteriori scope |
| Raccomandazione | Escludere v1; eventuale estensione richiede decisione separata |

## Decisione metodologica

La replica sintetica non è una copia completa del DB GAIA. È una **replica funzionale minima** finalizzata a testare l'accesso agentico a dati strutturati mantenendo relazioni realistiche.
