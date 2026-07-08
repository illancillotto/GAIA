# Progress Presenze

Data aggiornamento: 2026-07-08 (micro UX giornaliere, coda anomalie e blueprint integrazione GAIA/GATE)

## Stato attuale

Implementato un MVP collaboratori/giornaliere coerente con il documento
`IMPLEMENTATION_PRESENZE_COLLABORATORI_GIORNALIERE.md`.

Formalizzato anche il blueprint di integrazione con GATE Console Mobile in
`GAIA_GATE_PRESENZE_INTEGRATION_BLUEPRINT.md`: GAIA resta source of truth per
giornaliere, anomalie, validazioni, audit e organigramma operativo; GATE diventa
workspace mobile con cache applicativa limitata a mese corrente e mese
precedente, scrittura diretta su GAIA e API dedicate `/gate/presenze/*`.

Avviata l'implementazione lato GAIA del perimetro GATE Presenze:

- introdotto modello operativo squadre con `organization_teams`,
  `organization_team_memberships` e
  `organization_team_supervisor_assignments`;
- esposti endpoint backend `/gate/presenze/teams` per creazione, modifica,
  visibilita, membership collaboratori e assegnazione capi settore/operatori;
- applicata la regola iniziale di integrita: un collaboratore non puo avere
  membership sovrapposte su squadre diverse o duplicazioni sovrapposte nella
  stessa squadra;
- aggiunti permessi bootstrap `presenze.gate.*` per la futura segmentazione
  fine di lettura, validazione, patch, anomalie, export e squadre.
- aggiunto secondo blocco API GATE Presenze:
  - `GET /gate/presenze/months/available`;
  - `GET /gate/presenze/giornaliere?month=YYYY-MM`;
  - `GET /gate/presenze/giornaliere/{record_id}`;
  - `POST /gate/presenze/giornaliere/{record_id}/validate`;
  - `POST /gate/presenze/giornaliere/{record_id}/patch`;
  - `GET /gate/presenze/anomalie?month=YYYY-MM`;
  - `POST /gate/presenze/anomalie/{record_id}/resolve`;
  - `GET /gate/presenze/export/preview?month=YYYY-MM`;
  - `POST /gate/presenze/export/generate`;
- le API giornaliere usano il perimetro squadre GATE per limitare la visibilita
  dei capi settore/operatori, espongono `rules_version` e registrano audit
  operativo `gate_mobile` su validazioni, patch e chiusure anomalie.
- aggiunta sezione regole condivisa GAIA/GATE:
  - backend `GET /gate/presenze/rules` con `rules_version`,
    `export_rules_version`, sezioni e regole operative;
  - frontend GAIA `/presenze/regole` con spiegazione user-friendly di anomalie,
    validazione/audit ed export;
  - voce `Regole` nella sidebar del modulo Presenze.

### Backend

- aggiunto `module_presenze` a `application_users`;
- aggiunte sezioni bootstrap `presenze.*` nel catalogo permessi;
- introdotto vault credenziali `presenze_credentials` con cifratura via `CREDENTIAL_MASTER_KEY`;
- introdotto data model collaboratori-centrico:
  - `presenze_collaborators`
  - `presenze_daily_records`
  - `presenze_daily_punches`
  - `presenze_event_summaries`
  - `presenze_import_jobs`
- esteso il profilo collaboratore con `operai_group`, attributo persistente e modificabile dagli admin insieme al profilo contrattuale;
- introdotta configurazione persistente `presenze_operai_rule_configs` per spostare le formule operai da logica hardcoded a regole amministrabili;
- le configurazioni operai default distinguono:
  - gruppo `agrario`: sabati 1 e 3 del mese, sabato previsto da `6h30`;
  - gruppo `catasto_magazzino`: due sabati mensili alternati/scambiabili, sabato lavorato o giustificato previsto da `6h`;
