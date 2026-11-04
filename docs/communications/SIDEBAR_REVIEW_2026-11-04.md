# Revisione UI PEC/email — 4 novembre 2026

> Snapshot storico del commit `86fa982d`. Il successivo intervento autorizzato
> risolve gli otto incrementi senza deroghe: stato corrente e rilascio in
> [SIDEBAR_RELEASE_2026-11-04](SIDEBAR_RELEASE_2026-11-04.md).

## Perimetro e risultato

Revisione del layout successiva al rilascio CED `f7bb4d9f`, realizzata e
verificata in checkout isolato. Nessun deployment in questo intervento.

Cinque runtime modificati sotto `frontend/src/components/communications/`:
`workspace.tsx`, `workspace-controls.tsx`, `use-workspace.ts`, `composer.tsx`,
`composer-form.tsx`. Tre file test modificati: unit `workspace.test.tsx` e
`composer.test.tsx`, E2E `communications.spec.ts`. Nessuna dipendenza, API,
migrazione, regola tributaria o configurazione del trasporto modificata.

## Comportamenti e test

| Comportamento | Verifica pertinente |
| --- | --- |
| Desktop: elenco e composizione affiancati, circa 50/50 | E2E `expectSidebarLayout`, PEC/email a 1440 px |
| Mobile: composizione dopo elenco, senza overflow pagina | E2E `expectSidebarLayout`, PEC/email a 390 px |
| Componi carica il recapito e i campi dell’avviso selezionato nella sidebar | Unit workspace: selezione di due avvisi; E2E recapito nel complementary |
| Cambio selezione elimina precedente composizione e documento | Unit workspace: cambio avviso e apertura comunicazione esistente |
| Campi prima del PDF, checklist dopo il documento | Unit composer: ordine DOM; E2E: posizione effettiva |
| Rendering integrale tre pagine, zoom e checklist necessari | E2E PEC/email, PDF sintetico reale e invio simulato |
| Permessi, sola lettura, errori API e aggiornamento bozza conservati | Suite Communications esistente, 34 casi |
| Tabella scorrevole, intestazione e azioni sticky; sidebar scorrevole desktop | Ispezione screenshot sintetici desktop/mobile e E2E senza overflow |

Alla creazione di una nuova comunicazione il PDF appare dopo il comando
«Crea bozza e snapshot PDF»: viene mostrato lo snapshot effettivo. Non è
introdotto un caricamento documentale alternativo o un’anteprima simulata.

## Verifiche eseguite

| Controllo | Risultato |
| --- | --- |
| `npm run test:coverage -- tests/unit/communications` con include dei cinque runtime | 34 PASS; 192/192 statement, 121/121 branch, 85/85 funzioni, 123/123 linee |
| `npm run test:unit -- --maxWorkers=2` | 349 file, 5.470 test PASS |
| `npm test` | 18 PASS |
| `npm run typecheck` | PASS |
| ESLint dei cinque runtime e tre test | PASS |
| `npm run build:clean` | PASS; warning legacy estranei conservati |
| Chromium `tests/e2e/communications.spec.ts` | 4 PASS, PEC/email desktop/mobile, 9,9 secondi |
| Screenshot sintetici desktop/mobile | Ispezionati: composizione, PDF e checklist nell’ordine previsto |
| `git diff --check` | PASS |
| Ratchet contro merge-base `origin/main` | PASS, zero finding |

I test usano API mock e un PDF sintetico di tre pagine: nessun destinatario,
account, invio o credenziale reale. Nessuna riga o ramo runtime scoperto;
nessuna nuova esclusione coverage. Policy e gate CI invariati.

Log privati `/tmp/gaia-comm-sidebar-*`; report coverage
`/tmp/gaia-comm-sidebar-coverage-final/coverage-final.json`. Il worktree isolato
è `/tmp/gaia-communications-sidebar-20261104`. Prima del ratchet definitivo
un tentativo era fallito per un symlink root `node_modules` non ignorato:
rimosso quel solo link di test, senza modificare configurazioni o sorgenti.

Il lint esteso ai test ha rilevato un `prefer-const` preesistente in
`composer.test.tsx`: corretto `let` in `const`, senza cambiare il test.
Lint degli otto file e gli otto casi composer rieseguiti dopo la correzione.

