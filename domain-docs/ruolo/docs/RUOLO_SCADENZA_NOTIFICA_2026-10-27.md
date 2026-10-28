# Avvisi: pagamento entro 60 giorni dalla notifica

## Comportamento implementato

In `Regole ruolo`, `Scadenza pagamento avviso` offre `Data fissa` e
`Entro 60 giorni dalla data di notifica`. API e dominio ammettono soltanto
`fixed_date` e `notification_60_days`. La prima e il default per vecchie e nuove
regole; la migration additiva `20261027_1300` conserva tutte le date esistenti.
Dal 2026-10-28 la seconda conserva anche `payment_due_date`: i campi data
restano disponibili, anche per annualita. Con `print_bollettino=true` la data
fissa e obbligatoria. Il salvataggio senza data restituisce HTTP 422; anche
le regole storiche prive di data bloccano la preparazione dello snapshot
con bollettino. Senza bollettino il solo termine relativo e ammesso.

La regola dell'anno piu recente determina il termine degli avvisi multiannualita.
Lo snapshot conserva la scelta: modificare la regola non cambia i PDF gia
generati. Nella modalita a 60 giorni un'eventuale data residua nel payload non
prevale sul termine relativo dell'avviso. Il riquadro aggiuntivo della prima
pagina e i campi DOCX conservano `60 giorni dalla data di notifica`. I bollettini
v1/v2 usano invece la data fissa dello snapshot e stampano
`gg/mm/aaaa - Rata Unica` su entrambi i tagliandi. Il rendering di un bollettino
a 60 giorni senza data e bloccato anche per snapshot storici. Nessuna data
viene calcolata dalla generazione per questa modalita; il fallback legacy
della modalita `fixed_date` resta invariato.

Eccezione grafica dal 2026-10-28: nel solo box `Quanto e quando pagare` di un
avviso del solo ruolo 2021, l'eventuale data esplicita del payload viene affiancata
al termine: `entro il gg/mm/aaaa e comunque entro 60 giorni dalla data di notifica`.
Senza data esplicita si conserva solo il termine di notifica. Non viene modificato
il termine dei campi DOCX; i bollettini seguono la data fissa descritta sopra. Per gli altri anni
e i gruppi multiannualita resta il comportamento esistente.

Prima del portale del contribuente si stampano:

- `Pagamento entro 60 giorni dalla data di notifica`, senza ripetere l'importo
  gia presente nel riepilogo di pagamento;
- il rinvio delle scadenze di sabato o festive al primo giorno lavorativo;
- l'avvertenza sugli interessi di mora per pagamenti oltre i 60 giorni.

Sopra i due QR WhatsApp/Irrighiamo Insieme, dopo gli accessi portale, si stampa
l'intimazione con triangolo rosso e punto esclamativo rosso. La frase aggiornata e: «In caso di mancato pagamento, il Consorzio di Bonifica
dell'Oristanese tramite l'agente di riscossione attiverà le procedure di
riscossione coattiva previste dalla legge.» Il testo e adattato al Consorzio; le misure della
riscossione coattiva sono riferite ai casi e alle modalita previsti dalla legge.
Questi due riquadri sono presenti soltanto con il termine a 60 giorni.
Il paragrafo con contatti degli uffici e informazioni sul sito segue il blocco di accesso al portale,
in entrambe le modalita di scadenza. Nella modalita a 60 giorni lo spazio libero verticale
e ripartito tra termine, portale, contatti/sito e footer, con distacco minimo di
`1mm`: non e piu concentrato sopra l'intimazione. I test PDF verificano
ordine, assenza di sovrapposizioni e differenza tra i distacchi inferiore a
`12pt`, con una, due e cinque annualita.

Il motore degli interessi, le decorrenze dei piani sottoscritti, la scadenza
bonaria e il calcolo di una scadenza effettiva da una notifica acquisita non
sono modificati. Il rinvio per festivita e l'avvertenza di mora sono testi
dell'avviso, non nuovi automatismi contabili.

