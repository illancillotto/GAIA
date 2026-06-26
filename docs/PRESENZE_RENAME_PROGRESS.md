# Presenze Rename Progress

Ultimo aggiornamento: `2026-06-25`

## Obiettivo

Sostituire progressivamente il termine `Inaz` con un naming di dominio coerente per il prodotto.

Nome target lato utente:

- `Presenze` come nome funzionale del dominio
- `Giornaliere` come etichetta operativa dove il contesto e la pagina sono centrati sul cartellino giornaliero

Vincolo attuale:

- il namespace tecnico `inaz` resta ancora presente solo in artefatti storici, migration history e naming di alcune tabelle legacy

## Stato generale

Stato programma: `in corso`

Fase corrente: `Fase C - consolidamento finale e pulizia residui`

Completamento stimato Fase A: `100%`

## Completato

- Sidebar piattaforma:
  - modulo `Presenze` esposto all'utente come `Giornaliere`
- Titoli, breadcrumb e label principali del modulo:
  - dashboard
  - giornaliere
  - banca ore
  - export
  - sync
  - anomalie
  - collaboratori
  - dettaglio collaboratore
  - configurazione
  - festivita
  - recuperi
  - organigramma
- Testi operativi principali:
  - badge modulo
  - CTA di navigazione
  - messaggi di empty state principali
  - parte dei messaggi di errore e conferma
- Sezione utenti GAIA:
  - modulo `Inaz` rinominato in `Giornaliere` nelle label utente
- Cruscotto operatori:
  - riepilogo e metriche esposte come `giornaliere`
- Wiki context hints:
  - dominio `presenze` etichettato come `Giornaliere`
  - pagina banca ore etichettata come `Banca ore`
- Bootstrap sezioni backend:
  - label sezione aggiornate da `Inaz - ...` a `Giornaliere - ...`
- Graphify:
  - sorgente codice aggiornata con `make graphify-presenze-code`
  - target `graphify-inaz-*` mantenuti solo come alias legacy
- Backend canonico:
  - namespace `app.modules.presenze.*` introdotto come sorgente tecnica primaria per il wiring core
  - `api_router`, `main`, `db/base` e self-service `/me` migrati al namespace canonico
  - tag OpenAPI del router canonico aggiornato a `presenze`
  - mirror canonico esteso anche a `services/*`, scheduler e router helper del dominio
  - worker sync lanciato ora con `python -m app.modules.presenze.services.sync_worker`
  - script di verifica export rinominato in `verify_presenze_giornaliere_export.py` con wrapper legacy `verify_inaz_giornaliere_export.py`
  - payload `/me` ripulito: il contratto canonico non pubblica piu le chiavi legacy del modulo
  - package fisico backend ribaltato: `backend/app/modules/presenze/*` e ora la sorgente reale del dominio
  - flag runtime ribaltato: il modello applicativo usa ora `module_presenze` come attributo canonico anche a livello storage
  - contratti canonici backend/frontend ripuliti: il flag legacy non e piu pubblicato nei payload utente canonici ne nei tipi TS principali
  - alias pubblici rimossi: backend non espone piu il namespace legacy del modulo
  - layer frontend legacy eliminato: le route frontend legacy del modulo sono state rimosse dal repository

## In corso

- Preparazione del backlog tecnico per gli alias `Presenze`
- Separazione tra naming utente e naming tecnico legacy
- Chiusura quasi completa del layer compatibile:
  - nessun import applicativo residuo al package legacy del modulo
  - `backend/app/modules/presenze/*` e la sorgente reale del dominio
  - il package fisico legacy backend e stato dismesso
  - `models.py` e `schemas.py` espongono naming canonico `Presenze*`; la compatibilita `Inaz*` resta solo via bridge dinamico mirato
  - `backend/app/modules/me/*` usa tipi canonici `Presenze*`
  - la configurazione runtime accetta solo chiavi `PRESENZE_*`
  - l'artifact di sync usa `presenze_collaboratori.json`
  - la colonna utenti e stata rinominata via Alembic da `module_inaz` a `module_presenze`
  - la suite backend del dominio e stata rinominata al prefisso `test_presenze_*`
  - il corpus documentale del modulo e stato spostato nel namespace `domain-docs/presenze`
