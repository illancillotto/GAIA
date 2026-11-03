# Preparazione al rilascio

Nessun deployment eseguito. Migrazione, rete reale, credenziali e atti richiedono
autorizzazione specifica, backup provato e finestra di manutenzione.

## Artefatti

- Migrazione 20261103_1200_communications.py.
- deploy/communications/compose.yaml, overlay con profilo communications.
- env.example, account.example.json, worker-grants.sql, senza segreti reali.
- Immagini GAIA backend/frontend dai Dockerfile esistenti.
- Worker entrypoint diretto bypassa bootstrap/migrazioni web.
- PDF.js worker locale incluso nella build frontend.

## Sequenza autorizzata da eseguire successivamente

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

Comando di avvio previsto, non eseguito:
docker compose -f docker-compose.yml -f deploy/communications/compose.yaml --profile communications up -d communications-worker

Fornire variabili da file protetto esterno. Path relativi al primo Compose file.
config --quiet è stato validato con valori sintetici; non è prova di deployment.
Prima del CED: restore, grants sull'intero schema, carico/limiti contrattuali,
testi/trust/conservazione e checklist dell'ente approvati.
