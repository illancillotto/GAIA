# Regole annuali, blocchi e avvisi non notificati

## Comportamento

In `Regole ruolo`, ogni annualita conserva una regola indipendente. La modale
raggruppa le regole per nome base, rimuovendo dal nome il suffisso dell'anno
quando la regola riguarda un singolo anno: e lo stesso criterio gia usato
dal raggruppamento dei solleciti. Non esiste una nuova entita blocco nel DB.
`Modifica` ed `Elimina` restano azioni sulla singola regola, non sul blocco.

Il selettore `Componenti da applicare` offre maggiorazione, interessi, entrambi
o nessuno. Quest'ultima opzione rappresenta anche regole preesistenti a tasso
zero. Le componenti escluse vengono salvate a zero: non sono tassi sospesi da
riattivare automaticamente. Gli interessi comprendono Euribor e delibera.

Quando si crea un intervallo, ogni anno eredita le impostazioni comuni finche
non viene personalizzato. Per anno si possono impostare componenti, tassi,
scadenza bonaria, data fissa/fallback degli interessi, modalita di decorrenza e
checkbox `Solo avvisi non notificati`. Un Euribor annuale modificato manualmente
non conserva metadati BCE che attesterebbero un valore diverso. Il campo
bonario determina la maggiorazione dal giorno successivo, come in precedenza.

Il salvataggio multiplo conserva le richieste annuali separate preesistenti:
non e una transazione atomica di blocco. In caso di errore intermedio le
annualita gia salvate restano persistite; verificare e aggiornare le singole
regole prima di ripetere un intervallo. Restano vietate regole attive con anni
sovrapposti, anche se una ha la checkbox selezionata.

## Significato di non notificato

`only_unnotified` e un booleano persistito, esposto dalle API di lettura e
scrittura delle policy. Il default e `false`: le regole esistenti continuano
ad applicarsi come prima. Non viene creata o attivata automaticamente alcuna
regola 2022/2023 e non vengono assegnate percentuali o date operative.

La scelta concordata e **consegna PEC o ricezione raccomandata documentata**:

- PEC: ricevuta `CONSEGNA` con data valida nei dati inCASS dell'avviso
  selezionato. Vengono considerate tutte le spedizioni presenti nella mappa
  ricevute, non soltanto la prima spedizione o l'ultimo stato visualizzato.
- Raccomandata: data esplicita di ricezione/consegna nel payload di una
  raccomandata associata all'avviso, comprese le associazioni cumulative.
- Accettazione PEC, stato di spedizione senza ricevuta, mancata consegna,
  data invio e generica `data_esito` non provano la consegna.
- Dati mancanti o illeggibili significano assenza di notifica documentata in
  GAIA, non certificazione dell'assenza di una notifica esterna.

Se la checkbox e attiva e la prova di consegna esiste, questa policy non viene
applicata all'avviso: non aggiunge maggiorazioni/interessi e non fornisce la
policy necessaria per candidarlo ai solleciti GAIA. Non viene scelta una
regola alternativa implicita. Gli importi gia materializzati da inCASS,
comprese le rateizzazioni, non sono annullati o riscritti.

La selezione e condivisa da lista, dettaglio, riepiloghi e candidati solleciti.
La decorrenza degli interessi resta distinta dall'eleggibilita della policy:
il comportamento storico basato anche sull'accettazione PEC non cambia.
Per interessi sui non notificati occorre impostare la data fissa o il fallback
desiderato; l'assenza di una decorrenza continua a non produrre interessi.

## Implementazione e compatibilita

- `tributi_policy_model.py`: modello policy, riesportato da `models.py` per
  preservare gli import esistenti; nuova colonna non nullable con default falso.
- `tributi_notification_evidence.py`: parsing date riusato senza cambiarne
  la semantica, prove di consegna e selezione della policy applicabile.
- `tributi_policy_repository.py`: persistenza dello scope e delle decorrenze.
- `calculation-policy-form.ts`: serializzazione delle opzioni annuali.
- `calculation-policy-options.tsx`: controlli annuali e raggruppamento visuale.

Autorizzazioni, formule economiche, politica di sovrapposizione, numerazione
avvisi e dati di produzione non vengono modificati da questa configurazione.

## Verifica e rilascio

La suite API precedente e stata eseguita prima della modifica: file runtime
backend interessati al 100% statement. I nuovi scenari esercitano dati reali
in SQLite e richieste API: nessuna notifica, accettazione, mancata consegna,
consegna PEC, ricezione raccomandata, sola spedizione e solo esito generico.
Verificano CRUD, lista, dettaglio, riepilogo, candidati e disattivazione della
checkbox. Altre prove riguardano dati incompleti e ricevute di piu spedizioni.

Test UI montati verificano personalizzazione annuale, tassi azzerati per le
componenti escluse, date, scope, raggruppamento, modifica della singola regola
e reset. Migration test: upgrade/downgrade reale SQLite, conservazione regole
e default falso per le righe preesistenti. La stessa prova passa su PostgreSQL
16 isolato con le dipendenze dell'immagine candidata; verificati anche upgrade
Alembic, riavvio idempotente e compatibilita dell'immagine di rollback.

Il preflight di produzione rileva backend `gaia-backend:inaz-details-20261008`,
revisione Alembic `20261005_1500`, mentre il repository include revisioni
successive di altri moduli. `tributi_repositories.py` live contiene inoltre
implementazioni precedenti di parsing importi e classificazione avvisi speciali.
Il rilascio non deve sostituirle implicitamente ne applicare migrazioni estranee.
Il rilascio autorizzato e isolato: backend derivato dall'immagine live, con
soltanto sei moduli Tributi e la nuova migration. Le due implementazioni live
precedenti di parsing/classificazione sono preservate nel pacchetto operativo;
il repository conserva invece la propria versione corrente, testata a parte.
Il frontend viene ricostruito con le dipendenze dell'immagine precedente,
verificando l'identita del lockfile, senza aggiornare pacchetti.

