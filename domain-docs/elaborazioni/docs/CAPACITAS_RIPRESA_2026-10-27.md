# Capacitas: diagnosi e ripresa prudente del 27 ottobre 2026

## Diagnosi

Il servizio non era operativo: lo scheduler accodava lavoro, ma mancavano
entrambi gli esecutori.

- `gaia-elaborazioni-worker-runtime` era fermo dall'8 ottobre alle 09:46:06 UTC
  (11:46 italiane), exit 137 e `OOMKilled=false`. Il journal Docker registra
  uno stop esplicito, seguito da SIGKILL dopo 30 secondi di attesa del SIGTERM.
  Non identifica chi abbia richiesto lo stop; non dimostra un esaurimento RAM.
- `gaia-capacitas-full-recovery` era fermo dal 15 ottobre alle 05:22:52 UTC
  (07:22 italiane), exit 1. PostgreSQL era in avvio e rifiutava le connessioni;
  erano stati esauriti i tre tentativi della policy `on-failure:3`.
- La credenziale risultava attiva, senza errori consecutivi. Non sono stati
  modificati password, identita, mapping o finestre di disponibilita.

Alla diagnosi il batch particelle 3268 era `queued_resume`, 41/100 elementi
processati, tutti falliti nel precedente tentativo; irrigue 119 e inCASS 16889
restavano `pending`. Questi numeri descrivono lo stato precedente alla ripresa.

## Profilo applicato

Il profilo usa il trasporto comune esistente, con il medesimo file
`/runtime-data/capacitas/request-policy.json` su backend, scheduler, worker e
campagna. Il mount host condiviso e `/opt/gaia/runtime-data`.

| Parametro | Valore |
| --- | --- |
| Richieste HTTP contemporanee globali | 1, con lock filesystem |
| Pausa minima dopo la risposta completa | 5 secondi |
| Massimo teorico complessivo | 12 richieste/minuto, meno con latenze e pause |
| Cooldown per errori consecutivi | 300, 600, 1200, 2400, 3600 secondi |
| `Retry-After` | prevale anche oltre il massimo del backoff |
| `ELABORAZIONI_CAPACITAS_PARALLEL_WORKERS` | `1` |
| Famiglie riattivate nel runtime | `capacitas` |

Login, redirect e keep-alive consumano lo stesso budget. Il file policy non
viene azzerato: tempi e contatori persistenti restano validi dopo i riavvii.
Registry/NAS resta fuori dal perimetro di questa riattivazione.

## Continuita e isolamento del rilascio

La release operativa e `/opt/gaia/releases/capacitas-resume-20261027` sul CED.
L'override `compose.conservative.json` e aggiunto per ultimo ai riferimenti
Compose dei tre servizi. La campagna separata riceve gli stessi parametri
nella configurazione Docker; non e un servizio del Compose principale.

Backend e scheduler mantengono immagini, command, mount, porte e impostazioni
precedenti, salvo il profilo Capacitas. Il worker deriva dall'immagine
`capacitas-polite-20261007` con un solo predicato aggiunto a
`prepare_incass_sync_jobs_for_recovery`: esclude i job con `recovery_task_key`.
Questa protezione, gia presente nel repository e nel backend, mancava
nell'immagine del worker fermo. La funzione risultante e stata confrontata
tramite AST con quella canonica. L'immagine derivata e
`gaia-elaborazioni-worker-runtime:capacitas-resume-20261027`.
Non sono state distribuite le modifiche Ruolo concorrenti del working tree.

La campagna conserva command `--apply --retry-failed`, directory
`/runtime-data/capacitas-recovery-20261005`, audit identita e manifest.
I task riusciti non vengono cancellati o ripetuti per forzare una ripartenza.
I container precedenti vengono conservati, fermati e rinominati con suffisso
`-before-resume-20261027`; gli inspect e le configurazioni complete di rollback
sono protetti nella directory della release. Non copiarli nei report: contengono
variabili d'ambiente riservate.

Prima della ripresa della campagna e terminato un nuovo `pg_dump` completo
(exit 0, 39.677.008.097 byte, circa 37 GiB) ed e stata salvata una copia
consistente SQLite del manifest. `pg_restore -l` legge 3.067 righe di indice;
questo controllo non equivale a una prova di restore. La sincronizzazione
ordinaria e ripartita durante il dump, che mantiene uno snapshot consistente.

