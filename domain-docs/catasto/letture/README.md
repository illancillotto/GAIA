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
- esclusione automatica dei file temporanei Excel `~$...` nel picker frontend, con avviso esplicito all'operatore;
- normalizzazione e validazione dati;
- aggancio alle utenze tramite codice fiscale;
- visualizzazione nel dettaglio utente;
- dashboard e tabella nel modulo Catasto, con filtro anno a dropdown inizializzato sull'anno corrente solo se contiene dati, altrimenti sull'ultimo anno caricato;
- deduzione automatica del distretto dal nome file nel flusso di import frontend, privilegiando codice distretto esplicito ma con fallback anche sul nome distretto normalizzato nel filename; il resolver deve supportare anche codici composti nel formato reale tipo `D29-1 Uras 2025.xlsx`, provando sia la variante numerica composta sia il match sulla zona nel nome distretto;
- report validazione per file con modal di dettaglio warning/errori, inclusi i casi di distretto non dedotto;
- la validazione `DUPLICATO_FILE` deve colpire solo le vere letture contatore; attività operatore come `FLANGIA` e `SARACINESCA` possono condividere il `PUNTO_CONS` con una lettura senza generare falso duplicato;
- quando nello stesso `PUNTO_CONS` esistono più contatori reali distinti, la chiave duplicato deve includere anche `matricola/COD_CONT` se presente; il solo punto consegna non è sufficiente;
- upload supportato sui file `.xlsx`; il parser backend tenta anche una riparazione conservativa dei workbook con stylesheet OOXML malformato noto (es. font family fuori range). Se il file resta non leggibile dopo il recovery, il flusso deve restituire errore utente `400` con indicazione di riaprire e salvare nuovamente il workbook come `.xlsx`;
- la colonna `TIPO` governa la semantica del record: solo `CONT_TESSER` e `CONT_NO_TES` sono letture contatore; `FLANGIA`, `SARACINESCA` e tipi analoghi vanno trattati come attività operatore registrate nel flusso ma non come contatori standard;
- il normalizzatore deve assorbire anche alias già presenti nei file reali, in particolare `CONT_TES -> CONT_TESSER`;
- i filename di progetto generico (regola filename-based, es. presenza di `PROGETTO`) possono essere importati senza `distretto` risolto: il sistema li tratta come import generici non distrettuali invece di bloccarli con `DISTRETTO_MANCANTE`;
- il parser Excel deve supportare layout eterogenei osservati sulle annualità `2022-2026`: header in prima o seconda riga, colonne con anno nel nome (`lettura finale 2024`, `M3 finali 2023`, `consumo 2025 tot. M3`), naming XMC 2023 e file privi della colonna `TIPO`;
- quando `TIPO` manca, il parser applica un'inferenza conservativa da `TIPOLOGIA`, `matricola`, letture e note per distinguere almeno `CONT_NO_TES`, `FLANGIA`, `SARACINESCA`, `SFIATO`, `DIRAMATORE`, `DISMESSO`, `DA CENSIRE`;
- la stessa inferenza copre anche pattern storici/inventariali ricorrenti:
  - `non trovata`, `inacessibile`, `da verificare` -> `DA CENSIRE`
  - `Idrovalvola ...` o `... linea sotterranea ...` -> `IDROVALVOLA`
- per file storici senza anno nel filename, l'anno viene inferito dai nomi colonna se presente nel tracciato;
- per `CONT_NO_TES` senza codice fiscale, e per `CONT_TESSER` senza identificativo utenza, il sistema deve aprire automaticamente un'anomalia nel registro `catasto/anomalie` per triage manuale;
- dal drawer di dettaglio una lettura in `warning` può essere confermata manualmente con `Valida lettura`; la conferma porta il record a `valid`, chiude i warning correnti e lascia traccia nello storico `manual_audits`;
- pagina `catasto/letture-contatori/import` riservata ad `admin` e `super_admin`;
- predisposizione futura per GAIA Mobile.
