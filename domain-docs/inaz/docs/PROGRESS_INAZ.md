# Progress Inaz

Data aggiornamento: 2026-06-15 (festivita tipizzate + recuperi HR workflow)

## Stato attuale

Implementato un MVP collaboratori/giornaliere coerente con il documento
`IMPLEMENTATION_INAZ_COLLABORATORI_GIORNALIERE.md`.

### Backend

- aggiunto `module_inaz` a `application_users`;
- aggiunte sezioni bootstrap `inaz.*` nel catalogo permessi;
- introdotto vault credenziali `inaz_credentials` con cifratura via `CREDENTIAL_MASTER_KEY`;
- introdotto data model collaboratori-centrico:
  - `inaz_collaborators`
  - `inaz_daily_records`
  - `inaz_daily_punches`
  - `inaz_event_summaries`
  - `inaz_import_jobs`
- introdotto modello calendari/template orari:
  - `inaz_holidays`
  - `inaz_schedule_templates`
  - `inaz_schedule_rules`
  - `inaz_collaborator_schedule_assignments`
- import JSON compatibile con l'output dello scraper `inaz-collaboratori`;
- import JSON che normalizza e persiste anche i campi ricchi del dettaglio giorno Inaz:
  - orario programmato/effettivo
  - fasce orarie
  - ore teoriche / ore assenza
  - riepilogo giornata
  - totali giornata
  - richieste / anomalie;
- normalizzazione dedicata delle richieste giornaliere Inaz su `inaz_daily_records`:
  - `request_type`
  - `request_description`
  - `request_status`
  - `request_authorized_by`
  - `resolved_absence_cause` (es. `ferie`, `permesso`, `malattia`);
- mapping collaboratore -> `application_users`;
- endpoint calendario collaboratore;
- endpoint riepilogo eventi collaboratore;
- endpoint elenco giornaliere;
- endpoint admin per bootstrap festivita locali/mobili e assegnazione template orari ai collaboratori;
- modello festivita esteso con tipizzazione esplicita:
  - `ordinary`
  - `suppressed`
  - `working_override`
- classificazione giornaliera coerente con il dominio HR:
  - festivita ordinaria = giorno festivo;
  - festivita soppressa = giorno lavorativo con maturazione recupero;
  - working override = eccezione lavorativa senza maturazione recupero;
- precedenza corretta delle festivita configurate a DB rispetto al calendario standard;
- tracciamento applicativo recuperi su ogni giornaliera:
  - `grants_recovery_day`
  - `recovery_day_credit`
  - `uses_recovery_day`
  - `recovery_day_debit`
  - `recovery_day_balance_delta`;
- dashboard aggregata recuperi con KPI:
  - maturati
  - fruiti
  - saldo;
- introdotta tabella `inaz_recovery_adjustments` per rettifiche HR persistite;
- workflow rettifiche HR:
  - `pending`
  - `approved`
  - `rejected`
  - audit su creatore / revisore / ultimo aggiornamento;
- le rettifiche manuali entrano nel saldo solo se `approved`;
- export `.xlsm` dal DB con preservazione macro via `openpyxl(..., keep_vba=True)`;
- export `.xlsm` che usa la causale assenza normalizzata / descrizione richiesta (`Ferie`, `Permesso ordinario`, ecc.) nel blocco `absence_code`, prima del fallback su `evidenze`.
- export `.xlsm` allineato meglio al tracciato HR di `Archivio2`:
  - metadata riga (`A/E/F/G`) ereditati dallo storico del dipendente nel template;
  - fallback metadati da foglio `Operai` del template se per il dipendente manca una riga storica in `Archivio2`;
  - `OPESAB` trattato come ordinario previsto nel caso base;
  - `KM AUTO` valorizzato dal campo operatore `km_value`;
  - `N. ORE TRASFERTA` valorizzato dal campo strutturato `trasferta_minutes`;
  - supporto applicativo `trasferta_montano`: in GAIA resta separato, mentre nel template legacy viene esportato come `X` nello stesso blocco della trasferta;
  - template di default non piu hardcoded nel servizio: configurato via `INAZ_EXPORT_TEMPLATE_PATH`;
