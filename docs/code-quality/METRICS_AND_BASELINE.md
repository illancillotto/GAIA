# Metriche, soglie e baseline

Le soglie seguenti sono una configurazione iniziale da validare sulla prima
scansione. Il debito legacy non deve bloccare l'introduzione del sistema; nuove
violazioni e peggioramenti devono invece essere rilevati subito.

## Soglie iniziali per callable

| Metrica | Warning | Errore |
| --- | ---: | ---: |
| Complessita ciclomatica | 10 | 15 |
| Complessita cognitiva | 15 | 25 |
| Righe effettive | 50 | 80 |
| Profondita di annidamento | 4 | 5 |
| Parametri | 5 | 7 |

## Soglie iniziali per file o componente

| Metrica | Warning | Errore |
| --- | ---: | ---: |
| Righe effettive per file | 500 | 800 |
| `useState` per componente/hook | 10 | 20 |
| `useEffect` per componente/hook | 5 | 8 |

Le soglie LOC per file sono segnali secondari. Un file grande ma dichiarativo
non equivale a una funzione ad alta complessita cognitiva. Il ranking deve dare
priorita a complessita, nesting, densita, frequenza di modifica e rischio.
Le soglie file sono comunque calcolate e versionate: una nuova violation
error-level fallisce e il debito file legacy gia sopra warning non puo crescere.

## Regole di valutazione

### Codice nuovo

- warning: report non bloccante;
- errore: fallimento del gate differenziale;
- nessuna eccezione automatica.

### Codice legacy invariato

- puo restare sopra soglia se registrato in baseline;
- deve essere visibile nel report;
- non blocca per il solo fatto di essere legacy.

### Codice legacy modificato

- nessuna metrica primaria puo peggiorare;
- il debito aggregato dei file coinvolti non puo aumentare;
- una nuova violation fallisce anche se il massimo del file diminuisce;
- un miglioramento rimuove o riduce la relativa voce di baseline.

## Schema minimo della baseline

La baseline deve contenere almeno:

```json
{
  "schema_version": 2,
  "generated_at": "ISO-8601",
  "source_commit": "git-sha",
  "engines": {
    "python": {"name": "...", "version": "..."},
    "javascript": {"name": "...", "version": "..."}
  },
  "scope": {"include": [], "exclude": []},
  "files": {}
}
```

Ogni callable registra:

- percorso normalizzato;
- nome qualificato;
- tipo;
- fingerprint strutturale;
- posizione secondaria;
- metriche;
- violation attive.

Il formato reale puo aggiungere campi, ma non puo omettere provenance, versioni
dei motori e identita strutturale.

## Matching

Ordine:

1. stesso percorso e nome qualificato;
2. rename Git confermato;
3. fingerprint AST compatibile;
4. nome qualificato unico proveniente da un path rimosso, per split modulari
   che richiedono alias o accessi attributo equivalenti;
5. posizione come tie-breaker.

Il matching tramite fingerprint tra percorsi diversi considera soltanto
candidati baseline il cui percorso di origine non e piu presente nel report
corrente. Il riuso di una forma AST comune in un file nuovo non deve essere
scambiato per un rename quando le sorgenti originali esistono ancora.

Nel worktree locale, le righe aggiunte comprendono anche i file non tracciati
restituiti da `git ls-files --others --exclude-standard`. `git diff` da solo
non include quei file. Questo consente al matcher di classificare come nuovo
un callable interamente aggiunto quando il matching resta ambiguo, senza
indebolire le soglie: le sue violation error-level continuano a fallire.
I file ignorati non entrano nel calcolo; il fallback non autorizza move o
regressioni e non modifica la baseline.

Se due candidati sono equivalenti, uscita `2` e messaggio di configurazione.
Non scegliere il candidato piu vicino in silenzio.

Per un gruppo con stesso path, nome e fingerprint, il confronto puo provare
l'assenza di regressioni senza assegnare identita individuali: il multinsieme
delle tuple di metriche correnti deve essere un sottoinsieme di quello baseline.
Ogni occorrenza corrente consuma un'occorrenza distinta della stessa tupla:
sono ammesse rimozioni di duplicati invariati, non il riuso della stessa voce
per piu callable. Metriche diverse o molteplicita maggiori non godono di questa
equivalenza; continuano il matching ordinario e la gestione delle ambiguita.
Questa regola non abilita matching fra path o nomi diversi.

