# GAIA CED
## Product Requirements Document

> Nota repository
> Questo documento descrive l'evoluzione pianificata del modulo aggregatore `GAIA CED`.
> Nella prima fase il modulo riusa i backend esistenti `accessi` e `network` senza introdurre un nuovo backend dedicato.

## 1. Visione

`GAIA CED` e il punto di accesso unificato per i servizi IT infrastrutturali del Consorzio.
L'obiettivo e convergere le superfici oggi esposte come `GAIA NAS Control` e `GAIA Rete`
in un unico modulo frontend coerente, con navigazione, dashboard e linguaggio condivisi.

## 2. Problema

Lo stato attuale presenta due moduli distinti per un unico ambito operativo CED:

- `NAS Control` per audit accessi, review e report NAS
- `Rete` per scansioni LAN, alert, planimetrie e inventario osservato

Questa separazione genera:

- duplicazione di entrypoint in home, login e sidebar
- frammentazione della navigazione per l'utente CED
- permessi e naming non immediatamente leggibili lato piattaforma
- complessita aggiuntiva nei futuri flussi operativi trasversali

## 3. Obiettivo

Introdurre un modulo `GAIA CED` che:

- diventi l'entrypoint unico frontend per NAS e Rete
- mantenga invariati, nella prima fase, i backend e le API esistenti
- permetta una migrazione graduale di route e navigazione
- resti compatibile con i permessi attuali `module_accessi` e `module_rete`

## 4. Obiettivi di fase 1

- nuovo namespace frontend `frontend/src/app/ced/*`
- dashboard `GAIA CED` accessibile a utenti con almeno uno tra `accessi` e `rete`
- menu laterale unico con due aree:
  - `NAS`
  - `Rete`
- riuso delle pagine esistenti o dei loro componenti senza refactor distruttivo del backend
- aggiornamento home, login e sidebar per mostrare `GAIA CED` come entrypoint primario

## 5. Non obiettivi di fase 1

- introduzione immediata di un nuovo backend `app/modules/ced`
- sostituzione immediata dei router `/nas-control/*` e `/network/*`
- riscrittura del modello permessi applicativo
- fusione dei cataloghi sezione `accessi.*` e `rete.*`

## 6. Stakeholder

- amministratori IT e CED
- responsabili rete
- responsabili audit accessi NAS
- utenti applicativi che oggi usano `NAS Control` e `Rete`
- manutentori frontend/backend GAIA

## 7. Ambito funzionale target

### 7.1 Area NAS

- dashboard NAS
- sync
- utenti
- gruppi
- cartelle condivise
- permessi effettivi
- review
- report

### 7.2 Area Rete

- dashboard rete
- dispositivi
- alert
- scansioni
- planimetria

### 7.3 Dashboard CED

- ingresso unico con KPI e collegamenti rapidi alle aree NAS e Rete
- accesso contestuale solo alle sezioni abilitate per l'utente

## 8. Requisiti funzionali

### 8.1 Navigazione

- RF-CED-01: la home GAIA deve mostrare `GAIA CED` come modulo infrastrutturale unificato
- RF-CED-02: la sidebar piattaforma deve esporre `CED` come voce primaria
- RF-CED-03: la module sidebar di `CED` deve raggruppare la navigazione in sezioni `NAS` e `Rete`

### 8.2 Accesso e permessi

- RF-CED-04: `/ced` e visibile se l'utente ha almeno un modulo tra `accessi` e `rete`
- RF-CED-05: `/ced/nas/*` richiede i permessi attuali del dominio accessi
- RF-CED-06: `/ced/rete/*` richiede i permessi attuali del dominio rete

### 8.3 Compatibilita

- RF-CED-07: i backend `accessi` e `network` restano invariati nella fase 1
- RF-CED-08: le route legacy possono restare attive fino al completamento della migrazione interna
- RF-CED-09: la documentazione deve distinguere chiaramente stato attuale e target evolutivo

## 9. Requisiti non funzionali

- migrazione a basso rischio
- nessuna regressione sui moduli esistenti
- riuso massimo di componenti e API
- documentazione e routing repository coerenti con il piano

## 10. Struttura target proposta

```text
frontend/src/app/
  ced/
    page.tsx
    nas/
      page.tsx
      sync/page.tsx
      users/page.tsx
      groups/page.tsx
      shares/page.tsx
      effective-permissions/page.tsx
      reviews/page.tsx
      reports/page.tsx
    rete/
      page.tsx
      devices/page.tsx
      alerts/page.tsx
      scans/page.tsx
      floor-plan/page.tsx
```

## 11. Strategia di permessi raccomandata

### Fase 1

- mantenere `module_accessi`
- mantenere `module_rete`
- `GAIA CED` e solo un contenitore frontend

### Fase 2 opzionale

- valutare introduzione `module_ced`
- definire una migrazione applicativa e DB separata
- decidere se mantenere o deprecare i flag attuali

## 12. KPI iniziali

- riduzione da due a un solo entrypoint infrastrutturale in home e sidebar
- nessuna regressione sulle funzionalita NAS e Rete
- navigazione unificata percepita dagli utenti CED
- documentazione di esecuzione e stato disponibile prima dell'implementazione

## 13. Roadmap sintetica

1. preparazione documentale e piano operativo `GAIA CED`
2. introduzione shell frontend `/ced`
3. aggiornamento navigation e home
4. riuso delle viste NAS e Rete sotto `CED`
5. migrazione o redirect dei path legacy
6. eventuale unificazione futura dei permessi