- export `.xlsm` esteso anche al foglio `Archivio` con riepilogo mensile:
  - `LO Fer./Fest./Nott./Fest.Nott.` popolati dal breakdown CCNL runtime;
  - `LS Fer./Fest./Nott./Fest.Nott.` popolati dalle quote extra/straordinario runtime;
  - `Tot Ord.`, `Tot. Str.`, `TOT. ORE`, `Km. AUTO`, `Trasf.` aggiornati in coerenza;
  - `GG.Lav.` = giorni con lavoro ordinario o extra;
  - `GG.Retr.` = `GG.Lav.` + giornate con quota giustificata;
  - `REP. FERIALE/FESTIVA` = conteggio giornate con reperibilita in giorno feriale/festivo;
  - `ASSENZE` = giornate con `absence_minutes > 0`;
  - `B.O. MM.PP` = `InazEventSummary.residuo_prec_minutes` della voce `Banca ore*`, esportato in ore;
  - `B.O. MATURATA` = `InazEventSummary.spettante_minutes` della voce `Banca ore*`, esportato in ore;
  - `B.O. USATA MESE` = `InazEventSummary.fruito_minutes` della voce `Banca ore*`, esportato in ore;
  - `B.O. RESIDUE` = `InazEventSummary.saldo_totale_minutes` della voce `Banca ore*`, esportato in ore;
  - i campi `B.O.*` non vengono piu derivati da `mpe` o da bilanci locali di recupero: la sorgente autoritativa e il riepilogo eventi sincronizzato da INAZ.
- pagina `/inaz/export` aggiornata con preview operativa:
  - conteggio giorni con trasferta e ore esportabili;
  - conteggio dedicato dei giorni `comune montano`;
  - breakdown reperibilita `hours/days/shifts`;
  - evidenza esplicita del limite del template legacy, che degrada comunque la reperibilita a flag `X`.
- classificazione export `.xlsm` non piu solo `sabato/domenica`: adesso usa festivita, sabati alternati, primo sabato del mese e rientri stagionali se presenti nei template.
- precedenza logica classificazione giornaliera:
  - `detail` Inaz se presente e strutturato;
  - fallback su valori importati dalla griglia/cartellino;
  - fallback finale su template orari GAIA.

### Frontend

- dashboard `/inaz`;
- dashboard `/inaz` rifinita come vista macro delle presenze del mese:
  - KPI completi su collaboratori attivi, giornaliere mese, ore ordinarie, extra effettivi;
  - statistiche su assenze, anomalie, KM carburante, giorni speciali;
  - distribuzione causali principali (`ferie`, `permesso`, `malattia`);
  - codici orario / turni prevalenti del mese;
  - caricamento con paginazione completa delle giornaliere del mese, non piu campione ridotto;
- pagina `/inaz/settings` per gestione credenziali Inaz;
- lista `/inaz/collaboratori`;
- lista `/inaz/collaboratori` con suggerimento automatico di mapping verso utenti GAIA;
- apertura dettaglio collaboratore in modale embedded dalla lista, con fallback alla pagina completa;
- dettaglio `/inaz/collaboratori/[id]` con:
  - cartellino periodo;
  - riepilogo eventi;
  - mapping verso utente GAIA per admin;
  - suggerimento mapping come prima opzione del select, con preselezione automatica se il collaboratore non e ancora collegato;
