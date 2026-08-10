# GAIA Ruolo — Progress Tracking v1.0

> Stato documento: archivio storico di delivery.
> Traccia milestone e test anche del vecchio import file-based, oggi rimosso dal runtime.
> Per lo stato corrente del dominio fare riferimento al codice attivo e al PRD Ruolo aggiornato.

## Stato generale

- Modulo: Ruolo
- Stato complessivo: **documento archiviato; implementazione storica completata M1–M5**
- Owner: TBD
- Ultimo aggiornamento: 2026-08-10

---

## Milestone

| Milestone | Stato | Note |
|-----------|-------|------|
| M0 Analisi e design | ✅ done | PRD v1, Execution Plan v1, Prompt Codex prodotti |
| M1 Fondazione backend | ✅ done | Migration, modelli, enums, parser (23 test), import service |
| M2 API e query layer | ✅ done | Repository, schemas, route import + query, router.py |
| M3 Bootstrap e integrazione | ✅ done | Section keys, flag module_ruolo, router registrato in api/router.py |
| M4 Frontend | ✅ done | Dashboard, avvisi, dettaglio, stats, import, widget soggetto |
| M5 Hardening | ✅ completo | Permessi require_module attivi; test API, parser/import realistici e catasto parcels coperti |

---

## Aggiornamenti recenti

### 2026-08-10
- Migliorata la resa mobile della lista `/ruolo/tributi`: i pulsanti `Dettaglio`, `Dettaglio soggetto` e `Avviso sollecito` restano allineati sulla stessa riga nella card.
- Ridotto lo zoom della preview PDF degli avvisi sollecito nelle viewport mobili sotto `640px`, mantenendo invariata la resa desktop.
- Validata la change con coverage `100%` su `frontend/src/app/ruolo/tributi/page.tsx` tramite `frontend/tests/unit/ruolo-tributi-page.test.tsx`.

### 2026-08-07
- Corretto il riferimento visibile del bollettino TD 896 nei solleciti tributi: ora coincide con il `notice_number` GAIA, senza prefissi, padding o controcodici aggiuntivi.
- Il padding a lunghezza pari resta limitato al payload barcode Code 128-C quando necessario e non viene mostrato all'utente come numero di riferimento.
- Documentata la derivazione del campo `Esercizio`: per avvisi multi-annualita usa l'anno piu alto del payload e duplica il suffisso a due cifre, per esempio `2025 -> 2525`.
- Validata la change con coverage `100%` su `backend/app/modules/ruolo/services/tributi_reminder_service.py`.

### 2026-08-06
- Estesa la logica interessi delle `Regole ruolo`: il tasso effettivo usato dal saldo e `Euribor medio 6 mesi + tasso da delibera`.
- Aggiunto recupero automatico Euribor 6M dal Data Portal BCE per anno policy, con salvataggio di valore, periodo, URL sorgente e timestamp di recupero.
- La modal `Regole ruolo` espone i campi separati `% Euribor medio 6 mesi` e `% tasso da delibera`, il pulsante `Recupera da BCE` e il link di verifica del dato BCE.
- Aggiunta migration `20260730_1100_ruolo_tributi_euribor_interest_rate` e servizio backend `app.modules.ruolo.services.euribor`.
- Validata la change con test mirati backend/frontend e coverage `100%` sui file runtime modificati.

### 2026-08-05
- Implementata la logica operativa `Regole ruolo` per solleciti multi-annualita: un range come `2024-2025` viene salvato come policy annuali distinte per supportare scadenza bonaria e fallback interessi diversi per ruolo.
- Le policy annuali generate dallo stesso nome base vengono raggruppate in preview: cliccando `Avviso sollecito` sul 2024 o sul 2025, il backend espande il gruppo e produce un solo avviso con entrambe le annualita.
- La preview rapida riusa il `notice_number` quando CF/P.IVA, annualita e avvisi inclusi coincidono, evitando numeri diversi per lo stesso avviso logico.
- Gli avvisi con importi effettivi da inCASS rateizzazione/residuo mantengono `calculation_policy_id` e `calculation_policy_name`, quindi restano sollecitabili quando coperti da Regola ruolo attiva.
- Documentazione operativa aggiunta in `domain-docs/ruolo/docs/RUOLO_TRIBUTI_REGOLE_RUOLO_SOLLECITI_2026-08-05.md`.
- Validata la change con coverage mirata al `100%` su `backend/app/modules/ruolo/tributi_repositories.py`, `backend/app/modules/ruolo/services/tributi_reminder_service.py` e `frontend/src/app/ruolo/tributi/page.tsx`.

