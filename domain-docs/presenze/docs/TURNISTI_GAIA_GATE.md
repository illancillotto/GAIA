# Turnisti GAIA e GATE

Per lo stato del rilascio precedente vedere il report operativo GATE
`docs/TURNISTI_RELEASE_2026-10-05.md`. L'estensione senza scadenza descritta qui
è ora applicata in produzione, dopo autorizzazione esplicita dell'utente.

Nelle Giornaliere GATE, **Gestisci turnisti** permette di selezionare collaboratore,
tipologia e date. Le date iniziali coprono tutto il mese; due date uguali assegnano
un singolo giorno. Tipologie iniziali: `acquaiolo`, `telecontrollo`, `none`.
GAIA offre lo stesso controllo nel dettaglio della giornaliera e una T nella matrice.

## Regole

- Il teorico locale configurato è 420 minuti. Il buono automatico richiede
  almeno 420 minuti ordinari effettivi dal 26/08/2026.
- Timbrature INAZ complete e positive attestano il turno. Durata inferiore a 7 ore:
  ore mancanti da verificare, nessun buono automatico. Timbrature mancanti, incomplete o
  sovrapposte: verifica bloccante e nessun buono automatico.
- Buono manuale e buono da turno danno complessivamente un solo buono nella giornata.
- Mattina e sera usano la stessa durata; non si deduce un'entrata obbligatoria né
  una pausa non timbrata. L'alternanza settimanale comunicata non richiede di
  cambiare il flag ogni settimana. Senza calendario e settimana di partenza
  attestati non si genera un'anomalia di rotazione presunta.
- Si preservano le categorie di ore notturne/festive. Oltre le 7 ore, i minuti
  sono separati come eccedenza: rimangono applicabili i controlli ordinari
  sull'autorizzazione dello straordinario.
- Una giornata senza timbrature con codice INAZ SAB/DOM/RIPTURN/SMONTO è riposo,
  senza ore lavorate né buono. Le assenze seguono il riconoscimento INAZ già
  esistente; non si accetta un generico numero di minuti come giustificazione.
- Le due tipologie condividono le regole iniziali. Eventuali eccezioni future
  richiederanno regole esplicite e test per la tipologia interessata.

## Persistenza e precedenza

Le assegnazioni sono intervalli persistenti, separati dai record importati:
valgono anche per giornate importate successivamente. GATE comanda; GAIA non può
modificare intervalli sovrapposti a un'assegnazione GATE, inclusa la revoca `none`.
Tra assegnazioni della stessa sorgente prevalgono timestamp e identificativo del
comando. GATE attesta identità, record e timestamp sul server e ordina anche due
modifiche nello stesso millisecondo. Entrambi i trasporti GAIA applicano lo stesso
servizio idempotente con lock sul collaboratore.

ACK, errori e snapshot nuovi non cancellano l'assegnazione GATE. Gli errori
rimangono visibili. Dopo una revoca contro uno snapshot ancora turnista, GATE
azzera il diritto automatico e invalida i conteggi fino al nuovo ricalcolo GAIA.

La migrazione GAIA `20261003_1200` aggiunge `presenze_shift_assignments`; dipende
dalla revisione `20261002_1030`. La catena è stata rilasciata, insieme alla nuova
`20261005_1500` per la durata senza scadenza. Il checkout contiene altre modifiche
locali: i rilasci mirati hanno preservato ed escluso il lavoro degli altri team.


## Verifica corrente

Esiti, coverage full-file, matrice comportamento→test e problemi residui sono nel
[report coordinato](TURNISTI_COORDINATED_VERIFICATION_2026-10-05.md).
I risultati del report del 3 ottobre sono storici: non certificano il checkout
attuale. La coverage GATE legacy è stata chiusa; le regressioni del ciclo turnisti
sono state risolte nel [report slice](TURNISTI_COMPLEXITY_SLICES_2026-10-05.md).
Il gate globale osservato include regressioni Wiki dell'altro team, non assorbite
nella baseline. La verifica e l'applicazione operative senza scadenza sono nel
[report corrente](TURNISTI_OPEN_ENDED_2026-10-05.md).

