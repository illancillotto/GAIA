# Wiki Docs MCP - revisione del freeze

Data: 2026-10-05. Avvio: `main@44b0c4ac`.
Scope autorizzato: revisionare il delta del PRD Wiki rispetto al precedente
freeze e aggiornare soltanto la relativa entry del manifest, se ammissibile.

## Origine del drift

L'hash revisionato nel manifest corrisponde esattamente al PRD in `1995a1fc`:
`67501f4ecbda816a98b0324d743039c5b5574e409229956e8ebf1de0a38c88e8`.
Il commit `080cbdd6` aggiunge tre righe al PRD, senza aggiornare il freeze:

- rimando a `../../mcps/FINAL_CLOSURE_2026-10-03.md`;
- conferma storica della coverage e della build locale;
- chiarimento che il rilascio non e ancora attivo.

Nessuna altra differenza tra il documento approvato e quello corrente.
Il drift esiste nei blob committati: non dipende dai refactoring del parser,
di `load_corpus`, del servizio Docs o della valutazione offline.

## Revisione

Il report di [chiusura](../../mcps/FINAL_CLOSURE_2026-10-03.md) registra
coverage statement/branch del perimetro MCP e build locale verificate,
ma conserva il gate complessivo FAIL e i residui di pubblicazione/approvazione.
Le tre righe aggiunte sono coerenti con questa evidenza storica: non dichiarano
un deploy, una prova Claude live o il superamento del gate globale attuale.
Il resto del PRD e immutato rispetto alla versione gia revisionata.

Il delta non aggiunge dati personali, secret, prompt, risposte ai casi di
ground truth o contenuto preparato per migliorare il benchmark. I rimandi
restano semplici testo del PRD: il builder non espande i documenti collegati.
Questa review non introduce un re-audit del runtime o una nuova certificazione
dei risultati storici di coverage/build.

## Decisione e perimetro

Aggiornata la sola entry Wiki in `config/mcps/docs-manifest.json`, con reason
e hash revisionati:
`2b1938422cb60cb2b383b2a41186deaf21d3c5f7ef037f49eb5978a028f5aea4`.

Restano invariati path, dominio, categoria, status e included; Catasto,
Utenze e Ruolo non cambiano. Due documenti inclusi, nessuna nuova sorgente.
Questo report non viene aggiunto al corpus MCP. Nessuna modifica al PRD,
ai 32 casi congelati, al codice runtime, alle guardie hash, alle soglie o
alla baseline della complessita. Nessun commit, push, deploy o flag attivato.

## Confronto riproducibile

Il corpus precedente e ricostruito in una directory temporanea usando il
blob Wiki di `1995a1fc`, il documento Catasto dal checkout con hash verificato
e il manifest precedente. Nessun bypass della verifica hash e nessuna
modifica alle sorgenti per rendere verdi i test.

Prima: 59 chunk, 32 query, success rate e recall@10 `1.0`, MRR
`0.9833333333333333`, precision@10 `0.13873015873015873`.
Versione corpus precedente:
`6403a59b47c195dff2f38d4afe3bfb10c1223e8fc7ffb163852dc820936262f0`.
Evidenza: `/tmp/gaia-wiki-freeze-before-report.json`.

Le latenze sono misure locali diagnostiche, non un confronto prestazionale
controllato o una prova del proxy/modello live. Il cambio di hash/reason deve
produrre una nuova corpus_version; le query restano identiche.

Dopo: 59 chunk e due documenti inclusi; tutti i 32 casi conservano esito,
rank e numero risultati. Success rate, recall@10, MRR e precision@10
coincidono con il corpus precedente. Nuova corpus_version:
`424d100f9c1adedbee6516d2c18e3919426e30316793fefee07748dd0bdf3d3d`.

Le stime token non sono un invariante di una nuova versione documentale:
delta per caso da `-1` a `+37`, somma `+108`. Sono inclusi l'effetto del
contenuto aggiunto e della rappresentazione numerica degli score retrieval.
Un primo confronto troppo stretto di tutti i campi dei casi, incluse le
stime token, non passa; il confronto dei campi contrattualmente stabili
e degli score aggregati passa senza cambiare query, risultati o codice.
Evidenze: `/tmp/gaia-wiki-freeze-after-report.json` e comparison.log.

## Verifica finale

- Suite evaluation e contract: 12 passed, evaluation runtime full-file 100%.
  Le due failure hash preesistenti sono risolte, non saltate o indebolite.
- `make test-mcp QUALITY_PYTHON=backend/.venv/bin/python`: 295 passed,
  42 file runtime, 1990/1990 statement e 420/420 branch, coverage 100%
  su ciascun file, zero righe escluse o branch parziali.
- JSON manifest valido, whitespace verificato, nessuna modifica alla
  baseline complessita o ai gate/config coverage. Nessun runtime modificato
  da questa revisione; le slice precedenti restano nel working tree.
- Grafi Wiki docs e platform docs aggiornati tramite i rispettivi target
  make, verificando completamento dei chunk semantici e assenza warning.

Log locali: `/tmp/gaia-wiki-freeze-evaluation-tests.log`,
`/tmp/gaia-wiki-freeze-mcp-tests.log`, graph-wiki-docs.log e graph-platform-docs.log.
Il ripristino del freeze non risolve il debito globale della complessita e
non autorizza un rilascio, una pubblicazione esterna o l'attivazione di flag.
