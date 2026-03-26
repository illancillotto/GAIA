# Prompt Codex — GAIA Rete

> Regola strutturale vincolante
> GAIA usa un backend monolitico modulare. Il codice backend del dominio Rete va creato in `backend/app/modules/network/`. Il frontend del modulo vive in `frontend/src/app/network/`. Lo scanner LAN resta un servizio tecnico separato, ma non costituisce un backend applicativo autonomo.

> Da usare come system prompt o primo messaggio in una sessione di sviluppo dedicata al modulo Rete.

---

## Contesto del progetto

Stai sviluppando **GAIA Rete**, il modulo di monitoraggio della rete LAN della piattaforma **GAIA**.

GAIA e una piattaforma multi-modulo con backend e frontend condivisi. I moduli applicativi convivono nello stesso monolite:

- **Accessi**
- **Network**
- **Inventory**
- **Catasto**

Il repository adotta una struttura canonica in cui il backend applicativo vive sotto `backend/` e i moduli di dominio sotto `backend/app/modules/`.

---

## Stack obbligatorio

**Backend**
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic
- python-nmap
- APScheduler
- scapy per fallback ARP scan

**Frontend**
- Next.js
- React
- TypeScript
- TailwindCSS
- TanStack Table
- eventuali componenti drag-and-drop solo dove servono davvero alla planimetria

**Infrastructure**
- Docker Compose esistente
- backend e database condivisi con gli altri moduli
- servizio tecnico `scanner` separato con permessi di rete dedicati

---

## Principi architetturali

- Il backend resta un **monolite modulare**: nuove feature del dominio Rete vanno sviluppate nel modulo canonico `backend/app/modules/network/`
- Il punto di integrazione backend e il router di modulo `backend/app/modules/network/router.py`, incluso in `backend/app/api/router.py`
- I path legacy fuori da `backend/app/modules/` vanno trattati come area di compatibilita, non come destinazione primaria per nuove feature
- Il frontend del modulo vive in `frontend/src/app/network/` nel frontend condiviso
- Non creare un frontend separato o un backend applicativo separato per il modulo
- Lo scanner LAN puo vivere come container/processo tecnico separato, ma deve leggere e scrivere nel database condiviso della piattaforma
- Auth, sessione DB, logging, config e dipendenze FastAPI vanno riutilizzati dall'app esistente
- Alembic resta unico: nuove migration in `backend/alembic/versions/`
- Il modulo e **read-only** rispetto alla rete: nessuna modifica a configurazioni di host, switch, router o firewall
- L'integrazione con Inventario deve avvenire tramite database condiviso e correlazione dati, non tramite chiamate HTTP interne tra moduli

---

## Modello dati da implementare

Entita principali del modulo:

```text
network_scans
network_devices
network_alerts
floor_plans
device_positions
device_inventory_links
```

Riferimento funzionale e campi iniziali: `modules/network/docs/PRD_network.md`, sezione modello dati.

Linee guida:

- `network_scans` rappresenta snapshot coerenti delle scansioni
- `network_devices` conserva stato osservato, host metadata e cronologia minima utile
- `network_alerts` contiene eventi derivati o condizioni da evidenziare
- l'associazione con Inventario privilegia matching via `mac_address` o tabella di link dedicata

---

## API da implementare

Tutti gli endpoint del modulo devono essere esposti dal backend condiviso sotto prefisso `/network`.

Pattern architetturale:

- route del modulo nel package `backend/app/modules/network/`
- business logic in `services.py`
- schemi request/response in `schemas.py`
- modelli SQLAlchemy in `models.py`
- codice dello scheduler o del motore di scansione mantenuto separato dal layer HTTP

Riferimento endpoint: `modules/network/docs/PRD_network.md`, sezione API.

---

## Pagine frontend da implementare

```text
/network
/network/devices
/network/devices/[id]
/network/floor-plan
/network/alerts
/network/scans
/network/scans/[id]
```

Linee guida frontend:

- usare App Router nella struttura esistente di `frontend/src/app/`
- mantenere coerenza con auth flow, layout e componenti condivisi del progetto
- tabelle con sorting, filtri e paginazione lato server quando il dataset lo richiede
- la planimetria deve restare uno strumento operativo, non una demo grafica decorativa

---

## Requisiti UI/UX

- UI amministrativa sobria e leggibile, coerente con gli altri moduli GAIA
- badge online/offline immediati e leggibili
- planimetria con overlay chiaro, tooltip utili e focus sulla localizzazione operativa dei dispositivi
- storico scansioni e alert leggibili senza sovraccarico visivo
- responsive desktop-first; mobile secondario

---

## Priorita di sviluppo

1. Modello dati e migration Alembic
2. Scanner LAN e schedulazione
3. Router di modulo `backend/app/modules/network/router.py`
4. API `/network`
5. Frontend dashboard e lista dispositivi
6. Planimetria interattiva
7. Alert engine e pagina alert
8. Integrazione con Inventario nel database condiviso

---

## Vincoli tecnici

- non creare un backend separato per il modulo Rete
- non introdurre nuovi path primari fuori da `backend/app/modules/network/` per il codice backend di dominio
- il servizio `scanner` richiede permessi di rete dedicati, ad esempio `NET_RAW` e `NET_ADMIN`, nel `docker-compose.yml`
- il range di rete deve essere configurabile via environment
- privilegiare scansioni incrementali e costi controllati
- nessuna modifica attiva alla rete: solo discovery, osservazione, persistenza e visualizzazione
- l'integrazione con Inventario usa dati condivisi nel DB, non API inter-modulo

---

## Istruzioni operative per Codex

Quando implementi o modifichi il modulo Rete:

- verifica prima la struttura reale del repository e segui il pattern canonico del backend modulare
- usa `backend/app/modules/network/` come superficie primaria del backend
- mantieni separati router HTTP, logica di business e componenti di scansione/scheduler
- tratta i file legacy fuori da `app/modules/` come wrapper compatibili, non come punto di partenza per nuove feature
- aggiungi o modifica integrazioni backend passando sempre da `backend/app/api/router.py` e dal router di modulo
- preserva compatibilita con il monolite condiviso, con Alembic unico e con il database unico
- usa `modules/network/docs/PRD_network.md` come riferimento funzionale, ma fai prevalere l'architettura canonica del repository quando i documenti piu vecchi divergono
