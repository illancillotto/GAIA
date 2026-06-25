# Presenze Phase C Checklist

Ultimo aggiornamento: `2026-06-25`

## Obiettivo

Completare la migrazione tecnica pubblica da `Inaz` a `Presenze`, superando il solo layer di compatibilita frontend.

Questa fase inizia solo dopo la stabilizzazione funzionale del dominio `Presenze`.

## Stato di partenza

Gia fatto:

- superfici utente principali rinominate in `Giornaliere`
- layer frontend compatibile `Presenze*` introdotto
- pagine frontend del modulo migrate al layer `Presenze*`
- route frontend canoniche `/presenze/...` introdotte
- endpoint backend `/presenze/...` e `/me/presenze/...` introdotti come alias pubblici

Ancora legacy:

- route pubbliche `/inaz/...`
- namespace app `frontend/src/app/inaz`
- flag e capability come `module_inaz`
- endpoint backend pubblici `/inaz/...`
- tipi legacy `Inaz*` ancora presenti come base canonica
- modelli e tabelle `inaz_*`
- migration history Alembic centrata su `inaz_*`

## Decisione preliminare obbligatoria

Prima di partire va scelta una delle due strategie:

### Strategia A

- mantenere `/inaz` come alias permanente
- introdurre `/presenze` come route primaria
- mantenere un periodo lungo di doppio supporto

### Strategia B

- introdurre `/presenze`
- deprecare `/inaz`
- rimuovere il legacy in una release successiva pianificata

Raccomandazione:

- usare `Strategia A` come step iniziale
- decidere l'eventuale rimozione di `/inaz` solo dopo una release stabile

Decisione raccomandata formalizzata:

- vedi [docs/PRESENZE_PHASE_C_DECISION.md](/home/cbo/CursorProjects/GAIA/docs/PRESENZE_PHASE_C_DECISION.md:1)

## Blocco C1: Route Pubbliche

### Obiettivo

Esporre il dominio pubblico come `/presenze/...` senza rompere gli URL esistenti.

### Checklist

- creare route frontend `/presenze`
- decidere se usare:
  - alias router
  - redirect
  - doppio mount
- garantire equivalenza completa tra:
  - `/inaz`
  - `/presenze`
- aggiornare link interni di navigazione primaria
- aggiornare breadcrumb e deep-link condivisibili
- aggiornare documentazione utente che cita `/inaz/...`

Stato:

- `completato` nella prima ondata

### Gate

- tutte le viste principali apribili sia da `/inaz/...` sia da `/presenze/...`
- nessun deep link storico rotto

## Blocco C2: Client API Frontend

### Obiettivo

Fare di `Presenze*` il naming canonico lato frontend, lasciando `Inaz*` solo come alias di compatibilita.

### Checklist

- invertire la direzione degli alias in [frontend/src/types/api.ts](/home/cbo/CursorProjects/GAIA/frontend/src/types/api.ts:1):
  - `Presenze*` diventa canonico
  - `Inaz*` diventa alias legacy
- invertire la direzione degli alias in [frontend/src/lib/api.ts](/home/cbo/CursorProjects/GAIA/frontend/src/lib/api.ts:1)
- verificare che nuovi componenti importino solo `Presenze*`
- introdurre lint/search check per evitare nuove dipendenze su `Inaz*`
- aggiornare helper residuali ancora centrati sul naming legacy

### Gate

- nessuna pagina operativa dipende da tipi canonici `Inaz*`
- nuovi sviluppi bloccati se introducono nuovo naming legacy

## Blocco C3: API Backend Pubbliche

### Obiettivo

Esporre endpoint `/presenze/...` compatibili con gli attuali `/inaz/...`.

### Checklist

- introdurre router backend `/presenze`
- mantenere `/inaz` come alias compatibile in prima fase
- decidere se:
  - duplicare mount FastAPI
  - oppure rifattorizzare router comune con doppio prefisso
- aggiornare OpenAPI/tag/descrizioni
- aggiornare test API sui nuovi endpoint pubblici
- verificare policy CORS, auth e permessi sui nuovi path

Stato:

- `completato` nella prima ondata
- helper alias FastAPI attivo per `/presenze/...` e `/me/presenze/...`
- test di compatibilita aggiunti

### Gate

