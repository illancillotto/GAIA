# R16 — Diagnosi read-only del matching Capacitas

## Ownership e stato

Diagnosi autorizzata dall'utente dopo l'esplicazione dei due blocchi R19/R16.
Owner `/root/r16_matching_diagnosis`, worktree dedicato
`/home/cbo/CursorProjects/GAIA-campaign-20261008-c0-tests`, branch
`audit/complexity-r16-matching`, HEAD
`9f62fe26d47c73f15a54a43e7fe78281c6102fe8`, merge-base autorevole
`55a1b1d35911451e018b662c2acc450bf5994ea2`.

Unico file repository scrivibile: questo nuovo report. Runtime, test, matcher,
scanner, configurazione, baseline e tutti gli input/candidati R16 congelati
sono read-only. Prima dell'analisi: working tree pulito; manifesto SHA-256
dei 3563 path tracked, hash
`3eede86a39a68d49f69cad5f2c28cbc0fb852373f852662e98e5dc04d7457234`.

**Primo checkpoint STATIC ONLY**: nessuno scanner/comparatore/typecheck/test/
coverage o gate era stato eseguito nella prima allocazione. Successivamente il
Coordinator ha autorizzato il replay controllato e trasferito esplicitamente
heavy a questo agente: gli esiti terminali sono nella sezione dedicata sotto.
Nessun commit, candidato integrato o input congelato modificato.

## Esito causale

La failure conservata e una vera ambiguita del matcher posizionale sugli input
forniti, non una prova di regressione runtime e non una scansione parziale che
abbia cancellato il contesto globale. Il candidato mantiene tutti i 87 callable
omonimi `Program<anonymous>` presenti nell'originale; **87 non significa 87
funzioni nuove introdotte dalla slice**.

Il candidato R16 `34afe117…` deduplica l'assegnazione della credenziale:
aggiunge un helper prima della UI e sostituisce quattro callback nella funzione
`loadCredentials`. Complessivamente sposta di cinque righe verso l'alto il
codice seguente. La callback che scatena l'ambiguita NON appartiene alla
responsabilita credenziali: e l'`onClick` del bottone **Sincronizza** nel dialogo
di risoluzione frazione. I suoi byte, fingerprint e metriche sono invariati
rispetto all'originale di questa slice.

La callback era gia cambiata nella precedente slice di transizioni frazione
R10 (`b12780e2`), usando `transitionFractionResolution`. Per questo il suo
fingerprint corrente non esiste nella baseline immutabile 55a. Il matcher deve
quindi ricorrere al fallback path/nome e al tie-breaker di posizione.

| Input | Span callback Sincronizza | Fingerprint | Cognitive / cyclomatic / LOC |
| --- | --- | --- | --- |
| Baseline 55a, handler precedente | 3202–3223 | `e4321f91c0f17279` | 14 / 10 / 22 |
| Originale R16, handler dopo R10 | 3195–3216 | `023e933d8cbd06b2` | 3 / 4 / 22 |
| Candidato R16, handler invariato | 3190–3211 | `023e933d8cbd06b2` | 3 / 4 / 22 |

La baseline contiene inoltre l'anonimo del bottone **Chiudi**, a riga 3193,
fingerprint `169cc3d4299da6af`, cognitive 0 / cyclomatic 1 / LOC 1.
`span_distance` assegna distanza **zero a qualunque span sovrapposto**:

| Callback corrente | Baseline Sincronizza 3202–3223 | Baseline Chiudi 3193 |
| --- | ---: | ---: |
| Originale 3195–3216 | 0 | 2 |
| Candidato 3190–3211 | 0 | 0 |

L'originale conserva un minimo unico. Il candidato introduce un pareggio
puramente posizionale, senza modificare la callback interessata. Il matcher
non puo scegliere fra due baseline con comportamenti/metriche diversi, e
correttamente interrompe il confronto invece di attribuire un'identita a caso.

`resolve_baseline_callable` cerca prima il fingerprint, riserva i fingerprint
unici per altri callable correnti e solo poi usa il tie-breaker. In questo
gruppo riserva 6 record, lasciando **81** candidati effettivi. Il finding
`candidates: 87` riporta la dimensione iniziale di `same_identity`, non il numero
finale dei candidati rimasti e nemmeno il numero di record a pari distanza
minima. Per il callable responsabile i minimi sono i due record illustrati.

Un secondo anonimo con fingerprint non presente in baseline,
`02f6dca2f34c70a9`, e il selettore frazione: originale 3158–3159, candidato
3153–3154, baseline 3165–3166. Rimane un minimo unico (distanza 6→11) e non e
il punto del pareggio. Entrambi gli span conservano esattamente i byte sorgenti
dell'originale; nessuno dei due e codice interamente aggiunto dalla slice R16.

