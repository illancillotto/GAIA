# Capacitas — policy locale di risoluzione frazione

## Perimetro R10

La slice di campagna introduce una policy pura adiacente al workspace frontend,
`frontend/src/components/elaborazioni/capacitas-fraction-resolution.ts`, per
deduplicare le cinque transizioni del dialogo di risoluzione frazione.
Non cambia API, autorizzazione, parsing dei dati o orchestrazione delle richieste.
Il rilascio resta soggetto alla review e alla certificazione della branch di
campagna; questo documento non attesta un deploy o il completamento globale.

## Responsabilita e invarianti

Il workspace conserva apertura/chiusura del dialogo, token, chiamata API,
payload, attesa della risposta e filtro delle anomalie. La policy importa
soltanto tipi API e riceve lo stato nullable, un evento e il relativo payload.
Non introduce hook, effetti, chiamate esterne o un reducer generico.

| Evento | Campi aggiornati; gli altri restano invariati |
| --- | --- |
| `selected` | `selectedFrazioneId` dalla candidata |
| `started` | `busy = true`, `error = null` |
| `synchronized` | `busy = false`, `success = true` |
| `unsuccessful` | `busy = false`, errore risposta o `Errore sync` |
| `rejected` | `busy = false`, messaggio `Error` o `Errore` |

Lo stato null resta null per tutti gli eventi; nessun campo del payload viene
letto prima di questa guardia. Le chiamate restano nei precedenti updater
funzionali, preservando ordine, valutazione lazy e semantica delle closure.
Successo non cancella un precedente errore, e fallimento non cancella successo.

Una risposta tardiva continua ad aggiornare il dialogo corrente anche se la
richiesta proviene da una riga precedente; payload e filtro mantengono invece
l'identita catturata all'avvio. Questo comportamento legacy e caratterizzato,
non corretto dalla slice. Non si aggiungono ownership delle richieste,
cancellazione, generation guard o normalizzazione dello stato.

## Reader e contratti di libreria

La rimozione dei fallback ridondanti usa soltanto invarianti dimostrati di
costruzione delle stringhe, mappa degli header e preview, oppure del reader
SheetJS `0.20.3` con le opzioni effettive `defval: null` e `raw: false`.
Restano validazione, alias/precedenza, prima sheet, ritorni vuoti, indici delle
righe dense e colonne opzionali. La prova di densita dei record deve essere
rivalidata se cambia versione SheetJS, opzioni o pipeline del reader.
Le guardie nullable del dialogo non sono classificate come codice morto.

## Verifiche e riferimenti

Le dodici nuove caratterizzazioni rendered precedono il refactor e proteggono
UI → stato → API → UI con richieste sovrapposte, errore/successo conservati,
token assente, selezione durante la richiesta e chiusura/riapertura.
I quattordici test diretti della policy verificano transizioni, immutabilita,
null e accesso lazy; non costituiscono prova di reachability browser privata.

Evidenze complete: `reports/code-quality/READINESS_R10_CAPACITAS_2026-10-09.md`,
`reports/code-quality/SLICE_R10_CAPACITAS_2026-10-09.md` e report indipendenti
di review/verifica R10. Soglie, baseline, esclusioni e policy100% invariati.