### 2026-08-04
- Corretto il collo di bottiglia backend della lista `/ruolo/tributi` quando `Solo scoperti` (`open_only=true`) o i filtri `payment_status` richiedevano il calcolo dello stato effettivo: il repository non materializza piu il dettaglio completo su tutto il dataset filtrato prima della paginazione.
- `GET /ruolo/tributi/avvisi` pre-carica ora in batch notice inCASS, date notifica PEC/raccomandata e policy per annualita, applica i filtri effettivi sul perimetro bulk e costruisce `_row_to_tributi_item` solo per le righe della pagina corrente.
- `GET /ruolo/tributi/summary` riusa lo stesso precompute bulk per evitare full-scan N+1 sul read-model operativo e ridurre il rischio di `Gateway Time-out` sul perimetro GAIA dal 2022 in poi.
- Aggiunta regressione backend dedicata per verificare che con `open_only=true` la pagina costruisca item solo per il `page_size` richiesto.
- Validata la change con `pytest tests/ruolo/test_tributi_api.py --cov=app.modules.ruolo.tributi_repositories --cov-report=term-missing --cov-fail-under=100 -q`, coverage `100%` su `backend/app/modules/ruolo/tributi_repositories.py`.

### 2026-08-03
- Corretto `/ruolo/tributi` nella sezione `Avvisi e saldo pagamento`: il pulsante `Avviso sollecito` viene esposto solo per le annualita con sollecito GAIA attivo (`reminder_enabled=true`).
- La preview rapida da riga usa esclusivamente l'`anno_tributario` dell'avviso cliccato, senza riusare il range default del wizard batch.
- Corretto il calcolo degli avvisi inCASS non rateizzati: `importo_residuo` ora guida saldo e stato pagamento anche quando `importo_rateizzato=0`, riallineando `Pagato`, `Parzialmente pagato` e `Non pagato` alla posizione CapaciTas.
- Validata la change con coverage mirata al `100%` su `backend/app/modules/ruolo/tributi_repositories.py`, `backend/app/modules/ruolo/routes/tributi_routes.py` e `frontend/src/app/ruolo/tributi/page.tsx`.

### 2026-07-30
- In `/ruolo/tributi` le `Regole ruolo` e i `Gestori annualita tributo` restano visibili agli utenti con accesso di consultazione, evitando errori operativi su sola lettura.
- Le azioni di gestione delle regole (`Gestisci regole`, `Gestisci regole calcolo` e relative modali CRUD) sono disabilitate per utenti non `admin`/`super_admin`; il fallback in caso di sessione non verificabile resta read-only.
- Validata la change frontend con test unitari dedicati e coverage mirata al `100%` su `frontend/src/app/ruolo/tributi/page.tsx`.

## Checklist tecnica

### M0 — Analisi
- [x] PRD v1 prodotto
- [x] Execution Plan v1 prodotto
- [x] Prompt Codex prodotto
- [x] Formato file `.dmp` analizzato (sample 2 partite)
- [x] Modello dati definito (4 tabelle `ruolo_*` + `catasto_parcels`)
- [x] Logica temporale particelle definita (`valid_from`/`valid_to`)
- [x] Pattern job asincrono definito (su modello `wc_sync_job`)
- [x] Integrazione con `ana_subjects` via CF/PIVA definita
- [x] Unità SUP.CATA. verificata con dominio — **are** (1 ara = 100 mq)
- [x] Dipendenza `pypdf==5.4.0` aggiunta in requirements

### M1 — Fondazione backend
- [x] Migration Alembic creata e applicata (`20260416_0048_add_ruolo_module.py`)
  - [x] `ruolo_import_jobs`
  - [x] `ruolo_avvisi`
  - [x] `ruolo_partite`
  - [x] `ruolo_particelle`
  - [x] `catasto_parcels`
- [x] Modelli ORM in `backend/app/modules/ruolo/models.py`
- [x] Modello `CatastoParcel` aggiunto in `backend/app/models/catasto.py`
- [x] Enumerazioni in `ruolo/enums.py`
- [x] Parser `ruolo/services/parser.py`
  - [x] Split partite per marcatore `<inizio>` / `<-fine->`
  - [x] Estrazione codice CNC
  - [x] Parse riga N2 (CF/PIVA + extra)
  - [x] Parse nominativo, domicilio, residenza
  - [x] Parse partite catastali (codice, comune, tributi)
  - [x] Parse co-intestati (opzionale)
  - [x] Parse righe particelle positional (con gestione subalterni letterali)
  - [x] Parse righe N4 (totali + codice utenza)
  - [x] Fault-tolerance: errore per-partita senza interruzione
- [x] Test unitari parser — **23 test, tutti passanti** (`backend/tests/ruolo/test_parser.py`)
- [x] Import service `ruolo/services/import_service.py`
  - [x] Background task con sessione DB indipendente
  - [x] Estrazione testo da PDF (+ fallback `.dmp` grezzo)
  - [x] Loop import con contatori
  - [x] Upsert avvisi idempotente
  - [x] Risoluzione soggetto via CF/PIVA
  - [x] Upsert `catasto_parcels` con logica temporale
  - [x] Gestione `SubjectNotFound` → skipped
  - [x] Finalizzazione job (status, contatori, error_detail, finished_at)

### M2 — API e query layer
- [x] Schemas Pydantic in `ruolo/schemas.py`
- [x] Repository in `ruolo/repositories.py`
- [x] `ruolo/routes/import_routes.py`
  - [x] `GET /ruolo/import/jobs`
  - [x] `GET /ruolo/import/jobs/{job_id}`
