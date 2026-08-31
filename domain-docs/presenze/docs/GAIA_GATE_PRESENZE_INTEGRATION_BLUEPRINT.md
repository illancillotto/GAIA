# Blueprint integrazione GAIA / GATE Console Mobile - Presenze

Data: 2026-07-08

Stato implementazione GAIA:

- implementato il primo blocco backend per squadre operative GATE;
- aggiunte tabelle `organization_teams`, `organization_team_memberships`, `organization_team_supervisor_assignments`;
- aggiunti endpoint locali GAIA `/gate/presenze/teams`, `/gate/presenze/teams/{team_id}`, `/gate/presenze/teams/{team_id}/memberships`, `/gate/presenze/teams/{team_id}/supervisors` usati dalla UI GAIA;
- aggiunti endpoint `/gate/presenze/months/available`, `/gate/presenze/giornaliere`, `/gate/presenze/giornaliere/{record_id}`, `/gate/presenze/giornaliere/{record_id}/validate`, `/gate/presenze/giornaliere/{record_id}/patch`, `/gate/presenze/anomalie`, `/gate/presenze/anomalie/{record_id}/resolve`, `/gate/presenze/export/preview`, `/gate/presenze/export/generate`;
- aggiunto endpoint `/gate/presenze/rules` come fonte unica per mostrare in GAIA e GATE le regole operative del sistema;
- aggiunta pagina GAIA `/presenze/squadre` per creare squadre, cercare velocemente collaboratori importati dalle giornaliere e assegnare responsabili usando le API locali `/gate/presenze/teams`;
- esteso il sync outbound GAIA -> gateway GATE Mobile con capability `presenze_teams`, `presenze_months`, `presenze_giornaliere`, `presenze_anomalie`, `presenze_rules` e `presenze_pending_actions`;
- aggiunta pagina GAIA `/presenze/regole`, collegata alla sidebar Presenze, che consuma lo stesso contratto usato da GATE;
- aggiunti permessi bootstrap `presenze.gate.*`;
- copertura test del router `app.modules.presenze.gate_router`: `100%`.

## 1. Decisione architetturale

GAIA resta il sistema autorevole del dominio `presenze`.

GATE Console Mobile diventa il workspace operativo online per operatori e capi settore, con persistenza applicativa limitata a mese corrente e mese precedente. GAIA e installato in LAN/intranet e non deve essere esposto su internet: la sincronizzazione deve seguire il modello gia usato per contatori/giornaliere, cioe GAIA locale chiama in outbound il gateway GATE online, chiede il piano di sync e invia gli snapshot richiesti.

Questa scelta evita divergenze tra dashboard GAIA, giornaliere, anomalie, export e lavoro mobile.

## 2. Responsabilita dei sistemi

### GAIA

GAIA e responsabile di:

- collaboratori e profili contrattuali;
- giornaliere normalizzate;
- timbrature e dettaglio Inaz;
- regole anomalie;
- regole operative giornaliere;
- validazioni;
- audit;
- organigramma operativo e assegnazioni;
- generazione dati canonici per export;
- autorizzazioni e perimetro di visibilita.
- connector outbound verso gateway GATE online tramite `GATE_MOBILE_GATEWAY_BASE_URL` e `GATE_MOBILE_CONNECTOR_TOKEN`.

### GATE Console Mobile

GATE e responsabile di:

- esperienza operativa mobile;
- consultazione rapida di giornaliere, anomalie ed export;
- cache applicativa di mese corrente e mese precedente;
- lavorazione da parte di operatori e capi settore;
- generazione export lato GATE quando richiesta dal flusso operativo;
- ricezione e persistenza applicativa degli snapshot squadre/giornaliere/anomalie inviati da GAIA.

GAIA calcola i valori canonici di export; GATE compila fisicamente il template XLSM per garantire il download immediato anche senza attendere un nuovo ciclo di sincronizzazione. Entrambi dichiarano la stessa `export_rules_version`.

## 3. Perimetro funzionale minimo GATE

La sezione GATE dedicata alle presenze deve includere:

- pagina `Giornaliere`;
- pagina `Anomalie`;
- pagina `Export`;
- dettaglio completo della giornata;
- validazione giornaliera come in GAIA;
- note operative;
- filtro per collaboratore, squadra, mese, stato e gravita;
- vista mese corrente e mese precedente;
- audit visibile o consultabile almeno lato amministrativo.

