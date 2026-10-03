# GAIA Dotazioni

Verifica corrente della change: `GATE_CLOSURE_2026-10-03.md` (gate isolato
PASS; baseline globale Wiki/MCP non sincronizzata, nessun deploy).

Dotazioni gestisce i beni operativi del Consorzio di Bonifica dell'Oristanese.
Il bene appartiene al Consorzio; assegnazione organizzativa e custodia fisica
sono relazioni distinte. Inventory conserva richieste di magazzino e sync
WhiteCompany. Nessun dato Inventory viene migrato o reinterpretato.

## Superfici

- Backend: `backend/app/modules/dotazioni/`, router `/api/dotazioni`.
- Frontend: `/dotazioni`, `/dotazioni/assets/{uuid}`.
- Link stabile per QR: `/dotazioni/by-code/{asset_code}`, autenticato.
- Documentazione: `domain-docs/dotazioni/docs/`.
- Migration: `20261001_1600_dotazioni.py`, successiva a `20261001_1400`.

## Modello e invarianti

- `dotazioni_assets`: UUID, codice leggibile univoco e immutabile, tipo
  estensibile, nome, dettagli tecnici facoltativi, stato fisico, note,
  flag attivo, autore e date di creazione/modifica.
- `assigned_org_unit_id -> org_unit.id`: disponibilita organizzativa corrente.
  Sono utilizzate le unita canoniche, incluse le squadre, senza creare Team.
  `structure_kind` resta quello della specifica unita referenziata.
- `dotazioni_custodies`: persona canonica `application_users.id`, presa,
  restituzione, autore delle due azioni, precedente custode e note.
- `dotazioni_events`: eventi append-only con autore, azione, timestamp e
  dettagli; le modifiche registrano valori prima/dopo, incluse le unita.

Una sola custodia aperta per asset e garantita dall'indice univoco parziale
`uq_dotazioni_open_custody WHERE returned_at IS NULL`. Le mutazioni bloccano
la riga asset con `SELECT FOR UPDATE`; trasferimento, storico e audit sono
scritti in una transazione. La precedente custodia viene chiusa e flushed
prima di inserire la successiva, con lo stesso timestamp UTC.

Gli stati persistiti sono `available`, `maintenance`, `lost`, `damaged`,
`retired`; `in_use` e derivato dalla custodia quando lo stato fisico e
`available`. Una restituzione conserva manutenzione/danno/smarrimento.
Disattivazione, pensionamento e collegamento mezzo sono bloccati se esiste
una custodia aperta. Non sono esposte modifiche retroattive dello storico.

Codice obbligatorio inserito dall'utente, normalizzato maiuscolo, fino a 64
caratteri alfanumerici, trattino e underscore; nessuna generazione con
`MAX()+1`. Tipo estensibile in minuscolo; brand, seriale e modello facoltativi
per consentire anche chiavi e strumenti. Il seriale non e universalmente
univoco: possono esistere beni senza seriale o con seriali non globali.

## Integrazioni

`network_device_id -> network_devices.id` e opzionale e univoco: Network
mantiene monitoraggio e associazione tecnica a utente. Non viene creata alcuna
custodia dal suo `assigned_user_id`. Il placeholder legacy
`device_inventory_links` resta invariato ed e distinto dalla relazione
Dotazioni; non viene alimentato dalla nuova feature.

`vehicle_id -> vehicle.id` e opzionale e univoco. Un asset di tipo `vehicle`
deve riferirsi a un mezzo esistente; targa e stato operativo sono letti dal
mezzo, senza copie persistite. Le azioni di custodia Dotazioni sono vietate
sui mezzi: conducente, sessioni di utilizzo e assegnazioni restano in
Operazioni. La guida non viene presentata come prova di custodia fisica.

I namespace `Team`, `OrganizationTeam` e `OrgUnit` non sono equiparati.
La vista per squadra filtra esclusivamente `OrgUnit`; nessun matching per
nome o ID. L'identita Presenze usa soltanto `application_user_id`, quella
WhiteCompany soltanto `gaia_user_id`, mai nome/email/matricola.

## Autorizzazione

Il modulo e abilitato da `application_users.module_dotazioni`, default false.
Il super-admin mantiene il bypass previsto dal resolver esistente.
Il CRUD utenti generico gestisce il flag; la PATCH legacy dei soli moduli
non viene ampliata. Le sezioni sono `dotazioni.view`, `manage`, `assign`,
`custody`, `history` e riutilizzano resolver, concessioni ruolo e override utente.

- View/history: minimo viewer, accesso agli asset del Consorzio.
- Manage/assign: minimo admin; un override puo concedere o negare il diritto.
- Custody: minimo admin, con concessione esplicita al ruolo operator in migration.
  Viewer non eredita il diritto per la parita di rank con operator.
