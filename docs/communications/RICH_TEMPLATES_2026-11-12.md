# Template grafici Communications — 12 novembre 2026

Implementazione completata; rilascio CED attivo dal 12 novembre 2026 alle
**16:02:12 CET**. Commit applicativo **`75d2544d`**, pubblicato su
`chore/split-changes-20261109`.
La sezione Produzione registra solo operazioni effettivamente concluse.
Nessuna migrazione, nuova dipendenza, abilitazione dei trasporti o invio reale.

## Comportamento implementato

In `/gaia/communications`, **Crea layout con logo e link** converte il testo
corrente in un paragrafo senza perderlo. Sono disponibili logo ufficiale CBO,
titoli, paragrafi, elenchi (una voce per riga), link e pulsanti con etichetta.
Le frecce cambiano l’ordine; Rimuovi elimina un blocco. Restano da 1 a 60
blocchi. Il logo è l’asset PNG già usato negli avvisi, non un caricamento libero.

Dopo aver caricato **Modelli di partenza 2021 e variabili**, il selettore dei
campi inserisce un segnaposto nel testo selezionato. Senza un blocco testuale
selezionato aggiunge un paragrafo. Al limite di 60 blocchi l’inserimento dei
campi è disabilitato; il testo dei blocchi resta modificabile. L’anteprima è
immediata. Salva crea una versione bozza; Approva resta un comando distinto.
Le versioni precedenti e i messaggi già creati conservano i propri contenuti.

In PEC/Email l’unico template approvato compatibile viene preselezionato;
oggetto e testo sono compilati con i dati canonici dell’avviso. I messaggi
semplici mantengono il campo testo compatto. Per quelli grafici **Anteprima
messaggio** e **Modifica testo e layout** sono pannelli apribili: il PDF
resta sotto i campi. Tutti gli otto controlli individuali sono ancora richiesti.
Una modifica, anche solo grafica, invalida l’approvazione e richiede nuova
attestazione del rendering PDF per la versione del messaggio.

## Contratto persistito e resa

Il campo `body` esistente contiene testo semplice oppure il prefisso letterale
`GAIA-BLOCKS/1` seguito da newline e array JSON. Esempio sintetico:

```text
GAIA-BLOCKS/1
[{"kind":"logo"},{"kind":"paragraph","text":"Gentile {{contribuente_nome}}"},{"kind":"button","text":"Consulta il portale","url":"https://example.org/portale"}]
```

La bozza conserva lo stesso formato con i campi risolti. La sostituzione
avviene sui singoli testi: virgolette, ritorni a capo e nomi con `&` non
corrompono il JSON. Non vengono interpretate espressioni o attributi.
Il digest di approvazione include l’intero corpo, quindi anche URL e ordine.
Il trasporto genera `text/plain` e `text/html`; il logo è una parte related
`image/png` con Content-ID `gaia-official-logo`. Il PDF resta un allegato
separato. Il worker archivia gli esatti byte MIME prima della trasmissione.

Il limite HTTP è 20.000 caratteri per il corpo serializzato. Testi vuoti,
campi extra e tipi di blocco non validi producono 422. I link accettano HTTPS
assoluto senza credenziali o caratteri di controllo. Le destinazioni sono
fisse: nessuna variabile negli URL. Non sono ammessi HTML libero, CSS fornito
dall’operatore, script, immagini esterne o logo arbitrario. I testi sono
escapati nell’HTML; l’anteprima usa elementi React. Le differenze grafiche tra
client email restano possibili. Il controllo dimensionale MIME finale include
alternative HTML/testo, immagine, allegati e codifica.

Credenziali dell’avviso mancanti restano visibili nell’anteprima e bloccano la
creazione anche se il testo viene modificato. Gli avvisi riconciliati con Poste
restano esclusi. Nessun aggiornamento tributario o fallback PIN introdotto.

## Matrice comportamenti e test pertinenti