- i codici `OPE0714_1E3SAB`, `OPE0613`, `OP_5.3_12.3`, `OPESAB` e `OSAB5.3_12.3` condividono la stessa logica operaia, con orari nominali risolti dalla configurazione del gruppo;
- i sabati non previsti per il gruppo configurato vengono trattati con teorico `0`; per `catasto_magazzino`, se nel mese risultano gia due sabati lavorati o giustificati, gli altri sabati importati da INAZ non generano ore mancanti;
- ferie e permessi su un sabato previsto coprono il teorico configurato e possono chiudere la giornata in `ok` se non restano minuti mancanti nel mese/giorno valutato;
- mantenuto fallback legacy per collaboratori operai senza `operai_group`, cosi i codici storici continuano a essere analizzati fino al completamento anagrafico;
- l'endpoint admin `/presenze/configuration/operai-rules` inizializza i default se mancanti e consente la modifica delle regole attive senza deploy;
- la qualita operativa operaia blocca le giornate in cui una richiesta INAZ `ACC` risolve una timbratura ma genera MPE oltre la soglia giornaliera configurata.
- la soglia default di revisione MPE per le giornaliere operaie e stata riallineata a `3 ore`: le timbrature complete con solo extra/straordinario fino a `180` minuti non entrano piu nella coda anomalie, mentre i casi `> 3 ore` restano bloccanti e vengono segnalati agli operatori;
- per i profili non operai, una richiesta INAZ `ACC` con timbrature complete puo chiudere in `ok` anche quando INAZ lascia anomalie tecniche residue (`OREM`, timbratura mancante, assenza tecnica), se GAIA ricostruisce comunque una giornata coerente dai punch salvati e dal teorico del giorno;
- l'endpoint admin `PUT /presenze/collaborators/{collaborator_id}/contract-profile` aggiorna in modo esplicito `contract_kind`, `operai_group` e `standard_daily_minutes` del collaboratore;
- il conteggio anomalie della scheda `/me` usa il payload dettaglio Inaz normalizzato (`raw_payload_json`) oltre a `stato`, evitando falsi negativi quando i campi derivati non sono materializzati;
- introdotto modello calendari/template orari:
  - `presenze_holidays`
  - `presenze_schedule_templates`
  - `presenze_schedule_rules`
  - `presenze_collaborator_schedule_assignments`
- import JSON compatibile con l'output dello scraper `presenze-collaboratori`;
- import JSON che normalizza e persiste anche i campi ricchi del dettaglio giorno Inaz:
  - orario programmato/effettivo
  - fasce orarie
  - ore teoriche / ore assenza
  - riepilogo giornata
  - totali giornata
  - richieste / anomalie;
- normalizzazione dedicata delle richieste giornaliere Inaz su `presenze_daily_records`:
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
- introdotta tabella `presenze_recovery_adjustments` per rettifiche HR persistite;
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
- template di default non piu hardcoded nel servizio: configurato via `PRESENZE_EXPORT_TEMPLATE_PATH`;
- export `.xlsm` esteso anche al foglio `Archivio` con riepilogo mensile:
  - `LO Fer./Fest./Nott./Fest.Nott.` popolati dal breakdown CCNL runtime;
  - `LS Fer./Fest./Nott./Fest.Nott.` popolati dalle quote extra/straordinario runtime;
  - `Tot Ord.`, `Tot. Str.`, `TOT. ORE`, `Km. AUTO`, `Trasf.` aggiornati in coerenza;
  - `GG.Lav.` = giorni con lavoro ordinario o extra;
  - `GG.Retr.` per gli operai include le giornate di sabato retribuite quando le `38` ore settimanali vengono coperte su `5` giorni, con riporto delle eccedenze tra settimane contigue del mese;
  - fuori dal caso operaio, `GG.Retr.` resta pari a `GG.Lav.` piu eventuali giornate con quota giustificata;
  - `REP. FERIALE/FESTIVA` = conteggio giornate con reperibilita in giorno feriale/festivo;
  - `MA`, `MB`, `IR`, `IB` sono centri di costo legacy non piu usati nel processo HR corrente; nei file storici il popolamento effettivo confluisce in pratica su `MA`;
  - `ASSENZE` = giornate con `absence_minutes > 0`;
  - `B.O. MM.PP`, `B.O. MATURATA`, `B.O. USATA MESE`, `B.O. RESIDUE` non sono gestiti nel file `Giornaliera` secondo il processo HR corrente;
  - nell'export GAIA del template `Giornaliera` questi campi restano quindi a `0` finche non verra modellato il foglio/contatore operativo separato usato dall'HR per la liquidazione.