- [x] `ruolo/routes/query_routes.py`
  - [x] `GET /ruolo/avvisi`
  - [x] `GET /ruolo/avvisi/export` (CSV)
  - [x] `GET /ruolo/avvisi/{avviso_id}`
  - [x] `GET /ruolo/soggetti/{subject_id}/avvisi`
  - [x] `GET /ruolo/soggetti/{subject_id}/terreni-colture` — riepilogo read-only terreni/colture a ruolo con GeoJSON opzionale on-demand
  - [x] `GET /ruolo/particelle`
  - [x] `GET /ruolo/stats`
  - [x] `GET /ruolo/stats/comuni`
  - [x] `GET /catasto/parcels`
  - [x] `GET /catasto/parcels/{parcel_id}/history`
- [x] `ruolo/router.py` — aggregazione router con prefisso `/ruolo`

### M3 — Bootstrap e integrazione
- [x] `ruolo/bootstrap.py` con 4 section keys
- [x] Flag `module_ruolo` su `ApplicationUser` (ORM + enabled_modules)
- [x] `CurrentUser` e `ApplicationUser` TypeScript aggiornati con `module_ruolo`
- [x] `backend/app/scripts/bootstrap_sections.py` aggiornato
- [x] Router registrato in `backend/app/api/router.py`
- [x] Navigazione frontend aggiornata (platform-sidebar, module-sidebar, sidebar)
- [x] Integrazione scheda soggetto anagrafica
  - [x] Endpoint `GET /ruolo/soggetti/{subject_id}/avvisi` accessibile
  - [x] Componente `RuoloAvvisiSection` nella pagina soggetti utenze
  - [x] Link da avviso → dettaglio funzionante

### M4 — Frontend
- [x] `frontend/src/types/ruolo.ts`
- [x] `frontend/src/lib/ruolo-api.ts`
- [x] `frontend/src/components/ruolo/module-page.tsx`
- [x] Layout modulo `frontend/src/app/ruolo/layout.tsx`
- [x] `/ruolo` — dashboard con stats per anno + ultimi job
- [x] `/ruolo` — CTA stato vuoto apre import in modale con fallback `Apri pagina`
- [x] `/ruolo` — dashboard riallineata al pattern UI/UX dei moduli maturi (hero workspace, KPI, action cards, pannelli)
- [x] `/ruolo/import` — upload + lista job + polling automatico, riallineata al pattern UI/UX dei moduli maturi
- [x] `/ruolo/avvisi` — lista con filtri URL-driven + paginazione, riallineata al pattern UI/UX dei moduli maturi
- [x] `/ruolo/avvisi` — ricerca unificata live (`q`) con debounce, soglia minima 3 caratteri, toggle `Solo avvisi non collegati` inline e dettaglio avviso in modale embedded
- [x] `/ruolo/avvisi/[id]` — dettaglio completo con partite espandibili, riallineato al pattern UI/UX dei moduli maturi
- [x] `/ruolo/particelle` — vista dedicata al dataset storico `ruolo_particelle`, con filtri ruolo, stato di collegamento a `cat_particelle` e classificazione AdE
- [x] `/ruolo/stats` — statistiche per anno e per comune interattive, riallineate al pattern UI/UX dei moduli maturi
- [x] `/ruolo` — controllo economico `ruolo vs Capacitas` con KPI, mismatch per CF/P.IVA, breakdown per comune ed export CSV
- [x] `/ruolo/controlli-capacitas` — console dedicata di supervisione con drilldown verso avvisi per `codice_fiscale` e `comune`
- [x] Integrazione scheda soggetto `RuoloAvvisiSection`, riallineata al pattern UI/UX del modulo con hero compatta, mini-stat e CTA coerenti
- [x] Nessun errore lint (`ReadLints` verde)

### M5 — Hardening
- [x] `backend/tests/ruolo/test_parser.py` — **23 test passanti**
- [x] Permessi `require_module("ruolo")` applicati su tutti gli endpoint
- [x] Fix permessi admin esistenti: migration di backfill `module_ruolo` per account `admin` / `super_admin` creati prima del modulo
- [x] Export CSV `GET /ruolo/avvisi/export` implementato
- [x] Compatibilità Pydantic v2/UUID sugli endpoint `GET /ruolo/import/jobs`, `GET /ruolo/import/jobs/{job_id}` e sui response model `ruolo/schemas.py`
  - Fixato il mismatch tra UUID ORM nativi e campi `str` nei model di risposta, mantenendo serializzazione JSON string verso il frontend
  - Aggiunto test API dedicato `backend/tests/ruolo/test_api.py`
