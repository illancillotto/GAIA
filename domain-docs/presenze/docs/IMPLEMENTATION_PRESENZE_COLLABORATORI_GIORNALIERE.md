# Implementazione Inaz Collaboratori e Giornaliere

> Stato: documento operativo per portare in GAIA il flusso gia implementato nel repository esterno `/home/cbo/CursorProjects/presenze-scraper`.
> Data riferimento: 2026-05-29.
> Obiettivo: integrare in GAIA lo scraping dei cartellini collaboratori Inaz, il riepilogo eventi e la compilazione del file giornaliere `.xlsm`.

## 1. Cosa e stato implementato nello scraper

Nel repo `presenze-scraper` e stato aggiunto un flusso dedicato ai capisettore:

- file principale: `src/presenze_scraper/collaborators.py`;
- comando CLI: `presenze-collaboratori`;
- entrypoint in `pyproject.toml`: `presenze_scraper.collaborators:main`;
- documentazione d'uso aggiornata in `README.md`.

Il flusso usa una sessione Chrome gia autenticata esposta via CDP sulla porta `9224`.

Comando di prova validato:

```bash
cd /home/cbo/CursorProjects/presenze-scraper
PYTHONPATH=src .venv/bin/python -m presenze_scraper.collaborators \
  --year 2026 \
  --month 5 \
  --limit 1 \
  --json-output /tmp/presenze_test_giornaliere.json \
  --template Giornaliere/Giornaliere_2026_803_1.xlsm \
  --xlsx-output /tmp/Giornaliere_test_compilato.xlsm
```

Esito prova:

- 1 dipendente letto: `1854 AMADU SALVATORE`;
- 31 righe giornaliere estratte da `TblCart`;
- 7 righe di riepilogo eventi estratte da `TblRiepilogo`;
- file `.xlsm` generato preservando macro.

## 2. Flusso Inaz mappato

### 2.1 Accesso

Il login non viene automatizzato in questa iterazione: GAIA o il worker si collegano a un browser gia loggato.

Endpoint CDP usato:

```text
http://127.0.0.1:9224
```

Il browser deve avere aperta una pagina Inaz sotto:

```text
https://serviziweb.inaz.it/portalecbo/
```

### 2.2 Navigazione menu

La voce menu da aprire e:

```text
Consultare > Miei Collaboratori > Cartellino
```

Nel DOM Inaz e stata osservata come:

```text
id="linkPreferiti10614"
text="Cartellino"
onclick="EseguiMenuLeft(this, event, 10614);..."
```

Aprendo la voce viene caricato:

```text
FunModBase/WizRichiesta.aspx
```

con funzione:

```text
Elab=pr_cartellinoro
TipoUtente=respics
```

### 2.3 Periodo

La wizard espone i campi:

```text
date_$zzpf_pr_cartellinoro$periododal$1$0$0
$zzpf_pr_cartellinoro$periododal$1$0$0
date_$zzpf_pr_cartellinoro$periodoal$1$1$0
$zzpf_pr_cartellinoro$periodoal$1$1$0
```

Formato data:

```text
dd/mm/yyyy
```

Esempio maggio 2026:

```text
01/05/2026 - 31/05/2026
```

### 2.4 Apertura lista collaboratori

Il pulsante `Apri` della wizard chiama:

```text
GestMenu('55', '')
```

Dopo `Apri` compare una seconda `WizRichiesta.aspx` con la lista:

```text
Cartellino - (*All'elenco sono stati applicati filtri)
Codice Dipendente
Codice Azienda
Nominativo
Data di Nascita
```

Le righe hanno id del tipo:

```text
$zzlistadip$0$0
```

e attributo `chiave`, esempio:

```text
Kint=10159|KKint={...}|
```

Campi estratti per collaboratore:

- `list_index`;
- `kint`;
- `kkint`;
- `employee_code`;
- `company_code`;
- `name`;
- `birth_date`.

### 2.5 Apertura cartellino singolo

Per ogni collaboratore:

1. selezionare la riga nella lista;
2. chiamare `successivo('Esegui')`;
3. reimpostare il periodo nella wizard del singolo dipendente;
4. cliccare `Apri`.

Viene caricato:

