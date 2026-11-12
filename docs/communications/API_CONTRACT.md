# Contratto API

## Corpo grafico — 12 novembre 2026

`TemplateInput.body`, `MessageCreate.body` e `MessageChange.body` accettano una
stringa da 1 a 20.000 caratteri. Senza prefisso è testo semplice. Con prefisso
`GAIA-BLOCKS/1\n` è un array JSON di 1–60 blocchi. Tipi e campi esatti:
`logo` solo `kind`; `title/paragraph/list` con `kind,text`; `link/button` anche
`url` HTTPS assoluto, senza credenziali, controlli o variabili. Campi extra,
tipi errati, testo vuoto o URL non ammessi restituiscono 422 nei comandi.
Le variabili nei campi testuali usano lo stesso insieme del catalogo.

`GET /ruolo/candidates/{id}/template-preview?template_id=…&channel=pec|email`
restituisce `subject,body,source_sha256,missing_variables,send_blockers` con
no-store/private. Per un modello grafico, `body` rimane un documento a blocchi
risolto, non HTML. Le mancanze sono visibili nell’anteprima e continuano a
bloccare la creazione. Un template draft/incompatibile resta 409. Le API non
spediscono email né restituiscono URL pubblici del PIN. Esempi e matrice: [Template grafici e verifica finale](RICH_TEMPLATES_2026-11-12.md).


Prefisso /communications (esterno normalmente /api/communications). Bearer GAIA.
Lettura: modulo Ruolo + ruolo.tributi.view; scritture: anche manage_status.
Amministrazione: require_admin_user. Nessuna API riceve password provider.

| Metodo / path relativo | Contratto |
| --- | --- |
| GET /accounts, /admin/accounts | Utilizzabili senza endpoint/secret_ref / configurazioni admin senza password |
| POST /accounts | Configurazione completa; default disabilitato e in pausa |
| PATCH /accounts/{id} | Configurazione completa + expected_version, invalida fingerprint |
| POST /accounts/{id}/test | Job test SMTP+IMAP, senza messaggi |
| POST /accounts/{id}/reconcile | Job raccolta ricevute |
| POST /accounts/{id}/pause | paused boolean |
| GET /templates, /admin/templates | Approvati / tutte le versioni non eliminate |
| GET /admin/template-catalog | Solo admin attivo; variables, note e due proposals modificabili PEC/email; nessuna scrittura |
| POST /templates | Nuova versione draft |
| POST /templates/{id}/approve | Approvazione admin esplicita |
| DELETE /templates/{id} | Solo admin; body confirmed=true obbligatorio; elimina logicamente la singola versione |
| GET /ruolo/candidates | channel, year=2021, page/page_size; q/batch/contatti/stati/date/account |
| GET /ruolo/candidates/{id}/eligibility | Verifica attuale, authorizes_dispatch=false |
| GET /messages | channel/state/account_id e paginazione |
| POST /messages | source_entity_id, channel, recipient, account opzionale, template o subject/body, purpose |
| GET/PATCH /messages/{id} | Dettaglio / nuova revisione bozza |
| GET/POST /messages/{id}/attachments | Metadati / multipart upload + expected_version, PDF |
| GET /messages/{id}/attachments/{part}/preview | Byte privati, review UUID e SHA256 negli header, no-store |
| POST /messages/{id}/attachments/{part}/rendered | expected_version/review_id/pages/sha256, stesso operatore |
| POST /messages/{id}/validate | Ricontrollo dati e integrità, draft→ready |
| POST /messages/{id}/approve | Versione, confirmed=true, checklist completa |
| POST /messages/{id}/dispatch | Versione, job idempotente HTTP202; nessuna rete |
| POST /messages/{id}/cancel | Versione, solo senza effetti irreversibili; failed sicuro annullabile |
| GET /messages/{id}/events, /receipts | Storico senza binari nei JSON |
| GET /messages/{id}/receipts/{receipt}/original | EML autenticato scaricabile |
| GET /jobs, /jobs/{id} | Stato/errori normalizzati, lease_token omesso |
| GET /admin/monitor, /admin/unmatched-receipts | Code, heartbeat/pausa, incerti/non correlati |
| POST /admin/pause | Pausa globale dispatch |

PATCH bozza: account_id/recipient/subject/body/expected_version.
Versione incrementata anche aggiungendo PDF. Nessuno stato arbitrario nel payload.
Checklist esatta: identity, address, complete_pdf, notice_year, amounts, text,
attachments, account; tutti true. Nessuna approvazione batch.

401/403 auth/permessi; 404 assenza; 409 conflitto/integrità/eleggibilità/
concorrenza; 422 schema/anno/dati. Unique violation normalizzata, senza SQL/PII.
Schema autorevole completo: OpenAPI FastAPI e schemas.py. Dispatch idempotente
non significa exactly-once SMTP.

La cancellazione template restituisce HTTP200 con `status=deleted`; ripetere
lo stesso comando non aggiunge eventi di audit. Il template sparisce da entrambi
gli elenchi e non può più essere approvato o usato per creare messaggi (409).
Identità, contenuto, approvazione pregressa e riferimenti dei messaggi restano
conservati. Una nuova versione dello stesso codice prosegue la numerazione,
incluse le versioni eliminate. Conferma assente/falsa o campi extra:422;
identità inesistente:404. Il comando non contatta provider né accoda invii.

Verifica conclusiva: contratti invariati; la nuova prova con contabilità reale
conferma HTTP409 e assenza di job se un pagamento rende ineleggibile un avviso
già approvato. Matrice API/permessi/errori in FINAL_REVIEW.md.

## Classificazione dei recapiti — checkout 04/11/2026

`GET` e `PUT /communications/admin/subjects/{subject_id}/contacts` espongono
il registro Utenze anche per le persone fisiche. Accesso amministratore attivo,
modulo Ruolo e sezione Tributi visibile. Scrittura con `expected_version`,
indirizzo, canale (`pec/email/unclassified`), stato (`active/review/revoked`),
fonte e riferimento obbligatori. Un non classificato non può essere attivo.
Nessun comando trasmette messaggi. Endpoint rilasciati il 5 novembre; vedere CONTACT_RELEASE_2026-11-05.md.

Contratto completo e compatibilità dei campi legacy:
[CONTACT_CLASSIFICATION_2026-11-04.md](CONTACT_CLASSIFICATION_2026-11-04.md).

## Anteprima immediata — 4 novembre 2026

GET /communications/ruolo/candidates/{identity}/preview restituisce PDF private/no-store, X-Content-SHA256 e X-PDF-Pages. Richiede ruolo.tributi.view e modulo Ruolo. MessageCreate accetta expected_source_sha256 opzionale (64 hex): mismatch 409 prima dello snapshot.

Dettagli: [SOURCE_PREVIEW_2026-11-04](SOURCE_PREVIEW_2026-11-04.md).