Un gruppo puo anche crescere per callable interamente aggiunti nel diff:
in quel caso tutte le occorrenze non aggiunte devono riprodurre esattamente
il multinsieme completo delle metriche baseline. Solo allora gli invariati
sono equivalenti come gruppo e le aggiunte restano codice nuovo, senza
ereditare metriche legacy, anche se path/nome/fingerprint/riga coincidono
con una voce baseline. Aggiunte parziali, survivor mancanti o metriche
diverse non beneficiano di questa estensione; proseguono nel matching
ordinario. Le violation error-level del codice aggiunto continuano a fallire.

Il fallback per nome qualificato tra path diversi si applica solo quando il
path baseline non esiste piu nel report corrente e il candidato e unico sia
nella baseline sia nel report corrente. I nomi sintetici `<callback>` e
`<anonymous>` non identificano ownership e non possono usare questo fallback:
una nuova `useEffect[0]<callback>` GIS non e un move di una callback wiki rimossa.
Il matching per fingerprint resta disponibile per move strutturalmente identici. Se
piu path rimossi espongono lo stesso nome, il matcher non sceglie: il callable
resta nuovo e le normali soglie error-level continuano ad applicarsi. Anche un
move riconosciuto conserva il confronto completo delle metriche legacy, quindi
non autorizza regressioni o debt laundering.

## Provenance sorgente per ambiguita residue — R16

Il resolver ordinario conserva priorita, fingerprint, multinsiemi, prenotazioni
e fallback esistenti. Una sua ambiguita puo essere risolta soltanto con prova
aggiuntiva dai sorgenti, senza modificare baseline o scegliere il candidato
piu vicino: il commit sorgente e `baseline.source_commit`, non necessariamente
il merge-base da cui si legge il JSON autorevole.

Si leggono byte Git immutabili senza replacement refs e byte correnti, quindi
si riscansionano entrambi. L'intero multinsieme di callable del path deve
corrispondere a identita, span, fingerprint e metriche dei report forniti.
Un diff Git zero-context verificato sui byte mappa soltanto righe invariate;
entrambi i confini devono corrispondere allo stesso span baseline e avere
contesto esterno invariato e univoco. Senza tale prova resta exit `2`.

La prova rifiuta span monoriga, confini/contesto modificati, ownership multiple,
consumatori duplicati e owner gia reclamati dal resolver ordinario. Ogni
confronto conserva uno snapshot coerente per path, comprese le prove rifiutate,
e un registro locale degli owner utilizzati. Nessuna cache globale o identita
trasferita tramite metadati diff del chiamante.

Il parametro Python keyword-only `source_paths` permette diagnosi exterior
con sorgenti esatti senza applicarli al checkout; non accetta identita o mapping.
Il medesimo binding tramite scansione si applica a questi byte. Un confronto
exterior PASS non certifica equivalenza funzionale o coverage del candidato.
I normali controlli di regressione restano attivi dopo il matching provato.

## Posizione contraddetta dai sorgenti — R39

La correzione candidata R39 riguarda soltanto un owner posizionale di un gruppo
con nome duplicato e fingerprint diverso, dopo le prenotazioni ordinarie. Non
modifica il resolver diretto o la prova R16 a due confini. Lo snapshot Git/AST
completo del path deve validare entrambi i report prima che un header multilinea
invariato possa contraddire positivamente la posizione dell'owner selezionato.

Un owner alternativo richiede due fence esterne invariate, univoche e ordinate,
un solo owner/consumer compatibile nell'intervallo e start mappato corrispondente.
Gli antenati compatibili sovrapposti non vengono scartati; i peer sui confini
chiusi impediscono la prova. Prenotazioni, multinsiemi consumati e ledger locale
impediscono il riuso. Le metriche non scelgono l'identita: tutti i confronti
PRIMARY restano attivi, anche sotto soglia. Contraddizione provata senza owner
dimostrabile produce exit `2`, non il riuso dell'owner smentito.

Il fallback legacy senza header mappato o senza sorgenti validati resta un
limite preesistente, non una nuova certificazione universale dell'identita.
Replay globale exit `2` e ratchet locale exit `0` sono risultati distinti; la
correzione del matcher non certifica il comportamento di un candidato UI esterno.
Ammissione R39 confermata da final/root indipendenti nel registro della campagna;
nessuna baseline o soglia viene aggiornata per assorbire divergenze.