## Verifiche e stato operativo

Backend e scheduler ricreati e healthy con invarianti verificati. Il worker
Capacitas e ripartito alle 07:42:39 UTC, con heartbeat aggiornato e salute
Docker regolare anche al ricontrollo delle 10:47 UTC. Il campionamento iniziale
della policy ha misurato intervalli fra aggiornamenti delle risposte di circa
5,246-6,308 secondi su 28 intervalli, senza nuovi incrementi dei contatori
errori. Il vecchio
contatore SSO pari a 1 e conservato: i login non azzerano quel contatore.

Alle 10:47 UTC quattro batch inCASS ordinari sono `succeeded`: 400 soggetti,
3.930 avvisi sincronizzati e zero soggetti falliti; un ulteriore batch ha
raggiunto 92 soggetti e 949 avvisi senza soggetti falliti. Il batch 16707
conserva un avviso parziale: `succeeded` non certifica tutti i suoi dettagli.
Il batch irrigue 119 e `succeeded`: 100 ricerche, 558 domande aggiornate,
2.057 particelle inserite e zero elementi falliti. Il successivo 120 e in
corso. Le particelle 3268 restano `queued_resume`, dietro i job prioritari
inCASS della stessa corsia: quel recupero non e ancora dimostrato.

La campagna completa e ripartita alle 10:45:19 UTC, dopo il backup, con zero
riavvii al primo ricontrollo. La preparazione del manifest ha aggiunto cinque
nuovi soggetti eleggibili, senza eliminare i successi precedenti. Al controllo
delle 10:51 UTC non risultano ancora nuovi task conclusi nella campagna:
30.361 successi e 10.875 fallimenti storici restano invariati, con 43.529 task
pendenti. Il processo e vivo, senza nuovi errori nei log; l'audit iniziale e
terminato e la connessione DB non attende lock. La campagna condivide il budget
HTTP con i sync ordinari: l'avanzamento dei suoi primi task resta da confermare.
Questo limite non viene nascosto dai successi gia misurati nei sync ordinari. Il watchdog disco e eseguito sul
CED con log e PID nella directory della release; la prima unita systemd user
si fermava alla chiusura della sessione SSH ed e stata sostituita dal processo
persistente, verificato da una connessione successiva.

Sono passati 46 test della policy/sessione, con 100% statement e branch su
`request_policy.py` (104 statement, 14 branch), e tre test pertinenti alla
recovery dei job inCASS: esclusione della campagna separata, ripresa ordinaria
e retry delle credenziali. Non viene dichiarato il 100% dell'intero modulo
inCASS sulla base di questi tre test. La correzione distribuita riusa il
predicato gia versionato, senza introdurre nuovo codice runtime nel repository.

Anche i 57 test del comando full recovery sono superati (un warning runpy
gia noto nel test dell'entrypoint).

Gli import smoke senza rete verificano i valori effettivi `5/300/3600` nelle
quattro immagini/configurazioni. Il grafo codice del worker e aggiornato con
il target dedicato, senza cambi di topologia. Il corpus documentale e
aggiornato con il target elaborazioni e `gpt-6-luna`, verificando il
completamento del chunk semantico e l'assenza di warning di estrazione parziale.

## Monitoraggio e rollback

Controllare insieme salute dei container, heartbeat, aggiornamento dei job e
incremento dei task riusciti nel manifest. `processing` da solo non dimostra
un'importazione sana. Il manifest puo essere letto con SQLite `mode=ro`;
non lanciare una seconda campagna sulla stessa directory. Conservare i log
Docker limitati a tre file da 10 MB e il watchdog disco con soglia 12 GiB.

Per il rollback fermare prima campagna e worker, conservando policy e manifest;
quindi ripristinare i container archiviati e l'elenco precedente degli override.
Riavviare soltanto i servizi precedentemente attivi, salvo nuova decisione di
riprendere il recupero. Il ritorno al worker precedente rimuove anche la
protezione di ownership: non usarlo insieme alla campagna separata.

La campagna non e conclusa. I vecchi errori di sessione e i blocchi d'identita
restano da distinguere dai nuovi risultati; nessuno di questi viene convertito
in successo per la sola riattivazione del processo.