- pagina `/presenze/export` aggiornata con preview operativa:
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

- dashboard `/presenze`;
- dashboard `/presenze` rifinita come vista macro delle presenze del mese:
  - KPI completi su collaboratori attivi, giornaliere mese, ore ordinarie, extra effettivi;
  - statistiche su assenze, anomalie, KM carburante, giorni speciali;
  - distribuzione causali principali (`ferie`, `permesso`, `malattia`);
  - codici orario / turni prevalenti del mese;
  - sezione finale **`Casi da verificare`** con i casi prioritari del mese estratti dalle giornaliere, pensata come triage rapido per responsabili e operatori prima di entrare nel workspace completo `/presenze/anomalie`;
  - caricamento con paginazione completa delle giornaliere del mese, non piu campione ridotto;
- pagina `/presenze/settings` per gestione credenziali Inaz;
- lista `/presenze/collaboratori`;
- lista `/presenze/collaboratori` con suggerimento automatico di mapping verso utenti GAIA;
- lista `/presenze/collaboratori` con colonna e filtro **Gruppo operai** (`Agrario`, `Catasto / magazzino`, `Non impostato`);
- apertura dettaglio collaboratore in modale embedded dalla lista, con fallback alla pagina completa;
- la lista `/presenze/collaboratori` ricarica subito l'elenco quando il dettaglio embedded notifica modifiche a mapping, profilo contrattuale, assegnazioni template o rettifiche giornaliere, evitando dati stale nella tabella dopo il salvataggio in modale;
- dettaglio `/presenze/collaboratori/[id]` con:
  - cartellino periodo;
  - riepilogo eventi;
  - mapping verso utente GAIA per admin;
  - suggerimento mapping come prima opzione del select, con preselezione automatica se il collaboratore non e ancora collegato;
  - pannello admin **Modifica profilo contrattuale** per correggere `contract_kind`, gruppo operai e standard giornaliero senza passare da seed o migrazioni manuali;
  - prevenzione lato UI e API dell'assegnazione duplicata dello stesso template con identica validita;
  - tab `Cartellino` ottimizzato con sezioni collassabili per `Riepilogo giornata`, `Totali giornata`, `Richieste` e `Anomalie`, con indicatori sintetici nel titolo (`n voci`, preview richiesta singola, stato `errore`) per ridurre l'altezza verticale della modale e rendere piu veloce la lettura dell'elenco giornate;
