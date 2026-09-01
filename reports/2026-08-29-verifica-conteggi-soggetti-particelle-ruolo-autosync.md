# Verifica dati Soggetti e Particelle a ruolo — Auto Sync

**Data:** 2026-08-29

**Ambiente verificato:** CED `serverCed`, database PostgreSQL `naap`

**Modalità:** sola lettura; nessuna modifica a DB, codice o servizi

## Esito

I valori `168`, `168`, `2160`, `2160` mostrati nella configurazione Auto Sync **non sono conteggi** di particelle o soggetti.

Sono intervalli temporali espressi in ore:

- `role_parcel_refresh_hours = 168` → aggiornamento particelle Ruolo ogni 7 giorni;
- `role_subject_refresh_hours = 168` → aggiornamento soggetti Ruolo ogni 7 giorni;
- `consortium_parcel_refresh_hours = 2160` → aggiornamento particelle consorzio ogni 90 giorni;
- `registry_subject_refresh_hours = 2160` → aggiornamento soggetti anagrafe ogni 90 giorni.

La UI è ambigua perché presenta i campi come:

- `Particelle a ruolo`;
- `Soggetti a ruolo`;
- `Particelle consorzio`;
- `Soggetti anagrafe`;

senza indicare `ore`, `intervallo` o `SLA`.

## Conteggi reali verificati sul CED

### Particelle Ruolo

- righe complessive in `ruolo_particelle`: **1.124.188**;
- target distinti prodotti dal loader Auto Sync: **129.062**;
- righe duplicate/storiche eliminate dalla deduplica: **995.126**.

La deduplica applicativa usa la chiave:

```text
comune normalizzato | foglio | particella | subalterno
```

Le righe sono ordinate per anno tributario e data di creazione decrescenti; per ogni chiave viene conservata la riga più recente.

### Soggetti Ruolo

- righe complessive in `ruolo_avvisi`: **143.580**;
- avvisi con `subject_id`: **143.580**;
- `subject_id` distinti: **12.648**;
- target soggetto distinti prodotti dal loader Auto Sync: **12.648**;
- ripetizioni storiche/annuali eliminate: **130.932**.

L’identificativo operativo viene scelto in questo ordine:

1. codice fiscale persona;
2. codice fiscale azienda;
3. partita IVA azienda;
4. codice fiscale grezzo dell’avviso.

Il valore viene normalizzato in maiuscolo e deduplicato per identificativo.

## Verifica del codice

### Frontend

File:

```text
frontend/src/components/elaborazioni/continuous-catasto-sync-panel.tsx
```

Il mapping è:

```text
"Particelle a ruolo"      -> roleParcelHours
"Soggetti a ruolo"        -> roleSubjectHours
"Particelle consorzio"    -> consortiumParcelHours
"Soggetti anagrafe"       -> registrySubjectHours
```

Il draft legge i corrispondenti campi API:

```text
role_parcel_refresh_hours
role_subject_refresh_hours
consortium_parcel_refresh_hours
registry_subject_refresh_hours
```

Quindi il dato è tecnicamente corretto, ma l’etichetta è semanticamente fuorviante.

### Backend

File sorgente:

```text
backend/app/services/elaborazioni_perpetual_sources.py
```

Funzioni verificate:

```text
load_ruolo_parcel_targets
load_ruolo_subject_targets
```

File status:

```text
backend/app/services/elaborazioni_ruolo_autosync.py
backend/app/services/elaborazioni_perpetual_sync.py
```

I conteggi reali della coda sono restituiti separatamente in:

```text
scope_counts
```

attraverso `perpetual_sync_counts`, raggruppati per `scope` e `status`.

## Stato Auto Sync corrente sul CED

La configurazione principale verificata contiene:

- priorità Ruolo: abilitata;
- priorità consorzio/anagrafe: abilitata;
- pool credenziali configurato: 9 elementi;
- intervalli: `168 / 168 / 2160 / 2160` ore;
- `source_watermarks`: assente;
- elementi in `catasto_perpetual_sync_items`: **0** per tutti gli scope.

Questo significa che i target reali non risultano attualmente materializzati nella coda perpetua. Di conseguenza, le card `scope_counts` non possono ancora mostrare i totali **129.062** e **12.648**.

