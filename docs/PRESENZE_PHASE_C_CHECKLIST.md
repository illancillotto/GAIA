# Presenze Phase C Checklist

Ultimo aggiornamento: `2026-06-25`

## Obiettivo

Completare la migrazione tecnica pubblica dal naming legacy a `Presenze`, superando il solo layer di compatibilita frontend.

Questa fase inizia solo dopo la stabilizzazione funzionale del dominio `Presenze`.

## Stato di partenza

Gia fatto:

- superfici utente principali rinominate in `Giornaliere`
- layer frontend compatibile `Presenze*` introdotto
- pagine frontend del modulo migrate al layer `Presenze*`
- route frontend canoniche `/presenze/...` introdotte
- endpoint backend `/presenze/...` e `/me/presenze/...` introdotti come alias pubblici

Residuo legacy reale:

- tabelle fisiche `inaz_*`
- migration history Alembic centrata su `inaz_*`
- path canonico del repository esterno `presenze-scraper`
- documentazione storica e memo di analisi che parlano della fase `Inaz`

## Decisione preliminare obbligatoria

Prima di partire va scelta una delle due strategie:

### Strategia A

- mantenere alias pubblici legacy in modo permanente
- introdurre `/presenze` come route primaria
- mantenere un periodo lungo di doppio supporto

### Strategia B

- introdurre `/presenze`
- deprecare gli alias pubblici legacy
- rimuovere il legacy in una release successiva pianificata

Raccomandazione:

- la strategia iniziale e stata eseguita
- il tema residuo non e piu il routing pubblico ma il rename dello storage fisico

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
  - namespace legacy
  - `/presenze`
- aggiornare link interni di navigazione primaria
- aggiornare breadcrumb e deep-link condivisibili
- aggiornare documentazione utente che cita il namespace legacy

Stato:

- `completato` nella prima ondata

### Gate

- tutte le viste principali apribili dal namespace canonico `/presenze/...`
- nessun deep link utente residuo nel client canonico

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

Esporre endpoint `/presenze/...` compatibili con il namespace storico del modulo.

### Checklist

- introdurre router backend `/presenze`
- mantenere alias compatibile in prima fase
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
- wiring backend core spostato sul namespace canonico `app.modules.presenze.*`
- tag OpenAPI del router canonico aggiornato a `presenze`
- namespace canonico esteso anche ai `services/*` backend e al launcher del worker sync
- frontend runtime allineato al namespace canonico `presenze`
- package fisico backend invertito: `modules/presenze` sorgente reale
- alias pubblici legacy rimossi
- layer route frontend legacy rimosso

### Gate

- smoke test backend sul namespace canonico `/presenze/...`
- nessuna regressione sui client esistenti

## Blocco C4: Permessi e Sezioni

### Obiettivo

Capire se il flag storico del modulo vada mantenuto o se il naming canonico sia sufficiente.

### Checklist

- censire uso del flag legacy in:
  - tipi frontend
  - permessi backend
  - bootstrap sezioni
  - wiki/context hints
- decidere una strategia:
  - mantenere il flag legacy stabile e cambiare solo etichette
  - introdurre `module_presenze` con supporto doppio
- se si introduce `module_presenze`:
  - aggiungere migrazione dati
  - aggiornare controllo accessi
  - aggiornare bootstrap e test

Stato:

- `parzialmente completato`
- runtime canonico usa `module_presenze` come chiave esposta nei payload principali
- il runtime applicativo usa `module_presenze`; la migration della colonna utenti e gia stata introdotta
- il frontend non dipende piu dal flag legacy per il gating runtime
- il backend non usa piu il flag legacy come attributo primario del modello
- i payload canonici non espongono piu il flag legacy
- la configurazione runtime del dominio usa ora solo nomi canonici `presenze_*`
- i test unitari frontend principali non richiedono piu il flag legacy nei payload canonici utente
- la documentazione architetturale operativa usa ora `/presenze/...` come percorso corrente del modulo
- il layer frontend `@/lib/api` e `@/types/api` non espone piu alias runtime/type `Inaz*` per il dominio presenze

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

- aggiornare docs architetturali che descrivono il namespace legacy del modulo
- aggiornare wiki hints e support routing
- aggiornare Graphify docs del dominio
- aggiornare runbook e documenti di supporto operatori

Stato:

- `in corso`
- documentazione locale aggiornata in buona parte
- Graphify code e docs del dominio gia riallineati sul corpus `presenze`
- resta da pulire la documentazione storica che mescola stato attuale e decisioni passate

### Gate

- documentazione tecnica coerente con il dominio esposto
- routing wiki aggiornato sui path `presenze`

## Blocco C7: Rollout

### Obiettivo

Deployare senza interrompere utenti, link, integrazioni o workflow interni.

### Checklist

- rilasciare backend e frontend sul namespace canonico `/presenze`
- monitorare errori e regressioni sul modulo
- trattare separatamente eventuali consumer esterni storici
- raccogliere regressioni reali da operatori e HR

### Gate

- monitoraggio errori e accessi disponibile
- nessun blocco operativo su export, sync, banca ore, giornaliere

## Blocco C8: Rimozione Legacy

### Obiettivo

Rimuovere il naming `Inaz` solo quando non e piu necessario come compatibilita.

### Checklist

- decidere se rinominare le tabelle `inaz_*`
- verificare impatto di un eventuale rename del repository esterno
- mantenere solo documentazione storica strettamente necessaria
- eliminare i residui documentali non piu utili

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

1. chiudere la pulizia documentale
2. validare deploy e smoke del namespace canonico
3. decidere se toccare davvero il DB fisico `inaz_*`
4. decidere se rinominare il repository esterno

## No-Go attuali

Non partire con la Fase C se prima non sono stabili:

- banca ore
- regole CCNL principali
- export HR
- perimetro test backend/frontend del modulo