- pagina `/presenze/giornaliere` rifatta come **cartellino mensile a matrice**:
  - collaboratori in verticale, giorni in orizzontale, con colonna collaboratore e header giorni "sticky";
  - perimetro dati filtrato sul responsabile che ha eseguito la sync (`owner_user_id`);
  - celle colorate per stato (lavorato / assenza / giorno speciale / anomalia) con indicatori compatti `▲` extra, `🚗` KM, `✉` richieste; weekend ombreggiati e giorno corrente evidenziato;
  - dettaglio giornata in **modale** con navigazione `precedente/successivo`, supporto tastiera `Esc`, `←`, `→` e badge stato coerente con l'analisi;
  - il titolo della modale mostra anche il **giorno della settimana**;
  - nella modale il link **"Apri dettaglio collaboratore"** apre in un nuovo tab;
  - nella modale vengono mostrate anche le **timbrature dettaglio Inaz** (`entrata`, `uscita`, terminale se disponibile), usando le righe dettaglio solo quando aggiungono informazione rispetto alle coppie ricostruite o quando c'e una timbratura autorizzata;
  - le timbrature autorizzate da richiesta Inaz `ACC` evidenziano direzione (`ingresso`/`uscita`) e autorizzatore direttamente nella modale giornata;
  - riquadro dedicato **"Aggiungi KM carburante"** + modalita **"Inserisci KM"** che trasforma ogni cella in input rapido con salvataggio automatico al blur;
  - modifica diretta di `KM`, straordinario override, maggior presenza override e nota operativa;
  - evidenza esplicita della **causale Inaz rilevata** (es. ferie / permesso), stato richiesta e autorizzatore nel dettaglio giornata;
  - celle matrice rese piu leggibili per le assenze normalizzate (`ferie`, `permesso`, `malattia`) con etichette e tono distinti;
  - **filtri rapidi per tipo orario / contratto** derivati dal template orario prevalente (`schedule_code`) di ogni collaboratore;
  - selettore mese con **frecce `‹ ›`** per scorrere rapidamente; header riorganizzato su griglia a colonne (mese, ricerca, azioni, filtri, riepilogo mese, legenda);
  - **scroll orizzontale anche via drag** (tieni premuto il tasto sinistro e trascina), con soglia anti-click sulle celle;
  - **popup mese vuoto**: se per il mese non esistono giornaliere, una modal propone di caricare il mese precedente o avviare la sync;
  - **modal scheda collaboratore**: il nome del collaboratore apre una modal sintetica (totali mese + elenco giornate) invece di navigare, con link alla scheda completa;
  - la modal scheda collaboratore e stata estesa con riepilogo operativo mese allineato alla card laterale (`Extra`, `Sabati mese`, causali assenza con ore);
  - nella modal scheda collaboratore gli admin possono modificare il **profilo contrattuale** (`contract_kind`, `operai_group`, `standard_daily_minutes`) senza uscire dal cartellino mensile;
  - l'editor del profilo contrattuale nella modal collaboratore e ora **collassabile**, chiuso di default, con summary compatto e apertura esplicita tramite CTA dedicata per non rubare spazio verticale all'elenco giornate;
  - l'elenco giornate della modal collaboratore mostra data, giorno settimana e stato su colonne fisse, evitando sfalsamenti tra giorni con nomi di lunghezza diversa;
  - dalla modal collaboratore e possibile inserire rapidamente `KM` e reperibilita giornaliera sulle singole giornate, rispettando i permessi e il blocco operativo sulle ferie;
  - se una giornata viene aperta dalla modal collaboratore, la chiusura del dettaglio giornata torna alla modal del collaboratore invece che direttamente alla matrice mensile;
  - il campo **"Cerca collaboratore"** espone una `X` inline che compare solo quando il filtro contiene testo e permette di azzerare la ricerca con un click;
  - il cartellino espone un pannello inline **"Anomalie del mese"** pensato come coda di lavoro operativa, senza dover passare dalla pagina `/presenze/anomalie`;
  - il pannello anomalie mostra KPI sintetici del mese (`giornate nel pannello`, `correggere subito`, `da verificare`, `collaboratori coinvolti`) e una CTA **"Apri la prima giornata critica"** per portare subito l'operatore dentro la modale giorno;
  - il pannello anomalie distingue il linguaggio operativo tra **`Bloccante`** (da correggere subito) e **`Da verificare`** (giornata da confermare), con legenda inline dedicata e microcopy coerente sulle card;
  - il pannello anomalie e la modale giorno esplicitano ora anche la regola operativa sugli extra operai: fino a `3 ore` di extra/straordinario corretto la giornata non entra in anomalia, mentre oltre `3 ore` il caso resta nel flusso operativo;
  - il pannello anomalie supporta filtro rapido per stato (`Tutte`, `Correggere subito`, `Da verificare`) e doppio raggruppamento **per giorno** o **per collaboratore**, con default su **collaboratore** cosi l'operatore apre subito una coda persona-centrica ma puo ancora passare alla vista per data quando serve;
  - ogni card anomalia mantiene l'apertura diretta della modale giornata, ma ora espone anche contesto sintetico utile (`profilo`, `orario`, `minuti mancanti`, `richiesta presente`) per ridurre aperture inutili;
- pagina `/presenze/anomalie` dedicata all'analisi delle giornate da verificare (anomalie, richieste, giorni speciali):
  - nasce dal contenuto della vecchia giornaliere (tabella + pannello rettifiche);
  - resta il workspace principale per la lavorazione completa, mentre la dashboard espone solo il sottoinsieme dei casi piu importanti del mese;
  - scansione automatica degli ultimi mesi e fallback automatico al mese precedente se quello corrente non ha anomalie;
  - voce **"Anomalie"** aggiunta nella sidebar del modulo;
