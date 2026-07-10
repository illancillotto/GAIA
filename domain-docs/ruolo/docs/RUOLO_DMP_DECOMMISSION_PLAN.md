# Ruolo Legacy DMP — Piano Di Dismissione DB

> Stato documento: archivio storico.
> Il flusso file-based `.dmp/.pdf` e stato rimosso dal runtime GAIA.
> Usare questo file solo come audit della dismissione; per il comportamento attuale fare riferimento al PRD Ruolo e al workflow `inCASS`.

## Obiettivo

Dismettere in modo sicuro il percorso legacy basato su file `.dmp/.pdf` e rendere `ana_payment_notices` + partitario `inCASS` la fonte primaria del ruolo, senza perdere:

- storico annuale
- collegamenti soggetto
- collegamenti catasto
- viste operative del modulo `Ruolo`

## Stato attuale

Verifica locale al `2026-06-16`:

- `ruolo_import_jobs`: `14`
- `ruolo_avvisi`: `76.106`
- `ruolo_partite`: `101.313`
- `ruolo_particelle`: `478.522`
- `ana_payment_notices`: `144.238`
- `ana_payment_notices` `2025` da `inCASS`: `12.348`

Legacy 2025 ancora presente in `ruolo_import_jobs`:

- `R2025.14215.00001.dmp`
- `R2025.14215.00002.dmp`
- `R2025.14215.NOCF.dmp`
- `R2025.14215.NOIND.dmp`

## Decisione già applicata

Già fatto a codice:

- upload `.dmp/.pdf` dismesso
- `controlli-capacitas` spostato su `ana_payment_notices`
- UI Ruolo riallineata al workflow `Elaborazioni > Capacitas > inCASS`

Non ancora fatto a DB:

- le tabelle `ruolo_*` esistono ancora
- molte query applicative leggono ancora `RuoloAvviso`, `RuoloPartita`, `RuoloParticella`
- il legacy non è eliminabile subito senza rompere il modulo

## Dipendenze residue principali

Perimetri che leggono ancora `ruolo_*`:

- modulo `Ruolo`: avvisi, stats, particelle storiche
- modulo `Catasto`: particelle a ruolo, match AdE, preview GIS
- modulo `Utenze/ANPR`: code e subset “soggetti a ruolo”
- modulo `Wiki`: viste soggetto con storico ruolo
- script tecnici: backfill, repair, compare, materialize

Conclusione:

- `ruolo_avvisi` non va droppata per prima
- il primo candidato a sostituzione è la fonte dei totali ruolo
- il dataset storico `ruolo_particelle` va probabilmente mantenuto più a lungo, ma va rimaterializzato da `inCASS`

## Strategia target

### Modello sorgente canonico

Fonte primaria:

- `ana_payment_notices`
  - testata avviso
  - link Capacitas
  - dettagli HTML
  - `raw_detail_json.partitario`

### Modello storico derivato

Mantenere un dataset materializzato lato GAIA per le viste storiche:

- `ruolo_avvisi`
- `ruolo_partite`
- `ruolo_particelle`

ma con nuova semantica:

- non più “importati da DMP”
- bensì “materializzati da `inCASS`”

Questo evita di riscrivere in un colpo tutte le query `Catasto/GIS/AdE`.

## Piano operativo

### Fase 1. Freeze del legacy

Obiettivo:

- bloccare definitivamente nuovi ingressi `.dmp`

Stato:

- completata

Criterio di uscita:

- `POST /ruolo/import/upload` e `POST /ruolo/import/detect-year` non sono più esposti dal router pubblico

### Fase 2. Spostare i confronti economici su `inCASS`

Obiettivo:

- far sparire `RuoloAvviso` dai confronti importi/Capacitas

Stato:

- completata per `/ruolo/controlli-capacitas`

Criterio di uscita:

- i totali `0648/0985` arrivano da `ana_payment_notices.raw_detail_json.partitario`

### Fase 3. Materializzazione canonica da `inCASS`

Obiettivo:

- rigenerare `ruolo_avvisi`, `ruolo_partite`, `ruolo_particelle` a partire da `ana_payment_notices`

Strumento già presente:

- [materialize_ruolo_from_incass.py](/home/cbo/CursorProjects/GAIA/backend/scripts/materialize_ruolo_from_incass.py)

Azioni:

1. rieseguire la materializzazione per gli anni attivi
2. marcare i job come `source=ana_payment_notices`
3. distinguere chiaramente i record legacy `.dmp` dai record materializzati

Runbook operativo minimo per il `2025`:

1. dry run di stima
   - `docker compose exec -T backend python scripts/materialize_ruolo_from_incass.py --from-year 2025 --to-year 2025 --replace-year --reparse-partitario --max-notices 200`
