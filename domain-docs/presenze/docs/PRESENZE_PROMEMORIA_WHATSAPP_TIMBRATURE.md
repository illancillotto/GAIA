# Promemoria WhatsApp per timbrature incomplete

Stato al 2026-09-15: **implementato, disattivo** (provider vuoto nella configurazione GAIA).
Il motore vive in GAIA perché lavora sui dati Presenze live, sull'anagrafica di riferimento
(collegamenti utente, profilo operatore, telefono) e sullo scheduler di piattaforma. GATE non
ha logica WhatsApp.

## Canale

**Gateway non ufficiale self-hosted WAHA** (WhatsApp HTTP API), container `gaia-waha` collegato
via QR a un numero aziendale come sessione WhatsApp Web, motore `NOWEB`. Le API ufficiali Meta
sono state scartate.

| Rischio | Mitigazione |
| --- | --- |
| Blocco del numero da parte di WhatsApp | Numero **dedicato** intestato all'ente (mai quello principale), SIM attiva su un telefono, account usato a mano qualche settimana prima degli invii automatici; ritmo di invio dosato (sotto). |
| Sessione scollegata | Il dispatcher si ferma al primo 401/403/404/422 di WAHA o dopo 3 errori di fila; le giornate non notificate vengono ricalcolate all'esecuzione successiva. |
| Nessuna garanzia né supporto | Avviso di cortesia: le anomalie restano in GAIA e il capo squadra resta il riferimento. |
| Aggiornamenti WhatsApp che rompono WAHA | Fissare la versione con `PRESENZE_WAHA_IMAGE`; `latest` solo per prove. |

Messaggio:

```text
Ciao Angelo, per queste giornate la timbratura risulta incompleta:
• lun 14/09: uscita mancante (ingresso 07:02)
• mar 15/09: nessuna timbratura

Rivolgiti al tuo capo squadra per regolarizzarla.
Messaggio automatico GAIA. Rispondi STOP per non ricevere più questi avvisi.
```

## Flusso

```text
platform-scheduler (watcher ogni minuto; cron configurato in PostgreSQL, Europe/Rome)
  └─ punch_reminder_job.run_punch_reminder_job      advisory lock Postgres
       ├─ load_reminder_inputs        presenze_daily_records + presenze_daily_punches
       ├─ load_reminder_contacts      operator_profile.phone + application_users.is_active
       ├─ select_punch_reminders      regole sotto
       └─ dispatch_punch_reminders    check-exists → sendText → pausa casuale
            └─ record_dispatch_outcome   presenze_whatsapp_messages (+ notified_days)
gaia-waha ──webhook HMAC──▶ backend POST /presenze/whatsapp/webhook
            message.ack → SENT/DELIVERED/READ/FAILED     message "STOP" → opt-out
```

Una giornata viene registrata in `presenze_whatsapp_notified_days` dopo `SENT`
(accettazione WAHA, non prova di consegna). `NOT_ON_WHATSAPP` non e una notifica.
Un ack `FAILED` riapre la giornata, salvo che sia gia consegnata/letta.
I rinviati restano in `presenze_whatsapp_pending_days` anche oltre il lookback:
si ricalcolano sui dati correnti e vengono eliminati se corretti o giustificati.
Prima dell'invio si rileggono mapping, profilo, telefono, STOP e timbrature,
anche dopo la verifica numero; la fascia oraria viene ricontrollata dopo la pausa.

Il lock usa una transazione su connessione PostgreSQL dedicata: i commit dei
messaggi non rilasciano o trasferiscono il lock. Ogni invio viene preceduto da
un tentativo `SENDING` persistente collegato alle giornate pendenti. Un timeout,
errore server o risposta sendText senza ID produce `UNKNOWN`; un crash lascia
`SENDING`. Entrambi bloccano il retry automatico delle giornate: non esiste una
garanzia exactly-once offerta da WAHA. Un esito incerto ferma il batch corrente.
Risposte check-exists senza booleano sono errori, non numeri inesistenti.

Le ricevute sono persistite anche se arrivano prima della risposta sendText;
si riconciliano alla registrazione dell'esito e all'avvio del job successivo.
READ/DELIVERED non vengono retrocesse da callback tardive FAILED.

## Regole di selezione (`services/punch_reminders.py`)

- **Solo giornate chiuse**: nuove candidate da `oggi - PRESENZE_WHATSAPP_LOOKBACK_DAYS`
  a ieri (Europe/Rome), piu giornate gia pendenti; solo collaboratori attivi.
- **Solo errori di timbratura**: uscita mancante, ingresso mancante, due ingressi senza uscita.
  "Nessuna timbratura" solo con `PRESENZE_WHATSAPP_INCLUDE_MISSING_PUNCHES=true`, `teo_minutes > 0`
  e orario diverso da SAB/DOM/RIPTURN. Ritardi, uscite anticipate, permessi e ore mancanti non
  generano messaggi.