## Input metadata: problema separato, non soluzione automatica

Il comparatore exterior conservato acquisisce `changed` e `added_lines` dal
working tree ORIGINALE, poi sovrappone in memoria i callable del candidato.
Aggiunge il path workspace a `changed_only`, ma riutilizza le righe aggiunte
dell'originale. Questi metadati non descrivono fedelmente i due ulteriori hunk
del candidato.

Questo va corretto soltanto in un nuovo controllo diagnostico read-only,
preservando l'esecuzione fallita e senza modificare matcher o baseline. Non
autorizza a classificare callback invariate come nuove. L'ispezione statica dei
diff originale→candidato e baseline→candidato conferma che il callable
Sincronizza NON e wholly-added in nessuna delle tre rappresentazioni: metadati
originali, proposta exterior fedele, diff locale candidato. Anche il selettore
frazione non e wholly-added.

Quindi **fornire solamente le righe aggiunte corrette non risolve il pareggio**.
La regola per callable wholly-added non si applica a questo handler. Il replay
controllato successivo conferma exit2 e lo stesso finding sia con metadati
originali sia con metadati exterior fedeli; non e un gate candidato PASS.

## Provenance e hash

Directory congelate lette, senza riscrittura:

- `~/.cache/gaia-campaign/20261009-r16-original-characterization-8780c24d/`
- `~/.cache/gaia-campaign/20261009-r16-capacitas-credential-defaults/readiness/`

| Input | SHA-256 |
| --- | --- |
| Exterior `selected-workspace.tsx` | `34afe117a828dca307e90f72f1318ac17b4597e14f0e80a897601c8911fe8913` |
| Runtime originale workspace | `8111c1a4658055f29a4c0b56fb1113f8b06677f9e1e622e33d596ae3d9514f48` |
| Retained `full-original.json` | `0116c90c7b10b8fe7fac01f83f01da4f4c8a0d8b750a1cbbc28678771648e03a` |
| Retained `selected-metrics.json` | `e9412d7d86994bfd778543220b5e9c489f863d14c09fbffed47098298f942f0f` |
| Retained `original-metrics.json` | `112f81f0fd21c47c9c1ed5d17d7b99ede0f644e249fa1cc478a936ec443b8b84` |
| Retained `comparator.py` | `a4037bf0b0d2de292cbe20f601f3c773619f7a8be3e44c865176a211320818d3` |
| Retained `comparator-failure.json` | `774136e5074414f8f3e5e78e5f20bc489c373038cb9b9c2ae7ab74f0dcab80d8` |
| Retained comparator log | `5107a256254f21f07f2982805e823d17ab20811d89112cf04597f23ac19e148a` |
| Retained comparator command | `db2c25258aa412046b003cb87a38f2cb11360830e99b18df80da70ce72455e7e` |
| `tools/code_quality/complexity.py` | `315bc71fb48521f0049c968c8c4f262bdbb7077ad091c8f5f991b8088dc065af` |
| `tools/code_quality/js_ast_metrics.mjs` | `faf340a36a2a3730d313be34b17a89e1c96c6310084d3b63739e0a3fbf446b8d` |
| Baseline workspace/current 55a JSON | `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95` |

`complexity.py` e byte-identico al commit 55a. Tutti gli input elencati nel
manifesto retained `readiness-artifacts-before.json` sono stati ricalcolati:
zero drift. La failure precedente e conservata come audit-process exit 1
causato dall'assert sul risultato del comparatore: il matcher sottostante
restituisce l'ambiguita di configurazione, non una nuova violation metrica.
Non confondere l'exit del wrapper con quello del matcher.

## Evidenze nuove, soltanto statiche

Directory privata nuova:
`~/.cache/gaia-campaign/20261010-r16-matching-diagnosis/`.

- `protected-before.sha256`: tutti i 3563 path tracked prima dell'analisi.
- `static_inventory.py`: lettura JSON/sorgenti/Git, conteggi e distanze; nessun
  import/esecuzione del matcher, scanner o test.
- `static-results.json`: inventario input, span/fingerprint/metriche e controlli
  wholly-added; SHA-256
  `2d435572482a5a2fe6374481fa950058ed0557ace44cca5044dd8697bd2d3cfa`.
- `actual-original.diff`: diff Git unificato zero contro 55a sul runtime reale.
- `local-candidate.diff`: modello testuale zero-context originale→candidato.
- `proposed-faithful-exterior.diff`: modello testuale baseline→candidato;
  non spacciato per metadati gia certificati dal gate Git.

Il dato retained `full-original.json` e globale: il comparatore exterior
sostituisce solamente i record del workspace, preservando gli altri path.
Non e stato rigenerato alcun report globale in questa diagnosi.

## Riproduttore minimo: proposta statica originaria

