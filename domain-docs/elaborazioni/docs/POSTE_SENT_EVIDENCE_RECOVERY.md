# Recupero esiti e ricevute delle raccomandate inviate

## Perimetro e fonte

Il recupero avviato il 12 novembre 2026 riguarda le raccomandate già marcate `sent`
nei lotti GAIA, con account mittente, import e tracking coerenti. Il preflight
ha verificato 536 invii: account 1: 153, 2: 102, 3: 113, 4: 66, 5: 102.
Non include le 392 voci ancora in stato bozza: la loro spedizione non è provata
solo dalla presenza in GAIA e richiede una riconciliazione distinta.

La normale riconciliazione dei lotti cerca nell'archivio le bozze scomparse;
non è un aggiornamento periodico degli esiti di tutte le raccomandate `sent`.
Il nuovo strumento separa due letture, entrambe verificate su un campione reale:

- Tracking: richiesta JSON del webview ufficiale Poste a
  `https://www.poste.it/online/dovequando/DQ-REST/ricercasemplice`, con
  `tipoRichiedente=WEB`, `codiceSpedizione` e `periodoRicerca=1`. Non richiede
  login ai cinque account e non interroga `dettaglio.do`. Conserva la risposta
  originale, inclusi movimenti, codici, sintesi e indicazione di ritorno.
- Ricevuta di accettazione: dettaglio sul solo account del lotto, estrazione
  del riferimento dalla funzione `MostraAnteprima` della pagina, lettura di
  `recuperaRicevutaAccettazione.do` con lo stesso modulo del portale. Il PDF
  viene conservato soltanto se è valido e contiene il tracking atteso come
  numero completo, non come sottostringa di un numero più lungo.

Il controllo non aggira 403, OTP o CAPTCHA, non cambia account per leggere
uno stesso invio e non ripete automaticamente richieste rifiutate. Non crea
bozze, non invia raccomandate e non chiama pagamenti. Il dettaglio generico
`Servizio erogato` e la ricevuta di accettazione non attestano la consegna.
L'avviso di ricevimento è un documento distinto: non viene dichiarato acquisito
se il portale ha esposto soltanto la ricevuta di accettazione.

## Codice

- `modules/elaborazioni/worker/posta_online_delivery.py`: client di lettura,
  controlli di identità e verifica PDF.
- `scripts/poste_recover_sent_evidence.py`: piano, checkpoint, selezione per
  account e recupero. Non scrive nel database e non modifica i dati mostrati
  dalla UI. L'integrazione delle nuove evidenze nella UI è un intervento distinto.

Le evidenze reali sono private, fuori dal repository:
`/opt/gaia/runtime-data/poste-refresh-20261112/evidence` sul CED, montato nel
container come `/runtime-data/poste-refresh-20261112/evidence`.
Il file `plan.json` congela identità e account; ogni item ha `tracking.json`,
`receipt.json` e, quando disponibile, `acceptance.pdf`. File 0600 e nuove
cartelle 0700. Il PDF ha hash SHA-256, dimensione, pagine e data di osservazione.
Non includere dati dei destinatari, credenziali o ricevute nel repository.

## Esecuzione e ripresa

Usare un ambiente con dipendenze backend e worker e impostare `PYTHONPATH`
per backend/worker. La copia operativa sul CED è in una directory `tools`
privata del recupero; non sostituisce l'immagine del worker.

```bash
python scripts/poste_recover_sent_evidence.py --output /percorso/privato --phase plan
python scripts/poste_recover_sent_evidence.py --output /percorso/privato --phase tracking --limit 536
python scripts/poste_recover_sent_evidence.py --output /percorso/privato --phase receipts --limit 536
```

`--account ID` restringe il recupero a un account. Il limite conta gli elementi
ancora da tentare; i risultati riusciti non vengono riletti. Una nuova fotografia
completa richiede una nuova directory. Se il piano corrente non coincide con
quello congelato, l'esecuzione si ferma. Gli errori già registrati si ritentano
solo con `--retry-errors`, dopo averne valutato la causa.

Il tracking usa un client HTTP riutilizzato e pause di 5–9 secondi; si ferma al
primo CAPTCHA, 403/429 o dopo due errori consecutivi. Le ricevute usano una sessione nuova
per account, i ritmi prudenti del client Poste e un lease esclusivo per evitare
sovrapposizioni con il worker. Un errore termina la sessione di quell'account.
Il codice finale registra anche gli errori di apertura dell'account e prosegue
con gli altri; non considera riusciti gli invii non letti. Un lock locale per
directory (`.recovery.lock`) impedisce esecuzioni concorrenti anche tra fasi
diverse dello stesso piano. Alla ripresa, una ricevuta segnata disponibile
deve avere il PDF presente con lo stesso SHA-256: in caso contrario il recupero
si ferma per revisione, senza ignorare il documento mancante o alterato.

