# SISTER: deploy mirato sul CED

## Rilascio

- Autorizzato dall'utente dopo la verifica operativa in sola lettura.
- Commit runtime: 7d5aa2db; servizio elaborazioni-worker-visure.
- Completato il 2026-10-05 alle 16:14:44 Europe/Rome (14:14:44 UTC).
- Immagine: gaia-elaborazioni-worker-visure:sister-7d5aa2db.
- Digest immagine: sha256:828866450855c3402a244d212246ebbd7b4faf26efc1759687e41f63bf8e7dbf.
- Worker precedente arrestato con SIGTERM e finestra di 180 secondi: exit 0.
- Nuovo container running/healthy; nessun altro container ricreato.

## Perimetro e verifiche

L'immagine deriva dall'immagine effettivamente attiva sul CED e sostituisce
soltanto sister_exceptions.py, sister_request_rows.py e
sister_requests_navigation.py con le versioni del commit. Dipendenze, backend,
account, calendari e servizi estranei non sono aggiornati.
Le tre sorgenti corrispondenti in /opt/gaia sono state sincronizzate dopo
l'arresto, conservando copie precedenti per rollback.

Il Compose generale del CED espone bind mount delle sorgenti non presenti nel
container attivo: per non introdurre variazioni di configurazione, il deploy
usa un manifest dedicato ricostruito dalla configurazione runtime effettiva.
Ambiente, comando, healthcheck, rete, volumi, DNS, limiti CPU/RAM/PID e policy
di restart/logging sono stati confrontati prima e dopo: invariati.
L'alias locale latest punta ora alla nuova immagine; la precedente e conservata.

Prima del cambio, sull'immagine candidata e senza accesso di rete:
71 test superati (parser, navigazione, DOM e failure terminale), import del
worker e pip check superati. Il primo tentativo di raccolta DOM richiedeva
browser_test_support.py nel mount di verifica: aggiunto il supporto esistente
e rieseguiti tutti i 71 test senza modificare runtime o dipendenze.
Gli hash dei tre file nel container rilasciato coincidono con il commit.

## Prime osservazioni operative

Alle 16:15 il worker ha ripreso login, correlazione e recupero su Alessandro.
La prima richiesta remota 2060787989 e risultata non evadibile ed e stata
fermata con diagnosi esplicita di revisione, senza reinvio o cancellazione.
Questo errore terminale e il comportamento atteso, non un crash del worker.
Il canary 2060784896 risultava ancora pending e senza PDF alla prima verifica.
Restano risposte HTTP 501 del portale; non sono risolte da questo rilascio.
Non e ancora dimostrato un miglioramento dei tempi di download.

## Evidenze e rollback

Release remota: /opt/gaia/releases/sister-20261005-7d5aa2db/.
Contiene build.log, predeploy-tests-final.log, deploy.log, confronti container
e servizi, copie sorgenti precedenti e manifest deploy/rollback. Gli snapshot
contengono ambiente runtime: directory protetta e file riservati, non versionati.

Rollback operativo, soltanto se autorizzato o necessario per un incidente:

```sh
release=/opt/gaia/releases/sister-20261005-7d5aa2db
docker stop --timeout 180 gaia-elaborazioni-worker-visure
cp "$release/source-before/"*.py /opt/gaia/modules/elaborazioni/worker/
docker compose -p gaia -f "$release/compose-rollback.json" up -d --no-build --no-deps elaborazioni-worker-visure
docker tag gaia-elaborazioni-worker-visure:sister-rollback-20261005 gaia-elaborazioni-worker-visure:latest
```

Nessun recupero massivo, eliminazione manuale, migrazione DB o correzione dati.
Restano da verificare il dato canonico del canary e le metriche post-rilascio;
il recupero massivo resta subordinato al PDF verificato del canary.
