# Rapporto completo sulla complessità GAIA — 8 ottobre 2026

## 1. Sintesi esecutiva

GAIA presenta un debito di complessità significativo, distribuito su molti file e con picchi molto elevati nei componenti frontend e nell'orchestrazione backend. La maggior parte dei callable rimane piccola, ma alcuni concentrano centinaia di decisioni. I miglioramenti locali documentati non corrispondono ancora a una riduzione globale consistente.

- Perimetro ufficiale dello scanner: **1.665 file**, **20.261 callable**, **4.714 segnalazioni**: 1.956 error e 2.758 warning.
- Separando i test worker inclusi dal glob: **1.611 file applicativi**, **18.940 callable**, **318.856 LOC effettive** e **4.651 segnalazioni**.
- 2.339 callable applicativi (12,35%) presentano almeno una segnalazione; 788 file (48,91%) sono coinvolti.
- Il picco cognitivo è **550** in Presenze giornaliere, rispetto alla soglia di errore **25**.
- Il confronto differenziale locale contro il merge-base di main è **PASS**, zero finding. Il finding Presenze comunicato nel primo riepilogo è stato eliminato da una modifica concorrente prima della nuova scansione.
- Il confronto integrale contro la baseline registrata resta **FAIL**, con **30 divergenze**, tutte su file invariati rispetto a HEAD.
- Nessun refactoring, modifica di baseline o esecuzione di test applicativi è incluso in questo audit.

## 2. Identità e validità dello snapshot

- Branch analizzato: main.
- Commit sorgente e merge-base con main: 55a1b1d35911451e018b662c2acc450bf5994ea2.
- Inizio acquisizione: 2026-10-08T11:51:11.607433+00:00.
- Report AST generato: 2026-10-08T11:51:57.302516+00:00, equivalente alle **13:51:57 Europe/Rome** dell'8 ottobre 2026.
- Baseline caricata dal commit 55a1b1d35911451e018b662c2acc450bf5994ea2; provenance interna della baseline: 11ed944a46ebdeb32ad50c14e7fca90b2c55f1fd.
- Nessuna variazione rilevata nei percorsi e negli SHA256 dei file sorgente tra l'inizio e la fine della scansione.
- Python AST: runtime 3.12.3; Babel AST: Node v24.14.0, parser disponibile, versione dell'adapter 1.
- Errori di parsing: **0**. Errori di configurazione delle eccezioni: **0**. Eccezioni configurate: **0**.
- Preflight del confronto: scope invariato, motori compatibili e integrità della baseline verificata.

Il working tree contiene sviluppi concorrenti Presenze, Ruolo e documentazione. I conteggi includono i file non tracciati rientranti nel perimetro. Il commit identifica la base Git, non da solo il contenuto delle modifiche locali. Gli hash uguali ai confini della scansione supportano la stabilità dello snapshot acquisito, ma non trasformano il working tree in un commit immutabile. Questo rapporto non certifica modifiche successive.

## 3. Perimetro e significato delle misure

Sono analizzati i pattern versionati dello scanner:

- backend/app/**/*.py
- frontend/src/**/*.js
- frontend/src/**/*.jsx
- frontend/src/**/*.ts
- frontend/src/**/*.tsx
- modules/elaborazioni/worker/**/*.py

Il glob worker include anche **54 file di test**, con 1.321 callable e 63 segnalazioni, di cui 8 error e 55 warning. Le tabelle applicative li separano senza cambiare il perimetro dei gate. I test backend e frontend nelle directory esterne a questi pattern non entrano nei conteggi di complessità.

Esclusioni dello scanner:

