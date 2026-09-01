# Report — UI/UX mobile del monitor AutoSync

**Data:** 2026-08-30  
**Route:** `/elaborazioni/autosync`  
**Deploy:** CED `192.168.1.110`

## Obiettivo

Rendere il monitor AutoSync leggibile e azionabile a `390×844` senza cambiare la composizione desktop.

## Miglioramenti applicati

- **KPI del monitor:** griglia da una colonna a **due colonne** su mobile; sei metriche occupano tre righe invece di sei.
- **Card KPI:** padding, font label e valore resi più compatti sotto `sm`, mantenendo i valori troncati anziché causare overflow.
- **Pipeline AutoSync:** quattro fasi presentate in **2×2** su telefono, con spaziatura ridotta e contenitori `min-w-0`.
- **Dashboard:** padding mobile ridotto da `p-4` a `p-3`; spaziatura verticale più densa solo sotto `sm`.
- **Copertura scope:** le quattro card di stato passano a una griglia **2×2** su mobile; il layout a colonna desktop laterale resta invariato da `lg`.
- **Configurazione:** contenitore mobile `p-4`, desktop conservato con `md:p-6`.
- **Azioni:** `Metti su ON/OFF`, `Salva configurazione`, `Aggiorna sorgente`, `Esegui adesso` ora formano una griglia a due colonne con pulsanti a tutta cella; da `sm` torna il layout desktop flessibile.

## File modificati

- `frontend/src/components/elaborazioni/autosync-activity-dashboard.tsx`
- `frontend/src/components/elaborazioni/continuous-catasto-sync-panel.tsx`
- `frontend/tests/unit/elaborazioni-request-workspace-continuous-sync.test.tsx`

## TDD e verifiche

| Verifica | Esito |
| --- | --- |
| Test RED layout mobile | PASS: inizialmente falliva perché gli hook/test id e le griglie mobile non esistevano |
| Test mirato Continuous AutoSync | **15/15 PASS** |
| Coverage runtime modificato | **100%** — 166/166 statement, 172/172 branch, 72/72 funzioni, 119/119 linee |
| TypeScript | **PASS** |
| Build production Next | **PASS** |
| `git diff --check` | **PASS** |
| `make complexity-ratchet BASE_REF=main` | **PASS**, `findings: []` |
| `make graphify-frontend` | **PASS** — nessun cambio topologico |

## Deploy CED

Deploy chirurgico dei soli due componenti runtime modificati:

- backup pre-deploy: `/opt/gaia/backups/hotfixes/2026-08-30-autosync-mobile-ux/`;
- riavviato esclusivamente `gaia-frontend`;
- checksum CED uguali a quelli locali:
  - dashboard: `2b3861c332b7ba657d3c638842fbccd7f994bdf99a72144f0043f7d0bfe73743`;
  - pannello: `222e367d61e64cb6db6d8bd72390a3c882ca59b8e958ba0e13b7e1bae5df2173`.

## Smoke post-deploy

| Endpoint | Esito |
| --- | --- |
| `http://192.168.1.110:8080/elaborazioni/autosync` | **HTTP 200** |
| chunk AutoSync via LAN | **HTTP 200**, JavaScript, 2.591.588 byte |
| `gaia-frontend` | **healthy** |

La route è stata aperta internamente subito dopo il restart per completare la compilazione on-demand e prevenire il precedente `ChunkLoadError` al primo accesso.

## Limiti

Non è stato possibile effettuare uno screenshot o un tap-test autenticato a `390×844`: il browser pilotabile richiede l'abilitazione manuale del remote debugging e non è stata utilizzata una sessione autenticata. La struttura responsive è però coperta dal test e dal rendering/build verificati.

Nessun commit o push eseguito; modifiche concorrenti nei checkout locale/CED non sono state toccate.