- [x] Allineamento parser/import ai file DMP reali 2025 di Capacitàs
  - Lo split delle `Partita CNC` ora supporta sia il primo header con prefisso `<qm500>--` sia i blocchi successivi con header `---------Partita CNC ...`
  - Normalizzato `catasto_comuni.codice_sister` composito (es. `F272#MOGORO#0#0`) al codice catastale corto usabile in `catasto_parcels.comune_codice`
  - Normalizzati i comuni di partita catastale da DMP: rimozione quote tra parentesi e alias storici (`SILI'*ORISTANO`, `OLLASTRA SIMAXIS`, `SAN NICOLO ARCIDANO`)
  - Hardening del parser particelle: le righe legenda/header (`DOM.=DOMANDA IRRIGUA`, `FOG.=FOGLIO CATASTALE`, `CONSUMI DA CONTATORE`, separatori) non possono alimentare `catasto_parcels`
  - Risoluzione comune solo con match esatto case-insensitive; eliminato il fallback parziale `ILIKE '%nome%'` per evitare casi come `ARBOREA` risolto in `PALMAS ARBOREA`
  - Fallback risoluzione codice comune da `cat_particelle` quando `catasto_comuni` non contiene il comune ma la particella GAIA esiste in modo univoco
  - Aggiunti test `backend/tests/ruolo/test_parser.py` e `backend/tests/ruolo/test_import_helpers.py`
- [x] Report job Ruolo persistito e consultabile da UI
  - `params_json` del job contiene `report_summary` e `report_preview` con motivazioni dei casi `skipped` / `error`
  - In `/ruolo/import` ogni card job espone una modale “Apri report” con riepilogo e dettaglio operativo
  - Semantica esplicitata: `records_skipped` = avvisi importati ma non collegati a un soggetto in Anagrafica
- [x] Collegamento risolto `ruolo_particelle -> cat_particelle`
  - Aggiunta FK nullable `cat_particella_id` verso `cat_particelle.id`
  - L'import ruolo valorizza la FK solo per match univoci su codice catastale, foglio, particella e subalterno
  - Se il ruolo ha un subalterno ma `cat_particelle` ha solo la particella base, il match e consentito solo se la base e univoca e viene marcato `base_without_sub`
  - Aggiunto script `backend/scripts/backfill_ruolo_cat_particella_id.py` per allineare i dati gia importati
  - Aggiunto script `backend/scripts/repair_ruolo_catasto_parcels.py` per normalizzare dati gia importati, ricostruire `catasto_parcels` mancanti e rimuovere orfani sporchi con foglio/particella non numerici
  - Bonifica locale 2026-05-13: `catasto_parcel_not_resolved` ridotti da 4.099 a 3; eliminati 536 `catasto_parcels` orfani sporchi; export aggiornato in `exports/report_backfill_ruolo_cat_particella.md`
  - Bonifica mismatch comune 2026-05-13: riparate 5.520 righe con codice comune errato; 5.234 sono diventate collegate a `cat_particelle`; non collegate residue ridotte a 2.583
  - Estesa al Ruolo la regola storica gia usata da sync Terreni Capacitas per lo scambio Arborea/Terralba: se la particella non esiste sul comune sorgente, il resolver prova l'altro comune della coppia e marca il match con `swapped_arborea_terralba`; recuperate 249 righe ulteriori, non collegate residue a 2.334
  - Allineata la risoluzione Ruolo delle frazioni catastali di Oristano alla logica Capacitas/Agenzia: `SILI -> sezione E`, `NURAXINIEDDU -> D`, `MASSAMA -> C`, `DONIGALA -> B`. Il repair `--repair-oristano-frazione-sections` ricalcola anche righe gia collegate per evitare match permissivi su solo `G113 + foglio + particella`.
- [x] `backend/tests/ruolo/test_import.py` — import service, report job, skipped/error preview
- [x] `backend/tests/ruolo/test_api.py` — filtro unificato `GET /ruolo/avvisi?q=...` su nominativo, CF, comune, anno e codice utenza
- [x] `backend/tests/ruolo/test_api.py` — controllo `ruolo vs Capacitas` (riepilogo, comuni, export) coperto anche sui casi PostgreSQL con `nome_comune` valorizzato
- [x] `backend/tests/ruolo/test_catasto_parcels.py` — logica temporale `catasto_parcels`
- [x] `backend/tests/ruolo/test_import_integration.py` — smoke `integration-light` su blocchi DMP 2025 realistici con parser reale, merge duplicati, skipped report e filtro sezioni `CONSUMI`
- [x] `frontend/tests/e2e/ruolo-avvisi.spec.ts` — soglia minima 3 caratteri, debounce live search e apertura modale dettaglio
- [x] `frontend/tests/unit/ruolo-pages.test.tsx` — dashboard e console `controlli-capacitas` coperte su export, drilldown ed empty state
- [ ] Import completo file Ruolo 2024 (~9.810 partite) su dati reali (pendente)

---

## Decisioni aperte

| # | Decisione | Stato | Note |
|---|-----------|-------|------|
| D1 | Unità colonna `SUP.CATA.` | **✅ CHIUSA** | Are (1 ara = 100 mq = 0,01 ha). Colonne: `sup_catastale_are` (valore letto) + `sup_catastale_ha` (are / 100). |
| D2 | Libreria estrazione testo PDF (`pypdf` vs `pdfminer.six`) | Aperta | Verificare quale è già in requirements; se nessuna, aggiungere `pypdf` |
| D6 | Campo `1.679.520` riga N4 | **✅ CHIUSA** | Significato non determinato. Salvare as-is in `n4_campo_sconosciuto` (VARCHAR 30, nullable). Analisi futura. |
| D3 | Significato campi `00000000 00 N` riga N2 | Aperta | Conservati in `n2_extra_raw`; analisi futura |
| D4 | Co-intestati come FK in MVP vs testo libero | **Deciso: testo libero** | Post-MVP collegare come FK verso `ana_subjects` |
| D5 | Blocco automatico re-import anno già presente | **Deciso: avvertimento senza blocco** | L'operatore vede warning, non viene bloccato |