L'exit code da solo non certifica il recupero: confrontare sempre il piano
con i file di evidenza, gli errori e i PDF disponibili. Un file di tracking
indica un'osservazione del servizio, non necessariamente un esito finale.
Le ricevute assenti e gli errori rimangono espliciti, senza inventare esiti.

## Validazione finale del 17 novembre 2026

Il branch `fix/poste-evidence-release-20261117` parte da `31790da2`, che
contiene i prerequisiti Poste, e aggiunge soltanto i sei file del recupero e
la sincronizzazione della baseline dopo il ratchet. Il deploy riguarda solo
i due strumenti standalone, non il codice applicativo di quel commit storico.
La base usata inizialmente, `d867f17d`, includeva anche lavori successivi su
Presenze: il 17 novembre il ratchet globale ha confermato gli stessi 20 finding
già riprodotti sul commit base. Quei commit non fanno parte del branch di
rilascio, e i file estranei nel workspace principale sono preservati.

- 55 test mirati passati; coverage full-file dei due runtime: **100% statement
  e branch**, 220 statement e 74 branch, zero mancanti o esclusioni nuove.
- 55 test di regressione passati sul branch di rilascio: client, portale
  dispatch, lease e cooldown. La verifica sul checkout più recente ha passato
  anche i 69 test comprendenti il recupero liste. La differenza nel portale
  riguarda `_list_page`, non chiamato dal recupero ricevute; il bundle non
  sostituisce il portale installato. Non è una certificazione dell'intera suite GAIA.
- Ruff, formatter dei quattro file Python nuovi e `make lint-backend` passano.
- Ratchet del nuovo modulo worker rispetto al merge-base `origin/main`
  `686e529e` senza finding. Metriche modulo: 6 callable, massimi
  ciclomatico/cognitivo 9/9, nesting 2, zero violation.
- Audit esplicito anche dello script operativo, fuori dallo scope standard
  dello scanner: 11 callable, massimi ciclomatico/cognitivo 13/23, nesting 4,
  zero error-level; rimangono warning nei controlli di identità, ripresa e
  orchestrazione. Non sono state cambiate soglie o esclusioni.
- Ratchet globale del branch di rilascio contro `origin/main` **PASS**, zero
  finding; nessuna soglia o esclusione modificata. La sincronizzazione della
  baseline aggiunge esclusivamente il nuovo modulo worker e i suoi test:
  nessun record legacy modificato o rimosso. `make complexity-baseline-verify`
  **PASS** prima del commit: baseline riproducibile.
- Canary reale: ricevuta di accettazione account 2 verificata con parser PDF
  e rendering visuale. Il parser finale ha validato tutti i 246 PDF già
  acquisiti sul CED, verificando tracking e SHA-256 senza alterare le evidenze.

### Comportamenti coperti

| Comportamento | Prova pertinente |
| --- | --- |
| Endpoint e payload ufficiale, tracking ASCII, identità risposta e movimenti | Test client tracking, rifiuto prima della rete per input invalidi |
| CAPTCHA, 403/429, massimo due errori consecutivi, azzeramento dopo successo | Test arresto e checkpoint, conteggio richieste effettivamente tentate |
| Azione ricevuta consentita, modulo nascosto, ambiguità e tracking completo | Test HTML osservato con mutazioni di identità e azione |
| PDF valido, limite dimensione, testo assente o numero non corrispondente | PDF reali generati nei test, compreso un PDF vuoto |
| Salvataggio ricevuta e ripresa | Parsing reale del PDF, file persistiti, metadati e hash; rifiuto PDF mancanti/alterati |
| Account originario, lease esclusivo, sessione nuova, errore login | Test sui confini browser/DB, rilascio del lease e assenza di richieste successive |
| Prosecuzione degli altri account dopo un errore di apertura | Risultati parziali distinti per account |
| Piano immutabile, DB read-only, limiti e selezione account | Test piano e runner; smoke read-only reale della prima esecuzione |
| CLI ed esclusione reciproca tra fasi | Entrypoint realmente eseguito, piano prodotto, lock di sistema conteso |

Comando coverage riproducibile, con dipendenze backend/worker installate:

```bash
DATABASE_URL=sqlite:////tmp/gaia-poste-tests.db JWT_SECRET_KEY=local-poste-test-only \
PYTHONPATH=backend:modules/elaborazioni/worker:. python -m pytest -q \
  modules/elaborazioni/worker/tests/test_posta_online_delivery.py \
  tests/test_poste_recover_sent_evidence.py \
  --cov=posta_online_delivery --cov=scripts.poste_recover_sent_evidence \
  --cov-branch --cov-report=term-missing --cov-fail-under=100
```

