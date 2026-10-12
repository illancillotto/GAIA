# Import Poste: colonna CF prima dell'indirizzo

## Difetto e contratto

`_parse_posta_online_detail_html` interpretava la quarta cella della tabella
`destinatario` sempre come indirizzo e la quinta come informazioni/tracking.
Nell'import `posta-online-worker-job-5-optimized.json` risultano invece 1196
indirizzi con struttura CF e un indirizzo completo conservato in `raw.info`.
49 righe sono già associate; tutte hanno tracking assente nel database.
Il solo tracking assente non prova l'assenza di una spedizione.

Il parser continua a supportare il layout legacy. Quando la quarta cella è
un CF o un identificativo fiscale numerico di 11 cifre, richiede una quinta
cella con CAP, usa questa come indirizzo e cerca il tracking nelle celle
successive. Layout incompleti sono rifiutati, non importati come indirizzi CF.
Il CF e tutte le celle originali sono preservati nel payload `raw`.
La validazione identifica la struttura del codice, non ne certifica ownership
o correttezza fiscale. Non costituisce autorizzazione per il matching.

## Riparazione dei dati pregressi

- Usare un manifest sullo stato aggiornato e un backup scoped prima di scrivere.
- Recuperare indirizzo, CAP, provincia e comune soltanto dal dato originale
  `raw.info`, conservando CF originale e provenienza della riparazione.
- Aggiornare anche gli indirizzi normalizzati del payload.
- Non cambiare associazioni, annualità, stato matching, notifiche, costi o tracking.
- Simulare gli aggiornamenti in transazione e confermare il rollback; applicare
  soltanto se il database è identico al preflight e verificare dopo il commit.
- Non inventare tracking: recuperarli dalla fonte Poste in una fase separata.
- Eseguire il backfill dopo la conclusione di eventuali deploy concorrenti.
- Aggiornare il parser sia sul backend sia sul worker Poste, che importa
  `tributi_repositories` dal proprio runtime backend.

## Validazione locale

Test dedicati: `backend/tests/ruolo/test_posta_online_recipient_columns.py`.
Regressione: `backend/tests/ruolo/test_tributi_api.py`.
Coverage dei due file runtime modificati: 100%.
Ruff e ratchet complessità passano. Il parser passa da CC 23 / cognitiva 28
a CC 22 / cognitiva 26; helper nuovo CC 6 / cognitiva 7.

Questo documento descrive la correzione e la procedura, non attesta il deploy
o il backfill: l'esito operativo va verificato nei report di applicazione.

## Esito operativo 2026-10-08

Hotfix applicato a backend e worker Poste con immagini derivate dai runtime
live, mantenendo environment e mount e senza ricreare altri servizi.
Entrambi i servizi risultano healthy. Backfill di 1196 righe applicato dopo
simulazione con rollback e verifica fingerprint; controllo dopo commit
superato. CF nel campo indirizzo: 1196 → 0; associazioni rimaste 1044.
Indirizzo, CAP, provincia, comune e campi normalizzati recuperati dal dato
originale; CF e provenienza conservati. Nessun tracking modificato o inventato.

Artefatti persistenti sul server:
`/runtime-data/poste-recovery-backup/Correzione_Poste_20261008`.
Override software: `/opt/gaia/hotfixes/poste-address-20261008/compose.override.json`.
Un deploy successivo deve incorporare la patch o mantenere questo override.
