# Modello dati

Migrazione 20261103_1200, parent 20261103_0900. Undici tabelle, UUID applicativi,
FK verso utenti GAIA e documento Registro. Nessuna modifica a importi o formule.

| Tabella | Responsabilità / vincoli |
| --- | --- |
| communication_accounts | TLS, username, secret_ref esterno, canale/provider, utenti/moduli/default/priorità, limiti, pausa, versione, salute e cursore IMAP |
| communication_templates | Unique codice/versione, testo semplice, stato/approvatore |
| communication_messages | Sorgente e Registro, numero, envelope, fingerprint, versione/stato; unique active_key e technical_id |
| communication_attachments | PDF BYTEA, nome/MIME, pagine/byte/SHA256/versione/primario, immutabile |
| communication_reviews | Review UUID, allegato, operatore, versione messaggio, rendering |
| communication_authorizations | Unique messaggio/versione, digest/checklist/operatore; append-only |
| communication_jobs | Tipo/account/messaggio, unique idempotency_key, stato/lease/token/backoff/contatore/errori |
| communication_attempts | Unique job/numero e technical_id, MIME integrale e hash immutabili, esito |
| communication_events | Aggregato/tipo/attore/dettaglio/timestamp; append-only |
| communication_receipts | EML/hash/correlazione/date/classificazione; unique account/hash, immutabile |
| communication_controls | Singleton id=1, pausa globale/heartbeat; seed in pausa |

Indici su sorgente, numero, documento, account, stato/canale, job, aggregato,
correlazione. BYTEA deferred nell'ORM; costituisce il riferimento di archivio
privato, senza URL permanente. Trigger impediscono delete dello storico,
modifica envelope accodato/trasmesso e alterazione MIME.

## Stati

draft → ready → approved → queued → sending → submitted.
Modifiche da ready/approved tornano draft; annullamento fino a queued e dopo failed soltanto senza prove di trasmissione
iniziata/incerta/accettata.
Da sending: failed, uncertain o queued solo dopo rifiuto esplicito sicuro.
submitted/accepted/uncertain ammettono esiti documentati; delivered non regredisce
con ricevute tardive. Una consegna tardiva può superare not_delivered.
failed/cancelled non sono riaperti da PATCH. Mappa autorevole: policy.TRANSITIONS.

accepted = accettazione PEC certificata; submitted = accettazione SMTP.
dsn_delivered resta evento email, senza equiparazione a PEC. Nessun automatismo
di perfezionamento giuridico. Downgrade distruttivo vietato su evidenze popolate.

## Recapiti Utenze — migrazione predisposta `20261104_1400`

`ana_electronic_contacts` collega `subject_id -> ana_subjects.id` e indirizzo
normalizzato, univoci insieme. Canale PEC/email/non classificato; stato
attivo/revisione/revocato, fonte, riferimento, versione positiva e operatore.
Un non classificato non può essere attivo. I campi storici restano preservati.
La classificazione scrive un audit Utenze e partecipa ai trigger di revisione
su PostgreSQL. Nessun dato viene classificato dalla migrazione.
Dettagli e stato non rilasciato: CONTACT_CLASSIFICATION_2026-11-04.md.