- route `/presenze/import` mantenuta solo come redirect tecnico verso `/presenze/sync`, non piu esposta come flusso operativo utente;
- pagina `/presenze/festivita` dedicata a bootstrap, creazione, modifica e cancellazione festivita Inaz;
- pagina `/presenze/recuperi` per HR/super admin con:
  - saldi per collaboratore;
  - cronologia maturato / fruito / rettifiche;
  - filtri operativi (saldi negativi, pendenti, rettifiche manuali);
  - workflow approvazione / reiezione rettifiche;
  - audit visibile in timeline;
- pagina `/presenze/banca-ore` per HR/super admin con:
  - KPI aggregati su saldo importato, rettifiche approvate, saldo effettivo e liquidato;
  - elenco collaboratori con filtri operativi (ricerca, saldi negativi, pendenti, soli manuali);
  - dettaglio per collaboratore con snapshot Inaz, timeline rettifiche e disponibilita a scarico;
  - esposizione FE del profilo contrattuale risolto (`operaio` / `impiegato` / altro), orario standard giornaliero e giorni equivalenti disponibili;
  - tracciamento della provenienza del profilo (`manuale`, `derivato`, `mancante`) per evidenziare i casi che richiedono completamento HR;
  - summary CCNL del periodo direttamente nel dettaglio banca ore:
    - notturno totale;
    - straordinario diurno / notturno / festivo notturno;
    - conteggio notti del periodo e picco mensile;
    - evidenza soglia Art. 82 con rate `10%` / `15%` quando applicabile;
  - liquidazione guidata nel form HR:
    - proposta automatica dei minuti liquidabili come `min(saldo disponibile, straordinario classificato nel periodo)`;
    - conversione immediata in giorni standard;
    - guardrail espliciti se manca il profilo contrattuale o se il periodo non offre minuti candidabili;
    - scomposizione esplicita in:
      - quota `liquidabile`;
      - quota che `resta in banca ore`;
      - quota `da revisione HR`;
    - policy persistita a DB e gestibile da `/presenze/configurazione`, senza dover intervenire sugli env del backend;
    - storico revisioni della policy con audit su data e operatore che ha applicato la modifica;
  - workflow manuale per `carico`, `scarico`, `liquidazione`, `correzione`;
  - vincolo applicativo che blocca approvazioni o aggiornamenti a saldo negativo oltre la disponibilita maturata;
- pagina `/presenze/export` con download `.xlsm`;
- pagina `/presenze/export` con preview dataset del mese, perimetro collaboratori e KPI di righe/giorni speciali;
- pagina `/presenze/sync` con avvio job live, polling stato, retry e storico run;
- storico `/presenze/sync` con dettaglio espandibile di avanzamento, collaboratore corrente, stato worker e ultimo errore;
- storico `/presenze/sync` hardenizzato lato frontend contro payload `progress` non omogenei:
  - `last_event`, `state`, `error` e collaboratore corrente normalizzati prima del render;
  - evitati runtime error React in presenza di eventi strutturati come oggetti;
- navigazione modulo aggiornata in sidebar e module switcher.
- pagina `/presenze/giornaliere` aggiornata:
  - se la causale normalizzata e `ferie`, `KM carburante` e `Reperibilita giornaliera` sono disabilitati nella modale;
  - il messaggio in modale esplicita il blocco operativo sulle giornate in ferie.

### Sync live

