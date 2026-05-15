# Implementation Plan — Letture contatori irrigui

## Obiettivo

Portare in `GAIA Catasto` una gestione completa delle letture contatori irrigui con:

- import Excel distrettuale;
- validazione preventiva;
- persistenza storica import;
- persistenza letture con chiave tecnica `anno + distretto + punto_consegna`;
- linking anagrafico tramite CF normalizzato;
- consultazione Catasto;
- sezione dedicata nel dettaglio utente.

## Scelte implementative

- Backend modellato nel file condiviso `backend/app/models/catasto_phase1.py`, coerente con il resto del dominio.
- Route esposte in `backend/app/modules/catasto/routes/meter_readings.py`.
- Servizi dedicati in `backend/app/modules/catasto/services/`.
- API client integrato nel file esistente `frontend/src/lib/api/catasto.ts`.
- Dettaglio utente integrato lato frontend tramite chiamata diretta all'API Catasto, senza estendere il payload backend di `utenze`.

## Step

1. Aggiungere tabelle `catasto_meter_reading_imports` e `catasto_meter_readings` con migration Alembic.
2. Implementare parser Excel tollerante:
   header row autodetect, alias colonne, campi opzionali, deduzione anno/distretto dal filename.
3. Implementare validazione:
   errori bloccanti, warning, normalizzazione CF, deduplica intra-file, linking soggetto.
4. Implementare import modes:
   `import`, `upsert`, `replace`.
5. Esporre API:
   validate, import, lista import, dettaglio import, lista letture, dettaglio lettura, letture per soggetto.
6. Integrare frontend Catasto:
   pagina registro, pagina import, tabella, drawer dettaglio, report validazione.
7. Integrare sezione `Letture contatori` in `frontend/src/app/utenze/[id]/page.tsx`.
8. Coprire parser/import/API con test backend e allineare la documentazione di dominio.

## Rischi aperti

- Tracciati Excel eterogenei fra distretti.
- File con header non in prima riga.
- Distretto non sempre deducibile dal nome file.
- Ambiguità anagrafica su CF condivisi o sporchi.
- Necessità futura di estendere il modello a dati mobile senza rompere la chiave tecnica corrente.
