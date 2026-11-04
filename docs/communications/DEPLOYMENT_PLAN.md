# Preparazione al rilascio

Piano preparato durante il ciclo del 3 novembre senza eseguire deployment.
Il successivo rilascio CED autorizzato il 4 novembre è registrato nel
[report operativo](DEPLOYMENT_REPORT_2026-11-04.md), che distingue i passaggi
conclusi da quelli pendenti. La distribuzione mirata è completata su nuova
autorizzazione: migrazione applicata, backend/frontend/worker healthy.
Trasporti e caselle reali restano disabilitati.
Credenziali provider, collaudo con recapiti reali e atti richiedono
autorizzazione specifica.

## Artefatti

- Migrazione 20261103_1200_communications.py.
- deploy/communications/compose.yaml, overlay con profilo communications.
- env.example, account.example.json, worker-grants.sql, senza segreti reali.
- Immagini GAIA backend/frontend dai Dockerfile esistenti.
- Worker entrypoint diretto bypassa bootstrap/migrazioni web.
- PDF.js worker locale incluso nella build frontend.

## Sequenza operativa

1. Backup consistente DB e trust/secret; provare restore isolato. Congelare
   prenotazioni Poste durante la migrazione; verificare Alembic head unica.
2. Costruire/taggare immagini. Verificare OpenSSL eseguibile, CA e PDF.js.
3. Rivedere SQL privilegi, creare ruolo worker senza DDL/DELETE/UPDATE tributi.
   Configurare DATABASE_URL dedicata e internal key, non password provider.
4. Applicare migrazione dal servizio amministrativo. Verificare undici tabelle,
   trigger immutabilità/revision/cross-channel, due template draft e pausa globale.
5. Distribuire backend/frontend; avviare solo worker Communications con trasporto
   false e caselle disabilitate/in pausa. Verificare health e heartbeat.
6. Configurare account/template e mount; verificare PDF sorgenti NAS/runtime-data
   readonly accessibili da UID10001. Il test sintetico non dimostra accesso NAS CED.
7. Dopo ulteriore autorizzazione: abilitare rete/trasporto e testare connessioni/
   invio a recapito di collaudo approvato. Verificare accettazione, consegna PEC,
   EML e Registro; nessun salto da mock a casella reale.
8. Riprendere solo account/ambito approvati e monitorare. Incerti mai riprodotti.

Comando dell'overlay generico, da adattare alla configurazione CED preservata:
docker compose -f docker-compose.yml -f deploy/communications/compose.yaml --profile communications up -d communications-worker

Fornire variabili da file protetto esterno. Path relativi al primo Compose file.
config --quiet è stato validato con valori sintetici; non è prova di deployment.
La preparazione del 4 novembre usa una configurazione congelata e immagini derivate
dal runtime CED per preservare le correzioni operative preesistenti; vedere
il report per comandi effettivi e rollback, senza rigenerare tutti i servizi.
Restore completo e grant sullo schema CED verificati; ruolo ristretto applicato.
Prima dei trasporti reali restano carico/limiti contrattuali, NAS, configurazione
provider, testi/trust/conservazione e checklist dell'ente approvati.
