# SISTER: percorso rapido per documenti pronti

## Perimetro

Implementazione rilasciata sul CED il 2026-10-05 alle 16:14 Europe/Rome.
Dettagli e rollback in [SISTER_DEPLOY_2026-10-05.md](SISTER_DEPLOY_2026-10-05.md).
Nessuna modifica a
calendari, account, proprieta, ID remoti, durata di recupero o cooldown.

Prima della ricerca completa in Non evadibili, il worker verifica Espletate e
Prelevate: prima il periodo completo, poi la data odierna Europe/Rome soltanto
se esposta dal controllo SISTER. Il callback di correlazione esistente resta
autorevole; il percorso rapido restituisce soltanto una riga correlata ready.

Se non trova il documento, segue la ricerca completa preesistente, incluse
tutte le date esposte e il trattamento delle richieste non evadibili. Nessuna
eccezione viene nascosta. Non si deduce che una richiesta assente sia terminata,
non si reinvia e non si cancella una richiesta diversa.

## Benefici e limiti

Un PDF gia pronto puo evitare la scansione preventiva delle date storiche di
Non evadibili. I controlli negativi continuano invece a scandire l'intero storico
e pagano anche il costo del percorso rapido. Non e una scansione condivisa fra
richieste, ne una riduzione dell'attesa di produzione sul portale.

Prima di un rollout misurare durata dei poll positivi e negativi, timeout,
PDF persistiti per ora e carico sul portale. Il rapporto tempo/PDF non puo
essere stimato dai soli eventi login: i controlli di sessione riutilizzata
generano anch'essi eventi login. Collegare i PDF attraverso document_id.

## Validazione locale

- 60 test mirati superati; sister_requests_navigation al 100% statement/branch.
- Ruff e make lint-backend contro HEAD superati.
- Quality ratchet mirato contro il merge-base origin/main senza finding.
- Prima: ricerca pubblica cog/cyc/LOC 7/6/31. Ricerca completa estratta senza
  modifiche funzionali: 7/6/30. Classificazione REORGANIZED_AND_CHARACTERIZED,
  non una riduzione del debito: il beneficio prestazionale va misurato sul CED.
- Orchestrazione pubblica cog/cyc/LOC 3/3/12; nuovi helper 3/3/10 e 7/7/23,
  sotto soglia; warning preesistente sui parametri dello snapshot invariato.

Comando test dalla root:

```sh
PYTHONPATH=backend:modules/elaborazioni/worker backend/.venv/bin/pytest -q \
  modules/elaborazioni/worker/tests/test_sister_requests_navigation.py \
  modules/elaborazioni/worker/tests/test_browser_session_correlation_coverage.py \
  modules/elaborazioni/worker/tests/test_sister_reused_menu_html.py \
  --cov=sister_requests_navigation --cov-branch --cov-fail-under=100
```

## Correzione identita checkbox e categorie verificate

Riproduzione offline di cinque artifact di Alessandro, incluso il canary:
tutti espongono la rispettiva identita in input checkbox idElemento nella
categoria radioCount=nonEspletabili. Il parser precedente restituisce identita
null e stato unknown; normalizzando soltanto l'identita il match diventa univoco,
ma lo stato rimane unknown. Non e una prova di lentezza nella produzione PDF.

Il parser ora supporta idElemento sia come campo name=value sia in query string.
La ricerca conserva il match sull'ID remoto e il rifiuto delle identita duplicate.
Per righe senza stato testuale, soltanto una categoria nota con radio checked
univoco permette di inferire lo stato: Espletate/Prelevate diventano ready;
Non evadibili solleva SisterNonEvadibileReviewRequiredError. La classificazione
gia presente nella riga non viene sovrascritta, ne si deduce uno stato da una
categoria non verificata.

Questa eccezione terminale non e un errore di correlazione recuperabile: il
worker marca la richiesta failed per revisione tramite il percorso esistente,
senza defer, reinvio, selezione checkbox o eliminazione globale. Conserva ID,
proprietario, primo invio e ultimo stato remoto persistito; non scrive deleted.
La diagnosi esplicita resta nel messaggio di errore. Il percorso legacy per
righe gia classificate non evadibili non viene modificato da questa slice.

Il canary ha sezione A e subalterno A nella richiesta/item e nel ruolo;
il raccordo catastale canonico espone sezione A e subalterno null. Il recupero
sezioni non ha modificato il subalterno. La divergenza va verificata alla fonte:
non prova da sola il motivo del rifiuto e non autorizza un reinvio automatico.
Il recupero massivo resta subordinato al PDF verificato del canary.

Validazione: 136 test mirati, inclusi DOM Playwright e percorso terminale del
worker, con 100% statement/branch su navigation, request_rows ed exceptions.
Ruff e formato del nuovo test verificati. Ratchet contro origin/main senza
finding: extract_remote_id cog/cyc/LOC 13/7/14 invariato; funzioni di ricerca
invariate; nuovo helper 4/5/20 sotto soglia. Nessuna baseline modificata.
Al momento della validazione locale non era rilasciata in produzione; nessun dato corretto,
account modificato o richiesta remota cancellata.

## Chiusura del ciclo

Verifica finale e matrice comportamenti/test in
[SISTER_FINAL_VALIDATION_2026-10-05.md](SISTER_FINAL_VALIDATION_2026-10-05.md).
148 test mirati e coverage al 100%; build e smoke container superati.
Gate generale chiuso dopo la slice autorizzata sugli import dei test worker:
make test-worker supera 677 test in 49 file; nessuna asserzione indebolita.
Rilascio completato separatamente dopo la validazione. Non dichiarare
l'ottimizzazione prestazionale produttiva completata senza misure successive.
