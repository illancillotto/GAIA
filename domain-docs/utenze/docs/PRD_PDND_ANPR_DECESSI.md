# GAIA — Integrazione PDND/ANPR: Verifica Decessi
## Product Requirements Document v1

> Collocazione repository: `backend/app/modules/utenze/anpr/`
> Documentazione: `domain-docs/utenze/docs/`
> Servizi ANPR utilizzati: C030 (Accertamento ID Unico Nazionale), C004 (Verifica Dichiarazione Decesso)

---

## 1. Contesto e obiettivi

### 1.1 Contesto operativo

Il Consorzio di Bonifica dell'Oristanese gestisce un'anagrafica di soggetti (utenti irrigui, consorziati, intestatari catastali) che nel tempo possono decedere. Mantenere aggiornato lo stato di vita/morte dei soggetti è necessario per:

- evitare di emettere atti e notifiche verso persone decedute
- aggiornare la titolarità delle utenze irrigue
- supportare le pratiche di successione e voltura catastale
- mantenere coerenza con i dati ANPR (Anagrafe Nazionale della Popolazione Residente)

Oggi questo aggiornamento avviene manualmente, senza automazione né tracciabilità strutturata.

### 1.2 Soluzione proposta

Integrazione con i servizi ANPR esposti su PDND (Piattaforma Digitale Nazionale Dati) del Ministero dell'Interno:

- **C030** — dato un Codice Fiscale, restituisce l'`idANPR` (identificativo unico nazionale del cittadino in ANPR)
- **C004** — dato un `idANPR` e una data di riferimento, verifica lo stato del soggetto in ANPR, rilevando se è deceduto

### 1.3 Obiettivi

**Obiettivo primario**: Aggiornare automaticamente lo stato di vita/morte dei soggetti nell'anagrafica GAIA interrogando ANPR via PDND, entro i limiti di quota API giornalieri.

**Obiettivi specifici**:
- Job schedulato giornaliero che verifica un numero configurabile di soggetti per day
- Prioritizzazione intelligente della coda di verifica
- Endpoint API per sincronizzazione singola da scheda soggetto
- Audit trail completo di ogni chiamata ANPR
- Configurazione del job modificabile senza deploy

---

## 2. Utenti e ruoli

| Ruolo | Azioni consentite |
|---|---|
| `admin` | Configurazione job, trigger manuale, consultazione log, sync singola |
| `reviewer` | Sync singola da scheda soggetto, consultazione log |
| `viewer` | Consultazione stato ANPR in scheda soggetto (read-only) |

---

## 3. Requisiti funzionali

### RF-01 — Acquisizione idANPR via C030

Per ogni soggetto persona fisica con `codice_fiscale` valorizzato e senza `anpr_id` già noto:
- Chiamare C030 con il Codice Fiscale
- Persistere l'`idANPR` restituito in `ana_persons.anpr_id`
- Loggare l'esito in `anpr_check_log`

Casi di errore:
- CF non trovato in ANPR → `stato_anpr = not_found_anpr`, non ritentare per N giorni
- Errore tecnico → log errore, ritentare al prossimo ciclo

### RF-02 — Verifica stato decesso via C004

Per ogni soggetto persona fisica con `anpr_id` noto, non già segnato come deceduto:
- Chiamare C004 con `idANPR` e `dataRiferimentoRichiesta = data odierna`
- Interpretare la risposta:
  - Soggetto vivo → aggiornare `last_anpr_check_at`, nessun'altra variazione
  - Soggetto deceduto (`listaAnomalie` o campo `chiave/valore` indicante decesso) → impostare `stato_anpr = deceased`, valorizzare `data_decesso` se disponibile
  - Posizione non presente in ANPR per motivi diversi dal decesso → `stato_anpr = cancelled_anpr`
  - Errore 404 → `stato_anpr = not_found_anpr`
- Loggare l'esito in `anpr_check_log`

### RF-03 — Job schedulato giornaliero

