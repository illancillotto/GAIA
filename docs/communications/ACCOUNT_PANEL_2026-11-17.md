# Pannello account espandibile — 17 novembre 2026

## Comportamento

«Nuovo account» è un pannello HTML nativo `details/summary`, chiuso all'ingresso.
Si apre con clic, Invio o Spazio. La chiusura conserva i dati inseriti; «Modifica»
apre il pannello sull'account selezionato, anche dopo una precedente chiusura.
L'elenco account resta visibile. Payload, autorizzazioni, invii, test provider
e acquisizione ricevute restano invariati.

## Verifiche

- 13 test unitari PASS; intero `admin-accounts.tsx` al 100%: 55 statement,
  38 branch, 29 funzioni e 36 righe. Nessuna esclusione nuova.
- ESLint, typecheck e 18 smoke test PASS.
- Candidata di produzione: 25 E2E PASS, zero failure/skip/flaky; comprendono
  due casi specifici desktop 1440 px/mobile 390 px e 23 regressioni Communications.
  Clic/tastiera, bozza preservata e riapertura dello stesso account verificati;
  nessuna scrittura Communications. API intercettate con dati sintetici.
- I due nuovi E2E falliscono sulla precedente versione live per assenza
  del pannello. Il primo giro sulla candidata rilevava soltanto l'heartbeat
  della shell come scrittura inattesa: l'asserzione è stata corretta per
  controllare le scritture Communications, poi rieseguiti tutti i 25 casi.
- Ratchet autorevole rispetto al merge-base `origin/main`: zero finding.
  Ciclomatica/cognitiva invariate; un warning preesistente, nessun nuovo errore.
  Il confronto diagnostico contro HEAD segnala LOC 34→39 per
  `AccountAdministration` e 4→5 per `edit`, dovute al pannello e alla sua apertura.
  Non è dichiarato verde quel confronto aggiuntivo; baseline, soglie ed esclusioni
  restano intatte. Nessun refactoring estraneo per compensare la crescita.
- Graphify frontend e documentazione piattaforma aggiornati con i target dedicati.

## Rilascio

Candidata pronta, attivazione ancora da registrare. Un solo file runtime
applicato alla sorgente del frontend effettivamente online (rilascio navigazione),
con tutte le 196 route preservate. Nessun file concorrente del working tree
incluso nell'immagine. Release privata CED:
`/opt/gaia/releases/communications-account-panel-20261117`.

Configurazione effettiva, immagine precedente e Compose di rollback sono
conservati privatamente; non versionare environment o credenziali. L'attivazione
verifica assenza di release concorrenti, health, configurazione e container
estranei, con rollback automatico in caso di fallimento. Nessuna migrazione,
modifica backend o riattivazione trasporti.

[Evidenze verificabili](evidence/ACCOUNT_PANEL_2026-11-17.json).
