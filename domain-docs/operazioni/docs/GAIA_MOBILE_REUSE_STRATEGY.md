# GAIA Mobile — Strategia riuso mini-app Operazioni

## 1. Obiettivo

Valutare cosa riusare dalla mini-app Operazioni gia implementata nel repo GAIA e cosa invece riscrivere nel nuovo progetto `gaia-mobile`.

---

## 2. Cosa riusare

### UX e flussi

Riusare come riferimento:
- home mobile con azioni rapide;
- avvio attivita;
- chiusura attivita;
- nuova segnalazione;
- liste personali;
- bozze offline;
- stato online/offline;
- messaggi di errore e sync.

### Logica IndexedDB

Riusare il concetto di:
- draft locale;
- stato bozza;
- retry manuale;
- retry bulk;
- auto-sync al ritorno online.

Il file GAIA di riferimento e:

```text
frontend/src/features/operazioni/utils/offline-drafts.ts
```

Nel nuovo repo va pero adattato ai nuovi stati cloud:
- `LOCAL_DRAFT`;
- `LOCAL_PENDING`;
- `CLOUD_RECEIVED`;
- `APPLIED_TO_GAIA`;
- `FAILED_VALIDATION`;
- `FAILED_RETRYABLE`.

### Componenti visuali

Riusare solo come ispirazione.
Il nuovo progetto dovra avere una UI mobile-first autonoma, non dipendente dal layout desktop GAIA.

---

## 3. Cosa non copiare

- Client API che chiama direttamente GAIA.
- Routing Next.js interno a GAIA.
- Componenti legati alla sidebar/layout desktop.
- Assunzioni su sessione utente GAIA LAN.
- Chiamate dirette a `/api/operazioni/*`.
- Dipendenze da moduli frontend GAIA.

Motivo: nella nuova architettura la PWA parla solo con il gateway cloud.

---

## 4. Mapping concettuale

| Mini-app GAIA attuale | GAIA Mobile futuro |
|---|---|
| `startActivity()` verso GAIA | crea evento `ACTIVITY_START_REQUESTED` |
| `stopActivity()` verso GAIA | crea evento `ACTIVITY_STOP_REQUESTED` |
| `createReport()` verso GAIA | crea evento `FIELD_REPORT_CREATED` |
| bozze IndexedDB | bozze + sync event queue locale |
| liste personali da GAIA | workset cache cloud aggiornata dal connector |
| allegati verso GAIA | allegati verso cloud, poi connector li trasferisce |
| errore API GAIA immediato | errore asincrono da connector |

---

## 5. Impatti UX

La nuova PWA deve comunicare meglio gli stati asincroni.

Esempi:
- "Salvato sul telefono"
- "Inviato al cloud"
- "In attesa di GAIA"
- "Registrato in GAIA"
- "Richiede correzione"

Non promettere all'utente che una segnalazione e gia in GAIA finche il connector non ha mandato ack.

---

## 6. Raccomandazione

Non fare copia/incolla massivo.

Procedere cosi:
1. Implementare `packages/shared` con eventi e stati.
2. Implementare gateway con idempotenza.
3. Implementare connector contro GAIA mock.
4. Solo dopo portare i flussi UI prendendo ispirazione dalla mini-app esistente.
5. Adattare IndexedDB alla nuova macchina stati.

Questa sequenza evita di costruire una UI bella ma accoppiata al modello sbagliato.
