# Dotazioni nel cruscotto operatori — 2026-10-02

Aggiornamento 2026-10-03: gate della change isolata **PASS**, incluso il
cruscotto full-file al 100%; vedi `GATE_CLOSURE_2026-10-03.md`. Il testo sotto
conserva la cronologia delle prove, non certifica i lavori concorrenti.

## Scope e comportamento

Il pannello `OperatorAssets` consuma le API Dotazioni nella scheda
dell'operatore selezionato. Usa soltanto `detail.operator.gaia_user_id`, non
`wc_id`, UUID operatore, identita Presenze o matching nome/email. Senza
mapping nessuna richiesta; 403/errori API sono locali al pannello.
La chiave del componente e l'operatore del dettaglio caricato: al cambio la
vecchia richiesta viene invalidata e non mostra custodie della persona precedente.
Non viene rimontato il vecchio dettaglio con la chiave della nuova selezione.
Nessuna modifica backend, schema DB, permessi, dati operativi o Inventory.
La protezione esistente del cruscotto (Accessi, admin/super-admin) e invariata;
le API Dotazioni mantengono il proprio controllo di autorizzazione.

## Matrice comportamento/test

File `frontend/tests/unit/operatori-cruscotto.test.tsx`:

| Comportamento | Test |
| --- | --- |
| Custodie da identita GAIA, errore permesso isolato | `uses only canonical GAIA identity and isolates Dotazioni permission failures` |
| Cambio operatore, nessuna nuova richiesta per il vecchio custode e risposte tardive | `switches custody by the detail canonical identity and discards stale responses` |
| Mapping assente, nessun fallback nomi/ID | `does not infer identity from names, email or equal namespace identifiers` |
| Riepiloghi Presenze/rete/mezzi e link conservati | `preserves canonical mappings, presence, network and vehicle summaries` |
| Domini non accessibili, nessuna richiesta | `does not fetch inaccessible domains` |
| Cataloghi/record paginati e peer aggregati | `paginates catalogs and presence records without skipping operators`; `paginates daily records and aggregates duplicate peers` |
| Dati vuoti/sparsi, formattazione, filtri | `shows empty domains and healthy operators with search and anomaly filters`; `aggregates peers, tolerates sparse summaries and invalid dates/numbers` |
| Sessione assente e errori separati | `handles missing session and empty operator lists`; `reports base errors without crashing`; `reports detail errors separately` |
| Cancellazioni e selezione concorrente | test `ignores ...` e `does not apply a late detail response to another selected operator` |

`dotazioni-workflows.test.tsx` copre anche il pannello riutilizzato, compresi
mapping nullo, caricamento, lista e errori API. Nessun test artificiale o
esclusione coverage introdotta.

## Coverage e quality ratchet

37 test passati con i due file test; INTERO cruscotto e `OperatorAssets`:
100% statement (310/310), branch (380/380), funzioni (82/82), linee (267/267).
Lint mirato, typecheck e `git diff --check` passati.

Semplificazione locale di invarianti gia presenti: bundle creato soltanto
dopo dettaglio valido, `detail` ora non nullable; rimossi fallback opzionali
impossibili nella scheda caricata e guardia ridondante della riga selezionata.
Iniziali da token non vuoti; suffisso numerico sempre esplicito nei callsite.
Nessun refactoring esteso o split per nascondere metriche.
Componente principale: ciclomatica 140→135, cognitiva 153→148, LOC 695→694.
Ratchet contro merge-base `6b61fd27`: zero finding, baseline non modificata.
Il debito legacy resta alto, senza peggioramento.

## Regression gate ed ambiente

- `npm test`: 18/18 passati.
- Suite frontend globale ripetuta con accesso ambiente ripristinato:
  269 file e 3693 test passati prima dell'ultima correzione del rimontaggio;
  dopo la correzione 268 file passati, 1 fallito; 3704 test passati, 1 fallito.
  Failure: `catasto-gis-page.test.tsx:261`, `exercises the primary map, popup
  and tool workflows`, timeout di 5000ms. Il run avveniva durante la build
  e altri lavori concorrenti: non basta per attribuire il problema al carico
  o escludere una regressione. Nessuna modifica al test Catasto o ai timeout.
  Rerun isolato dello stesso file: 31/31 passati (9.79s); il successo isolato
  non rende verde il run globale e non dimostra da solo la causa del timeout.
- Script build repository `./scripts/frontend_clean_build.sh`: PASS nel
  retry con accesso Docker. La build pulita ha riparato la cache runtime:
  il primo avvio browser aveva restituito Internal Server Error per
  `/app/.next/routes-manifest.json` mancante. Warning legacy estranei restano.
- `operatori-cruscotto-dotazioni.spec.ts` e `dotazioni.spec.ts`: 3 E2E Chromium
  passati, API simulate e ID coincidente WC/GAIA per verificare il fail-closed.
  Il test tollera le richieste iniziali duplicate in StrictMode, controlla
  che tutte usino l'ID canonico e che selezionare una persona senza mapping
  non produca nuove richieste. Il browser ha rilevato un rimontaggio transitorio
  del vecchio dettaglio: corretto allineando chiave e dati del pannello;
  aggiunta anche un'asserzione di regressione nel test unitario del cambio.
- Graphify docs Dotazioni e piattaforma ripetuti: entrambi `chunk 1/1 done`,
  senza warning semantic failure; 98 nodi/157 edge e 2330 nodi/5317 edge
  rispettivamente nel primo retry. Costi stimati $0.0091 e $0.0066.
  Questi risultati sostituiscono i tentativi parziali bloccati dalla rete.
  Refresh Dotazioni dopo la correzione e il primo aggiornamento del report:
  `chunk 1/1 done`, 109 nodi/173 edge, costo stimato $0.0053.
  Grafo frontend ricontrollato: 624/624 file AST, nessun cambio di topologia.

## File e residui

Runtime modificato: `frontend/src/app/gaia/users/operatori-cruscotto/page.tsx`.
Nuovi test unit/E2E del cruscotto; documentazione Dotazioni/Accessi/piattaforma.
Il componente Dotazioni esistente e riutilizzato senza duplicare logica.
Working tree concorrente preservato, nessun commit o modifica baseline.
Browser E2E non piu bloccato; il timeout Catasto nel rerun globale resta una
failure da non ignorare. I gate globali precedenti (ratchet piattaforma,
lint backend e regression backend completo) non sono certificati risolti da
questo retry frontend. Log aggiornati in `/tmp/dotazioni-recheck-*.log`.

FINAL QUALITY GATE — FAIL