---

## Change log

### 2026-07-28
- Arricchita la lista `/ruolo/avvisi`: le righe non mostrano piu il codice utenza e pubblicano badge separati per notifica `Digitale/PEC` e `Raccomandata`, entrambi visibili quando le due sorgenti risultano agganciate allo stesso avviso.
- Il backend `GET /ruolo/avvisi` espone un riepilogo notifica opzionale caricato in batch: delivery PEC da `inCASS` (`mailing_list`) e raccomandate abbinate da Poste Online (`ruolo_tributi_registered_mails`), evitando query per singola riga.
- Coperti i casi con PEC+racc., avviso senza notifiche, payload inCASS malformati, preferred notice non corrispondente e scelta della raccomandata piu recente.
- Validato il perimetro modificato con coverage `100%`:
  backend changed-line coverage su `repositories.py`, `query_routes.py`, `schemas.py`;
  frontend coverage 100% su `frontend/src/app/ruolo/avvisi/page.tsx` e `frontend/src/lib/ruolo-avvisi-notifications.ts`.
- Aggiunta nel dettaglio tributo (`/ruolo/tributi/[avvisoId]`) e nella modal `Dettaglio tributo` della lista `/ruolo/tributi` l'azione `Accoda sync inCASS`.
- L'azione accoda una sincronizzazione puntuale sul soggetto GAIA collegato all'avviso tramite `POST /elaborazioni/capacitas/incass/avvisi/jobs`, con `subject_ids` valorizzato, `include_details=true`, `include_partitario=true`, mailing escluso e `continue_on_error=true`.
- Se l'avviso non espone `subject_id`, la UI mostra un errore operativo e non invia job inCASS.
- Validato il perimetro frontend modificato con test unitari dedicati e coverage 100% su `frontend/src/app/ruolo/tributi/page.tsx` e `frontend/src/app/ruolo/tributi/[avvisoId]/page.tsx`.
- Aggiornato il renderer PDF del template GAIA: il partitario viene ripulito anche dalle azioni UI finali `Chiudi`/`Scarica`, ogni pagina del partitario stampa `Dettaglio partitario allegato - pagina X di N` e il bollettino TD 896 viene unito come ultima pagina dopo il partitario.
- Il renderer mantiene tre job Chromium separati (`avviso/comunicazioni`, `partitario`, `bollettino`) e merge finale con `pypdf`, cosi partitari lunghi non ridimensionano il bollettino.
- Estesa la copertura regressione su `tributi_reminder_service.py` con gate coverage 100% e aggiornato il grafo codice Ruolo.
- La prima pagina del template GAIA espone ora `Numero avviso` nella tabella riepilogo per ogni
  riga annuale `Ruolo {anno}`, usando il `codice_cnc` dell'avviso corrispondente; coperti sia
  renderer HTML/PDF sia tabella DOCX stabile.
- Per avvisi rateizzati, `Dettaglio tributo` e la sezione `Avvisi di pagamento` del soggetto espongono il riepilogo inCASS (`importo_rateizzato`, carico, riscosso, residuo) e calcolano il costo rateizzazione come differenza positiva fra rateizzato e carico.
- Nei solleciti/preview GAIA il totale da mettere in avviso usa l'emesso rateizzato inCASS piu il versato dell'utenza e include anche la quota raccomandata (`11,55` euro) nel bollettino.
- La scadenza rata del bollettino GAIA usa la data esplicita se presente; in assenza di scadenza, il fallback e `generated_at + 30 giorni` dalla creazione della preview.
- Estesa la policy di calcolo tributi con `interest_start_mode`: `fixed_date` mantiene la decorrenza fissa, mentre `notification_date` usa per gli interessi la data invio/accettazione PEC da inCASS o la data ricezione/consegna raccomandata dal payload Poste Online; `interest_from` resta data minima/fallback.
- Aggiunta migration `20260728_1120_ruolo_tributi_interest_start_mode` per persistere la modalita di decorrenza interessi sulle policy di maggiorazione.
- Aggiunta la scadenza del pagamento bonario (`bonario_due_date`) sulle regole di calcolo ruolo: la data amministrativa resta esplicita e la decorrenza tecnica della maggiorazione (`surcharge_from`) viene derivata automaticamente dal giorno successivo.
- Aggiunta UI/UX dedicata in `/ruolo/tributi` per gestire le `Regole ruolo`: annualita, scadenza pagamento bonario, percentuale maggiorazione ruolo, percentuale interessi annui, fallback/minimo interessi e scelta decorrenza da notifica.
- In creazione, una nuova `Regola ruolo` con range annualita chiuso multi-anno viene espansa dalla UI in una policy distinta per ogni annualita, consentendo scadenze bonarie diverse per `2024`, `2025` e anni successivi senza modificare il motore backend di calcolo per singola annualita.
- Il dettaglio tributo espone ora `Decorrenza interessi` e `Sorgente decorrenza` per rendere verificabile il calcolo operativo su singolo avviso.

