# Multi-hop codice avviso → pagamenti — 2026-10-01

## Analisi della causa

Tracce originarie: `comparison-live-2026-10-01-validated.jsonl`, caso `payments`.
La domanda identifica l'avviso tramite `SYN-N0121`. Il catalogo originale espone
`account_code` ma non `notice_code` in `search_role_notices`; `get_role_notice`
richiede un UUID che la domanda non fornisce. La capability richiesta e quindi
incompleta, non soltanto un problema di prompting o numero di iterazioni.

Entrambe le ripetizioni iniziano applicando erroneamente
`account_code=SYN-N0121`. Il database restituisce correttamente zero risultati:
l'utenza collegata e `SYN-A0121`, namespace distinto dal codice avviso.

- Ripetizione fallita: una chiamata, 85 token di evidenze, poi `absent` falso.
  Nessun errore di servizio, scope, autenticazione o budget esaurito.
- Ripetizione riuscita: toglie il filtro, legge 25 avvisi, trova quello richiesto
  nella prima pagina e usa il suo UUID per ottenere un pagamento. Tre chiamate,
  2892 token. Il successo dipende dalla posizione UUID del record; una pagina
  troncata non garantisce di trovare un codice arbitrario.

Verifica deterministica offline con replica `gaia-v1`: filtro errato zero righe;
avviso esistente con UUID `0043a6f7-7634-5cd6-a6ad-a0551f40e043`, codice utenza
`SYN-A0121`; pagamento `20b06d8e-a7d0-58ea-889e-a5e874f143e7`, importo `188.05`.
Il codice utenza corretto restituisce due avvisi, quindi neppure sostituire
meccanicamente il prefisso N con A identifica univocamente l'avviso richiesto.

## Correzione implementata

1. `SearchNotices.notice_code`: filtro opzionale esatto, stesso tipo/limiti degli
   altri filtri testuali; compatibilita delle chiamate esistenti preservata.
2. `NOTICE_FILTERS`: confronto parametrizzato `t.notice_code=:notice_code`,
   combinato con AND con gli altri filtri. Nessun SQL arbitrario, nuova tabella,
   migration, dipendenza o modifica di dataset/schema.
3. Descrizioni schema: distinzione codice avviso/codice utenza/UUID; UUID avviso
   ottenuto dalle evidenze, mai dedotto dal nome/codice.
4. Catalogo MCP: contratto esplicito `notice_code → risultato.id → notice_id`,
   significato limitato di zero risultati e paginazione dei pagamenti.
5. Manifest sperimentale: hash anche di inputs/queries/server/service Data e
   client, non solo orchestrazione. Un cambiamento del catalogo non puo essere
   ripreso nello stesso journal come se fosse la stessa configurazione.

Non introdotti orchestratori paralleli, retry automatici della risposta,
fallback basati sull'oracle, parsing hardcoded di `SYN-N0121`, aumento budget
o obbligo artificiale di due chiamate per ogni domanda. Scope `ruolo.read`,
autenticazione, read-only, provenance e blocco Docs restano invariati.
Il server non trasforma `account_code=SYN-N0121` in una ricerca diversa:
un filtro semanticamente errato continua a restituire zero senza ampliare accessi.

## Test e failure path

- `test_notice_code_lookup_payment_chain_and_filter_identity`: avviso fuori
  dalla prima pagina, ricerca esatta, payment chain, provenance, filtri AND,
  conflitto filtri, codice inesistente, namespace errato, SQL injection come
  valore, input vuoto/tipo errato/lungo, permesso negato e descrizioni schema.
- `test_comparison_uses_real_sdk_catalog_and_http_tools_without_docs`: catalogo
  reale HTTP/SDK/bearer, schema `notice_code` trasmesso al client, agente corrente
  su due tool sequenziali con modello simulato, no-answer e zero richieste Docs.
- Suite MCP completa copre anche null/default, paginazione/cursor, permessi,
  fonte remota errata, budget e compatibilita degli altri tool. Non rimossi test.

