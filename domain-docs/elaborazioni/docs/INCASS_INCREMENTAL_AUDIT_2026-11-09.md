# Audit iniziale: snapshot incrementali inCASS

Rilevazione locale 2026-11-09, prima dell'implementazione.
HEAD `2115dd7bb74384c7dc3b843450bd73fd76b8405f`, branch
`feature/avvisi-solleciti-2021`, merge-base origin/main `686e529e`.
Working tree ampiamente sporco (Presenze, comunicazioni, Poste, documentazione):
queste modifiche non appartengono al presente intervento e non vanno incluse nei commit.

## Flusso verificato nel codice

- `ruoli_export_runner` polla ogni 300 s, slot domenica 07 Europe/Rome;
  `--once` bypassa il flag. Stato JSON per gruppo, replace atomico ma senza
  lock interprocesso. Retry parziali dopo un'ora; gli item uploaded/empty
  non vengono riesportati nello slot. Il cambio di cron da solo non basta.
- `SnapshotRun` trova il nome su Drive prima dell'upload: evita duplicati nel
  retry seriale, ma non certifica il contenuto e non protegge due worker.
  Manifest riscrivibile, senza SHA o schema. Drive precede il login al portale;
  indisponibilità Drive blocca la raccolta. Empty non viene archiviato.
- Sessione per gruppo, `pick_credential` applica stato/fascia credenziale;
  retry esponenziale su rete, 408/429/5xx e sessione persa. Il transport polite
  ha limite e backoff persistenti; gli export usano un file di policy distinto
  dal runtime. Non esiste un lease condiviso di credenziale fra tutti i worker.
- Ricerca avvisi: export XLSX server-side per tutti i codici del filtro anno,
  inclusi codici speciali (esempio storico 9926). Minuta: stored procedure per
  venti annualità ordinarie, polling e fallback server quando `__TotRighe`
  segnala troncamento. Registro Bollettini: altra app, tutti gli esercizi,
  JSON di griglia. Non sono fonti intercambiabili. Costo attuale: ricerca
  almeno POST+GET per anno, Minuta molte richieste/poll; nessuna misura live
  nuova. Il dato 12.353 del 30 ottobre resta storico.
- Autosync: finestra configurabile, selezione Ruolo per soggetti stale;
  controlla job attivi e credenziali, chunk per soggetto, evita soggetti già
  accodati. `run_incass_sync_job` ricerca tutti gli avvisi del soggetto,
  committa progresso per soggetto e riprende i successi dopo riavvio.
  Unicità avviso DB: `(source_system, source_notice_id)`, senza anno/lista.
- `_upsert_payment_notice` aggiorna importi, date, stato, lista e recapito,
  materializza testata canonica; `preserve_heavy_fields=True` conserva dettaglio,
  PDF e partitario. Il recovery Ruolo riusa il materializzatore di partite e
  particelle, senza cancellare particelle per assenza dall'Excel.
- Identità: `audit_recovery_subjects` valida identità fiscali e ownership
  univoca; `assert_notice_owner` impedisce riassegnazioni silenziose.

## Evidenza XLSX e limiti

Ricerca mirata dei file versionati e di runtime-data/reports: nessun export
`incass_ricerca_avvisi_*.xlsx` o `incass_avvisi_minuta_*.xlsx` trovato.
Sono presenti workbook di altri processi, non prove dello schema inCASS.
Non sono stati interrogati Drive, Capacitas o il CED. Intestazioni effettive,
tipi Excel, copertura e costo corrente richiedono verifica live successiva.
I test useranno fixture con alias del modello corrente (Avviso, Anno, CodFisc,
Carico, ecc.), numeri/date/stringhe e dati fiscali sintetici. Questo non prova
la compatibilità del formato live: colonne mancanti/inattese devono bloccare.

## Rischi e piano conservativo

1. Ciclo giornaliero autonomo, flag off predefinito; nessuna modifica al
   runner settimanale o all'autosync. Solo Ricerca avvisi alimenta il diff;
   Minuta e Bollettini mantengono il flusso storico, evitando doppia SP giornaliera.
2. PostgreSQL per snapshot, firme, puntatore e outbox: diff+puntatore atomici;
   XLSX originali content-addressed su volume persistente e Drive, senza round
   trip. Lease PostgreSQL fra istanze incrementali e credenziale dedicata
   obbligatoria; non dichiarare serializzazione con worker legacy non cooperanti.
3. Chiave Avviso coerente col vincolo DB; anno e lista sono attributi. Duplicati,
   alias numerici irreversibili, schema drift, conteggi incoerenti, vuoti anomali
   e sparizioni oltre soglia impediscono promozione. Missing non cancella nulla.
4. Baseline iniziale senza job. Shadow persiste soltanto storage del diff e
   osservazioni; active opt-in, mai abilitato nel presente lavoro. Ownership
   certa e controllo di drift prima di scrivere; recovery pesante per avviso,
   preservando payload non recuperati e riusando riconciliazione canonica.
5. Audit periodico e campioni configurabili necessari per active: l'Excel non
   certifica l'immutabilità del partitario, incluse variazioni da riordino.
   Fallback conservativo: autosync esistente resta attivo; anomalie in outbox
   senza espansione automatica in scansioni massive.

## Test richiesti

Normalizzazione semantica e ordine/metadati; pagamenti/sgravi/annullamenti;
liste/anni speciali/identità mutate/duplicati; snapshot parziali e vuoti;
crash tra upload e commit, replay/outbox e dead-letter; off/shadow senza
dispatch; active sintetico senza HTTP pesante; partitario mancante;
fake HTTP/Drive, finestre e lease concorrenti; regressioni export/autosync,
coverage completa dei runtime nuovi, Ruff, ratchet e aggiornamento Graphify.
