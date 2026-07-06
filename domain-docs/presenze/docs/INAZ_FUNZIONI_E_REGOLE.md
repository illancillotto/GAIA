# Presenze scraper: funzioni implementate e regole operative

Questo documento riassume cosa e stato implementato nel progetto sperimentale `inaz-scraper` e cosa deve essere mantenuto in un progetto dedicato del dominio Presenze.

Nota architetturale per l'integrazione in GAIA:

- nel progetto dedicato o nel modulo GAIA integrato, le credenziali Presenze non devono stare in `.env`;
- vanno salvate in DB, cifrate a riposo, e associate al singolo `application_user_id`;
- la configurazione evento banca ore deve essere persistita per operatore o per credenziale, non come costante globale in file ambiente.

## Comandi attuali

Dal `pyproject.toml` attuale:

```toml
presenze-straordinari = "presenze_scraper.cli:main"
presenze-crea-mesi = "presenze_scraper.monthly_excel:main"
presenze-popola-excel = "presenze_scraper.populate_excel:main"
presenze-collaboratori = "presenze_scraper.collaborators:main"
presenze-richiedi-straordinari = "presenze_scraper.request_overtime:main"
```

## File principali attuali

- `src/presenze_scraper/cli.py`
  - login generico;
  - scraping interattivo righe potenzialmente relative a straordinari;
  - output JSON/CSV.
- `src/presenze_scraper/populate_excel.py`
  - navigazione calendario;
  - apertura dettaglio giorno;
  - parsing extra orario;
  - parsing richieste banca ore;
  - scrittura Excel mensili.
- `src/presenze_scraper/request_overtime.py`
  - lettura anomalie STRNA;
  - richiesta straordinario o banca ore;
  - dry-run/apply;
  - idempotenza su evento + intervallo.
- `src/presenze_scraper/monthly_excel.py`
  - creazione file mensili da template.
- `src/presenze_scraper/collaborators.py`
  - cartellini collaboratori;
  - JSON checkpoint;
  - compilazione giornaliere XLSM.
- `/home/cbo/.codex/skills/inaz-straordinari-filtrati/scripts/calcola_straordinari.py`
  - calcolo robusto degli straordinari con soglia 30 minuti;
  - stampa timbrature;
  - include banca ore nel report.

## Regole straordinari

1. Ogni singolo straordinario sotto 30 minuti va escluso dal totale.
2. Gli esclusi vanno comunque mostrati nel report.
3. Ogni giorno incluso deve mostrare le timbrature.
4. Le richieste banca ore vanno sempre lette nello stesso periodo.
5. Tenere separati:
   - straordinario lordo sopra soglia;
   - banca ore richiesta;
   - straordinario da mettere nel file Excel pagabile.
6. Il file Excel degli straordinari deve escludere le giornate/intervalli richiesti in banca ore.
7. Non sottrarre due volte: alcune banca ore possono non essere mai state righe Excel, ma vanno comunque nel totale banca ore.

## Caso reale: giugno 2026

### Banca ore

Totale banca ore: `18:19`.

Dettaglio:

- 04/06/2026: 14:54-19:18, 04:24
- 05/06/2026: 14:28-19:53, 05:25
- 17/06/2026: 14:30-18:35, 04:05
- 24/06/2026: 15:16-19:41, 04:25

### Straordinari nel file Excel pagabile

Totale Excel pagabile: `40:11`.

Dettaglio:

- 08/06/2026: 14:53-19:17, 04:24
- 09/06/2026: 14:24-19:56, 05:32
- 11/06/2026: 14:38-17:37, 02:59
- 15/06/2026: 14:52-18:42, 03:50
- 16/06/2026: 15:32-18:43, 03:11
- 18/06/2026: 14:50-18:38, 03:48
- 22/06/2026: 15:00-19:56, 04:56
- 23/06/2026: 14:35-18:47, 04:12
- 26/06/2026: 15:03-18:30, 03:27
- 29/06/2026: 15:03-18:55, 03:52

### Esclusi sotto soglia

- 01/06/2026: 13:51-14:13, 00:22
- 30/06/2026: 13:50-14:10, 00:20

## Selettori e funzioni del portale usate

### Login

- URL: `https://serviziweb.inaz.it/portalecbo/default.aspx`
- Cerca frame con `input[type=password]`.
- Username:
  - `input[type=text]`
  - `input[name*=user i]`
  - `input[id*=user i]`
  - `input[name*=login i]`
  - `input[id*=login i]`