2. purge/rebuild controllato in finestra manutentiva
   - locale: `docker compose exec -T backend python scripts/materialize_ruolo_from_incass.py --from-year 2025 --to-year 2025 --replace-year --reparse-partitario --apply --commit-every 1`
   - server: fermare `backend`, `elaborazioni-worker-*` e `presenze-worker`, poi usare `docker compose run --rm --no-deps backend python scripts/materialize_ruolo_from_incass.py --from-year 2025 --to-year 2025 --replace-year --reparse-partitario --apply --commit-every 1 --purge-batch-size 2000`
4. verifica finale
   - `docker compose exec -T backend python scripts/report_ruolo_legacy_state.py`
   - query superfici 2025: `over_1000=0`, `eq_are=0`, `max_irr=49.7000`

Note operative:

- `--purge-only` e `--rebuild-only` servono a separare la fase distruttiva da quella ricostruttiva
- il `2025` legacy da `.dmp` contiene circa `106k` record `ruolo_particelle`, quindi il purge reale va trattato come operazione pesante
- la materializzazione stampa avanzamento ogni `commit_every` notices per rendere il run osservabile

Criterio di uscita:

- per ogni anno target, il dataset `ruolo_*` deriva solo da `inCASS`

### Fase 4. Sostituire le dipendenze residue su `RuoloAvviso`

Obiettivo:

- eliminare l’uso di `RuoloAvviso` come fonte primaria “viva”

Ordine consigliato:

1. `Utenze/ANPR`
2. `Wiki`
3. `Ruolo stats`
4. `Catasto/GIS`

Nota:

- per `Catasto/GIS` non conviene saltare subito a `ana_payment_notices` puro
- conviene continuare a leggere `ruolo_particelle`, ma rigenerata da `inCASS`

Criterio di uscita:

- nessuna logica business usa più record `.dmp` come fonte autorevole

### Fase 5. Pulizia dei dati legacy `.dmp`

Obiettivo:

- rimuovere solo i record materialmente derivati da dump incompleto

Azioni:

1. identificare i `ruolo_import_jobs` legacy da filename `.dmp/.pdf`
2. cancellare a cascata solo i dati collegati a quei job
3. mantenere i record materializzati da `inCASS`

Prerequisito:

- Fase 3 conclusa

Rischio principale:

- cancellare prima della rimaterializzazione rompe:
  - viste `Ruolo`
  - `Catasto`
  - `ANPR`

### Fase 6. Dismissione schema legacy

Obiettivo:

- valutare se tenere o eliminare `ruolo_import_jobs`

Opzioni:

- `A`: mantenere `ruolo_avvisi/partite/particelle` come schema storico materializzato e rimuovere solo la semantica “import job file”
- `B`: progettare un nuovo schema `ruolo_materialized_*` e migrare tutte le query

Raccomandazione:

- scegliere `A` nel breve periodo
- è molto meno rischiosa e riusa l’ecosistema `Catasto/GIS` esistente

## Query di verifica prima del drop

### 1. Verifica copertura soggetti 2025

```sql
with ruolo as (
  select distinct subject_id
  from ruolo_avvisi
  where anno_tributario = 2025 and subject_id is not null
),
notices as (
  select distinct subject_id
  from ana_payment_notices
  where anno = '2025' and source_system = 'incass' and subject_id is not null
)
select
  (select count(*) from ruolo) as ruolo_subjects,
  (select count(*) from notices) as incass_subjects,
  (select count(*) from ruolo r join notices n using (subject_id)) as overlap_subjects;
```

### 2. Verifica presenza partitario

```sql
select
  count(*) as notices_2025,
  count(*) filter (where raw_detail_json is not null) as notices_con_detail,
  count(*) filter (
    where raw_detail_json is not null
      and (raw_detail_json::jsonb ? 'partitario')
  ) as notices_con_partitario
from ana_payment_notices
where anno = '2025' and source_system = 'incass';
```

### 3. Verifica residuo legacy `.dmp`

```sql
select id, anno_tributario, filename, status, records_imported, created_at
from ruolo_import_jobs
where filename ilike '%.dmp' or filename ilike '%.pdf'
order by anno_tributario desc, created_at desc;
```

## Script di audit

Per il check rapido usare:

- [report_ruolo_legacy_state.py](/home/cbo/CursorProjects/GAIA/backend/scripts/report_ruolo_legacy_state.py)

Comando:

```bash
docker compose exec -T backend python scripts/report_ruolo_legacy_state.py
```

## Raccomandazione finale

Non fare `DROP TABLE ruolo_*` nel prossimo step.

Il prossimo step corretto lato DB è:

1. rimaterializzare `ruolo_*` da `ana_payment_notices`
2. taggare e isolare i record `.dmp`
3. cancellare solo il contenuto legacy
4. solo dopo valutare se lo schema `ruolo_*` serve ancora come read-model storico
