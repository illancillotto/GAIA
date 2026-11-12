# Modelli PEC/email dall'esempio dell'ufficio — 7 novembre 2026

Il catalogo testuale descritto qui è compatibile con l’editor grafico del
12 novembre: può essere convertito in blocchi senza perdere il testo.
Stato corrente: [Template grafici e verifica finale](RICH_TEMPLATES_2026-11-12.md). Le misure e decisioni successive in questo documento
restano riferite alla data originaria.


## Analisi e implementazione locale

L'esempio comunica l'emissione di un avviso 2025. L'operatore ha confermato
l'adattamento all'anno/dati del singolo avviso, IBAN, fasce di rateizzazione,
termine del 31 dicembre 2026 e dati di accesso salvati in GAIA. Communications
resta limitato ai solleciti definitivi 2021. Le proposte comunicano un sollecito;
l'email esplicita la finalità di cortesia. Nessuna approvazione applicativa
dedotta dalla conferma in chat, nessuna modifica delle formule tributarie.

L'IBAN `IT15L0760117400001007214826` coincide con il codice preesistente
(`bollettino_v2.py`, `tributi_reminder_service.py`). Fasce 2/4/6/12/18 rate,
termine e firma sono testo modificabile, non un piano di rateizzazione
calcolato. Prima di riutilizzare il testo oltre il periodo indicato, l'ufficio
deve revisionare e approvare una nuova versione. Nessun dato personale
dell'esempio viene copiato nei sorgenti, nei report o nei test.

In **Communications → Template versionati**, aprire **Modelli di partenza 2021
e variabili**, scegliere PEC o Email, revisionare i campi e salvare la nuova
versione bozza. La scelta popola il form senza salvare, approvare o accodare.
L'approvazione dell'admin e quella individuale di ogni messaggio con PDF
restano distinte. Testo semplice UTF-8, paragrafi, elenco fasce e link completo;
nessuna nuova gestione HTML o riproduzione grafica della tabella.

## Campi e fonti

| Campo | Fonte verificata | Regola |
| --- | --- | --- |
| Intestatario, CF/P.IVA | `RuoloTributiReminderBatchItem.display_name/codice_fiscale` | Destinatario determinato dal dominio |
| Numero | `payload_json.notice_number` | Stringa definitiva, zeri iniziali conservati |
| Annualità | `years_json` | Backend ancora limitato a `[2021]` |
| `importo_documento` | `notice_total_amount(payload_json)` | Formula del PDF, spese incluse e formato italiano |
| `importo` storico | Implementazione preesistente | Compatibilità delle versioni approvate preservata |
| `termine_pagamento` | `front_payment_due_phrase`, formatter PDF | Stesso riquadro 2021, senza calcolare date di notifica |
| `url_portale` | `notice_branding.TAXPAYER_PORTAL_URL` | URL già usato dal PDF |
| `codice_utenza`, `pin_utenza` | `printable_portal_access(payload_json)` | Singolo snapshot cifrato associato al PDF, zeri conservati |
| Bonifico, fasce, contatti, firma | Catalogo e conferma operatore | Modificabili nel gestore, indipendenti dall'account SMTP |

Importo assente/non canonico/non finito e accessi assenti, multipli, corrotti o
non decifrabili lasciano assenti le variabili richieste. Rendering rifiutato
con HTTP409, senza messaggio parziale; nessuna scelta della prima utenza o
ricerca per nome/email. PIN decifrato solo nella composizione, mai nel catalogo,
negli eventi o negli errori. Corpo finale, PDF e MIME sono artefatti sensibili
persistiti nell'archivio privato, non dichiarati cifrati separatamente.

## Disponibilità e audit PIN

Prima query aggregata CED, transazione READ ONLY terminata con rollback:

| Controllo documentale 2021 | Numero |
| --- | ---: |
| Righe definitive con percorso PDF | 1.195 |
| Numeri avviso distinti / CF distinti | 1.009 / 986 |
| Payload con un'utenza associata | 138 |
| Payload senza utenza | 1.057 |
| Utenza univoca nell'archivio GAIA per il CF del sollecito | 864 |
| Più utenze nell'archivio | 1 |
| Nessuna utenza nell'archivio | 330 |
| Utenza univoca GAIA senza accessi nel payload PDF | 726 |
| Importo presente nel payload | 1.195 |

Questi conteggi non certificano il contenuto dei PDF né l'eleggibilità dopo
pagamenti/notifiche/prenotazioni. I 1.195 percorsi PDF sono distinti, ma includono
più versioni/righe per lo stesso numero avviso: non sono 1.195 utenze o invii.
L'utente ha richiesto il confronto dei PIN con i file PDF effettivi prima
della decisione sui 726 casi. Audit completo **1.195/1.195**, lettura di tutte
le pagine, concluso in 1.052,3 secondi; nessun file non leggibile, privo di testo
o con etichette PIN non estraibili. I **138 PDF con accessi** coincidono con
archivio e snapshot, inclusa la titolarità per CF: **zero discordanti**.
I restanti **1.057 PDF non riportano PIN nel testo**: 726 con utenza univoca in
GAIA, 330 senza utenza, uno con due utenze da verificare. Nessun login al portale
o controllo esterno della validità operativa dei PIN.

I 138 file con PIN riguardano **131 numeri avviso**. Per **93 numeri** sono
presenti sia versioni con PIN sia versioni senza PIN: non sovrascrivere
automaticamente lo storico. Hash PDF distinti: 1.186. I 12.353 record accessi
dell'archivio sono decifrabili e con PIN numerici; questo controllo di formato
non certifica l'accesso al portale. Confronti in memoria, nessun PIN esportato.