- Password:
  - `input[type=password]`
- Submit:
  - `input[type=submit]`
  - `button[type=submit]`
  - testo `Accedi` / `Login`
  - fallback `Enter`.

### Calendario

- frame home URL contiene `HomeCliente/Home.aspx`;
- caption mese: `#WdgtCalendarCaption`;
- cambio mese: `WdgtCalendarMove(step)`;
- apertura giorno: `WdgtCalendarOpen(cell)`;
- celle giorno: `span.WdgtCalCell`;
- dettaglio giorno: frame URL contiene `Cartellino_Giorno.aspx`.

### Dettaglio giorno

- chiusura overlay:
  - `ChiudiFunzione2('')`;
  - `#btnChiudi`;
- riepilogo valori da tabelle;
- extra orario cercato come etichetta `extra orario`;
- anomalie STRNA riconosciute da celle che iniziano con `STRNA`;
- timbrature riconosciute da righe `HH:MM` + `E/U`.

### Richieste

- griglia anomalie: `#TblAnom`;
- griglia richieste: `#TblRich`;
- griglia totali giorno: `#TblTotGio`;
- apri giustificazione: `LocalActionGrid('#TblAnom', 'giustifica', rowId)`;
- maschera evento: frame URL contiene `FunEventi/FunEventiDettaglio.aspx`;
- select evento: `#ListaEventi_MySelect`;
- salvataggio: `GestMenu('6', '')`;
- conferma globale: `#DivDialogBtConferma`.

## Eventi noti

- Straordinario autorizzato:
  - codice: `1081`
  - label: `STR - Straordinario autorizzato`
- Banca ore:
  - codice: `10003`
  - label: `RicBOFT - Incremento Banca Ore`

## Template Excel straordinari

Template: `Straordinari.xlsx`.

Campi:

- `F7`: dipendente;
- `F9`: mese;
- `I9`: anno;
- righe dati: `13:41`;
- colonna B: data;
- colonna C: motivazione;
- colonna H: ora entrata;
- colonna I: ora uscita;
- colonna J: durata;
- totale: `H42 = SUM(J13:J41)`;
- formato durata: `[h]:mm`.

Motivazione consigliata:

```text
Attività di sviluppo applicativi (GAIA/TETI)
```

## PDF e firma

La conversione attuale usa:

```bash
libreoffice --headless --convert-to pdf --outdir straordinari_2026 Straordinari_2026_06_Giugno.xlsx
```

Problemi osservati:

- se la motivazione è troppo lunga, invade le colonne;
- se la colonna B è stretta, le date risultano tagliate;
- la firma del caposettore non sempre è presente nell’Excel, ma può essere presente nel PDF di riferimento.

Regole:

- verificare sempre visualmente il PDF finale;
- la firma deve comparire sotto `V° IL CAPO SETTORE`;
- non deve coprire totale o footer;
- preferire firma nel template, altrimenti supportare overlay configurabile.

## Comandi operativi utili

Leggere codice evento banca ore:

```bash
presenze-richiedi-straordinari \
  --year 2026 \
  --month 6 \
  --day 17 \
  --request-kind banca-ore \
  --list-events \
  --headless
```

Richiedere banca ore:

```bash
presenze-richiedi-straordinari \
  --year 2026 \
  --month 6 \
  --day 17 \
  --request-kind banca-ore \
  --event-value 10003 \
  --event-label "RicBOFT - Incremento Banca Ore" \
  --apply \
  --headless
```

Calcolare straordinari filtrati:

```bash
.venv/bin/python /home/cbo/.codex/skills/inaz-straordinari-filtrati/scripts/calcola_straordinari.py \
  --start-date 2026-06-01 \
  --end-date 2026-06-30 \
  --headless
```

Creare Excel mensili:

```bash
presenze-crea-mesi --template Straordinari.xlsx --output-dir straordinari_2026 --year 2026
```

Estrarre collaboratori/giornaliere:

```bash
presenze-collaboratori \
  --year 2026 \
  --month 5 \
  --json-output giornaliere_maggio_2026.json \
  --template Giornaliere/Giornaliere_2026_803_1.xlsm \
  --xlsx-output Giornaliere/Giornaliere_2026_803_1_compilato.xlsm
```