La revisione `20261019_1400` deriva da `20261005_1500`, in un ramo indipendente.
La merge revision senza DDL `20261019_1500` unisce questo ramo a `20261007_1800`
nel repository completo. L'immagine isolata include solo `20261019_1400`:
`alembic upgrade heads` non esegue migrazioni Catasto/Personale estranee.
Un futuro rilascio completo eseguira le migrazioni mancanti e il merge;
il test del grafo verifica entrambi i percorsi, senza stampare revisioni saltate.

Directory operativa: `/opt/gaia/releases/tributi-rules-20261019`. Contiene
manifest SHA256, snapshot dei container, configurazioni Compose risolte,
backup privato della tabella policy/versione e dello schema, script separati
di deploy/rollback per backend e frontend. Si conservano gli overlay specifici
di ciascun servizio con `up --no-deps --no-build`, senza aggiornare il checkout
sporco `/opt/gaia` o ricreare worker e servizi estranei.

Rollback applicativo: prima `frontend-rollback.sh`, poi `backend-rollback.sh`.
Il backend di rollback contiene il codice live precedente e la sola migration
additiva, cosi il suo entrypoint riconosce la nuova revisione Alembic. Il
rollback non elimina la colonna ne i dati; non usare direttamente la vecchia
immagine priva della revisione, ne eseguire downgrade distruttivi automatici.
Rilascio completato il 19 ottobre 2026 alle 14:46 Europe/Rome, dalla feature
`c58250bb`. Immagini attive: `gaia-backend:tributi-rules-20261019` e
`gaia-frontend:tributi-rules-20261019`.

## Evidenze finali locali

- Backend: 132 test PASS nello stesso run con coverage: 111 API preesistenti,
  19 casi notifica e due test migration/topologia. Sull'immagine candidata con
  Python 3.11 passano anche tutti i 130 test API/notifica; il run locale usa 3.13.
- Coverage full-file dei sei file runtime backend nuovi/modificati: statement
  2447/2447 e branch 778/778, 100%. Nessuna nuova esclusione.
- Entrambe le migration: coverage 18/18 statement, 100%, incluse le funzioni
  di upgrade/downgrade del merge senza DDL.
- Frontend completo su dipendenze da lockfile: 5249 test in 322 file e 18 smoke,
  tutti PASS, nessuno skip. Coverage dei tre file runtime frontend: statement
  721/721, branch 712/712, funzioni 239/239 e linee 655/655, 100%.
- Typecheck e ESLint PASS, salvo il warning hook preesistente in `page.tsx`.
  Build produzione locale PASS, comprese tutte le 163 pagine generate.
  `make lint-backend` e Ruff sui file modificati PASS; i file Python nuovi
  passano anche il formatter. Restano i warning JWT della fixture di test.
- Ratchet autorevole `BASE_REF=61411aa8`: zero finding, poi sincronizzazione
  esplicita e `baseline-verify` riproducibile. Nessun cambio soglie o esclusioni.
- Metriche prima/dopo: `CalculationPoliciesPanel` cognitiva 26 -> 24,
  ciclomatica 27 -> 25, LOC 302 -> 258; `_upsert_calculation_policy` 10/10/35
  -> 9/9/30; `_precompute_tributi_effective_cores` 5/6/36 -> 4/5/33.
  I controlli annuali e le evidenze notifica hanno responsabilita dedicate;
  non si dichiara una riduzione globale del debito per questa feature.
- Graphify backend, Ruolo codice e frontend aggiornati via target dedicati con
  pruning forzato; JSON/report correnti. HTML backend/frontend omesso per il
  limite dimensionale, HTML Ruolo generato. Docs Ruolo aggiornati con
  `gpt-reserve`, chunk completato senza failure semantiche. Output non versionati.

## Verifica finale live

- Backend e frontend healthy; `/api/health`, home, login e pagina Tributi
  rispondono correttamente. Gli asset pubblicati contengono pulsanti annuali,
  filtri saldo, componenti annuali, blocchi e checkbox non notificati.
- OpenAPI espone `only_unnotified` in richiesta e risposta, con default falso.
  La route policy resta protetta: richiesta senza credenziali rifiutata.
- Database alla sola revisione `20261019_1400`; entrambe le regole preesistenti
  sono identiche al backup, salvo la nuova colonna falsa. Nessuna regola,
  percentuale, data operativa o notifica e stata creata/modificata dal deploy.
- Diff immagini backend verificato: esattamente sei moduli Tributi e una
  migration. Environment, comandi e mount preservati; nessun container
  permanente estraneo ricreato.
- Il primo tentativo ha attivato il rollback precauzionale: l'istantanea dei
  container includeva un processo temporaneo terminato durante i test.
  Ripristino riuscito; secondo tentativo con istantanea aggiornata PASS,
  preservando il controllo d'identita degli altri container. Entrambi i
  tentativi e il risultato finale sono conservati nella directory di rilascio.
- Nessuna regressione rilevata nel perimetro verificato. Restano warning
  preesistenti: hook ESLint, chiave JWT delle fixture e metadata Compose del
  volume PostgreSQL recuperato (nessuna modifica del volume).

Non e stata eseguita una verifica browser autenticata; le interazioni sono
coperte dai test UI montati. Restano i limiti funzionali dichiarati sopra:
salvataggio multianno non atomico e divieto di policy annuali sovrapposte.
