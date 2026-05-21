# Prompt GAIA - Endpoint TETI Fault Work Requests

Usa questo prompt nel repository **GAIA** per implementare l'endpoint richiesto dal connector GAIA Mobile.

```text
Implementa l'endpoint GAIA per ricevere dal connector GAIA Mobile una anomalia TETI e creare/recuperare un intervento GAIA in modo idempotente.

Endpoint richiesto:

POST /api/mobile-sync/teti/fault-work-requests

Header atteso:

X-GAIA-Connector-Token: <token connector>

Payload:

{
  "cloud_event_id": "uuid",
  "client_event_id": "uuid",
  "operator_id": "uuid",
  "device_id": "uuid",
  "payload_version": 1,
  "payload_hash": "sha256",
  "teti_fault_id": "string",
  "payload": {
    "plantId": "uuid",
    "assetId": "uuid opzionale",
    "title": "string",
    "description": "string",
    "severity": "LOW|MEDIUM|HIGH|CRITICAL",
    "latitude": "number opzionale",
    "longitude": "number opzionale"
  },
  "attachments": []
}

Requisiti:

- Non riscrivere parti esistenti di GAIA.
- Usa pattern, middleware auth, routing, logging e validazione gia presenti nel repo GAIA.
- L'endpoint deve essere accessibile solo al connector mobile-sync.
- Verifica il token X-GAIA-Connector-Token secondo la logica gia usata dagli altri endpoint /api/mobile-sync/*.
- Implementa idempotenza su client_event_id o su teti_fault_id se esiste gia un mapping piu adatto.
- Se arriva due volte lo stesso evento con stesso client_event_id, restituisci lo stesso intervento GAIA gia creato.
- Se arriva stesso client_event_id con payload/hash incompatibile, restituisci errore 409.
- Crea un intervento/lavorazione GAIA partendo dai dati TETI:
  - titolo da payload.title;
  - descrizione da payload.description;
  - priorita/severita mappata da payload.severity;
  - riferimento esterno a teti_fault_id;
  - eventuale posizione GPS;
  - eventuale asset/impianto come riferimento esterno se non esiste modello GAIA dedicato.
- Se non e ancora chiaro il mapping definitivo su tabelle GAIA, crea una implementazione conservativa usando il modello intervento piu vicino gia esistente e documenta le assunzioni.
- Registra audit/log dell'operazione.
- Non implementare ancora chiamate verso TETI.
- Non cambiare il contratto del connector GAIA Mobile.

Risposta attesa in caso successo:

{
  "gaia_entity_type": "gaia_work",
  "gaia_entity_id": "<id intervento GAIA>",
  "extra": {
    "status": "created|already_exists",
    "teti_fault_id": "<teti_fault_id>"
  }
}

Risposta errore coerente con il connector GAIA Mobile:

{
  "error_code": "GAIA_VALIDATION_ERROR | GAIA_RETRYABLE_ERROR | GAIA_CONFLICT",
  "message": "string",
  "retryable": true|false,
  "details": {}
}

Aggiungi o aggiorna test automatici per:

- richiesta senza token: non autorizzata;
- payload valido: crea intervento;
- reinvio stesso client_event_id: ritorna stesso intervento;
- stesso client_event_id con payload/hash diverso: 409;
- errore validazione payload: errore non retryable;
- eventuale errore temporaneo DB: retryable se il pattern del progetto lo prevede.

Aggiorna la documentazione interna GAIA relativa agli endpoint /api/mobile-sync/*.

Alla fine esegui i comandi di verifica disponibili nel repo GAIA, ad esempio:

npm install
npm run typecheck
npm run test
npm run build

oppure gli equivalenti reali del progetto.

Produci un riepilogo finale con:

- file modificati;
- endpoint aggiunto;
- mapping campi TETI -> GAIA applicato;
- test eseguiti;
- problemi o decisioni architetturali rimaste.
```
