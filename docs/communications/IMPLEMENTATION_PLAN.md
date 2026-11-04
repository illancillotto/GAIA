# Piano di implementazione e stato

## Mandato e invarianti

Piattaforma trasversale, primo adapter Ruolo2021. Il ciclo di sviluppo del
3 novembre non ha eseguito invii, migrazioni produzione o deployment.
Il rilascio mirato CED del 4 novembre, con trasporto disabilitato,
è tracciato in [DEPLOYMENT_REPORT_2026-11-04](DEPLOYMENT_REPORT_2026-11-04.md).
Backend/frontend/worker attivi; caselle e collaudo reale restano da configurare.
Commit locali incrementali richiesti; nessun push/PR/merge.

| Fase | Esito locale | Evidenza |
| --- | --- | --- |
| A — Audit/progetto | Completata | CODE_AUDIT, PRD, ARCHITECTURE e contratti |
| B — Dati | Completata | 11 tabelle, migration20261103_1200, seed draft/in pausa, schema compare/roundtrip PG |
| C — Backend | Completata | API protette, routing/account/template, snapshot, validazione/versione/autorizzazione |
| D — Worker | Completata | Servizio autonomo, mutex/lease/recovery/retry sicuri/health |
| E/F — Esiti | Completata in isolamento | SMTP/IMAP mock, CMS sintetico reale, PEC/DSN/originali/Registro |
| G — UI | Completata | PEC/email, filtri/paginazione, compositore/PDF.js/checklist/amministrazione |
| H — Collaudo | Gate mirati passati | TEST_REPORT:100% statement/branch sui runtime toccati, build, E2E, backend8015PASS/471SKIP, frontend5468PASS, workerPoste166PASS |
| I — Rilascio | Distribuzione CED completata, trasporti disabilitati | Backup/restore completo, migrazione/ruolo/health/API/PDF.js PASS; configurazione e collaudo caselle residui |

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
La prima sincronizzazione ordinaria era stata rifiutata per17 metriche Poste
preesistenti. La successiva verifica finale ha applicato la procedura documentata
di riparazione del runtime già committato: baseline riproducibile nel commit
d826c904, ratchet merge-base sempre PASS (BASELINE_REPAIR.md).
Nessuna soglia/esclusione allargata. Non è una campagna hotspot:
crescita dovuta alla piattaforma, nessuna riduzione legacy dichiarata.
Backend100% include i due registri API/ORM; frontend100% include workspace
Solleciti preesistente. Suite/skip e prove provider distinguibili in TEST_REPORT.

## Confini della change

Sorgente iniziale66b72e5; durante il lavoro il branch ha ricevuto commit esterni
Poste a2bd56f/9676aaa. Le modifiche a .codex/config.toml, .gitignore e documenti
Elaborazioni/Presenze restano fuori dai commit Communications.
Graphify aggiornato solo tramite target dei corpus; nessun graphify-out committato.

## Chiusura di qualità

FINAL_REVIEW.md contiene la matrice completa dei comportamenti/test e le misure
finali. PROGRESS.md distingue sviluppo/collaudo locale dalle attività esterne
residue. Due nuovi test verificano migrazione SQLite e contabilità Ruolo reale;
nessuna funzionalità aggiunta durante la chiusura.

Gate complessivo finale: FAIL; le prove Communications sono verdi, ma i limiti
della regressione generale restano espliciti in FINAL_REVIEW.md.

## Revisione UI successiva al rilascio

Completata e verificata localmente la sidebar destra: elenco e composizione
a metà desktop, campi prima del PDF e checklist, disposizione verticale mobile.
Nessun cambiamento backend, schema, trasporto o dipendenza. Pubblicazione UI
residua; [evidenze](SIDEBAR_REVIEW_2026-11-04.md).