- introdotta tabella `presenze_sync_jobs` per orchestrare le run live;
- aggiunto worker Python separato avviato fuori dal processo FastAPI;
- integrazione con lo scraper esterno `presenze-scraper` tramite worker dedicato;
- login automatico con credenziali cifrate selezionate dal vault `Inaz`;
- ogni run live produce ancora artefatti su filesystem (`json`, `log`, `summary`, `progress`, `events`) per diagnostica;
- il worker salva progressivamente a DB i collaboratori completati, senza aspettare piu l'import finale monolitico;
- collaboratori, giornaliere e summary persistiti portano anche `owner_user_id`, distinto dal mapping `application_user_id` del singolo dipendente;
- il job aggiorna un checkpoint persistito in `presenze_sync_jobs.params_json.checkpoint.completed_employee_codes`;
- il retry riparte dai collaboratori non ancora persistiti, invece di ricominciare da `1/N`;
- il worker espone fasi di avanzamento piu granulari (`opening_timesheet`, `daily_rows_loaded`, `opening_summary`, `summary_loaded`) per rendere piu leggibile lo stato del job;
- il payload `progress.last_event` puo contenere anche eventi strutturati (non solo stringhe) e la UI li gestisce correttamente;
- se il riepilogo eventi di un collaboratore fallisce, la sync non perde piu il collaboratore: prosegue persistendo almeno anagrafica e giornaliere, e registra il warning nel log/event stream;
- retry applicativo disponibile fino al limite configurato;
- schedulazione automatica attiva su cron `06:00 / 12:00 / 18:00`:
  - a ogni slot aggiorna il mese corrente;
  - al primo slot giornaliero aggiorna anche il mese precedente entro una finestra di chiusura iniziale del mese successivo, per recepire rettifiche tardive su Inaz senza triplicare il carico;
- cancel e delete dei job falliti/storici disponibili da UI.

### Test e verifica

- aggiornati test backend `backend/tests/test_presenze_api.py` sul nuovo flusso collaboratori/sync/XLSM;
- aggiornati test backend su festivita tipizzate, recuperi maturati/fruiti e workflow rettifiche HR;
- aggiunti test unitari backend `backend/tests/test_presenze_schedule_engine.py` per:
  - Martedi della Sartiglia e Pasquetta;
  - sabato alternato/scambiato operai catasto, incluso il caso secondo/quarto sabato;
  - rientro del lunedi stagionale;
  - scrittura corretta delle colonne speciali in `Archivio2`;
- aggiunta verifica backend dell'export `.xlsm` su:
  - causale assenza nel blocco corretto di `Archivio2`;
  - metadata riga ereditati dal template;
  - `KM AUTO` esportato dal valore manuale operatore;
- aggiunti test backend sul workflow banca ore:
  - aggregazione snapshot Inaz + rettifiche approvate;
  - blocco di una liquidazione/rettifica che supera il saldo disponibile;
  - esposizione di `contract_kind`, `standard_daily_minutes` e giorni equivalenti nel dashboard/dettaglio banca ore;
  - esposizione del summary CCNL notturno/straordinario nel dettaglio banca ore;
  - proposta di liquidazione guidata nel dettaglio banca ore;
  - instradamento automatico della quota candidata verso `liquidabile` o `revisione HR` in base alla qualita del profilo contrattuale;
- aggiunti test per la precedenza `detail Inaz > template fallback`;
- aggiunti test frontend iniziali `frontend/tests/unit/presenze-pages.test.tsx`;
- aggiunto test frontend sul refresh immediato della lista `/presenze/collaboratori` quando la modale embedded del dettaglio invia `gaia:presenze-collaborator-detail-updated`;
- aggiunti test frontend sul dettaglio collaboratore e preselezione del mapping suggerito in `frontend/tests/unit/presenze-collaboratore-detail.test.tsx`;
- aggiunti test frontend per modifica profilo contrattuale e badge gruppo operai nel dettaglio collaboratore;
- aggiunti test frontend sul `Cartellino` del dettaglio collaboratore per verificare:
  - sezioni compatte espandibili;
  - indicatori sintetici nel titolo dei blocchi;
  - apertura automatica del blocco `Anomalie` in presenza di `detail_error`;
- aggiornati test frontend sul cartellino a matrice in `frontend/tests/unit/presenze-giornaliere-page.test.tsx` (rendering matrice, apertura giornata + salvataggio rettifiche, apertura modal collaboratore, timbrature in modale);
- aggiornati test frontend sul filtro gruppo operai nella lista collaboratori e sulla resa delle timbrature autorizzate Inaz;
- i test frontend `Inaz` oggi coprono esplicitamente:
  - dashboard / pagine principali, inclusa la dashboard macro mese `/presenze`;
  - mapping suggerito collaboratori;
  - workspace giornaliere e modale operativa;
  - dettaglio collaboratore;
  - storico `/presenze/sync` con payload `progress` strutturato e non solo stringhe;
