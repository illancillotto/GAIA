# Modifica dei template salvati — 17 novembre 2026

## Comportamento implementato

In **Template versionati**, **Modifica template** riapre una bozza o una versione
approvata nell’editor esistente e sposta il focus sul titolo con il nome corrente.
Sono modificabili testo, oggetto e, nei modelli grafici, logo, blocchi, link e
pulsanti HTTPS. L’anteprima mostra il contenuto aggiornato. **Annulla modifiche**
svuota l’editor senza scritture. Salvare con lo stesso codice crea una nuova
versione bozza tramite l’API esistente; originale e messaggi già creati restano
conservati. L’approvazione rimane un passaggio separato.

Il mini editor e i link cliccabili erano già presenti. Questa change rende
esplicito l’accesso alla modifica dei template salvati e aggiunge focus,
istruzioni e annullamento. Nessuna modifica backend, schema, trasporto o permessi.

## Verifiche

- 109 test unitari Communications PASS, su 15 file; intero runtime modificato
  `admin-templates.tsx` al 100%: 35 statement, 16 branch, 13 funzioni, 25 righe.
  Nessuna nuova esclusione. I test verificano caricamento dei campi, focus,
  nuova bozza da template approvato, originale preservato, link in anteprima,
  annullamento senza scritture e riapertura.
- ESLint mirato, typecheck e 18 smoke test PASS.
- 25 E2E sulla candidata PASS, zero failure/skip/flaky: due casi di authoring
  desktop 1440 px/mobile 390 px e 23 regressioni Communications. I casi nuovi
  falliscono sulla versione precedente all’assenza di **Modifica template**.
  Le API browser sono intercettate con dati sintetici: non sono stati modificati
  account/template reali né inviati messaggi.
- Ratchet autorevole sul file runtime rispetto al merge-base di `origin/main`:
  zero finding. `TemplateAdministration`: ciclomatica 10→11, cognitiva 11→12,
  LOC 30→37 rispetto al codice precedente; un warning dopo la modifica e zero
  errori. Non si dichiara una riduzione della complessità. Baseline e soglie
  invariate; il debito storico fuori perimetro non è certificato da questo gate.
- Graphify frontend aggiornato tramite `make graphify-frontend`; l’AST non
  rileva cambiamenti di topologia. Documentazione tramite
  `make graphify-platform-docs`, verificando anche il completamento semantico.

Comandi riproducibili, dalla directory `frontend`:

```sh
VITEST_COVERAGE_INCLUDE=src/components/communications/admin-templates.tsx npm run test:coverage -- tests/unit/communications
npx eslint src/components/communications/admin-templates.tsx tests/unit/communications/admin.test.tsx tests/e2e/communications-rich-templates.spec.ts
npm run typecheck
npm test
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3190 npx playwright test tests/e2e/communications.spec.ts tests/e2e/communications-rich-templates.spec.ts tests/e2e/communications-office-templates.spec.ts tests/e2e/communications-pagination.spec.ts tests/e2e/communications-template-deletion.spec.ts tests/e2e/communications-navigation.spec.ts tests/e2e/communications-loading.spec.ts tests/e2e/communications-account-panel.spec.ts --workers=2
```

Dalla root:

```sh
python tools/code_quality/complexity.py ratchet --base-ref origin/main frontend/src/components/communications/admin-templates.tsx
make graphify-frontend
make graphify-platform-docs
```

## Rilascio

Pubblicato sul CED il **17 novembre 2026 alle 10:32:01 CET**, commit applicativo
`a6421cff23dbf2d4674fe7b34047742f06f89965`, branch
`chore/split-changes-20261109`. Immagine:
`sha256:aec8c602da0f533be8cb5c692b61b6b77f69a54efb8b592fe926878da6c22a06`.
Un solo file runtime sovrapposto alla sorgente del frontend effettivamente live
(rilascio pannello account); tutte le 196 route preservate. Le modifiche
concorrenti nel working tree non sono incluse. Release privata CED:
`/opt/gaia/releases/communications-template-edit-20261117`.
Configurazione effettiva e rollback conservati privatamente, senza versionare
credenziali. Attivazione protetta da controlli su release concorrenti, health,
configurazione e container estranei, con rollback automatico in caso di errore.

[Evidenze verificabili](evidence/TEMPLATE_EDIT_2026-11-17.json).

## Verifica dopo il deploy

Tutti i **25 E2E ripetuti sul live passano**, zero failure/skip/flaky. Frontend,
backend e worker Communications healthy. Build pubblicata identica alla
candidata, configurazione effettiva preservata e 36 altri container invariati.
Login, amministrazione, solleciti PEC/email e health API rispondono 200;
l’API amministrativa anonima continua a rispondere 401. Nessun invio reale.

## Limiti della verifica

Il 100% riguarda il file runtime modificato, non l’intero repository. I test
browser verificano la UI servita dalla build reale con API sintetiche, non una
nuova transazione sui dati di produzione. Nessun problema bloccante rilevato
nel perimetro; restano separati il debito storico di complessità e gli avvisi
sulle dipendenze preesistenti segnalati da GitHub al push: otto, di cui sette
high e uno moderate. Nessuna dipendenza è stata modificata.