- **Esclusi**: giornate validate; assenze giustificate (`resolve_export_absence_code`, oppure
  `absence_minutes >= teo_minutes`).
- **Identità fail closed**: solo `presenze_collaborators.application_user_id`, con la stessa
  coerenza record/collaboratore del payload GATE (`canonical_record_gaia_user_id`). Nessun
  matching per nome, matricola o telefono.
- **Telefono**: `operator_profile.phone` normalizzato E.164; per +39 solo cellulari. Nessun
  fallback su `application_users.phone_extension` (è l'interno d'ufficio).
- **Un messaggio per collaboratore** con tutte le giornate aperte; **opt-out** vince su tutto.

Motivi di scarto: `operator_not_linked`, `operator_profile_missing`, `operator_disabled`,
`opted_out`, `phone_missing`, `phone_invalid` (restituiti nel report del job e nel log).

## Ritmo di invio (`services/punch_reminder_dispatch.py`)

| Parametro | Variabile | Default |
| --- | --- | --- |
| Pausa casuale tra messaggi | `PRESENZE_WHATSAPP_MIN/MAX_DELAY_SECONDS` | 25–75 s |
| Messaggi per esecuzione | `PRESENZE_WHATSAPP_MAX_PER_RUN` | 40 |
| Fascia oraria (lun–ven) | `PRESENZE_WHATSAPP_SEND_START/END_HOUR` | 08–19 |
| Stop su errori consecutivi | — | 3, o subito su errore di sessione/API key |
| Verifica numero | — | `check-exists` prima di ogni invio |

## Tabelle (migration `20260915_1200`, `20260915_1300` e `20260915_1400`)

- `presenze_whatsapp_messages`: esito di ogni tentativo, testo inviato, giornate, id WAHA, ack.
- `presenze_whatsapp_notified_days`: unicità `(kind, collaborator_id, work_date)`.
- `presenze_whatsapp_opt_outs`: per `application_user_id`; `source=whatsapp_reply`.
- `presenze_whatsapp_pending_days`: chiave collaboratore/giornata e ultimo tentativo.
- `presenze_whatsapp_receipts`: ricevuta WAHA monotona per ID messaggio, per
  non perdere callback anticipate o duplicate.
- `presenze_whatsapp_config`: singleton con provider, collegamento WAHA, cron e
  limiti runtime. API key e chiave HMAC sono cifrate con `CREDENTIAL_MASTER_KEY`;
  le API restituiscono solo i flag di presenza e mai i segreti in chiaro.

## Recupero esiti incerti

Non cambiare automaticamente SENDING/UNKNOWN in FAILED. Verificare nella
sessione WAHA destinatario, testo e orario. Se l'esito non e dimostrabile,
mantenere la quarantena. Dopo verifica amministrativa, usare il servizio
`reconcile_uncertain_attempt(db, attempt_id, sent=..., evidence=...,
provider_message_id=...)`: richiede evidenza non vuota, ID WAHA se inviato,
lock esclusivo e stato ancora incerto. L'evidenza deve identificare l'autore
e la verifica svolta. Un invio confermato chiude le giornate; una mancata
spedizione confermata consente la rivalutazione automatica dei dati correnti.
La riconciliazione e disponibile nella dashboard amministrativa tramite una
route autenticata riservata ad `admin` e `super_admin`. Non esistono route
pubbliche per questa operazione.

Il ricontrollo riduce la finestra di concorrenza: uno STOP o una correzione
successivi all'ultimo controllo, con richiesta WAHA gia in partenza, non
possono annullare atomicamente l'invio esterno.

## Verifica correzioni review (2026-09-15)

56 test mirati passati, inclusi PostgreSQL 16 temporaneo per lock con commit,
rilascio su eccezione, upsert ricevute, upgrade/downgrade delle due migration
e vincolo giornate duplicate. Coverage full-file dei sei runtime corretti:
513/513 statement e 104/104 branch, 100%. Ruff e ratchet contro `2507f223`
passano; nessuna nuova violation error-level. Nessun commit, deploy o invio
reale; provider invariato e disattivo.

## Dashboard amministrativa

La pagina `/presenze/whatsapp`, disponibile dal menu Presenze ai soli ruoli
`admin` e `super_admin`, e una console di controllo: non contiene un comando di
invio immediato e l'anteprima non scrive sul database.

- Stato del provider, stato live della sessione WAHA, prossima esecuzione,
  finestra oraria e limite per batch.
- Anteprima dei destinatari pronti e dei messaggi completi, calcolata con le
  stesse regole del job.
- Elenco delle esclusioni con motivo leggibile; per telefono mancante o non
  valido consente di aggiornare esclusivamente `operator_profile.phone`.