| Comportamento | Prova |
| --- | --- |
| Conversione senza perdita, inserimento nel testo selezionato | `rich-templates.test.tsx`: legacy text e field selection |
| Aggiunta, modifica, spostamento, rimozione dei sei tipi | `rich-templates.test.tsx`: supported block types; E2E editor desktop/mobile |
| Minimo un blocco, massimo 60 anche per inserimento campo | Unit: disabled controls/one-block/60-block limit; API: array vuoto e 61 blocchi |
| Input malformati, inclusi kind array/oggetto/null | API: invalid structures, 422 su modifica bozza; nessun errore server |
| URL non ammessi e HTML letterale | Unit: unsafe links/raw text; API/rendering: unsafe destinations ed escaping |
| Virgolette, newline e `&` nei dati dell’intestatario | Backend: escape values/preserve JSON and plain text |
| Bozza, approvazione, composizione PEC/email, versioni successive | Backend: create/approve/compose/snapshot/MIME; E2E creazione nuova versione |
| Credenziali mancanti non aggirabili | Backend: missing PIN preview + edited text; E2E storico/credenziali e Poste |
| Modifica grafica revoca approvazione e attestazione PDF | Backend: graphical edit revokes approval, per entrambi i canali |
| Worker archivia e trasmette gli stessi byte, PDF e immagine CID | Backend: graphical edit/worker e MIME snapshot; SMTP simulato senza rete |
| Compatibilità testo semplice e stato disabled | Unit composer/message body; suite backend/worker preesistente |
| Campi sopra PDF, preview apribile, tutte le pagine renderizzate | E2E composizione grafica 1440/390 e flussi PEC/email 1920/1440/390 |
| Nessun salvataggio/approvazione implicito, errori catalogo e retry | Unit admin/catalog e E2E modelli ufficio |

Test backend: `backend/tests/communications/test_rich_templates.py` con la
suite Communications, incluse prove PostgreSQL e controlli di ruoli/lock.
Test frontend: `frontend/tests/unit/communications/`; browser:
`communications-rich-templates.spec.ts`, `communications-office-templates.spec.ts`
e `communications.spec.ts`. Nessuna esclusione coverage o test disabilitato.

## Verifiche e qualità

- Suite locale backend: **314 PASS, zero skip**, PostgreSQL effettivo in un
  database sintetico isolato. Coverage dei sei runtime modificati/nuovi:
  **618 statement e 166 branch, 100%**.
- Suite unit Communications frontend: **99 PASS**, undici runtime modificati/
  nuovi: **231 statement, 183 branch, 112 funzioni e 160 righe, 100%**.
- Regressione completa frontend: **5.712 PASS** in 367 file; **18 smoke PASS**.
- Candidata frontend CED: **14 E2E PASS**, zero failure/skip/flaky, su build di
  produzione, con API/PDF sintetici; desktop e mobile.
- Immagini backend e worker CED: **314 PASS ciascuna, zero skip**, inclusi
  PostgreSQL e privilegi reali nel database sintetico; sui sei runtime della
  feature **618 statement e 166 branch, 100%** in entrambe le immagini.
- Ruff e formato dei file nuovi PASS; typecheck, lint Communications e smoke
  verificati separatamente. Risultati candidata e regressione nel riepilogo
  finale/evidenza della release.
- Il confronto completo contro la baseline del merge-base `origin/main`
  non attribuisce rilievi a Communications. Il gate globale conserva i
  20 rilievi Presenze già presenti nel branch; non è dichiarato verde.
- Confronto aggiuntivo sullo snapshot completo precedente alla feature:
  nessuna regressione nei callable esistenti e nessuna nuova violation error.
  `TemplateAdministration`: cyc/cog/LOC 12/13/35 → 10/11/30;
  `TemplateCatalog`: 7/7/17 → 5/4/9. Il nuovo form/catalog hook è una
  riorganizzazione funzionale, non una riduzione autonoma dichiarata del debito.
- Baseline, soglie e gate invariati. I report già sporchi prima di questo
  ciclo restano fuori dal commit; nessuna deroga per assorbire i rilievi.
- Graphify backend, frontend con pruning e documentazione piattaforma
  aggiornati dopo il contenuto finale; risultati nell’evidenza di chiusura.

