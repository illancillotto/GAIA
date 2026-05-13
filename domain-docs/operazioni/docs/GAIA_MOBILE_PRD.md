# GAIA Mobile — PRD

## 1. Visione

GAIA Mobile e il prodotto satellite cloud/mobile per gli operatori sul campo del Consorzio.

Obiettivo principale: permettere agli operatori di registrare attivita, chiusure, segnalazioni, posizione e allegati da smartphone senza esporre il gestionale GAIA LAN su internet.

GAIA resta il sistema master interno. GAIA Mobile raccoglie eventi operativi, li sincronizza tramite un connector locale outbound-only e conserva nel cloud solo i dati minimi necessari alla continuita operativa.

---

## 2. Obiettivi

- Fornire una PWA mobile-first semplice per operatori non tecnici.
- Supportare uso in campo con rete instabile o assente.
- Evitare port forwarding o esposizione diretta di GAIA.
- Garantire sincronizzazione idempotente e auditabile verso GAIA.
- Gestire allegati fotografici e posizione GPS in modo controllato.
- Consentire al Consorzio di mantenere GAIA in LAN come fonte autorevole.

---

## 3. Non obiettivi

- Non replicare tutta la UI desktop di GAIA.
- Non sostituire il modulo Operazioni interno.
- Non gestire amministrazione completa, approvazioni avanzate o configurazioni cataloghi.
- Non esporre direttamente database o API interne di GAIA.
- Non conservare nel cloud dati storici completi oltre la retention operativa definita.

---

## 4. Architettura funzionale

```text
Operatore smartphone
  -> GAIA Mobile PWA cloud
  -> Gateway API cloud
  -> Sync queue cloud
  <- Connector locale in LAN, outbound-only
  -> GAIA LAN
```

GAIA Mobile cloud riceve eventi e li mette in coda.
Il connector locale apre solo connessioni in uscita verso il cloud, scarica eventi pendenti, li applica a GAIA usando API interne e rimanda esito, mapping ID e messaggi di errore.

---

## 5. Ruoli

### Operatore

- Avvia attivita.
- Chiude attivita.
- Crea segnalazioni.
- Allega foto o note.
- Consulta il proprio workset sincronizzato.
- Vede lo stato di sincronizzazione.

### Capo servizio

Nella prima release usa GAIA LAN.
Eventuale supporto mobile futuro:
- consultazione segnalazioni del team;
- conferma presa in carico;
- messaggi operativi.

### Admin tecnico

- Configura connector.
- Gestisce chiavi cloud.
- Monitora code, errori e backlog.
- Gestisce retention e storage.

---

## 6. Funzionalita mobile

### 6.1 Login operatore

- Login tramite credenziali dedicate o magic link.
- Sessione mobile separata dalla sessione GAIA LAN.
- Associazione stabile tra utente mobile e operatore GAIA.
- Possibile supporto MFA in fase successiva.

### 6.2 Home operativa

- Stato online/offline.
- Stato sync: sincronizzato, in coda, errori.
- Azioni rapide:
  - nuova attivita;
  - chiudi attivita;
  - nuova segnalazione;
  - bozze;
  - mie liste.

### 6.3 Avvio attivita

- Selezione catalogo attivita sincronizzato.
- Selezione mezzo se richiesto o disponibile.
- Note opzionali.
- GPS iniziale se disponibile.
- Creazione evento locale con UUID client.

### 6.4 Chiusura attivita

- Lista attivita aperte sincronizzate per operatore.
- Inserimento note, km, allegati facoltativi.
- GPS finale se disponibile.
- Invio evento di chiusura idempotente.

### 6.5 Nuova segnalazione

- Categoria e severita.
- Descrizione.
- Posizione GPS automatica se disponibile.
- Foto/allegati.
- Possibile collegamento ad attivita in corso.
- Creazione pratica su GAIA solo dopo applicazione connector.

### 6.6 Liste personali

- Attivita in corso.
- Segnalazioni inviate.
- Pratiche assegnate o collegate.
- Ultimo stato ricevuto da GAIA.

### 6.7 Bozze e offline

- Salvataggio locale su IndexedDB.
- Retry automatico quando torna la rete.
- Retry manuale per singola bozza.
- Stati visibili all'utente:
  - bozza locale;
  - in invio;
  - ricevuta dal cloud;
  - applicata a GAIA;
  - errore da correggere.

---

## 7. Requisiti sync

Ogni evento mobile deve avere:
- `client_event_id` UUID generato dal device;
- `event_type`;
- `operator_id` mobile;
- `device_id`;
- `created_at_device`;
- `received_at_cloud`;
- payload versione;
- stato sync;
- hash payload;
- eventuale `gaia_entity_id` dopo applicazione;
- log errori.

Il connector deve garantire:
- polling outbound-only;
- lock/claim degli eventi;
- retry con backoff;
- idempotenza;
- mapping ID cloud/GAIA;
- ack finale al cloud;
- nessuna perdita silenziosa.

---

## 8. Sicurezza

- GAIA LAN non deve essere raggiungibile da internet.
- Il connector usa solo connessioni HTTPS in uscita.
- Autenticazione connector con chiave ruotabile o mTLS.
- Token operatori a scadenza breve.
- Payload validati lato gateway e lato connector.
- Allegati scansionabili e limitati per tipo/dimensione.
- Audit log completo su cloud e su GAIA.
- Retention cloud minima e configurabile.

---

## 9. Storage allegati

- Upload diretto al gateway cloud.
- Ogni allegato ha checksum, dimensione, mime type, owner e stato sync.
- Il connector scarica allegati solo per eventi da applicare.
- Dopo conferma GAIA, il cloud puo mantenere solo metadata e allegato per retention breve.
- Limiti iniziali suggeriti:
  - immagini: max 10 MB per file;
  - video: disabilitato in MVP o max 50 MB;
  - batch per segnalazione: max 5 allegati.

---

## 10. Requisiti non funzionali

- PWA installabile su Android e iOS.
- UX usabile con una mano.
- Target: 100 operatori attivi.
- Operativita offline minima per almeno 24 ore di bozze locali.
- Sync cloud entro pochi secondi quando il device ha rete.
- Sync GAIA dipendente dalla frequenza connector, default ogni 10-30 secondi.
- Osservabilita su backlog, errori, latenza media, eventi bloccati.

---

## 11. MVP

### Incluso

- PWA mobile.
- Gateway API cloud.
- Connector locale outbound-only.
- Auth operatori base.
- Cataloghi sincronizzati da GAIA.
- Avvio attivita.
- Chiusura attivita.
- Nuova segnalazione.
- Allegati foto.
- GPS iniziale/finale.
- Bozze offline.
- Queue sync con idempotenza.
- Dashboard tecnica minima per code/errori.

### Escluso

- App nativa.
- Workflow approvazioni mobile.
- GIS completo.
- Editing avanzato pratiche.
- Chat o messaggistica.
- Integrazione Telegram.

---

## 12. Criteri di accettazione

- Un operatore puo creare una segnalazione offline, tornare online e vedere lo stato applicato a GAIA.
- Lo stesso evento inviato due volte non crea duplicati in GAIA.
- GAIA non espone porte pubbliche.
- Il connector puo essere spento e riacceso senza perdere eventi.
- Gli errori validazione GAIA tornano visibili nella PWA.
- Gli allegati arrivano su GAIA con checksum coerente.
- La lista personale mostra gli stati aggiornati dopo sync connector.