- smoke test backend sia su `/inaz/...` sia su `/presenze/...`
- nessuna regressione sui client esistenti

## Blocco C4: Permessi e Sezioni

### Obiettivo

Capire se `module_inaz` va mantenuto come chiave storica o se va introdotto `module_presenze`.

### Checklist

- censire uso di `module_inaz` in:
  - tipi frontend
  - permessi backend
  - bootstrap sezioni
  - wiki/context hints
- decidere una strategia:
  - mantenere `module_inaz` stabile e cambiare solo etichette
  - introdurre `module_presenze` con supporto doppio
- se si introduce `module_presenze`:
  - aggiungere migrazione dati
  - aggiornare controllo accessi
  - aggiornare bootstrap e test

Stato:

- `rimandato`
- `module_inaz` resta invariato nella prima ondata

### Gate

- nessuna perdita di accesso utenti
- capability e ACL coerenti dopo il deploy

## Blocco C5: Modelli e Tabelle DB

### Obiettivo

Valutare se il rename deve arrivare fino a modelli ORM e tabelle `inaz_*`.

### Checklist

- censire tabelle `inaz_*`
- stimare costo reale di rename su:
  - ORM
  - foreign key
  - indici
  - migration Alembic
  - script export/import
  - test
- decidere se fermarsi a:
  - route/API/domain rename
  - senza rename fisico DB
- se si procede:
  - preparare migrazioni reversibili
  - predisporre doppia compatibilita applicativa durante rollout

Stato:

- `rimandato`
- nessun rename DB nella prima ondata

### Raccomandazione

- non rinominare subito le tabelle se il beneficio e solo estetico
- toccare il DB solo se porta un vantaggio chiaro di manutenzione o onboarding

### Gate

- migrazione reversibile
- zero perdita dati
- piano rollback testato

## Blocco C6: Documentazione e Wiki

### Obiettivo

Rendere coerente la documentazione tecnica e operativa col nuovo dominio pubblico.

### Checklist

- aggiornare docs architetturali che descrivono `/inaz/...`
- aggiornare wiki hints e support routing
- aggiornare Graphify docs del dominio
- aggiornare runbook e documenti di supporto operatori

Stato:

- `in corso`
- documentazione locale aggiornata
- refresh Graphify da riallineare sul corpus docs se disponibile la pipeline LLM

### Gate

- documentazione tecnica coerente con il dominio esposto
- routing wiki aggiornato sui path `presenze`

## Blocco C7: Rollout

### Obiettivo

Deployare senza interrompere utenti, link, integrazioni o workflow interni.

### Checklist

- rilasciare backend con doppio supporto `/inaz` + `/presenze`
- rilasciare frontend che preferisce `/presenze`
- monitorare accessi a `/inaz`
- mantenere redirect o alias per una finestra definita
- raccogliere regressioni reali da operatori e HR

### Gate

- monitoraggio errori e accessi disponibile
- nessun blocco operativo su export, sync, banca ore, giornaliere

## Blocco C8: Rimozione Legacy

### Obiettivo

Rimuovere il naming `Inaz` solo quando non e piu necessario come compatibilita.

### Checklist

- misurare uso residuo di `/inaz`
- verificare assenza di integrazioni esterne dipendenti dai path legacy
- rimuovere alias `Inaz*` solo dopo finestra di stabilizzazione
- eliminare route legacy e documentazione deprecata

### Gate

- zero dipendenze attive sul legacy
- release note chiare
- rollback ancora praticabile fino all'ultima release compatibile

## Stima realistica

### Scenario minimo

- doppio supporto route/API senza rename DB
- effort: `4-6` giorni netti

### Scenario completo

- doppio supporto + eventuale rename capability/DB
- effort: `8-12` giorni netti

## Ordine consigliato

1. decidere strategia alias `/inaz` vs `/presenze`
2. chiudere route e API pubbliche
3. rendere `Presenze*` canonico nel client
4. decidere se toccare davvero `module_inaz`
5. decidere se evitare il rename DB
6. rollout controllato
7. rimozione legacy solo dopo stabilizzazione

## No-Go attuali

Non partire con la Fase C se prima non sono stabili:

- banca ore
- regole CCNL principali
- export HR
- perimetro test backend/frontend del modulo
