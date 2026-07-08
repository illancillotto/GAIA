# Blueprint integrazione GAIA / GATE Console Mobile - Presenze

Data: 2026-07-08

Stato implementazione GAIA:

- implementato il primo blocco backend per squadre operative GATE;
- aggiunte tabelle `organization_teams`, `organization_team_memberships`, `organization_team_supervisor_assignments`;
- aggiunti endpoint `/gate/presenze/teams`, `/gate/presenze/teams/{team_id}`, `/gate/presenze/teams/{team_id}/memberships`, `/gate/presenze/teams/{team_id}/supervisors`;
- aggiunti endpoint `/gate/presenze/months/available`, `/gate/presenze/giornaliere`, `/gate/presenze/giornaliere/{record_id}`, `/gate/presenze/giornaliere/{record_id}/validate`, `/gate/presenze/giornaliere/{record_id}/patch`, `/gate/presenze/anomalie`, `/gate/presenze/anomalie/{record_id}/resolve`, `/gate/presenze/export/preview`, `/gate/presenze/export/generate`;
- aggiunto endpoint `/gate/presenze/rules` come fonte unica per mostrare in GAIA e GATE le regole operative del sistema;
- aggiunta pagina GAIA `/presenze/squadre` per creare squadre, aggiungere collaboratori e assegnare responsabili usando le API `/gate/presenze/teams`;
- aggiunta pagina GAIA `/presenze/regole`, collegata alla sidebar Presenze, che consuma lo stesso contratto usato da GATE;
- aggiunti permessi bootstrap `presenze.gate.*`;
- copertura test del router `app.modules.presenze.gate_router`: `100%`.

## 1. Decisione architetturale

GAIA resta il sistema autorevole del dominio `presenze`.

GATE Console Mobile diventa il workspace operativo per operatori e capi settore, con persistenza applicativa locale limitata a mese corrente e mese precedente. Le modifiche fatte in GATE non devono creare un secondo stato ufficiale: ogni validazione, correzione o nota deve essere scritta su GAIA tramite API dedicate e poi riletta da GAIA.

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

### GATE Console Mobile

GATE e responsabile di:

- esperienza operativa mobile;
- consultazione rapida di giornaliere, anomalie ed export;
- cache applicativa di mese corrente e mese precedente;
- lavorazione da parte di operatori e capi settore;
- generazione export lato GATE quando richiesta dal flusso operativo;
- creazione e manutenzione operativa di squadre, da sincronizzare con GAIA.

GATE puo duplicare temporaneamente parte della logica di export per immediatezza operativa, ma deve dichiarare la versione delle regole usate e deve rimanere allineato ai casi campione GAIA.

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
| `valid_from`, `valid_to` | Validita temporale |
| `role` | `member`, `lead`, `substitute` |
| `source_channel` | `gaia_web` o `gate_mobile` |

Campi minimi `organization_team_supervisor_assignments`:

| Campo | Note |
| --- | --- |
| `id` | Identificativo assegnazione |
| `team_id` | Squadra |
| `application_user_id` | Capo settore / operatore abilitato |
| `permission_scope` | `view`, `validate`, `export`, `manage_team` |
| `valid_from`, `valid_to` | Validita temporale |

Regola consigliata:

- un collaboratore dovrebbe avere una sola assegnazione attiva principale nello stesso periodo;
- eventuali eccezioni devono essere esplicite tramite ruolo o flag dedicato;
- GATE puo proporre squadre e assegnazioni, ma GAIA deve validarle e persisterle.

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

## 7. API dedicate GATE

Le API dedicate devono essere stabili, aggregate e pensate per consumo mobile. Non devono obbligare GATE a ricostruire il dominio da endpoint granulari pensati per GAIA web.

Endpoint proposti:

| Metodo | Path | Uso |
| --- | --- | --- |
| `GET` | `/gate/presenze/months/available` | Mesi disponibili per cache GATE |
| `GET` | `/gate/presenze/giornaliere?month=YYYY-MM` | Cartellino mensile per perimetro utente |
| `GET` | `/gate/presenze/giornaliere/{record_id}` | Dettaglio completo giornata |
| `POST` | `/gate/presenze/giornaliere/{record_id}/validate` | Validazione giornata |
| `POST` | `/gate/presenze/giornaliere/{record_id}/patch` | Correzioni operative ammesse |
| `GET` | `/gate/presenze/anomalie?month=YYYY-MM` | Coda anomalie gia classificata |
| `POST` | `/gate/presenze/anomalie/{record_id}/resolve` | Chiusura anomalia |
| `GET` | `/gate/presenze/export/preview?month=YYYY-MM` | Preview export |
| `POST` | `/gate/presenze/export/generate` | Generazione export lato GAIA o richiesta dati per GATE |
| `GET` | `/gate/presenze/teams` | Squadre visibili |
| `POST` | `/gate/presenze/teams` | Creazione squadra |
| `PUT` | `/gate/presenze/teams/{team_id}` | Aggiornamento squadra |
| `POST` | `/gate/presenze/teams/{team_id}/memberships` | Assegnazione collaboratore |
| `POST` | `/gate/presenze/teams/{team_id}/supervisors` | Assegnazione capo settore / operatore |

