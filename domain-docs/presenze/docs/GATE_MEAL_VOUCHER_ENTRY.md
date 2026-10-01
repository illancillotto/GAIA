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
nessuna riga esclusa. Ruff, format check dei moduli nuovi e ratchet del dominio
contro `f687c213` passano. Il dizionario delle anomalie usa lo stesso formato
compatto del builder giornaliere; gli alias e il comportamento non cambiano.

Frontend GAIA non modificato in questa integrazione: il comando è nella
console GATE e usa il dialogo mensile esistente. Contratto, uso e matrice test
sono documentati in GATE: `docs/PRESENZE_MEAL_VOUCHER_ENTRY.md`.

Stato operativo: deploy in preparazione, da verificare dopo backup DB,
migration `20261001_1400`, aggiornamento backend e servizio `gate-mobile-sync`.
Preservare il checkout remoto e le hotfix preesistenti; aggiornare solo le
immagini dei due servizi. Il collaudo su una persona reale resta separato.
