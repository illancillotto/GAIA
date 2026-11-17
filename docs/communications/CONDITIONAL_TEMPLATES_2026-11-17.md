# Blocchi ICATASTO condizionali — 17 novembre 2026

Stato: candidata verificata; pubblicazione e attivazione autorizzate in preparazione.
Il rilascio effettivo sarà registrato soltanto dopo i controlli della produzione.
Nessuna migrazione, modifica delle credenziali canoniche
o approvazione automatica dei template.

## Comportamento implementato

L'editor aggiunge **+ Servizio ICATASTO**, un paragrafo con anno, codice utenza
e PIN e un pulsante HTTPS verso il portale ufficiale. Testi e destinazione sono
modificabili. La casella **Solo con codice utenza e PIN ICATASTO disponibili**
è inizialmente selezionata per entrambi e si può applicare anche agli altri
blocchi. La condizione richiede entrambi i valori canonici non vuoti.
Credenziali assenti, ambigue o non decifrabili nello snapshot PDF escludono
il blocco da anteprima, bozza, testo semplice, HTML e immagini incorporate.

Le variabili richieste altrove restano obbligatorie. Le condizioni vengono
risolte prima di aggiungere i segnaposto dell'anteprima; non compaiono nel
messaggio materializzato. Un template composto soltanto da blocchi esclusi
produce un'anteprima vuota, ma non può creare una bozza priva di testo.
Il MIME rifiuta condizioni non risolte. L'editor del messaggio già composto
non offre comandi per introdurle.

**Crea nuova versione → Crea layout con logo e link** converte esplicitamente
il modello ufficio: riconosce il paragrafo SERVIZIO ICATASTO con i tre campi
utenza/PIN/URL, lo rende condizionale e sostituisce il segnaposto URL con un
pulsante. Il resto del testo è conservato in paragrafi normali. Separatori
vuoti, anche incollati con terminatori Windows, non creano blocchi vuoti.
Oltre 60 blocchi resta un paragrafo per revisione manuale; l'inserimento del
blocco ICATASTO richiede due posti liberi. Catalogo, versioni approvate e
messaggi storici non vengono convertiti automaticamente.

## Matrice dei comportamenti e prove

| Comportamento | Prova pertinente |
| --- | --- |
| Entrambe le credenziali richieste; assenza parziale, null, vuoto, spazi, tipo errato | `test_conditional_templates.py`: omissione dell'intera sezione e link |
| Snapshot completo, assente, corrotto o ambiguo; PEC ed email | API creazione/approvazione template, anteprima, bozza e MIME con dati cifrati sintetici |
| Nessuna variabile mancante dai soli blocchi esclusi | Anteprima e bozza concordanti; campi obbligatori esterni ancora bloccanti |
| Nessun messaggio vuoto quando tutti i blocchi sono esclusi | API restituisce 409 e non salva una bozza parziale |
| Condizioni/URL non ammessi, campi sconosciuti | Validazione HTTP e renderer anche sui contenuti che sarebbero nascosti |
| Condizioni rimosse dallo snapshot, template conservato | Confronto bozza/anteprima e lettura del template salvato |
| MIME non accetta condizioni irrisolte; logo coerente con visibilità | Contratto MIME e presenza/assenza della parte PNG e del suo CID |
| Inserimento/modifica/riordino/rimozione, checkbox e anteprima | `conditional-templates.test.tsx` e regressioni `rich-templates.test.tsx` |
| Conversione PEC/email ufficio, testo personalizzato, CRLF e righe vuote | Conversione dei due veri modelli di catalogo e testi incollati |
| Limite 60 blocchi e assenza di authoring condizionale sui messaggi | Test UI del limite, comandi disabilitati e MessageBodyEditor |
| Salvataggio versione, ripresa della condizione, desktop/mobile | E2E editor con payload intercettati e screenshot |
| Rendering PDF e composizione grafica dopo il cambio | E2E sulla build di produzione candidata, incluse tutte le suite Communications |

I test utilizzano dati sintetici. La copertura è misurata sui file runtime
interi modificati, senza esclusioni o test che sostituiscono la logica con
implementazioni simulate. I fixture isolano contabilità/rete negli stessi
confini delle suite preesistenti; PostgreSQL verifica i vincoli reali in un
database temporaneo dedicato.

## Qualità e limiti