```text
FunPresenze/Cartellino.aspx
```

La pagina contiene:

```text
Cartellino collaboratori in sola lettura
Azienda 53 - Consorzio di bonifica dell'oristanese
Dipendente 1854 - AMADU SALVATORE
```

### 2.6 Griglia giornaliera

La griglia principale e:

```text
table#TblCart
```

Righe:

```text
#TblCart tr.jqgrow
```

Le celle sono mappabili tramite `aria-describedby`, per esempio:

| Campo DOM | Significato |
| --- | --- |
| `TblCart_Data` | giorno settimana + data |
| `TblCart_DataRaw` | data `dd/mm/yyyy` |
| `TblCart_kint_ora` | codice orario, es. `OPE0714`, `OPESAB`, `DOM` |
| `TblCart_Tmb1E` | prima entrata |
| `TblCart_Tmb1U` | prima uscita |
| `TblCart_Tmb2E` | seconda entrata |
| `TblCart_Tmb2U` | seconda uscita |
| `TblCart_Tmb3E` | terza entrata |
| `TblCart_Tmb3U` | terza uscita |
| `TblCart_Cau00` | `TEO` |
| `TblCart_Cau01` | `ORD` |
| `TblCart_Cau02` | `ASS` |
| `TblCart_Cau03` | `GIUST` |
| `TblCart_Cau04` | `MAGG` |
| `TblCart_Cau05` | `MPE` |
| `TblCart_Cau06` | `STR` |
| `TblCart_Stato` | stato giornata |
| `TblCart_Evidenze` | evidenze/anomalie/testo evento |

Esempio riga estratta:

```json
{
  "raw_weekday": "S",
  "work_date": "16/05/2026",
  "schedule_code": "OPESAB",
  "punches": [{"entry": "06:55", "exit": "12:30"}],
  "teo": "06:30",
  "ordinary": "05:30",
  "absence": "01:00",
  "evidenze": "Ore mancanti Permesso ordinario"
}
```

### 2.7 Riepilogo eventi

Dal cartellino singolo si apre:

```text
Eventi > Riepilogo
```

DOM osservato:

```text
id="pr_eventiRiepilogo"
onclick="GestVoceMenu('mnu_eventi','pr_eventiRiepilogo')"
```

Frame caricato:

```text
FunEventi/FunEventiRiepilogo.aspx
```

La griglia riepilogo e:

```text
table#TblRiepilogo
```

Righe:

```text
#TblRiepilogo tr.jqgrow
```

Campi utili:

| Campo DOM | Significato |
| --- | --- |
| `TblRiepilogo_istituto` | codice istituto/evento |
| `TblRiepilogo_descrizione` | descrizione, es. `Ferie`, `Permesso ordinario` |
| `TblRiepilogo_dal` | inizio validita |
| `TblRiepilogo_al` | fine validita |
| `TblRiepilogo_spettante` | spettante/fruibile |
| `TblRiepilogo_fruito` | fruito |
| `TblRiepilogo_residuoprec` | residuo precedente |
| `TblRiepilogo_saldo` | saldo |
| `TblRiepilogo_autorizzato` | autorizzato |
| `TblRiepilogo_proposto` | pianificato/proposto |
| `TblRiepilogo_richiesto` | richiesto |
| `TblRiepilogo_totale` | saldo totale |
| `TblRiepilogo_unitamisura` | unita misura |

Esempio riga:

```json
{
  "code": "10011",
  "description": "Permesso ordinario",
  "start_date": "01/01/2026",
  "end_date": "31/12/2026",
  "values": {
    "spettante": "38:00",
    "fruito": "18:00",
    "saldo": "20:00",
    "richiesto": "04:30",
    "totale": "15:30"
  }
}
```

## 3. Output JSON dello scraper

Il file JSON prodotto ha questa forma:

```json
{
  "period_start": "01/05/2026",
  "period_end": "31/05/2026",
  "employees": [
    {
      "collaborator": {
        "list_index": 1,
        "kint": "10159",
        "kkint": "{...}",
        "employee_code": "1854",
        "company_code": "53",
        "name": "AMADU SALVATORE",
        "birth_date": "26/02/1967"
      },
      "company_label": "53 - Consorzio di bonifica dell'oristanese",
      "period_start": "01/05/2026",
      "period_end": "31/05/2026",
      "daily_rows": [],
      "summary_rows": []
    }
  ]
}
```

