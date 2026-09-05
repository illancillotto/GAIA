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

Se due candidati sono equivalenti, uscita `2` e messaggio di configurazione.
Non scegliere il candidato piu vicino in silenzio.

Il fallback per nome qualificato tra path diversi si applica solo quando il
path baseline non esiste piu nel report corrente e il candidato e unico. Se
piu path rimossi espongono lo stesso nome, il matcher non sceglie: il callable
resta nuovo e le normali soglie error-level continuano ad applicarsi. Anche un
move riconosciuto conserva il confronto completo delle metriche legacy, quindi
non autorizza regressioni o debt laundering.

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