I test simulati provano il contratto e il flusso, non che un modello esterno
scegliera sempre i parametri corretti. Per questo e prevista una prova live
separata con piu ripetizioni positive e negative.

## Limiti e criteri di lettura

Il filtro risolve il difetto di capability; non rende ogni risposta del modello
corretta per definizione. `absent` resta una decisione del modello e lo scorer
locale ne verifica la correttezza sul dataset sintetico. Un risultato zero
con filtri sbagliati non prova l'assenza dell'entita richiesta. Non introdurre
un validatore generale di semantica naturale senza un contratto dedicato.

La baseline Static resta invariata: retrieval lessicale senza espansione delle
relazioni. Nessuna conclusione statistica da questo campione limitato. Artifact
precedenti conservati, nuovo journal `multihop-notice-code-v1.jsonl` ignorato da
Git; freeze dei checkout tesi e modifiche concorrenti preservati.

## Risultati realmente eseguiti

- Suite MCP: **186 test PASS**, **1342/1342 statement e 250/250 branch (100%)**,
  zero esclusioni aggiunte. Test deterministico include anche avviso esistente
  senza pagamenti, distinto da avviso inesistente; modello simulato nei test HTTP.
- Regressioni API chat/articoli Wiki: **100 PASS**, soli warning legacy per
  lunghezza della chiave JWT dei test. Nessun frontend runtime modificato qui.
- Ruff check/format-check del perimetro: PASS. Ratchet mirato `origin/main`:
  `findings=[]`. Quattro runtime toccati: 20 callable, 0 error, 5 warning;
  nuova logica di ricerca dichiarativa, budget/callable dell'agente invariati.
- Graphify tramite `make graphify-wiki-code`: PASS, nessuna estrazione docs
  remota. Nessun cambiamento strutturale del grafo necessario all'ultimo refresh.
- Lint globale ancora FAIL su import del test Presenze PostgreSQL concorrente;
  ratchet globale ancora FAIL con 10 finding esclusivamente Presenze allo snapshot.
  Non corretti fuori scope, baseline/eccezioni non modificate. Il working tree
  e HEAD cambiano per lavoro concorrente: non e uno snapshot di release congelato.

Pilot **live** nuovo, non simulato: due casi (pagamenti esistenti e avviso
inesistente), cinque ripetizioni per condizione, seed dataset `gaia-v1`.
Provider reale `gpt-reserve` da configurazione esistente, server HTTP/SDK/bearer
reali e principal sintetico; nessun login/DB operativo. Tutti i documenti della
fixture sono sintetici e le richieste Docs osservate sono **zero**.

| Condizione | Esecuzioni complete | Risposte corrette | p50 ms | p95/p99 ms |
| --- | ---: | ---: | ---: | ---: |
| MCP | 10/10 | 10/10 | 9114.950 | 21008.814 |
| Static lessicale | 10/10 | 5/10 | 4912.604 | 12597.388 |

MCP usa sempre il filtro `notice_code` corretto: nei cinque positivi effettua
esattamente due chiamate ricerca→pagamenti; nei cinque negativi effettua una
ricerca esatta a zero risultati. Nessun tentativo di scansione generica,
nessun retry infrastrutturale, massimo due tool e 367 token di evidenze.
Static risolve i negativi, fallisce i positivi per il limite relazionale gia
documentato. Il campione non dimostra perfezione generale o significativita
statistica; conferma il percorso corretto in queste ripetizioni osservate.

Raw journal e summary ignorati: `runtime-data/mcps/evaluation/
multihop-notice-code-v1.jsonl` e `.summary.json`. Hash dei runtime del manifest
verificati uguali alla versione consegnata. Tracce iniziali fallite preservate,
nessun aggiornamento di oracle/schedule storico per nascondere l'errore.
Log locali: `/tmp/gaia-multihop-{tests-final,live,regression,ratchet,lint-global,
ratchet-global,graph-final}.log`. Nessun commit, push o deploy eseguito da questo
ciclo. Il gate globale resta FAIL per i controlli esterni citati, non per il
percorso multi-hop verificato.
