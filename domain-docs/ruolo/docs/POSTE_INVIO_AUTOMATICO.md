# Poste: Predisposizione Invio Automatico

## Stato Al 2026-09-21

Richiesta: predisporre anche l'invio automatico e tracciare gli endpoint Poste.
Questo blocco introduce un **contratto interno eseguibile e testato**, non un
connettore operativo. Nessuna spedizione, autenticazione live o modifica al
portale e stata eseguita. Nessun dato operativo o storage state letto.

- `backend/app/modules/ruolo/notice_dispatch_contract.py`: envelope immutabile,
  controlli richiesti all'approvazione/claim e transizioni di spedizione.
- `backend/app/modules/ruolo/services/poste_endpoint_inventory.py` e
  `scripts/poste_endpoint_inventory.py`: inventario locale da HAR, senza rete
  e senza replay delle richieste.
- Nessuna route, UI di invio, tabella outbox o worker di spedizione e collegato
  al contratto. `require_poste_submission_adapter()` rifiuta sempre l'invio;
  non esiste una variabile ambiente che lo abilita.

La richiesta conferma che va previsto il canale automatico. Sono ancora da
confermare prodotto postale, account/ambiente di test e disponibilita di API
ufficiali. Se esiste un contratto API aziendale, preferirlo agli endpoint del
portale. Non assumere che il contratto del portale consenta tutte le operazioni.

## Cosa Conosciamo

Fonte: `modules/elaborazioni/worker/posta_online_client.py`, non una nuova
osservazione live. Il client esistente autentica e legge lo storico:

| Host | Percorso | Uso nel client |
| --- | --- | --- |
| `www.posta-online.it` | `/` | Accesso portale |
| `idp-business.poste.it` | `/jod-idp-business/cas/login.html` | Login/SSO |
| `corrispondenza.poste.it` | `/col/archivio.do` | Archivio e navigazione |
| `corrispondenza.poste.it` | `/col/gestioneListeContatti.do` | POST lettura contatti |
| `corrispondenza.poste.it` | `/col/dettaglio.do` | POST lettura dettaglio |

Il dettaglio usa multipart con `idInvio`, `numrows`, `controller`. Il metodo
POST non identifica da solo una spedizione: e usato anche per letture.
`idInvio`, numero documento GAIA e tracking postale sono namespace distinti.

Credenziali cifrate, fasce orarie e job di lettura esistono in
`backend/app/services/elaborazioni_posta_online.py`. Il worker supporta sessione
browser/CDP e segnala l'autenticazione interattiva; non aggirare OTP/MFA.
Non riutilizzare `_request_with_backoff` per operazioni di scrittura: i retry
automatici su timeout/5xx potrebbero duplicare una spedizione o un addebito.

## Acquisire Il Contratto

Preferire ambiente Poste di test e destinatari sintetici. Per una sessione
assistita sul portale reale serve delimitare prima account, prodotto e azioni
consentite. Fermarsi prima della conferma/invio/addebito; anche caricamento e
salvataggio bozza possono avere effetti remoti. Non eseguirli implicitamente
per il solo scopo di scoprire endpoint. Per osservare l'invio finale occorrono
sandbox oppure autorizzazione separata per una specifica spedizione reale.

1. Aprire DevTools Network nella sessione autorizzata e attivare Preserve log.
2. Annotare localmente ordine delle azioni, prodotto e ambiente; acquisire
   solo il flusso concordato, senza duplicare submit o aggirare MFA.
3. Conservare l'HAR grezzo fuori dal repository in una directory privata
   (`0700`, file `0600`). L'HAR puo contenere credenziali, cookie, destinatari e
   documenti anche se il browser lo definisce sanitized. Non inviarlo a Graphify,
   chat, issue, log, storage pubblico o servizi esterni.