- aggiunti test frontend per la pagina anomalie e gli helper mesi/anomalie in `frontend/tests/unit/presenze-anomalie-page.test.tsx` e `presenze-anomaly-months.test.ts`;
- aggiunto test frontend iniziale sulla pagina `/presenze/banca-ore` con creazione di una liquidazione pendente;
- aggiunto test backend sul filtro per `owner_user_id`, per garantire che un capo settore veda i dati da lui importati anche senza mapping del collaboratore verso `application_users`;
- `docker compose exec -T backend sh -lc 'cd /app && alembic upgrade heads && alembic current'`: ok;
- `pytest backend/tests/test_presenze_api.py tests/test_presenze_schedule_engine.py -q`: ok;
- `pytest --cov=app.modules.presenze --cov-report=term-missing tests/test_presenze_api.py tests/test_presenze_schedule_engine.py`: ok, coverage modulo `presenze` 74.15%;
- `frontend npm run typecheck`: ok;
- `frontend npm run test:unit -- tests/unit/presenze-pages.test.tsx tests/unit/presenze-collaboratore-detail.test.tsx tests/unit/presenze-giornaliere-page.test.tsx tests/unit/presenze-collaborator-mapping.test.ts`: ok (16 test);
- `frontend npm run test:unit -- tests/unit/presenze-collaboratore-detail.test.tsx tests/unit/presenze-giornaliere-page.test.tsx tests/unit/presenze-pages.test.tsx tests/unit/api-request.test.ts`: ok (46 test);
- `frontend VITEST_COVERAGE_INCLUDE='src/app/presenze/collaboratori/[id]/page.tsx,src/app/presenze/giornaliere/page.tsx,src/lib/api.ts' npx vitest run --coverage --coverage.thresholds.lines=0 --coverage.thresholds.functions=0 --coverage.thresholds.statements=0 --coverage.thresholds.branches=0 tests/unit/presenze-collaboratore-detail.test.tsx tests/unit/presenze-giornaliere-page.test.tsx tests/unit/api-request.test.ts`: ok come diagnostica senza gate (33 test); `src/app/presenze/collaboratori/[id]/page.tsx` misura `98.21%` statement / `81.19%` branch / `100%` functions / `98.26%` lines, mentre `src/lib/api.ts` resta basso perche file aggregatore;
- `pytest backend/tests/test_me_router_helpers.py backend/tests/test_presenze_contract_profile.py backend/tests/test_presenze_router_helpers.py -q`: ok (21 test);
- `backend pytest tests/test_me_router_helpers.py tests/test_presenze_contract_profile.py --cov=app.modules.me.router --cov=app.modules.presenze.services.contract_profile --cov-report=term-missing --cov-report=json:coverage.json --cov-fail-under=0 -q`: ok come diagnostica senza gate; `contract_profile.py` al `100%`, `me/router.py` al `31%` perche router aggregatore;
- `frontend npx vitest run`: ok (57 test);
- `frontend npx vitest run --coverage --coverage.include=src/app/presenze/**/*.tsx --coverage.include=src/lib/api.ts --coverage.include=src/types/api.ts tests/unit/presenze-collaboratore-detail.test.tsx tests/unit/presenze-giornaliere-page.test.tsx tests/unit/presenze-pages.test.tsx tests/unit/presenze-anomalie-page.test.tsx tests/unit/presenze-anomaly-months.test.ts`: ok, coverage frontend perimetro Presenze 29.64% statement / 30.15% line;
- `frontend npm run test:unit -- tests/unit/presenze-pages.test.tsx tests/unit/presenze-collaboratore-detail.test.tsx tests/unit/presenze-collaborator-mapping.test.ts`: ok (64 test);
- `frontend VITEST_COVERAGE_INCLUDE='src/app/presenze/collaboratori/page.tsx' npx vitest run --coverage tests/unit/presenze-pages.test.tsx`: ok (29 test), coverage file `src/app/presenze/collaboratori/page.tsx` al 100% statement / branch / functions / lines;
- `frontend npm run test:unit -- tests/unit/presenze-giornaliere-page.test.tsx`: ok (14 test), copre anche editor profilo contrattuale collassabile nella modal collaboratore, pulsante `X` per pulire la ricerca e pannello anomalie inline come coda di lavoro con raggruppamento `giorno/collaboratore` e apertura diretta della giornata;
- `frontend VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx npm run test:coverage -- tests/unit/presenze-giornaliere-page.test.tsx`: ok; il file pagina e marcato `v8 ignore`, quindi il report V8 conferma il gate coverage ma misura `0/0` statement/branch/function/line sulla shell pagina;
- `.venv/bin/pytest backend/tests/test_presenze_api.py -q -k 'gate_presenze' --cov=app.modules.presenze.gate_router --cov-report=term-missing --cov-fail-under=100`: ok, 13 test e coverage `100%` sul router GATE Presenze;
- `.venv/bin/pytest backend/tests/test_presenze_api.py -q`: ok, suite backend Presenze completa;
- `.venv/bin/pytest backend/tests/test_section_permissions.py -q`: ok, 8 test sui permessi/sezioni;
- `frontend npm run test:unit -- tests/unit/presenze-pages.test.tsx`: ok, 44 test;
- `frontend VITEST_COVERAGE_INCLUDE='src/app/presenze/regole/page.tsx' npm run test:coverage -- tests/unit/presenze-pages.test.tsx -t 'presenze rules'`: ok, coverage `100%` statement/branch/functions/lines sulla pagina regole;
- `frontend npm run test:unit -- tests/unit/app-shell.test.tsx`: ok, 3 test inclusa voce sidebar `Regole`;
- `frontend npm run typecheck`: fallisce su debito TypeScript preesistente in `.next/types/app/presenze/*`, `src/app/presenze/collaboratori/[id]/page.tsx`, `src/app/presenze/giornaliere/page.tsx` e fixture test Presenze non allineate ai tipi correnti;
- verifica smoke backend eseguita su parser JSON e compilazione XLSM.

