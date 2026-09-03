# Pending action squadre GATE → GAIA: contratto disallineato

Data: 2026-09-02 · Origine: analisi in produzione dal repo GaTe-mobile · Stato: **da implementare**

## Sintesi

Il write-back delle squadre da GATE a GAIA non ha mai funzionato. Il trasporto è a posto — il worker
`gaia-gate-mobile-sync` (`python -m app.scripts.gate_mobile_sync_runner`) polla il gateway cloud e risponde
`ack`/`fail` — ma **ogni** azione squadra viene rifiutata. Nel database del gateway cloud, al 2026-09-02:

| `action_type` | Stato | Conteggio |
| --- | --- | --- |
| `propose_team_create` | FAILED_FATAL | 8 |
| `propose_team_membership` | FAILED_FATAL | 47 |
| `propose_team_supervisor` | FAILED_FATAL | 42 |
| `propose_team_change` | FAILED_FATAL | 17 |

Errore uniforme: `GAIA_PRESENZE_VALIDATION_ERROR — "application_user_id mancante nella pending action"`.

Conseguenza operativa: le 6 squadre create dalla console GATE non esistono in GAIA, restano
`pending_gaia=true` con `rules_version=gate-local`, e i capi squadra non vedono le giornaliere dei
sottoposti. L'unica squadra sana è quella nata in GAIA.

## I cinque disallineamenti

Le pending action fallirebbero in cascata anche risolvendo solo il primo: vanno chiusi tutti.

### 1. L'attore non viene riconosciuto — `app/services/gate_mobile_sync.py:1105`

```python
def _pending_action_user(db: Session, payload: dict[str, Any]) -> ApplicationUser:
    user_id = payload.get("application_user_id") or payload.get("user_id")
```

GATE ha reso `gaia_user_id` l'unica chiave autorizzativa e **rimuove esplicitamente**
`application_user_id` dal payload (`canonicalPresenzePendingActionPayload`). Il valore trasportato è lo
stesso — `application_users.id` — ma con l'altro nome, e arriva come **stringa numerica** (`"182"`).

Correzione GAIA: accettare `gaia_user_id` nella catena di lookup, incluso il ramo `payload["actor"]`.
`int(user_id)` continua a funzionare sulla stringa.

### 2. Tre tipi di azione su quattro non sono implementati — `app/services/gate_mobile_sync.py:823`

Il dispatch gestisce solo `propose_team_change`; `propose_team_create`, `propose_team_membership` e
`propose_team_supervisor` cadono su `raise ValueError(f"Tipo pending action non supportato: {action_type}")`.

`apply_presenze_team_change_proposal` sa creare e aggiornare una `OrganizationTeam`, ma **non esiste alcun
applier per membership e responsabili**: è la parte di lavoro più consistente e può stare solo in GAIA.

### 3. Il blocco impianti viene rifiutato — `app/modules/presenze/services/gate_mobile_team_actions.py:15`

```python
TEAM_SCOPES = {"presenze", "gate", "global"}
```

Il modello concordato ha due blocchi operativi: agrario (`scope: "presenze"`) e impianti (`scope: "teti"`).
GAIA è master di entrambi — TETI non ha un'anagrafica di squadre propria — quindi `teti` va accettato.
Tre delle sei squadre GATE sono di quel blocco e oggi fallirebbero con
`scope squadra non supportato: teti`.

### 4. L'envelope non combacia — stessa file, `_validate_team_change_envelope`

| Campo | Atteso da GAIA | Inviato da GATE |
| --- | --- | --- |
| `schema_version` | `1` | *assente* |
| `source` | `gate_admin_console` \| `gate_mobile` \| `gate` | *assente* (usa `requested_from: "gate_console_mobile"`) |
| `operation` | `create_team` \| `update_team` \| `upsert_team` | `create_team`, `rename_team`, `update_team_memberships`, `update_team_supervisors` |

Questa parte va corretta **lato GATE** (`buildGateTeam*PendingActionPayload` in
`apps/gateway-api/src/db/sync-event-repository.ts`), oppure GAIA deve accettare i nomi esistenti. Va scelta
una sola direzione: oggi i due lati usano vocabolari diversi per la stessa cosa.

### 5. Payload legacy già in circolo

