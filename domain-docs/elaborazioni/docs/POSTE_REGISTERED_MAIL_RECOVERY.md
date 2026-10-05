# Recupero dettagli raccomandate Poste

## Job 9 sul CED

Il job 9 e ancora `cancelled` al 2026-09-25 e non si avvia automaticamente. Il suo
checkpoint contiene 437 `archive_ids` univoci e nessun dettaglio. Prima di
riattivarlo, verificare che il worker sul CED usi il codice aggiornato e che il
checkpoint `job-9-scrape-payload.json` sia ancora presente. Il primo avvio
registra la lista degli ID nel payload del job; in seguito la ripresa rifiuta
checkpoint con una lista diversa. Non cancellare il checkpoint durante la
campagna.

## Comportamento del recupero

- Una richiesta Poste per dettaglio usa al massimo un retry immediato in caso
  di timeout, `429` o `5xx`, rispettando `Retry-After` quando presente.
- Dopo due dettagli consecutivi falliti per errore transitorio, la sessione si
  ferma. Il job conserva i dettagli gia acquisiti e riparte dopo 20 minuti.
- Dopo tre cicli automatici incompleti il job passa a `paused` e richiede una
  ripresa esplicita tramite la route `/raccomandate/jobs/{id}/run`.
- Ogni dettaglio deve contenere almeno un destinatario con nome e indirizzo.
  Le risposte prive di dati validi restano tra gli ID mancanti.
- I dettagli acquisiti sono importati in blocchi da 25. La modalita predefinita
  del job aggiorna i dati Poste senza ricalcolare le associazioni agli avvisi;
  un nuovo record rimane da associare.

Monitorare `remaining_ids_count`, `details_scraped`, `scrape_errors`,
`recovery_rounds` e `retry_not_before` nel risultato del job. `succeeded` indica
che tutti gli ID richiesti hanno un dettaglio; `queued_resume` indica una pausa
temporanea; `paused` richiede un intervento manuale. La bonifica dei 493
segnaposto storici e documentata sotto; i 437 residui richiedono ancora il
recupero del dettaglio da Poste. Il job 9 non parte senza un avvio esplicito.

## Bonifica segnaposto del 2026-09-25

L'audit CED ha identificato 493 righe di luglio con `recipient_index=0`,
`missing_recipient` e `destinatario_table_not_found`, senza associazioni agli
avvisi. Per 56 invii esisteva gia un unico dettaglio valido dello stesso ID;
per gli altri 437 non esiste ancora alcun dettaglio valido e gli ID coincidono
esattamente con il checkpoint del job 9.

Le 56 righe obsolete non avevano `subject_id`, pagamento, tracking o riferimenti
da `ruolo_notice_attempts`. Prima della cancellazione e stato salvato un backup
di tutte le colonne sul volume persistente CED:

`/opt/gaia/runtime-data/poste-recovery-backup/placeholder-56-20260925T060332Z.json`

Il file ha permessi `0600`, 56 righe e SHA-256
`e180a224034b7ba0dab3bc019b817ad4049c4da2759ecdab062a2b1090ba8a59`.
La prima prova ORM si e fermata prima del commit per un modello FK non caricato
e ha fatto rollback. La cancellazione successiva, limitata agli ID del backup,
ha confrontato tutte le colonne e i dettagli gemelli nella stessa transazione.
Verifica indipendente dopo il commit: righe Poste `2341 -> 2285`, incomplete
`493 -> 437`, con `avviso_id` `114 -> 114`; i 437 ID residui coincidono con il
checkpoint, job 9 ancora `cancelled`, nessun job Poste attivo. Non sono stati
avviati scrape, import o ricalcoli delle associazioni.

Il worker Poste attualmente sul CED usa ancora il codice precedente (quattro
retry e nessun filtro per i 437 ID). Non avviare il job 9 prima del rilascio
verificato del worker aggiornato e di un canary controllato.

## Recupero isolato dei 437 ID (2026-09-25)

Per evitare il rilascio del worktree non conforme ai gate, e stato avviato sul
CED lo strumento one-off `scripts/poste_recover_missing_recipients.py`, copiato
nel container Poste come `/tmp/poste_recover_missing_recipients.py`. Il job 9
rimane `cancelled`; lo strumento legge soltanto i suoi 437 ID dal checkpoint
immutato, usa il client Poste distribuito con `max_retries=0`, una pausa tra
richieste di 5-10 secondi e una pausa lunga ogni 12 richieste. Dopo due errori
consecutivi termina la sessione. Non associare automaticamente i nuovi dati
agli avvisi.

Il preflight ha verificato tutti i 437 segnaposto e creato un backup integrale
con permessi `0600` in
`/opt/gaia/runtime-data/poste-recovery-backup/poste-recovery-437-backup.json`
(SHA-256 `4426e41b26025f027b3e52161736cd44df98a6146a76f17ecde9394fede8e77c`).
Lo stato riprendibile e in `poste-recovery-437-state.json` nella stessa directory;
il log e in `poste-recovery-437-run.log`, con exit code finale in
`poste-recovery-437-run.exit`. Questi file contengono dati sensibili e non
devono essere copiati nel repository.

