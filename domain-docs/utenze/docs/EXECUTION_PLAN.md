# Execution Plan

> Documento storico. Non usarlo piu come piano corrente di implementazione.
> Il dominio Anagrafica e confluito operativamente nel modulo `utenze`, non in
> `backend/app/modules/anagrafica/`.

## Stato

Il piano originario qui contenuto e superato dall'implementazione gia completata.
Le milestone previste per bootstrap modulo, modelli dati, import, CRUD, ricerca,
export e correlazioni risultano chiuse nel runtime attuale.

Riferimenti correnti:

- stato di avanzamento generale: `domain-docs/utenze/docs/PROGRESS.md`
- integrazione PDND/ANPR: `domain-docs/utenze/docs/PROGRESS_ANPR.md`
- architettura ANPR: `domain-docs/utenze/docs/ARCH_PDND_ANPR_DECESSI.md`
- PRD Anagrafica: `domain-docs/utenze/docs/PRD_anagrafica.md`

## Indicazioni operative

- Per il codice backend usare `backend/app/modules/utenze/`
- Per il frontend usare `frontend/src/app/utenze/` e componenti correlati
- Per nuove evoluzioni del dominio aggiornare `PROGRESS.md` o il documento architetturale/PRD pertinente, non questo file

## Motivo dell'archiviazione

La versione precedente di questo file riportava:

- path backend obsoleto (`backend/app/modules/anagrafica/`)
- milestone ancora marcate `pending` nonostante il dominio sia in produzione locale
- riferimenti a sorgenti documentali non piu valide (`domain-docs/anagrafica/...`)

Mantenere quel contenuto come piano corrente avrebbe creato un secondo punto di verita errato.
