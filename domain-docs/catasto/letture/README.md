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
- deduzione automatica del distretto dal nome file nel flusso di import frontend;
- pagina `catasto/letture-contatori/import` riservata ad `admin` e `super_admin`;
- predisposizione futura per GAIA Mobile.