GAIA deve trattare questo JSON come formato di interscambio stabile anche quando la sync live Inaz fallisce.

## 4. Compilazione file XLSM

Template di esempio:

```text
/home/cbo/CursorProjects/presenze-scraper/Giornaliere/Giornaliere_2026_803_1.xlsm
```

Fogli osservati:

- `Giornaliera`;
- `Operai`;
- `Archivio`;
- `Archivio2`;
- `Giornaliera2`;
- `Riepilogo`.

La compilazione attuale scrive nel foglio `Archivio2`, preservando il file `.xlsm` con `openpyxl(..., keep_vba=True)`.

Chiave riga:

- matricola/dipendente in colonna `B`;
- periodo in colonna `C`, es. `AVVENTIZI_maggio-2026`.

Campi giornalieri scritti per giorno:

- ordinario feriale;
- ordinario festivo;
- giustificato;
- straordinario feriale/festivo;
- maggiorazione;
- ore assenza;
- codice/testo assenza sintetico da `Evidenze`.

Nota importante: la mappatura XLSM e una prima traduzione tecnica. Va validata con l'ufficio paghe/personale per confermare ogni offset del foglio `Archivio2`.

## 5. Come integrarlo in GAIA

### 5.1 Decisione architetturale

Non eseguire Playwright dentro il processo API FastAPI.

Implementare un worker dedicato o job runner specifico:

```text
modules/presenze/worker/
```

oppure, nel monolite:

```text
backend/app/modules/presenze/services/sync_service.py
```

ma con processo separato per i job live.

Motivo:

- il browser CDP puo restare bloccato;
- Inaz usa iframe e funzioni JS fragili;
- una sync completa su tutti i collaboratori puo durare parecchi minuti;
- dopo restart API serve recovery job.

### 5.2 Moduli backend GAIA

Creare:

```text
backend/app/modules/presenze/
  router.py
  bootstrap.py
  models.py
  schemas.py
  repositories.py
  routes/
    giornaliere.py
    imports.py
    sync_jobs.py
    exports.py
  services/
    import_service.py
    json_parser.py
    xlsm_export.py
    sync_orchestrator.py
```

Per il runtime Playwright, valutare:

```text
modules/presenze/worker/
  worker.py
  presenze_client.py
  requirements.txt
  Dockerfile
```

### 5.3 Data model minimo

Tabelle da aggiungere:

- `presenze_collaborators`;
- `presenze_daily_records`;
- `presenze_daily_punches`;
- `presenze_event_summaries`;
- `presenze_sync_jobs`;
- `presenze_import_jobs`;
- `presenze_export_jobs` opzionale.

`presenze_collaborators`:

- `id`;
- `application_user_id` nullable, se mappato a utente GAIA;
- `kint`;
- `kkint`;
- `employee_code`;
- `company_code`;
- `name`;
- `birth_date`;
- `is_active`;
- `last_seen_at`.

`presenze_daily_records`:

- `id`;
- `collaborator_id`;
- `application_user_id` nullable;
- `work_date`;
- `schedule_code`;
- `teo_minutes`;
- `ordinary_minutes`;
- `absence_minutes`;
- `justified_minutes`;
- `maggiorazione_minutes`;
- `mpe_minutes`;
- `straordinario_minutes`;
- `stato`;
- `evidenze`;
- `raw_payload_json`;
- `source_job_id`;
- `created_at`;
- `updated_at`.

`presenze_daily_punches`:

- `id`;
- `daily_record_id`;
- `sequence`;
- `entry_time`;
- `exit_time`;

`presenze_event_summaries`:

- `id`;
- `collaborator_id`;
- `application_user_id` nullable;
- `period_start`;
- `period_end`;
- `event_code`;
- `description`;
- `valid_from`;
- `valid_to`;
- `spettante`;
- `fruito`;
- `residuo_prec`;
- `saldo`;
- `autorizzato`;
- `pianificato`;
- `richiesto`;
- `saldo_totale`;
- `unitamisura`;
- `raw_payload_json`.

