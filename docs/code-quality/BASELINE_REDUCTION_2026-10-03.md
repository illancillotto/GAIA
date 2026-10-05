# Baseline — riduzione reale, 2026-10-03

## Decisione e perimetro

L'utente richiede di ridurre il codice prima di aggiornare la baseline,
non di sostituire la fotografia del debito con numeri desiderati. Soglie,
scope, eccezioni e gate restano invariati. Una sola unita revisionabile per
slice; nessun commit, push o intervento sui lavori concorrenti.

Audit completo del solo codice committato a `main@fccd06b0`, in worktree
detached: 1580 file e 19591 callable; 4731 violation, delle quali 2043 error
e 2688 warning. Una funzione puo avere piu violation. I 23 finding che
bloccavano l'aggiornamento baseline sono regressioni rispetto alla fotografia
precedente, non l'intero debito sopra soglia del progetto.

## Prima slice — `DataService.call`

Runtime: `backend/app/modules/wiki/mcps/data/service.py`.
Responsabilita separate: costruzione della risposta query con provenance,
errori e stima token in `_call_response`; orchestrazione, misura del tempo,
telemetria e audit in `call`. Il lookup della scope opzionale usa il registro
query senza ripetere il controllo di appartenenza.

| Metrica | Prima | Dopo |
| --- | --- | --- |
| Target cognitiva/ciclomatica | 13 / 10 | 2 / 3 |
| Target LOC/nesting/parametri | 60 / 2 / 4 | 25 / 1 / 4 |
| Nuovo `_call_response`: cognitiva/ciclomatica/LOC | — | 10 / 7 / 38 |
| Nuovo helper: nesting/parametri | — | 2 / 4 |
| File somma cognitiva/ciclomatica | 58 / 48 | 57 / 48 |
| File LOC/callable | 172 / 9 | 175 / 10 |
| File warning/error | 5 / 0 | 3 / 0 |

Target e nuovo helper sotto tutte le soglie warning. Nessuna violation
trasferita al helper. Classificazione **IMPROVED**, ma la riduzione reale
aggregata e di un punto cognitivo: il calo del target deriva soprattutto
dalla separazione delle responsabilita, non da una riduzione equivalente
dell'intero algoritmo. Ciclomatica aggregata invariata.

Restano i warning preesistenti di `_read` e `_execute`, non rifattorizzati in
questa slice. Auth, query parametrizzate, schema DB, protocollo e API invariati.

## Invarianti e prove

Sei nuovi casi di caratterizzazione: successo paginato, risultato vuoto,
tool ignoto, scope negato, limite superato e errore dello storage audit.
Verificati forma completa della risposta, provenance, correlazione, scope,
unica scrittura audit con gli stessi oggetti risposta/argomenti e log prima
di un errore audit propagato. Nessun errore audit viene assorbito.

La sequenza interna di aggiornamento della risposta e gestione eccezioni e
invariata, inclusi errori database/interni minimizzati e stima token prima
dell'aggiunta del suo campo. Nessuna nuova esclusione coverage.

- Prima della modifica runtime: 90 test dominio/console passati, full-file
  106/106 statement e 22/22 branch, 100%.
- Dopo: 129 test dominio, console, HTTP e integrazione passati, full-file
  109/109 statement e 22/22 branch, 100%.
- Ruff sui due file e `make lint-backend BASE_REF=HEAD` sullo snapshot
  isolato: PASS. Whitespace del perimetro: PASS.
- Scanner completo sullo snapshot isolato, confronto con baseline del
  merge-base: nessun finding nuovo; restano due finding ereditati del
  costruttore, quindi **ratchet exit 1**, non PASS.
- `complexity.py check` completo: finding baseline **23 -> 20**;
  violation globali **4731 -> 4729**, warning **2688 -> 2686**,
  error **2043 invariati**. I lavori concorrenti non entrano nello snapshot.

## Perche la baseline non viene ancora aggiornata

I tre finding di `DataService.call` sono eliminati. Nel suo file restano
`DataService.__init__`: LOC `7 -> 8` e parametri `2 -> 3` rispetto alla
baseline, entrambi identici al commit base. Il parametro audit opzionale e
una funzionalita gia committata: riportarlo al vecchio numero eliminandolo,
nascondendolo in `kwargs` o comprimendo il codice non sarebbe una riduzione
sicura e contrattualmente equivalente.

Questi numeri del costruttore sono sotto le soglie del progetto; tuttavia il
ratchet vieta comunque aumenti non registrati rispetto alla baseline. I 20
finding residui non sono automaticamente errori sopra soglia, ne difetti
funzionali. La loro revisione deve distinguere semplificazioni sicure da
estensioni funzionali necessarie, senza cambiare API per soddisfare un numero.

**Baseline invariata.** La sincronizzazione ordinaria non viene eseguita dopo
un ratchet non verde. Non si dichiara `baseline-verify` superato. La prima
slice dimostra una riduzione reale ma non chiude la riconciliazione globale.
Un eventuale recupero delle estensioni funzionali approvate richiede una
decisione esplicita e separata; non e implicito nel presente refactoring.

## Evidenze e prossime azioni

Metriche `/tmp/gaia-mcp-data-{before,after}.{json,md}`; log e coverage
`/tmp/gaia-mcp-data-*`; audit completo `/tmp/gaia-baseline-audit-20261003.*`.
Graphify Wiki consultato e aggiornato col target codice e pruning force:
115 file AST, 985 nodi, 2361 archi. Grafi ignorati e non versionati.

Fermarsi al singolo hotspot verificato. Possibile slice successiva:
`DataService._execute`, cognitiva 16 e ciclomatica 10; richiede nuovamente
invarianti, metriche prima/dopo e coverage full-file. Non dichiarare l'intero
repository sotto soglia, ne proseguire con refactoring massivi.
