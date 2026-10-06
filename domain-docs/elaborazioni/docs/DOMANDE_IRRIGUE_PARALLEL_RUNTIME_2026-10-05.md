# Domande irrigue: corsia runtime indipendente

## Aggiornamento: pool da quattro

Su richiesta successiva il runtime usa
`ELABORAZIONI_RUNTIME_PARALLEL_WORKERS=4` (intervallo ammesso 1-4).

- Domande: un job e un cursore, quattro sessioni HTTP indipendenti per ricerca
  anagrafica e recupero contesti. Prefetch limitato e consumo ordinato;
  deduplicazione comune prima dei contesti e persistenza seriale tramite il
  coordinatore esistente. Discordanze di ricerca/contesto falliscono chiuse.
- Altri Capacitas: quattro slot di esecuzione di job. inCASS con insiemi di
  soggetti disgiunti puo procedere contemporaneamente; sovrapposizioni e
  selezioni senza scope attendono. Le selezioni dinamiche vengono congelate
  prima dell'esecuzione. Storico anagrafica protegge lo stesso namespace dei
  soggetti. Terreni/particelle condividono una protezione conservativa del
  catalogo: i loro job non vengono sovrapposti. Il parallelismo interno gia
  previsto da questi job non viene elevato oltre il limite esistente di due.
- NAS: quattro thread con sessioni DB e connector SSH distinti recuperano i
  metadati; il coordinatore REGISTRY originale continua a persistere in ordine.
  Resume esclude i soggetti gia completati e il buffer resta limitato.

Questa configurazione non dichiara quattro scritture contemporanee su ciascun
dominio: cataloghi condivisi e persistenza sono deliberatamente coordinati.
Il gate di conflitto opera nel singolo runtime; non autorizza repliche del
container o lanci indipendenti degli stessi job. Il recovery resta singolo
prima dell'avvio dei task; heartbeat aggiorna anche i job che attendono il
gate, evitando scadenze artificiali.

Test dei cinque runtime nuovi/modificati: statement e branch al 100%, zero
esclusioni. Suite worker/runner: 43 test; suite backend mirata con scheduler,
scraper e runtime precedenti: 61 test. Ruff/formatter mirati e ratchet contro
merge-base `9bc764e2` passano; baseline invariata, nessun errore di complessita.
Il lint globale resta bloccato dalla violation UP038 concorrente in inCASS.

Prova live senza scritture: quattro sessioni simultanee della credenziale 1,
quattro ricerche anagrafiche e quattro contesti domande, zero errori. Non
certifica throughput di una notte o assenza di throttling prolungato.

Nuova immagine isolata `gaia-elaborazioni-worker-runtime:irrigue-four-20261005`,
derivata dal primo hotfix; aggiunge solo i cinque runtime della change.
Override `/opt/gaia/hotfixes/irrigue-four-20261005/compose.override.yml` da
aggiungere dopo gli override documentati sotto. Non ricreare backend o
scheduler per questo aggiornamento; la finestra domande resta 18:00-07:00.
Rollback: togliere solo l'ultimo override e ricreare il runtime; mantenere il
pin backend e il primo override irrigue. Monitorare errori di sessione,
fallimenti, durata del chunk e attese prima di aumentare il carico.

## Problema e comportamento

Audit produzione del 2026-10-05: 107.305 domande presenti, 5.200 identificatori
percorsi dall'autosync su 11.566, 6.366 ancora da percorrere. Il job 57 ha
completato 100 ricerche e 926 domande senza errori alle 06:12 Europe/Rome,
dopo quasi dieci ore in coda. La scansione storica di agosto aveva invece
percorso tutti i CF, ma terminato con errore di anno: questi numeri misurano
il refresh automatico, non domande sicuramente assenti da GAIA.

`elaborazioni-worker-runtime` usa ora `runtime_runner.py`, che esegue nello
stesso processo tre corsie asincrone indipendenti:

- domande irrigue: un job per volta;
- altre elaborazioni Capacitas: storico anagrafica, inCASS, terreni e particelle,
  conservando priorita manuali e ordine di selezione esistenti;
- famiglie residue del worker, normalmente REGISTRY/NAS.

Le domande non attendono piu la conclusione di un job inCASS o particelle.
Ogni elaborazione mantiene le proprie sessioni HTTP e database. Il claim usa
il metodo esistente con `FOR UPDATE SKIP LOCKED`; checkpoint, persistenza,
deduplicazione e cursore dello scheduler restano quelli esistenti.
Non sono avviati piu job domande contemporanei: la velocizzazione rimuove
l'attesa fra servizi senza introdurre cursori concorrenti.