### 5.4 API GAIA

Endpoint consigliati:

| Metodo | Path | Scopo |
| --- | --- | --- |
| `GET` | `/presenze/collaborators` | lista collaboratori Inaz |
| `PUT` | `/presenze/collaborators/{id}/application-user` | collega collaboratore a `application_users` |
| `GET` | `/presenze/giornaliere` | lista giornaliere con filtri |
| `GET` | `/presenze/giornaliere/{id}` | dettaglio giornaliera |
| `GET` | `/presenze/collaborators/{id}/calendar` | calendario mese |
| `GET` | `/presenze/collaborators/{id}/summary` | riepilogo eventi |
| `POST` | `/presenze/import/json` | importa JSON prodotto dallo scraper |
| `POST` | `/presenze/sync/jobs` | avvia job live Inaz |
| `GET` | `/presenze/sync/jobs/{id}` | stato job |
| `GET` | `/presenze/export/giornaliere.xlsm` | genera XLSM |

### 5.5 Permessi

Estendere quanto gia previsto in `GAIA_PRESENZE_GIORNALIERE_MODULE_SPEC.md`:

- `inaz.dashboard`;
- `inaz.collaborators`;
- `inaz.giornaliere`;
- `inaz.summary`;
- `inaz.import`;
- `inaz.sync`;
- `inaz.export`;
- `inaz.admin`.

### 5.6 Frontend

Route:

```text
frontend/src/app/presenze/
  page.tsx
  collaboratori/page.tsx
  collaboratori/[id]/page.tsx
  giornaliere/page.tsx
  import/page.tsx
  sync/page.tsx
  export/page.tsx
```

Viste:

- dashboard mese corrente;
- lista collaboratori con stato mapping GAIA;
- dettaglio collaboratore con calendario mensile;
- tab `Cartellino`;
- tab `Riepilogo eventi`;
- import JSON;
- monitor sync live;
- export XLSM.

## 6. Strategia di import sicura

Fase 1 consigliata:

1. GAIA importa solo JSON prodotto da `presenze-collaboratori`.
2. Nessuna sync live dal backend.
3. Persistenza DB e UI consultazione.
4. Export XLSM da dati DB.

Fase 2:

1. worker Inaz live collegato a browser/CDP;
2. job persistenti;
3. diagnostica HTML/JSON in caso di errore;
4. retry controllato per singolo collaboratore;
5. fallback manuale con import JSON.

## 7. Validazioni necessarie

Prima di mettere in produzione:

- confermare con l'utente finale che `TblCart_Cau00..Cau06` siano sempre mappati a `TEO`, `ORD`, `ASS`, `GIUST`, `MAGG`, `MPE`, `STR`;
- confermare la semantica di `MPE` rispetto a `STR`;
- confermare gli offset del foglio `Archivio2`;
- verificare casi con piu di tre timbrature;
- verificare dipendenti senza data nascita;
- verificare collaboratori duplicati con stesso nome ma matricola diversa;
- verificare periodo diverso dal mese pieno;
- verificare cosa succede se Inaz apre un riepilogo gia esistente in frame precedente.

## 8. Test da implementare in GAIA

Backend:

- parser JSON con fixture reale;
- conversione `HH:MM` in minuti;
- import idempotente stesso collaboratore/data;
- mapping collaboratore -> `application_users`;
- riepilogo eventi normalizzato;
- export XLSM preserva macro;
- job sync fallito non lascia record parziali non tracciati.

Frontend:

- lista collaboratori;
- calendario giornaliere;
- dettaglio riepilogo eventi;
- import JSON con preview;
- monitor job.

Worker:

- mock DOM per lista collaboratori;
- mock DOM per `TblCart`;
- mock DOM per `TblRiepilogo`;
- recovery se frame non trovato;
- timeout per singolo dipendente.

## 9. Prompt Codex per implementare in GAIA