### 2026-07-27
- Aggiunto endpoint read-only `GET /ruolo/soggetti/{subject_id}/terreni-colture`: aggrega le particelle gia presenti a ruolo per soggetto e anno, con default sull'anno piu recente disponibile.
- La risposta espone totali, breakdown per coltura/comune/distretto, preview particelle, warning di mapping catastale e `geojson` opzionale solo con `include_geojson=true`; non avvia sync, non modifica importi e non scrive dati.
- Coperti i casi API su anno default, anno esplicito, payload vuoto e caricamento GeoJSON on-demand in `backend/tests/ruolo/test_api.py`.
- Rafforzato il flusso `Raccomandate Poste Online`: il parser HTML legge il valore esplicito di `<label>Stato</label>` evitando che footer, script o banner cookie finiscano in `status_label`; il limite DB resta una difesa finale.
- L'import raccomandate usa savepoint per riga, quindi un record sporco o un errore SQL non manda piu in rollback l'intero job e viene registrato come anomalia di import.
- Il worker Posta Online salva checkpoint di scraping su `/data/catasto/debug/posta-online-resume` e mantiene `result_json.resume_state`; un rerun dopo scrape completato riusa il payload locale senza rientrare su Poste e l'upsert evita duplicazioni.
- Validata la change Posta Online con coverage mirata al `100%` su:
  `backend/app/modules/ruolo/tributi_repositories.py`,
  `modules/elaborazioni/worker/posta_online_client.py`,
  `modules/elaborazioni/worker/posta_online_sync.py`.
- Riallineati i permessi del workflow solleciti tributi al comportamento operativo richiesto: gli utenti con accesso `ruolo.tributi.view` possono aprire la preview `Avviso sollecito`, usare il wizard batch e scaricare i documenti generati senza incorrere nel `403 Section access denied` del backend.
- Mantenuta la separazione dei permessi mutativi: pagamenti, stati e note restano protetti dalle rispettive section key dedicate.
- Validata la change con coverage mirata al `100%` sui file runtime toccati:
  `backend/app/modules/ruolo/routes/tributi_routes.py`,
  `frontend/src/app/ruolo/tributi/page.tsx`,
  `frontend/src/app/ruolo/tributi/solleciti/page.tsx`.
- Corretto il default operativo dei solleciti batch: il wizard `Genera PDF nel NAS` e il
  fallback backend usano ora il template GAIA `__gaia_proposal__`, quindi il PDF generato
  contiene avviso, bollettino postale TD 896 e partitario. Il DOCX legacy resta disponibile
  solo se un chiamante passa un path esplicito.
- Verificato sul server CED che il renderer produce un PDF di 4 pagine con bollettino a pagina 3.
- Validata la change con coverage mirata al `100%` su:
  `backend/app/modules/ruolo/tributi_repositories.py`,
  `frontend/src/app/ruolo/tributi/page.tsx`.
- Separata definitivamente la console `Raccomandate Poste Online` dalla pagina Tributi:
  `/ruolo/tributi` resta dedicata all'elenco tributi e ai solleciti, mentre la sidebar apre
  le raccomandate su `/ruolo/raccomandate`.
- Aggiunti test frontend di regressione per verificare che `/ruolo/tributi` non contenga piu
  la console Raccomandate e che la sidebar mantenga attive route distinte.
- Corretto il renderer PDF del template GAIA per partitari reali lunghi: Chromium genera ora
  avviso/comunicazioni/bollettino e partitario in PDF separati, poi il backend li unisce con
  `pypdf`, evitando che il partitario faccia ridurre o spostare il bollettino.
- Validato localmente il caso `00050540384_avviso_sollecito_2024-2025`: bollettino a pagina 3,
  partitario da pagina 4, dimensione piena allineata al riferimento
  `/tmp/gaia_sollecito_bollettino_896_prova.pdf`.
- Validata la change renderer con coverage mirata al `100%` su
  `backend/app/modules/ruolo/services/tributi_reminder_service.py`.

### 2026-07-24
- Predisposta la console read-only `Raccomandate Poste Online` per controllare matching e anomalie degli invii importati da Poste; la route frontend operativa corrente e `/ruolo/raccomandate`.
- Aggiunto in sidebar Ruolo il link diretto `Raccomandate` verso `/ruolo/raccomandate`.
- La console usa `GET /ruolo/tributi/raccomandate` con filtri su ricerca libera, `match_status`, `recovery_status`, `anomalies_only` e paginazione; la vista iniziale mostra solo le anomalie operative.
- Confermata la semantica di matching: Poste Online non espone identificativi GAIA di avviso/utenza, quindi l'associazione resta backend-only e indiziaria; il frontend mostra score, motivo, stato recupero e link all'avviso quando il backend ha prodotto un match.
- Il perimetro frontend modificato e coperto con test unitari dedicati e coverage 100% su `registered-mails-console.tsx` e `ruolo-api.ts`.
- Validata in locale la sync Poste Online con job limitato (`max_pages=1`, `max_details=1`, senza contatti): login headless, archivio e dettaglio sono stati letti correttamente; corretto il fallback di persistenza troncando i campi Poste indicizzati ai limiti DB e preservando il raw payload completo.

