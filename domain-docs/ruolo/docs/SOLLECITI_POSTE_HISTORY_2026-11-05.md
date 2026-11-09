# Storico Posta Online nei solleciti — 2026-11-05

## Stato e perimetro

Implementata la visualizzazione dei riferimenti Poste già persistiti nel dettaglio
dei solleciti generati. La consultazione non chiama Poste, non spedisce messaggi,
non modifica dati tributari e non richiede migrazioni o nuove dipendenze.
Rilasciata sul CED il 2026-11-05 alle 18:14:59 CET dopo le verifiche finali.

Il controllo read-only sul CED ha rilevato 431 record `sent`, tutti con
`poste_draft_id`, `sent_at` e `tracking_number`. Il conteggio fotografa i record
di spedizione, non certifica la consegna al destinatario.

## Comportamento e contratto API

`GET /ruolo/tributi/solleciti/batch-overview` mantiene i controlli esistenti
`require_module("ruolo")` e `require_section("ruolo.tributi.view")` e aggiunge
`poste_dispatches` alle voci. La query `dispatches_by_notice` associa i tentativi
per numero avviso esatto, anche quando provengono da una diversa copia/lotto
dello stesso avviso; non usa il solo codice fiscale.

Il nuovo schema `BatchPosteDispatch` espone esclusivamente i metadati:
ID interno, numero avviso, stato, ID Poste, stato rilevato sul portale,
creazione bozza, spedizione, codice raccomandata, operatore di caricamento,
aggiornamento GAIA e username account Poste. Non espone artefatti, destinatari
o credenziali. Nessun tentativo produce un array vuoto.

`NoticeCards` usa l'overview e `PosteHistory` mostra tutti i tentativi, dal più
recente, inclusi annullati. I valori mancanti sono indicati esplicitamente.
La data di bozza è distinta dalla spedizione; lo stato tecnico `sent` è
visualizzato come «Spedito», senza dedurre una consegna legale.
Le regole di selezione/caricamento e le evidenze PEC restano quelle esistenti.

## Matrice comportamento → test

| Comportamento | Verifica |
| --- | --- |
| Metadata salvati, più tentativi, ordinamento, annullati e valori nulli | backend `test_overview_shows_saved_poste_history_for_same_notice_across_batches` |
| Stesso numero avviso in lotti diversi, esclusione numeri estranei, assenza di dati sensibili e nessuna mutazione | stesso test backend |
| Numero avviso assente, payload vuoto, nessuna spedizione, fallback e overview precedente | `test_poste_overview_without_notice_numbers_or_matching_shipments`, altri test overview |
| Autenticazione e input query obbligatorio | test overview: richiesta anonima 401, parametro mancante 422; consultazione con viewer |
| Tutti i campi, fallback, assenza storico, bozza distinta da spedizione | `frontend/tests/unit/solleciti-poste-history.test.tsx` |
| Integrazione scheda, PEC e anteprima invariati | `frontend/tests/unit/notice-solleciti-page.test.tsx` |
| Desktop/mobile, storico, anteprima e percorso di caricamento simulato | `frontend/tests/e2e/ruolo-invio-solleciti.spec.ts` a 1440/390 px |

## Verifiche eseguite

- Backend overview: 4 test passati, 100% statement e branch sui tre runtime
  modificati (82 statement, 8 branch), nessuna esclusione.
- Regressione backend overview/PDF/Poste API: 33 test passati.
- Frontend mirato: 63 test passati; 100% statement/branch/funzioni/linee sui
  tre runtime modificati (21 statement, 31 branch, 10 funzioni, 15 linee).
- Regressione frontend: 352 file, 5.495 test passati. Il runner jsdom segnala
  la navigazione documentale non implementata; nessun test fallito.
- `npm test`, `npm run typecheck`, ESLint mirato e `make lint-backend`: passati.
- Build Docker backend e frontend `npm run build:clean`: passate; 196 route
  frontend preservate, 984 file backend estranei preservati tramite hash.
  La build riporta warning ESLint in componenti legacy estranei (tra cui Wiki);
  il lint dei file di questa modifica passa senza warning.
- E2E sulla build candidata: 2 test passati, desktop/mobile senza overflow.
  Prima esecuzione fallita per fixture account Poste obsoleta (`{}` invece
  di array): corretta la fixture e la selezione account, senza modificare runtime.
- Ratchet complessità completo contro `origin/main`: passato, nessun finding.
  Massimo del nuovo codice: ciclomatica 9, cognitiva 8; nessuna nuova violazione.
  `batch_overview`: 11/14 → 3/2; mapper estratto 9/8.
  La prima sincronizzazione isolata ha rifiutato `NoticeCard` (6/5/17 →
  7/6/18): ripristinati 6/5/17 gestendo l'array assente in `PosteHistory` e
  destrutturando le props nella firma. Baseline sincronizzata e verificata
  nel checkout QA isolato: nessun allargamento soglie/esclusioni e nessuna
  sovrascrittura della baseline del working tree condiviso.
- Graphify codice Ruolo e frontend aggiornati tramite target dedicati.

Evidenze di lavoro locali: `/tmp/gaia-poste-ui-20261105/` (non versionate).
Il working tree contiene modifiche concorrenti: la candidata include soltanto
i sei runtime elencati nel manifest, senza commit o push di questa unità.

## Rilascio e ripristino

Candidata e configurazioni protette in
`/opt/gaia/releases/solleciti-poste-history-20261105`.
Attivare esclusivamente backend/frontend se ID container e configurazioni
coincidono con la fotografia di preparazione. Conservare immagini precedenti
e Compose di rollback; verificare healthcheck, risposta autenticata e parità
con i dati archiviati. Nessun aggiornamento worker o migrazione previsto.
In caso di problema ripristinare soltanto le proprie immagini, senza sovrascrivere
un eventuale rilascio concorrente. PEC/email restano disabilitate e in pausa.

### Esito produzione

- Backend: `sha256:37485fd790edae64cc3a26a7b7df1760aa5e378919c673c56e74b379556dc7ea`.
- Frontend: `sha256:4a5cd4745224ddb3c6524b95828d6cb0bed43bfcce3c6df5487fa816ee72e436`.
- Entrambi i servizi healthy, configurazioni effettive preservate; altri 51
  container invariati. Build frontend identica alla candidata collaudata.
- Database invariato a `20261104_1400`; nessuna migrazione o spedizione.
  Controllo Communications: pausa globale attiva, zero account/messaggi/job.
- Probe HTTP sulle sei pagine operative: 200; endpoint riservati senza
  autenticazione: 401, incluso batch-overview.
- Probe autenticato read-only: tutti i metadati di una spedizione campione
  coincidono esattamente tra database e API. Controllo aggregato: tutti i 431
  record `sent` hanno ID Poste, data di spedizione e tracking.
- Regressione finale dopo semplificazione: 5.495 test frontend passati.
- E2E ripetuti sull'immagine finale e su `http://gaia.lan`: 2 + 2 passati.
  Le API negli E2E sono simulate, inclusa la creazione lotto; il probe separato
  verifica i dati reali tramite sole letture. Non è un nuovo collaudo del
  provider Poste né una verifica della consegna delle raccomandate.

`ACTIVATED.json`, manifest, gate ed evidenze sono nella directory di release.
Il rilascio è circoscritto a questa visualizzazione; non costituisce una nuova
attestazione del quality gate dell'intera piattaforma Communications.