Dopo il trasferimento heavy, creare un nuovo script/manifesto solo nella
directory privata di questa diagnosi; non toccare script/input originali.

1. Verificare hash baseline 55a, tool invariato, sorgente8111, candidato34af,
   report globale originale e manifesto protected. Usare l'intero report
   retained, non un report scoped che faccia apparire altri path rimossi.
2. Materializzare solo in directory privata i byte Git del workspace 55a e
   i byte esatti del candidato; ottenere `git diff --no-index --unified=0`,
   normalizzando esclusivamente il path destinazione al workspace canonico.
   Usare il parser **invariato** `parse_added_lines` per i metadati exterior.
   Per altri path mantenere i metadati del loro sorgente originale invariato.
3. Eseguire il controllo ORIGINALE completo contro la baseline immutabile,
   preservando finding ed exit senza assert anticipati.
4. Fare la stessa scansione exterior del candidato prevista nel comparatore
   retained, assegnando soltanto il path canonico e sovrapponendo SOLO i suoi
   record al report globale; nessuna identita scelta o metrica alterata.
5. Eseguire entrambi i controlli candidato→55a: metadati originali conservati
   (riproduzione failure) e metadati exterior fedeli (controllo causale).
   Pubblicare i risultati anche quando exit2; non convertirli in PASS.
6. Separatamente candidato→baseline locale costruita dal report originale,
   con metadati del solo diff locale originale→candidato. Questo confronto
   puo chiarire il delta R16 ma **NON sostituisce** il gate autorevole 55a.
7. Controllo negativo solo in memoria su un callable dal matching non ambiguo:
   aumentare una metrica oltre baseline e verificare che l'engine invariato
   la respinga. Non alterare sorgenti o input conservati.
8. Verificare nuovamente tutti i manifesti, congelare command/exit/finding/hash
   e fermarsi. Nessuna riparazione matcher/baseline, applicazione runtime,
   padding di righe o wrapper finalizzato a rendere verde il controllo.

La previsione statica era che il controllo con metadati fedeli conservasse
l'ambiguita Sincronizza: il callback non e wholly-added e la distanza resta0/0.
Il replay autorizzato successivo la conferma, come documentato di seguito.

## Replay controllato autorizzato — risultati terminali

Ownership registry aggiornata e messaggio esplicito del Coordinator hanno
trasferito heavy a questo agente sullo stesso worktree9f62. Nessun altro gate
GAIA e stato avviato da questo agente. Prima del replay: verifica di tutti i
3563 tracked path, del report statico congelato e dei 237 file retained nelle
due directory di input. Manifesto privato `retained-inputs-before.json`, SHA-256
`d5c1fea2d3ec0ff949264110d1024590fb5a6582e7d5d395aa467156efcd27d0`.

Il nuovo script `replay/controlled_replay.py` usa `complexity.py` invariato,
la baseline letta via `baseline_at_merge_base(55a, DEFAULT_BASELINE)` e il
report globale retained originale. Riscansiona frescamente il solo candidato
JS exterior tramite lo stesso `scan_js`, canonicalizzando esclusivamente il
path workspace. Sovrappone i suoi record al contesto globale completo: tutti
gli altri file/callable/finding restano esattamente invariati. Il report passa
da 20316 a20317 callable solo per il nuovo helper candidato, con1672file.

Per i metadati fedeli materializza solo in directory privata i byte Git del
workspace55a e i byte esatti candidato34af, esegue Git
`diff --no-index --no-color --unified=0` e usa `parse_added_lines` invariato.
Normalizza soltanto i path nelle intestazioni `---/+++`; preserva i metadati
originali per tutti gli altri path. Il diff locale originale→candidato e
costruito analogamente. I normali exit1 dei due `git diff --no-index` indicano
differenze previste, non fallimenti del replay; stdout/stderr/command/exit sono
conservati per entrambi.

Il confronto55a impiega il perimetro changed autorevole dal merge-base
(piu il path candidato), **non il confronto integrale di tutti i path
invariati**: il report usato resta globale per non perdere contesto di matching.
Non vengono assorbite o dichiarate risolte le30divergenze globali storiche.

Ogni confronto e eseguito in un subprocess distinto che termina con il vero
codice restituito dal matcher; il wrapper non sostituisce quei codici con0.

| Controllo | Exit processo / matcher | Finding | Interpretazione |
| --- | ---: | --- | --- |
| Originale globale, scope changed→55a | 0 / 0 | zero | Controllo originale PASS |
| Candidato, metadati originali→55a | 2 / 2 | `ambiguous_identity`, `Program<anonymous>`,87 | Failure retained riprodotta |
| Candidato, metadati Git fedeli→55a | 2 / 2 | stesso finding87 | Correzione dei soli metadati non basta |
| Candidato→riferimento locale originale, diff locale | 0 / 0 | zero | Controllo locale PASS, NON autorevole |
| Originale con aumento cognitivo solo in memoria→55a | 1 / 1 | `legacy_metric_regression`, `loadCredentials`,12→13 | Controllo negativo correttamente respinto |