- Operatore autorizzato: prende per se beni assegnati a un'unita di cui e
  membro tramite `OrgAssignment` attivo nella finestra temporale corrente.
- Restituzione: custode o gestore autorizzato; il custode divenuto inattivo
  puo essere sostituito dal gestore. Il login inattivo resta vietato.
- Passaggio: custode o gestore; un operatore puo passare solo a un utente
  attivo nella stessa unita assegnataria. Il gestore puo operare per terzi.

La responsabilita gerarchica non concede da sola poteri di gestione. In questa
iterazione non esiste una policy di mutazione limitata al sottoalbero del capo:
`manage` e un diritto di gestione del modulo, da concedere consapevolmente.

## API

| Metodo | Percorso relativo a `/api/dotazioni` | Funzione |
| --- | --- | --- |
| GET/POST | `/assets` | Lista paginata / creazione |
| GET/PATCH | `/assets/{uuid}` | Dettaglio / modifica |
| GET | `/assets/by-code/{code}` | Risoluzione codice stabile |
| GET | `/assets/{uuid}/custody` | Custodia corrente o null |
| GET | `/assets/{uuid}/custody-history` | Storico paginato |
| GET | `/assets/{uuid}/events` | Audit paginato |
| POST | `/assets/{uuid}/take` | Presa, destinatario facoltativo |
| POST | `/assets/{uuid}/return` | Restituzione |
| POST | `/assets/{uuid}/transfer` | Passaggio, destinatario obbligatorio |
| GET | `/operators/{application_user_id}/assets` | Beni in custodia alla persona |
| GET | `/org-units/{uuid}/assets` | Beni assegnati all'unita |
| GET | `/lookups` | Utenti attivi, unita, riferimenti e permessi |

Filtri: `search`, `asset_type`, `status`, `org_unit_id`, `holder_user_id`,
`active`, `page`, `page_size` (massimo 100). `active` omesso comprende anche
i disattivati; la UI parte dal filtro attivi. Conflitti di stato/concorrenza
restituiscono 409; riferimento inesistente/inattivo 422; permesso mancante
403; risorsa inesistente 404. I timestamp delle azioni sono prodotti dal server.

## Operativita e limiti

Applicare la migration con il normale flusso Alembic condiviso, poi abilitare
Dotazioni agli utenti autorizzati. Nessuna migration viene applicata al DB
operativo durante i test: le prove PostgreSQL usano schemi temporanei rimossi
al termine. Il downgrade elimina lo storico: richiede backup e decisione
esplicita prima dell'uso su un database con dati.

La UI offre lista, filtri per persona/unita/tipo/stato, scheda, modifica,
custodia, storico e link QR. Non genera immagini QR o PDF etichette.
Stati e tipologie note sono presentati in italiano senza cambiare i codici
API; le tipologie personalizzate mantengono il proprio nome. Le date sono
formattate in italiano nel fuso `Europe/Rome`, con ora legale/solare.
Lo storico presenta il nome del precedente custode, anche se inattivo,
tramite `handover_from_name` derivato dall'utente canonico (nome corrente,
non snapshot storico). Nessuna migration e necessaria per questa lettura.
Tabelle scorrevoli e focalizzabili da tastiera evitano l'allargamento della
pagina su mobile; azioni custodia hanno touch target di almeno 44 pixel,
feedback di caricamento e campi bloccati durante la registrazione.
La scheda mette in evidenza unita, stato e custode; i dati tecnici e le note
sono in un disclosure nativo richiudibile, utilizzabile anche da tastiera.
Il filtro unita evidenzia la vista della squadra selezionata; non e una nuova
anagrafica o una pagina separata.

Dal 2026-10-02 `/gaia/users/operatori-cruscotto` presenta per l'operatore
selezionato **Dotazioni in custodia**, riutilizzando `OperatorAssets` e
`GET /api/dotazioni/operators/{application_user_id}/assets`.
L'identita proviene solo da `detail.operator.gaia_user_id`: nessun fallback
per nome, email, ID WC o collaboratore Presenze. Mapping assente non genera
richieste; errori API restano locali al pannello. Al cambio operatore le
risposte tardive non mostrano custodie della persona precedente. Permessi
del cruscotto e API invariati. Verifiche: `CRUSCOTTO_VALIDATION.md`.
L'audit e consultabile via API; non e presente una pagina audit dedicata.
MDM, SIM avanzate, contratti, contabilita e acquisti sono fuori perimetro.

Per requisiti, execution plan e PROGRESS vedere `IMPLEMENTATION_PLAN.md`.
Per matrice funzionalita/test, verifiche e gap vedere `VALIDATION.md`.