- pagina `/inaz/giornaliere` rifatta come **cartellino mensile a matrice**:
  - collaboratori in verticale, giorni in orizzontale, con colonna collaboratore e header giorni "sticky";
  - perimetro dati filtrato sul responsabile che ha eseguito la sync (`owner_user_id`);
  - celle colorate per stato (lavorato / assenza / giorno speciale / anomalia) con indicatori compatti `▲` extra, `🚗` KM, `✉` richieste; weekend ombreggiati e giorno corrente evidenziato;
  - dettaglio giornata in **modale** con navigazione `precedente/successivo`, supporto tastiera `Esc`, `←`, `→` e badge stato coerente con l'analisi;
  - il titolo della modale mostra anche il **giorno della settimana**;
  - nella modale il link **"Apri dettaglio collaboratore"** apre in un nuovo tab;
  - nella modale vengono mostrate anche le **timbrature** (`entrata`, `uscita`, terminale se disponibile);
  - riquadro dedicato **"Aggiungi KM carburante"** + modalita **"Inserisci KM"** che trasforma ogni cella in input rapido con salvataggio automatico al blur;
  - modifica diretta di `KM`, straordinario override, maggior presenza override e nota operativa;
  - evidenza esplicita della **causale Inaz rilevata** (es. ferie / permesso), stato richiesta e autorizzatore nel dettaglio giornata;
  - celle matrice rese piu leggibili per le assenze normalizzate (`ferie`, `permesso`, `malattia`) con etichette e tono distinti;
  - **filtri rapidi per tipo orario / contratto** derivati dal template orario prevalente (`schedule_code`) di ogni collaboratore;
  - selettore mese con **frecce `‹ ›`** per scorrere rapidamente; header riorganizzato su griglia a colonne (mese, ricerca, azioni, filtri, riepilogo mese, legenda);
  - **scroll orizzontale anche via drag** (tieni premuto il tasto sinistro e trascina), con soglia anti-click sulle celle;
  - **popup mese vuoto**: se per il mese non esistono giornaliere, una modal propone di caricare il mese precedente o avviare la sync;
  - **modal scheda collaboratore**: il nome del collaboratore apre una modal sintetica (totali mese + elenco giornate) invece di navigare, con link alla scheda completa;
- pagina `/inaz/anomalie` dedicata all'analisi delle giornate da verificare (anomalie, richieste, giorni speciali):
  - nasce dal contenuto della vecchia giornaliere (tabella + pannello rettifiche);
  - scansione automatica degli ultimi mesi e fallback automatico al mese precedente se quello corrente non ha anomalie;
  - voce **"Anomalie"** aggiunta nella sidebar del modulo;
- route `/inaz/import` mantenuta solo come redirect tecnico verso `/inaz/sync`, non piu esposta come flusso operativo utente;
- pagina `/inaz/festivita` dedicata a bootstrap, creazione, modifica e cancellazione festivita Inaz;
- pagina `/inaz/recuperi` per HR/super admin con:
  - saldi per collaboratore;
  - cronologia maturato / fruito / rettifiche;
  - filtri operativi (saldi negativi, pendenti, rettifiche manuali);
  - workflow approvazione / reiezione rettifiche;
  - audit visibile in timeline;
- pagina `/inaz/export` con download `.xlsm`;
- pagina `/inaz/export` con preview dataset del mese, perimetro collaboratori e KPI di righe/giorni speciali;
- pagina `/inaz/sync` con avvio job live, polling stato, retry e storico run;
- storico `/inaz/sync` con dettaglio espandibile di avanzamento, collaboratore corrente, stato worker e ultimo errore;
- storico `/inaz/sync` hardenizzato lato frontend contro payload `progress` non omogenei:
  - `last_event`, `state`, `error` e collaboratore corrente normalizzati prima del render;
  - evitati runtime error React in presenza di eventi strutturati come oggetti;
- navigazione modulo aggiornata in sidebar e module switcher.
- pagina `/inaz/giornaliere` aggiornata:
  - se la causale normalizzata e `ferie`, `KM carburante` e `Reperibilita giornaliera` sono disabilitati nella modale;
  - il messaggio in modale esplicita il blocco operativo sulle giornate in ferie.

### Sync live