Dopo il portale si stampano consecutivamente, nello stesso paragrafo:

> Per maggiori chiarimenti contattare l'Ente o recarsi presso la sede nei seguenti giorni: Lunedi e giovedì 11.00 - 13.00, - tel. 0783 3150212.

> È possibile consultare il sito internet www.bonificaoristanese.it per una migliore individuazione delle proprietà assoggettate a tributo, degli indici applicati nel calcolo, e la normativa inerente l’attività istituzionale dell’Ente.

## Verifica

Data fissa bollettini, ciclo finale 2026-10-28: **234 PASS, zero skip**,
**100%** statement/branch su 15 runtime (`1532` statement, `406` branch),
zero esclusioni e branch parziali. I test verificano conservazione data nelle
regole/API/snapshot multiannualita, rifiuto del salvataggio senza data con
bollettino, regole storiche senza data, avviso senza bollettino ammesso e
stampa della data su entrambi i tagliandi v1/v2, da payload ISO o italiano.
Il frontend conserva le date cambiando modalita e ripristina le regole storiche
senza data per consentirne la correzione. **72 test frontend PASS** su quattro
suite, coverage statement/branch/funzioni/righe **100%** sui tre runtime del
form (`78` statement, `91` branch). Lint backend, ESLint mirato e
TypeScript PASS. Ratchet autorevole contro `9ff86d83` PASS, nessun finding;
baseline dei cinque runtime sincronizzata e verificata su scansione fresca,
conservando record e metadati estranei. Il debito legacy resta censito.

Anteprima corrente `output/pdf/avviso-2021-anteprima-blu.pdf`: quattro pagine,
marcatura dimostrativa su ciascuna, prime tre pagine pixel-identiche alla
precedente versione; entrambi i tagliandi stampano `30/11/2026 - Rata Unica`.
Bollettino ispezionato visivamente, QR WhatsApp/Irrighiamo e Code128/DataMatrix
decodificati dal PDF finale. Evidenze locali:
`/tmp/gaia-bollettino-deadline-20261028/`. Nessuna migration aggiuntiva o
modifica alle regole/database degli uffici: la colonna data esiste gia.
Le vecchie regole a 60 giorni con bollettino richiedono la data prima dell'uso;
i PDF gia prodotti non vengono riscritti.

Verifica precedente del 2026-10-28, prima della data fissa nei bollettini:
**229 PASS, zero skip**, **100%** statement/branch
su 14 runtime (`1477` statement, `394` branch), zero esclusioni. Include i nuovi
casi del box 2021 con/senza data, famiglia Arial uniforme, triangolo rosso e
entrambi i QR decodificati dalla stampa. Anteprima corrente:
`output/pdf/avviso-2021-anteprima-blu.pdf`; pagine 2-4 pixel-identiche alla
precedente versione blu. Evidenze: `/tmp/gaia-avviso-20261028/`.
Le prove sotto conservano il dettaglio delle iterazioni precedenti.

- Backend, verifica aggiornata dopo accessi/riepilogo: **221 PASS, zero skip**,
  statement/branch **100%** sui 14 runtime misurati (1469 statement, 390 branch).
  Nessuna esclusione o riga/branch scoperti. Test aggiuntivi pertinenti per
  colonna Interessi assente con importi arrotondati a zero, presente con importi
  non nulli anche negativi o compensati, e singola coppia per utenza con
  sospensione dei casi ambigui anche negli snapshot storici.
- Frontend: **71 test PASS** su quattro suite; copertura statement, branch,
  funzioni e righe **100%** su `calculation-policy-form.ts`,
  `policy-notice-print.tsx` e `policy-payment-deadline.tsx`.
- Test pertinenti: default e salvataggio API, aggiornamento e rimozione data
  residua, scelta in UI e serializzazione, rifiuto modalita invalide,
  precedenza annualita, snapshot batch persistito che resta a 60 giorni anche
  dopo il cambio della regola a data fissa, importo conservato nel solo riepilogo,
  ordine dei blocchi, compatibilita data fissa e migration upgrade/downgrade.
