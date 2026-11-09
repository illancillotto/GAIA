# Contratto API

`GET /communications/admin/template-catalog`: solo amministratori attivi; restituisce `variables`, `note` e due `proposals` PEC/email modificabili, senza scritture. Nuove variabili: `codice_fiscale`, `url_portale`, `importo_documento`, `termine_pagamento`, `codice_utenza`, `pin_utenza`. Le variabili richieste prive di fonte valida causano HTTP 409 senza messaggio parziale.

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
| GET /templates, /admin/templates | Approvati / tutte le versioni |
| POST /templates | Nuova versione draft |
| POST /templates/{id}/approve | Approvazione admin esplicita |
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

Verifica conclusiva: contratti invariati; la nuova prova con contabilità reale
conferma HTTP409 e assenza di job se un pagamento rende ineleggibile un avviso
già approvato. Matrice API/permessi/errori in FINAL_REVIEW.md.