- introdotta tabella `inaz_sync_jobs` per orchestrare le run live;
- aggiunto worker Python separato avviato fuori dal processo FastAPI;
- integrazione con lo scraper esterno `inaz-scraper` tramite worker dedicato;
- login automatico con credenziali cifrate selezionate dal vault `Inaz`;
- ogni run live produce ancora artefatti su filesystem (`json`, `log`, `summary`, `progress`, `events`) per diagnostica;
- il worker salva progressivamente a DB i collaboratori completati, senza aspettare piu l'import finale monolitico;
- collaboratori, giornaliere e summary persistiti portano anche `owner_user_id`, distinto dal mapping `application_user_id` del singolo dipendente;
- il job aggiorna un checkpoint persistito in `inaz_sync_jobs.params_json.checkpoint.completed_employee_codes`;
- il retry riparte dai collaboratori non ancora persistiti, invece di ricominciare da `1/N`;
- il worker espone fasi di avanzamento piu granulari (`opening_timesheet`, `daily_rows_loaded`, `opening_summary`, `summary_loaded`) per rendere piu leggibile lo stato del job;
- il payload `progress.last_event` puo contenere anche eventi strutturati (non solo stringhe) e la UI li gestisce correttamente;
- se il riepilogo eventi di un collaboratore fallisce, la sync non perde piu il collaboratore: prosegue persistendo almeno anagrafica e giornaliere, e registra il warning nel log/event stream;
- retry applicativo disponibile fino al limite configurato;
- cancel e delete dei job falliti/storici disponibili da UI.

### Test e verifica

- aggiornati test backend `backend/tests/test_inaz_api.py` sul nuovo flusso collaboratori/sync/XLSM;
- aggiornati test backend su festivita tipizzate, recuperi maturati/fruiti e workflow rettifiche HR;
- aggiunti test unitari backend `backend/tests/test_inaz_schedule_engine.py` per:
  - Martedi della Sartiglia e Pasquetta;
  - sabato alternato operai catasto;
  - rientro del lunedi stagionale;
  - scrittura corretta delle colonne speciali in `Archivio2`;
- aggiunta verifica backend dell'export `.xlsm` su:
  - causale assenza nel blocco corretto di `Archivio2`;
  - metadata riga ereditati dal template;
  - `KM AUTO` esportato dal valore manuale operatore;
- aggiunti test per la precedenza `detail Inaz > template fallback`;
- aggiunti test frontend iniziali `frontend/tests/unit/inaz-pages.test.tsx`;
- aggiunti test frontend sul dettaglio collaboratore e preselezione del mapping suggerito in `frontend/tests/unit/inaz-collaboratore-detail.test.tsx`;
- aggiornati test frontend sul cartellino a matrice in `frontend/tests/unit/inaz-giornaliere-page.test.tsx` (rendering matrice, apertura giornata + salvataggio rettifiche, apertura modal collaboratore, timbrature in modale);
- i test frontend `Inaz` oggi coprono esplicitamente:
  - dashboard / pagine principali, inclusa la dashboard macro mese `/inaz`;
  - mapping suggerito collaboratori;
  - workspace giornaliere e modale operativa;
  - dettaglio collaboratore;
  - storico `/inaz/sync` con payload `progress` strutturato e non solo stringhe;