### 2026-07-23
- Corretto il flusso `Avviso sollecito` in `/ruolo/tributi`: la modale di preview si apre immediatamente al click con stato di caricamento e mostra gli errori di generazione nella stessa superficie, evitando che l'utente resti senza feedback mentre vengono creati i PDF.
- Reso robusto il renderer PDF del template GAIA: il backend ora trova Chromium anche nella cache Playwright del container Docker, oltre a binari di sistema e snap.
- Corretto il comportamento dell'autosync inCASS: i job automatici `Avvisi pagamenti` ora eseguono un refresh leggero di stato sugli avvisi gia sincronizzati, senza riscaricare dettaglio/partitario e senza riscrivere gli importi contabili.
- I nuovi avvisi intercettati durante l'autosync restano invece arricchibili con dettaglio e partitario tramite flag dedicati, cosi il monitor periodico aggiorna pagato/rateizzato/parziale e cattura novita senza rieseguire una sincronizzazione completa di tutti i ruoli.
- Limitato l'autosync automatico Ruolo/inCASS alla finestra notturna configurabile `20:00-06:00 Europe/Rome`: scheduler e worker saltano i job automatici fuori fascia, mentre le sync manuali restano disponibili.
- Ottimizzata la lettura dei recapiti mailing lato tributi: su PostgreSQL il summary legge solo `raw_detail_json.mailing_list`, evitando di materializzare l'intero JSON pesante del partitario.
- Validato il perimetro runtime modificato con coverage mirata al 100% su config, modelli payload inCASS, scheduler autosync, servizio inCASS e repository tributi.

### 2026-07-11
- Riallineate le `ruolo_particelle` 2019-2024 su locale e server CED con `scripts/materialize_ruolo_from_incass.py --replace-year --reparse-partitario`.
- Creati backup mirati pre-apply delle tabelle `ruolo_avvisi`, `ruolo_partite`, `ruolo_particelle`, `ruolo_import_jobs` e `catasto_parcels`.
- Conteggi finali allineati locale/server: 2019=17065, 2020=20226, 2021=24390, 2022=93540, 2023=95062, 2024=96684.
- Verifiche qualità post-run: `sup_irrigata_ha > 1000 = 0` e `distretto NULL/0/2019 = 0` per tutte le annualità 2019-2024.
- Dettaglio operativo in `domain-docs/ruolo/docs/RUOLO_PARTICELLE_RIALLINEAMENTO_2019_2024_2026-07-11.md`.

### 2026-04-16
- PRD v1, Execution Plan v1, Prompt Codex e Progress v1 prodotti.
- Formato file `.dmp` analizzato su sample Ruolo 2024 (2 partite CNC).
- Modello dati definito: 4 tabelle `ruolo_*` + `catasto_parcels` con logica temporale.
- Decisione architetturale: `ruolo` modulo autonomo (non sub-modulo di `utenze`).
- Decisione: co-intestati come testo libero nel MVP.
- Decisione: avvertimento (non blocco) su re-import anno già presente.
- Punto aperto D1 (unità superfici) identificato come prerequisito critico per M1.

### 2026-04-16 (aggiornamento)
- D1 chiusa: SUP.CATA. confermata in are. Colonne DB: `sup_catastale_are` + `sup_catastale_ha`.
- Aggiornati PRD, Execution Plan e Prompt Codex con unità corretta.

### 2026-04-16 (implementazione M1–M5)
- M1 completata: migration applicata, modelli ORM, enums, parser con 14 test unitari, import service asincrono.
- M2 completata: schemas Pydantic, repository, 10 endpoint REST (import + query + export CSV + catasto parcels).
- M3 completata: bootstrap section keys, flag `module_ruolo` su ApplicationUser, router registrato.
- M4 completata: 6 pagine frontend (`/ruolo`, `/ruolo/avvisi`, `/ruolo/avvisi/[id]`, `/ruolo/particelle`, `/ruolo/stats`, `/ruolo/import`), widget soggetto, navigazione aggiornata.
- M5 parziale: permessi `require_module` attivi; test di integrazione API pendenti.

### 2026-04-17
- Allineata anche l'integrazione embedded `RuoloAvvisiSection` nella scheda soggetto del dominio utenze, con visual language coerente al workspace `ruolo` e CTA operative uniformate.
- Ridotta l'altezza della hero di `/ruolo/import` quando aperta in modale (`embedded=1`), per migliorare leggibilità e densità del workspace rapido.
- Compattata anche la KPI row del workspace rapido `/ruolo/import` in modalità embedded, con gap e tile più bassi per aumentare spazio utile sopra il fold.
- `/ruolo/import` ora prova a rilevare automaticamente l'anno tributario dal file selezionato (contenuto PDF/testo o filename) e consente comunque override manuale.
- Euristica anno `ruolo` resa deterministica: priorità a filename `R2024...`, poi pattern `Partita CNC 01.02021000039305` da cui viene estratto `2021`, infine fallback testuali.
- Aumentato il limite upload Nginx del progetto per supportare file `ruolo` fino a 128 MB senza errore `413 Request Entity Too Large`.