## Causa dell’equivoco

1. Il frontend omette l’unità di misura `ore`.
2. Le etichette descrivono l’entità, non l’intervallo di aggiornamento.
3. I conteggi effettivi sono visualizzati in una sezione separata (`ScopeCoverage`).
4. Sul CED la coda perpetua è attualmente vuota, quindi quella sezione non contiene ancora i target reali.

## Correzione UI applicata

Il `2026-08-30` è stato aggiornato esclusivamente il pannello Auto Sync:

- titolo esplicito `Intervalli di aggiornamento`;
- testo di chiarimento: `Questi valori indicano la frequenza del nuovo controllo, non il numero di particelle o soggetti.`;
- campi rinominati:
  - `Aggiorna particelle Ruolo ogni (ore)`;
  - `Aggiorna soggetti Ruolo ogni (ore)`;
  - `Aggiorna particelle consorzio ogni (ore)`;
  - `Aggiorna soggetti anagrafe ogni (ore)`;
- conversione automatica leggibile, per esempio:
  - `168 ore · 7 giorni`;
  - `2160 ore · 90 giorni`;
- `Righe per micro-batch` mantenuto separato con il chiarimento che rappresenta la quantità massima del singolo micro-batch;
- associazioni accessibili esplicite tramite `label/htmlFor`, `input/id` e `aria-describedby`;
- layout a una colonna su mobile e due colonne da breakpoint `sm`.

File runtime modificato:

```text
frontend/src/components/elaborazioni/continuous-catasto-sync-panel.tsx
```

Test regressivo aggiornato:

```text
frontend/tests/unit/elaborazioni-request-workspace-continuous-sync.test.tsx
```

## Verifiche della correzione

- TDD RED: il nuovo test falliva perché `Intervalli di aggiornamento` non era presente.
- Test mirati finali: **12/12 PASS**.
- Coverage del file runtime:
  - statements: **127/127 — 100%**;
  - branches: **126/126 — 100%**;
  - functions: **54/54 — 100%**;
  - lines: **89/89 — 100%**.
- Suite frontend completa: **184/184 file e 1.659/1.659 test PASS**.
- Typecheck TypeScript: **PASS**.
- Build Next.js production: **PASS**, `154/154` pagine generate.
- Test harness Quality Code: **46/46 PASS**.
- Complexity ratchet sul file modificato:
  - primo assetto: correttamente bloccato, `SyncConfiguration` cyclomatic `16` con soglia errore `15`;
  - assetto finale dopo estrazione dei blocchi UI: **PASS, `findings: []`**.
- `git diff --check`: **PASS**.

## Deploy CED

Deploy chirurgico del solo file frontend, senza modifiche al backend o al database.

- Backup rollback:

```text
/opt/gaia/backups/hotfixes/20260830-002836-autosync-sla-ui/continuous-catasto-sync-panel.tsx
```

- Checksum precedente/backup:

```text
f9c0b5fd8e86db458bc2b330d0b8e7861d585b3c2a53da9325796c7b18622f94
```

- Checksum testato e distribuito:

```text
051f7ede8024dd09e5f8b6bf98c0d1be64fe3cbb5e9c7e9bdb7c9fc9776c5323
```

- servizio riavviato: soltanto `gaia-frontend`;
- stato finale container: **healthy**;
- `/elaborazioni`: **HTTP 200**;
- compilazione live di `/elaborazioni`: **PASS**;
- verifica sorgente live:
  - titolo intervalli presente;
  - quattro etichette `ogni (ore)` presenti;
  - avviso “non il numero di particelle o soggetti” presente.

## Conclusione

- `168` e `2160` sono **ore**, non quantità.
- I conteggi reali verificati restano **129.062 particelle Ruolo distinte** e **12.648 soggetti Ruolo distinti**.
- L’ambiguità della UI è stata corretta, testata e distribuita sul CED.
- La coda perpetua non è stata materializzata automaticamente: i circa **141.710 target Ruolo** non sono stati inseriti né inviati ai worker SISTER durante questo intervento.
- Nessun commit, push, pull request o merge è stato eseguito.
