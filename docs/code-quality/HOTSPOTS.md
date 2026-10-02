# Hotspot backlog

Questo elenco non e una coda automatica di refactoring. Il quality ratchet opera
prima sul codice realmente toccato dagli sviluppi; un hotspot di questa lista si
apre solo quando ostacola feature, test o manutenzione e dopo una decisione
esplicita. Una iterazione neutra non autorizza il candidato successivo.

Questo elenco e un seed derivato da una ricognizione del repository. Non e la
baseline autorevole. Hermes deve sostituire dimensioni e priorita con i risultati
del motore AST e con la frequenza di modifica Git.

Snapshot di preparazione: `main` a
`79794c89e42e381a01d5dbbab36fa3a7abbde98d`, 2026-08-17.

## Candidati iniziali

Audit baseline globale e ordine delle tranche:
[BASELINE_RECOVERY.md](BASELINE_RECOVERY.md), 2026-09-15.

| Stato | Percorso | Segnale iniziale | Nota |
| --- | --- | --- | --- |
| reduced | `frontend/src/lib/catasto-anomalie.ts` / descrizione importi | `describeCatastoAnomalia` cog/cyc `60/32 -> 44/24`, LOC `54 -> 49` | `IMPROVED` 2026-10-02: descrizione condivisa delle voci VAL-07, testo e ordine invariati; aggregati cog/cyc `133/88 -> 122/85`, 35 test e full-file 100%, ratchet mirato verde; warning LOC eliminato, debito legacy residuo |
| reduced | `frontend/src/features/wiki/request-support-payload.ts` / query opzionale | `buildSupportHrefFromPayload` cog/cyc `10/11 -> 4/5`, LOC `23 -> 22` | `IMPROVED` 2026-10-02: chiavi ordinate e serializzazione comune preservano omissione, encoding e ordine; aggregati cog/cyc `16/22 -> 11/18`, zero violation nel file, 60 test e full-file 100%, ratchet mirato verde |
| reduced | `frontend/src/features/wiki/request-support-payload.ts` / mapping pathname | `inferModuleKeyFromPath` cog/cyc `12/13 -> 1/2`, LOC `15 -> 3` | `IMPROVED` 2026-10-02: tabella ordinata conserva startsWith e alias; aggregati cog/cyc `27/32 -> 16/22`, warning mapper rimosso, full-file 100% e ratchet mirato verde |
| reduced | `frontend/src/features/wiki/context-links.ts` | `buildWikiContextHref` cog `36 -> 23`, cyc `21` invariata, LOC `62 -> 61`, nesting `2 -> 1` | `IMPROVED` 2026-10-02: chiave assente normalizzata, guardia esterna eliminata; 29 test e full-file 100%, ratchet mirato verde; error cognitiva rimossa, ciclomatica legacy residua |
| reduced | `frontend/src/features/wiki/audit-utils.ts` | `buildWikiAuditStats` cog/cyc `15/15 -> 12/12`, LOC `59 -> 51` | `IMPROVED` 2026-10-02: Map delle modalita, sconosciute ignorate, nessun nuovo callable; aggregati cog/cyc `31/37 -> 25/31`, error `1 -> 0`, full-file 100%, ratchet mirato verde |
| blocked | `frontend/src/lib/api/core.ts` / risposte vuote | `request` cog/cyc/LOC `24/20/60` invariati | `NO_SAFE_CHANGE` 2026-10-02: guardia condivisa aumentava la cognitiva a 25, ripristinata; conservati 19 test di precedenza/parsing, nessun delta runtime della slice; scegliere un candidato diverso |
| reduced | `frontend/src/lib/api/core.ts` / lifecycle timeout-abort | `request` cog `28 -> 24`, cyc `22 -> 20`, LOC `62 -> 60` | `IMPROVED` 2026-10-02: cleanup in finally e guardia ridondante rimossa, nessun nuovo helper; 842 test API, full-file 100%, ratchet mirato verde; error cognitiva rimossa, ciclomatica legacy residua |
| reduced | `frontend/src/lib/api/core.ts` | `request` cog `54 -> 28`, cyc `30 -> 22`, LOC `82 -> 62` | `IMPROVED` 2026-10-02: decoder HTTP privato sotto soglia error, cognitiva aggregata `155 -> 147`; 833 test API e coverage full-file 100%, ratchet mirato verde; debito timeout/abort e decoder Blob/XHR residuo |
| reduced | `frontend/src/lib/network-device-utils.ts` | `getNetworkDeviceAdminUrl` cog `22 -> 18`, cyc `12` invariata, LOC `28 -> 24`, nesting `3 -> 2` | `IMPROVED` 2026-10-01: risoluzione target appiattita senza helper; 30 test e coverage full-file 100%, ratchet mirato verde, due warning residui |
| reduced | `frontend/src/features/wiki/request-support-payload.ts` | `buildWikiRequestPayload` cyc `10 -> 6`, cog `13 -> 5`, LOC `61 -> 49` | `IMPROVED` 2026-09-22: campi comuni consolidati senza helper, target sotto soglia, due warning distinti residui; 27 test e coverage full-file 100% |
| closed | `frontend/src/lib/document-preview.ts` | `getDocumentPreviewKind` cyc `12 -> 9`, cog `15 -> 9`, LOC `23` invariata | `IMPROVED` 2026-09-22: estensione normalizzata una volta, tre guard null eliminati, zero violation nel file; 13 test e coverage full-file 100% |
| blocked | `frontend/src/app/gis/catalogo/guided-workflow.ts` / `guidedChangeValidation` | cognitive `17`, cyclomatic `12`, LOC `29`, invariati | `NO_SAFE_CHANGE` 2026-09-22: nessuna semplificazione locale convincente individuata; dieci test di precedenza/confine aggiunti, 33 test complessivi e coverage 100%; scegliere un candidato diverso |
| reorganized | `frontend/src/app/gis/strumenti/activity-center.tsx` | Componente cyc `15 -> 10`, cog `14 -> 9`, LOC `95 -> 62` | `REORGANIZED_AND_CHARACTERIZED` 2026-09-22; lifecycle in hook locale sotto soglia, error `2 -> 0`, due warning residui; decisioni aggregate invariate, 24 test e coverage full-file 100% |
| reduced | `frontend/src/app/gis/catalogo/guided-workflow.ts` | `geometryFromCoordinates` cyc `15 -> 10`; slice 2026-09-22 `coordinatesFromGeometry` cyc `11 -> 9`, cog `13 -> 10`, LOC `19 -> 17` | `IMPROVED`; rami Polygon/MultiLineString unificati, aggregati ridotti senza estrazioni, zero error e quattro warning nel file, 23 test e coverage full-file 100%; baseline globale ancora da recuperare |
| reorganized | `backend/app/modules/presenze/router.py` | facade package; cognitive legacy sum/max `1.353/111`, cyclomatic legacy sum/max `1.139/64` | `REORGANIZED_AND_CHARACTERIZED`; 86 route e OpenAPI invariati, coverage 100%, file max LOC `718`; tre mismatch di identita contro baseline storica da risolvere separatamente |
| reorganized | `backend/app/modules/me/router.py` | facade package; cognitive legacy sum/max `123/38`, cyclomatic legacy sum/max `130/24` | `REORGANIZED_AND_CHARACTERIZED`; 17 route e OpenAPI invariati, coverage 100%, tutti i 29 fingerprint legacy e le metriche callable preservati, file max LOC `336` |
| reorganized | `backend/app/modules/gis/router.py` | facade package; cognitive legacy sum/max `6/2`, cyclomatic legacy sum/max `52/3` | `REORGANIZED_AND_CHARACTERIZED`; 51 operazioni e OpenAPI invariati, coverage 100%, tutti i 46 fingerprint legacy preservati, file max LOC `122` |
| candidate | `frontend/src/features/organigramma/organigramma-workspace.tsx` | circa 4.652 righe | Workspace React ad alto rischio di stato accoppiato |
| reduced | `frontend/src/app/catasto/gis/page.tsx` | Controlli e archivio 2026-09-07: cyc `386 -> 302`, cog `433 -> 338`, LOC file `2619 -> 2187` | `IMPROVED`; otto runtime GIS al 100% full-file, archivio caratterizzato e ratchet GIS verde; restano debito legacy della pagina e sincronizzazione baseline globale separata |
| reduced | `frontend/src/app/catasto/particelle/[id]/page.tsx` | Catasto-H1 `CatastoParticellaDetailPage` cyc `131 -> 3` cog `145 -> 2` LOC `656 -> 42` | Hotspot dedicato chiuso; perimetro aggregato senza violation error-level |
| reduced | `frontend/src/app/gis/strumenti/tools-workspace.tsx` | GIS-H8 `GisToolsWorkspace` cyc `60 -> 2` cog `72 -> 1` LOC `226 -> 17` | Hotspot dedicato chiuso; warning LOC residuo sull'hook |
| candidate | `frontend/src/lib/api.ts` | circa 5.833 righe | Valutare quanto e dichiarativo prima di priorizzarlo |
| candidate | `frontend/src/app/presenze/giornaliere/page.tsx` | file molto grande | Misurare componenti, hook e handler |
| candidate | `backend/app/modules/ruolo/tributi_repositories.py` | circa 4.233 righe | Dominio critico; refactor solo con caratterizzazione forte |
| candidate | `frontend/src/app/ruolo/tributi/page.tsx` | file molto grande | Dominio critico e UI complessa |
| candidate | `frontend/src/components/elaborazioni/capacitas-workspace.tsx` | file molto grande | Verificare stato, effetti e confini feature |
| reorganized | `backend/app/modules/catasto/routes/anagrafica.py` | facade package; cognitive sum/max `2.101/363`, cyclomatic sum/max `1.367/135` | `REORGANIZED_AND_CHARACTERIZED`; 13 operazioni e OpenAPI invariati, coverage 100%, file max LOC `712`, ratchet verde senza aggiornare la baseline |
| reorganized | `backend/app/modules/network/router.py` | facade package; cognitive sum/max `1.101/209`, cyclomatic sum/max `774/109` | `REORGANIZED_AND_CHARACTERIZED`; 39 endpoint e OpenAPI invariati, coverage 100%, nessun file estratto sopra soglia LOC |
| candidate | `backend/app/modules/gis/services.py` | circa 2.580 righe | Servizio ad alto rischio di responsabilita multiple |
| candidate | `modules/elaborazioni/worker/worker.py` | circa 1.676 righe | Preservare retry, concorrenza e lifecycle |
| reorganized | `frontend/src/types/api.ts` | `0` callable; facciata di 8 righe su 7 barrel dominio, tutti i file sotto soglia | `REORGANIZED_AND_CHARACTERIZED`; nessun runtime o contratto pubblico modificato |
| reorganized | `frontend/src/lib/api.ts` | facciata su 15 moduli; cognitive sum/max `545/54`, cyclomatic sum/max `851/30` | `REORGANIZED_AND_CHARACTERIZED`; 450 export preservati, coverage completa, warning file-level residuo in `network.ts` |
| reorganized | `backend/app/modules/utenze/router.py` | facade package + route modules; cognitive sum/max `409/39`, cyclomatic sum/max `403/28` | `REORGANIZED_AND_CHARACTERIZED`; OpenAPI identica, coverage 100%, warning LOC residuo in `routes/support.py` |

## Dati da aggiungere dopo la Fase 1

| Percorso | Max cognitive | Max cyclomatic | Densita | Violazioni | Churn 90d | Rischio | Priorita |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| - | - | - | - | - | - | - | - |

## Regole di selezione

1. Il candidato deve essere misurato dal motore corrente.
2. LOC da sole non determinano la priorita.
3. Preferire una slice con test esistenti e comportamento osservabile.
4. Evitare come primo intervento un dominio fiscale/catastale critico se manca
   caratterizzazione.
5. Considerare churn e difetti storici.
6. Un file dichiarativo puo diventare eccezione stretta, non un refactoring
   artificiale.
7. Ogni goal sposta una sola riga in `in_progress`.

## Stati

- `candidate`: da misurare;
- `ready`: invarianti e test individuati;
- `in_progress`: un solo goal attivo;
- `reduced`: metriche ridotte, debito residuo presente;
- `closed`: sotto soglia o responsabilita adeguatamente separate;
- `blocked`: serve decisione o test mancante;
- `exception-review`: possibile codice dichiarativo da valutare.
- `reorganized`: ownership migliorata senza dichiarare una riduzione di complessita callable.