I test sostituiscono la connessione DB e i servizi esterni ai loro confini;
non richiedono credenziali Poste né effettuano invii o pagamenti.
Log, coverage e metriche della verifica: `/tmp/gaia-poste-final-20261117/`.
La strategia e i gate coverage del repository restano invariati.

## Stato del rilascio

Deploy completato e verificato il **17 novembre 2026**, commit runtime
`879df2213d19552cb1ec7a25dee3930aba57ec63`, pubblicato sul branch
`fix/poste-evidence-release-20261117`. Copia attiva in `tools/` corrispondente
al commit per entrambi gli SHA-256; backup della versione precedente in
`backups/before-879df2213d19552cb1ec7a25dee3930aba57ec63/`.

Il rilascio è limitato a `posta_online_delivery.py` e
`poste_recover_sent_evidence.py`, con archivio immutabile per commit sotto
`/opt/gaia/runtime-data/poste-refresh-20261112/releases/` e copia operativa in
`tools/`. Conservare il backup della precedente copia, verificare SHA-256 e
assenza di processi di recupero attivi prima di sostituirla. Non cambia
l'immagine del worker, non richiede restart o migrazioni e non aggiorna la UI.

Smoke eseguito sia dalla release versionata sia dalla copia attiva:
`--phase plan` in sola lettura sul database, **536 identità coerenti** con il
piano congelato. Il client effettivamente importato da `tools/` ha validato
le **246 ricevute**, inclusi tracking e SHA-256; ripresa verificata con 289
ricevute e 517 tracking non tentati. Nessuna richiesta a Poste durante lo smoke.
Il manifest privato `deployment.json` della release riporta `status=verified`.
Il recupero non è stato riavviato e la consegna dei restanti invii non è provata.
Non riavviare il tracking finché resta la richiesta CAPTCHA.

```bash
docker exec -e PYTHONPATH=/runtime-data/poste-refresh-20261112/tools:/app/worker:/app/backend \
  gaia-elaborazioni-worker-poste python \
  /runtime-data/poste-refresh-20261112/tools/poste_recover_sent_evidence.py \
  --output /runtime-data/poste-refresh-20261112/evidence --phase plan
```

Stato operativo del deploy e relativo commit sono registrati nel manifest
privato del rilascio sul CED. Il rollback ripristina i due file dal backup,
con nessun recupero attivo; conserva `evidence/` e i relativi checkpoint.

## Blocco effettivo del tracking nel recupero esteso

Dopo 17 osservazioni valide, due richieste hanno ricevuto HTTP 400. Una prova
diagnostica tramite il webview ufficiale, sullo stesso tracking, ha confermato
HTTP 400 con errore `id=2`, `tipo=error` e descrizione:
`Non e' possibile effettuare ulteriori richieste senza specificare una captcha valido`.
La pagina mostra «Servizio momentaneamente non disponibile, riprovare più tardi».

Il recupero tracking è fermo: 17 risultati, 2 errori, 517 non tentati. Non
riprendere cambiando IP, account o endpoint per eludere la verifica. Serve un
flusso interattivo supportato o un servizio contrattuale per il tracking massivo.
Il codice finale distingue `InteractiveCheckRequired` e si ferma al primo
errore CAPTCHA, conservando il checkpoint. Nessun esito finale è dedotto da
questa risposta. Le 17 risposte raccolte esponevano codice stato `3`, «In
transito» nel codice del webview ufficiale, non «Consegnata».

Il controllo finale del 17 novembre ha rilevato **246 PDF di accettazione**:
144 per account 1 e 102 per account 2. Sono presenti 247 osservazioni ricevuta:
246 riuscite e un errore di sessione non autenticata sull'account 1. Restano
289 elementi non tentati e un errore; gli account 3, 4 e 5 non hanno ricevute
acquisite da questa esecuzione. `receipts-run.exit=1`: il vecchio runner si è
fermato durante un login successivo con timeout di navigazione. Non vi è prova
di completamento del recupero dei cinque account.

La prima esecuzione operativa usa la revisione validata prima dell'aggiunta dei
lock CLI e del riconoscimento esplicito CAPTCHA. Hash script:
`5e5a0dda721c15ef6163fa19c88c5972ab7f32ccfa61b0210b9ef283725bdffa`;
hash client: `e7ef43ddaa0f6424f29be11f4bed08986946ddb0725f9113ed5bae16c3967451`.
Il tracking di quella revisione si è fermato dopo due errori consecutivi.
Questi hash identificano la revisione precedente, conservata nel backup di
rilascio. La revisione finale usa il lock unico `.recovery.lock`; non avviare
contemporaneamente copie vecchie e nuove nella stessa directory.