- PDF Chromium: una, due e cinque annualita, nomi lunghi, residui, una
  coppia Codice ditta/PIN per utenza e fallback uffici per snapshot ambigui. Prima pagina completa, comunicazioni sulla seconda,
  termine relativo sul bollettino e QR WhatsApp decodificato dal PDF.
- Anteprima 2021 aggiornata in `output/pdf/avviso-2021-anteprima.pdf`, con
  dati dimostrativi e marcatura visibile su ogni pagina. Prima pagina e
  comunicazioni ispezionate; QR WhatsApp e codici Code 128/Data Matrix
  decodificati dal PDF finale.
- Typecheck frontend e `make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
  BASE_REF=HEAD` PASS. Lint frontend PASS con avvisi in altri file;
  i test backend riportano anche avvisi sulla chiave JWT dell'ambiente di test.

Evidenze locali: `/tmp/gaia-avviso-deadline-20261027/` e
`/tmp/gaia-avviso-spacing-20261027/` e
`/tmp/gaia-avviso-contact-prefix-20261027/` (JUnit, coverage JSON,
log dei gate, metriche e render). Non rappresentano una verifica dell'intero
repository o un collaudo sul server degli uffici.

## Complessita

Ratchet ordinario contro il merge-base `9ff86d83`: nessun nuovo finding.
In questo ciclo il renderer passa da LOC `1785` a `1771`, cognitive aggregate
`429 -> 428`, cyclomatic `434 -> 433`. Il riepilogo passa all'helper
`notice_summary.py` (LOC `35`, cognitive massimo `8`, cyclomatic massimo `9`),
che gestisce le colonne condizionali e non introduce violation.
Accessi portale: LOC `36 -> 43`, cognitive massimo `5`, cyclomatic massimo `5`;
branding LOC `80`, cognitive/cyclomatic massimi `2/3`. Nessuna nuova violation
error-level; il debito legacy del renderer resta censito. Ratchet ordinario,
senza dichiarare una riduzione di complessita globale.

Baseline sincronizzata soltanto sui quattro runtime di questo ciclo, dopo il
ratchet autorevole, a partire dalla proiezione immutabile del merge-base.
La proiezione locale intermedia rifiutava la crescita LOC degli accessi non
ancora committati: non e il riferimento autorevole della change.
`baseline-verify` della proiezione corrente passa con scansione fresca; record
estranei, ordine e metadati globali sono preservati. Nessuna certificazione
della baseline globale con sviluppi concorrenti presenti.

## Graphify

Aggiornati con i target dedicati `graphify-ruolo-code`, `graphify-backend`,
`graphify-frontend`, `graphify-ruolo-docs` e `graphify-platform-docs`.
I corpus docs completano i chunk semantici senza warning di chunk falliti.
Nel ciclo data fissa bollettini: Ruolo `1340` nodi, backend `10575`; il target
frontend non rileva cambi di topologia e conserva il grafo esistente. Backend e frontend aggiornano JSON/report ma omettono la nuova
visualizzazione HTML per il limite predefinito di `5000` nodi; non e un
errore d'estrazione. Gli output restano locali e non vengono versionati.

## Stato di rilascio

Backend e frontend sono rilasciati sul CED dal 2026-10-28, con migration
`20261027_1300` applicata e schema finale `20261028_0900`. Le cinque regole
esistenti conservano `fixed_date` e le date precedenti: la modalita a 60 giorni
si sceglie dalle Regole ruolo, con data fissa obbligatoria se si stampa il
bollettino. Nessun PDF esistente riscritto o nuova importazione degli accessi.
I sei CF con piu utenze restano sospesi in attesa dei colleghi.
Verifiche e rollback: [rilascio CED](RUOLO_AVVISI_DEPLOY_2026-10-28.md).
