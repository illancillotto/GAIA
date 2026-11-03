# Piano di implementazione e stato

## Mandato e invarianti

Piattaforma trasversale, primo adapter Ruolo2021. Nessun invio reale,
casella reale, migrazione produzione o deployment eseguito.
Commit locali incrementali richiesti; nessun push/PR/merge.

| Fase | Esito locale | Evidenza |
| --- | --- | --- |
| A — Audit/progetto | Completata | CODE_AUDIT, PRD, ARCHITECTURE e contratti |
| B — Dati | Completata | 11 tabelle, migration20261103_1200, seed draft/in pausa, schema compare/roundtrip PG |
| C — Backend | Completata | API protette, routing/account/template, snapshot, validazione/versione/autorizzazione |
| D — Worker | Completata | Servizio autonomo, mutex/lease/recovery/retry sicuri/health |
| E/F — Esiti | Completata in isolamento | SMTP/IMAP mock, CMS sintetico reale, PEC/DSN/originali/Registro |
| G — UI | Completata | PEC/email, filtri/paginazione, compositore/PDF.js/checklist/amministrazione |
| H — Collaudo | Gate mirati passati | TEST_REPORT:100% statement/branch sui runtime toccati, build, E2E e regressioni |
| I — Rilascio | Preparato, non eseguito | Overlay opt-in, esempi, grants, manuale, rollback; decisioni esterne aperte |

## Ordine operativo

1. Revisionare diff e report locale, preservando modifiche estranee.
2. Revisionare i commit locali e i contratti di dominio/permesso.
3. Chiudere OPEN_DECISIONS con l'ente: testi, trust, recapiti, conservazione,
   contratto provider, grants, NAS, backup/restore e autorizzazione al collaudo.
4. Applicare DEPLOYMENT_PLAN soltanto dopo autorizzazione specifica.
5. Collaudare le caselle reali su destinatari autorizzati, senza equivalenze
   improprie fra submitted, accettazione PEC, consegna e notifica giuridica.
6. Autorizzare eventuale produzione separatamente.

## Qualità

Metriche prima:1836file/21785callable,1918error-level legacy.
Dopo:1870file/22099callable,1918error-level, zero nuovi errori;
warning2845→2893. Ratchet merge-base main: finding0.
Nessuna soglia/esclusione allargata. Non è una campagna hotspot:
crescita dovuta alla piattaforma, nessuna riduzione legacy dichiarata.
Backend100% include i due registri API/ORM; frontend100% include workspace
Solleciti preesistente. Suite/skip e prove provider distinguibili in TEST_REPORT.

## Confini della change

Sorgente iniziale66b72e5; durante il lavoro il branch ha ricevuto commit esterni
Poste a2bd56f/9676aaa. Le modifiche a .codex/config.toml, .gitignore e documenti
Elaborazioni/Presenze restano fuori dai commit Communications.
Graphify aggiornato solo tramite target dei corpus; nessun graphify-out committato.
