# Prompt Codex — GAIA Rete (Network Monitor)

> Da usare come system prompt o primo messaggio in una sessione di sviluppo dedicata.

---

## Contesto del progetto

Stai sviluppando **GAIA Rete**, il modulo di monitoraggio di rete della piattaforma **GAIA** per il Consorzio di Bonifica dell'Oristanese.

GAIA è una piattaforma IT governance con tre moduli:
- **GAIA Accessi** — NAS Audit (già completato, repo esistente)
- **GAIA Rete** — Network Monitor (questo modulo)
- **GAIA Inventario** — IT Inventory (modulo parallelo)

Il repository si trova su `github.com/illancillotto/GAIA`.

---

## Stack obbligatorio

**Backend**
- FastAPI, SQLAlchemy, Alembic, PostgreSQL
- python-nmap, APScheduler
- scapy (fallback ARP scan)

**Frontend**
- Next.js, React, TypeScript, TailwindCSS
- TanStack Table
- react-draggable (planimetria drag-and-drop)

**Infrastructure**
- Docker Compose — aggiunta servizio `scanner` con `cap_add: [NET_RAW, NET_ADMIN]`

---

## Principi architetturali

- Il modulo si aggiunge al backend e frontend **esistenti** come router/sezione aggiuntiva
- **NON** creare un backend separato: aggiungere `app/routers/network.py` al FastAPI esistente
- **NON** creare un frontend separato: aggiungere `frontend/src/app/network/` al Next.js esistente
- Lo scanner LAN gira come **container Docker separato** con `cap_add: [NET_RAW, NET_ADMIN]`
- Auth JWT condivisa: riutilizzare il middleware esistente senza modifiche
- Alembic: creare nuove migration in `alembic/versions/` senza toccare quelle esistenti
- Il modulo è **read-only** rispetto alla rete: nessuna modifica a configurazioni

---

## Modello dati da implementare

```
network_scans         — snapshot scansioni
network_devices       — dispositivi rilevati
network_alerts        — alert generati
floor_plans           — planimetrie per piano
device_positions      — posizione dispositivo su planimetria
device_inventory_links — collegamento rete ↔ inventario
```

Schema completo in `modules/network/docs/PRD.md` sezione 3.

---

## API da implementare

Tutti gli endpoint sotto il prefisso `/network`.  
Lista completa in `modules/network/docs/PRD.md` sezione 4.

---

## Pagine frontend da implementare

```
/network                  — dashboard
/network/devices          — lista dispositivi
/network/devices/[id]     — dettaglio dispositivo
/network/floor-plan       — mappa planimetria
/network/alerts           — gestione alert
/network/scans            — storico scansioni
/network/scans/[id]       — dettaglio snapshot
```

---

## Requisiti UI/UX

- Stile coerente con GAIA Accessi: professionale, orientato alla lettura amministrativa, no effetti decorativi
- Badge stato online/offline: verde/rosso, leggibile a colpo d'occhio
- Planimetria: SVG overlay con cerchi colorati per dispositivi, tooltip al hover con IP e hostname
- Tabelle: TanStack Table con sorting, filtering lato server, paginazione
- Responsive desktop-first; mobile non prioritario

---

## Priorità di sviluppo

1. Modello dati + migration Alembic
2. Scanner LAN (`python-nmap`) con scheduler APScheduler
3. API FastAPI router `/network`
4. Frontend: lista dispositivi + dashboard
5. Frontend: planimetria interattiva
6. Alert engine + pagina alert
7. Integrazione con GAIA Inventario (MAC matching)

---

## Vincoli e note tecniche

- Ambiente: rete LAN privata, nessun accesso a internet dal container scanner
- `nmap` richiede `NET_RAW`: configurare il container scanner con `cap_add` nel `docker-compose.yml`
- Range di rete configurabile tramite variabile d'ambiente `NETWORK_RANGE`
- Preferire scansioni incrementali: ping scan + port scan sui soli host attivi
- Il modulo è read-only rispetto alla rete: nessuna modifica a configurazioni
- Integrazione GAIA Inventario: matching via `mac_address` con JOIN diretto su DB, non API call
