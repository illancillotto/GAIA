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

| Stato | Percorso | Segnale iniziale | Nota |
| --- | --- | --- | --- |
| reorganized | `backend/app/modules/presenze/router.py` | facade package; cognitive legacy sum/max `1.353/111`, cyclomatic legacy sum/max `1.139/64` | `REORGANIZED_AND_CHARACTERIZED`; 86 route e OpenAPI invariati, coverage 100%, file max LOC `718`; tre mismatch di identita contro baseline storica da risolvere separatamente |
| reorganized | `backend/app/modules/me/router.py` | facade package; cognitive legacy sum/max `123/38`, cyclomatic legacy sum/max `130/24` | `REORGANIZED_AND_CHARACTERIZED`; 17 route e OpenAPI invariati, coverage 100%, tutti i 29 fingerprint legacy e le metriche callable preservati, file max LOC `336` |
| reorganized | `backend/app/modules/gis/router.py` | facade package; cognitive legacy sum/max `6/2`, cyclomatic legacy sum/max `52/3` | `REORGANIZED_AND_CHARACTERIZED`; 51 operazioni e OpenAPI invariati, coverage 100%, tutti i 46 fingerprint legacy preservati, file max LOC `122` |
| candidate | `frontend/src/features/organigramma/organigramma-workspace.tsx` | circa 4.652 righe | Workspace React ad alto rischio di stato accoppiato |
| in_progress | `frontend/src/app/catasto/gis/page.tsx` | H2 cyc `538 -> 388`, cog `591 -> 435`, LOC `3007 -> 2341`; H3 controller/composer attivo | Cinque pannelli H2 coperti al 100%; resta il gate full-file della route |
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
