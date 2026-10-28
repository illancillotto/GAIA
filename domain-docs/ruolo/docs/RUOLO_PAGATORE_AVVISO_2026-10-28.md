# Pagatore diverso dall'intestatario dell'avviso

## Flusso implementato

Nel dettaglio Tributi, il riquadro **Pagatore diverso dall'intestatario** permette
di collegare un soggetto gia presente nell'anagrafica GAIA tramite CF/P.IVA.
I motivi ammessi sono `decesso` (erede), `vendita` (acquirente) e `ufficio`.
Il pagatore deve differire dall'intestatario. Un soggetto assente deve essere
inserito da Utenze prima del collegamento; il servizio non crea anagrafiche.

L'assegnazione riguarda il singolo avviso. Sostituirla o rimuoverla conserva
lo storico, con autore e data di creazione/annullamento. L'indice parziale
`uq_ruolo_payer_assignment_active` ammette una sola assegnazione attiva per
avviso; il motivo e vincolato anche nel database.

La selezione del lotto avviene per intestatario originale. Gli avvisi assegnati
sono poi separati e raggruppati per pagatore all'interno del candidato originale:
gli altri avvisi restano all'intestatario. Le eventuali separazioni inCASS
restano applicate dopo la riassegnazione. Denominazione, CF, indirizzo e cartella
archivio del destinatario provengono dall'anagrafica del pagatore. Il riepilogo
conserva il riferimento all'intestatario originale e indica erede/acquirente
quando pertinente; importi e avvisi originari non vengono riscritti.

Gli accessi al portale sono acquisiti **dopo** la riassegnazione, usando il CF
del destinatario effettivo. PIN cifrati nello snapshot; una sola coppia univoca
Codice ditta/PIN viene stampata. Le sei utenze ambigue restano sospese e usano
il messaggio per contattare gli uffici.

Il flusso della pagina Tributi usa i lotti anche per l'anteprima di un solo
destinatario. Il generatore DOCX singolo legacy non applica la riassegnazione:
per questi avvisi usare anteprima/generazione a lotti della pagina Tributi.

## API e autorizzazioni

Tutte le route richiedono autenticazione, modulo `ruolo` e sezione
`ruolo.tributi.view`:

| Metodo | Percorso | Comportamento |
| --- | --- | --- |
| GET | `/ruolo/tributi/avvisi/{id}/payer` | Assegnazione attiva e storico |
| PUT | stesso percorso | Collega/sostituisce; richiede `ruolo.tributi.manage_status` |
| DELETE | stesso percorso | Annulla l'assegnazione; stesso permesso di modifica |

Avviso inesistente: HTTP 404. CF assente, intestatario gia coincidente o motivo
non valido: HTTP 422. Un utente con sola lettura puo consultare ma non modificare.
Il componente frontend non effettua richieste senza sessione e non salva se la
sessione scade prima dell'azione.

## Migrazioni e bozze

- `20261027_0900`: tabella `ruolo_tributi_payer_assignments`, vincoli e indici.
- `20261028_0900`, successiva a `20261027_1300`: trigger PostgreSQL di revisione
  sull'assegnazione, attivi anche in modalita replica. Insert/update/delete e
  truncate invalidano la revisione al commit. Una bozza preparata prima del
  cambio pagatore non puo essere confermata: occorre rigenerarla.

Il downgrade `20261028_0900` rimuove soltanto i trigger aggiunti; non cancella
assegnazioni. Su SQLite la migrazione dei trigger e un no-op. La verifica della
concorrenza e dell'invalidazione usa PostgreSQL con schemi temporanei isolati.
Questo ciclo non applica migrazioni o deploy al server degli uffici.

## Importazione CSV

```bash
python -m app.scripts.import_payer_assignments /percorso/pagatori.csv
python -m app.scripts.import_payer_assignments /percorso/pagatori.csv --apply
```

Intestazioni con separatore `;`: `avviso_id;avviso;cf_pagatore;motivo;note`.
`avviso_id` e l'UUID GAIA; `avviso` e il riferimento usato nel report. Senza
`--apply` la transazione viene annullata. Le assegnazioni gia attive allo stesso
pagatore sono saltate; soggetti non trovati e errori di dominio sono riportati
senza creare collegamenti. Una riga con UUID non valido interrompe il comando:
la transazione non viene confermata. Nessun CSV reale o credenziale va versionato.

## Contratti di test

- `test_payer_assignments.py`: collegamento, sostituzione/storico, rimozione,
  vincoli di dominio, autorizzazioni, candidati, stampa e import dry-run/apply.
- `test_payer_revision_postgres.py`: cambio pagatore dopo preparazione e rifiuto
  della conferma, invalidazione update/delete/truncate anche in replica,
  downgrade e compatibilita SQLite.
- `test_notice_register.py`: un documento intestato al pagatore assegnato non
  e classificato come destinatario discordante.
- `ruolo-payer-assignment-card.test.tsx`: operazioni, storico, errori,
  normalizzazione CF e sessione assente/scaduta.

I risultati finali del ciclo sono registrati in `PROGRESS_ruolo.md`.