```text
Implementa in GAIA il modulo Inaz Collaboratori/Giornaliere partendo dal flusso gia
sviluppato in `/home/cbo/CursorProjects/presenze-scraper/src/presenze_scraper/collaborators.py`.

Obiettivo MVP:
- importare in GAIA il JSON prodotto da `presenze-collaboratori`;
- salvare collaboratori, giornaliere, timbrature e riepilogo eventi;
- collegare opzionalmente un collaboratore Inaz a `application_users`;
- mostrare frontend con lista collaboratori, calendario giornaliere e riepilogo eventi;
- generare export `.xlsm` dal DB usando la stessa logica di compilazione del template.

Regole:
- backend nel monolite modulare sotto `backend/app/modules/presenze/`;
- route sotto prefisso `/presenze`;
- usare job persistenti per import/export/sync;
- non eseguire Playwright nel processo API per sync live;
- non salvare credenziali o storage state in chiaro;
- aggiungere `module_presenze` a `application_users` solo se non gia presente;
- aggiungere sezioni `inaz.*` al bootstrap permessi;
- aggiungere test backend con fixture JSON reale o ridotta;
- preservare macro XLSM con `openpyxl.load_workbook(..., keep_vba=True)`.

Dettagli Inaz:
- menu collaboratori: `linkPreferiti10614`;
- wizard: `FunModBase/WizRichiesta.aspx`;
- funzione: `pr_cartellinoro`;
- periodo: campi `date_$zzpf_pr_cartellinoro$periododal$1$0$0`,
  `date_$zzpf_pr_cartellinoro$periodoal$1$1$0` e relativi hidden;
- lista collaboratori: righe `tr[id^="$zzlistadip$"]`, attributo `chiave`
  con `Kint` e `KKint`;
- cartellino: `FunPresenze/Cartellino.aspx`, tabella `#TblCart tr.jqgrow`;
- riepilogo: `FunEventi/FunEventiRiepilogo.aspx`, tabella `#TblRiepilogo tr.jqgrow`.
```

## 10. Comandi operativi per generare input GAIA

Genera JSON del mese completo:

```bash
cd /home/cbo/CursorProjects/presenze-scraper
PYTHONPATH=src .venv/bin/python -m presenze_scraper.collaborators \
  --year 2026 \
  --month 5 \
  --json-output giornaliere_maggio_2026.json
```

Genera JSON e XLSM:

```bash
cd /home/cbo/CursorProjects/presenze-scraper
PYTHONPATH=src .venv/bin/python -m presenze_scraper.collaborators \
  --year 2026 \
  --month 5 \
  --json-output giornaliere_maggio_2026.json \
  --template Giornaliere/Giornaliere_2026_803_1.xlsm \
  --xlsx-output Giornaliere/Giornaliere_2026_803_1_compilato.xlsm
```

Genera XLSM da JSON gia estratto:

```bash
cd /home/cbo/CursorProjects/presenze-scraper
PYTHONPATH=src .venv/bin/python -m presenze_scraper.collaborators \
  --year 2026 \
  --month 5 \
  --from-json giornaliere_maggio_2026.json \
  --template Giornaliere/Giornaliere_2026_803_1.xlsm \
  --xlsx-output Giornaliere/Giornaliere_2026_803_1_compilato.xlsm
