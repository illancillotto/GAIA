# Implementation plan: progetto dedicato Presenze

## Obiettivo

Realizzare un progetto Python dedicato per automatizzare:

- login e navigazione sul portale Presenze CBO;
- lettura cartellino giornaliero;
- calcolo straordinari con soglia minima;
- rilevazione e richiesta banca ore;
- richiesta straordinario autorizzato;
- generazione Excel/PDF mensili;
- firma caposettore nei PDF;
- estrazione cartellini collaboratori e giornaliere.

Il progetto sorgente da cui derivare logiche e selettori e `/home/cbo/CursorProjects/inaz-scraper`.

## Note di naming

- nel prodotto GAIA il naming canonico del dominio e `Presenze`;
- `Inaz` resta solo come riferimento legacy al portale sorgente o al repository sperimentale;
- nuovo codice, nuova documentazione operativa e nuove CLI non devono usare `Inaz` come naming principale del modulo.
- i nomi `src/inaz_scraper/` e le CLI `inaz-*` presenti in questo piano descrivono il materiale legacy da migrare o un bridge temporaneo di compatibilita, non il naming finale raccomandato.

## Architettura proposta

```text
src/inaz_scraper/
  auth.py           # login, storage state, browser factory
  portal.py         # frame helpers, wait, overlay/dialog helpers
  calendar.py       # calendario home, cambio mese, apertura giorno
  day_detail.py     # parse Cartellino_Giorno.aspx
  overtime.py       # calcolo straordinari e banca ore
  requests.py       # inserimento richieste STR/banca ore
  excel.py          # template mensili e popolamento
  pdf.py            # export LibreOffice + firma
  collaborators.py  # flusso collaboratori/giornaliere
  inspect.py        # diagnostica DOM/iframe
  models.py         # dataclass dominio
  timeutils.py      # HH:MM <-> minuti, date
```

## Modelli dominio

```python
@dataclass(frozen=True)
class OvertimeItem:
    day: date
    start_time: str | None
    end_time: str | None
    duration: str
    punches: list[tuple[str, str]]

@dataclass(frozen=True)
class BankHoursRequest:
    day: date
    description: str
    start_time: str | None
    end_time: str | None
    duration: str | None
    status: str | None

@dataclass(frozen=True)
class DayReport:
    overtime: list[OvertimeItem]
    bank_hours_requests: list[BankHoursRequest]

@dataclass(frozen=True)
class RequestCandidate:
    day: date
    anomaly_row_id: str
    start_time: str
    end_time: str
    duration: str
    already_requested: bool
```

## Fase 1: bootstrap progetto

1. Crea `pyproject.toml`.
2. Dipendenze minime:
   - `playwright>=1.44`
   - `python-dotenv>=1.0`
   - `openpyxl>=3.1`
   - `pytest`
   - opzionale `pillow`
3. Entry point CLI:
   - `inaz-inspect`
   - `inaz-straordinari-scan`
   - `inaz-straordinari-calcola`
   - `inaz-richieste`
   - `inaz-crea-mesi`
   - `inaz-popola-excel`
   - `inaz-collaboratori`

## Fase 2: browser, credenziali e login

Implementare:

- `load_credentials(db, current_user, credential_id=None)` che:
  - legge la credenziale dal database;
  - limita l'accesso alle credenziali del singolo operatore;
  - decifra la password solo al momento dell'uso;
- `save_operator_request_config(...)` per persistere configurazioni come evento banca ore per operatore;
- `system_chromium()` che cerca `chromium`, `chromium-browser`, `google-chrome`, `google-chrome-stable`;
- `open_browser(headless, browser_executable, storage_state)`;
- `login(page, username, password)`;
- `wait_for_portal_idle(page)`.

Dettagli login:

- URL: `https://serviziweb.inaz.it/portalecbo/default.aspx`;
- cercare iframe con `input[type=password]`;
- cercare input username con selettori generici `user/login`;
- submit con bottone `Accedi/Login` o `Enter`;
- salvare storage state dopo login.

Dettagli persistenza credenziali:

- creare modello DB dedicato credenziali Presenze associato a `application_user_id`;
- cifrare `password` a riposo;
- esporre CRUD backend per creazione, aggiornamento, test login e disattivazione;
- evitare completamente username/password del portale in `.env`, salvo eventuali fallback temporanei solo in ambienti di sviluppo isolati se esplicitamente richiesto.

## Fase 3: navigazione calendario

Implementare:

- `home_frame(page)` trova frame con URL contenente `HomeCliente/Home.aspx`;
- `open_calendar_month(page, year, month)`:
  - legge `#WdgtCalendarCaption`;
  - calcola delta mesi;
  - invoca `WdgtCalendarMove(step)`;
  - attende caption attesa, es. `Giugno 2026`;
- `open_day_detail(page, day)`:
  - chiude overlay vecchi;
  - trova `span.WdgtCalCell` con numero giorno;
  - invoca `WdgtCalendarOpen(cell)`;
  - attende frame `Cartellino_Giorno.aspx` con testo data `dd/mm/yyyy`.

## Fase 4: parsing dettaglio giorno

Implementare funzioni pure e testabili:

- `table_rows(frame) -> list[list[str]]`;
- `read_detail_date(frame, fallback_day)`;
- `summary_values(rows)` per leggere `extra orario`;
- `punch_rows(rows)` per timbrature `HH:MM E/U`;
- `anomaly_intervals(rows)` per anomalie `STRNA`;
- `first_last_punch(rows)` fallback.

Regola calcolo:

1. Se non c’è `extra orario` o è `00:00`, non c’è overtime.
2. Se ci sono anomalie STRNA con due orari, usare quegli intervalli.
3. Altrimenti usare primo/ultimo punch fallback e durata da `extra orario`.
4. Durata = differenza `end-start`, con gestione attraversamento mezzanotte.