Comando finale di stile backend: `make lint-backend
QUALITY_PYTHON=backend/.venv/bin/python BASE_REF=HEAD`, PASS sui sette file Python
della change, inclusi formato dei due file nuovi. Per lint/typecheck frontend
sono stati usati gli script del package e il perimetro Communications.

Il primo collaudo delle immagini mancava del file di fixture
`deploy/communications/worker-grants.sql`: due failure di lettura, nessuna
modifica dei privilegi reali. Il primo canary usava una rete Docker senza
connettività e non esponeva la porta al browser. Corretti esclusivamente il
pacchetto test e l’avvio del container effimero; i tentativi iniziali restano
conservati separatamente e non sono conteggiati come PASS.

## Distribuzione e rollback

Release CED `/opt/gaia/releases/rich-templates-20261112`. Configurazioni risolte,
manifest hash, immagini e rollback sono conservati lì in file privati; non
contengono dati da copiare nei log o nel repository. Le immagini candidate
partono dai runtime effettivi, con un delta limitato a Communications e al
PNG. Il worker precedente era più vecchio: riceve il modulo Communications
coerente e `notice_communication_fields.py`, preservando gli altri domini.
Le immagini backend e worker vengono collaudate prima dell’attivazione.

Aggiornare prima il worker compatibile, poi API e UI; preservare trasporti,
pausa, mount, risorse, rete, account e altri container. Nessun riavvio globale
né ripresa del worker Poste. Controlli concorrenti prima di ogni sostituzione,
health, confronto configurazione, API private e browser dopo il cambio.

Rollback dai file `*.rollback.json` soltanto se non sono intervenute release
successive. Un vecchio worker non capisce i body grafici: prima del rollback
inventariare messaggi/job e sospendere il dispatch. Preferire il ripristino di
UI/API lasciando il worker compatibile, oppure mantenere il trasporto
esplicitamente disabilitato fino alla gestione dei body grafici. Nessun
restore DB per annullare il solo codice, nessun downgrade o reinvio automatico.

## Problemi residui e limiti

Il viewer PDF preesistente genera `Object.defineProperty called on non-object`
con il server Next in modalità sviluppo; l’errore si riproduce nel flusso
precedente. Le prove finali usano una build di produzione, dove il PDF funziona.
Il renderer PDF non è stato modificato in questo ciclo.

Il gate globale Presenze resta separato dal perimetro Communications. I test
sintetici non collaudano provider SMTP/PEC, certificati effettivi o consegna
legale. Le decisioni esterne in OPEN_DECISIONS restano in vigore.

Durante il push GitHub segnala otto vulnerabilità sul branch predefinito
(sette high, una moderate). È una segnalazione del repository, non un audit
eseguito in questo ciclo; nessuna dipendenza o lockfile è stata modificata.

## Produzione

Worker aggiornato per primo, poi backend e frontend; tutti healthy. La build
pubblicata coincide con la candidata collaudata. Ambiente, comandi, mount,
reti, limiti risorse e healthcheck effettivi coincidono con quelli precedenti;
**34 container estranei preservati**, incluso il worker Poste.

Otto GET pubblici rispondono HTTP 200 (pagine, health e logo); le due API admin
anonime restano HTTP 401. Quattro GET autenticati rispondono 200; catalogo e
funzioni di preview/riparazione già disponibili restano presenti. Il renderer
attivo riconosce il formato grafico ed esegue escaping su dati sintetici.
Un secondo probe dopo l’attivazione conferma gli stessi risultati.

Schema `20261106_1000`, due account, otto righe template con hash integrale
invariato, zero messaggi/autorizzazioni/ricevute e cinque job invariati. Pausa
**true** e trasporto **false**. Nessuna migrazione, creazione/approvazione di
un template reale, modifica di PIN o invio; avvisi riconciliati Poste esclusi.

Collaudo browser sulla versione pubblicata: **14 E2E PASS**, zero failure,
skip o flaky, desktop e mobile. Usa API/PDF sintetici intercettati, mentre le API
reali sono verificate separatamente in sola lettura. Configurazioni di rollback
e immagini precedenti restano nella directory privata della release.
Evidenza senza segreti: [RICH_TEMPLATES_2026-11-12.json](evidence/RICH_TEMPLATES_2026-11-12.json).
