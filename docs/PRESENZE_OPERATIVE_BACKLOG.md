# Presenze Operative Backlog

Ultimo aggiornamento: `2026-06-25`

## Obiettivo

Chiudere il perimetro funzionale del modulo oggi esposto come `Giornaliere` e progressivamente consolidato come dominio `Presenze`.

Priorita prodotto:

1. rendere affidabile la `Banca Ore`
2. formalizzare le `Regole CCNL`
3. allineare `Export HR` e file reali
4. completare il `Refactor Presenze` tecnico

## Stato sintetico

- UI e perimetro operativo principali sono gia disponibili
- naming frontend lato prodotto e compatibilita `Presenze*` sono in buona parte chiusi
- restano da consolidare soprattutto logiche di dominio, edge case contrattuali e allineamento con i file HR

## Stream 1: Banca Ore

### Obiettivo

Portare la banca ore a uno stato affidabile lato HR, con workflow completo, tracciabilita e vincoli coerenti con il CCNL.

### Ambito

- saldo importato da INAZ
- saldo effettivo GAIA
- carichi, scarichi, liquidazioni e correzioni
- policy di liquidazione guidata
- approvazioni HR
- audit e storico modifiche

### Lavori aperti

- validare il modello finale dei bucket liquidabili:
  - straordinario diurno
  - straordinario notturno
  - straordinario festivo
  - straordinario festivo notturno
- chiarire il perimetro dei minuti che restano in banca ore vs minuti liquidabili
- verificare i casi con profilo derivato da template e fallback manuale
- chiudere i controlli su saldo disponibile prima di scarico/liquidazione
- verificare il trattamento delle rettifiche manuali nel saldo effettivo
- aggiungere test mirati sui casi negativi e sui casi di revisione HR

### Gate di accettazione

- ogni movimento modifica il saldo in modo deterministico
- nessuna liquidazione puo eccedere il disponibile
- storico revisioni e approvazioni consultabile
- test backend dedicati verdi
- validazione HR su casi reali campione

## Stream 2: Regole CCNL

### Obiettivo

Esplicitare e centralizzare le regole di calcolo oggi distribuite tra parsing, giornaliere, export e banca ore.

### Ambito

- maggiorazione notturna
- maggiorazione festiva
- maggiorazione festiva notturna
- differenze operai vs impiegati
- orario standard giornaliero:
  - operai `7:00`
  - impiegati `6:25`
- recuperi e giorni retribuiti su settimana 5 giorni

### Lavori aperti

- tradurre il CCNL in regole applicative versionate
- definire precedenze tra causali, straordinario e fasce orarie
- chiarire i casi di sovrapposizione:
  - notturno + festivo
  - straordinario + festivo
  - straordinario + notturno
  - straordinario + festivo notturno
- formalizzare il meccanismo dei `giorni retribuiti` segnalato da Carlo
- decidere quali risultati esporre a frontend come dato spiegabile e non solo come numero finale

### Gate di accettazione

- documento regole leggibile da tecnico e HR
- test parametrizzati per tutti i casi contrattuali principali
- output spiegabile per singola giornata e per periodo
- nessuna regola critica lasciata implicita nel codice

## Stream 3: Export HR

### Obiettivo

Rendere l'export GAIA aderente ai file HR reali per i collaboratori presenti in piattaforma.

### Ambito

- export XLSM/XLSX
- allineamento voci con file giornaliere HR
- mapping colonne e semantica contatori
- selezione del solo perimetro collaboratori GAIA

### Input gia acquisiti

- file HR completo ricevuto
- chiarimenti Carlo:
  - `MB`, `IR`, `IB`, `MA` sono centri di costo non piu usati
  - la banca ore non viene gestita nel file giornaliera
  - `giorni retribuiti` seguono la logica settimana 38 ore su 5 giorni con compensazione tra settimane
  - assenze conteggiate in giorni

### Lavori aperti

- chiudere il mapping tra campi GAIA e colonne HR residue ancora ambigue
- verificare gennaio, febbraio e marzo sui dati sincronizzati
- distinguere chiaramente:
  - dato importato da INAZ
  - dato derivato GAIA
  - dato solo informativo per export
- eliminare dipendenze da template locali non disponibili lato server
- definire fallback robusti quando il template legacy manca

### Gate di accettazione

- export riproducibile sul server
- mapping colonne documentato
- verifica campione con HR su mesi reali
- nessun errore bloccante dovuto a template path o file mancanti

## Stream 4: Refactor Presenze

### Obiettivo

Completare il passaggio da naming e struttura legacy `Inaz` a dominio prodotto `Presenze`, senza regressioni.

### Stato attuale

- naming utente principale gia rinominato in `Giornaliere`
- layer frontend `Presenze*` gia introdotto e adottato
- route e namespace legacy `/inaz` ancora mantenuti per compatibilita

### Lavori aperti

- decidere strategia finale per route pubbliche:
  - mantenere `/inaz` come alias permanente
  - oppure introdurre `/presenze` e deprecare il legacy
- decidere strategia finale per:
  - `module_inaz`
  - modelli e tabelle `inaz_*`
  - helper e file legacy rimasti
- valutare se la Fase C porta valore adesso o dopo la stabilizzazione funzionale

### Gate di accettazione

- perimetro pubblico scelto e documentato
- piano migrazione chiaro se si tocca backend pubblico o DB
- zero regressioni sui client esistenti

## Ordine di esecuzione raccomandato

### Fase 1

- chiudere `Banca Ore`
- chiudere regole `CCNL` minime bloccanti

### Fase 2

- chiudere `Export HR` sui mesi reali e sui collaboratori GAIA

### Fase 3

- rifinire `Refactor Presenze` tecnico solo dove serve al dominio

## Task immediati consigliati

1. costruire una matrice test CCNL con casi operai e impiegati
2. verificare liquidazione banca ore su casi reali gennaio-febbraio-marzo
3. completare la documentazione di mapping export HR
4. preparare backlog di bug e scarti emersi dal confronto con i file Carlo

## Domande ancora aperte

- quali voci export restano da chiarire con HR oltre a quelle gia risolte?
- i `giorni retribuiti` devono entrare solo in export oppure anche in reporting e banca ore?
- serve una vista FE dedicata per spiegare il breakdown CCNL per giornata?
- la Fase C del rename deve essere trattata come obiettivo separato post-stabilizzazione?
