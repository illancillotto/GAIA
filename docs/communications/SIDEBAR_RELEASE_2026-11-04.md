# Sidebar PEC/email: risoluzione gate e rilascio — 4 novembre 2026

## Mandato e perimetro

Autorizzazione utente: «risolvi il quality gate e poi deploya».
Una sola unità: la composizione PEC/email con sidebar del commit `86fa982d`.
Nessuna nuova feature, modifica backend/DB, migrazione o attivazione trasporti.
Il gate riportato qui riguarda questa revisione frontend; la verifica generale
storica PostgreSQL/GIS di FINAL_REVIEW.md non viene trasformata in PASS.

## Correzione senza eccezioni

- `NewCommunication` gestisce già l’assenza di selezione: ora rende direttamente
  l’aiuto iniziale. Eliminato il secondo controllo duplicato nel workspace.
- Scelta esclusiva fra comunicazione esistente e nuova bozza. `CandidateTable`
  possiede la propria sezione semantica; la griglia unica elimina due contenitori.
- Rimosso l’alias ridondante della selezione e riunite le indicazioni operative
  in un solo paragrafo, senza perdere le istruzioni di revisione/invio.
  Eliminata la nota che ripeteva il comando di creazione dello snapshot.
- `finally` garantisce il ripristino dello stato busy anche sul percorso di errore.
  Un nuovo test osserva documento svuotato durante la richiesta, errore, rilascio
  busy e successiva selezione funzionante.

Nessun wrapper aggiunto, callable rinominato, soglia allargata o esclusione.
Non sono state compattate arbitrariamente righe per aggirare LOC.
API, PDF, checklist, permessi e ordine campi→PDF→controlli restano invariati.

## Metriche e baseline

| Callable | Prima sidebar Cyc/Cog/LOC | Finale Cyc/Cog/LOC | Baseline precedente LOC |
| --- | --- | --- | --- |
| ComposerForm | 8/7/23 | 8/7/22 | 22 |
| useCommunicationSelection | 9/11/33 | 9/11/32 | 32 |
| open | 5/6/9 | 5/6/8 | 8 |
| CandidateTable | 11/10/6 | 11/10/5 | 5 |
| NewCommunication | 4/4/13 | 4/4/12 | 12 |
| ChannelWorkspace | 6/5/19 | 4/3/12 | 12 |

Sui cinque runtime: 85 callable invariati, somma Cyc194→192, Cog123→121,
LOC330→318. Rispetto al codice prima della sidebar: Cyc193→192, Cog121→121,
LOC325→318. Due warning precedenti invariati, zero error-level.
Esito **IMPROVED**: gli otto incrementi sono eliminati e gli aggregati
scendono, senza trasferimento di debito.

Ratchet completo contro merge-base `origin/main` PASS, zero finding.
Sincronizzazione ordinaria e `baseline-verify` su copia completa privata PASS.
Applicato al repository solo il risultato riproducibile: cambiano i record dei
cinque runtime Communications; scope, motori, soglie ed eccezioni invariati.
La prima proposta con il Python di sistema 3.14 era passata ma alterava i
fingerprint Python estranei: scartata. Ripetuto con Python3.12 della baseline;
nessun file Python entra nel diff. Nessun uso di baseline-repair.

## Verifiche

| Verifica eseguita | Esito |
| --- | --- |
| Communications Vitest, nuovo caso di failure incluso | 35 PASS |
| Coverage cinque runtime completi | 190/190 statement, 118/118 branch, 85/85 funzioni, 120/120 linee: 100% |
| Regressione frontend completa prima dell’aggiunta del solo nuovo test | 349 file, 5.470 PASS; nuovo caso eseguito nella suite mirata successiva |
| `npm test` | 18 PASS |
| ESLint cinque runtime/tre test e nuovo test finale | PASS |
| `npm run typecheck` | PASS |
| `npm run build:clean` isolato | PASS |
| Chromium build locale: PEC/email, 1440/390 px, PDF tre pagine e approvazione | 4 PASS |
| Build immagine CED derivata dall’immagine attuale, senza installazioni/rete | PASS |
| Chromium stessa suite sull’immagine candidata CED, API tutte simulate | 4 PASS |
| Screenshot desktop/mobile sintetici | Controllati, layout preservato |
| `git diff --check` | PASS |

Warning legacy Next/React, deprecazione next-lint e avvisi ambiente conservati;
nessuna nuova failure runtime, esclusione, skip o mock di rendering PDF.
SMTP/IMAP reali e regressioni backend non rieseguiti: non toccati dal rilascio.

Evidenze private `/tmp/gaia-sidebar-qg-*`; coverage
`/tmp/gaia-sidebar-qg-coverage-final/coverage-final.json`.
Un primo avvio canary precedeva il completamento dell’export immagine ed è
fallito prima di creare container. Ripetuto dopo image-inspect con pull vietato.
Il primo confronto Env usava l’ordine della lista e ha fermato il preflight:
le mappe risultano identiche. Corretto il confronto per ordine irrilevante,
senza cambiare configurazioni o ignorare differenze di valori.

## Preparazione CED

Release protetta `/opt/gaia/releases/communications-sidebar-20261104-1`.
Base frontend `59b2b4bdfcd2`, candidata `6218c83aa7da`.
Sorgenti del builder precedente preservate (762 file), overlay limitato ai cinque
runtime; package e lockfile uguali a quelli dell’immagine effettiva. Tutte le
196 route esistenti preservate. Backup configurazione/immagine e `rollback.json`
preparati; nessun backup/migrazione DB richiesto per questa sostituzione frontend.

Preflight: frontend attuale invariato, ambiente/comando/mount/risorse confrontati;
backend e worker Communications healthy, trasporti false. Posta Online è già
running all’inizio di questo intervento: la release ne preserva identità e stato.
Non viene ripristinato il precedente stato fermo della vecchia release.

## Graphify e working tree

Frontend aggiornato tramite target dedicato con pruning forzato: 717 sorgenti,
7.113 nodi, 16.965 relazioni, 260 comunità. JSON/report aggiornati;
HTML omesso dallo strumento per limite 5.000 nodi. Documentazione aggiornata
tramite `make graphify-platform-docs`: chunk1/1 done, nessun semantic failure;
10.033 token input e 1.219 output, stima strumento $0,0060. Nessun grafo versionato.

Modifiche concorrenti Poste, Presenze, configurazioni e documenti estranei
preservate. Nessun push, merge o rilascio completo GAIA.

## Attivazione

Pubblicazione frontend autorizzata, da eseguire dopo commit e registrazione
locale delle verifiche. Esito operativo definitivo da registrare a fine rilascio.

Gate di sviluppo della revisione sidebar: **PASS**, tutti i controlli pertinenti
eseguiti. L’attivazione frontend è una fase successiva distinta.
