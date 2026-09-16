# Dashboard sincronizzazioni

Aggiornamento: 2026-09-16.

La pagina `/elaborazioni` raccoglie 15 servizi in un catalogo responsive,
filtrabile per nome, descrizione e stato (tutti, da verificare, in corso/coda).
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

Le modali dei monitor arrivano a `1472 px` di larghezza e `1035 px` di altezza,
con margine orizzontale minimo di `16 px` per lato e limite al `96%` dell'altezza
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
| Presenze INAZ | client `listPresenzeSyncJobs`, `limit=1` | `/elaborazioni/presenze-sync` |
| SISTER visure | `/elaborazioni/batches` | `/elaborazioni/visure` |
| NAS e directory | `/sync/jobs` | `/nas-control/sync` |
| WhiteCompany | `/elaborazioni/bonifica/sync/status` | `/elaborazioni/bonifica` |
| AUTODOC mezzi | `/operazioni/vehicles/autodoc-sync/status` | `/elaborazioni/autodoc` |
| GAIA Mobile Sync | `/operazioni/mobile-gateway-sync/status` | `/elaborazioni/gaia-mobile-sync` |
| SISTER autosync | `/elaborazioni/ruolo-autosync/status` | `/elaborazioni/autosync` |
| Allineamento AdE | `/catasto/gis/ade-wfs/runs/latest` | `/elaborazioni/ade-alignment` |
| ANPR | `/elaborazioni/utenze-anpr/summary` | `/elaborazioni/anpr` |

Le API applicano le autorizzazioni esistenti. La pagina mantiene il requisito
di accesso al modulo Catasto; una risposta negata di un servizio viene mostrata
nella relativa scheda, senza nascondere le letture riuscite.

## Selezione e significato degli stati

- Capacitas, inCass, Poste, Presenze, visure e NAS mostrano il job con `created_at`
  piu recente fra quelli restituiti. `updated_at` non determina l'ultimo sync:
  l'aggiornamento di un vecchio job non lo rende la sincronizzazione piu recente.
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

## Implementazione e verifiche

- `frontend/src/app/elaborazioni/page.tsx`: composizione, ricerca e riepilogo.
- `frontend/src/lib/sync-dashboard-{model,jobs,services}.ts`: modello, catalogo
  e adattamento delle risposte API.
- `frontend/src/components/elaborazioni/use-sync-dashboard.ts`: caricamento
  indipendente, polling e protezione dalle risposte successive allo smontaggio.
- `sync-service-card.tsx` e `sync-schedules.tsx`: schede e pianificazioni.
- `sync-service-details.tsx` e `sync-dashboard-dialog.tsx`: risultati completi
  e navigazione in modale con caricamento differito dei monitor.

Verifica finale del 2026-09-15: 47 test unitari nelle suite dashboard e
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