- Alias pubblici rimossi dal runtime:
  - nessun path applicativo residuo del namespace legacy
- restano solo riferimenti esterni/storici alla migration history e a documenti di analisi
- Layer frontend compatibile quasi esaurito:
  - il runtime canonico non usa piu alias legacy in sidebar, shell, self-service e support payload
  - il layer route frontend legacy e stato rimosso dal repository
  - fixture e test unitari frontend principali non dipendono piu dal campo legacy nei payload canonici utente
  - copy e descrizioni frontend di test sono state riallineate a `Presenze`
  - il client frontend non esporta piu wrapper runtime `Inaz*` da `frontend/src/lib/api.ts` ne wrapper `inaz-*` da `frontend/src/lib/*`
  - `frontend/src/types/api.ts` non mantiene piu type alias `Inaz*` per il dominio presenze
- Documentazione fattuale riallineata:
  - [docs/ARCHITECTURE.md](/home/cbo/CursorProjects/GAIA/docs/ARCHITECTURE.md:1) descrive ora il modulo `/presenze` come superficie attiva
  - [docs/IMPLEMENTATION_PLAN.md](/home/cbo/CursorProjects/GAIA/docs/IMPLEMENTATION_PLAN.md:1) non descrive piu il namespace legacy come percorso applicativo corrente
- Prime adozioni applicative completate:
  - dashboard modulo
  - export modulo
  - sync modulo
  - collaboratori modulo
  - festivita modulo
  - settings modulo
  - anomalie modulo
  - recuperi modulo
  - banca ore modulo
  - giornaliere modulo
  - dettaglio collaboratore modulo
  - configurazione modulo

## Residuo noto della Fase A

- la Fase A e considerata chiusa sul perimetro utente principale
- il nome tecnico `inaz` resta intenzionalmente presente in:
  - modelli e tabelle `inaz_*`
  - migration history e storage legacy gia versionati

## Verifiche eseguite

- smoke test frontend locale: `18/18` verdi
- ricerca mirata delle etichette utente residue con `rg`
- controllo mirato: nel perimetro principale non risultano piu titoli o breadcrumb utente con `Inaz`
- review finale del perimetro Fase A completata prima del commit dedicato
- smoke test frontend rieseguiti dopo l'introduzione del layer compatibile `Presenze`
- smoke test frontend rieseguiti dopo la prima adozione reale dei wrapper `Presenze`
- test backend mirati verdi nel virtualenv di progetto:
  - `test_auth.py`
  - `test_user_management.py`
  - `test_section_permissions.py`
  - `test_presenze_api.py`
  - `test_wiki_guardrails.py`
  - `test_wiki_semantic_router.py`
  - `test_wiki_capability_registry.py`
  - batch dominio presenze su auto sync, runtime sync, live login, import, API, scheduler, worker e credenziali
  - batch Fase C confermato verde dopo il rename dei service `credentials`, `bank_hours_guidance_config`, `sync_runtime`, `sync_worker`
  - batch Fase C confermato verde dopo il ribaltamento canonico di `models.py` e `schemas.py`
  - compatibilita dinamica `__getattr__` confermata con import smoke sui nomi legacy del dominio
  - batch verdi dopo il rename del flag modulo e dell'artifact collaboratori
- test frontend unit mirati verdi:
  - `presenze-redirects`
  - `presenze-pages`
  - `presenze-giornaliere-page`
  - `presenze-anomalie-page`
  - `presenze-collaboratore-detail`
  - `presenze-collaborator-mapping`
  - `wiki-conversations-page`
  - `gaia-users-page`

## Decisioni prese

- non cambiare nella Fase A route, tipi o storage
- usare `Giornaliere` nelle superfici operative del modulo
- usare `Presenze` come termine di dominio nei documenti di refactor e nella futura fase tecnica
- mantenere solo il minimo storico necessario su tabelle legacy e migration history, spostando tutto il wiring runtime attivo sul namespace canonico `presenze`

## Prossimo passo

Chiudere la Fase C con gli ultimi residui documentali e operativi:

- ripulire i documenti di stato e wiki dal naming superato
- decidere separatamente se rinominare anche le tabelle legacy `inaz_*`
- lasciare invariato il path reale dello scraper esterno finche non viene rinominato anche quel repository