Le squadre GATE create prima dell'irrigidimento hanno responsabili con `application_user_id` valorizzato
con l'**`operator_id` GATE** (un UUID, non `application_users.id`) e nessun `gaia_user_id`; i membri hanno
solo `collaborator_id` ed `employee_code`. `int(user_id)` su quell'UUID solleverebbe comunque.

GAIA deve rifiutare quei payload in modo esplicito (`fail closed`), non tentare riconciliazioni per nome o
matricola. Il rimedio sta lato GATE: rifare le assegnazioni dal wizard, che accetta solo persone con
`identity_resolution=canonical`.

## Payload realmente inviati da GATE

Costruiti in `apps/gateway-api/src/db/sync-event-repository.ts`; a ognuno viene aggiunto in coda il
`gaia_user_id` dell'autore autenticato.

```jsonc
// propose_team_create
{
  "requested_from": "gate_console_mobile",
  "operation": "create_team",
  "note": "...",
  "team": {
    "team_id": "gate-team-manutenzione-sud-1787899019363",
    "name": "Reparto Sud", "code": "MANUTENZIONE-SUD",
    "scope": "teti", "active": true,
    "created_from_channel": "gate_console_mobile",
    "memberships": [], "supervisors": []
  },
  "gaia_user_id": "182"
}

// propose_team_membership
{
  "requested_from": "gate_console_mobile",
  "operation": "update_team_memberships",
  "note": "...",
  "team": { "team_id": "...", "name": "...", "code": "...", "memberships": [ /* vedi sotto */ ] },
  "previous_memberships": [ /* stato precedente, per audit */ ],
  "requested_memberships": [ /* identico a team.memberships */ ],
  "gaia_user_id": "182"
}

// membership: gaia_user_id e l'unica chiave autorizzativa, il resto e descrittivo
{ "gaia_user_id": "67", "collaborator_id": "6e1f0fa9-...", "employee_code": "1394",
  "collaborator_name": "CORONA DAVIDE", "role": "member" }

// propose_team_supervisor: identico con operation "update_team_supervisors",
// team.supervisors / previous_supervisors / requested_supervisors
{ "gaia_user_id": "182", "username": "pau.mauro", "user_label": "Mauro Pau",
  "permission_scope": "team" }
```

Semantica attesa da GATE: `update_team_memberships` e `update_team_supervisors` sono **sostituzioni
integrali** dell'elenco, non delta. `previous_*` serve solo all'audit.

## Regola di identità, non negoziabile

`gaia_user_id` = `application_users.id` = `supervisor.application_user_id`: stesso valore, nomi diversi ai
due lati del confine. Non sono chiavi Presenze. Nome, username, email, matricola, `collaborator_id`,
`employee_code` e `operator_id` sono metadati descrittivi e **non** devono mai partecipare alla risoluzione
della persona: se `gaia_user_id` manca, è ambiguo o non risolve a un `ApplicationUser` attivo, l'azione va
respinta con `fail` di validazione. Il riferimento canonico è
`GaTe-mobile/docs/PRESENZE_IDENTITY_RELATIONSHIPS.md`.

## Ordine di lavoro suggerito

1. GAIA: accettare `gaia_user_id` in `_pending_action_user` — sblocca la diagnosi, le azioni iniziano a
   fallire con l'errore *vero* invece che sull'attore.
2. GATE **o** GAIA: allineare envelope e vocabolario delle `operation` (punto 4). Decidere la direzione.
3. GAIA: aggiungere `teti` a `TEAM_SCOPES`.
4. GAIA: implementare gli applier di membership e responsabili e collegarli al dispatch.
5. Verifica end-to-end: ricreare le assegnazioni di «Reparto Sud» dalla console GATE e controllare che
   `presenze_pending_action` vada in `ACKED` e che la squadra compaia in
   `GET /api/mobile-sync/presenze/teams` con supervisor `gaia_user_id: "182"`.

## Come diagnosticare

```bash
# stato delle azioni sul gateway cloud
ssh gate "docker exec gate-mobile-postgres-1 psql -U gate_mobile -d gate_mobile \
  -c \"select action_type, status, error_message, count(*) from presenze_pending_action \
       group by 1,2,3 order by 1\""

# log del worker GAIA
ssh serverCed 'docker logs --since 10m gaia-gate-mobile-sync'
```