Il job si esegue ogni giorno a orario configurabile (default: 02:00 UTC).

**Logica di prioritizzazione coda** (ordine decrescente di priorità):

1. **Soggetti con domanda irrigua solo nell'annualità precedente** (presenti in `cat_utenze_irrigue` per `anno = anno_corrente - 1` ma non per `anno = anno_corrente`): probabilità più alta di decesso/inattività
2. **Soggetti non già marcati come deceduti** (`stato_anpr != 'deceased'`)
3. **Soggetti più anziani anagraficamente** (ordinamento per `data_nascita` ASC, i più vecchi prima)

Numero massimo di chiamate per esecuzione: configurabile via `anpr_sync_config.max_calls_per_day` (default: 100).

Ogni chiamata C030 (acquisizione idANPR) e ogni chiamata C004 (verifica decesso) contano come 1 chiamata verso la quota.

Il job deve essere interrompibile e riprendibile: in caso di errore a metà esecuzione, al successivo ciclo riparte dal prossimo soggetto non verificato.

### RF-04 — Sync singola da scheda soggetto

Il dettaglio soggetto espone un pulsante **"Verifica ANPR"** visibile agli utenti con ruolo `admin` o `reviewer`.

Al click:
1. Se il soggetto non ha `anpr_id` → esegue prima C030 (1 chiamata)
2. Esegue C004 (1 chiamata)
3. Restituisce l'esito all'utente in forma leggibile
4. Aggiorna il record in DB e loga in `anpr_check_log`