## 4. Regole anomalie da rispettare

GATE deve usare la stessa logica operativa di GAIA.

Regola gia definita per le giornaliere:

- se le timbrature sono coerenti e l'unica differenza e extra/straordinario entro `3 ore`, la giornata non e un'anomalia bloccante;
- se extra/straordinario supera `3 ore`, la giornata deve entrare nella coda di verifica;
- se mancano timbrature essenziali, teorico, causale o richiesta coerente, la giornata resta da correggere o verificare;
- le anomalie tecniche Inaz residue non devono prevalere se GAIA ricostruisce una giornata coerente da timbrature, teorico e causali normalizzate.

Ogni payload verso GATE deve esporre una `rules_version`, in modo da rendere esplicito quale versione della logica ha prodotto lo stato.

## 5. Modello squadre e organigramma

Il modello raccomandato e generico, non solo `presenze-only`, ma con primo utilizzo nel dominio presenze.

Entita minime:

- `organization_teams`;
- `organization_team_memberships`;
- `organization_team_supervisor_assignments`.

Campi minimi `organization_teams`:

| Campo | Note |
| --- | --- |
| `id` | Identificativo squadra |
| `name` | Nome operativo, es. `Squadra Verde` |
| `code` | Codice stabile opzionale |
| `scope` | `presenze`, `gate`, `global` |
| `active` | Stato squadra |
| `created_from_channel` | `gaia_web` o `gate_mobile` |
| `created_by_user_id` | Utente che ha creato la squadra |
| `created_at`, `updated_at` | Audit tecnico |

Campi minimi `organization_team_memberships`:

| Campo | Note |
| --- | --- |
| `id` | Identificativo membership |
| `team_id` | Squadra |
| `collaborator_id` | Collaboratore presenze |
| `gaia_user_id` | `application_users.id` collegato al collaboratore, se mappato |
| `valid_from`, `valid_to` | Validita temporale |
| `role` | `member`, `lead`, `substitute` |
| `source_channel` | `gaia_web` o `gate_mobile` |

Campi minimi `organization_team_supervisor_assignments`:

| Campo | Note |
| --- | --- |
| `id` | Identificativo assegnazione |
| `team_id` | Squadra |
| `application_user_id` | Capo settore / operatore abilitato |
| `gaia_user_id` | Alias di trasporto dello stesso `application_user_id`; i valori devono coincidere |
| `permission_scope` | `view`, `validate`, `export`, `manage_team` |
| `valid_from`, `valid_to` | Validita temporale |

Regola consigliata:

- un collaboratore dovrebbe avere una sola assegnazione attiva principale nello stesso periodo;
- eventuali eccezioni devono essere esplicite tramite ruolo o flag dedicato;
- GATE puo proporre squadre e assegnazioni, ma GAIA deve validarle e persisterle.

### 5.1 Identita canonica GAIA/GATE/Presenze

La correlazione utente autorevole e una sola:

```text
GATE operator.gaia_user_id
  = GAIA application_users.id
  = supervisor.application_user_id
  = supervisor.gaia_user_id
```

`application_user_id` e il nome della foreign key interna GAIA; `gaia_user_id` e il nome esplicito nel contratto GATE. Non sono due chiavi alternative. GAIA deve propagare `gaia_user_id` su membership, supervisor, giornaliere e anomalie quando il collaboratore e mappato. Per giornaliere e anomalie il valore autorevole viene letto dal mapping corrente `PresenzeCollaborator.application_user_id`, non dalla copia denormalizzata eventualmente storica presente sul record giornaliero.

`collaborator_id` resta la chiave tecnica Presenze per giornaliere, anomalie, pending action ed export. `employee_code` e una matricola descrittiva del dominio Presenze e non deve mai essere confrontato con `gaia_user_id`.

GATE non usa nome, username, email o matricola come fallback autorizzativo. Un mapping assente, duplicato o incoerente deve fallire chiuso. Un valore numerico uguale in `gaia_user_id` ed `employee_code` non dimostra alcuna relazione.

## 6. Permessi

Permessi minimi lato GAIA:

- `presenze.gate.read`;
- `presenze.gate.validate`;
- `presenze.gate.patch`;
- `presenze.gate.resolve_anomaly`;
- `presenze.gate.export.preview`;
- `presenze.gate.export.generate`;
- `presenze.gate.teams.read`;
- `presenze.gate.teams.manage`.

Perimetro dati:

- amministratori HR vedono tutto;
- capi settore vedono i collaboratori delle squadre assegnate;
- operatori vedono i collaboratori delle squadre abilitate;
- il singolo collaboratore non e target primario di GATE, salvo futuro accesso self-service.

## 7. Contratti di sincronizzazione outbound GAIA -> GATE

Il gateway GATE online deve esporre endpoint per il connector GAIA locale. GAIA chiama sempre in outbound: GATE non deve chiamare GAIA LAN.

Endpoint gateway richiesti:

| Metodo | Path | Uso |
| --- | --- | --- |
| `POST` | `/api/mobile/connector/sync/plan` | GATE comunica a GAIA quali snapshot o delta servono |
| `POST` | `/api/mobile/connector/presenze/teams/snapshot` | GAIA invia snapshot completo squadre, membri e responsabili |
| `POST` | `/api/mobile/connector/presenze/months/snapshot` | GAIA invia mesi disponibili e metadata cache |
| `POST` | `/api/mobile/connector/presenze/giornaliere/snapshot` | GAIA invia mese corrente/precedente o delta giornaliere |
| `POST` | `/api/mobile/connector/presenze/anomalie/snapshot` | GAIA invia coda anomalie gia classificata |
| `POST` | `/api/mobile/connector/presenze/rules/snapshot` | GAIA invia regole operative e versioni |
| `GET` | `/api/mobile/connector/presenze/pending-actions` | GAIA legge azioni pendenti prodotte da GATE |
| `POST` | `/api/mobile/connector/presenze/pending-actions/{id}/ack` | GAIA conferma applicazione azione |
| `POST` | `/api/mobile/connector/presenze/pending-actions/{id}/fail` | GAIA rifiuta azione con errore validato |

Capability gia predisposta lato GAIA:

```json
{
  "connector_id": "gaia",
  "capabilities": [
    "operators",
    "presenze_teams",
    "presenze_months",
    "presenze_giornaliere",
    "presenze_anomalie",
    "presenze_rules",
    "presenze_pending_actions"
  ]
}
```

Task atteso dal gateway per chiedere lo snapshot squadre:

```json
{
  "type": "presenze_teams",
  "mode": "full"
}
```

Payload snapshot squadre inviato da GAIA:

```json
{
  "schema_version": 1,
  "source": "gaia",
  "rules_version": "presenze-2026-07-extra-3h",
  "synced_from_gaia_at": "2026-07-09T09:30:00Z",
  "teams": [
    {
      "team_id": "uuid",
      "name": "Squadra Presenze Nord",
      "code": "PNORD",
      "scope": "presenze",
      "active": true,
      "created_from_channel": "gaia",
      "created_by_user_id": 77,
      "audit": {},
      "created_at": "2026-07-09T09:00:00Z",
      "updated_at": "2026-07-09T09:00:00Z",
      "memberships": [
        {
          "membership_id": "uuid",
          "collaborator_id": "uuid",
          "gaia_user_id": "77",
          "employee_code": "P001",
          "collaborator_name": "ROSSI MARIO",
          "role": "member",
          "valid_from": null,
          "valid_to": null,
          "source_channel": "gaia",
          "updated_at": "2026-07-09T09:00:00Z"
        }
      ],
      "supervisors": [
        {
          "supervisor_assignment_id": "uuid",
          "application_user_id": 77,
          "gaia_user_id": "77",
          "username": "caposettore",
          "user_label": "Capo Settore",
          "collaborator_id": "uuid",
          "employee_code": "P001",
          "collaborator_name": "ROSSI MARIO",
          "permission_scope": "validate",
          "valid_from": null,
          "valid_to": null,
          "source_channel": "gaia",
          "updated_at": "2026-07-09T09:00:00Z"
        }
      ]
    }
  ]
}
```

Snapshot rules implementato lato GAIA:

```json
{
  "schema_version": 1,
  "source": "gaia",
  "rules_version": "presenze-2026-07-extra-3h",
  "export_rules_version": "presenze-xlsm-2026-08",
  "synced_from_gaia_at": "2026-07-10T08:00:00Z",
  "rules": {}
}
```

Pending actions implementate lato GAIA:

- `validate_daily_record`;
- `patch_daily_record`;
- `resolve_anomaly`;
- `propose_team_change`, applicata automaticamente da GAIA per creare,
  aggiornare o fare upsert delle squadre operative proposte da GaTe.