```


## Buoni pasto manuali, sync operativa e permessi sindacali — 2026-10-01

### Analisi preliminare (prima dell'implementazione)

| Requisito | Implementazione attuale | Problema | Modifica proposta e applicata |
| --- | --- | --- | --- |
| Buono pasto manuale | GATE XLSM applica automaticamente data >= 2026-08-26 ed extra riconosciuto >= 120 minuti; GAIA non persiste un riconoscimento manuale | Nessuna eccezione giornaliera per turnazione temporanea | Flag sulla giornaliera, audit, conteggio OR 0/1; nessun attributo turnista sull'anagrafica |
| UI operativa | Giornaliere con PATCH autorizzata; Giornaliera individuale di consultazione | Inserimento rapido e riepilogo mancanti | Checkbox nel dettaglio Giornaliere, riga e totale nella Giornaliera individuale |
| Sync INAZ manuale | API sync/jobs, worker, polling, retry e scheduler esistenti | Avvio non serializzato con lo scheduler; comando fuori dalla sezione operativa | Comando mese/persona e lock PostgreSQL condiviso, senza altra pipeline |
| Anomalie dopo sync | Import aggiorna record/timbrature; algoritmo calcolato nelle letture | Dashboard snapshot e cache mensile frontend possono essere stale | Invalidazione snapshot nella transazione di finalizzazione import e ricaricamento UI al completamento |
| Permesso sindacale | KEvento strutturato nelle richieste; normalizzazione testuale generica | OREM e ore mancanti possono includere ore coperte dal permesso | PSIRSA/PSIEST/ASS.SIN, stato valido e justified_minutes; filtraggio solo OREM interamente coperto |
| Sabati | Policy operai e riposi contributivi gia presenti | Nessuna nuova regola richiesta | Algoritmi mantenuti e test di regressione riutilizzati |
| Export | GAIA/GATE ARCHIVE2 e ARCHIVIO XLSM esistenti | GAIA non scrive buoni; GATE non legge manuale | Stesso conteggio unico nelle colonne giornaliere e nel totale, macro preservate |

### Modelli, API e servizi

Entita riutilizzata: `PresenzeDailyRecord`, univoca per collaboratore/data.
Migration Alembic `20261001_1400` sopra `20260923_1300`: `meal_voucher_manual`
boolean non nullable con default false e `meal_voucher_audit` JSON nullable.
Upgrade preserva i record; downgrade rimuove i soli nuovi campi, perdendo
necessariamente i riconoscimenti manuali e relativo audit. Verifica reale
upgrade/downgrade/upgrade su PostgreSQL isolato.

PATCH `/presenze/giornaliere/{record_id}` usa i privilegi di rettifica esistenti.
La scrittura manuale prende un row lock; ripetere lo stesso valore non aggiunge
voci audit. Attivazione/revoca registrano attore, istante UTC, valore precedente
e nuovo. L'import INAZ preserva questi campi. La risposta full/matrix espone
manuale, automatico, count, sources; full espone anche audit. Il payload canonico
GAIA/GATE porta gli stessi valori; l'export GATE riconosce il flag manuale.
Il conteggio e sempre `int(automatic or manual)`, incluso quando entrambi sono veri.
La soglia automatica esistente resta invariata, centralizzata in GAIA e
compatibile con il compilatore GATE. XLSM: ARCHIVE2 offset 341 e ARCHIVIO colonna 23.

### Pipeline e concorrenza

Il frontend accoda il job tramite l'API esistente e non attende il lavoro INAZ
nella richiesta HTTP. Il worker esistente esegue scraper, import, normalizzazione,
persistenza e finalizzazione; i serializer e il servizio operational_quality
riutilizzano il calcolo presenze/anomalie. Nessun microservizio, database o worker
aggiuntivo. Backend unico FastAPI modulare, frontend unico, PostgreSQL unico.

Avvio manuale e retry prendono l'advisory transaction lock 760031001, lo stesso
dello scheduler. Il controllo pending/running e l'accodamento restano sotto lock
fino al commit. Contesa o job incompatibile restituiscono 409. Stale reconciliation,
lease e retry del runtime esistente restano in uso. Il frontend protegge il doppio
click con ref, non sovrappone polling, recupera lo stato persistito dopo refresh,
mostra disponibilita/in corso/esito/errore/ultima riuscita per periodo e persona.
Completamenti parziali sono segnalati e non contano come ultima riuscita.
La richiesta mensile non impone limiti ai circa 200 collaboratori; la richiesta
individuale usa employee_codes. Lo storico Sync Presenze mantiene i comandi Retry.

### Causali INAZ e limiti funzionali

Codici effettivi osservati in lettura: `PSIRSA` (permesso sindacale HH RSA),
`PSIEST` (permesso GG direttivo sindacato), `ASS.SIN` (assemblea sindacale), stato FRU.
Il codice strutturato precede la descrizione. Stati accettati dalla normalizzazione:
FRU, ACC, AUT, APPROVATO, AUTORIZZATO. Quantita assente/negativa o stato non valido
non coprono ore. Per il sindacale si usa justified_minutes: absence_minutes puo
contenere tutta la giornata anche per un permesso parziale e non e prova di copertura.

OREM e rimosso dalla vista normalizzata solo se ordinario + minuti giustificati
coprono la teoria positiva. Altre anomalie, timbrature mancanti ed errori tecnici
restano visibili; il payload originale resta disponibile per audit. Causali legacy
e sabati mantengono il comportamento precedente. L'assenza ingiustificata non viene
trasformata in permesso. Codici/stati INAZ diversi richiedono un esempio strutturato
verificato; non si deducono dai nomi dei collaboratori.

### Esecuzione e verifica

Implementazione e test locali; nessun deploy o avvio sync di produzione.
Esiti aggiornati nella sezione operazioni del documento PROGRESS_PRESENZE e nel
piano coverage. Il commit finale resta subordinato ai quality gate richiesti.


### Report finale del ciclo locale — 2026-10-01

Implementati il buono pasto manuale per collaboratore/data con audit, il conteggio
unico automatico OR manuale, i comandi INAZ nelle viste operative, il refresh
delle anomalie e degli snapshot dopo import, la causale sindacale strutturata
e gli export XLSM GAIA/GATE. Nessun attributo turnista sul collaboratore.

Bug corretti: avvii concorrenti manuali/scheduler, snapshot dashboard stale,
falsi OREM per permesso sindacale interamente giustificato e RangeError della
matrice quando il selettore mese viene svuotato. Il mese precedente valido
rimane selezionato fino a una nuova scelta valida.

Gia presenti e verificati: pipeline in background, worker/lease, retry,
normalizzazione delle timbrature, algoritmo presenze/anomalie e sabati,
autorizzazioni e conservazione macro XLSM. Nessuna seconda pipeline o nuova
infrastruttura. Monolite modulare FastAPI, frontend unico e PostgreSQL unico.

Migration reversibile `20261001_1400` su `20260923_1300`: riusa la giornaliera
persistendo `meal_voucher_manual` (default false) e `meal_voucher_audit`.
Upgrade/downgrade/upgrade verificati su PostgreSQL isolato senza perdere i dati
pregressi. GATE conserva gia il payload canonico: nessuna migration GATE.

#### Intervento circoscritto autorizzato sui blocchi

Le baseline non riproducevano neppure il codice precedente. Riparate da checkout
con runtime pulito, prima della feature, in commit separati:

- GAIA `dc66972813970573ec5d1dd8d0b3426fa6c56116`,
  `fix(quality): repair stale baselines only from clean runtime`;
- GATE `3baaed8cab5412dca2cc7c405161bb105b33a22e`,
  `chore(quality): repair stale baseline from committed runtime`.

Il nuovo comando GAIA `baseline-repair` rifiuta runtime/eccezioni modificati,
scansioni parziali e cambi di scope. Tooling: 83 test GAIA e 36 GATE passati.
Il ratchet feature usa le baseline di questi commit, senza assorbire regressioni.
Le baseline finali sono sincronizzate soltanto dopo il ratchet e verificate.

Semplificazioni locali: serializzazione condivisa dei bucket classificati,
contratto esplicito dei campi manuali giornalieri, toolbar della Giornaliera
Individuale, riga dei buoni e contatori mensili con responsabilita separate,
riuso del caricamento mese dopo sync e aggiornamenti null-safe dell'editor.
I callback modificati hanno nomi espliciti per evitare matching posizionali
ambigui. Nessuna esclusione coverage aggiunta; rimossa quella file-wide della
pagina Giornaliere. Nessun refactoring di altri domini.

| Quality gate | Esito locale |
| --- | --- |
| Backend Presenze + payload/sync GATE | 985 casi raccolti; 975 passati e 10 PostgreSQL inizialmente skipped; tutti i 10 rieseguiti con URL dedicati e passati |
| PostgreSQL nuovo comportamento | 3 test: lock scheduler/manuale, grant concorrente idempotente, migration round trip |
| Backend full-file runtime modificato | 17 file, 100% statement e branch nelle suite aggregate |
| Frontend unit pertinenti | 215 passati; 100% statement, branch, funzioni e linee su tutti i runtime modificati |
| Frontend suite completa | 2881 passati; una failure preesistente Ruolo/Solleciti riprodotta anche sul checkout precedente |
| npm test frontend | 18 passati |
| Typecheck GAIA/GATE, Ruff, formatter nuovi Python | Passati |
| Lint frontend e runtime XLSM GATE | Passati; warning frontend legacy in altri domini |
| Build frontend pulita e build workspace GATE | Passate |
| E2E Chromium | 3 passati: voucher/sync/refresh e permessi read-only/approve |
| Alembic | Unica head 20261001_1400; round trip PostgreSQL passato |
| Ratchet GAIA/GATE | Passati contro HEAD riparati; nessuna regressione assorbita |
| Baseline verify GAIA/GATE | Passati |
| Export XLSM GATE | 35 passati, caso directory rieseguito dopo correzione della fixture; 599/599 statement, 435/435 branch, 116/116 funzioni, 513/513 linee (100%) aggregando i due run sullo stesso runtime |

La failure frontend fuori scope e `ruolo-tributi-placeholder-pages.test.tsx`,
caso `renders reminders placeholder`: il componente Solleciti richiede il router
Next. Riprodotta sul codice precedente; nessuna modifica automatica al dominio
Ruolo o al suo test. Il working tree condiviso contiene altre modifiche, escluse
dai commit: Wiki/MCP, cancellazione squadre, refresh collaboratori GATE,
Makefile, altri hotspot, Poste/Ruolo e test/documenti di cicli concorrenti.
I controlli sono eseguiti su checkout isolati con il solo perimetro della feature.

#### File principali e test

Backend `backend/app/modules/presenze/`: models, schemas,
`daily_record_schemas.py`, helper daily_records/jobs, route collaborators_daily/
sync_jobs e servizi meal_vouchers, sync_start, inaz_absences, daily_details,
parser, import_jobs, operai_rules, operational_quality, gate_mobile_payloads e
xlsm_export. Frontend: Giornaliere, Giornaliera Individuale (page/table/controls),
InazSyncControl/useInazSync, MealVoucherControl, stato INAZ/editor, contatori
mensili e tipi API. GATE: `presenze-xlsm-export.ts` e relativo test.

Test aggiunti: meal voucher automatico/manuale e audit, causali/stati sindacali,
schema giornaliera, PostgreSQL concorrenza/migration, controlli UI operativi,
regressioni della matrice ed editor, E2E voucher/sync. Test aggiornati: helper
API, Giornaliera Individuale, gerarchia E2E con mese fixture esplicito ed export
XLSM con directory complete, metadati assenti e codici fiscali discordanti.
La suite di regressione separata consente di verificare le modifiche senza
includere wholesale il test condiviso modificato da altri cicli.

Documentazione aggiornata in luogo: questo implementation plan/report,
GIORNALIERA_INDIVIDUALE, INAZ_FUNZIONI_E_REGOLE, PROGRESS_PRESENZE,
PRESENZE_PROGETTO_DEDICATO_IMPLEMENTATION_PLAN, GAIA_PRESENZE_GIORNALIERE_MODULE_SPEC,
GATE_MOBILE_INAZ_SYNC_CONTRACT, piano coverage e progress code quality.
GATE: PRESENZE_EXPORT_CONTROLS. Graphify usa i corpus previsti dagli AGENTS.md;
gli artifact restano locali e ignorati.

#### Dipendenze esterne e consegna

Le prove usano fixture sintetiche e PostgreSQL isolato. Nessuna sincronizzazione
INAZ, migration o modifica dati eseguita in produzione. Il risultato reale
richiede INAZ disponibile e credenziali attive. Codici osservati PSIRSA/PSIEST/
ASS.SIN con stato FRU; ACC/AUT e stati testuali autorizzati sono supportati.
Nuovi codici richiedono conferma funzionale, senza affidarsi solo alla descrizione.
La giustificazione usa `justified_minutes`, mai le ore di assenza aggregate.

Branch di consegna `main` in entrambi i repository. HEAD iniziali:
GAIA `4a9af2318d5c289cadc05f3d1bf64cf4c6ba500e`,
GATE `aa259f29bbc19f4b9ed52c3dd4be470d2b7e86e6`.
Commit feature previsti dopo i gate:
`feat(presenze): add audited meal vouchers and operational INAZ sync` e
`fix(presenze): include manual meal vouchers in XLSM export`.
Hash finali e inventario esatto sono riportati nella consegna e in `git show`.
Nessun push o deploy richiesto.