- aggiunti test frontend per la pagina anomalie e gli helper mesi/anomalie in `frontend/tests/unit/inaz-anomalie-page.test.tsx` e `inaz-anomaly-months.test.ts`;
- aggiunto test backend sul filtro per `owner_user_id`, per garantire che un capo settore veda i dati da lui importati anche senza mapping del collaboratore verso `application_users`;
- `docker compose exec -T backend sh -lc 'cd /app && alembic upgrade heads && alembic current'`: ok;
- `pytest backend/tests/test_inaz_api.py tests/test_inaz_schedule_engine.py -q`: ok;
- `pytest --cov=app.modules.inaz --cov-report=term-missing tests/test_inaz_api.py tests/test_inaz_schedule_engine.py`: ok, coverage modulo `inaz` 74.15%;
- `frontend npm run typecheck`: ok;
- `frontend npm run test:unit -- tests/unit/inaz-pages.test.tsx tests/unit/inaz-collaboratore-detail.test.tsx tests/unit/inaz-giornaliere-page.test.tsx tests/unit/inaz-collaborator-mapping.test.ts`: ok (16 test);
- `frontend npx vitest run`: ok (57 test);
- `frontend npx vitest run --coverage --coverage.include=src/app/inaz/**/*.tsx --coverage.include=src/lib/api.ts --coverage.include=src/types/api.ts tests/unit/inaz-collaboratore-detail.test.tsx tests/unit/inaz-giornaliere-page.test.tsx tests/unit/inaz-pages.test.tsx tests/unit/inaz-anomalie-page.test.tsx tests/unit/inaz-anomaly-months.test.ts`: ok, coverage frontend perimetro Inaz 29.64% statement / 30.15% line;
- verifica smoke backend eseguita su parser JSON e compilazione XLSM.

## Gap aperti

- UI frontend ancora essenziale:
  - cartellino mensile a matrice disponibile su `/inaz/giornaliere`, ma manca ancora un calendario per singolo collaboratore nel dettaglio;
  - niente preview differenziale/import duplicati avanzata;
  - niente selector template assistito lato filesystem;
  - il "tipo di contratto" e oggi un proxy basato sul template orario (`schedule_code`): manca il dato contrattuale reale (tag manuale GAIA o estrazione da Inaz);
- la dashboard macro mese e stata arricchita, ma i KPI sono ancora calcolati in frontend da tutte le giornaliere del mese; un endpoint aggregato backend dedicato resta un miglioramento utile per performance;
- la UI dedicata per festivita e recuperi HR e ora presente; restano ancora migliorabili export/report e viste operative avanzate;
- `Trasferte` sono ora esportate se presenti nel record GAIA (`trasferta_minutes`); resta ancora aperta l'estrazione affidabile automatica dal portale Inaz quando il dato non arriva gia strutturato nel payload;
- il tracciato HR legacy di export ha una sola cella giornaliera per `N. ORE TRASFERTA / COMUNE MONTANO (X)`: per questo in export `trasferta_montano` ha priorita sul numero ore, mentre in GAIA i due dati restano distinti;
- `Reperibilita` e oggi strutturata in GAIA (`hours/days/shifts`) e visibile nella preview export, ma il template HR legacy continua ad accettare solo il flag `X`;
- per i dipendenti assenti sia nello storico `Archivio2` sia nel foglio `Operai` del template HR, restano ancora non determinabili automaticamente i metadati anagrafici tecnici (`mansione`, `inquadramento`, testo periodo);
- questi metadati mancanti sono quindi **ancora da implementare** tramite una fonte esterna affidabile (altro archivio GAIA, estensione dello scraper Inaz, oppure tabella manuale di completamento gestita in GAIA);
- sync live ancora minimale:
  - nessuna policy di retry automatica schedulata;
  - nessuna orchestrazione multi-worker o schedulazione periodica;
- la persistenza progressiva e stata introdotta, ma va ancora consolidata con:
  - piu test specifici di resume dopo crash/restart;
  - eventuale tabella dedicata `sync job items` se servira audit e retry per singolo collaboratore;
- resta solo un warning non bloccante nei test export `openpyxl/zipfile`;
- test end-to-end con credenziali reali e run live su mese completo ancora da consolidare come procedura operativa.

## Prossimi passi consigliati

1. consolidare il resume post-crash con test live e recovery automatica dei job parziali;
2. calendario mensile dedicato nel dettaglio collaboratore;
3. export/report HR recuperi;
4. preview differenziale e duplicate handling piu ricco lato giornaliere;
5. run end-to-end documentata su credenziale reale e validazione `.xlsm` su mese completo.
