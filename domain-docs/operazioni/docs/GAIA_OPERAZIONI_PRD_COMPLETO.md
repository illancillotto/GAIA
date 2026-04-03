# GAIA Operazioni – PRD DEFINITIVO (Production-Ready)

---

## 1. Visione

GAIA Operazioni è il modulo per la gestione certificata delle operazioni sul campo del Consorzio, integrato nel monolite GAIA.
Copre:
- gestione mezzi
- consuntivazione attività operatori
- gestione segnalazioni come pratiche interne

Il sistema produce dati **auditabili**, con distinzione tra:
- dato dichiarato
- dato rilevato (GPS)
- dato validato (capo servizio)

---

## 2. Obiettivi

- Tracciamento completo e verificabile dei mezzi
- Consuntivazione affidabile delle attività
- Workflow strutturato per segnalazioni/pratiche
- Riduzione errori operativi sul campo
- Semplicità d’uso per operatori non tecnici

---

## 3. Ruoli e Permessi

### Admin
- configurazione globale
- gestione cataloghi
- visione completa

### Capo Servizio
- approvazione attività
- gestione pratiche
- riassegnazioni

### Operatore
- inserimento attività
- creazione segnalazioni

### Regole permessi
- operatore → solo proprie attività
- capo → attività del team
- admin → tutto

---

## 4. Domini Funzionali

### 4.1 Mezzi

#### Funzioni
- anagrafica mezzo
- assegnazione a operatore o squadra (storica)
- sessione utilizzo (obbligatoria)
- km iniziali/finali obbligatori
- registrazione carburante
- manutenzioni
- documenti/scadenze

#### Regole
- un mezzo può essere usato da un solo soggetto per sessione
- km finale >= km iniziale
- non è possibile aprire 2 sessioni contemporanee sullo stesso mezzo

---

### 4.2 Attività

#### Funzioni
- selezione da catalogo fisso
- avvio/stop attività
- associazione mezzo (facoltativa)
- note testo/audio
- tracciamento tempo automatico

#### Regole
- attività deve avere timestamp start/stop
- attività senza stop → stato “in corso”
- attività sovrapposte vietate per stesso operatore

---

### 4.3 Segnalazioni / Pratiche

#### Funzioni
- creazione segnalazione rapida
- GPS automatico obbligatorio se disponibile
- allegati (foto/audio/video)
- creazione automatica pratica

#### Regole
- ogni segnalazione genera una pratica
- la pratica ha stato e assegnazione
- allegati obbligatori per categorie critiche

---

## 5. Workflow Dettagliati

### 5.1 Utilizzo Mezzo

1. operatore seleziona mezzo
2. inserisce km iniziali
3. avvia sessione
4. sistema registra timestamp + GPS
5. operatore chiude sessione
6. inserisce km finali
7. sistema valida coerenza

Errore:
- km finali < iniziali → blocco

---

### 5.2 Attività

1. selezione attività
2. avvio
3. sistema registra timestamp
4. eventuale associazione mezzo
5. chiusura
6. invio
7. stato → in approvazione

Capo:
- approva → stato finale
- respinge → ritorna all’operatore

---

### 5.3 Segnalazione

1. apertura schermata
2. GPS acquisito
3. selezione categoria
4. allegati
5. invio
6. creazione pratica

Errore:
- GPS assente → warning ma non blocco

---

## 6. Stati e Transizioni

### Attività
- bozza → inviata → in approvazione → approvata
- respinta → modificabile

### Pratiche
- aperta → assegnata → in lavorazione → chiusa
- chiusa → non modificabile

---

## 7. Requisiti Non Funzionali

### Performance
- supporto 100+ operatori simultanei

### Affidabilità
- sistema resiliente a perdita rete

### Sicurezza
- audit log completo
- immutabilità dati critici

### Storage
- limite 50GB
- alert:
  - 70% warning
  - 85% warning forte
  - 95% critico

---

## 8. Offline Strategy

Supportato:
- creazione attività
- creazione segnalazioni

Non supportato:
- approvazioni
- modifiche avanzate

### Sync
- retry automatico
- gestione duplicati tramite ID locale

---

## 9. GPS

### Tipologie dati
- dichiarato (operatore)
- rilevato (device/GPS)
- validato (capo)

### Regole
- GPS obbligatorio quando disponibile
- fallback manuale consentito

---

## 10. Validazioni

- campi obbligatori:
  - attività → tipo + timestamp
  - mezzo → km iniziali/finali
  - segnalazione → categoria

- allegati:
  - video compressione automatica

---

## 11. UX Mini-App

### Home
- Avvia attività
- Chiudi attività
- Nuova segnalazione

### Regole UX
- massimo 3 click per azione
- input minimi
- feedback immediato

---

## 12. Error Handling

- rete assente → modalità offline
- GPS assente → warning
- upload fallito → retry

---

## 13. KPI

- utilizzo mezzi
- tempo medio attività
- numero pratiche
- tempo chiusura pratiche

---

## 14. SLA (base)

- segnalazioni critiche → presa in carico < 24h

---

## 15. Roadmap

### MVP
- mezzi
- attività
- segnalazioni

### Evoluzione
- GPS avanzato
- analytics
- mappe

---

## 16. Note Finali

PRD progettato per sviluppo diretto e integrazione completa con architettura GAIA monolite modulare.

Questo documento è considerato vincolante per:
- schema DB
- API
- sviluppo backend/frontend

