# R58 — Complexity Slice Report

## Ownership

Ownership preventiva in MULTI_AGENT_OWNERSHIP_R58_INACTIVE_VEHICLES_2026-10-12.md.
Coordinator integrazione, autore /root/r58_inactive_vehicle_author, reviewer
indipendente thread01a12d47. Worktree SSD autore/reviewer e branch dedicate;
integrazione su refactor/complexity-campaign-20261008, non su main.

## Baseline

HEAD114fbf7196382c6446a7963c34bd89e4c9795ef5; main/merge-base
55a1b1d35911451e018b662c2acc450bf5994ea2. Originale ammesso R52 analytics0aa1f196.
Report originale fresco original-format-tail/complexity.json; candidato
root-evidence/candidate/complexity.json SHA33c957c3ddb1b92375167190b8850920e8eacf745dd87319735318a1e8aef484.
Baseline38e6b794 e matcher32b11750 invariati. Nessun riferimento operativo al7/10.

## Target callable

anomalies_analytics: sola emissione degli eventi inactive_vehicle, non query,
orchestrazione di altre anomalie o fuel_analytics.

## Behavioral invariants

Query/bind/loading byte-equivalenti; nessun nuovo filtro o confine transazionale.
Rifornimenti prima delle sessioni; sorting stabile e inserimento dei conteggi
identici. Payload, etichette, conversioni, ID/date/null/falsy e permessi invariati.
Letture lazy dell'ID e short-circuit targa/codice; codice riletto nei dettagli;
conversione litri prima del codice dettagli. Eccezioni propagate nello stesso ordine.

## Characterization tests

| Behavior | Existing test | Missing | Added | Result |
|---|---|---|---|---|
| Payload/fallback/litri/controlli attivi | R27 e suite analytics | casi DB completi | 18 persistiti | PASS |
| Status/dispatch/confini/default/inversione date | suite analytics | contratti completi | 13 persistiti | PASS |
| Query/bind/ordine/ORM/sorting/conteggi | R27 parziale | query reali e stato | 4 persistiti | PASS |
| Login/401/403/200/type alias | auth preesistente | payload HTTP esatto | 2 HTTP | PASS |
| Mapper null/transitori/whitespace/letture/errori | nessuno per nuovo servizio | confine puro | 49 puri | PASS |

Tutti i457 casi storici conservati, senza rimozioni o assertion indebolite.
37 nuovi persistiti/HTTP più49 puri: totale543, non543 test persistiti.

## Changes

Due mapper fuel/session e label policy condivisa nel modulo Operazioni.
Route modificata soltanto nell'import e nei due costruttori di risposta.
Nessun megahelper, Context, relocation massiva o modifica funzionale.

## Metric before

Principale238 cognitive/112 cyclomatic/320LOC/nesting4/params5.
File route1193LOC/29callable/cognitiveSUM723/cyclomaticSUM501.
Decisioni AST fisiche342. Python useState/useEffect non applicabili.

## Metric after

Principale221/104/302/nesting4/params5. Route1179LOC, mapper33LOC/3callable.
Helper cognitive3/2/0, nessun finding. Somma posseduta711cognitive/501cyclomatic.
Decisioni340. Tutti i survivor e gli altri file/metriche invariati.

## Delta

Principale -17 cognitive(-7,14%), -8 cyclomatic, -18LOC. Netto cognitive -12
(-1,66%), non -17 globale. Decisioni -2; cyclomaticSUM invariata, LOC combinate
+19(+1,59%). Nessun credito su finding, parametri, nesting o coda estrema.
Globale1676file20345callable332660LOC/1920error2735warning4655finding.
Applicativo1621file19014callable319060LOC/1912error2680warning4592finding.
Coda3>300/17>200/55>100 invariata. Finding sovrapposti, non problemi indipendenti.

## Tests

Original81385:416genuine+78supplemental PASS, Ruff0/custody0, formatFAIL.
STOP37record bc8b6686 preservato. Solo tre wrapping corretti, AST6b24→bc260
esattamente equivalente; tail67599 completa format/report/ratchet/diff/custody0,
senza ripetere test verdi. Reviewer accetta questa lineage composita d0dc087e.
Mapper47713:49PASS/0skip/Ruff/format/custody0. Candidate91594:494PASS/0skip,
tutti7gate0/custody0; identità e molteplicità JUnit esatte, gate aggiuntivo disgiunto.
Comandi esatti nei rispettivi *.argv.json. Nessuna suite completa finale implicita.

## Coverage

Candidate full-file: analytics625/625statement252/252branch; driver49/49 e16/16;
orphan27/27 e10/10; mapper8/8statement e0/0branch (denominatore nullo dichiarato).
Nessuna nuova esclusione: guard originali413/414/883/884 diventano417/418/887/888
per le quattro righe import aggiunte; sorgenti dei guard byte-identici.
I49 contratti verificano i percorsi booleani anche senza archi coverage misurati.

## Ratchet

make complexity-ratchet BASE_REF=main: PASS, zero finding nuovi. Nessuna baseline,
soglia, esclusione o configurazione aggiornata. Metadata audit iniziale FAIL
su scope.files1675→1676 preservato; V2 confronta policy esattamente e conta
l'unico nuovo file posseduto, exit0. Nessun retry native per correggere l'audit.

## Classification

IMPROVED: cognitive aggregata -12 e due decisioni duplicate eliminate.
Audit indipendente candidato c9e22328. Global check separato exit2: stessa
ambiguità GAIA users/useEffect[0]<callback>/4candidati, non attribuita alla slice
né automaticamente alle30 divergenze storiche. Baseline provenance resta separata.

## Files changed

- backend/app/modules/operazioni/routes/analytics.py
- backend/app/modules/operazioni/services/inactive_vehicle_anomalies.py
- backend/tests/test_operazioni_inactive_vehicle_r58.py
- backend/tests/test_operazioni_inactive_vehicle_mapper_r58.py
- Ownership, progress, report globale e documentazione Operazioni.

## Commit

Non creato. Integrazione via apply_patch, nessun Git merge/push/commit/main edit.

## Residual risks

Suite backend completa R56 precede R58; frontend/build R54/R55 precedono R57.
449 skip backend, worker coverage ed E2E quota restano non certificati.
Presenze R43 resta non ammessa: distinta decisione sui test strict pendente.
Prima falsa segnalazione del reviewer sui guard preservata e rettificata su
V3 byte-esatto, senza modifica del gate. Campagna ACTIVE/INCOMPLETE.

## Recommended next slice

Fermare questa responsabilità. Priorità alla progettazione Presenze già scelta,
solo dopo risoluzione della distinta decisione fixture; non ampliare R58.

## Evidence

SSD .codex-gaia-campaign-20261012-r58-inactive-vehicles/root-evidence conserva
originale, STOP, tail, mapper, candidato, audit metriche e companion R57.
Graphify codice Operazioni force/pruning PASS541nodes1549edges30communities;
grafo ignorato, non prova di complessità. Manutenzione docs registrata a parte.

Independent final e77e8aec imported byte-exact, reviewer freeze52621da8.
Domain docs Graphify PASS125nodes159edges11communities, chunk1/1done/zero failed
semantic chunks,801input4266outputtokens/$0.0071. Platform docs graph and
publication receipt finali restano manutenzione Coordinator, non prove metriche.
Prima ricevuta platform-docs PASS641nodes757edges129communities,
chunk1/1done/no failed semantic chunks,6976input1865outputtokens/$0.0058.
Sincronizzazione conclusiva dei documenti di stato eseguita separatamente;
nessun test, coverage o risultato complessità dedotto dai grafi.
