# Turnisti GAIA e GATE

Implementazione locale, senza deploy né migrazioni di produzione.

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
attualmente dalla revisione locale `20261002_1030`. Verificare la catena completa
prima di qualsiasi rilascio, perché il checkout contiene altre modifiche locali.


## Verifica corrente

Esiti, coverage full-file, matrice comportamento→test e problemi residui sono nel
[report coordinato](TURNISTI_COORDINATED_VERIFICATION_2026-10-05.md).
I risultati del report del 3 ottobre sono storici: non certificano il checkout
attuale. La coverage GATE legacy è stata chiusa; GAIA presenta regressioni del
ratchet nei file del ciclo. Non sono assorbite nella baseline.

## Contratto API

GATE usa `POST /api/admin/presenze/pending-actions`, con `action_type` =
`patch_daily_record`, `target_type` = `daily_record` e `target_id` della
 giornaliera autorizzata. Nel `payload`: `operation` = `set_shift_worker`,
`shift_worker_type`, `date_from`, `date_to` (date ISO nello stesso mese).
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

## Piano e residui

- [x] Modelli, API, regole, sincronizzazione, UI e test implementati localmente.
- [x] Review architetturale: nessuna dipendenza applicativa nuova, nessuno stack parallelo.
- [x] Verifica funzionale e coverage full-file completate.
- [ ] Quality gate GAIA: regressioni del ratchet da risolvere prima del commit;
  vedere [report corrente](TURNISTI_COORDINATED_VERIFICATION_2026-10-05.md).
- [ ] Rilascio coordinato previa autorizzazione; includere la catena Alembic completa.
- [ ] Verifica live dei dati citati nella telefonata: il codice non dimostra il recupero dei dati reali.

L'alternanza settimanale è una pratica comunicata, non un calendario attestato.
Le eccezioni per tipologia e più turni nella stessa giornata non sono state
richieste né introdotte; il conteggio attuale resta massimo un buono/giornata.


## Correzione slice successiva

Il 2026-10-05 sono state rimosse le19regressioni del ciclo, senza cambiare
baseline/soglie. Risultati e stato corrente: [report slice](TURNISTI_COMPLEXITY_SLICES_2026-10-05.md).
Gli esiti precedenti restano storici; il gate globale include lavoro Wiki unrelated.