## Complessità e qualità

Confronto AST prima/dopo sui cinque file, senza refactoring hotspot:
86→85 callable; somme Cyc 193→194, Cog 121→123, LOC 325→330.
`ChannelWorkspace` passa Cyc/Cog/LOC 4/3/12→6/5/19 per la nuova struttura e
lo stato vuoto. `CandidateTable` resta Cyc11/Cog10 (LOC5→6);
`useCommunicationSelection` resta Cyc9/Cog11 (LOC32→33);
`CommunicationComposer` resta Cyc1/Cog0, LOC16→10. Due warning già presenti,
zero error-level e zero finding del ratchet. Nessuna riduzione di debito dichiarata.

Frontend nel dominio Communications esistente, componenti condivisi GAIA e
stesso viewer PDF.js. Nessuna architettura parallela, modifica backend o
cambiamento di autorizzazione. Nessun test rimosso o indebolito; eliminata
soltanto l’interazione con il vecchio slider del layout PDF/testo sostituito.

## Sincronizzazione baseline: FAIL, senza forzature

Il ratchet autorevole contro il merge-base `origin/main` passa. Il confronto
ulteriore con la baseline corrente del branch rifiuta la sincronizzazione
ordinaria della copia privata completa: otto incrementi nei file della change.
Non sono regressioni di test o nuove soglie violate, ma restano finding del
gate di aggiornamento e impediscono di dichiarare il quality gate completo PASS.

| Callable | Metrica | Prima → dopo |
| --- | --- | --- |
| ComposerForm | LOC | 22 → 23 |
| useCommunicationSelection | LOC | 32 → 33 |
| open | LOC | 8 → 9 |
| CandidateTable | LOC | 5 → 6 |
| NewCommunication | LOC | 12 → 13 |
| ChannelWorkspace | Cyc / Cog / LOC | 4/3/12 → 6/5/19 |

Comando eseguito nel worktree isolato:
`python3 tools/code_quality/complexity.py baseline --baseline /tmp/gaia-sidebar-baseline-private.json`.
Exit 1, `baseline_update_rejected`; log `/tmp/gaia-sidebar-baseline-sync.log`.
La baseline repository resta invariata; nessuna eccezione, esclusione o soglia
modificata. `baseline-verify` della nuova fotografia non eseguito: il comando
precedente non l’ha prodotta. Non è stata usata la riparazione del codice già
committato per aggirare il rifiuto. Residuo: risolvere o accettare esplicitamente
questi incrementi con una decisione distinta; non sono già autorizzati dal
record di debito Poste. Nessun refactoring artificiale introdotto per abbassare
le metriche tramite impaginazione o wrapper.

## Graphify

Aggiornato il corpus frontend con `make graphify-patch-force-pruning` e
`make graphify-frontend GRAPHIFY_CODE_FLAGS=--force`: 717/717 file,
7.113 nodi, 16.965 relazioni, 257 comunità. Il grafo HTML non è generato
perché supera il limite di 5.000 nodi; JSON e report sono aggiornati.
Il corpus documentale è aggiornato con `make graphify-platform-docs`: chunk
1/1 done, nessun semantic chunk failed; 10.185 token input e 1.307 output
(stima strumento $0,0062). Nessuna estrazione dalla root GAIA e nessun
`graphify-out/` versionato.

## Stato e limiti

La revisione UI è locale e pronta per revisione/rilascio; il server mantiene
il layout precedente. Lo stato CED e i trasporti restano quelli descritti nel
[report di rilascio](DEPLOYMENT_REPORT_2026-11-04.md). Nessun backend, worker,
DB o processo Poste riavviato. Il gate generale storico di FINAL_REVIEW.md
resta FAIL per le prove PG/GIS non verificate; questa verifica frontend non
lo sostituisce e non dichiara verificato alcun provider reale.

Modifiche concorrenti Poste, Presenze e configurazioni locali preservate ed
escluse dal perimetro. Documentazione aggiornata: PRD, ARCHITECTURE,
IMPLEMENTATION_PLAN, PROGRESS, OPERATIONS, TEST_REPORT e CHANGELOG.

FINAL QUALITY GATE — FAIL
