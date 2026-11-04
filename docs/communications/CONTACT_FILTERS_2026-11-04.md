# Presenza recapiti iniziale — 4 novembre 2026

## Modifica

`use-workspace.ts` inizializza il filtro `has_<channel>=true` insieme agli
altri filtri, prima di qualsiasi fetch. PEC seleziona Presenza PEC=Presente;
Email seleziona Presenza email=Presente. L’altro canale rimane non vincolato:
un contribuente con entrambi i recapiti può comparire in entrambe le schede.
Tutti e Assente restano selezionabili; nessun filtro viene forzato al refresh.

Unico runtime modificato, nessuna nuova dipendenza, API o migrazione.
I parametri di presenza già supportati dal backend filtrano e paginano i dati.
Nessun invio reale, modifica tributaria o cambio di stato di worker/trasporto.

## Matrice e controlli

| Comportamento | Verifica |
| --- | --- |
| PEC presente da prima richiesta, Email libera | Test workspace parametrizzato PEC; E2E query/dropdown PEC desktop/mobile |
| Email presente da prima richiesta, PEC libera | Test workspace parametrizzato Email; E2E query/dropdown Email desktop/mobile |
| Operatore seleziona Tutti e Assente | Entrambi i test workspace verificano le richieste successive |
| Snapshot PDF, revisione e invio accodato invariati | Suite Communications e flussi Chromium sintetici esistenti |

Test Communications: 37 PASS. Coverage dell’intero runtime modificato: 65/65
statement, 33/33 branch, 14/14 funzioni, 46/46 linee, 100% senza esclusioni.
Suite frontend completa: 349 file, 5.473 PASS. Smoke18, build:clean,
type-check e lint dei file modificati PASS. Ratchet completo `origin/main` PASS,
zero finding. Metriche del file invariate: 14 callable, somme Cyc49/Cog43/LOC113,
zero warning/error. Nessun refactoring o deroga al quality gate.
Sincronizzazione ordinaria e baseline-verify su copia completa PASS, con
Python3.12 della baseline: cambia solo il fingerprint di useCandidates,
metriche, scope e motori invariati. Nessuna esclusione o baseline-repair.
Graphify frontend aggiornato (717 sorgenti, nessun cambiamento topologico);
Graphify piattaforma docs chunk1/1 done, zero semantic failure, 5.758 token
input e 1.786 output, stima strumento $0,0052. Grafi non versionati.

La prima corsa E2E falliva sul nuovo selettore `getByLabel(..., exact:true)`:
lo snapshot browser mostrava già Presente selezionato e le query erano corrette,
ma il testo della label implicita comprende le option per quel selettore.
Corretto il test per usare il ruolo combobox e il nome accessibile esatto;
nessuna modifica runtime o indebolimento dell’assert sul valore true.
Log e trace della corsa iniziale conservati separatamente dalla ripetizione.

Quattro E2E Chromium sull’immagine candidata CED PASS (9,4 secondi),
PEC/email desktop1440/mobile390, con query e valore iniziale verificati.

Evidenze private `/tmp/gaia-contact-filters-*`. Le prove browser usano API
simulate, PDF sintetico e destinatari example.org; non collaudano provider reali.
Le verifiche generali PostgreSQL/GIS storiche non sono modificate da questa UI.

## Stato di rilascio

Pubblicato alle **12:13:03 CET**, commit runtime `2df77b43`.
Frontend `gaia-frontend:communications-contact-filters-20261104`, ID `1318fd5bdc5c`.
Aggiornato solo frontend, derivato dall’immagine sidebar `6218c83aa7da`. Preservate le sorgenti del builder CED
precedente; overlay limitato a `src/components/communications/use-workspace.ts`,
package e lockfile dell’immagine effettiva. Rollback alla sidebar precedente,
nessuna operazione backend/worker/database.

Il primo tentativo di attivazione ha rilevato un cambio concorrente delle
identità backend/Poste da un rilascio `antiduplicati` separato. Il guard ha
annullato l’attivazione e ripristinato il frontend precedente, healthy.
I log Compose confermano che questo intervento ha ricreato soltanto frontend.
Nessun tentativo di ripristinare backend o worker estranei; nuova fotografia
e secondo tentativo soltanto dopo la conclusione del rilascio concorrente.


Il secondo tentativo, nella directory protetta
`/opt/gaia/releases/communications-contact-filters-20261104-2`, è completato:
frontend healthy, configurazione invariata, 196 route preservate, sei URL
HTTP200 e stesso BUILD_ID della candidata collaudata. Tutti i 50 container
preesistenti hanno mantenuto identità, incluse le nuove versioni del rilascio
concorrente backend `78b5f2e6ea03f` e Poste `c9a6efa7c0e6f`.
Il primo tentativo e i suoi log restano conservati nella directory `-1`.
Nessuna soglia o guard è stato indebolito per il secondo tentativo.

Quattro flussi Chromium attraverso nginx di produzione PASS (13,5 secondi),
API tutte simulate. Query e dropdown iniziali corretti per entrambi i canali.
Controllo DB READ ONLY prima/dopo: zero account/messaggi/job Communications,
pausa globale true. Trasporti backend/worker false; identità del backend e del
worker dopo il rilascio separato preservate; tre API anonime HTTP401.
Nessun invio reale o scrittura tributaria effettuato da questo intervento.

Rollback della sola UI: `rollback.json` della directory `-2`, con
`docker compose --project-directory /opt/gaia -f <release>/rollback.json up -d
--no-deps --no-build --pull never frontend`, health, `nginx -t` e reload.
Ripristina `6218c83aa7da`; non usare configurazioni o immagini di rollback per
ripristinare backend/Poste che appartengono al rilascio concorrente.

Gate specifico della modifica e del rilascio: **PASS**. Nessuna modifica
estranea inclusa nei commit, nessun push/merge o rilascio generale GAIA.