4. Produrre l'inventario minimizzato con il comando locale sottostante.
5. Revisionare i percorsi oscurati localmente nel HAR. Solo dopo aver verificato
   che un percorso sia tecnico e non contenga dati personali/token, ripetere il
   comando con `--reviewed-path /percorso/tecnico`. Non passare URL completi,
   query, cookie o credenziali. Ogni output deve avere un nome nuovo.
6. Definire fixture sintetiche request/response e classificazione degli errori
   per ogni operazione; un HAR osservato non e da solo un contratto affidabile.

```bash
backend/.venv/bin/python scripts/poste_endpoint_inventory.py \
  /percorso/privato/poste.har \
  --output /percorso/privato/poste-inventory.json
```

Il tool non effettua richieste. Accetta al massimo 32 MiB/20000 richieste e
solo i tre host HTTPS esatti censiti sopra sulla porta standard, senza userinfo.
Nuovi host richiedono una revisione esplicita del codice, non wildcard `*.poste.it`.
Esclude intestazioni, cookie, query, corpi, nomi dei campi e timestamp; esporta
metodo, stato HTTP e tipi MIME da allowlist. I percorsi non revisionati sono
identificati con HMAC casuale stabile solo dentro il singolo report, non con
hash riutilizzabili fra acquisizioni. Anche gli errori sono privi di dati grezzi.
L'output e creato esclusivamente nuovo, con permessi `0600`, senza sovrascrivere
file o seguire symlink esistenti. `--reviewed-path` e una dichiarazione locale
dell'operatore: non e un anonimizzatore per un percorso contenente dati personali.

### Operazioni Da Osservare, Non Endpoint Inventati

| Operazione | Evidenze richieste |
| --- | --- |
| Sessione/account | Scadenza, MFA, CSRF, redirect login anche con HTTP 200 |
| Prodotto e opzioni | Codice prodotto, formati, destinatari, limiti e costi |
| Upload | Multipart, limiti PDF, risposta, identificatore documento, cleanup |
| Creazione bozza | Correlazione bozza/account/documento; effetti e idempotenza |
| Validazione/preventivo | Errori destinatario, totale, validita del preventivo |
| Conferma/invio | Effetto irreversibile, risposta positiva certa, riferimenti |
| Ricerca esito | Ricerca univoca dopo timeout, ritardo indicizzazione, paginazione |
| Ricevuta/tracking | Identificatori distinti, formato e download delle prove |

Non dedurre l'assenza di invio da una ricerca vuota: il portale puo essere
eventualmente consistente. Non dedurre un rifiuto certo dal solo 4xx/5xx o un
successo dal solo 2xx. Non inventare un header `Idempotency-Key` se Poste non lo
supporta contrattualmente. Le fixture approvate devono usare dati sintetici.

## Logica Predisposta

L'envelope identifica UUID/versione documento, credenziale e digest SHA-256 di
account, file esatto, destinatario e opzioni postali. I digest non sostituiscono
la conservazione privata dell'artefatto; account/opzioni/destinatario richiedono
una serializzazione canonica concordata con l'adapter. La chiave di deduplica
locale include tutti questi dati e **non** garantisce idempotenza su Poste.

| Stato/evento | Risultato |
| --- | --- |
| `draft` + approvazione | `ready`, solo con tutti i riscontri server |
| `draft`/`ready` + annullamento | `cancelled`, prima del submit |
| `draft`/`ready` + dati cambiati | `blocked`, serve nuova preparazione |
| `ready` + avvio | `submitting`, con nuova verifica prima del claim |
| `submitting` + ricevuta positiva | `accepted` |
| `submitting` + rifiuto certo documentato | `rejected` |
| `submitting` + timeout/crash/esito ambiguo | `unknown` |
| `unknown` + riscontro autorevole | `accepted` o `rejected` |

La revisione server scade e deve riferirsi allo stesso envelope. Sono richiesti
ammissibilita, coordinamento con tutti i writer, file verificato, contratto
Poste verificato e approvazione esplicita. `SubmissionReview` NON e un payload
client: un futuro endpoint non deve accettare booleani/prove dal browser.
Il GET consultivo `ammissibilita` non puo produrre questa autorizzazione.

