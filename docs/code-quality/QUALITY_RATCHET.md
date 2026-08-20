# GAIA Quality Ratchet

## Decisione

Il branch `gaia/code-complexity-refactor` viene conservato come esperimento e
fonte di evidenze, ma non va integrato integralmente e non deve ricevere nuovi
hotspot. Lo snapshot di riferimento e `52798f964301a382bba37a794e4d5892ff06807d`.

Il programma passa da una campagna di refactoring a un quality ratchet:

- gli sviluppi ordinari non devono aumentare il debito nel perimetro toccato;
- una semplificazione locale e ammessa solo se coerente con la responsabilita
  gia modificata e coperta da test;
- gli hotspot dedicati si aprono soltanto quando ostacolano una feature, i test
  o la manutenzione;
- scanner, CI e coverage applicano le regole; la skill guida il processo ma non
  sostituisce i gate automatici.

## Evidenze dell'esperimento

- Catasto GIS ha validato il metodo su confini UI isolabili: il callable
  principale e sceso circa del `23%` in complessita cognitiva e del `26%` in
  complessita ciclomatica prima della stop condition.
- Presenze H2-I1 ha validato caratterizzazione ed estrazione, ma non la
  riduzione: il callable principale e rimasto a cognitive `577`, cyclomatic
  `482` e LOC `2314`; le `6` violation sono state trasferite al nuovo helper.
- H2-I1 deve quindi essere classificato `REORGANIZED_AND_CHARACTERIZED`, non
  `IMPROVED`.
- Il prototipo ha rivelato un difetto di enforcement: confrontare il codice con
  la baseline modificata nella stessa PR permette a una regressione coordinata
  di passare. Il gate autorevole deve leggere la baseline dal merge-base.

## Modalita ordinaria

Per ogni sviluppo sotto il perimetro runtime:

1. determinare i file modificati dal merge-base;
2. dichiarare gli invarianti rilevanti e usare i test della feature;
3. acquisire le metriche del perimetro prima della modifica;
4. implementare la feature senza introdurre nuove violation error-level e
   senza peggiorare il debito legacy;
5. applicare al massimo una semplificazione locale collegata alla feature;
6. verificare test, coverage, typecheck/lint e ratchet;
7. sincronizzare la baseline solo dopo il confronto con quella del merge-base;
8. aggiornare Graphify quando struttura o relazioni del modulo cambiano.

Una feature conforme puo terminare con debito invariato. Non deve essere
forzata a ridurre un hotspot non correlato.

## Modalita hotspot

Un refactoring dedicato richiede un obiettivo esplicito, un singolo hotspot e
una stop condition. L'esito e uno dei seguenti:

| Esito | Criterio |
| --- | --- |
| `IMPROVED` | cala la metrica obiettivo e il debito non viene spostato |
| `REORGANIZED_AND_CHARACTERIZED` | struttura o test migliorano, ma la metrica obiettivo/debito resta invariata |
| `NO_SAFE_CHANGE` | gli invarianti non consentono una slice sicura |
| `BLOCKED` | baseline ambigua, failure nuova o decisione funzionale necessaria |

Solo `IMPROVED` conta come riduzione della complessita. Gli altri esiti possono
essere utili, ma non autorizzano automaticamente una seconda iterazione.

Il gate automatico controlla identita e metriche callable/file, nuove violation
e regressioni. Non puo dimostrare da solo che una nuova astrazione abbia valore
semantico: per gli hotspot resta obbligatoria la review degli aggregati dei file
coinvolti e del diff delle violation. Un totale globale invariato non e prova di
miglioramento.

## Rollout

Il rollout deve avvenire con change brevi e separate:

1. fondazione: rules, skill, scanner, test, baseline e report, senza refactoring
   applicativi e senza CI bloccante;
2. enforcement: attivazione del gate solo quando la baseline revisionata e gia
   presente nel branch di destinazione;
3. uso ordinario: ratchet sulle feature in corso;
4. hotspot dedicati: solo su necessita concreta e uno per volta.

Il plugin non e necessario finche il processo resta specifico di GAIA. Va
riconsiderato soltanto per distribuzione multi-repository o hook condivisi.

## Coverage

La fondazione non indebolisce la policy corrente: resta richiesto il `100%` dei
file runtime nuovi o modificati. Un eventuale passaggio a coverage differenziale
su righe e branch legacy richiede una decisione separata e l'aggiornamento di
`docs/TEST_COVERAGE_100_PLAN.md` e dei gate CI.
