# Giorni di riposo lavorati con inserimento timbratura in attesa (RIC)

## Problema

Mastrolilli (1395) e Corona (1394) hanno lavorato sabato 29 agosto 2026, orario
`SAB`, con timbrature complete 06:00–12:04 e 06:00–12:00. L'entrata era un
inserimento chiesto dal lavoratore ("Inserimento - 06:00 E") ancora in stato
**RIC**. INAZ non contabilizzava la giornata (ordinario nullo, extra zero).
Senza turno la policy operai non si applica e GAIA copiava i valori INAZ;
`imported_extra or None` rendeva nullo lo zero. La giornaliera e l'export GATE
mostravano un giorno lavorato senza ore, con stato `unknown` e nessuna anomalia.

## Regola

Decisione del responsabile: il dato va esportato anche se la richiesta è ancora
in stato RIC. Nei giorni di riposo (`SAB`, `DOM`, `RIPTURN`) con richiesta di
variazione timbrature in stato RIC, nessun minuto contabilizzato da INAZ, nessuna
rettifica amministrativa e tutte le coppie di timbrature complete, GAIA ricava i
minuti dalle timbrature (`source = pending_punch_request`). Il giorno di riposo è
tutto straordinario: festivo, con la quota prima delle 06:00 festiva notturna,
come INAZ classifica gli altri sabati non programmati lavorati. Appena INAZ
contabilizza la giornata, o esiste una rettifica MPE/STR, prevale quel valore.

La giornaliera GAIA (`effective_extra_values`) e il payload GATE usano gli stessi
minuti. I giorni feriali sono esclusi: una simulazione sui dati di produzione ha
mostrato che su orari senza policy operai (`OPEF0714` di Dessi 1–4/09, `ADD_*` di
Serra) le sole timbrature trasformerebbero l'intera giornata in straordinario.
Quelle giornate restano un problema distinto, non risolto da questa modifica.

## Verifiche

- Commit `03882c8d`, `fab1f3ed`; test `tests/test_presenze_pending_punch_request.py`.
- 417 test Presenze passati; `schedule_engine.py` e `operai_daily_policy.py` al
  100% statement e branch. Ratchet complessità e style gate contro `main` senza finding.
- Simulazione read-only in produzione su 82 record candidati (richiesta RIC,
  INAZ senza minuti): cambiano solo 5 giorni di riposo: 1404 e 162 il 30/05,
  1373 il 26/07, 1394 e 1395 il 29/08. Nessun feriale modificato.

## Rilascio

Immagine overlay `gaia-backend:pending-punch-fab1f3ed` sopra
`gaia-backend:before-pending-punch-fab1f3ed` (= `extra-30828445`, `6725e0ef`).
Stessa procedura del rilascio `extra-30828445`: hash di partenza verificati su
host e container, backup, attesa di una finestra senza importazioni INAZ,
aggiornamento di backend, `gate-mobile-sync` e worker Presenze, health e hash
finali, rollback automatico in caso di errore. Manifest, backup e rollback:
`/opt/gaia/releases/pending-punch-fab1f3ed/`.

Deploy concluso l'11 settembre 2026 alle 11:16:04 UTC, dopo 45 attese per
importazioni INAZ in corso; tre processi healthy con hash verificati. L'API
`mobile-sync` espone 364 minuti festivi per 1395 e 360 per 1394 il 29/08, e i
valori attesi per gli altri tre giorni. GATE ha ricevuto lo snapshot successivo
alle 11:17:24 UTC. Nessuna modifica a timbrature, richieste o dati INAZ.
