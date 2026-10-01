# Refresh INAZ del collaboratore richiesto da GATE

Il runner `app.scripts.gate_mobile_sync_runner` avvia un thread outbound
indipendente (`app.scripts.gate_collaborator_refresh`) che ogni 3 secondi
interroga GATE per `sync_collaborator`. Non dipende dal ciclo completo da
300 secondi e non apre API entranti sulla LAN.

Il servizio `app.modules.presenze.services.gate_collaborator_refresh` verifica
mapping canonico, visibilità GATE delle squadre nel mese o accesso
amministrativo/proprio e matricola INAZ univoca, poi crea un job Presenze con
priorità 0 e un solo employee_code. La credenziale proviene dal record
`presenze_auto_sync_config`, deve essere attiva; lo scheduler automatico può
restare disabilitato. Il worker Presenze conserva claim, lease, retry e
fencing ordinari. I job già in esecuzione non vengono interrotti.

La chiave UUID5 di `action.id` rende i poll ripetuti idempotenti. Il comando
resta pendente fino a importazione completa con giornaliere; GAIA pubblica
snapshot persona/mese di giornaliere e anomalie e conferma solo dopo entrambi
i 2xx. Errori INAZ/identità/configurazione vengono segnalati con fail; errori
HTTP/DB mantengono la richiesta pendente per riprovare. La console GATE legge
lo stato e ricarica la scheda interessata dopo l'ack.

`gate_mobile_record_items.build_presenze_record_items` serializza i record
selezionati dalla query mirata usando classificazione, regole, analisi e
formato timbrature già usati dagli snapshot mensili. I wrapper mensili
conservano gli alias `records`/`giornaliere` e `anomalies`/`anomalie`.
I timestamp sono acquisiti prima delle letture, così il ricevente può evitare
sovrascritture da snapshot precedenti, incluse anomalie già rimosse.

Rilascio coordinato: prima GATE con migration 028 e supporto agli snapshot
scoped, poi backend GAIA e restart di `gate-mobile-sync`; mantenere
`presenze-worker` attivo. Il contratto dettagliato è in
`GaTe-mobile/docs/PRESENZE_COLLABORATOR_SYNC.md`. Anche con trasporto periodico
pull LAN, il comando mirato richiede il runner outbound GAIA configurato.

La verifica finale ha aggiunto controlli sul risultato worker: `completed`,
righe importate, zero `records_errors`, zero `progress.failed_collaborators`
e matricola richiesta in `checkpoint.completed_employee_codes`. Un errore di
scraping o checkpoint incompleto resta fallimento anche quando il worker ha
marcato il job completato. Gli identificativi dell'autore usano il parser
canonico; valori booleani, frazionari e non positivi sono rifiutati.

Riesame GAIA del 2026-10-01 su `f687c213`: 136 test backend passati, inclusi
refresh, cancellazione squadre, sync esistente, runner e API mobile-sync.
Coverage reale dei sei runtime coinvolti: 1080/1080 statement e 368/368 branch
(100%), senza nuove esclusioni. Ruff e style ratchet sui nove file Python
passano; il format check richiesto sui cinque file nuovi passa. I file legacy
non vengono riformattati in massa. Complexity ratchet contro `origin/main`
passato, `findings: []`, senza modificare baseline/scanner.

Regressione estesa Presenze/GATE/mobile-sync: 1076 test passati, 10 saltati,
exit 0. I test saltati non sono attestati come verificati; gli scenari con
PostgreSQL opzionale richiedono `GAIA_TEST_POSTGRES_URL`. Restano warning
preesistenti delle fixture JWT e del test `runpy` del runner. Nessuna failure
o modifica ai test per sopprimerla.

Verificati mapping canonico fail-closed, idempotenza del job, checkpoint e
importazione completa, visibilità persona/squadra, failure HTTP senza ack
anticipato e riuso del serializer mensile. Restano 31 violation di complessità
legacy nel perimetro (11 error, 20 warning), senza regressioni nel ratchet.
Il coupling del serializer con i builder esistenti evita duplicazione del
contratto; non è una nuova architettura parallela.

Graphify Presenze/backend aggiornati tramite target dedicati. Evidenze locali:
`/tmp/gaia-gate-review/`. Questo riesame attesta il lato GAIA, non il checkout
GATE o integrazioni live PostgreSQL/INAZ/GATE. Il report cross-repository
`GaTe-mobile/docs/PRESENZE_COLLABORATOR_SYNC_FINAL_REPORT.md` conserva i propri
residui; serve rilascio coordinato. Nessuna sincronizzazione o deploy produttivo
eseguiti.
