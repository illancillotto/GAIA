# Progress ANPR

## Stato Modulo

- milestone corrente: `PDND/ANPR — Verifica Decessi`
- stato: `completed`

## Completato

- aggiunta migration backend per campi ANPR su `ana_persons`, tabelle `anpr_check_log` e `anpr_sync_config`
- registrati modelli ORM ANPR e singleton config nel modulo `backend/app/modules/utenze/anpr/`
- introdotti schemi Pydantic per config, log, stato soggetto, sync result e job status
- implementato `PdndAuthManager` con client assertion JWT, voucher cache e header `Agid-JWT-*`
- implementato `AnprClient` per i servizi C030 e C004 con parsing difensivo delle risposte
- implementato service ANPR con queue builder, sync singolo soggetto, config update e daily job
- esposti endpoint backend `/utenze/anpr/*` per sync, status, log, config e trigger job
- endpoint `POST /utenze/anpr/preview-lookup` (`{ codice_fiscale }`): C030 e, se richiesto, C004 senza soggetto in DB e senza persistenza log `anpr_check_log`; ruoli come sync (`reviewer`/`admin`/`super_admin`, modulo utenze); usato dalla modale creazione persona fisica («Recupera dati», nessun `anpr_id` manuale)
- integrato scheduler APScheduler nel lifecycle backend per il job giornaliero ANPR
- aggiunta card frontend stato ANPR nel dettaglio soggetto `frontend/src/app/utenze/[id]/page.tsx`
- aggiunta pagina admin `frontend/src/app/anagrafica/anpr-config/page.tsx` per configurazione e monitor job
- aggiornata la navigazione modulo utenze con voce admin per configurazione ANPR
- copiati gli spec ANPR nel path dominio atteso:
- `domain-docs/utenze/docs/specs/C004-servizioVerificaDichDecesso.yaml`
- `domain-docs/utenze/docs/specs/SpecificaAPI_C030.yaml`
- completata la suite test dedicata backend per auth, client, service esteso (**preview lookup** senza soggetto), routes e scheduler
- aggiunta validazione esplicita della configurazione PDND (`PDND_CLIENT_ID`, `PDND_KID`, `PDND_PRIVATE_KEY_PATH`/`PDND_PRIVATE_KEY_PEM`) con risposta API `503` invece di `500` grezzo quando il backend non ha credenziali ANPR utilizzabili
- corretta la generazione del voucher PDND: `client_assertion` con audience configurabile/derivata, supporto `purposeId` opzionale e cache separata per purpose, per evitare `403` sul token endpoint quando C030/C004 usano credenziali o scopi distinti
- corretto il default `PDND_AUTH_URL` su `https://auth.interop.pagopa.it/token.oauth2` dopo verifica runtime: l'endpoint precedente `/as/token.oauth2` rispondeva `403 {"message":"Missing Authentication Token"}` con le stesse credenziali
- verificato nei log backend che il nuovo blocco residuo è TLS verso `modipa-val.anpr.interno.it`: certificato emesso da `Sogei Certification Authority Test`; aggiunto supporto config `ANPR_CA_BUNDLE_PATH` e `ANPR_SSL_VERIFY` per fidare la CA test nel container
- dopo il fix TLS, l'errore runtime si è spostato su `401 AuthenticationRequired / Errore nella validazione del JWT`; riallineati gli header verso GovWay con `Digest` HTTP, `aud` ANPR normalizzato, `iss/sub`, `nbf` e `purposeId` nei JWS `Agid-JWT-*`
- aggiunto binding tra `Agid-JWT-TrackingEvidence` e `client_assertion` PDND tramite digest SHA-256 del tracking JWT, in linea con il flusso operativo documentato per il profilo interoperabilità
- verificato runtime ANPR `prod`: `idOperazioneClient` di C030 non può superare 30 caratteri; adeguata la generazione a identificatori numerici compatti
- verificato runtime ANPR `prod`: C004 richiede `verifica.datiDecesso`; aggiunto `dataEvento=ieri` per evitare l'errore `EN148`
- estesa la test suite backend ANPR con casi service-level su stop anticipato dopo `C030 not_found`, gestione errore `C004` in preview e vincoli runtime emersi su header/payload
- aggiunto test route-level sul contratto `POST /utenze/anpr/sync/{subject_id}`: gli errori operativi ANPR restano `200` con `success=false`, mentre i soli problemi di configurazione PDND continuano a esporre `503`
- sostituita la coda batch basata su `CatUtenzaIrrigua` con una coda basata su `ruolo_avvisi.subject_id`; se `ANPR_JOB_RUOLO_YEAR` non è valorizzato il job usa automaticamente l'ultimo `anno_tributario` disponibile, escludendo tutti i soggetti non a ruolo
- ordinamento batch ANPR fissato per data di nascita crescente (`più anziano -> più giovane`) con esclusione dei soggetti già processati nella stessa giornata locale
- esclusione esplicita dalla coda dei soggetti già marcati `stato_anpr = deceased`
- introdotto hard cap giornaliero da `.env` (`ANPR_DAILY_CALL_HARD_LIMIT`) applicato come tetto invalicabile rispetto al valore operativo `anpr_sync_config.max_calls_per_day`
- introdotta finestra oraria locale `ANPR_JOB_START_HOUR` / `ANPR_JOB_END_HOUR` e batch size `ANPR_JOB_BATCH_SIZE`; il cron di default è ora `0 8-17 * * *` nel timezone `ANPR_JOB_TIMEZONE`
- aggiunta tabella `anpr_job_runs` per tracciare ogni esecuzione batch giorno per giorno con budget prima/dopo, soggetti selezionati/processati, errori e deceduti rilevati
- esteso endpoint `GET /utenze/stats` e dashboard `frontend/src/app/utenze/page.tsx` con i KPI `deceased_updates_last_24h`, `deceased_updates_current_month`, `deceased_updates_current_year`

## Verifiche Eseguite

- `alembic upgrade head` nel container `gaia-backend` ✅
- `pytest tests/test_config.py tests/test_pdnd_auth.py` ✅ (`6 passed`)
- `pytest tests/test_anpr_client.py` ✅ (`6 passed`)
- `pytest tests/test_anpr_service.py` ✅ (include lookup CF)
- `pytest tests/test_anpr_routes.py` ✅ (include `preview-lookup` e ruoli)
- `pytest tests/test_anpr_scheduler.py` ✅ (`4 passed`)
- `pytest backend/tests/test_anpr_service.py backend/tests/test_anpr_scheduler.py backend/tests/test_config.py -q` ✅ (`33 passed`)
- `npx tsc --noEmit` in `frontend` ✅
- `npm run build` in `frontend` ✅

## Note Aperte

- il mapping definitivo della risposta C004 resta marcato come non validato via `_RESPONSE_MAP_VALIDATED = False` finché non viene confermato su ambiente ANPR di test
- restano da eseguire i test di integrazione end-to-end con credenziali PDND reali e soggetti di test ANPR/SOGEI
- il tracciamento giornaliero `anpr_job_runs` è persistito lato backend ma non è ancora esposto in una vista dedicata del workspace `elaborazioni`

## Prossimo Step

- implementazione locale completata per batch a ruolo, cap giornaliero e KPI dashboard
- prossimo passo utile: esporre `anpr_job_runs` nel workspace `elaborazioni` e validare in runtime il throughput giornaliero reale con dati di ruolo 2025
