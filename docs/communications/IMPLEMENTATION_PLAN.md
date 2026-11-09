# Piano di implementazione e stato

## 2026-11-07 — Modelli dall'esempio dell'ufficio

- [x] Analisi fonti, conferma testi/condizioni e campi del singolo avviso.
- [x] Catalogo PEC/email amministrativo, form modificabile, solo draft esplicito.
- [x] Mapping Ruolo, totale/termine PDF, accessi univoci e blocchi sui dati mancanti.
- [x] Test mirati, PostgreSQL, coverage, build e otto E2E sintetici.
- [x] Confronto completo PIN archivio/payload/file PDF: 1.195 documenti, 138 con PIN coincidente, zero discordanti/errori di lettura.
- [ ] Decidere uso dei dati GAIA nei 726 documenti senza PIN nel PDF e revisione dei casi mancanti/multipli.
- [ ] Rilascio: non eseguito né autorizzato per questo ciclo.
- Fonti, matrice ed evidenze: [OFFICE_TEMPLATES_2026-11-07.md](OFFICE_TEMPLATES_2026-11-07.md).

## 2026-11-07 — Eliminazione template con conferma

- [x] Pulsante Elimina per singola versione, con conferma e blocco durante la richiesta.
- [x] DELETE amministrativo, conferma validata dal backend, cancellazione logica e audit.
- [x] Preservati messaggi/snapshot e numerazione delle versioni.
- Verifiche e stato del rilascio: [TEMPLATE_DELETION_2026-11-07.md](TEMPLATE_DELETION_2026-11-07.md).
- [x] Rilascio selettivo CED autorizzato, 09:42:21 CET; sola modifica template sopra le immagini effettive, collaudo candidata/live e health conclusi. [Report](TEMPLATE_DELETION_RELEASE_2026-11-07.md).

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
completata alle 11:50 CET dopo risoluzione gate; [evidenze](SIDEBAR_RELEASE_2026-11-04.md).

## Risoluzione gate sidebar

Gli otto incrementi del commit `86fa982d` sono eliminati senza deroghe.
Ratchet completo, sincronizzazione ordinaria e verifica baseline PASS;
35 test mirati e coverage 100%, regressione frontend, build/lint/types e
quattro E2E locali più quattro sull’immagine candidata CED PASS.
Dettagli e stato di pubblicazione corrente in
[SIDEBAR_RELEASE_2026-11-04](SIDEBAR_RELEASE_2026-11-04.md).

Default recapiti per canale completato e verificato: nessuna variazione backend
o schema. [Verifiche e pubblicazione frontend](CONTACT_FILTERS_2026-11-04.md).

## Consolidamento recapiti del 04/11/2026

Completati nel checkout registro Utenze, resolver condiviso, API admin e collaudo
per PEC/email su persone e aziende. Completato audit read-only dei solleciti2021.
Restano rilascio e migrazione `20261104_1400`, applicazione controllata del piano,
classificazione degli sconosciuti e revisione dei discordanti. Ratchet globale
con sette finding preesistenti riprodotti: nessuna baseline aggiornata per
assorbirli. Stato verificabile: CONTACT_CLASSIFICATION_2026-11-04.md.

## Anteprima immediata — 4 novembre 2026

[x] Anteprima immediata da Componi/checkbox, hash confrontato al comando di creazione, retry e abort, test API/UI/browser. [ ] Rilascio del registro e classificazione recapiti, distinto dalla patch preview.

Dettagli: [SOURCE_PREVIEW_2026-11-04](SOURCE_PREVIEW_2026-11-04.md).

Pubblicazione preview completata alle 16:32:01 CET: PDF reale 2021 verificato, quattro E2E live con API simulate PASS. Registro recapiti/migrazione ancora non pubblicati; elenco PEC legacy ancora 17. Vedere SOURCE_PREVIEW_2026-11-04.md per rollback, matrice e limiti del gate.

## Chiusura rilascio registro recapiti — 05/11/2026

[x] Schema, integrazione, grant ristretto e classificazioni pubblicati.
[x] Quarantena dei quattro valori invalidi, audit e report ufficio.
[x] Verifica effettiva di liste, recapiti per entrambi i tipi di soggetto e PDF.
[ ] Revisione discordanti e abilitazione/collaudo dei provider reali.
La pubblicazione non abilita trasporti o caselle: vedere [CONTACT_RELEASE_2026-11-05](CONTACT_RELEASE_2026-11-05.md).
