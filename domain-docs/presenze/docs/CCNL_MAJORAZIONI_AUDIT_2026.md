# Audit CCNL INAZ 2026 - Maggiorazioni, notturno, festivo, profili orari

Data: 2026-06-23

## Obiettivo

Verificare se il modulo `inaz` di GAIA implementa gia una logica coerente con il CCNL Bonifica 2026 per:

- maggiorazione notturna;
- maggiorazione festiva;
- maggiorazione festiva notturna;
- distinzione tra operai e impiegati;
- esposizione al frontend del dato "orario teorico standard".

Documento contrattuale analizzato:

- `/home/cbo/Downloads/CCNL_Bonifica_2026.pdf`

Articoli rilevanti:

- `Art. 47 - Orario di lavoro`
- `Art. 48 - Riposo settimanale`
- `Art. 49 - Lavoro notturno`
- `Art. 50 - Festivita`
- `Art. 80 - Compenso per lavoro straordinario e festivo`
- `Art. 82 - Compenso per lavoro ordinario notturno`
- `Art. 83 - Compenso per lavoro prestato in turni`

## Evidenze CCNL

### Art. 47 - Orario di lavoro

- L'orario ordinario contrattuale e `38 ore settimanali`.
- Il CCNL non codifica come regola generale un unico standard "operai 7:00 al giorno" e "impiegati 6:25 al giorno".
- La distribuzione concreta dell'orario e demandata all'organizzazione aziendale e agli accordi con `RSA/RSU`.

### Art. 49 - Lavoro notturno

- Il periodo notturno e definito come `22:00 - 06:00`.

### Art. 80 - Lavoro straordinario e festivo

Per lavoro compiuto oltre l'orario normale:

- `+25%` lavoro straordinario diurno;
- `+50%` lavoro straordinario festivo o notturno;
- `+75%` lavoro straordinario festivo notturno.

Il CCNL specifica inoltre:

- lavoro notturno = lavoro compiuto tra `22:00` e `06:00`;
- lavoro festivo = lavoro compiuto nei giorni riconosciuti festivi;
- eccezione da valutare per lavoro svolto in conseguenza di regolare turno.

### Art. 82 - Lavoro ordinario notturno

Per il dipendente che svolge normalmente lavoro di notte:

- `+15%` per ogni ora di effettivo lavoro notturno se il lavoro notturno raggiunge almeno `20 notti` nel mese;
- `+10%` altrimenti.

### Art. 83 - Lavoro prestato in turni entro orario ordinario

Maggiorazioni su lavoro in turni entro orario ordinario:

- `+10%` lavoro festivo o domenicale diurno;
- `+15%` lavoro feriale notturno;
- `+20%` lavoro festivo o domenicale notturno.

## Stato attuale dell'implementazione GAIA

### Aggiornamento implementativo 2026-06-23

Da oggi il backend espone anche un breakdown runtime dei minuti giornalieri derivato da timbrature e template:

- `night_minutes`
- `festive_minutes`
- `festive_night_minutes`
- `ordinary_night_minutes`
- `overtime_day_minutes`
- `overtime_night_minutes`
- `overtime_festive_minutes`
- `overtime_festive_night_minutes`
- `shift_festive_day_minutes`
- `shift_night_minutes`
- `shift_festive_night_minutes`

Stato del dato:

- il breakdown e calcolato a runtime nel `schedule_engine`;
- supporta anche turni e timbrature oltre la mezzanotte;
- non e ancora materializzato in tabella su `presenze_daily_records`;
- non e ancora scritto in colonne dedicate dell'export XLSM;
- non implementa ancora la soglia Art. 82 delle `20 notti/mese`.

### Backend - import/parsing

Il parsing importa un campo generico:

- `maggiorazione_minutes`

Riferimenti:

- [backend/app/modules/presenze/services/parser.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/presenze/services/parser.py:151)
- [backend/app/modules/presenze/models.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/presenze/models.py:270)
- [backend/app/modules/presenze/schemas.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/presenze/schemas.py:357)

Limite:

- il modello non distingue il tipo di maggiorazione;
- non separa notturno, festivo, festivo notturno;
- non distingue il perimetro `ordinario`, `straordinario`, `turni`.

### Backend - motore orari

Il motore attuale:

- risolve festivita e giorni speciali;
- applica template orari e regole di presenza;
- calcola `ordinary_minutes` e `extra_minutes` come differenza tra timbrature e regole ordinarie.

Riferimenti:

- [backend/app/modules/presenze/services/schedule_engine.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/presenze/services/schedule_engine.py:93)
- [backend/app/modules/presenze/services/schedule_engine.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/presenze/services/schedule_engine.py:180)

Limite:

- il motore non calcola oggi la quota di minuti nella fascia `22:00-06:00`;
- non produce breakdown `festivo`, `notturno`, `festivo_notturno`;
- non distingue il lavoro a turni dal lavoro straordinario per finalita contrattuali.

### Backend - export XLSM

L'export distingue solo:

- ordinario feriale / ordinario festivo;
- extra feriale / extra festivo.

Riferimenti:

- [backend/app/modules/presenze/services/xlsm_export.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/presenze/services/xlsm_export.py:271)

Limite:

- manca la scrittura di maggiorazioni contrattuali specifiche;
- `special_day` e un flag utile, ma non sufficiente per rappresentare il CCNL.

### Distinzione operai / impiegati

La distinzione esiste gia a livello di template orario, non di contratto.

Preset attuali:

- operai `07:00-14:00` con `1°` e `3°` sabato `07:00-13:30`;
- impiegati `07:35-14:00`;
- impiegati con rientro `07:35-14:00` + `14:30-17:45` il lunedi;
- operai `06:20-13:56`.

Riferimenti:

- [backend/app/modules/presenze/router.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/presenze/router.py:159)
- [frontend/src/app/presenze/configurazione/page.tsx](/home/cbo/CursorProjects/GAIA/frontend/src/app/presenze/configurazione/page.tsx:56)

Limite:

- il "tipo di contratto" non e un dato esplicito del collaboratore;
- oggi e solo un proxy derivato dal template orario prevalente.

### Frontend - esposizione ore teoriche

Il frontend gia mostra il dato giornaliero di ore teoriche.

Riferimenti:

- [frontend/src/app/presenze/collaboratori/[id]/page.tsx](/home/cbo/CursorProjects/GAIA/frontend/src/app/presenze/collaboratori/[id]/page.tsx:550)
- [frontend/src/app/me/page.tsx](/home/cbo/CursorProjects/GAIA/frontend/src/app/me/page.tsx:1287)

Limite:

- il FE non riceve un campo strutturato come `standard_daily_minutes`;
- il FE non riceve un campo strutturato come `employee_contract_kind`;
- non esiste un breakdown esplicito delle maggiorazioni CCNL.

## Gap funzionali rispetto al CCNL

Oggi GAIA non implementa ancora:

1. calcolo autonomo di `notturno` (`22:00-06:00`);
2. distinzione tra:
   - `straordinario_diurno`
   - `straordinario_notturno`
   - `straordinario_festivo`
   - `straordinario_festivo_notturno`;
3. distinzione tra:
   - `ordinario_notturno`
   - `turno_festivo_diurno`
   - `turno_feriale_notturno`
   - `turno_festivo_notturno`;
4. soglia Art. 82 sulle `20 notti nel mese`;
5. separazione tra dato importato da INAZ e dato ricalcolato da GAIA a fini contrattuali;
6. profilo contrattuale esplicito del collaboratore.

## Proposta di modello dati

### Nuovi campi su `presenze_daily_records`

Consigliati:

- `contract_kind`: enum logico su collaboratore, non su record
- `standard_daily_minutes`: derivato o materializzato
- `night_minutes`
- `festive_minutes`
- `festive_night_minutes`
- `ordinary_night_minutes`
- `overtime_day_minutes`
- `overtime_night_minutes`
- `overtime_festive_minutes`
- `overtime_festive_night_minutes`
- `shift_festive_day_minutes`
- `shift_night_minutes`
- `shift_festive_night_minutes`

Nota:

- `contract_kind` ha piu senso su `presenze_collaborators` o su una nuova assegnazione contrattuale con validita temporale.
- i minuti di dettaglio possono stare su `presenze_daily_records` come snapshot calcolato, per reporting ed export.

### Nuova entita suggerita

`presenze_collaborator_contract_assignments`

Campi minimi:

- `collaborator_id`
- `contract_kind` (`operaio`, `impiegato`, `quadro`, `altro`)
- `valid_from`
- `valid_to`
- `notes`
- `source` (`manual`, `bootstrap`, `import`, `derived`)

Questo evita di confondere:

- template orario;
- profilo contrattuale;
- regole di maggiorazione.

## Proposta logica di calcolo

### Step 1 - normalizzazione giornata

Input:

- timbrature;
- template orario;
- festivita tipizzata;
- override HR;
- profilo contrattuale.

Output base:

- `scheduled_minutes`
- `worked_minutes`
- `ordinary_minutes`
- `extra_minutes`
- `special_day`

### Step 2 - scomposizione temporale

Per ogni intervallo di timbratura:

- calcolare overlap con finestre ordinarie del template;
- calcolare overlap con fascia notturna `22:00-06:00`;
- calcolare overlap con giorno festivo;
- identificare minuti in contemporanea `festivo` + `notturno`.