- **/__pycache__/**
- **/.pytest_cache/**
- **/.ruff_cache/**
- **/.next/**
- **/node_modules/**
- **/coverage/**
- **/htmlcov/**
- **/graphify-out/**
- backend/alembic/versions/*.py
- **/*.min.js
- **/*.d.ts
- **/fixtures/**
- **/__snapshots__/**

Il rapporto non misura tutto il codice versionato del repository: script esterni a questi alberi, CI, Docker/Compose, configurazioni, Go, CSS e migration non costituiscono un audit completo in questo perimetro. La policy di coverage GAIA è più ampia e resta distinta.

Le segnalazioni sono coppie entità/metrica oltre soglia: una funzione può produrre più segnalazioni. Error indica severità metrica, non un bug funzionale, una vulnerabilità o un errore di parsing. Callable comprende funzioni, metodi e callback riconosciuti dagli adapter; non equivale a una responsabilità di dominio indipendente.

## 4. Soglie operative

| Metrica callable | Warning da | Error da |
| --- | --- | --- |
| Ciclomatica | 10 | 15 |
| Cognitiva | 15 | 25 |
| LOC effettive | 50 | 80 |
| Annidamento | 4 | 5 |
| Parametri | 5 | 7 |

| Metrica file | Warning da | Error da |
| --- | --- | --- |
| LOC effettive | 500 | 800 |
| useState | 10 | 20 |
| useEffect | 5 | 8 |

Le soglie sono inclusive. LOC esclude righe vuote e commenti secondo l'implementazione locale. La cognitiva è lo score definito dagli adapter GAIA: decisioni e annidamento, non una misura certificata Sonar. La ciclomatica è anch'essa quella dell'implementazione locale.

Gli adapter attraversano anche callable annidati nel calcolo del contenitore e possono poi registrarli separatamente. Quindi le somme cognitive e ciclomatiche dei callable **non rappresentano decisioni uniche**: possono includere sovrapposizioni. Non vanno sommate per stimare ore di lavoro o numero minimo di test. Il JSX dichiarativo non è di per sé una decisione, mentre espressioni condizionali e logiche nel rendering contribuiscono allo score.

I conteggi useState/useEffect e import del frontend sono ottenuti con pattern testuali nel file, non con una risoluzione semantica dei binding. Alias, wrapper o testo non eseguibile possono influenzarli. Gli hook sono riportati **per file**, non attribuiti automaticamente a un unico componente. Import count non è fan-in/fan-out né una misura affidabile del coupling.

## 5. Quadro quantitativo per area

| Area senza test worker | File | Callable | LOC file | Error | Warning | File coinvolti | Callable coinvolti |
| --- | --- | --- | --- | --- | --- | --- | --- |
| backend | 921 | 6.301 | 160.226 | 1.035 | 1.688 | 446 | 1.429 |
| frontend | 652 | 12.063 | 149.559 | 878 | 881 | 317 | 810 |
| worker | 38 | 576 | 9.071 | 35 | 134 | 25 | 100 |
| Totale | 1.611 | 18.940 | 318.856 | 1.948 | 2.703 | 788 | 2.339 |

| Area | Quota callable con segnalazioni | Massimo cognitivo |
| --- | --- | --- |
| backend | 22,68% | 366 |
| frontend | 6,71% | 550 |
| worker | 17,36% | 122 |

Il backend ha il maggior numero assoluto di segnalazioni; il frontend presenta i maggiori picchi individuali. Il worker è più piccolo ma mantiene percorsi ad alta complessità nell'automazione browser. Le percentuali tra linguaggi non sono una classifica di qualità: il frontend registra numerose callback piccole e gli adapter differiscono.

## 6. Distribuzione: mediana e coda

| Metrica callable applicativi | Mediana | P90 | P95 | P99 | Massimo |
| --- | --- | --- | --- | --- | --- |
| cognitive | 1 | 10 | 16 | 48 | 550 |
| cyclomatic | 2 | 9 | 13 | 34 | 457 |
| loc | 7 | 31 | 48 | 172 | 2.631 |
| nesting | 0 | 2 | 2 | 3 | 13 |
| params | 1 | 3 | 4 | 6 | 18 |

La mediana cognitiva è 1 e il percentile 95 è 16. La maggioranza del codice non è un monolite, ma la coda arriva a 550. Questo sostiene un intervento selettivo sulle responsabilità difficili da cambiare, non un refactoring uniforme dell'intero repository. I percentili sono empirici, senza interpolazione, sull'insieme di callable riconosciuti.

## 7. Segnalazioni per metrica

| Livello | Metrica | Error | Warning | Totale |
| --- | --- | --- | --- | --- |
| callable | cognitive | 507 | 590 | 1.097 |
| callable | cyclomatic | 704 | 939 | 1.643 |
| callable | loc | 445 | 481 | 926 |
| callable | nesting | 34 | 103 | 137 |
| callable | params | 182 | 523 | 705 |
| file | loc | 65 | 97 | 162 |
| file | useEffect | 10 | 11 | 21 |
| file | useState | 9 | 14 | 23 |

Questa tabella usa il perimetro ufficiale, inclusi i test worker. Le categorie non identificano funzioni distinte: la stessa funzione può superare cognitiva, ciclomatica, LOC e parametri. Le LOC file sono un segnale secondario, soprattutto nei modelli/schema dichiarativi.

## 8. Domini e sottosistemi con maggior debito

| Gruppo di percorsi | File | Callable | Error | Warning | Totale | Max cognitiva |
| --- | --- | --- | --- | --- | --- | --- |
| backend/catasto | 74 | 784 | 186 | 233 | 419 | 146 |
| backend/ruolo | 83 | 784 | 117 | 230 | 347 | 95 |
| backend/presenze | 107 | 875 | 93 | 240 | 333 | 87 |
| backend/wiki | 124 | 678 | 108 | 193 | 301 | 188 |
| backend/elaborazioni-services-legacy | 22 | 456 | 120 | 156 | 276 | 269 |
| backend/operazioni | 49 | 302 | 103 | 107 | 210 | 366 |
| frontend/components/elaborazioni | 40 | 1.244 | 82 | 108 | 190 | 472 |
| frontend/components/catasto | 70 | 1.017 | 83 | 101 | 184 | 246 |
| frontend/app/presenze | 33 | 1.232 | 78 | 101 | 179 | 550 |
| backend/utenze | 36 | 334 | 65 | 111 | 176 | 67 |
| worker/runtime | 38 | 576 | 35 | 134 | 169 | 122 |
| backend/elaborazioni | 78 | 522 | 50 | 96 | 146 | 101 |
| frontend/app/operazioni | 24 | 748 | 98 | 48 | 146 | 144 |
| backend/network | 34 | 239 | 75 | 65 | 140 | 209 |
| frontend/features/wiki | 27 | 644 | 68 | 62 | 130 | 166 |
| frontend/app/catasto | 36 | 906 | 60 | 56 | 116 | 390 |
| frontend/app/ruolo | 20 | 577 | 64 | 37 | 101 | 204 |
| backend/gis | 45 | 391 | 16 | 71 | 87 | 27 |
| backend/riordino | 71 | 192 | 34 | 51 | 85 | 47 |
| frontend/app/network | 13 | 557 | 56 | 29 | 85 | 183 |

I gruppi sono costruiti dalle directory, non da una classificazione semantica: backend/app/modules usa il nome del modulo; i servizi elaborazioni legacy sono separati; app, components e features frontend restano distinti. Le righe frontend di uno stesso dominio non vanno lette come moduli indipendenti. La decomposizione completa è nell'appendice B.

Catasto ha il maggior volume di segnalazioni tra i moduli backend; Ruolo contiene il singolo file più carico; Presenze combina debito backend e il principale picco frontend. Wiki/MCP è incluso nell'audit: esclusioni operative di vecchie campagne non costituiscono esclusioni della misurazione attuale.

## 9. File principali per accumulo di segnalazioni

| File | LOC | Callable | Error | Warning | Max cognitiva | Commit nella finestra |
| --- | --- | --- | --- | --- | --- | --- |
| [backend/app/modules/ruolo/tributi_repositories.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/ruolo/tributi_repositories.py:1) | 3.693 | 178 | 59 | 58 | 59 | 5 |
| [backend/app/services/elaborazioni_capacitas_terreni.py:1](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_terreni.py:1) | 1.905 | 66 | 42 | 39 | 102 | 0 |
| [frontend/src/app/presenze/giornaliere/page.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/app/presenze/giornaliere/page.tsx:1) | 3.009 | 310 | 26 | 29 | 550 | 4 |
| [backend/app/modules/ruolo/repositories.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/ruolo/repositories.py:1) | 1.885 | 40 | 29 | 21 | 95 | 1 |
| [frontend/src/features/organigramma/organigramma-workspace.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/features/organigramma/organigramma-workspace.tsx:1) | 3.597 | 350 | 32 | 16 | 167 | 2 |
| [frontend/src/components/elaborazioni/capacitas-workspace.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/components/elaborazioni/capacitas-workspace.tsx:1) | 3.109 | 251 | 24 | 20 | 472 | 0 |
| [backend/app/modules/operazioni/routes/mobile_sync.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/operazioni/routes/mobile_sync.py:1) | 1.907 | 58 | 22 | 21 | 83 | 2 |
| [frontend/src/app/operazioni/analisi/page.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/app/operazioni/analisi/page.tsx:1) | 1.627 | 136 | 25 | 17 | 56 | 0 |
| [backend/app/services/elaborazioni_capacitas_incass.py:1](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_incass.py:1) | 1.126 | 55 | 14 | 21 | 68 | 5 |
| [backend/app/modules/gis/services.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/gis/services.py:1) | 2.169 | 109 | 14 | 20 | 27 | 4 |
| [backend/app/modules/operazioni/routes/analytics.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/operazioni/routes/analytics.py:1) | 1.305 | 27 | 19 | 14 | 366 | 0 |
| [frontend/src/app/ruolo/tributi/page.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/app/ruolo/tributi/page.tsx:1) | 3.051 | 224 | 21 | 11 | 204 | 0 |
| [backend/app/modules/network/services.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/network/services.py:1) | 1.451 | 67 | 18 | 14 | 195 | 1 |
| [frontend/src/components/catasto/gis/MapContainer.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/components/catasto/gis/MapContainer.tsx:1) | 1.411 | 74 | 23 | 8 | 246 | 3 |
| [backend/app/modules/utenze/services/import_service.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/utenze/services/import_service.py:1) | 1.618 | 67 | 11 | 20 | 53 | 1 |
| [backend/app/modules/catasto/services/ade_wfs.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/catasto/services/ade_wfs.py:1) | 2.002 | 41 | 21 | 9 | 58 | 0 |
| [backend/app/modules/riordino/services/block_service.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/riordino/services/block_service.py:1) | 829 | 38 | 13 | 17 | 39 | 0 |
| [backend/app/modules/utenze/anpr/service.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/utenze/anpr/service.py:1) | 1.016 | 26 | 16 | 13 | 67 | 0 |
| [backend/app/modules/catasto/routes/anagrafica/matching.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/catasto/routes/anagrafica/matching.py:1) | 704 | 17 | 12 | 17 | 44 | 10 |
| [backend/app/modules/catasto/services/gis_service.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/catasto/services/gis_service.py:1) | 1.657 | 55 | 16 | 12 | 42 | 0 |
| [frontend/src/app/catasto/anomalie/page.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/app/catasto/anomalie/page.tsx:1) | 2.267 | 197 | 11 | 16 | 390 | 0 |
| [backend/app/modules/catasto/routes/anomalie.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/catasto/routes/anomalie.py:1) | 754 | 19 | 13 | 14 | 48 | 1 |
| [backend/app/modules/catasto/routes/import_routes.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/catasto/routes/import_routes.py:1) | 636 | 19 | 4 | 22 | 29 | 0 |
| [frontend/src/components/elaborazioni/settings-workspace.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/components/elaborazioni/settings-workspace.tsx:1) | 1.887 | 127 | 9 | 16 | 402 | 2 |
| [frontend/src/components/elaborazioni/bonifica-sync-workspace.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/components/elaborazioni/bonifica-sync-workspace.tsx:1) | 1.137 | 104 | 13 | 11 | 259 | 0 |
| [frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx:1) | 1.103 | 90 | 9 | 14 | 181 | 3 |
| [backend/app/modules/operazioni/services/import_fleet_transactions.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/operazioni/services/import_fleet_transactions.py:1) | 643 | 24 | 10 | 13 | 83 | 0 |
| [backend/app/modules/wiki/services/orchestrator.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/services/orchestrator.py:1) | 737 | 15 | 16 | 7 | 67 | 0 |
| [backend/app/services/gate_mobile_sync.py:1](/home/cbo/CursorProjects/GAIA/backend/app/services/gate_mobile_sync.py:1) | 1.090 | 54 | 11 | 12 | 51 | 2 |
| [modules/elaborazioni/worker/browser_session.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/browser_session.py:1) | 1.254 | 81 | 4 | 19 | 47 | 3 |

La graduatoria ordina il numero totale di segnalazioni e poi il massimo cognitivo. Non normalizza per dimensione e non è un ordine automatico di refactoring. I commit nella finestra sono quelli restituiti da Git a partire dal 2026-09-08, non modifiche non committate o frequenza d'uso in produzione.

## 10. Callable principali per complessità cognitiva

| File e riga | Callable | Cognitiva | Ciclomatica | LOC | Nesting | Parametri |
| --- | --- | --- | --- | --- | --- | --- |
| [frontend/src/app/presenze/giornaliere/page.tsx:816](/home/cbo/CursorProjects/GAIA/frontend/src/app/presenze/giornaliere/page.tsx:816) | PresenzeGiornalierePage | 550 | 457 | 2.275 | 3 | 0 |
| [frontend/src/components/elaborazioni/capacitas-workspace.tsx:528](/home/cbo/CursorProjects/GAIA/frontend/src/components/elaborazioni/capacitas-workspace.tsx:528) | ElaborazioniCapacitasWorkspace | 472 | 416 | 2.631 | 2 | 1 |
| [frontend/src/components/elaborazioni/settings-workspace.tsx:350](/home/cbo/CursorProjects/GAIA/frontend/src/components/elaborazioni/settings-workspace.tsx:350) | ElaborazioniSettingsWorkspace | 402 | 334 | 1.565 | 2 | 1 |
| [frontend/src/app/utenze/\[id\]/page.tsx:214](/home/cbo/CursorProjects/GAIA/frontend/src/app/utenze/[id]/page.tsx:214) | DetailContent | 391 | 304 | 1.908 | 2 | 1 |
| [frontend/src/app/catasto/anomalie/page.tsx:175](/home/cbo/CursorProjects/GAIA/frontend/src/app/catasto/anomalie/page.tsx:175) | CatastoAnomaliePageContent | 390 | 342 | 2.109 | 2 | 0 |
| [backend/app/modules/operazioni/routes/analytics.py:338](/home/cbo/CursorProjects/GAIA/backend/app/modules/operazioni/routes/analytics.py:338) | fuel_analytics | 366 | 208 | 402 | 4 | 5 |
| [backend/app/modules/operazioni/routes/analytics.py:1102](/home/cbo/CursorProjects/GAIA/backend/app/modules/operazioni/routes/analytics.py:1102) | anomalies_analytics | 365 | 160 | 388 | 4 | 5 |
| [frontend/src/app/catasto/gis/page.tsx:298](/home/cbo/CursorProjects/GAIA/frontend/src/app/catasto/gis/page.tsx:298) | CatastoGisPage | 334 | 298 | 1.896 | 4 | 0 |
| [frontend/src/app/me/me-page-content.tsx:347](/home/cbo/CursorProjects/GAIA/frontend/src/app/me/me-page-content.tsx:347) | MePageContent | 271 | 256 | 1.133 | 2 | 1 |
| [backend/app/services/elaborazioni_bonifica_sync.py:354](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_bonifica_sync.py:354) | _run_bonifica_sync_background | 269 | 47 | 232 | 13 | 3 |
| [frontend/src/components/elaborazioni/bonifica-sync-workspace.tsx:332](/home/cbo/CursorProjects/GAIA/frontend/src/components/elaborazioni/bonifica-sync-workspace.tsx:332) | ElaborazioniBonificaSyncWorkspace | 259 | 202 | 835 | 4 | 1 |
| [frontend/src/components/catasto/gis/MapContainer.tsx:453](/home/cbo/CursorProjects/GAIA/frontend/src/components/catasto/gis/MapContainer.tsx:453) | MapContainer | 246 | 169 | 953 | 3 | 1 |
| [frontend/src/app/presenze/collaboratori/\[id\]/page.tsx:100](/home/cbo/CursorProjects/GAIA/frontend/src/app/presenze/collaboratori/[id]/page.tsx:100) | PresenzeCollaboratoreDetailPage | 233 | 212 | 1.600 | 2 | 0 |
| [frontend/src/components/elaborazioni/batch-detail-workspace.tsx:53](/home/cbo/CursorProjects/GAIA/frontend/src/components/elaborazioni/batch-detail-workspace.tsx:53) | ElaborazioneBatchDetailWorkspace | 216 | 177 | 751 | 3 | 1 |
| [frontend/src/app/presenze/export/page.tsx:266](/home/cbo/CursorProjects/GAIA/frontend/src/app/presenze/export/page.tsx:266) | PresenzeExportPage | 209 | 172 | 1.097 | 3 | 0 |
| [backend/app/modules/network/router/helpers/traffic.py:264](/home/cbo/CursorProjects/GAIA/backend/app/modules/network/router/helpers/traffic.py:264) | _build_network_statistics_summary | 209 | 109 | 226 | 4 | 2 |
| [backend/app/modules/organigramma/services/whitecompany_sync.py:198](/home/cbo/CursorProjects/GAIA/backend/app/modules/organigramma/services/whitecompany_sync.py:198) | sync_from_whitecompany | 205 | 77 | 290 | 6 | 2 |
| [frontend/src/app/ruolo/tributi/page.tsx:404](/home/cbo/CursorProjects/GAIA/frontend/src/app/ruolo/tributi/page.tsx:404) | RuoloTributiPageContent | 204 | 173 | 1.064 | 3 | 0 |
| [backend/app/modules/network/services.py:1158](/home/cbo/CursorProjects/GAIA/backend/app/modules/network/services.py:1158) | run_network_scan | 195 | 101 | 267 | 3 | 5 |
| [backend/app/modules/wiki/services/conversation_metrics.py:150](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/services/conversation_metrics.py:150) | refresh_wiki_conversation_daily_metrics | 188 | 49 | 155 | 7 | 3 |
| [frontend/src/components/utenze/utenze-subjects-section.tsx:56](/home/cbo/CursorProjects/GAIA/frontend/src/components/utenze/utenze-subjects-section.tsx:56) | UtenzeSubjectsSection | 184 | 169 | 991 | 3 | 1 |
| [frontend/src/app/network/tracking/page.tsx:406](/home/cbo/CursorProjects/GAIA/frontend/src/app/network/tracking/page.tsx:406) | TrackingContent | 183 | 159 | 913 | 2 | 1 |
| [frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx:295](/home/cbo/CursorProjects/GAIA/frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx:295) | AnagraficaBulkPanel | 181 | 155 | 839 | 2 | 0 |
| [frontend/src/app/catasto/import/page.tsx:77](/home/cbo/CursorProjects/GAIA/frontend/src/app/catasto/import/page.tsx:77) | CatastoImportPage | 175 | 149 | 1.114 | 3 | 0 |
| [frontend/src/app/utenze/import/page.tsx:102](/home/cbo/CursorProjects/GAIA/frontend/src/app/utenze/import/page.tsx:102) | ImportContent | 173 | 160 | 971 | 1 | 1 |
| [frontend/src/app/ruolo/page.tsx:176](/home/cbo/CursorProjects/GAIA/frontend/src/app/ruolo/page.tsx:176) | RuoloDashboardPage | 168 | 157 | 1.147 | 1 | 0 |
| [frontend/src/features/organigramma/organigramma-workspace.tsx:1537](/home/cbo/CursorProjects/GAIA/frontend/src/features/organigramma/organigramma-workspace.tsx:1537) | OrganigrammaWorkspace | 167 | 147 | 1.086 | 2 | 1 |
| [frontend/src/features/wiki/WikiRequestsPage.tsx:230](/home/cbo/CursorProjects/GAIA/frontend/src/features/wiki/WikiRequestsPage.tsx:230) | WikiRequestsPage | 166 | 132 | 759 | 3 | 1 |
| [frontend/src/app/gaia/users/page.tsx:283](/home/cbo/CursorProjects/GAIA/frontend/src/app/gaia/users/page.tsx:283) | GaiaUsersPage | 162 | 146 | 1.011 | 2 | 0 |
| [frontend/src/app/presenze/configurazione/page.tsx:271](/home/cbo/CursorProjects/GAIA/frontend/src/app/presenze/configurazione/page.tsx:271) | PresenzeConfigurazionePage | 158 | 148 | 1.135 | 1 | 0 |

Presenze giornaliere arriva a 22 volte la soglia cognitiva di errore; il workspace Capacitas a 18,88 volte. Analytics Operazioni concentra due callable oltre 360. Questi valori indicano che una slice deve separare una responsabilità verificabile, non spostare tutto il corpo in un helper e dichiarare il file risolto.

## 11. Stato React e annidamento

| File | useState | useEffect |
| --- | --- | --- |
| [frontend/src/features/organigramma/organigramma-workspace.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/features/organigramma/organigramma-workspace.tsx:1) | 23 | 25 |
| [frontend/src/app/utenze/\[id\]/page.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/app/utenze/[id]/page.tsx:1) | 28 | 10 |
| [frontend/src/app/catasto/gis/page.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/app/catasto/gis/page.tsx:1) | 28 | 8 |
| [frontend/src/app/ruolo/tributi/page.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/app/ruolo/tributi/page.tsx:1) | 25 | 10 |
| [frontend/src/app/catasto/anomalie/page.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/app/catasto/anomalie/page.tsx:1) | 24 | 10 |
| [frontend/src/app/presenze/giornaliere/page.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/app/presenze/giornaliere/page.tsx:1) | 21 | 13 |
| [frontend/src/components/elaborazioni/capacitas-workspace.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/components/elaborazioni/capacitas-workspace.tsx:1) | 31 | 2 |
| [frontend/src/components/utenze/utenze-create-subject-trigger.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/components/utenze/utenze-create-subject-trigger.tsx:1) | 30 | 1 |
| [frontend/src/app/operazioni/analisi/page.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/app/operazioni/analisi/page.tsx:1) | 18 | 9 |
| [frontend/src/app/presenze/configurazione/page.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/app/presenze/configurazione/page.tsx:1) | 22 | 1 |

Questi sono segnali da verificare con le transizioni UI e le dipendenze degli effetti. Non dimostrano che serva un reducer, un nuovo hook o una libreria di stato. Eventuali estrazioni devono preservare ordine degli effetti, cleanup, race, selezioni e rendering.

| File e riga | Callable | Nesting | Cognitiva | Ciclomatica |
| --- | --- | --- | --- | --- |
| [backend/app/services/elaborazioni_bonifica_sync.py:354](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_bonifica_sync.py:354) | _run_bonifica_sync_background | 13 | 269 | 47 |
| [backend/app/modules/wiki/services/conversation_metrics.py:150](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/services/conversation_metrics.py:150) | refresh_wiki_conversation_daily_metrics | 7 | 188 | 49 |
| [backend/app/modules/catasto/routes/anagrafica/execution.py:288](/home/cbo/CursorProjects/GAIA/backend/app/modules/catasto/routes/anagrafica/execution.py:288) | execute_bulk_search_payload | 7 | 126 | 31 |
| [backend/app/modules/organigramma/services/whitecompany_sync.py:198](/home/cbo/CursorProjects/GAIA/backend/app/modules/organigramma/services/whitecompany_sync.py:198) | sync_from_whitecompany | 6 | 205 | 77 |
| [modules/elaborazioni/worker/autodoc_sync.py:336](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/autodoc_sync.py:336) | run_autodoc_sync_job_by_id | 6 | 122 | 46 |
| [backend/app/modules/organigramma/services/visibility_service.py:153](/home/cbo/CursorProjects/GAIA/backend/app/modules/organigramma/services/visibility_service.py:153) | compute_visibility | 6 | 102 | 43 |
| [backend/app/modules/wiki/routes/conversations.py:137](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/routes/conversations.py:137) | resolve_conversation_context_link | 6 | 71 | 24 |
| [backend/app/modules/wiki/services/orchestrator.py:147](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/services/orchestrator.py:147) | _build_orchestration_plan | 6 | 67 | 31 |

La sincronizzazione Bonifica raggiunge nesting 13. L'annidamento elevato suggerisce attenzione a retry, fallimenti parziali e side effect; questo audit non ha dimostrato equivalenza funzionale di alcuna riscrittura.

## 12. Worker: hotspot applicativi

| File e riga | Callable | Cognitiva | Ciclomatica | LOC |
| --- | --- | --- | --- | --- |
| [modules/elaborazioni/worker/autodoc_sync.py:336](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/autodoc_sync.py:336) | run_autodoc_sync_job_by_id | 122 | 46 | 145 |
| [modules/elaborazioni/worker/posta_online_client.py:286](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/posta_online_client.py:286) | PostaOnlineBrowserClient.scrape_registered_mails | 73 | 41 | 80 |
| [modules/elaborazioni/worker/visura_flow.py:371](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/visura_flow.py:371) | execute_visura_flow | 71 | 30 | 168 |
| [modules/elaborazioni/worker/posta_online_sync.py:151](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/posta_online_sync.py:151) | run_posta_online_registered_mail_job_by_id | 68 | 39 | 124 |
| [modules/elaborazioni/worker/browser_session.py:218](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/browser_session.py:218) | BrowserSession.login | 47 | 19 | 56 |

L'automazione dei portali esterni richiede preservazione di login, retry, sessioni, timeout, documenti e diagnostica. Le simulazioni di trasporto non equivalgono al collaudo contro SISTER/Poste reali. I 15 finding baseline nei test worker non sono errori del runtime worker.

## 13. Frequenza di modifica e priorità pratica

| File | Commit dal 2026-09-08 | Segnalazioni | Max cognitiva |
| --- | --- | --- | --- |
| [backend/app/modules/catasto/routes/anagrafica/exports.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/catasto/routes/anagrafica/exports.py:1) | 26 | 9 | 15 |
| [backend/app/modules/catasto/routes/anagrafica/matching.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/catasto/routes/anagrafica/matching.py:1) | 10 | 29 | 44 |
| [backend/app/modules/catasto/routes/anagrafica/resolvers.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/catasto/routes/anagrafica/resolvers.py:1) | 10 | 21 | 36 |
| [backend/app/modules/catasto/routes/anagrafica/execution.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/catasto/routes/anagrafica/execution.py:1) | 8 | 6 | 126 |
| [backend/app/modules/presenze/services/schedule_engine.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/presenze/services/schedule_engine.py:1) | 8 | 16 | 55 |
| [backend/app/modules/presenze/services/gate_mobile_payloads.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/presenze/services/gate_mobile_payloads.py:1) | 8 | 1 | 11 |
| [frontend/src/components/layout/navigation.ts:1](/home/cbo/CursorProjects/GAIA/frontend/src/components/layout/navigation.ts:1) | 7 | 4 | 49 |
| [modules/elaborazioni/worker/worker.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/worker.py:1) | 6 | 21 | 41 |
| [backend/app/modules/catasto/routes/anagrafica/intestatari.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/catasto/routes/anagrafica/intestatari.py:1) | 6 | 11 | 16 |
| [frontend/src/app/gaia/users/page.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/app/gaia/users/page.tsx:1) | 5 | 21 | 162 |

La frequenza di modifica è un indicatore grezzo: i refactoring recenti possono aumentare il churn senza aumentare il rischio. Zero commit nella finestra non significa codice morto o irrilevante. Export/matching Catasto e schedule Presenze meritano attenzione quando vengono toccati da feature: il ratchet ordinario è più appropriato di una campagna trasversale. Non sono stati usati traffico produttivo, incidenti, tempi di delivery o ownership approvata per calcolare un indice di rischio.

## 14. Andamento rispetto al 7 ottobre

| Metrica | Iniziale 7/10 | Finale corretto 7/10 | Attuale 8/10 | Delta vs iniziale |
| --- | --- | --- | --- | --- |
| files | 1.645 | 1.656 | 1.665 | +20 |
| callables | 20.150 | 20.210 | 20.261 | +111 |
| errors | 1.968 | 1.961 | 1.956 | -12 |
| warnings | 2.742 | 2.747 | 2.758 | +16 |
| violations | 4.710 | 4.708 | 4.714 | +4 |

Rispetto allo snapshot iniziale: error **0,61% in meno**, warning **0,58% in più**, segnalazioni complessive **0,08% in più**. Il perimetro cresce di 20 file e 111 callable.

Rispetto al finale corretto del 7/10: error -5, warning +11, totale +6.

Gli snapshot confrontano working tree diversi e lavoro concorrente: questi delta non misurano una sola change. La campagna del 7/10 documenta sul proprio perimetro 153→146 error e 166→158 warning, circa -4,70% di segnalazioni nelle sole slice; non è una riduzione globale del repository. I target storici -50% error e -25% warning non risultano raggiunti.

Fonti: [docs/code-quality/GLOBAL_CAMPAIGN_2026-10-07.md:65](/home/cbo/CursorProjects/GAIA/docs/code-quality/GLOBAL_CAMPAIGN_2026-10-07.md:65) e /tmp/gaia-complete-audit.json. Lo snapshot accepted-final precedente è esplicitamente superato dal finale corretto e non è usato qui come risultato di accettazione.

## 15. Ratchet locale e disallineamento globale

**Confronto locale: PASS, zero finding.** Baseline del merge-base 55a1b1d35911451e018b662c2acc450bf5994ea2, confrontata mediante la funzione compare dello stesso scanner e il diff comprensivo dei file non tracciati. Scope, integrità e compatibilità dei motori sono stati verificati separatamente.

Il primo audit delle 13:38 segnalava build_presenze_mobile_record_payload, LOC 32→33. Nello snapshot delle 13:51 il callable è tornato a **LOC 32**, cognitiva 2, ciclomatica 3, parametri 6. Questa variazione deriva dal lavoro concorrente: l'audit non ha modificato la sorgente. Il risultato aggiornato sostituisce il FAIL locale del riepilogo precedente.

Il comportamento concreto del checker confronta tutte le metriche primarie dei callable riconosciuti nella baseline: può rifiutare +1 LOC anche sotto la soglia LOC. Non richiede che proprio la metrica peggiorata fosse già oltre soglia.

**Confronto integrale: FAIL, 30 finding.** Tutti riguardano percorsi invariati rispetto a HEAD, quindi non sono attribuibili al diff locale. La provenienza precisa va ancora ricostruita: una divergenza non dimostra da sola né una regressione introdotta da una determinata change, né una baseline legittimamente stale.

| Gruppo | Finding |
| --- | --- |
| Backend MCP | 13 |
| Frontend MCP | 1 |
| Frontend raccomandate Ruolo | 1 |
| Test worker | 15 |

Le 30 voci non sono 30 funzioni diverse: comprendono metriche multiple e due controlli LOC file. Alcune coinvolgono funzione contenitore e callback annidata. La lista integrale con baseline, valore e delta è nell'appendice A.

Il ratchet passa perché filtra al perimetro della change; il confronto integrale vede il resto del codice già committato. PASS locale non significa assenza di debito o baseline globalmente sincronizzata. Non è stata eseguita baseline-verify e non è dichiarata riproducibilità della baseline corrente.

Le 21 divergenze storiche contro 6b61fd27 riconciliate il 7/10 sono una questione distinta: erano già corrette in dc669728. Non vanno confuse con queste 30 divergenze attuali. Fonte: [docs/code-quality/HISTORICAL_MISMATCH_RECONCILIATION_2026-10-07.md:3](/home/cbo/CursorProjects/GAIA/docs/code-quality/HISTORICAL_MISMATCH_RECONCILIATION_2026-10-07.md:3).

## 16. Test e coverage: evidenza disponibile e limiti

Durante questo audit sono stati eseguiti analisi AST, controlli della baseline e query Graphify. **Non sono state rieseguite suite applicative, lint, typecheck, build o coverage.** Zero errori AST non equivale a typecheck PASS né a equivalenza funzionale.

Evidenze storiche del 7/10, non nuova validazione di questo checkout:

| Verifica documentata | Risultato storico | Fonte |
| --- | --- | --- |
| Backend completo | 6.361 PASS, 448 skipped | [docs/code-quality/ANPR_E2E_FOLLOWUP_2026-10-07.md:68](/home/cbo/CursorProjects/GAIA/docs/code-quality/ANPR_E2E_FOLLOWUP_2026-10-07.md:68) |
| Frontend unit | 3.986 PASS, 277 file | [docs/code-quality/ANPR_E2E_FOLLOWUP_2026-10-07.md:68](/home/cbo/CursorProjects/GAIA/docs/code-quality/ANPR_E2E_FOLLOWUP_2026-10-07.md:68) |
| E2E rebuilt | 52 PASS, 7 skipped | [docs/code-quality/ANPR_E2E_FOLLOWUP_2026-10-07.md:115](/home/cbo/CursorProjects/GAIA/docs/code-quality/ANPR_E2E_FOLLOWUP_2026-10-07.md:115) |
| Tooling | 169 PASS | [docs/code-quality/ANPR_E2E_FOLLOWUP_2026-10-07.md:68](/home/cbo/CursorProjects/GAIA/docs/code-quality/ANPR_E2E_FOLLOWUP_2026-10-07.md:68) |
| Worker | 774 PASS, 1 skipped; coverage circa 99% | [docs/code-quality/VERIFICATION_2026-10-07.md:103](/home/cbo/CursorProjects/GAIA/docs/code-quality/VERIFICATION_2026-10-07.md:103) |
| Nove runtime della campagna | Full-file statement/branch 100% | [docs/code-quality/VERIFICATION_2026-10-07.md:31](/home/cbo/CursorProjects/GAIA/docs/code-quality/VERIFICATION_2026-10-07.md:31) |

I nove file sono Ruolo tributi_repositories, inCASS, Presenze xlsm_export, Operazioni mobile_sync, GIS services, controller layout Organigramma, Network services e route/helper Catasto anomalie. Quel 100% non è il coverage globale del repository e non certifica cambi successivi. Le esclusioni legacy documentate e i test skipped restano limiti espliciti.

La policy GAIA richiede 100% sui runtime nuovi/modificati; ogni futura slice deve misurare l'intero file e i branch pertinenti. La sola percentuale non dimostra qualità degli assert, equivalenza delle transazioni o compatibilità PostgreSQL/PostGIS/provider. I precedenti risultati ANPR/E2E falliti sono superati dal follow-up citato, non conteggiati nuovamente come blocker attuale.

## 17. Valutazione qualitativa

- **Concentrazione UI:** Presenze, Capacitas, Utenze e Catasto hanno componenti molto grandi, con rendering, stato, callback e side effect nello stesso contenitore. Lo score sostiene una review delle responsabilità, non prescrive da solo una nuova architettura.
- **Accumulo backend:** Ruolo ha un repository con numerose operazioni; analytics e sincronizzazioni presentano picchi di branching e annidamento. Estrarre confini coesi può rendere i percorsi revisionabili, ma duplicare logica o spostare interi monoliti non riduce il debito.
- **Debito più ampio dei primi dieci file:** quasi metà dei file applicativi ha almeno una segnalazione. Una singola estrazione non può rendere il progetto complessivamente sotto soglia.
- **Guardrail già utili:** scanner AST e confronto contro il merge-base consentono misure ripetibili per la change; il caso Presenze mostra che un finding puntuale viene rilevato e può scomparire quando il codice rientra nel valore registrato.
- **Allineamento metadata da verificare:** i 30 finding globali su codice già committato richiedono provenienza, non una nuova baseline generata per rendere verde il check.
- **Nessuna stima economica:** queste metriche non giustificano una previsione in giorni/uomo o un giudizio su sicurezza, performance e affidabilità produttiva.

## 18. Piano raccomandato, non eseguito

| Priorità | Obiettivo | Intervento delimitato proposto | Criterio di uscita |
| --- | --- | --- | --- |
| P0 — verificabilità | Provenienza dei 30 finding globali | Confrontare sorgenti e baseline nei commit d'introduzione; distinguere drift da regressione | Ogni voce spiegata; nessun aggiornamento che assorba regressioni |
| P1 — UI | Presenze giornaliere | Una responsabilità coerente tra stato/derivazioni/rendering, concordata con l'owner | Riduzione reale della metrica obiettivo, UI invariata, full-file 100%, ratchet PASS |
| P1 — backend | Una funzione analytics Operazioni | Una fase di aggregazione o classificazione, non entrambe le funzioni insieme | Risultati e query invariati, aggregati senza trasferimento del debito |
| P2 — manutenzione | Ruolo tributi_repositories | Una responsabilità realmente toccata da feature; evitare sovrapposizione al lavoro attivo | Una slice coesa con invarianti di import/pagamenti/transazioni |
| P2 — churn | Catasto matching/resolvers e schedule Presenze | Ratchet ordinario nella prossima modifica funzionale | Nessuna regressione; semplificazione locale solo se pertinente |
| P2 — resilienza | Bonifica sync | Un confine di orchestration o gestione errori | Ordine side effect, retry e scritture parziali caratterizzati |
| P3 — UI/worker | Capacitas, Utenze e AutoDoc | Selezionare un solo hotspot quando ostacola lavoro reale | Una unità revisionabile e stessa matrice di validazione |

La graduatoria è una proposta tecnica, non un'autorizzazione ad avviare sette refactoring o una campagna parallela. Il quality ratchet resta la modalità predefinita. Prima di ogni hotspot: ownership libera, invarianti, test di caratterizzazione, metriche iniziali e stop condition. Dopo: coverage full-file, ratchet autorevole, aggregati e Graphify del modulo se cambiano struttura/relazioni.

Classificare IMPROVED solo quando diminuisce la metrica obiettivo senza trasferimento del debito; una riorganizzazione neutra è REORGANIZED_AND_CHARACTERIZED. Non introdurre wrapper artificiali, duplicazioni, nuove esclusioni o aggiornamenti baseline prima del confronto.

## 19. Riproduzione e traccia delle evidenze

Per una nuova scansione sul checkout corrente, usando destinazioni separate:

```bash
make complexity-report \
  REPORT_JSON=/tmp/gaia-complexity-next.json \
  REPORT_MD=/tmp/gaia-complexity-next.md
make complexity-ratchet BASE_REF=main
make complexity-check
```

Il report può uscire 0 pur contenendo error-level legacy: l'exit code del report segnala parsing/configurazione, non il superamento delle soglie. complexity-check è read-only e consulta la baseline corrente; complexity-ratchet è il controllo autorevole della change contro il merge-base. Cambiare BASE_REF cambia la domanda e non è una soluzione a una failure. Non eseguire complexity-baseline o baseline-repair per assorbire i finding.

Artefatti di questo rapporto:

- Rapporto persistente: [reports/code-quality/COMPLEXITY_AUDIT_2026-10-08.md:1](/home/cbo/CursorProjects/GAIA/reports/code-quality/COMPLEXITY_AUDIT_2026-10-08.md:1).
- Dati aggregati persistenti: [reports/code-quality/complexity-audit-2026-10-08-summary.json:1](/home/cbo/CursorProjects/GAIA/reports/code-quality/complexity-audit-2026-10-08-summary.json:1).
- Report AST completo dello snapshot: /tmp/gaia-complexity-complete-2026-10-08.json.
- Ranking AST: /tmp/gaia-complexity-complete-ranking-2026-10-08.md.
- Analisi grezza con confronti: /tmp/gaia-complexity-complete-analysis-2026-10-08.json.
- Driver temporaneo: /tmp/gaia-complexity-complete-audit.py.
- Log: /tmp/gaia-complexity-complete-audit.log.
- Query Graphify: /tmp/gaia-complexity-complete-graph-backend.log e /tmp/gaia-complexity-complete-graph-frontend.log.

SHA256 baseline: 38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95.
SHA256 eccezioni: 81a515050e5d312ac4a453fa1bdaa999cfc11ad6a652659776bf5747c6b69168.
SHA256 report AST completo: 0dda986212e26125c509e338a18713a0b19d733be2175b51b0d256354253a2a2.
Digest SHA256 del mapping path→hash sorgente in ingresso: 0f15c4321f65fa033cfcf9612ac58f2d9ff422a0cb91e2a379bb44e6db5be69e.

I file /tmp sono locali e temporanei; il rapporto e il JSON aggregato conservano i principali risultati nel repository. I due report generati preesistenti complexity-report.json/md non sono stati sovrascritti. Graphify è stato usato per orientamento, non per calcolare complessità o dimostrare freshness del codice; non è stata lanciata un'estrazione sulla root GAIA.

## Appendice A — Tutte le divergenze dalla baseline

| File | Callable/livello | Metrica | Baseline | Misurato | Delta |
| --- | --- | --- | --- | --- | --- |
| [backend/app/modules/wiki/mcps/auth.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/mcps/auth.py:1) | verify_token | loc | 21 | 22 | +1 |
| [backend/app/modules/wiki/mcps/cli.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/mcps/cli.py:1) | main | cyclomatic | 3 | 4 | +1 |
| [backend/app/modules/wiki/mcps/cli.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/mcps/cli.py:1) | main | loc | 22 | 28 | +6 |
| [backend/app/modules/wiki/mcps/data/cli.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/mcps/data/cli.py:1) | main | loc | 26 | 29 | +3 |
| [backend/app/modules/wiki/mcps/data/server.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/mcps/data/server.py:1) | create_server | loc | 28 | 31 | +3 |
| [backend/app/modules/wiki/mcps/data/service.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/mcps/data/service.py:1) | DataService.__init__ | loc | 7 | 8 | +1 |
| [backend/app/modules/wiki/mcps/data/service.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/mcps/data/service.py:1) | DataService.__init__ | params | 2 | 3 | +1 |
| [backend/app/modules/wiki/mcps/experiment_cli.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/mcps/experiment_cli.py:1) | live | loc | 3 | 4 | +1 |
| [backend/app/modules/wiki/mcps/experiment_runner.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/mcps/experiment_runner.py:1) | experiment_manifest | loc | 29 | 30 | +1 |
| [backend/app/modules/wiki/mcps/http.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/mcps/http.py:1) | create_http_app | cyclomatic | 1 | 2 | +1 |
| [backend/app/modules/wiki/mcps/http.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/mcps/http.py:1) | create_http_app | cognitive | 0 | 1 | +1 |
| [backend/app/modules/wiki/mcps/http.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/mcps/http.py:1) | create_http_app | loc | 44 | 50 | +6 |
| [backend/app/modules/wiki/mcps/http.py:1](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/mcps/http.py:1) | create_http_app | nesting | 0 | 1 | +1 |
| [frontend/src/app/wiki/mcp/page.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/app/wiki/mcp/page.tsx:1) | WikiMCPPreview | loc | 54 | 55 | +1 |
| [frontend/src/components/ruolo/registered-mails-console.tsx:1](/home/cbo/CursorProjects/GAIA/frontend/src/components/ruolo/registered-mails-console.tsx:1) | RegisteredMailRow | loc | 39 | 40 | +1 |
| [modules/elaborazioni/worker/tests/test_sister_browser_reliability.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_sister_browser_reliability.py:1) | _Page.__init__ | loc | 11 | 12 | +1 |
| [modules/elaborazioni/worker/tests/test_sister_browser_reliability.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_sister_browser_reliability.py:1) | _Page.locator | cyclomatic | 3 | 4 | +1 |
| [modules/elaborazioni/worker/tests/test_sister_browser_reliability.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_sister_browser_reliability.py:1) | _Page.locator | cognitive | 2 | 3 | +1 |
| [modules/elaborazioni/worker/tests/test_sister_browser_reliability.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_sister_browser_reliability.py:1) | _Page.locator | loc | 6 | 8 | +2 |
| [modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1) | test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice | cyclomatic | 6 | 7 | +1 |
| [modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1) | test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice | cognitive | 11 | 16 | +5 |
| [modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1) | test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice | loc | 35 | 46 | +11 |
| [modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1) | test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice | nesting | 3 | 4 | +1 |
| [modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1) | test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice.scenario | cyclomatic | 6 | 7 | +1 |
| [modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1) | test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice.scenario | cognitive | 11 | 16 | +5 |
| [modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1) | test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice.scenario | loc | 33 | 44 | +11 |
| [modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py:1) | test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice.scenario | nesting | 3 | 4 | +1 |
| [modules/elaborazioni/worker/tests/test_worker_repository.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_worker_repository.py:1) | test_document_path_builders_cover_subject_and_immobile_fallbacks | loc | 28 | 33 | +5 |
| [modules/elaborazioni/worker/tests/test_worker_reliability.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_worker_reliability.py:1) | <file> | loc | 567 | 584 | +17 |
| [modules/elaborazioni/worker/tests/test_worker_repository.py:1](/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker/tests/test_worker_repository.py:1) | <file> | loc | 512 | 534 | +22 |

## Appendice B — Decomposizione completa per percorsi

| Gruppo | File | Callable | LOC file | Error | Warning | File coinvolti | Max cognitiva |
| --- | --- | --- | --- | --- | --- | --- | --- |
| backend/__init__.py | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| backend/accessi | 19 | 111 | 1.955 | 3 | 18 | 6 | 28 |
| backend/catasto | 74 | 784 | 21.948 | 186 | 233 | 47 | 146 |
| backend/core | 2 | 0 | 5 | 0 | 0 | 0 | 0 |
| backend/dotazioni | 8 | 38 | 734 | 0 | 9 | 4 | 20 |
| backend/elaborazioni | 78 | 522 | 10.149 | 50 | 96 | 37 | 101 |
| backend/elaborazioni-services-legacy | 22 | 456 | 9.823 | 120 | 156 | 18 | 269 |
| backend/gis | 45 | 391 | 8.266 | 16 | 71 | 23 | 27 |
| backend/inventory | 5 | 4 | 185 | 1 | 0 | 1 | 9 |
| backend/me | 10 | 37 | 1.339 | 8 | 12 | 5 | 38 |
| backend/network | 34 | 239 | 7.085 | 75 | 65 | 20 | 209 |
| backend/operazioni | 49 | 302 | 11.482 | 103 | 107 | 24 | 366 |
| backend/organigramma | 31 | 141 | 3.452 | 21 | 24 | 11 | 205 |
| backend/platform-__init__.py | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| backend/platform-api | 13 | 13 | 193 | 0 | 0 | 0 | 5 |
| backend/platform-core | 10 | 15 | 1.048 | 0 | 1 | 1 | 4 |
| backend/platform-db | 2 | 0 | 387 | 0 | 0 | 0 | 0 |
| backend/platform-jobs | 2 | 3 | 114 | 1 | 4 | 1 | 20 |
| backend/platform-main.py | 1 | 5 | 102 | 0 | 0 | 0 | 9 |
| backend/platform-models | 23 | 6 | 2.623 | 1 | 1 | 2 | 5 |
| backend/platform-platform_scheduler_runner.py | 1 | 3 | 71 | 0 | 0 | 0 | 1 |
| backend/platform-repositories | 5 | 36 | 327 | 0 | 2 | 2 | 12 |
| backend/platform-schemas | 13 | 14 | 2.358 | 3 | 1 | 2 | 29 |
| backend/platform-scripts | 14 | 59 | 1.119 | 2 | 13 | 4 | 23 |
| backend/platform-services | 28 | 225 | 4.354 | 24 | 48 | 14 | 51 |
| backend/platform-utils | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| backend/platform-worker_health.py | 1 | 11 | 147 | 0 | 0 | 0 | 10 |
| backend/presenze | 107 | 875 | 19.448 | 93 | 240 | 65 | 87 |
| backend/riordino | 71 | 192 | 4.852 | 34 | 51 | 23 | 47 |
| backend/ruolo | 83 | 784 | 18.949 | 117 | 230 | 48 | 95 |
| backend/search | 4 | 13 | 414 | 4 | 1 | 1 | 28 |
| backend/shared | 3 | 10 | 157 | 0 | 1 | 1 | 9 |
| backend/utenze | 36 | 334 | 9.095 | 65 | 111 | 22 | 67 |
| backend/wiki | 124 | 678 | 18.042 | 108 | 193 | 64 | 188 |
| frontend/app-root | 3 | 30 | 840 | 7 | 5 | 2 | 99 |
| frontend/app/anagrafica | 5 | 34 | 366 | 3 | 0 | 1 | 56 |
| frontend/app/auth | 4 | 41 | 582 | 5 | 4 | 4 | 17 |
| frontend/app/catasto | 36 | 906 | 10.633 | 60 | 56 | 15 | 390 |
| frontend/app/dotazioni | 3 | 3 | 28 | 0 | 0 | 0 | 0 |
| frontend/app/elaborazioni | 19 | 34 | 204 | 0 | 1 | 1 | 6 |
| frontend/app/gaia | 6 | 362 | 4.134 | 37 | 34 | 4 | 162 |
| frontend/app/gis | 25 | 451 | 5.746 | 9 | 22 | 10 | 95 |
| frontend/app/inventory | 1 | 1 | 43 | 0 | 0 | 0 | 0 |
| frontend/app/login | 1 | 15 | 306 | 3 | 0 | 1 | 26 |
| frontend/app/mcp | 1 | 1 | 7 | 0 | 0 | 0 | 0 |
| frontend/app/me | 8 | 202 | 2.020 | 15 | 12 | 3 | 271 |
| frontend/app/nas-control | 11 | 204 | 2.213 | 20 | 12 | 7 | 56 |
| frontend/app/network | 13 | 557 | 6.627 | 56 | 29 | 13 | 183 |
| frontend/app/operazioni | 24 | 748 | 9.462 | 98 | 48 | 22 | 144 |
| frontend/app/organigramma | 3 | 3 | 56 | 0 | 0 | 0 | 2 |
| frontend/app/presenze | 33 | 1.232 | 12.552 | 78 | 101 | 18 | 550 |
| frontend/app/riordino | 7 | 57 | 408 | 3 | 0 | 1 | 47 |
| frontend/app/ruolo | 20 | 577 | 8.837 | 64 | 37 | 11 | 204 |
| frontend/app/search | 1 | 20 | 207 | 2 | 1 | 1 | 23 |
| frontend/app/utenze | 7 | 326 | 4.318 | 31 | 15 | 6 | 391 |
| frontend/app/wiki | 14 | 18 | 289 | 0 | 1 | 1 | 6 |
| frontend/components/accessi | 1 | 4 | 31 | 0 | 0 | 0 | 1 |
| frontend/components/anagrafica | 1 | 15 | 222 | 3 | 2 | 1 | 35 |
| frontend/components/app | 4 | 64 | 924 | 8 | 7 | 4 | 53 |
| frontend/components/auth | 1 | 7 | 41 | 0 | 0 | 0 | 2 |
| frontend/components/catasto | 70 | 1.017 | 12.611 | 83 | 101 | 42 | 246 |
| frontend/components/elaborazioni | 40 | 1.244 | 13.941 | 82 | 108 | 24 | 472 |
| frontend/components/inventory | 1 | 4 | 111 | 0 | 0 | 0 | 4 |
| frontend/components/layout | 12 | 84 | 1.421 | 4 | 7 | 6 | 49 |
| frontend/components/network | 5 | 54 | 1.061 | 5 | 6 | 3 | 142 |
| frontend/components/operazioni | 10 | 142 | 1.942 | 16 | 20 | 9 | 40 |
| frontend/components/presenze | 12 | 153 | 1.481 | 9 | 20 | 8 | 139 |
| frontend/components/riordino | 17 | 267 | 2.721 | 23 | 7 | 11 | 60 |
| frontend/components/ruolo | 41 | 418 | 3.502 | 6 | 37 | 16 | 55 |
| frontend/components/search | 1 | 48 | 495 | 4 | 3 | 1 | 53 |
| frontend/components/security | 1 | 3 | 72 | 0 | 0 | 0 | 3 |
| frontend/components/table | 3 | 10 | 177 | 1 | 1 | 1 | 13 |
| frontend/components/ui | 11 | 37 | 425 | 0 | 0 | 0 | 6 |
| frontend/components/utenze | 12 | 261 | 3.511 | 33 | 33 | 9 | 184 |
| frontend/features/dotazioni | 12 | 86 | 402 | 0 | 4 | 3 | 12 |
| frontend/features/operazioni | 2 | 127 | 792 | 1 | 2 | 1 | 25 |
| frontend/features/organigramma | 15 | 446 | 4.724 | 32 | 39 | 7 | 167 |
| frontend/features/wiki | 27 | 644 | 8.956 | 68 | 62 | 22 | 166 |
| frontend/hooks | 3 | 14 | 135 | 0 | 2 | 1 | 12 |
| frontend/lib | 77 | 1.092 | 11.436 | 7 | 37 | 20 | 35 |
| frontend/types | 28 | 0 | 8.547 | 2 | 5 | 7 | 0 |
| worker/runtime | 38 | 576 | 9.071 | 35 | 134 | 25 | 122 |

## Checkpoint e chiusura

Obiettivo completato: rapporto statico completo sullo snapshot misurato, con metriche, trend, hotspot, baseline e limiti. File creati dall'audit nel repository: soltanto questo Markdown e il JSON aggregato. Codice applicativo, test, baseline, soglie ed esclusioni preservati. Nessun commit, deploy o nuovo hotspot avviato. Lo stato delle suite e del coverage corrente non è certificato. Prossima decisione proposta: riconciliare la provenienza dei finding globali oppure scegliere una sola slice con ownership libera.
