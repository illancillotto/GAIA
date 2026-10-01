# Buono pasto manuale da GATE — 2026-10-01

Il contratto `GatePresenzeDailyRecordPatchRequest` accetta un booleano esplicito
`meal_voucher_manual`. Null, stringhe e numeri sono respinti. Omettere il campo
mantiene il buono precedente. Gli altri campi e permessi restano compatibili.

Sia il poll outbound (`patch_daily_record`) sia la route LAN
`POST /gate/presenze/giornaliere/{id}/patch` usano
`services/gate_daily_record_patch.py`: lock della giornaliera, audit idempotente
con autore canonico e origine `gate_console_mobile`, commit tramite il confine
esistente. Il campo non viene più ignorato con un ACK privo di effetto.
`services/meal_voucher_audit.py` condivide l'aggiornamento di stato e audit;
la web GAIA mantiene l'origine `gaia_web` e la firma del servizio precedente.

L'export e gli snapshot pubblicano il flag canonico. Manuale OR automatico
vale sempre uno per persona/giorno: revocare il manuale conserva l'automatico.
La migration dei campi è `20261001_1400`, già presente nel repository; nessuna
migration aggiunta dal collegamento GATE.

Test: `test_gate_meal_vouchers.py` copre entrambi i trasporti, valori invalidi,
autenticazione/record mancante, persistenza, audit idempotente, rollback,
compatibilità KM/reperibilità e pubblicazione. La regressione di 9 file pytest
passa: 237 test, 2108 statement e 358 branch nei 7 runtime modificati, 100%,
nessuna riga esclusa. Ruff e format check dei moduli nuovi passano. Anche il ratchet completo
contro `f687c213` passa, senza findings. Il dispatch delle appartenenze e
dei supervisori usa una tabella esplicita dopo la validazione; heartbeat e
transazioni mantengono il comportamento precedente. La regressione aggiuntiva
di questi due runtime passa: 60 test, 288 statement e 108 branch, 100%,
nessuna esclusione. Il dizionario delle anomalie usa lo stesso formato
compatto del builder giornaliere; gli alias e il comportamento non cambiano.

Frontend GAIA non modificato in questa integrazione: il comando è nella
console GATE e usa il dialogo mensile esistente. Contratto, uso e matrice test
sono documentati in GATE: `docs/PRESENZE_MEAL_VOUCHER_ENTRY.md`.

Stato operativo: rilasciato il 2026-10-01. Immagine
`gaia-backend:meal-voucher-ffa557fe`, sorgenti dello stesso commit in
`/opt/gaia/releases/meal-voucher-ffa557fe/backend` per il bind `/app`.
Migration `20261001_1400` applicata. Backup della tabella modificata
`presenze_daily_records` verificato con `pg_restore --list` (289 MB), file
`/opt/gaia/releases/meal-voucher-ffa557fe/presenze-daily-records-pre-deploy.dump`.
Il tentativo di backup integrale, interrotto per gli archivi Catasto, non è
considerato un backup; il dump incompleto è stato rimosso.

Solo backend e `gate-mobile-sync` ricreati, entrambi healthy; gli altri servizi
conservano gli ID precedenti. Checkout remoto e hotfix preservati, checksum
Compose invariati. L'override operativo aggiunto è
`/opt/gaia/docker-compose.meal-voucher.yml`: mantenerlo nei comandi Compose,
insieme a `docker-compose.override.yml` per backend e a
`docker-compose.team-delete.yml` per sync. Non sostituire il bind della release
con quello del checkout remoto durante le operazioni successive.

GATE VPS è alla release `105d9a5`, console
https://static.186.92.233.167.clients.your-server.de/admin .
Schema runtime, colonne e snapshot LAN verificati; settembre contiene 5670
giornaliere con booleano manuale. Lo stesso campo è arrivato nella cache GATE
e un record rappresentativo coincide in lettura. Il ciclo outbound post-deploy è riuscito: avvio 14:52:28 UTC,
conclusione 14:55:30 UTC, senza errore. I 502 del riavvio VPS sono transitori.
Il collaudo operativo su una persona/giornata reale resta separato.


FINAL QUALITY GATE — PASS