Esiti definitivi richiedono ID operazione del provider e riferimento a evidenza
privata, vincolati allo stesso envelope. Nessuna transizione imposta notifica
perfezionata o STEP. Stato `unknown` senza transizione di retry/cancel locale;
esiti definitivi terminali. Eventuali nuovi invii richiedono un nuovo processo
approvato, non la riapertura silenziosa dell'intento precedente.

## Collegamento Operativo Ancora Da Implementare

Il contratto puro calcola transizioni: non dimostra autenticita delle prove,
non acquisisce lock e non garantisce durabilita. Per attivarlo servono:

1. Outbox SQL con intenti/versioni, envelope/artefatto immutabile, audit append-only,
   vincoli deduplica, blocco di intenti attivi sovrapposti per posizione/account
   anche su documenti/versioni diversi e separazione dalle semplici bozze.
2. Conferma del lotto e claim con autorizzazione server, verifica coordinata di
   saldo/notifica/STEP/import/orfani/policy; risolvere i sei casi concorrenti
   documentati in `REGISTRO_AVVISI_IMPLEMENTAZIONE.md` prima dell'attivazione.
3. Commit di `submitting` PRIMA dell'I/O, token di claim e un solo worker;
   recupero dei claim abbandonati in `unknown`. Evitare transazioni SQL aperte
   durante la rete. Un crash non deve rispedire il lotto automaticamente.
4. Adapter del contratto verificato, gestione sessione/MFA, tempi limite,
   riconciliazione univoca e prove. Senza idempotenza/ricerca autorevole offerta
   dal provider, non promettere exactly-once e mantenere revisione manuale.
5. Registrazione atomica dell'accettazione con tentativo/evidenza/audit nel
   registro, senza chiamare il comando manuale di invio passato e senza dedurre
   notifica. Riconciliare gli import Poste evitando duplicati di eventi/provider.
6. UI lotto/approvazione/esiti e permesso specifico per invio con costo; collaudo
   in sandbox di crash, timeout, doppio click/worker, login HTML 200, pagamenti
   concorrenti, import tardivi, ricevute duplicate e fallimento commit locale.

Il confine irreversibile dell'invio esterno deve essere esplicito: un pagamento
arrivato dopo il claim non puo essere annullato semplicemente con rollback SQL.
La policy per cambiamenti fra claim e accettazione va definita con l'operatore,
non nascosta dietro un presunto controllo atomico sul portale remoto.

## Verifiche Del Blocco

73 test passati. Coverage full-file sui due runtime nuovi e sulla CLI:
130/130 statement, 24/24 branch, 100%, senza esclusioni di linee. Prima esecuzione
coverage aveva selezionato solo i runtime backend; il repeat con configurazione
isolata include anche la CLI (import e entrypoint reale) ed elimina quel limite.
Testano identita, scadenza, transizioni, assenza retry dopo submit, privacy HAR,
allowlist, input malformati, limiti e output privato senza sovrascrittura.

Metriche nuove: contratto LOC 117, inventario LOC 81; prima entrambi assenti,
nessun debito preesistente
toccato. Massimi cognitiva/ciclomatica 8/6 e 14/11, due warning non bloccanti
nell'inventario. Metriche in `/tmp/gaia-poste-foundation-after.json`.
Lint mirato e `make lint-backend BASE_REF=ec5b1375` passano. Il ratchet globale
rileva una modifica concorrente Presenze in `daily_records.py`, estranea a questo
blocco; non modificata per renderlo verde. Baseline/soglie/esclusioni invariate.
Il ratchet mirato ai due runtime contro `ec5b1375` passa con `findings: []`;
non viene dichiarato verde il gate globale. Il commit concorrente `d47679e0`
ha registrato le modifiche WhatsApp precedenti; non e stato creato da questo lavoro.
Log test e coverage: `/tmp/gaia-poste-foundation-final-tests.log`,
`/tmp/gaia-poste-foundation-final-coverage.json`.