## Orario e arresto

Configurazione effettiva su backend, scheduler e runtime:

```dotenv
CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_START_HOUR=18
CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_END_HOUR=7
CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_TIMEZONE=Europe/Rome
CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_INTERVAL_MINUTES=10
CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_CHUNK_SIZE=100
```

La finestra include le 18:00 ed esclude le 07:00, anche al cambio ora legale.
Fuori finestra la corsia non preleva job automatici domande; le richieste
manuali conservano il comportamento esistente. Un job gia avviato viene
lasciato terminare. SIGTERM ferma nuovi claim tramite lo stato condiviso del
worker; TaskGroup cancella le altre corsie se una termina con eccezione.
Il recupero Capacitas avviene una volta prima dell'avvio delle corsie;
REGISTRY conserva il recupero del worker originale.

## Validazione

- Test di concorrenza con barriera: tutte e tre le corsie entrano prima di
  completare, senza serializzazione accidentale.
- Test su isolamento dei modelli, priorita manuale, attesa, arresto,
  cancellazione in caso di errore, recovery singolo e heartbeat.
- Confini orari verificati in Europe/Rome, con ora legale e ora solare.
- Coverage full-file del nuovo runtime: 100% statement e branch, nessuna
  esclusione. Suite nuova e runner originale: 18 test.
- Ratchet mirato contro merge-base `9bc764e2`: nessun finding. Nuovo file:
  quattro callable, massimo cognitive 16/cyclomatic 9, un warning cognitivo
  sotto soglia di errore. Nessuna baseline aggiornata.
- Ruff e formatter dei nuovi file verificati. Il lint globale rileva una
  violation UP038 in `elaborazioni_capacitas_incass.py`, modifica concorrente
  fuori perimetro; non corretta da questa change.
- Graphify worker aggiornato tramite target dedicato.

## Attivazione produzione

Hotfix isolato in `/opt/gaia/hotfixes/irrigue-parallel-20261005/`: immagine
`gaia-elaborazioni-worker-runtime:irrigue-parallel-20261005`, derivata
dall'immagine runtime attiva `incass-ruolo-20261001` e con il solo nuovo runner.
Conservare l'override inCASS esistente e aggiungere quello irrigue:

```bash
docker compose -f docker-compose.yml \
  -f hotfixes/incass-ruolo-20261001/compose.override.yml \
  -f hotfixes/irrigue-parallel-20261005/compose.override.yml \
  --env-file .env up -d --no-build --no-deps \
  elaborazioni-worker-runtime platform-scheduler backend
```

Le due variabili orarie sono aggiornate in `.env` e `.env.production`, anche
nel checkout locale. La copia precedente resta nel file protetto `env.before`
del hotfix. Il compose versionato punta al nuovo runner per i build successivi.

Nel rollout la ricreazione del backend ha selezionato il vecchio tag `latest`
del Compose base, incompatibile con la revisione DB `20261005_1500`. Ripristino
immediato tramite pin dell'immagine gia disponibile
`gaia-backend:turnisti-open-ended-44b0c4ac`; backend tornato healthy e `/health`
200. Per futuri rollout conservare questo pin finche il tag standard non e
riallineato. Non sono state modificate migrazioni o versioni nel database.

Backend, scheduler e runtime risultano healthy dopo il rollout. Il precedente
job particelle 3069 era gia terminato prima del riavvio, quindi non e stato
interrotto. Credenziale 1 attiva con zero fallimenti consecutivi. Il rollout e
stato verificato fuori finestra: il primo nuovo job automatico domande va
controllato dalle 18:00, con il normale tick dello scheduler entro dieci minuti.

## Monitoraggio e rollback

Verificare log `Corsia Capacitas domande_irrigue`, tempo fra creazione e avvio,
`failed_items`, completamento dei chunk e avanzamento del cursore. La durata
di un giro va misurata: non e garantita dal numero di corsie e dipende dal
portale e dalle sessioni concorrenti. Le anomalie pregresse e i collegamenti
anagrafici mancanti restano attivita distinte.

Per rollback runtime ripristinare immagine e comando precedenti, mantenendo
il pin backend aggiornato. Ripristinare solo le due variabili orarie se
necessario, senza sovrascrivere altri aggiornamenti successivi di `.env`.
Il recovery esistente riprende i job in coda; non azzerare il cursore.