GAIA valida:

- utente applicativo attivo;
- abilitazione modulo Presenze;
- perimetro dati via squadre/visibilita esistente;
- payload Pydantic del tipo azione;
- presenza record e stato modificabile.

Per `propose_team_change`, GAIA accetta solo payload `schema_version=1`,
source `gate_admin_console`, `gate_mobile` o `gate`, operazioni `create_team`,
`update_team` e `upsert_team`, scope `presenze`, `gate` o `global`, nomi e
codici nei limiti del modello locale. Le squadre create da GaTe sono persistite
con `created_from_channel="gate_mobile"` e risultano visibili nella pagina
GAIA `/presenze/squadre` dopo la sync successiva.

## 8. Contratto dati giornaliera

Payload minimo per elenco mensile:

```json
{
  "month": "2026-07",
  "rules_version": "presenze-2026-07-extra-3h",
  "export_rules_version": "presenze-xlsm-2026-08",
  "synced_from_gaia_at": "2026-07-08T12:00:00Z",
  "records": [
    {
      "record_id": "uuid",
      "collaborator_id": "uuid",
      "gaia_user_id": "77",
      "collaborator_name": "ROSSI MARIO",
      "team_ids": ["uuid"],
      "work_date": "2026-07-01",
      "weekday": "mercoledi",
      "status": "ok",
      "review_status": "pending",
      "severity": "none",
      "contract_kind": "operaio",
      "schedule_code": "OPE0714_1E3SAB",
      "ordinary_minutes": 390,
      "extra_minutes": 120,
      "export_special_day": false,
      "export_ordinary_minutes": 390,
      "export_extra_minutes": 120,
      "export_ordinary_night_minutes": 0,
      "export_overtime_day_minutes": 120,
      "export_overtime_night_minutes": 0,
      "export_overtime_festive_minutes": 0,
      "export_overtime_festive_night_minutes": 0,
      "export_shift_festive_day_minutes": 0,
      "export_shift_night_minutes": 0,
      "export_shift_festive_night_minutes": 0,
      "export_absence_code": null,
      "justified_minutes": 0,
      "km_value": 24,
      "trasferta_minutes": null,
      "trasferta_montano": false,
      "reperibilita_unit": "none",
      "reperibilita_quantity": null,
      "missing_minutes": 0,
      "absence_cause": null,
      "has_request": false,
      "has_complete_punches": true,
      "validated_at": null,
      "validated_by": null
    }
  ]
}
```

Payload dettaglio giornata:

```json
{
  "record_id": "uuid",
  "rules_version": "presenze-2026-07-extra-3h",
  "collaborator": {
    "id": "uuid",
    "name": "ROSSI MARIO",
    "contract_kind": "operaio",
    "operai_group": "agrario"
  },
  "work_date": "2026-07-01",
  "analysis": {
    "status": "da_verificare",
    "severity": "warning",
    "reasons": ["extra_over_threshold"],
    "operator_message": "Straordinario superiore a 3 ore: verificare autorizzazione."
  },
  "times": {
    "theoretical_minutes": 390,
    "ordinary_minutes": 390,
    "extra_minutes": 190,
    "missing_minutes": 0
  },
  "punches": [
    {
      "time": "06:03:00",
      "direction": "entrata",
      "terminal": "INAZ"
    },
    {
      "time": "17:51:00",
      "direction": "uscita",
      "terminal": "INAZ"
    }
  ],
  "requests": [],
  "notes": [],
  "audit": []
}
```

## 9. Scritture da GATE verso GAIA

Le scritture GATE devono essere intenzionali e auditate.

Operazioni ammesse:

- validare giornata;
- inserire nota operativa;
- correggere campi operativi ammessi, come KM, reperibilita, trasferta, override motivati;
- chiudere anomalia;
- creare o aggiornare squadra;
- assegnare collaboratori a squadra;
- assegnare capi settore/operatori a squadra.

Ogni scrittura deve salvare:

- utente GAIA;
- canale `gate_mobile`;
- timestamp;
- prima/dopo quando applicabile;
- motivazione o nota se richiesta;
- `client_request_id` per idempotenza;
- `rules_version` visualizzata dall'operatore al momento della decisione.

## 10. Export

Decisione operativa:

- GAIA calcola e sincronizza nel payload giornaliera i valori canonici del tracciato HR;
- GATE compila il file `Giornaliere_YYYY_MM.xlsm` a partire dal template HR con macro preservate;
- l'amministratore GATE esporta tutti i collaboratori del mese;
- il capo operaio esporta i membri delle squadre assegnate e anche sé stesso quando il suo utente GAIA e collegato a un `PresenzeCollaborator`;
- i campi legacy non disponibili restano vuoti; `KM` alimenta `KM AUTO`, reperibilita usa `X`, trasferta usa le ore o `X` per comune montano e banca ore resta `0`;
- GATE applica all'export anche l'overlay locale di KM/reperibilita pendenti, cosi una correzione appena inserita e subito visibile senza attendere la sync;
- GATE dichiara e persiste `export_rules_version = presenze-xlsm-2026-08` insieme allo snapshot.

Mitigazione obbligatoria:

- casi campione mensili condivisi;
- test del dataset canonico GAIA e del compilatore XLSM GATE;
- `export_rules_version`;
- blocco dell'export in presenza di giornate `Correggere subito` non risolte.

## 11. Persistenza applicativa GATE

GATE deve mantenere solo:

- mese corrente;
- mese precedente;
- snapshot squadre e assegnazioni necessarie;
- stato di sincronizzazione;
- eventuali code locali di richieste non ancora confermate da GAIA, se serve resilienza mobile.

La persistenza GATE non deve diventare uno storico ufficiale. Storico e audit restano in GAIA.

### 7.1 Pending action `propose_operator_update`

Dal `2026-08-10` GAIA consuma anche pending action create dalla console admin GATE quando vengono creati/modificati operatori o variati domini/permessi console.

Contratto:

- `action_type`: `propose_operator_update`;
- payload in `payload_json`, anche serializzato come stringa JSON;
- `schema_version`: `1`;
- `source`: `gate_admin_console`;
- `operation`: `create_operator`, `update_operator`, `update_operator_domains`;
- `password_changed`: booleano opzionale solo per audit; GATE non invia mai password o hash.

Campi operatore recepiti da GAIA dopo validazione:

- `operator_id`, `display_name`, `email`, `gaia_user_id`, `gaia_operator_profile_id`, `gaia_username`, `phone`, `status`;
- `domains`;
- `gate_mobile_console_enabled`, `gate_mobile_console_role`, `gate_mobile_console_pages`.

GAIA resta master: applica solo proposte coerenti con utenti/profili GAIA esistenti e vincoli di unicita email/username. In caso positivo invia ack con `gaia_entity_type = "wc_operator"`; in caso di payload non valido invia fail con errore chiaro e `retryable = false`. Errori temporanei applicativi o DB producono fail retryable.

### 7.2 Campi operativi giornalieri e rinnovo snapshot

Dal `2026-08-20` ogni record dello snapshot `presenze_giornaliere` include anche
`km_value`, `reperibilita_unit` e `reperibilita_quantity`, mantenendo GAIA come
fonte autorevole dei valori inseriti dall'operatore.

Le giornaliere possono essere rigenerate durante una nuova importazione mensile.
Se una pending action GATE riferisce un `record_id` non piu esistente, GAIA
risolve il record corrente usando la coppia stabile `collaborator_id/work_date`,
applicando poi gli stessi controlli di autorizzazione previsti per un ID ancora
valido. In assenza di questi riferimenti stabili, il record non viene sostituito
e la pending action segue il normale flusso di errore.

## 12. Flusso operativo consigliato

1. GAIA locale esegue il job outbound `gate_mobile_sync`.
2. GAIA chiama `POST /api/mobile/connector/sync/plan` sul gateway GATE online.
3. GATE risponde con i task necessari, ad esempio `presenze_teams`, `presenze_giornaliere`, `presenze_anomalie`.
4. GAIA invia gli snapshot richiesti, inclusi squadre e mese corrente/precedente.
5. GATE aggiorna la cache applicativa e mostra giornaliere/anomalie filtrate per squadra.
6. Operatore o capo settore lavora in GATE; le azioni vengono salvate come `pending-actions` sul gateway.
7. Alla sync successiva GAIA legge le `pending-actions`, valida permessi, regole e stato.
8. GAIA persiste modifiche e audit come source of truth.
9. GAIA invia un nuovo snapshot o ack/fail verso GATE.
10. GATE aggiorna lo stato locale e mostra l'esito all'operatore.
11. Capo settore genera l'XLSM usando dati sincronizzati, overlay locale pendente e `export_rules_version`; l'amministratore usa lo stesso flusso senza filtro squadra.

