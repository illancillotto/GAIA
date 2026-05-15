# PRD — GAIA Catasto: Letture contatori irrigui

> Documento di prodotto per l'implementazione della gestione letture contatori nel modulo GAIA Catasto.
>
> Percorso consigliato nel repository: `domain-docs/catasto/docs/PRD_letture_contatori.md`
>
> Stato: bozza operativa pronta per sviluppo

## 1. Scopo

Implementare in **GAIA Catasto** una funzionalità per importare, archiviare, validare, consultare e collegare alle utenze consortili le letture dei contatori irrigui provenienti dai file Excel distrettuali.

La prima fase usa i file Excel oggi utilizzati dagli operatori, uno per ogni distretto. La seconda fase deve predisporre il sistema per l'integrazione con **GAIA Mobile**, in modo da sostituire progressivamente la raccolta manuale su Excel con letture raccolte da app.

## 2. Contesto operativo

Oggi le letture vengono gestite tramite file Excel distrettuali, ad esempio:

- `D01-Sinis 2025.xlsx`
- altri file analoghi per i diversi distretti irrigui

Il nuovo tracciato contiene informazioni più complete rispetto al vecchio file. Non cambia il numero dei punti di consegna, ma vengono aggiunte colonne operative, tecniche e di intervento.

Campi principali rilevati nel nuovo tracciato:

- ID
- punto di consegna
- matricola contatore
- sigillo
- tipologia idrante
- versione firmware
- livello batteria
- lettura iniziale 2025
- lettura finale 2025
- consumo 2025
- data lettura
- operatore lettura
- intervento da eseguire
- intervento eseguito
- operatore intervento
- data intervento
- D.U.I.
- codice fiscale
- coltura
- tariffa
- fondo chiuso
- note
- numero di telefono

## 3. Obiettivo funzionale

Il sistema deve permettere di:

1. caricare un file Excel distrettuale;
2. validare il contenuto del file;
3. importare le letture dei contatori;
4. agganciare ogni lettura all'utenza tramite codice fiscale;
5. mostrare nel dettaglio utente le letture e i punti di consegna associati;
6. consultare le letture per anno, distretto, punto di consegna, codice fiscale e stato anomalia;
7. preparare il modello dati alla futura acquisizione da GAIA Mobile.

La regola principale di aggancio è:

```text
lettura_contatore.codice_fiscale_normalizzato
        ->
utenza.codice_fiscale_normalizzato
```

## 4. Ambito della fase 1

### Incluso

- Upload file Excel da interfaccia GAIA.
- Scelta o riconoscimento del distretto.
- Scelta anno campagna.
- Validazione preventiva del file.
- Import delle righe valide.
- Salvataggio storico import.
- Collegamento alle utenze tramite codice fiscale.
- Report anomalie.
- Pagina Catasto dedicata alle letture.
- Sezione nel dettaglio utente.
- API backend per consultazione e import.
- Predisposizione campo `source` per futura origine `mobile`.

### Escluso dalla fase 1

- Lettura diretta da app mobile.
- Sincronizzazione offline.
- Foto obbligatoria del contatore.
- GPS obbligatorio.
- Firma operatore.
- Calcolo tariffario definitivo.
- Emissione ruoli o fatturazione.

## 5. Utenti e ruoli

| Ruolo | Esigenza |
|---|---|
| Admin | Gestione completa del modulo |
| Operatore Catasto | Import e verifica letture |
| Responsabile Catasto | Controllo anomalie e consumi |
| Operatore mobile futuro | Inserimento letture da app |
| Utente consultazione | Visualizzazione dati collegati all'utenza |

## 6. Regole di business

### 6.1 Codice fiscale come chiave di aggancio

Il campo `COD FISCALE` / `COD. FISC` è la chiave logica per agganciare il record alla relativa utenza.

La normalizzazione deve:

- rimuovere spazi;
- convertire in maiuscolo;
- eliminare caratteri non significativi;
- trattare valori vuoti come `null`;
- segnalare valori formalmente anomali.

Il codice fiscale non deve essere usato come chiave primaria della lettura, perché una stessa utenza può avere più punti di consegna.

### 6.2 Punto di consegna come riferimento tecnico

Il campo `PUNTO DI CONSEGNA` è il riferimento tecnico stabile del contatore/punto irriguo.

La chiave funzionale consigliata è:

```text
anno + distretto_id + punto_consegna
```

### 6.3 ID Excel non affidabile

Il campo `ID` del file Excel non deve essere usato come chiave tecnica affidabile, perché possono esistere valori vuoti o progressivi non allineati.

Il campo va comunque salvato come `excel_id` per tracciabilità.