### Step 3 - classificazione contrattuale

Separare i minuti in bucket:

- ordinario diurno;
- ordinario notturno;
- turno festivo diurno;
- turno festivo notturno;
- straordinario diurno;
- straordinario notturno;
- straordinario festivo diurno;
- straordinario festivo notturno.

### Step 4 - regole economiche CCNL

Applicare una tabella regole, non hardcodare percentuali sparse.

Esempio tabella:

- `overtime_day` -> `25`
- `overtime_night` -> `50`
- `overtime_festive` -> `50`
- `overtime_festive_night` -> `75`
- `ordinary_night_qualified_worker` -> `15`
- `ordinary_night_non_qualified_worker` -> `10`
- `shift_festive_day` -> `10`
- `shift_night` -> `15`
- `shift_festive_night` -> `20`

### Step 5 - soglia Art. 82

Serve un aggregato mensile per collaboratore:

- contare quante notti nel mese hanno almeno una quota di lavoro notturno ordinario;
- se `>= 20`, applicare `15%`, altrimenti `10%`.

Questo richiede:

- funzione batch di ricalcolo mensile;
- o materializzazione incrementalmente aggiornata.

## Proposta API

### Estensione `PresenzeDailyRecordResponse`

Aggiungere:

- `employee_contract_kind`
- `standard_daily_minutes`
- `scheduled_minutes`
- `night_minutes`
- `festive_minutes`
- `festive_night_minutes`
- `ordinary_night_minutes`
- `overtime_day_minutes`
- `overtime_night_minutes`
- `overtime_festive_minutes`
- `overtime_festive_night_minutes`
- `shift_festive_day_minutes`
- `shift_night_minutes`
- `shift_festive_night_minutes`
- `ccnl_compensation_profile`

### Estensione `PresenzeDashboardSummaryResponse`

Aggiungere aggregati:

- `scheduled_minutes_total`
- `ordinary_night_minutes_total`
- `overtime_day_minutes_total`
- `overtime_night_minutes_total`
- `overtime_festive_minutes_total`
- `overtime_festive_night_minutes_total`
- `shift_festive_day_minutes_total`
- `shift_night_minutes_total`
- `shift_festive_night_minutes_total`

## Proposta Frontend

### Vista giornata / dettaglio collaboratore

Mostrare in modo esplicito:

- `profilo contrattuale`
- `orario teorico standard`
- `ore ordinarie`
- `ore straordinario diurno`
- `ore straordinario notturno`
- `ore straordinario festivo`
- `ore straordinario festivo notturno`
- `ore turno notturno`
- `ore turno festivo`

### Dashboard Presenze

Nuovi KPI suggeriti:

- `Teoriche mese`
- `Notturne ordinarie`
- `Straordinario notturno`
- `Straordinario festivo`
- `Straordinario festivo notturno`

### Export XLSM

Da chiarire prima di implementare:

- il template legacy ha colonne dedicate a queste casistiche?
- oppure il file attuale accetta solo bucket feriale/festivo?

Se il tracciato non le supporta:

- i minuti vanno comunque modellati a DB/API;
- l'XLSM legacy resta una vista ridotta.

## Decisioni aperte

1. GAIA deve ricalcolare la verita contrattuale o solo rappresentare il dato INAZ?
2. Le maggiorazioni contrattuali devono essere:
   - solo informative;
   - oppure operative per export/paghe?
3. Il profilo `operaio/impiegato` va assegnato manualmente o derivato dal template?
4. I casi `sabato programmato`, `rientro impiegati`, `turni`, `reperibilita` devono avere policy dedicate?
5. Serve una tabella configurabile per percentuali/deroghe per consorzio?

## Sequenza consigliata di implementazione

1. Introdurre `contract_kind` e `standard_daily_minutes`.
2. Introdurre il breakdown minuti a livello record.
3. Implementare il calcolo fascia `22:00-06:00`.
4. Separare `turno` da `straordinario`.
5. Introdurre regole Art. 80, 82, 83.
6. Estendere API e FE.
7. Valutare adeguamento export XLSM.

## Conclusione

Il modulo `inaz` oggi e coerente con:

- import dati INAZ;
- classificazione oraria base;
- distinzione feriale/festivo;
- template orari operai/impiegati.

Non e ancora coerente in modo pieno con il CCNL per:

- maggiorazione notturna;
- maggiorazione festiva;
- maggiorazione festiva notturna;
- lavoro ordinario notturno;
- lavoro in turni;
- soglia delle 20 notti mensili;
- profilo contrattuale esplicito.

Il passo corretto non e aggiungere una sola formula, ma introdurre un piccolo sottodominio "compensi orari CCNL INAZ".