## Fase 5: richieste banca ore esistenti

Implementare:

- lettura griglia `TblRich` via jqGrid;
- fallback ricerca tabella con titolo `Richieste`;
- normalizzazione chiavi a lowercase;
- riconoscimento banca ore se descrizione contiene:
  - `banca ore`;
  - `ricbo`;
  - `RicBOFT`;
- estrazione:
  - `Dalle` / `dalle`;
  - `Alle` / `alle`;
  - `Qta` / `durata`;
  - `Stato`.

Deduplicare su `(day, description, start_time, end_time, duration)`.

## Fase 6: calcolo straordinari

CLI:

```bash
inaz-straordinari-calcola --start-date 2026-06-01 --end-date 2026-06-30 --threshold-minutes 30 --headless
```

Output richiesto:

- lordi sopra soglia;
- esclusi sotto soglia;
- banca ore;
- pagabili.

Regole:

- soglia default 30 minuti;
- mostra timbrature per ogni incluso;
- in output utente usare date `dd/mm/yyyy`;
- per report macchina usare anche ISO se utile;
- non mischiare questi concetti:
  - `straordinari_lordi_sopra_soglia`: tutto l’extra orario sopra soglia rilevato;
  - `banca_ore_richieste`: richieste banca ore, anche se il giorno non era nel file pagabile;
  - `straordinari_excel_pagabili`: righe da scrivere su Excel dopo esclusione banca ore;
  - `pagamento_total`: se serve come differenza contabile, chiarire sempre la formula.

Acceptance test giugno 2026:

- banca ore totale: `18:19`;
- Excel pagabile dopo esclusioni: `40:11`;
- esclusi sotto soglia: `01/06/2026 00:22`, `30/06/2026 00:20`.

## Fase 7: creazione richieste

CLI:

```bash
inaz-richieste --year 2026 --month 6 --day 17 --request-kind banca-ore --list-events --headless
inaz-richieste --year 2026 --month 6 --day 17 --request-kind banca-ore --event-value 10003 --apply --headless
```

Implementare:

- `read_request_candidates(detail, day, threshold_minutes, request_event)`;
- legge `TblAnom`, `TblRich`, `TblTotGio`;
- filtra anomalie `STRNA`;
- ignora sotto soglia;
- controlla richiesta esistente con evento/intervallo;
- `open_event_detail` via `LocalActionGrid('#TblAnom', 'giustifica', rowId)`;
- `read_event_options` da `#ListaEventi_MySelect`;
- `fill_event_detail`;
- `save_event_detail`;
- `confirm_global_dialogs`.

Eventi noti:

- `1081` = `STR - Straordinario autorizzato`;
- `10003` = `RicBOFT - Incremento Banca Ore`.

Dry-run default. Solo `--apply` salva.

## Fase 8: Excel

Creazione mensili:

- template `Straordinari.xlsx`;
- output `straordinari_YYYY/Straordinari_YYYY_MM_Mese.xlsx`;
- mese in `F9`;
- anno in `I9`;
- dipendente in `F7` se richiesto.

Popolamento:

- righe 13-41;
- colonna B data `dd/mm/yyyy`;
- colonna C motivazione;
- colonna H entrata;
- colonna I uscita;
- colonna J durata con `[h]:mm`;
- totale in `H42 = SUM(J13:J41)`.

Gestione layout:

- saltare `MergedCell`;
- preservare stili;
- motivazione compatta `Attività di sviluppo applicativi (GAIA/TETI)`;
- se la colonna data risulta tagliata, allargare B e ridurre motivazione mantenendo stampa su A4.

## Fase 9: PDF e firma

Implementare `export_pdf(xlsx, out_dir)` con LibreOffice.

Firma:

- supportare immagine `--signature-image`;
- preferire inserirla in Excel se possibile;
- se non affidabile, overlay su PDF con Pillow/Poppler come fallback;
- coordinate configurabili via opzioni o file YAML;
- verificare visivamente o con test snapshot manuale che:
  - firma sta sotto `V° IL CAPO SETTORE`;
  - non copre il totale;
  - resta dentro bordo pagina.

## Fase 10: collaboratori/giornaliere

Migrare il modulo esistente mantenendo:

- connessione CDP a browser già loggato;
- apertura wizard collaboratori;
- impostazione periodo;
- lista collaboratori;
- estrazione giornaliere;
- dettaglio giorno;
- riepilogo eventi;
- JSON checkpoint;
- compilazione XLSM preservando macro.

## Fase 11: test

Test unitari minimi:

- `time_to_minutes`, `minutes_to_duration`, `duration_to_excel_time`;
- soglia 30 minuti;
- esclusione banca ore da Excel pagabile;
- somma banca ore `04:24 + 05:25 + 04:05 + 04:25 = 18:19`;
- somma straordinari pagabili giugno `40:11`;
- parsing righe jqGrid fixture;
- idempotenza richiesta: stessa data/intervallo/evento => `already_requested=True`.

Test integrazione manuale:

- login headless;
- `--list-events`;
- dry-run richieste;
- `--apply` su un giorno controllato;
- generazione Excel/PDF.

## Rischi e mitigazioni

- DOM portale cambia: mantenere un comando di inspect e fallback robusti.
- Iframe lenti: wait espliciti e retry.
- jqGrid non disponibile: fallback su DOM tabellare.
- LibreOffice altera layout: mantenere template pulito e verificare PDF.
- Richieste duplicate: controllo evento + orario prima di salvare.
- Banca ore non coincide con righe Excel: tenere totali separati.