## 13. Rischi

| Rischio | Impatto | Mitigazione |
| --- | --- | --- |
| Divergenza regole GAIA/GATE | Export o anomalie incoerenti | valori canonici GAIA, `export_rules_version`, test condivisi |
| Doppio stato operativo | Validazioni discordanti | GATE salva solo pending actions; GAIA valida e conferma con ack/snapshot |
| Organigramma locale GATE non allineato | Permessi errati | GAIA source of truth per squadre e assegnazioni |
| Collisione fra ID utente e matricola | Accesso o export di una persona errata | correlazione solo via `gaia_user_id`, record via `collaborator_id`, test fail-closed |
| Operativita offline non gestita | Perdita modifiche | `client_request_id`, pending actions, retry, ack/fail |
| Permessi troppo larghi | Accesso improprio a giornaliere | Perimetro per team e audit |
| Export generato con dati vecchi | File non coerente | snapshot versionato e overlay immediato delle azioni KM/reperibilita pendenti |

## 14. Prompt per team GATE

Implementare in GATE Console Mobile una sezione `Presenze` integrata con GAIA tramite gateway cloud e sync outbound-only da GAIA.

Obiettivo:

- consentire a operatori e capi settore di consultare e validare giornaliere;
- lavorare le anomalie con UX mobile;
- generare export mensili;
- ricevere e mostrare squadre operative sincronizzate da GAIA.

Vincoli:

- GAIA e il source of truth;
- GATE mantiene in persistenza applicativa solo mese corrente e mese precedente;
- GATE non deve chiamare GAIA LAN/intranet;
- GAIA locale chiama in outbound il gateway GATE online;
- ogni scrittura mobile deve diventare una pending action sul gateway;
- ogni modifica operatori/domains/permessi console dalla console admin GATE deve diventare `propose_operator_update`;
- GAIA applica o rifiuta le pending action alla sync successiva;
- dopo ogni ack/snapshot GATE aggiorna lo stato locale;
- audit obbligatorio per validazioni, correzioni, chiusure anomalie e modifiche squadre;
- le regole anomalie devono rispettare la logica GAIA, inclusa soglia extra/straordinario `> 3 ore`;
- gli export GATE devono usare regole identiche a GAIA e dichiarare `export_rules_version`.

Pagine richieste:

- `Giornaliere`: cartellino mensile per collaboratore/squadra;
- `Anomalie`: coda prioritaria, default raggruppata per collaboratore;
- `Export`: preview, controlli bloccanti e generazione;
- `Squadre`: consultazione squadre, membri e responsabili ricevuti da GAIA; eventuali proposte di modifica solo come pending action.
- `Regole`: sezione informativa che spiega anomalie, validazione, audit ed export usando `GET /gate/presenze/rules`.

API gateway da implementare:

- `POST /api/mobile/connector/sync/plan`;
- `POST /api/mobile/connector/presenze/teams/snapshot`;
- `POST /api/mobile/connector/presenze/months/snapshot`;
- `POST /api/mobile/connector/presenze/giornaliere/snapshot`;
- `POST /api/mobile/connector/presenze/anomalie/snapshot`;
- `POST /api/mobile/connector/presenze/rules/snapshot`;
- `GET /api/mobile/connector/presenze/pending-actions`;
- `POST /api/mobile/connector/presenze/pending-actions/{id}/ack`;
- `POST /api/mobile/connector/presenze/pending-actions/{id}/fail`.

UX richiesta:

- mobile first;
- elenco anomalie leggibile da operatore non tecnico;
- linguaggio operativo `Correggere subito` / `Da verificare`;
- dettaglio completo giornata con timbrature, causali, richieste, note e audit;
- azioni rapide ma confermate per validazione e chiusura;
- evidenza se i dati non sono sincronizzati;
- blocco export se esistono anomalie bloccanti non chiuse.

## 15. Prossimi passi GAIA

1. Preparare dataset campione per confronto GAIA/GATE.
2. Valutare se promuovere `organization_teams` a modulo condiviso anche fuori dal dominio presenze.
3. Collegare `POST /gate/presenze/export/generate` al generatore file definitivo se si decide che GAIA deve produrre anche l'artefatto, non solo validare il dataset canonico per GATE.
4. Valutare una tabella audit dedicata se l'audit JSON `_gate_audit` non basta per reporting amministrativo avanzato.
