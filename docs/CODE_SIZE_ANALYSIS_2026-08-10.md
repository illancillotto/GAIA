# Code size analysis GAIA - sintesi sanificata

Data analisi: `2026-08-10`
Ambito: `backend/app` runtime e `frontend/src`

## Scopo

Questa nota conserva le conclusioni operative dell'analisi locale sulla dimensione del codice, senza path assoluti o output raw. L'obiettivo e orientare refactor e priorita di test coverage.

## Executive summary

GAIA non presenta un problema classico di classi OOP molto grandi. Su circa `1.476` classi Python analizzate:

- nessuna classe supera `1.000` LOC;
- `2` classi superano `500` LOC;
- `9` classi superano `200` LOC.

Il rischio principale e invece la presenza di file procedurali monolitici:

| Area | Segnale |
|---|---|
| Backend | diversi router/service sopra `1.000` LOC |
| Frontend | molte page/workspace e `src/lib/api.ts` sopra `1.000` LOC |
| Stile frontend | quasi nessuna classe TypeScript, molta logica in funzioni/componenti |
| Hotspot Graphify | spesso hub architetturali, non necessariamente classi lunghe |

## Distribuzione classi Python

| Banda LOC | Conteggio |
|---|---:|
| `>= 1000` | 0 |
| `>= 500` | 2 |
| `>= 300` | 6 |
| `>= 200` | 9 |
| `>= 100` | 13 |
| `>= 50` | 42 |

Classi grandi concentrate soprattutto in:

- configurazione core;
- resolver live e session manager Capacitas/Bonifica;
- client esterni ANPR/inCASS/InVolture;
- servizio import anagrafica;
- client NAS.

## File monolitici

Il refactor va prioritizzato sui file grandi, piu che sulle classi:

- router backend di dominio con molte route e helper inline;
- service procedurali con parsing, IO e persistenza nello stesso file;
- page frontend monolitiche con fetch, stato, layout, modali e helper insieme;
- client API aggregatori con molte funzioni dominio nello stesso modulo.

## Impatto su coverage

I file monolitici rendono piu costoso mantenere `100%` coverage perche:

- concentrano molte branch eterogenee nello stesso target;
- accoppiano rendering, IO e trasformazioni dati;
- rendono difficile testare solo la logica nuova senza misurare codice legacy non correlato;
- favoriscono test molto lunghi e fragili.

Pattern consigliati:

- estrarre helper puri e mapper dati;
- isolare adapter API per dominio;
- separare shell dati da componenti UI presentazionali;
- spostare modali complesse in componenti dedicati;
- introdurre test unitari su helper prima degli integration test.

## Priorita suggerite

1. Spezzare progressivamente `src/lib/api.ts` per dominio, preservando compatibilita degli export pubblici.
2. Estrarre componenti e helper dalle page frontend sopra `1.000` LOC.
3. Separare parsing/normalizzazione/persistenza nei service backend piu grandi.
4. Trattare router backend monolitici come orchestratori sottili, spostando logica in service testabili.
5. Usare Graphify per impact analysis sui moduli toccati, non come sostituto dei test.

## Decisione

L'analisi raw resta in `reports/` come artefatto locale. Questa sintesi e il riferimento versionato per pianificare refactor e coverage.