## Ambiguita risolta dal contesto sorgente — R146

Quando il matching resta `ambiguous_identity` per un pareggio di distanza, lo
snapshot sorgente validato puo risolvere l'owner soltanto se il contesto lo
prova: fence invariate e mappate attorno al callable, un solo candidato
compatibile non prenotato e nessun fratello non rivendicato in grado di
contendere l'owner. Le metriche non scelgono mai l'identita; i pareggi non
dimostrabili restano exit `2`. L'owner risolto e soggetto al controllo del
budget condiviso (R147) e a tutti i confronti di regressione.

## Budget condiviso fra callable correnti — R147

Dopo la risoluzione ordinaria, se due o piu callable correnti risolvono allo
stesso callable baseline (o il fingerprint dell'owner resta detenuto da un
gruppo di gemelli equivalenti), il budget non puo essere prestato in silenzio.
Il detentore e l'unico condivisore la cui prima riga, nello snapshot sorgente
validato, mappa sulla prima riga dell'owner e non risulta aggiunta nel diff.
Ogni altro condivisore viene valutato anche come callable nuovo; senza
detentore provato, soltanto i condivisori interamente aggiunti. Il confronto
con l'owner resta sempre attivo, cosi un one-liner modificato non perde il
ratchet; nessun owner nuovo viene scelto. Il controllo aggiunge soltanto
finding `new_callable_violation`: exit `2` e confronti esistenti invariati.

Limiti noti: con prima riga dell'hotspot modificata e ultima riga allineata
dal diff all'aggiunto, il prestito resta possibile (preesistente). Un hotspot
riscritto su ogni riga con un fratello omonimo aggiunto nella stessa change
puo fallire come nuovo (fail-closed); separare l'aggiunta in un'altra change.

## Debt laundering da bloccare

- rinominare un simbolo per farlo apparire nuovo o sparito;
- spostare una funzione senza trasferire la baseline;
- dividere una funzione in wrapper banali mantenendo lo stesso debito totale;
- copiare rami complessi in piu file;
- eliminare una violation aggiornando soltanto il JSON;
- escludere cartelle applicative.

Per i file modificati confrontare:

- somma e massimo delle complessita;
- densita;
- numero di violation;
- LOC effettive;
- numero di callable;
- variazioni sospette tra file coinvolti nello stesso diff.

## Eccezioni

Le eccezioni possono coprire solo strutture prevalentemente dichiarative, per
esempio:

- modelli/schema Pydantic o SQLAlchemy con poca logica;
- mapping e costanti;
- file di tipi TypeScript;
- configurazioni;
- codice generato identificabile;
- migration, limitatamente alla complessita funzionale.

Ogni eccezione deve avere:

- percorso esatto o pattern stretto;
- regola/metrica;
- motivazione concreta;
- owner;
- data di introduzione;
- data di scadenza o motivazione dell'assenza;
- riferimento a issue/decisione quando disponibile.

Vietati wildcard di intere directory runtime e ignore senza scadenza per codice
imperativo.

## Aggiornamento

`complexity-check`, `complexity-changed` e `complexity-ratchet` sono read-only.
Il controllo autorevole e `complexity-ratchet`: carica la baseline dal
merge-base. Una baseline modificata nella stessa change non puo autorizzare il
codice che la modifica.

`complexity-baseline` propone una nuova baseline, ma deve fallire se questa:

- aggiunge una violation;
- aumenta una metrica legacy;
- amplia un'esclusione;
- perde il matching senza spiegazione;
- usa versioni di motore non compatibili senza migrazione dichiarata.

L'aggiornamento deve inoltre fallire per ogni variazione non approvata di
`scope.include` o `scope.exclude`, anche quando la versione del motore non
cambia.

Il diff della baseline fa parte della review del codice.

## Classificazione di un hotspot

Una iterazione e `IMPROVED` solo quando cala la metrica obiettivo e gli
aggregati dimostrano che il debito non e stato spostato. Se testabilita o
struttura migliorano ma la metrica obiettivo e le violation restano invariate,
l'esito corretto e `REORGANIZED_AND_CHARACTERIZED`.