### 2026-05-15
- `GET /ruolo/avvisi` e `GET /ruolo/avvisi/export` supportano ora il parametro `q`, con matching su `codice_cnc`, `nominativo_raw`, `codice_fiscale_raw`, `codice_utenza`, `anno_tributario` e `comune_nome` delle partite collegate.
- `/ruolo/avvisi` e stata riallineata alla UX di `utenze`: campo singolo di ricerca, stato iniziale “Ricerca pronta”, avvio automatico dopo 3 caratteri, debounce client-side e aggiornamento URL con `router.replace` per evitare raffiche di chiamate.
- Le card avviso aprono una modale con iframe embedded del dettaglio; `/ruolo/avvisi/[id]` nasconde il top header quando riceve `?embedded=1`.
- Aggiunti test backend sul filtro `q` e test Playwright sul comportamento live search + apertura modale.

### 2026-05-18
- Aggiunta la page frontend `/ruolo/particelle` come vista del dataset storico `ruolo_particelle`, non limitata a `cat_particelle`.
- Esteso `GET /ruolo/particelle` con comune di partita, stato di match verso `cat_particelle` e classificazione/stato scansione AdE.
- La dashboard `Ruolo`, la sidebar modulo e la ricerca globale ora espongono il nuovo accesso rapido alle particelle a ruolo.
- La dashboard `Ruolo` separa ora gli `avvisi non collegati` dai `non collegati a catasto` e dai casi `soppresse AdE`, eliminando l'indicatore ambiguo precedente.
- `/ruolo/particelle` supporta ora apertura riga in modale con dettaglio storico e link al Catasto quando il match esiste.
- Il workspace `/ruolo/particelle` riusa la section permission `ruolo.avvisi` per evitare blocchi operativi su ambienti dove non sia stato riallineato il catalogo sezioni.

### 2026-06-15
- Aggiunto il controllo economico `ruolo vs Capacitas` sulla dashboard `/ruolo`, con KPI, delta aggregati `0648/0985`, mismatch per `CF/P.IVA`, breakdown per comune ed export CSV.
- Introdotta la console dedicata `/ruolo/controlli-capacitas`, collegata dalla navigazione di modulo e pensata come workspace operativo per responsabile e supervisione.
- Estesa `/ruolo/avvisi` con supporto ai drilldown URL-driven su `codice_fiscale` e `comune`, così i mismatch del controllo Capacitas aprono direttamente la lista di lavoro coerente.
- Hardening backend sulle query aggregate PostgreSQL: corretto il riuso delle espressioni `coalesce(...)` in `GET /ruolo/stats/analytics` e `GET /ruolo/stats/capacitas-check/comuni`, eliminando i `500 Internal Server Error` dovuti a `GroupingError`.
- Rafforzata la copertura test backend/frontend sul perimetro `controlli-capacitas`, inclusi drilldown, export e caso di stato vuoto.

### 2026-06-16
- Promossa la console `/ruolo/calcolo-gaia` a vista operativa principale del modulo per il calcolo del ruolo, lasciando `/ruolo/controlli-capacitas` come `Audit Capacitas` tecnico.
- Il payload backend `GET /ruolo/stats/calcolo-gaia` e ora autosufficiente: include valori `Ruolo`, `GAIA`, `Excel`, stato confronto e diagnosi per soggetto, senza dipendere dal dataset mismatch di `capacitas-check`.
- Corretto un rischio funzionale della prima implementazione frontend: soggetti presenti nel ruolo ma fuori dal top mismatch o sotto soglia potevano apparire come “senza confronto ruolo”; ora la console usa solo il payload dedicato `calcolo-gaia`.
- Esteso anche l'export CSV `calcolo-gaia` per scrivere direttamente i valori ruolo e la diagnosi derivati dal medesimo endpoint, mantenendo coerenza tra UI ed export.
- Aggiornata la copertura con test backend sul payload `calcolo-gaia` arricchito e test frontend dedicato alla nuova console con apertura modale del dettaglio calcolo.

### 2026-07-08
- Chiarita in UI e documentazione la separazione delle tre sorgenti economiche: `Ruolo inCASS` dal partitario del ruolo pubblicato, `Excel Capacitas` dal file importato nel batch attivo, `Calcolo GAIA` da imponibile e aliquote Capacitas.
- Il breakdown per comune di `capacitas-check/comuni` normalizza frazioni e alias territoriali prima del confronto (`FRAZIONE*COMUNE -> COMUNE`, `SILI -> ORISTANO`, `SAN NICOLO D'ARCIDANO -> SAN NICOLO ARCIDANO`) ed espone le denominazioni sorgenti aggregate.
- Aggiunta l'anteprima delle righe Excel Capacitas nel drilldown `Apri calcolo`, con importi originali, campi sorgente e segnali di anomalia.
- Verifiche eseguite: `backend/tests/ruolo/test_api.py`, `frontend/tests/unit/ruolo-pages.test.tsx`, lint frontend mirato e controllo coverage puntuale sulle linee runtime modificate.
