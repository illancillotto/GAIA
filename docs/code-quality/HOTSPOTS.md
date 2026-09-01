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
| candidate | `backend/app/modules/presenze/router.py` | circa 5.099 righe | Router molto esteso; verificare separazione endpoint/service |
| candidate | `frontend/src/features/organigramma/organigramma-workspace.tsx` | circa 4.652 righe | Workspace React ad alto rischio di stato accoppiato |
| in_progress | `frontend/src/app/catasto/gis/page.tsx` | H2 cyc `538 -> 388`, cog `591 -> 435`, LOC `3007 -> 2341`; H3 controller/composer attivo | Cinque pannelli H2 coperti al 100%; resta il gate full-file della route |
| reduced | `frontend/src/app/catasto/particelle/[id]/page.tsx` | Catasto-H1 `CatastoParticellaDetailPage` cyc `131 -> 3` cog `145 -> 2` LOC `656 -> 42` | Hotspot dedicato chiuso; perimetro aggregato senza violation error-level |
| reduced | `frontend/src/app/gis/strumenti/tools-workspace.tsx` | GIS-H8 `GisToolsWorkspace` cyc `60 -> 2` cog `72 -> 1` LOC `226 -> 17` | Hotspot dedicato chiuso; warning LOC residuo sull'hook |
| candidate | `frontend/src/lib/api.ts` | circa 5.833 righe | Valutare quanto e dichiarativo prima di priorizzarlo |
| candidate | `frontend/src/app/presenze/giornaliere/page.tsx` | file molto grande | Misurare componenti, hook e handler |
| candidate | `backend/app/modules/ruolo/tributi_repositories.py` | circa 4.233 righe | Dominio critico; refactor solo con caratterizzazione forte |
| candidate | `frontend/src/app/ruolo/tributi/page.tsx` | file molto grande | Dominio critico e UI complessa |
| candidate | `frontend/src/components/elaborazioni/capacitas-workspace.tsx` | file molto grande | Verificare stato, effetti e confini feature |
| candidate | `backend/app/modules/catasto/routes/anagrafica.py` | circa 3.869 righe | Router da separare senza cambiare precedenza/contratti |
| candidate | `backend/app/modules/network/router.py` | circa 2.886 righe | Verificare accoppiamento tra endpoint e logica |
| candidate | `backend/app/modules/gis/services.py` | circa 2.580 righe | Servizio ad alto rischio di responsabilita multiple |
| candidate | `modules/elaborazioni/worker/worker.py` | circa 1.676 righe | Preservare retry, concorrenza e lifecycle |
| exception-review | `frontend/src/types/api.ts` | circa 4.930 righe | Probabile file dichiarativo; non esentare senza verifica |

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