Il canary su un ID e riuscito: incomplete `437 -> 436`, associazioni agli
avvisi `114 -> 114`, job 9 sempre `cancelled`. Il recupero degli altri ID e
stato avviato in background; **non considerarlo completato** finche il processo
non e terminato e non sono stati confrontati lo stato, le righe incomplete,
le associazioni e gli errori. Se il circuito si apre, verificare Poste prima
di una ripresa manuale; non cancellare backup, checkpoint o stato.

La prima sessione si e fermata a `233/437` dopo due dettagli consecutivi che
restituivano la pagina di login invece del dettaglio (sessione Poste scaduta,
non HTTP 500). Il 2026-09-25 e stato eseguito un nuovo login e un canary
positivo sull'ID che aveva fallito: `234/437`, incomplete `203`, associazioni
`114`. Il secondo ciclo e stato avviato dal medesimo stato, senza ripetere gli
ID gia completati; log ed exit code sono in `poste-recovery-437-run-2.log` e
`poste-recovery-437-run-2.exit`. La presenza di exit code `0` non prova da sola
il completamento, perche anche l'apertura del circuito termina normalmente:
confrontare sempre `completed_ids`, `errors` e le righe incomplete nel DB.

## Esito del recupero isolato (2026-09-25)

Il secondo ciclo e terminato a `434/437`: due timeout isolati e un dettaglio
con due destinatari. I due timeout sono stati recuperati in un ciclo limitato
a quei due ID. Il dettaglio multi-destinatario e stato verificato senza esporre
dati personali nei log: il parser ha restituito due righe valide con indici
`1` e `2`. Una versione verificata dello strumento ha trasformato il solo
segnaposto indice `0` nel destinatario `1` e inserito il destinatario `2`
nella stessa transazione, senza assegnare avvisi.

Verifica finale indipendente: i 437 ID del checkpoint coincidono esattamente
con i 437 `completed_ids` dello stato; `errors` e vuoto. Il DB contiene 437
invii e 438 righe destinatario per quel set, tutte con nome e indirizzo validi
e senza `avviso_id`. I segnaposto `missing_recipient` residui sono `0`; il
numero complessivo di righe Poste associate ad avvisi e rimasto `114`. Il job
9 e ancora `cancelled` e nessun processo isolato e attivo. Il backup originale
e rimasto integro, SHA-256
`4426e41b26025f027b3e52161736cd44df98a6146a76f17ecde9394fede8e77c`.

La bonifica dei dati destinatario e completa; l'associazione dei nuovi dettagli
agli avvisi e una verifica separata, non eseguita da questo recupero.

## Associazione agli avvisi del 2026-09-28

Eseguito un audit read-only sulle 438 righe destinatario dei 437 ID completati,
usando lo stesso matcher deterministico del codice rilasciato e annualita
`2022, 2023`. Il preflight ha verificato job 9 `cancelled`, stato di recupero
completo senza errori, nessuna associazione manuale e nessuna modifica
concorrente.

L'aggiornamento atomico ha associato 37 righe a un solo avviso compatibile (34
del 2023 e 3 del 2022), lasciato 314 righe in `ambiguous_match` con i candidati
salvati per revisione manuale e 87 in `no_match`. Le 37 associazioni si
aggiungono alle 114 gia presenti: totale `114 -> 151`. Le righe ambigue e senza
match non hanno ricevuto un `avviso_id`.

Prima del commit e stato creato il backup privato
`/opt/gaia/runtime-data/poste-recovery-backup/poste-association-438-20260928.json`
con permessi `0600`, SHA-256
`7a4795afcbdf3b0ee0cf3f515d9f0a57a3d47740db4c9aa8ef55ef4074fcb8af`.

## Verifica pre-rilascio del 2026-09-24

- Worker: `make test-worker` passato. I runtime modificati
  `posta_online_client.py`, `posta_online_sync.py` e `worker.py` hanno ciascuno
  100% statement e branch. La coverage globale worker e 99% per due file
  SISTER non toccati.
- Backend: suite `test_elaborazioni_posta_online.py` e `tests/ruolo` passate con
  100% statement e branch su `schemas.py`, `posta_online_routes.py` e
  `tributi_repositories.py`. Il run richiede il preload del pacchetto reale
  `pypdf` per evitare la collisione tra stub delle due suite.
- Frontend: 12 test del workspace Poste passati con 100% statement, branch,
  funzioni e righe; typecheck passato.
- Rilascio bloccato: il ratchet di complessita contro `origin/main` segnala
  64 finding nella feature Poste e il gate di stile Python 52 finding sui file
  cambiati. Non aggiornare la baseline o distribuire il checkout sporco per
  nasconderli. Nessun commit, deploy o avvio del job 9 eseguito in questa
  verifica.
