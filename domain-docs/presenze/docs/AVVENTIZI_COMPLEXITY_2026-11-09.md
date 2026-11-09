# Avventizi: riduzione della complessità e controlli — 9 novembre 2026

Stato: refactoring verificato; commit e push richiesti dall'utente il 9 novembre
2026 dopo la comunicazione dei due residui LOC. Il ratchet resta FAIL.
Il comportamento di riferimento è la feature Avventizi già preparata, non il
solo HEAD `023a8bd5`, che non contiene ancora la sua proiezione runtime.

## Invarianti e perimetro

AG resta una presentazione derivata di una giornata lavorativa trascorsa,
senza timbrature o lavoro e senza altre assenze o richieste. Il contratto deve
coprire la data; un intervallo scoperto non eredita un vecchio profilo aperto.
Restano visibili le anomalie tecniche diverse da OREM. Non cambiano dati INAZ,
mapping canonici, contratti, autenticazione, autorizzazioni, ore o giorni pagati.

I servizi `avventizio_absence.py` ed `employment_periods.py` restano invariati.
La riduzione riguarda le proiezioni: campi richiesta condivisi fra dettaglio e
matrice, precedenze dell'export, classificazione delle celle e presentazione AG.
I parser ricevono un payload vuoto per sorgenti non strutturate e mantengono
valori espliciti e fallback; la tabella degli stati AG restituisce copie per
evitare che una modifica del consumatore alteri le risposte successive.

## Metriche prima e dopo

| Responsabilità | Ciclomatica | Cognitiva | LOC callable |
| --- | --- | --- | --- |
| Serializer dettaglio | 55 → 43 | 71 → 59 | 138 → 131 |
| Serializer matrice | 19 → 7 | 18 → 6 | 77 → 70 |
| Proiezione richiesta condivisa, nuova | 5 | 4 | 9 |
| Risoluzione causale export | 6 → 4 | 7 → 3 | 14 → 6 |
| Classificazione cella | 15 → 13 | 19 → 17 | 12 → 10 |
| Etichetta stato cella | 9 → 8 | 10 → 8 | 7 → 7 |
| Stato giorno mensile | 13 → 12 | 17 → 15 | 16 → 14 |
| Costruzione mensile | 9 → 9 | 13 → 13 | 17 → 15 |

Sul medesimo perimetro di nove file, includendo i nuovi callable: somme
ciclomatica **1941 → 1917**, cognitiva **1860 → 1830**, LOC callable
**6063 → 6045**, LOC file **5806 → 5792**. Nessuna nuova esclusione o baseline
modificata; il nuovo helper non supera le soglie. Esito **IMPROVED** per questa
unità di proiezione, senza trasferire violation imperative.

## Verifiche

- 55 casi aggiuntivi: 35 backend e 20 frontend. Coprono estremi inclusivi,
  sovrapposizioni, intervalli scoperti, precedenze, sorgenti non strutturate,
  mancati accrediti, diagnostica tecnica e indipendenza degli oggetti restituiti.
- La cache è verificata su sessione SQLAlchemy con dati sintetici: una query dei
  contratti per collaboratore, ma validità ricalcolata per ogni data, senza write.
- 709 test backend e 600 test frontend PASS, zero failure o skip.
- Sei file runtime backend: **100% statement e branch**, 1829 statement e 310
  rami, zero esclusioni. Tre file frontend: **100% statement, branch, funzioni e
  righe**. Questa evidenza riguarda il blocco, non la coverage globale di GAIA.
- Confronto differenziale della UI: 20136 combinazioni senza differenze.
  Proiezione campi richiesta: 1792 combinazioni senza differenze.
- `make lint-backend QUALITY_PYTHON=backend/.venv/bin/python` PASS;
  `npm --prefix frontend run typecheck` PASS. File Python nuovi formattati con Ruff.
- Il primo nuovo test assumeva erroneamente che `riposo` esportasse `None`:
  la verifica prima del refactoring ha confermato `RS`; attesa corretta e log
  del primo tentativo conservato. Il primo lint usava Python globale privo di
  Ruff; il controllo è stato eseguito con il venv previsto, senza installazioni.

## Limite residuo del ratchet

`make complexity-ratchet BASE_REF=origin/main` resta FAIL: **20 finding**, dei
quali **18 già riprodotti prima della feature** e **2 del blocco Avventizi**,
rispetto ai 17 iniziali. I due residui sono esclusivamente LOC:

- `schemas.py`: 1084 → 1091, per i sette nuovi campi del contratto di risposta;
- `build_presenze_mobile_record_payload`: 32 → 33, per includere la proiezione.

L'utente ha successivamente richiesto «ok continuamo con i commit e con il
push?», dopo il riepilogo esplicito dei due residui e del ratchet non verde.
Si procede con la pubblicazione Git richiesta, conservando l'esito FAIL e i
due incrementi come debito aperto. La richiesta non autorizza nuovi incrementi,
modifiche della baseline, deroghe CI, merge o deploy. Non sono state spostate
dichiarazioni né introdotti wrapper per aggirare il conteggio. Il successivo
intervento dovrà risolvere i due residui mantenendo distinti i 18 finding
preesistenti; questa pubblicazione non costituisce una certificazione dei gate.

Evidenze locali: `/tmp/gaia-avventizi-refactor-20261109/`, con patch iniziale,
metriche prima/dopo, log/JUnit, coverage, confronto differenziale e ratchet.
Il lavoro risiede nel worktree `/tmp/gaia-commit-execution-20261109/worktree`;
il checkout originale e i commit già pushati sono preservati.
