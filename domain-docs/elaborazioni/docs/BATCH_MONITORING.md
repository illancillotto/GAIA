# Monitoraggio batch e utilizzo credenziali

La modal di dettaglio in `/elaborazioni` e la pagina
`/elaborazioni/batches/{id}` condividono `ElaborazioneBatchDetailWorkspace`.

## Righe del batch

- La colonna `Credenziale` mostra l'etichetta del profilo indicato da
  `sister_credential_id`, risolta nelle statistiche del lotto. Non deduce nomi
  da username o identificatori. Senza assegnazione mostra `Non assegnata`;
  senza metadati mostra `Credenziale non disponibile`.
- Le righe sono ordinate per `processed_at` decrescente, usando `created_at`
  quando manca la data di elaborazione. A parita di data prevale il numero
  riga maggiore. Le date con fuso diverso sono confrontate come istanti.
- Filtri e aggiornamenti websocket conservano questo ordine. La tabella
  rappresenta lo stato corrente delle richieste, non ogni singolo tentativo
  storico; l'ordinamento non modifica i dati ricevuti dall'API.

## Contatori per credenziale

Il dettaglio API espone `statistics.credentials_used`:

| Campo | Etichetta UI | Significato |
| --- | --- | --- |
| `request_count` | richieste distinte | ID richiesta distinti negli eventi della credenziale, uniti alle richieste attualmente assegnate al profilo |
| `execution_count` | avvii elaborazione | Eventi `execution_start`; per lo storico senza telemetria il minimo resta `request_count` |
| `completed_count` | visure completate | Richieste attualmente `completed` attribuite alla credenziale finale tramite `sister_credential_id` |

Una richiesta trasferita fra profili puo contribuire a piu conteggi di
richieste/avvii, ma la visura completata viene attribuita una sola volta alla
credenziale finale. Fallite, saltate, non trovate e richieste ancora in corso
non contribuiscono alle visure completate. Richieste storiche completate senza
credenziale non vengono attribuite artificialmente: la somma per profilo puo
quindi essere inferiore al totale completato del batch.

Esempio: `Alessandro · 215 richieste distinte · 706 avvii elaborazione`
non significa 706 PDF ottenuti. Il contatore separato `visure completate`
misura le richieste concluse con successo, non il numero di file fisici.
Con un backend precedente che non espone il nuovo campo, la UI mostra `—`
invece di inventare un conteggio zero. Nessuna migration DB e necessaria.

## Verifica della change del 2026-09-09

- Backend: 32 test; servizio statistiche e schema Catasto al 100% di statement
  e branch (`511` statement, `60` branch).
- Frontend: 37 test; modal completa e pannello statistiche al 100% di
  statement (`379`), branch (`359`), funzioni (`109`) e righe (`336`).
- Coperti ordinamento dopo refresh e filtri, attribuzione dopo cambio
  credenziale, assenza di metadati, download e relativi errori, CAPTCHA,
  scadenza della sessione e risposte preview concorrenti durante refresh.
- Ratchet contro il merge-base `f1875ee8`: nessun finding. Modal: LOC
  `808 -> 798`, ciclomatica massima `182 -> 177`, cognitiva massima
  `222 -> 216`. Rimosso il pulsante PDF duplicato e il controllo non
  raggiungibile dal relativo contratto UI; API e workflow restano invariati
  salvo il nuovo contatore di risposta.
- Coverage senza nuove esclusioni o soglie ridotte. Report locali:
  `/tmp/gaia-batch-full-coverage`, `/tmp/gaia-batch-backend-coverage.json`.
- Chromium: due test desktop `1440x1000` e mobile `390x844`, con API simulate
  e componenti reali, verificano nomi, contatori e ordine senza errori JavaScript.
- TypeScript, ESLint mirato, `make lint-backend` e `make quality-test`
  (`69 passed`) passano. `complexity-baseline` rifiuta la sincronizzazione
  globale per debito fuori perimetro gia presente prima della change;
  `complexity-baseline-verify` resta non riproducibile. Baseline invariata:
  non si assorbono regressioni estranee per rendere verde il programma globale.

Suite backend: `test_elaborazioni_batch_statistics.py`,
`test_elaborazioni_sister_coverage.py`, `test_elaborazioni_credential_schedule.py`,
`test_catasto_batch_response_contract.py`.
Suite frontend: `batch-detail-interactions.test.tsx`,
`batch-statistics.test.tsx`, `elaborazioni-batch-detail-workspace.test.ts`.