## Contratto API

GATE usa `POST /api/admin/presenze/pending-actions`, con `action_type` =
`patch_daily_record`, `target_type` = `daily_record` e `target_id` della
 giornaliera autorizzata. Nel `payload`: `operation` = `set_shift_worker`,
`shift_worker_type`, `date_from`, `date_to` (date ISO nello stesso mese).
Per un'assegnazione senza scadenza inviare esplicitamente `date_to: null`:
la decorrenza vale anche nei mesi e negli anni successivi. Il campo non può
essere omesso. Gli intervalli con data finale restano ordinati nello stesso
mese. I dialoghi esistenti continuano a proporre intervalli mensili; la durata
senza scadenza è disponibile nel contratto API, non come nuovo controllo UI.
Identità, timestamp e command ID vengono attestati dal server: i valori
presentati dal client non possono cambiarli. Risposte: 201 salvato, 400 input
non valido/target assente, 401 non autenticato, 403 fuori scope o ruolo
insufficiente. L’assegnazione richiede console_admin/gateway_admin;
team_manager non può modificare questo attributo globale.

GAIA espone `POST /presenze/giornaliere/{record_id}/turnista` con body
`{"shift_worker_type":"acquaiolo","date_from":"2026-10-01","date_to":"2026-10-31"}`.
Risposta 200: giornaliera ricalcolata; 422 input non valido, 401 non autenticato,
403 permessi insufficienti, 404 record non visibile/assente, 409 intervallo GATE.
Il comando GAIA richiede ruolo admin/super_admin/hr_manager, modulo Presenze
e record visibile. Essere proprietario della sola giornata non autorizza
l’assegnazione della persona su un intervallo. UI e API applicano lo stesso limite.
LAN e outbound applicano lo stesso servizio con metadati GATE attestati.
I record restituiscono tipo, sorgente, versione delle regole e provenienza del
buono; `shift_covered_absence_minutes` trasporta la copertura riconosciuta da GAIA.

La migrazione aggiuntiva `20261005_1500`, dopo `20261003_1200`, rende nullable
la data finale. Il downgrade rifiuta di procedere se esistono assegnazioni
senza scadenza: occorre prima chiuderle esplicitamente, senza perdita silenziosa
dei dati. Sovrapposizioni, revoche, precedenza GATE e retry conservano la
semantica precedente anche con estremi aperti.

La richiesta corrente è di assegnare nove acquaioli dal **01/09/2026**, senza
scadenza. È **DONE**: rilascio e inserimento reale completati, snapshot settembre
e ottobre verificati e agosto senza flag. Il dettaglio dei controlli è nel
[report assegnazioni permanenti](TURNISTI_OPEN_ENDED_2026-10-05.md).

## Piano e residui

- [x] Modelli, API, regole, sincronizzazione, UI e test implementati e rilasciati.
- [x] Review architetturale: nessuna dipendenza applicativa nuova, nessuno stack parallelo.
- [x] Verifica funzionale e coverage full-file completate.
- [ ] Quality gate globale GAIA: regressioni Wiki dell'altro team fuori scope;
  il perimetro turnisti passa. Vedere il report corrente sulle assegnazioni permanenti.
- [x] Rilascio coordinato autorizzato; catena Alembic applicata fino a `20261005_1500`.
- [x] Verifica live dei nove collaboratori richiesti: flag settembre/ottobre presente,
  agosto senza flag, decorrenza e scadenza NULL confermate nella persistenza GAIA.

L'alternanza settimanale è una pratica comunicata, non un calendario attestato.
Le eccezioni per tipologia e più turni nella stessa giornata non sono state
richieste né introdotte; il conteggio attuale resta massimo un buono/giornata.


## Correzione slice successiva

Il 2026-10-05 sono state rimosse le19regressioni del ciclo, senza cambiare
baseline/soglie. Risultati e stato corrente: [report slice](TURNISTI_COMPLEXITY_SLICES_2026-10-05.md).
Gli esiti precedenti restano storici; il gate globale include lavoro Wiki unrelated.
