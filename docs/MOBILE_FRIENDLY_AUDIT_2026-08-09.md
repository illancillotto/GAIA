# Mobile friendly audit GAIA - sintesi sanificata

Data audit: `2026-08-09`
Viewport: `390 x 844 px`
Target locale: ambiente GAIA in container

## Scopo

Questa nota conserva le conclusioni operative dei report mobile locali senza includere screenshot, output JSON raw o path locali. Gli artefatti generati restano sotto `reports/` e non sono pensati per il versionamento.

## Esito sintetico

L'audit mobile automatico sulle pagine statiche testabili ha confermato:

- nessun overflow orizzontale pagina secondo `documentElement.scrollWidth <= innerWidth + 2`;
- sidebar desktop non visibile su mobile;
- pagine navigabili senza errore;
- presenza di contenuto o controlli interattivi.

Risultato all-subpages:

| Indicatore | Conteggio |
|---|---:|
| Route statiche navigate | 145 |
| Route OK | 145 |
| Route KO | 0 |
| Route dinamiche censite ma non navigate | 26 |

## Riepilogo per modulo

| Modulo | Route testate | OK |
|---|---:|---:|
| `anagrafica` | 4 | 4 |
| `auth` | 1 | 1 |
| `catasto` | 23 | 23 |
| `elaborazioni` | 15 | 15 |
| `gaia` | 5 | 5 |
| `gis` | 2 | 2 |
| `home` | 1 | 1 |
| `inventory` | 1 | 1 |
| `login` | 1 | 1 |
| `me` | 5 | 5 |
| `nas-control` | 8 | 8 |
| `network` | 10 | 10 |
| `operazioni` | 19 | 19 |
| `organigramma` | 2 | 2 |
| `presenze` | 17 | 17 |
| `riordino` | 4 | 4 |
| `ruolo` | 11 | 11 |
| `search` | 1 | 1 |
| `utenze` | 5 | 5 |
| `wiki` | 10 | 10 |

## Interventi UI confermati

### Shell e navigazione

- Sidebar desktop nascosta su mobile.
- Drawer mobile con overlay e chiusura da cambio route / escape.
- Hamburger mobile in topbar.
- Breadcrumb compattato su viewport stretti.
- Layout desktop preservato con sidebar sticky sui breakpoint piu ampi.

### Spaziatura globale

- Padding pagina e panel ridotti su mobile.
- Metric card e contenitori principali resi piu compatti.
- Tabelle larghe protette con wrapper `overflow-x-auto` dove necessario.

### Catasto GIS

La pagina `/catasto/gis` e stata trattata come caso UX specifico:

- mappa prioritaria su mobile;
- console strumenti come bottom sheet;
- header piu compatto;
- azioni primarie ridotte a `Vista` e `Strumenti` su mobile.

## Automazione

Artefatti introdotti per audit:

- script mirato per campione mobile;
- script per route statiche censite;
- test Playwright mobile-friendly.

Linee guida:

- usare solo credenziali da variabili ambiente;
- non salvare screenshot nel repository;
- committare solo report sanificati o note operative come questa.

## Decisioni

- Gli screenshot e i JSON raw sono artefatti rigenerabili e restano ignorati.
- Le conclusioni utili devono essere riportate in docs sanificate.
- Le route dinamiche con ID/token reali richiedono test dedicati o fixture controllate.