Riepilogo verificabile senza dati personali:
[evidence/OFFICE_PIN_AUDIT_2026-11-07.json](evidence/OFFICE_PIN_AUDIT_2026-11-07.json).
Report operativo e dettaglio ID/numero/hash, senza credenziali, nella directory
privata `/home/cbo/Desktop/Verifica_PIN_GAIA_PDF_20261107/` (directory0700,
file0600). Nessun fallback all'archivio è abilitato: resta da decidere l'uso dei
726 accessi presenti solo in GAIA, senza rigenerazioni o modifiche automatiche.

## API, architettura e file

`GET /communications/admin/template-catalog`, solo admin attivo, restituisce
`variables` (descrizioni), `note`, `proposals` (due TemplateInput) dal catalogo
JSON nel package Communications. Nessuna scrittura o informazione personale;
le versioni salvate usano le tabelle esistenti.

Nuovi runtime: `communications/template_catalog.py`,
`ruolo/services/notice_communication_fields.py`, componente frontend
`communications/template-catalog.tsx`. Integrazione nei file esistenti
`communications/{admin,registry,ruolo_source}.py` e `admin-templates.tsx`.
Campi di dominio sotto Ruolo; riferimento pubblico
`ruolo_source.template_variables` conservato. Nessuna migrazione, dipendenza,
modifica dei trasporti o della state machine.

## Matrice comportamento → test

| Comportamento | Prova |
| --- | --- |
| Catalogo senza scritture, solo admin attivo/autenticato | `test_catalog_is_read_only…`, `test_catalog_requires…` |
| Totale PDF/spese/formato, input mancanti o invalidi | `test_document_total…`, `test_missing_or_invalid_source_total…`, API missing-total |
| Termine PDF senza notifica fittizia | `test_deadline_matches_pdf…` |
| Variabili preesistenti preservate | `test_legacy_variables_remain_compatible…` |
| Utenza/PIN del renderer, zeri conservati | `test_portal_fields_match_existing_pdf_snapshot…` |
| Accessi mancanti/multipli/corrotti, chiave assente e PIN invalido | `test_missing_ambiguous_or_corrupt_access…`, `test_decrypted_invalid_pin…`, `test_missing_master_key…` |
| Approvazione distinta, PDF e MIME identici, niente job | `test_catalog_draft_requires_approval_then_composes_exact_snapshot_and_mime`, PEC/email |
| PIN obbligatorio rifiutato se manca l'utenza | `test_approved_office_template_requires_own_utenza_and_pin`, PEC/email |
| Form editabile, salvataggio esplicito, errori/retry | unit `template-catalog.test.tsx` |
| Desktop/mobile, errore catalogo e salvataggio draft | E2E `communications-office-templates.spec.ts` |
| Regressione eliminazione, PDF e approvazione | E2E `communications-template-deletion.spec.ts`, `communications.spec.ts` |

## Verifiche

- Backend Communications e accessi portale: **268 PASS**, zero skip, inclusi
  dieci test PostgreSQL su DB isolato, trasporti sintetici.
- Cinque runtime backend: **327 statement, 86 branch, 100%**; due componenti UI:
  **48 statement, 28 branch, 21 funzioni, 37 righe, 100%**; zero missing o
  partial branch, nessuna nuova esclusione; **67 test unit frontend PASS**.
- **18 smoke PASS**, typecheck, build clean isolata e lint mirato PASS;
  **8 E2E PASS** sulla build ottimizzata con API mock, desktop/mobile.
- Ratchet autorevole completo contro merge-base `main`: FAIL per 17 finding
  Presenze concorrenti, nessuno nei sette runtime del ciclo. Nessuna baseline,
  soglia o esclusione modificata. Lint backend globale FAIL per due import
  Presenze e format di un test concorrente; Ruff runtime/test del ciclo PASS.
- Nuovo mapping Ruolo: cinque callable, massimi cognitive15/cyclomatic13,
  nessun errore di soglia. Mapping principale 7/8; controlli accessi 15/13,
  due warning accettati sotto le soglie errore. Catalogo UI 7/7; componente
  amministrativo principale invariato a 13/12. Non dichiarata riduzione di
  complessità legacy o PASS globale; nessun refactoring estraneo.
- Graphify codice Ruolo/backend/frontend aggiornati tramite target dedicati.
  Pruning forzato con patch prevista da AGENTS: rimosso il vecchio nodo della
  funzione in Communications, presente il nuovo mapping Ruolo; nessun grafo
  versionato. Dopo l'audit PIN, aggiornati anche i grafi docs piattaforma e
  Ruolo: entrambi chunk1/1 completato, nessun semantic chunk fallito.
  Piattaforma: 15.500 token input, 911 output, stima USD0,0077;
  Ruolo: 6.181 input, 1.448 output, stima USD0,0048.

Primo test fallito: assunzione di importi localizzati nel payload, mentre il
renderer richiede numeri canonici. Ora quei dati vengono rifiutati, senza
accettare il fallback a zero. Primo E2E: il mock catturava anche l'heartbeat
Auth, corretto il confine del mock. Una scansione intermedia rilevava nuova
complessità: mapping importi/accessi ora distinti, sotto soglia errore, senza
alterare comportamento, soglie o esclusioni. Report intermedi non equivalgono
alla verifica finale del freeze.

Evidenze: `/tmp/gaia-office-templates-20261107/`. Nessun deployment, commit,
template reale creato/approvato, rigenerazione PDF o invio per questo ciclo.
