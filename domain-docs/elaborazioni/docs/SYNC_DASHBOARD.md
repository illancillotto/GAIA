# Dashboard sincronizzazioni

Aggiornamento: 2026-10-28 (avvisi delle sincronizzazioni nella home admin).

La pagina `/elaborazioni` raccoglie 16 servizi in un catalogo responsive,
filtrabile per nome, descrizione e stato (tutti, da verificare, in corso/coda).
L'ordine iniziale e intenzionale: `SISTER autosync`, `ANPR`, `GAIA Mobile
Sync`, poi gli altri servizi. La priorita resta invariata anche quando le
risposte API arrivano in ordine diverso.
Le card hanno dimensioni uniformi e mostrano stato sintetico, numero di flussi
e ultimo avvio. Gli errori hanno precedenza sullo stato attivo nel riepilogo;
i filtri considerano tutti i flussi, quindi un servizio puo comparire in
entrambi i gruppi. Nessun dettaglio lungo aumenta l'altezza della card.

`Vedi dettagli` apre una modale con avvio/fine, contatori ed errori di ogni
flusso. `Apri monitor` apre il workspace operativo nella stessa pagina.
Pianificazioni, configurazioni e richieste si aprono anch'esse in modale.
Ricerca e filtro restano selezionati alla chiusura. Il dialog gestisce focus,
ciclo Tab/Shift+Tab, Escape, blocco dello scroll e ritorno al pulsante iniziale.
I monitor nativi sono riutilizzati tramite `NativeWorkspaceRenderer`; quelli
non nativi conservano il fallback iframe esistente. API, permessi e azioni
operative dei monitor restano invariati.

Le modali dei monitor arrivano a `1600 px` di larghezza e `1035 px` di altezza,
con margine orizzontale minimo di `8 px` per lato e limite al `96%` dell'altezza
visibile. Il contenuto e gli iframe utilizzano l'altezza residua sotto la
testata; dettagli e pianificazioni restano compatti.

## Catalogo e sorgenti

I percorsi API seguenti sono relativi al prefisso `/api`.

| Servizio | Sorgente | Monitor |
| --- | --- | --- |
| Capacitas domande irrigue | `/elaborazioni/capacitas/involture/domande-irrigue/jobs` | `/catasto/domande-irrigue` |
| Capacitas anagrafica | `/elaborazioni/capacitas/involture/anagrafica/storico/jobs` | `/elaborazioni/capacitas?section=storico` |
| Capacitas terreni | `/elaborazioni/capacitas/involture/terreni/jobs` | `/elaborazioni/capacitas?section=terreni` |
| Capacitas particelle | `/elaborazioni/capacitas/involture/particelle/jobs` | `/elaborazioni/capacitas` |
| Capacitas inCass | `/elaborazioni/capacitas/incass/avvisi/jobs?limit=1` | `/elaborazioni/capacitas?section=incass` |
| Poste Online | `/elaborazioni/posta-online/raccomandate/jobs` | `/elaborazioni/posta-online` |
| STEP riscossione | `/elaborazioni/step/jobs` (super admin) | `/elaborazioni/step` |
| Presenze INAZ | client `listPresenzeSyncJobs`, `limit=1` | `/elaborazioni/presenze-sync` |
| SISTER visure | `/elaborazioni/batches` | `/elaborazioni/sister` |
| NAS e directory | `/sync/jobs` | `/nas-control/sync` |
| WhiteCompany | `/elaborazioni/bonifica/sync/status` | `/elaborazioni/bonifica` |
| AUTODOC mezzi | `/operazioni/vehicles/autodoc-sync/status` | `/elaborazioni/autodoc` |
| GAIA Mobile Sync | `/operazioni/mobile-gateway-sync/status` | `/elaborazioni/gaia-mobile-sync` |
| SISTER autosync | `/elaborazioni/ruolo-autosync/status` | `/elaborazioni/sister` |
| Allineamento AdE | `/catasto/gis/ade-wfs/runs/latest` | `/elaborazioni/ade-alignment` |
| ANPR | `/elaborazioni/utenze-anpr/summary` | `/elaborazioni/anpr` |

Le API applicano le autorizzazioni esistenti. La pagina mantiene il requisito
di accesso al modulo Catasto; una risposta negata di un servizio viene mostrata
nella relativa scheda, senza nascondere le letture riuscite.

I due servizi SISTER condividono il workspace canonico `/elaborazioni/sister`.
Nel pool AutoSync ogni credenziale occupa una riga, con intestazione compatta
e fasce settimanali a tutta larghezza. `Sempre disponibile` sospende il vincolo
orario conservando le fasce; `Fasce personalizzate` le riattiva.
`Applica fuori orario ufficio` ripristina il preset e attiva il vincolo in un
solo passaggio. Le modifiche si persistono con `Salva configurazione`.
La vista iniziale contiene AutoSync, richieste e batch recenti; `Stato portale`
apre `/elaborazioni/sister?view=health` ed e disponibile agli admin e agli
utenti con accesso Catasto. Le vecchie route UI `visure`, `autosync` e
`portal-health` restano redirect compatibili; gli endpoint API Portal Health
non cambiano.

## Selezione e significato degli stati

- Capacitas, inCass, Poste, Presenze, visure e NAS mostrano il job con `created_at`
  piu recente fra quelli restituiti. `updated_at` non determina l'ultimo sync:
  l'aggiornamento di un vecchio job non lo rende la sincronizzazione piu recente.
- Gli endpoint job sono normalizzati sia nella forma lista canonica sia
  nell'envelope `{ items: [...] }`; una risposta nulla o non iterabile viene
  trattata come nessuna esecuzione e non genera l'errore JavaScript `is not
  iterable` nella modale dettagli.
- InCass richiede esplicitamente `limit=1`; nessuno storico viene renderizzato
  nella sua scheda. Le altre schede Capacitas applicano la selezione lato client.
- WhiteCompany mostra l'ultimo stato di ogni entity. AUTODOC, Mobile e AdE
  utilizzano il rispettivo stato corrente/ultimo run.
- SISTER autosync privilegia `running_batch`, poi `last_batch`; include
  abilitazione del planner, eventuale errore di pianificazione e il totale delle
  visure completate nelle 24 ore rappresentate da `dashboard.hourly`.
- ANPR seleziona l'ultimo `started_at` e mostra chiamate odierne/limite e totale
  dei deceduti trovati; il totale usa `0` come fallback per risposte legacy.
- `In esecuzione / coda` conta i servizi con almeno uno stato mostrato attivo:
  non e il censimento di tutti i job pendenti nel database.
- `Da verificare` conta errori di lettura, errori espliciti degli snapshot e
  stati falliti, parziali o saltati. Non somma i contatori numerici dei record.
- Date assenti sono `Non disponibile`; un elenco vuoto e `Nessuna
  sincronizzazione registrata`. AdE risponde 404 in assenza di run; gli altri
  errori di lettura restano visibili.

## Aggiornamento e pianificazioni

Le letture partono al caricamento, al ritorno in primo piano e ogni 30 secondi
a pagina visibile, anche quando non risultano job attivi. `Aggiorna ora` usa lo
stesso percorso. Non partono cicli concorrenti; ogni risposta aggiorna solo il
proprio servizio. Una lettura fallita rimuove gli snapshot di quella scheda,
evitando che dati precedenti appaiano aggiornati. `Dati letti` indica l'istante
di acquisizione dello stato, distinto dalle date del job.

`Pianificazioni automatiche` carica i controlli all'apertura della modale. I pulsanti
attivano/disattivano il singolo controllo tramite l'API esistente e rileggono
l'elenco dopo il salvataggio. L'aggiornamento degli stati non modifica
schedulazioni e non avvia job. La configurazione Mobile incompleta viene
segnalata anche quando non esiste ancora un run.

## Toast nella home degli amministratori

La home `/` mostra un toast accessibile (`role="alert"`) solo ai ruoli
`admin` e `super_admin`. La lettura parte quando la sessione e pronta e si
ripete ogni 30 secondi a scheda visibile, anche al ritorno in primo piano.
Ogni richiesta scade dopo 15 secondi e non si sovrappone alla precedente.
Fuori dalla home o per utenti non amministratori non partono queste richieste.

La sorgente e `GET /elaborazioni/sync-alerts` (prefisso pubblico `/api`), con
protezione backend `require_admin_user`. La risposta e una lista di
`{ id, service, message }`: non espone errori grezzi, nominativi, credenziali,
cookie o payload di scraping. Questa autorizzazione riguarda soltanto gli
avvisi; le azioni e i workspace operativi mantengono i permessi preesistenti.
Gli admin possono quindi ricevere gli avvisi senza ottenere accesso ai monitor
riservati ai super admin.

Il riepilogo legge dal database gli stessi 16 servizi del catalogo. Per ogni
sorgente considera l'ultimo job secondo `created_at` (oppure `started_at` per
WhiteCompany, AUTODOC, Mobile, AdE e ANPR), con ID decrescente a parita di data.
WhiteCompany mantiene distinti i flussi per entity e separa AUTODOC; SISTER
separa batch manuali e autosync e considera l'ultima esecuzione per proprietario.
Un successo successivo sostituisce il fallimento precedente nello stesso flusso.

Generano un avviso gli stati terminali `failed`, `error`, `cancelled`, `partial`
e `completed_with_errors`. Job assenti, attivi, in coda, completati con successo
o `skipped` non generano un allarme per il solo stato. I contatori storici di
errori e il metadato aggregato INAZ `degraded` non sono usati come prova di
interruzione del servizio. Si aggiungono controlli espliciti per:

- INAZ: pianificazione abilitata con credenziale mancante o disattivata;
- INAZ: job `running` con lease del worker scaduto;
- SISTER autosync: errore registrato nel planner, anche se il planner e stato
  disabilitato dopo il problema.

La lettura e priva di scritture e chiamate ai portali esterni. Non e un health
check Docker e non deduce un blocco dalla sola durata di un job: per i servizi
senza lease non rileva un processo morto finche il loro stato persistito non
segnala il problema. Per INAZ il riepilogo dei job considera l'ultimo job,
non ricostruisce la completezza di tutti gli shard di una campagna. Questi
avvisi non sostituiscono gli audit di completezza o i monitor infrastrutturali.

Il toast elenca i servizi interessati e resta visibile fino alla chiusura o al
recupero. E collocato sopra il pulsante dell'assistente Wiki, con priorita
visiva sufficiente a mantenere raggiungibile `Chiudi` anche su mobile.
`Chiudi` silenzia gli ID correnti durante quella permanenza nella
home: lo stesso problema non ricompare a ogni polling. Un nuovo incidente
oppure la ricomparsa dopo un controllo sano genera un nuovo avviso. Tornare
nella home o cambiare sessione ricrea il monitor e ripresenta i problemi attivi.
Le risposte di una sessione precedente non aggiornano il monitor corrente.

Se il riepilogo non e leggibile, il toast mostra `Monitor sincronizzazioni:
Stato non disponibile` e conserva gli incidenti gia noti; il successo seguente
riconcilia l'elenco. Una risposta 401/403 rimuove gli avvisi. La chiusura del
toast non modifica la configurazione o lo stato di alcun servizio.

## Implementazione e verifiche

- `frontend/src/app/elaborazioni/page.tsx`: composizione, ricerca e riepilogo.
- `frontend/src/lib/sync-dashboard-{model,jobs,services}.ts`: modello, catalogo
  e adattamento delle risposte API.
- `frontend/src/components/elaborazioni/use-sync-dashboard.ts`: caricamento
  indipendente, polling e protezione dalle risposte successive allo smontaggio.
- `sync-service-card.tsx` e `sync-schedules.tsx`: schede e pianificazioni.
- `sync-service-details.tsx` e `sync-dashboard-dialog.tsx`: risultati completi
  e navigazione in modale con caricamento differito dei monitor.
- `backend/app/modules/elaborazioni/sync_alerts.py`: riepilogo read-only e
  endpoint riservato agli amministratori per la home.
- `frontend/src/components/elaborazioni/home-sync-alerts.tsx`: controllo della
  route/sessione, polling e toast; integrato in `frontend/src/app/layout.tsx`.

I test `backend/tests/test_elaborazioni_sync_alerts.py` verificano ogni sorgente
del catalogo, permessi reali, recupero, separazione dei flussi e assenza di
scritture o dati sensibili nella risposta. Le suite frontend
`home-sync-alerts.test.tsx` e `root-layout.test.tsx` verificano composizione,
ruoli, polling, errori di lettura, chiusura, recupero e cambio di sessione.
I file runtime del toast e del relativo endpoint richiedono coverage full-file
al 100%, inclusi branch; non vengono modificate le policy o le soglie esistenti.

Verifica locale del 2026-10-28 per il toast: 40 test backend della feature e
5 regressioni Portal Health, 23 test frontend della feature e 45 regressioni
home/dashboard, tutti superati. Coverage full-file dei quattro runtime
modificati: backend statement `75/75` e branch `6/6`; frontend statement
`51/51`, branch `22/22`, funzioni `16/16`, righe `38/38`, tutto `100%`.
TypeScript, Ruff, ESLint sui file toccati e build produzione passano; la build
mantiene warning su file fuori perimetro. Tre test Chromium sulla build locale
con API simulate verificano desktop 1440px, mobile 390px e assenza di letture
per un operatore, inclusi chiusura, polling, nuovo incidente e mancata
sovrapposizione con il pulsante Wiki. Questo collaudo non e un deploy su GAIA.

Il report di complessita del perimetro rileva zero violation: massimo nuovo
cognitive `14`, cyclomatic `9`, LOC `49`; `RootLayout` mantiene cognitive `0`,
cyclomatic `1`, LOC `14`. Il ratchet usa la baseline del merge-base `main`,
senza modificare soglie o esclusioni. La sincronizzazione esplicita della
baseline usa Python 3.14, coerente con il motore gia registrato: oltre ai
quattro runtime della feature riallinea sette record file Ruolo relativi a
codice gia committato, senza modificarlo. Non introduce nuovo debito.

Rilascio sul CED del 2026-10-29 alle 10:16: release
`sync-alerts-20261029-09ec7751`, solo backend e frontend, senza migration.

- **Immagine backend appiattita.** L'immagine attiva aveva 127 layer, il
  limite di overlay. Il candidato copia il suo filesystem in un solo layer,
  con la stessa configurazione, poi aggiunge i file della feature. Contenuti,
  permessi e proprietari coincidono con l'immagine precedente, esclusi i file
  della feature; il candidato ha 3 layer.
- **Verifiche.**
  - Nell'immagine candidata: 40 test superati, build frontend riuscita,
    Compose cambia solo l'immagine.
  - Dopo il rilascio: home, pagina Poste e `gaia.lan` HTTP 200; senza login
    gli avvisi e i lotti Poste rispondono HTTP 401; gli altri servizi sono
    invariati.
  - Lettura in produzione: 11 avvisi attivi, su GAIA Mobile Sync, NAS e
    directory, Poste Online, SISTER visure e WhiteCompany.
- **Ripristino.** `/opt/gaia/releases/sync-alerts-20261029-09ec7751/rollback.sh`.

Verifica finale del 2026-09-16: 23 test unitari nella suite dashboard,
coverage full-file dei runtime modificati al `100%` (statement `83/83`, branch
`99/99`, funzioni `28/28`, righe `60/60`). I test caratterizzano l'ordine delle
prime tre card e le risposte lista/envelope/non iterabili. La suite E2E esegue
2 test Chromium su 1440px e 390px, sia sul sorgente locale sia su `gaia.lan`,
con API simulate, senza pageerror.

Verifica precedente del 2026-09-15: 47 test unitari nelle suite dashboard e
workspace, con coverage full-file sui 10 runtime della dashboard e delle
modali: statement `296/296`, branch `238/238`, funzioni `93/93`, righe
`246/246`, tutto `100%`. Sono inclusi hook di polling, modello e adattatori
dei servizi. Le soglie e il perimetro di policy non sono stati modificati.

La suite `frontend/tests/e2e/elaborazioni-dashboard.spec.ts` verifica desktop
1440px e mobile 390px, catalogo di 15 servizi, ultimo inCass, errori isolati,
ricerca, uniformita delle card, apertura monitor in modale, tastiera, ripristino
del focus e assenza di overflow/pageerror con API simulate.

TypeScript, ESLint e ratchet sul diff passano. La baseline globale della
complessita resta non riproducibile per debito preesistente fuori perimetro;
non viene aggiornata per assorbire quelle regressioni.