- Storico paginato e filtrabile per persona, username, telefono e stato. Ogni
  tentativo mostra utente canonico, numero usato, testo, giornate, ID provider,
  errore, creazione, consegna e lettura.
- Gestione degli utenti che hanno risposto STOP e ripristino esplicito dei
  promemoria.
- Riconciliazione dei soli tentativi `SENDING`/`UNKNOWN`, con evidenza
  obbligatoria e ID WAHA obbligatorio quando l'invio viene confermato.
- Configurazione completa del runtime dalla modal dedicata: provider spento,
  `dry_run` o WAHA, URL e sessione, segreti, cron, lookback, anomalie senza
  timbrature, batch, pause e fascia oraria. La sezione e le relative API sono
  visibili esclusivamente al ruolo `super_admin`; gli `admin` mantengono le
  funzioni operative e lo storico. Le modifiche sono lette dal watcher entro un
  minuto e non richiedono il riavvio dello scheduler.

| Metodo | Route | Uso |
| --- | --- | --- |
| `GET` | `/presenze/whatsapp/dashboard` | KPI, configurazione e stato sessione |
| `GET` | `/presenze/whatsapp/configuration` | configurazione senza segreti (`super_admin`) |
| `PUT` | `/presenze/whatsapp/configuration` | aggiorna configurazione e segreti (`super_admin`) |
| `GET` | `/presenze/whatsapp/messages` | storico paginato e filtrabile |
| `GET` | `/presenze/whatsapp/preview` | anteprima read-only |
| `GET` | `/presenze/whatsapp/opt-outs` | elenco STOP |
| `DELETE` | `/presenze/whatsapp/opt-outs/{user_id}` | riattivazione esplicita |
| `PATCH` | `/presenze/whatsapp/users/{user_id}/phone` | telefono profilo operatore |
| `POST` | `/presenze/whatsapp/messages/{message_id}/reconcile` | esito incerto |

Il legame mostrato nello storico resta quello persistito al momento del
tentativo: `application_user_id` identifica l'utente GAIA, mentre il nome del
collaboratore e il numero E.164 documentano destinatario e contatto effettivi.

## Attivazione

1. Numero dedicato + telefono, account riscaldato.
2. Verificare che `CREDENTIAL_MASTER_KEY` sia configurata. Il deploy standard
   avvia WAHA e, se assenti, genera nel file produzione API key, chiave HMAC e
   password dashboard. Fissare `PRESENZE_WAHA_IMAGE` prima dell'uso reale.
3. `alembic upgrade head`.
4. Dopo il deploy, tunnel `ssh -L 3100:127.0.0.1:3100 <server>`, quindi
   `http://localhost:3100/dashboard` → avvio sessione `default` → scansione QR.
5. Come `super_admin`, aprire `/presenze/whatsapp` → `Configura WhatsApp`,
   verificare che API key e HMAC risultino configurate, lasciare URL
   `http://waha:3000` e sessione `default`, quindi scegliere `Prova senza invio`.
6. Per una settimana i messaggi finiscono nello storico con stato `DRY_RUN`
   senza essere inviati. Dopo la verifica a campione selezionare `WAHA, invio reale`.

La UI configura tutto il runtime applicativo e non espone Docker. Creazione del
container, aggiornamento dell'immagine e prima scansione QR restano operazioni
infrastrutturali intenzionali; dare alla web app accesso al socket Docker o alla
console WAHA aumenterebbe inutilmente i privilegi del backend.

## Copertura anagrafica (verifica 2026-09-15)

196 collaboratori attivi, 184 collegati a un utente GAIA, 12 senza collegamento; 15 collegati
senza profilo operatore. Il limite principale è `operator_profile.phone`: va compilato in GAIA e
arriva anche a GATE con il sync operatori. La dashboard WhatsApp permette ora di compilarlo per
gli utenti scartati per numero mancante o non valido.

## Privacy

Uso del cellulare personale per comunicazioni di servizio da inserire nell'informativa
dipendenti; valutare con DPO/RSU (art. 4 Statuto dei lavoratori). Il messaggio contiene solo
giornata e timbratura mancante.

## Prima dell'attivazione reale

Le pagine operative `/presenze/giornaliere` e `/presenze/anomalie` mostrano nel
dettaglio un avviso per le giornate passate non validate con punch incompleti e
collegano alla dashboard WhatsApp. E un'indicazione potenziale: la selezione
definitiva resta nel job e applica provider, mapping, telefono, STOP, validazione
e assenza giustificata.

- Procurare il numero dedicato e scansionare il QR della sessione WAHA.
- Eseguire una settimana con `PRESENZE_WHATSAPP_PROVIDER=dry_run` e revisionare
  anteprime e storico dalla dashboard.
- Formalizzare informativa privacy e autorizzazione del canale.