| Controllo | Esito finale locale/candidata |
| --- | --- |
| Backend Communications, incluso PostgreSQL dedicato | 341 PASS, zero skip; 138 statement e 54 branch coperti al 100% sui due file runtime |
| Immagini candidate backend e worker Communications | 341 PASS ciascuna, zero skip, stessi due file al 100% statement/branch |
| Frontend Communications | 106 PASS; sei file runtime, 103 statement, 90 branch, 45 funzioni e 74 righe al 100% |
| Regressione frontend isolata HEAD + feature | 5.733 PASS, 370 file |
| Smoke frontend | 18 PASS |
| Suite strumenti code quality | 270 PASS |
| Typecheck, Ruff e formato nuovi file Python | PASS |
| Lint frontend completo | PASS con 35 warning legacy; nessun nuovo warning nei file della feature |
| Build di produzione candidata | PASS, 196 route preservate |
| E2E Communications candidata | 19 PASS, zero failure/skip/flaky, incluso PDF desktop/mobile |
| Ratchet del perimetro contro merge-base `origin/main` | PASS, zero finding |

Metriche massime ciclomatiche/cognitive e LOC effettive dei file:

| Runtime | Prima → dopo (Cyc/Cog; LOC) |
| --- | --- |
| `rich_template.py` | 13/15; 120 → 13/15; 149 |
| `template_composition.py` | 5/5; 32 → 5/5; 33 |
| `template-block-editor.tsx` | 6/5; 19 → 7/6; 22 |
| `template-editor.tsx` | 11/13; 46 → 12/14; 49 |
| `template-preview.tsx` | 10/15; 23 → 10/15; 24 |
| `template-blocks.ts` | 8/10; 22 → invariato |
| `message-body-editor.tsx` | 2/1; 12, logica invariata: passa il flag di authoring |
| `icatasto-blocks.tsx` | nuovo, 5/4; 31 |

Il perimetro finale ha 61 callable, zero errori e cinque warning, come prima
della feature. È un'estensione funzionale verificata dal ratchet, non un
refactoring dichiarato come riduzione della complessità.

Evidenze locali: `/tmp/gaia-icatasto-release-20261117/`. Il manifest congela
gli otto file runtime, con test aggiuntivi, documentazione e report separati.
Le modifiche preesistenti a Tributi, worker Poste, configurazioni e report
di complessità non appartengono a questa change e non saranno pubblicate.
Evidenza versionata priva di segreti:
[CONDITIONAL_TEMPLATES_2026-11-17.json](evidence/CONDITIONAL_TEMPLATES_2026-11-17.json).

Il problema PDF `Object.defineProperty called on non-object` è riprodotto
anche sul codice precedente con Next development; la build di produzione
candidata supera tutti i 19 E2E Communications, zero failure, skip o flaky.
Non è stata modificata la logica PDF per questa feature.

Il ratchet autorevole del perimetro contro `origin/main` passa. Il confronto
globale su HEAD pulito rileva 20 finding Presenze preesistenti; la baseline
storica non è riproducibile già prima della feature. Il working tree condiviso
presenta inoltre un matching ambiguo nel file Tributi modificato da altro
lavoro. La verifica isolata di questa change confronta HEAD con il solo
manifest Communications; baseline e soglie non vengono alterate per assorbire
il debito estraneo. L'esito finale viene riportato con questi limiti distinti.
La sincronizzazione della baseline, tentata soltanto nel worktree isolato,
è rifiutata per 65 rilievi sui file già divergenti dalla baseline; nessuno
appartiene agli otto file runtime della feature. Il confronto autorevole
globale candidato/HEAD restituisce gli stessi identici 20 rilievi Presenze.
Baseline e report preesistenti nel checkout condiviso sono preservati.

Nel primo collaudo delle immagini due test dei grant fallivano perché il
pacchetto di test non conteneva `deploy/communications/worker-grants.sql`.
È stato completato il pacchetto e ripetuta la suite senza modificare runtime,
grant reali o test. Log della prima prova conservati distinti dalla prova finale.
Il test iniziale delle righe vuote usava per errore escape letterali in un
attributo JSX; corretto il fixture con veri newline, il caso verifica ora il
comportamento di testo incollato. Nessun test rimosso o indebolito.

## Rilascio e rollback

Release preparata in `/opt/gaia/releases/icatasto-blocks-20261117` sul CED.
Le immagini derivano dai runtime effettivi: due file Python per backend e
worker, sei file frontend. Il confronto dei file preserva gli altri runtime;
il frontend mantiene tutte le 196 route della build precedente.
Configurazioni risolte e immagini precedenti sono conservate privatamente.
Non riportare environment o credenziali dai file `*.before.json`/Compose.

Attivazione prevista: worker, backend, frontend, con controllo concorrenza,
health, configurazioni effettive e reload nginx dopo `nginx -t`. Non usare
`down`, rebuild globali o riavvii dei worker estranei. Verificare API protette,
schema, hash template, conteggi, pausa/trasporti e identità della build.
Per rollback usare i file `*.rollback.json` soltanto in assenza di release
successive, preservando dati e compatibilità dei template condizionali;
vedere [ROLLBACK_PLAN](ROLLBACK_PLAN.md).
