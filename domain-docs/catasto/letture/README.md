# GAIA Catasto — Letture contatori irrigui

Pacchetto documentale per implementare in GAIA Catasto la gestione delle letture contatori provenienti da file Excel distrettuali.

## File inclusi

- `PRD_letture_contatori.md`
- `IMPLEMENTATION_PLAN_letture_contatori.md`
- `CODEX_PROMPT_letture_contatori.md`
- `PROGRESS_letture_contatori.md`

## Percorso consigliato nel repository

```text
domain-docs/catasto/docs/
```

## Sintesi

La funzionalità prevede:

- import Excel dei file distrettuali, anche multiplo;
- normalizzazione e validazione dati;
- aggancio alle utenze tramite codice fiscale;
- visualizzazione nel dettaglio utente;
- dashboard e tabella nel modulo Catasto, con filtro anno a dropdown inizializzato sull'anno corrente solo se contiene dati, altrimenti sull'ultimo anno caricato;
- deduzione automatica del distretto dal nome file nel flusso di import frontend, privilegiando codice distretto esplicito ma con fallback anche sul nome distretto normalizzato nel filename; il resolver deve supportare anche codici composti nel formato reale tipo `D29-1 Uras 2025.xlsx`, provando sia la variante numerica composta sia il match sulla zona nel nome distretto;
- report validazione per file con modal di dettaglio warning/errori, inclusi i casi di distretto non dedotto;
- upload supportato sui file `.xlsx`; il parser backend tenta anche una riparazione conservativa dei workbook con stylesheet OOXML malformato noto (es. font family fuori range). Se il file resta non leggibile dopo il recovery, il flusso deve restituire errore utente `400` con indicazione di riaprire e salvare nuovamente il workbook come `.xlsx`;
- la colonna `TIPO` governa la semantica del record: solo `CONT_TESSER` e `CONT_NO_TES` sono letture contatore; `FLANGIA`, `SARACINESCA` e tipi analoghi vanno trattati come attività operatore registrate nel flusso ma non come contatori standard;
- per `CONT_NO_TES` senza codice fiscale, e per `CONT_TESSER` senza identificativo utenza, il sistema deve aprire automaticamente un'anomalia nel registro `catasto/anomalie` per triage manuale;
- pagina `catasto/letture-contatori/import` riservata ad `admin` e `super_admin`;
- predisposizione futura per GAIA Mobile.