## 8. Contratto dati giornaliera

Payload minimo per elenco mensile:

```json
{
  "month": "2026-07",
  "rules_version": "presenze-2026-07-extra-3h",
  "generated_at": "2026-07-08T12:00:00Z",
  "records": [
    {
      "record_id": "uuid",
      "collaborator_id": "uuid",
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

- GATE genera l'export per renderlo immediatamente fruibile;
- la logica deve essere identica a GAIA;
- GAIA deve esporre preview e dataset canonico per ridurre divergenze;
- GATE deve dichiarare nel file o nei metadati la versione export usata.

Rischio accettato:

- codice duplicato in due sistemi.

Mitigazione obbligatoria:

- casi campione mensili condivisi;
- test di confronto tra export GAIA e export GATE;
- `export_rules_version`;
- fallback a export GAIA in caso di mismatch bloccante.

## 11. Persistenza applicativa GATE

GATE deve mantenere solo:

- mese corrente;
- mese precedente;
- snapshot squadre e assegnazioni necessarie;
- stato di sincronizzazione;
- eventuali code locali di richieste non ancora confermate da GAIA, se serve resilienza mobile.

La persistenza GATE non deve diventare uno storico ufficiale. Storico e audit restano in GAIA.

## 12. Flusso operativo consigliato

1. GATE chiama `GET /gate/presenze/months/available`.
2. GATE sincronizza mese corrente e mese precedente.
3. Operatore apre `Anomalie`.
4. GATE mostra casi raggruppati per collaboratore e filtrati per squadra.
5. Operatore apre dettaglio giornata.
6. Operatore valida, corregge o chiude anomalia.
7. GATE scrive su GAIA con `client_request_id`.
8. GAIA valida permessi, regole e stato.
9. GAIA persiste modifica e audit.
10. GATE rilegge record aggiornato da GAIA.
11. Capo settore genera o scarica export.

## 13. Rischi

| Rischio | Impatto | Mitigazione |
| --- | --- | --- |
| Divergenza regole GAIA/GATE | Export o anomalie incoerenti | `rules_version`, test condivisi, dataset canonico |
| Doppio stato operativo | Validazioni discordanti | Scrittura diretta su GAIA e rilettura post-write |
| Organigramma locale GATE non allineato | Permessi errati | GAIA source of truth per squadre e assegnazioni |
| Operativita offline non gestita | Perdita modifiche | `client_request_id`, retry, stato sync |
| Permessi troppo larghi | Accesso improprio a giornaliere | Perimetro per team e audit |
| Export generato con dati vecchi | File non coerente | sync obbligatoria prima della generazione |

## 14. Prompt per team GATE

Implementare in GATE Console Mobile una sezione `Presenze` integrata con GAIA.

Obiettivo:

- consentire a operatori e capi settore di consultare e validare giornaliere;
- lavorare le anomalie con UX mobile;
- generare export mensili;
- gestire squadre operative sincronizzate con GAIA.

Vincoli:

- GAIA e il source of truth;
- GATE mantiene in persistenza applicativa solo mese corrente e mese precedente;
- ogni scrittura deve andare direttamente su GAIA tramite API dedicate;
- dopo ogni scrittura GATE deve rileggere lo stato da GAIA;
- audit obbligatorio per validazioni, correzioni, chiusure anomalie e modifiche squadre;
- le regole anomalie devono rispettare la logica GAIA, inclusa soglia extra/straordinario `> 3 ore`;
- gli export GATE devono usare regole identiche a GAIA e dichiarare `export_rules_version`.

Pagine richieste:

- `Giornaliere`: cartellino mensile per collaboratore/squadra;
- `Anomalie`: coda prioritaria, default raggruppata per collaboratore;
- `Export`: preview, controlli bloccanti e generazione;
- `Squadre`: creazione squadre, membri e assegnazione capi settore/operatori.
- `Regole`: sezione informativa che spiega anomalie, validazione, audit ed export usando `GET /gate/presenze/rules`.

API da consumare:

- `GET /gate/presenze/months/available`;
- `GET /gate/presenze/rules`;
- `GET /gate/presenze/giornaliere?month=YYYY-MM`;
- `GET /gate/presenze/giornaliere/{record_id}`;
- `POST /gate/presenze/giornaliere/{record_id}/validate`;
- `POST /gate/presenze/giornaliere/{record_id}/patch`;
- `GET /gate/presenze/anomalie?month=YYYY-MM`;
- `POST /gate/presenze/anomalie/{record_id}/resolve`;
- `GET /gate/presenze/export/preview?month=YYYY-MM`;
- `POST /gate/presenze/export/generate`;
- `GET/POST/PUT /gate/presenze/teams`;
- `POST /gate/presenze/teams/{team_id}/memberships`;
- `POST /gate/presenze/teams/{team_id}/supervisors`.

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