## Gap aperti

- UI frontend ancora essenziale:
  - cartellino mensile a matrice disponibile su `/presenze/giornaliere`, ma manca ancora un calendario per singolo collaboratore nel dettaglio;
  - niente preview differenziale/import duplicati avanzata;
  - niente selector template assistito lato filesystem;
- il profilo contrattuale e ora un dato manuale esplicito del collaboratore, ma manca ancora l'estrazione automatica affidabile da Inaz o da una fonte HR esterna;
- la banca ore e oggi modellata come workflow HR su snapshot/eventi importati `Banca ore*` + rettifiche manuali approvabili:
  - non e ancora stato implementato il contatore storico esterno usato da Carlo per la liquidazione;
  - restano da chiarire le eventuali regole CCNL aggiuntive su maturazione/decadenza oltre ai semplici vincoli di saldo e approvazione;
- la dashboard macro mese e stata arricchita, ma i KPI sono ancora calcolati in frontend da tutte le giornaliere del mese; un endpoint aggregato backend dedicato resta un miglioramento utile per performance;
- la UI dedicata per festivita e recuperi HR e ora presente; restano ancora migliorabili export/report e viste operative avanzate;
- `Trasferte` sono ora esportate se presenti nel record GAIA (`trasferta_minutes`); resta ancora aperta l'estrazione affidabile automatica dal portale Inaz quando il dato non arriva gia strutturato nel payload;
- il tracciato HR legacy di export ha una sola cella giornaliera per `N. ORE TRASFERTA / COMUNE MONTANO (X)`: per questo in export `trasferta_montano` ha priorita sul numero ore, mentre in GAIA i due dati restano distinti;
- `Reperibilita` e oggi strutturata in GAIA (`hours/days/shifts`) e visibile nella preview export, ma il template HR legacy continua ad accettare solo il flag `X`;
- per i dipendenti assenti sia nello storico `Archivio2` sia nel foglio `Operai` del template HR, restano ancora non determinabili automaticamente i metadati anagrafici tecnici (`mansione`, `inquadramento`, testo periodo);
- questi metadati mancanti sono quindi **ancora da implementare** tramite una fonte esterna affidabile (altro archivio GAIA, estensione dello scraper Inaz, oppure tabella manuale di completamento gestita in GAIA);
- sync live ancora minimale:
  - nessuna policy di retry automatica schedulata;
  - nessuna orchestrazione multi-worker;
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
