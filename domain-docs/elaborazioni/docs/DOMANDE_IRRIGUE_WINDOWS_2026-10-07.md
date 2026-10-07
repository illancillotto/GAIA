# Domande irrigue: finestre separate e stima del throughput

## Configurazione

Su richiesta del 7 ottobre, le finestre sono `05:00-07:30,17:00-19:00`
in `Europe/Rome`: complessivamente 270 minuti al giorno. Il nuovo parametro
`CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_WINDOWS` prevale sui precedenti start/end
hour. Se vuoto mantiene la configurazione legacy; disabilitando il gate orario
si mantiene l'esecuzione senza finestra. Gli estremi iniziali sono inclusi,
quelli finali esclusi, al secondo. Il cambio fra ora solare e legale usa sempre
il fuso locale. I job gia avviati terminano anche oltre la fine della finestra.

Il tick passa da dieci a un minuto, con un solo scheduler (`max_instances=1`)
e senza aggiungere job se ce n'e uno attivo. Chunk di 100 CF, quattro sessioni
HTTP indipendenti con prefetch ordinato e persistenza seriale. Non si avviano
quattro job domande indipendenti: l'attuale stato ha un solo cursore e un solo
job pendente. Per quella variante serve una coda di blocchi disgiunti prenotati
atomicamente e un checkpoint aggregato, non una replica del worker corrente.

Il cursore viene preservato fra finestre e giornate. `processed_identifiers`
misura il ciclo giornaliero e puo azzerarsi al cambio `cycle_key`; non equivale
al totale storico percorso. Nessuna migrazione, modifica dei dati o reset del
cursore e incluso nel cambio delle finestre. Una credenziale disabilitata resta
disabilitata: il nuovo orario non risolve automaticamente i guasti Capacitas.

## Stima misurata

I sette job domande riusciti dal job 82 al 97 hanno elaborato 100 ricerche
ciascuno. Durate: 5,93; 22,83; 20,88; 20,79; 23,92; 24,38; 25,38 minuti.
Media 20,59 minuti per chunk, con quattro sessioni gia attive. Non moltiplicare
questa velocita per quattro una seconda volta. Il campione piccolo e la
variabilita dei contesti non consentono un SLA.

Con 270 minuti disponibili e fino a un minuto d'attesa fra chunk: previsione
operativa di circa 10-13 chunk, ovvero 1.000-1.300 CF/giorno, se Capacitas
rimane disponibile. La media ideale suggerisce circa 1.250 CF/giorno; nessuna
stima e valida durante il disservizio o con credenziale inattiva. Il numero di
domande importate non e proporzionale al numero di CF e non e stimabile da
questo campione. La minore attesa non accelera le singole richieste HTTP.

Audit del 7 ottobre: 11.566 CF validi totali e 5.166 oltre il cursore corrente,
circa 4-6 giornate sane per il residuo e 9-12 per un giro completo. Il residuo
misura il refresh da eseguire, non domande sicuramente mancanti. Alla verifica
la credenziale 1 era inattiva e nessun job Capacitas era in lavorazione.

## Validazione e rollout

38 test scheduler/finestre: statement e branch al 100% nei tre runtime
modificati/nuovi, zero esclusioni aggiunte. Confini alle 05:00, 07:30, 17:00,
19:00; minuti/secondi, ora legale/solare, fallback legacy anche overnight,
validazione degli orari e persistenza del progresso tra chunk. Ratchet mirato
contro `703f8411`: zero findings, baseline invariata. `_window_context` passa
da cognitive/cyclomatic 10/10 a 5/6; il valutatore delle finestre e 15/8.
Questa e una feature, non una riduzione del debito: il nuovo valutatore
introduce la responsabilita di piu finestre senza violazioni error-level.

Hotfix isolato `/opt/gaia/hotfixes/irrigue-windows-20261007` con tre immagini
derivate dalle immagini effettive di runtime, scheduler e backend. Cambiano
soltanto settings, valutatore delle finestre e scheduler domande. L'override
va aggiunto dopo `incass-ruolo-20261001`, `irrigue-parallel-20261005` e
`irrigue-four-20261005`. Conservare il pin backend compatibile con le migrazioni,
non ricreare dal solo Compose base e non riallineare `latest`.

Rollback: rimuovere solo l'ultimo override e ricreare backend, scheduler e
runtime con gli override precedenti. Non modificare credenziali o cursore.