### 6.4 Reimport

Il sistema deve gestire il caricamento ripetuto dello stesso distretto/anno.

Modalità previste:

| Modalità | Descrizione |
|---|---|
| `validate_only` | valida senza salvare |
| `import` | importa solo se non esistono dati per distretto/anno |
| `upsert` | inserisce nuovi record e aggiorna gli esistenti |
| `replace` | sostituisce logicamente i dati del distretto/anno |

## 7. Requisiti funzionali

### RF-01 — Import Excel

Il sistema deve consentire il caricamento di un file `.xlsx` contenente le letture di un distretto.

Input richiesti:

- file Excel;
- anno;
- distretto, manuale o dedotto dal nome file;
- modalità import.

### RF-02 — Validazione preventiva

Prima dell'import definitivo il sistema deve mostrare:

- numero righe lette;
- numero righe valide;
- numero warning;
- numero errori bloccanti;
- anteprima dati;
- elenco anomalie.

### RF-03 — Import definitivo

Il sistema deve salvare:

- record import;
- righe lettura;
- anomalie per riga;
- esito aggancio utenza.

### RF-04 — Aggancio utenze

Per ogni lettura con codice fiscale valorizzato il sistema deve cercare una utenza/soggetto con lo stesso codice fiscale normalizzato.

Esiti possibili:

| Esito | Azione |
|---|---|
| una utenza trovata | collega automaticamente |
| nessuna utenza trovata | importa con warning |
| più utenze trovate | importa con warning di ambiguità |
| CF mancante | importa senza aggancio |
| CF anomalo | importa con warning |

### RF-05 — Dettaglio utente

Nel dettaglio utente deve comparire una sezione:

```text
Letture contatori
```

La sezione deve mostrare tutte le letture collegate al codice fiscale del soggetto.

Campi minimi:

- anno;
- distretto;
- punto consegna;
- matricola;
- lettura iniziale;
- lettura finale;
- consumo mc;
- data lettura;
- operatore;
- coltura;
- tariffa;
- intervento;
- note;
- stato validazione.

### RF-06 — Pagina Catasto dedicata

La sidebar Catasto deve includere:

```text
Catasto -> Contatori irrigui
```

La pagina deve permettere:

- consultazione tabellare;
- filtri;
- dettaglio lettura;
- import Excel;
- report anomalie;
- esportazione CSV/XLSX.

### RF-07 — Dashboard sintetica

La pagina deve mostrare indicatori:

- totale letture;
- distretti importati;
- utenze agganciate;
- utenze non agganciate;
- record con warning;
- consumi totali per distretto;
- interventi da eseguire;
- fondi chiusi;
- batterie basse, se disponibili.

## 8. Validazioni

### Errori bloccanti

| Caso | Azione |
|---|---|
| punto di consegna mancante | riga scartata |
| anno mancante | import bloccato |
| distretto mancante e non deducibile | import bloccato |
| duplicati nello stesso file su anno/distretto/punto | errore o warning in base alla modalità |

### Warning non bloccanti

| Caso | Azione |
|---|---|
| codice fiscale mancante | import senza aggancio |
| codice fiscale anomalo | import con warning |
| utenza non trovata | import con warning |
| più utenze con stesso CF | import con warning |
| telefono non valido | import come testo con warning |
| consumo incoerente | warning |
| lettura finale minore della iniziale | warning |
| intervento da eseguire valorizzato | warning operativo |
| batteria bassa | warning operativo |

## 9. Requisiti non funzionali

- Import robusto anche con nomi colonna leggermente diversi.
- Import idempotente per stesso anno/distretto/punto consegna.
- Audit degli import.
- Tracciabilità del file sorgente.
- Nessun backend separato.
- Codice backend nel monolite modulare GAIA sotto `backend/app/modules/catasto/`.
- Frontend in `frontend/src/app/catasto/`.
- Predisposizione per GAIA Mobile senza obbligo di implementarla subito.

## 10. Criteri di accettazione

La fase 1 è completa quando:

1. un utente autorizzato carica un Excel distrettuale;
2. il sistema valida il file e mostra anomalie;
3. il sistema importa le righe valide;
4. il sistema collega le letture alle utenze tramite CF normalizzato;
5. nel dettaglio utente compaiono le letture collegate;
6. la pagina Catasto consente filtri per anno, distretto, CF e punto consegna;
7. il sistema gestisce reimport e upsert;
8. il campo `ID` Excel non viene usato come chiave primaria;
9. vengono salvati stato validazione e messaggi anomalia;
10. sono presenti test backend su parser, validazione, import e linking.
