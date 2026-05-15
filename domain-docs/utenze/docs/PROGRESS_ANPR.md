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

## Verifiche Eseguite

- `alembic upgrade head` nel container `gaia-backend` ✅
- `pytest tests/test_config.py tests/test_pdnd_auth.py` ✅ (`6 passed`)
- `pytest tests/test_anpr_client.py` ✅ (`6 passed`)
- `pytest tests/test_anpr_service.py` ✅ (include lookup CF)
- `pytest tests/test_anpr_routes.py` ✅ (include `preview-lookup` e ruoli)
- `pytest tests/test_anpr_scheduler.py` ✅ (`4 passed`)
- `npx tsc --noEmit` in `frontend` ✅

## Note Aperte

- il mapping definitivo della risposta C004 resta marcato come non validato via `_RESPONSE_MAP_VALIDATED = False` finché non viene confermato su ambiente ANPR di test
- restano da eseguire i test di integrazione end-to-end con credenziali PDND reali e soggetti di test ANPR/SOGEI

## Prossimo Step

- implementazione locale completata fino allo step documentale
- prossimo passo utile: validazione su ambiente ANPR di test e chiusura del mapping C004 con evidenza dei payload reali