Il riferimento locale e una serializzazione privata del report originale per
il solo controllo diagnostico: non e una baseline registrata/rigenerata o un
nuovo BASE_REF. Il suo PASS non autorizza l'integrazione e non risolve il gate55a.
Il controllo negativo modifica solo la copia in memoria di una metrica di
`loadCredentials`, il cui matching e unico; nessun sorgente o input retained
e alterato. Il finding ha delta1 e viene correttamente respinto anche sotto
la soglia warning cognitiva15, confermando il controllo non-regressione legacy.

Il wrapper termina0 perche TUTTI gli esiti diagnostici sono quelli previsti;
**il candidato autorevole resta exit2/BLOCKED_MATCHING**. Nessun assert PASS
su candidato, waiver, scelta identitaria, padding o correzione del matcher.
Nessuna failure inattesa, riavvio o ripetizione del replay.

Comando del wrapper, con cwd del worktree dedicato:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  /home/cbo/.cache/gaia-campaign/20261010-r16-matching-diagnosis/replay/controlled_replay.py
```

Il wrapper genera le cinque command/exit/log/result separate, preservando gli
exit0/2/2/0/1. Gli input prima del replay e quelli usati in ciascun confronto
hanno hash registrati. Nuove evidenze:

| Artefatto in `replay/` | SHA-256 |
| --- | --- |
| `controlled_replay.py` | `2048413c7c496303988740e1e53ef6fab5427631e994db70b3c46ad16754b669` |
| `fresh-candidate-scoped.json` | `f8a90f770c8974bd1a8651a52c4fd77be769911a629afd7f1ada5275318d9a38` |
| `candidate-full.json` | `60ba692b8143d23286fce39f727545fae78acdd86a915a3501e1967e9918c6ba` |
| `immutable-canonical.diff` | `8a022bc73d2ca85e6fcf3b669b68019a5e98ff46c4c596441c791ed81ccde3a0` |
| `local-canonical.diff` | `3a64df357b7a31ffaf750e2f35e8cec4a2d5134502935ad50e5c28301c5c3b81` |
| `faithful-metadata.json` | `73e1ca87a1097501e8f99ac973f98145e45394422a4dee2999fd49de4cda6652` |
| `cases.json` | `1e9250150dab51ad2af39b9cae756ce921563d598a271bfffe1818ca93a7a50f` |
| `replay-results.json` | `6be13b792a3feb41e81cb03ab8d5f4e96ba00197643349cd70300410e0b416ff` |
| `terminal-status.json` | `f4c0360234b33986e9ecea1564cf0173c56fc72b1870d80628896474b67bd95c` |

Proiezione candidato:1926error/2739warning/4665finding, rispetto all'originale
1926/2740/4666. Non e una riduzione runtime ottenuta: il candidato non e
applicato o certificato e queste cifre non entrano nel delta integrato.

Custody audit finale: tutti i3563tracked path e tutti i237retained file esatti;
zero drift negli input/scanner/matcher/baseline/config. Unico file repository
non tracciato di questa allocazione rimane questo report. `git diff --check`
PASS. Nessun test/type/coverage/build eseguito o dichiarato PASS per il
candidato; non richiesti per la presente diagnosi read-only.

Il processo shell originale `session64295` e terminale con exit0; tutti i suoi
subprocess sono terminali. Heavy esplicitamente **RELEASED** dopo custody audit
e freeze delle evidenze. Nessun commit o integrazione effettuato.

## Classificazione e azione successiva

`NO_CHANGE` runtime / `DIAGNOSIS_ONLY`, nessun `IMPROVED`. Il candidato R16
rimane **BLOCKED_MATCHING**, non integrato e non certificato. Coverage e test
dell'originale precedentemente verdi non dimostrano equivalenza del candidato.
Le proiezioni di riduzione metrica R16 restano proiezioni.

Il riproduttore read-only autorizzato e completato: l'ambiguita permane sul
gate autorevole anche con input fedeli. Qualunque cambiamento al tooling
richiede ownership/slice separata e prove che l'identita derivi da provenance
reale (non prossimita o scelta arbitraria). Non risolvere mediante baseline
inflation, esclusioni, soglie, cancellazione del finding o padding posizionale.

Nessun cambio di responsabilita/dipendenze/component boundary runtime:
nessun aggiornamento Graphify-code applicabile a questa diagnosi statica.
Campagna globale ACTIVE/INCOMPLETE; questo report non certifica il suo termine.