La sync singola non consuma quota del job giornaliero (è un'azione operatore esplicita), ma incrementa un contatore separato `anpr_check_log.triggered_by = 'manual'`.

### RF-05 — Configurazione job

Endpoint admin per leggere e aggiornare la configurazione del job:
- `max_calls_per_day`: limite chiamate API giornaliere (intero, default 100)
- `job_enabled`: abilitazione/disabilitazione job (booleano)
- `job_cron`: espressione cron orario esecuzione (stringa, default `"0 2 * * *"`)
- `lookback_years`: quanti anni di storico `cat_utenze_irrigue` considerare per la priorità 1 (intero, default 1)
- `retry_not_found_days`: giorni prima di ritentare soggetti con `not_found_anpr` (intero, default 90)

### RF-06 — Tracciabilità e audit

Ogni chiamata ANPR deve produrre un record in `anpr_check_log` con:
- soggetto verificato
- tipo di chiamata (C030 / C004)
- payload inviato (sanitizzato — no CF in chiaro nel log, solo hash o riferimento)
- esito ricevuto
- timestamp
- chi ha scatenato la chiamata (job automatico / utente specifico)
- `idOperazioneClient` univoco usato nella chiamata (per correlazione con ANPR)

---

## 4. Requisiti non funzionali

| Requisito | Target |
|---|---|
| Quota API giornaliera | Configurabile, MVP max 100 chiamate/giorno |
| Latenza sync singola | < 10 secondi (incluse chiamate ANPR) |
| Disponibilità job | Il job non deve bloccare il backend su errori ANPR transitori |
| Sicurezza credenziali PDND | Client assertion JWT firmata con chiave privata — mai in chiaro nel log |
| Traceability | Ogni chiamata ANPR tracciata con `idOperazioneClient` per audit PDND |
| Compatibilità | Nessuna modifica distruttiva ai modelli `ana_subjects`, `ana_persons` esistenti |

---

## 5. Modello dati

### 5.1 Estensioni a tabelle esistenti

**Tabella `ana_persons`** — campi aggiunti:

| Campo | Tipo | Descrizione |
|---|---|---|
| `anpr_id` | `VARCHAR(50) nullable` | Identificativo unico nazionale ANPR (idANPR) |
| `stato_anpr` | `VARCHAR(30) nullable` | Stato ANPR: `alive`, `deceased`, `not_found_anpr`, `cancelled_anpr`, `error`, `unknown` |
| `data_decesso` | `DATE nullable` | Data decesso restituita da ANPR |
| `luogo_decesso_comune` | `VARCHAR(100) nullable` | Comune decesso (da ANPR) |
| `last_anpr_check_at` | `TIMESTAMP nullable` | Timestamp ultimo controllo ANPR (C004) riuscito |
| `last_c030_check_at` | `TIMESTAMP nullable` | Timestamp ultima chiamata C030 |

### 5.2 Nuove tabelle

**Tabella `anpr_check_log`** — log ogni singola chiamata ANPR:

| Campo | Tipo | Note |
|---|---|---|
| `id` | `UUID PK` | |
| `subject_id` | `UUID FK → ana_subjects.id` | |
| `call_type` | `VARCHAR(10)` | `C030` o `C004` |
| `id_operazione_client` | `VARCHAR(100)` | ID univoco passato ad ANPR |
| `id_operazione_anpr` | `VARCHAR(100) nullable` | ID restituito da ANPR |
| `esito` | `VARCHAR(30)` | `alive`, `deceased`, `not_found`, `cancelled`, `error`, `anpr_id_found` |
| `error_detail` | `TEXT nullable` | Dettaglio errore se esito=error |
| `data_decesso_anpr` | `DATE nullable` | Data decesso se trovata |
| `triggered_by` | `VARCHAR(30)` | `job` o `user:{user_id}` |
| `created_at` | `TIMESTAMP` | |

**Tabella `anpr_sync_config`** — configurazione job (riga singola, upsert):

| Campo | Tipo | Default |
|---|---|---|
| `id` | `INTEGER PK` | 1 (singleton) |
| `max_calls_per_day` | `INTEGER` | 100 |
| `job_enabled` | `BOOLEAN` | true |
| `job_cron` | `VARCHAR(50)` | `"0 2 * * *"` |
| `lookback_years` | `INTEGER` | 1 |
| `retry_not_found_days` | `INTEGER` | 90 |
| `updated_at` | `TIMESTAMP` | |
| `updated_by_user_id` | `INTEGER nullable FK → application_users.id` | |

---

## 6. Flusso PDND — autenticazione

Il protocollo PDND richiede:

1. **Client Assertion JWT** (per ottenere il Voucher Bearer da PDND Authorization Server): JWT firmato con la chiave privata del fruitore, contenente `iss`, `sub`, `aud`, `jti`, `iat`, `exp`
2. **Voucher Bearer** (access token OAuth2 `client_credentials`): ottenuto dal PDND Auth Server, valido per un tempo limitato — da cachare e rinnovare
3. **Agid-JWT-Signature** (header su ogni chiamata): JWS del payload della request per garantire integrità del messaggio (pattern `INTEGRITY_REST_02`)
4. **Agid-JWT-TrackingEvidence** (header su ogni chiamata): JWS con claims di tracciatura per audit (`userID`, `userLocation`, `LoA`) — pattern `AUDIT_REST_02`

Tutti i segreti (chiave privata, client_id, client_secret) devono essere forniti via variabili d'ambiente e mai loggati.

---

## 7. Limiti e vincoli MVP

- Solo soggetti persona fisica con `codice_fiscale` valorizzato
- Persone giuridiche escluse (ANPR non gestisce PG)
- La quota API è globale (C030 + C004 sommati)
- Non gestisce la propagazione automatica del decesso verso altri moduli (es. chiusura utenze irrigue): solo flag `stato_anpr`
- Non integra PREGEO/DOCTE per volture catastali conseguenti al decesso

---

## 8. Evoluzioni future

- Aumento quota API con PDND (il limite 100/giorno è provvisorio)
- Notifica automatica agli operatori quando un soggetto risulta deceduto
- Propagazione decesso al modulo Catasto per segnalare particelle con intestatari deceduti
- Integrazione con flusso Riordino per aggiornamento automatico delle pratiche
- Supporto soggetti AIRE (italiani all'estero)
