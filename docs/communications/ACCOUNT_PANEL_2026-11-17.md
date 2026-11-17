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

Pubblicato sul CED il **17 novembre 2026 alle 09:36:22 CET**, commit applicativo
`ac288c6ba3e763fbb632adef079dc0d694e97998`, branch `chore/split-changes-20261109`.
Immagine `sha256:4687a014294aabefb8ed4446c9093741b17ddd4bb8c4830176f95be3d1cd0b94`.
Un solo file runtime
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

## Verifica dopo il deploy

Tutti i **25 E2E ripetuti sul live passano**, zero failure/skip/flaky.
Frontend, backend e worker Communications healthy. Build pubblicata identica
alla candidata, configurazione effettiva preservata e 36 altri container
invariati. Login, amministrazione, solleciti PEC/email e health API rispondono
200; API amministrativa anonima ancora 401. Nessun invio o scrittura di
configurazione reale: i test browser usano esclusivamente API sintetiche.

Restano separati il debito storico di complessità e gli otto avvisi dipendenze
preesistenti segnalati da GitHub (sette high, uno moderate). Nessuna dipendenza
o baseline è stata modificata da questa change.
