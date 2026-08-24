# Report batch Demanio_R9 storiche analitiche — 24 agosto 2026 ore 06:00

Batch ID: `398cb756-dc10-4351-844f-c4a9f4a2e0d6`  
Batch sintetiche di attualità completato di riferimento: `e3862317-8fa4-46fd-8c2b-23da253c40ef`  
Origine dati: server `serverCed`, container PostgreSQL `gaia-postgres`, DB `naap`.

## Stato complessivo

- **Stato batch:** `processing`
- **Operazione corrente:** `Lavorazione Marrubiu Fg.12 Part.710`
- **Avvio batch:** `2026-08-23 16:01:40.25861+00` (18:01:40 CEST)
- **Completamento batch:** non ancora completato
- **Totale richieste:** 3.359
- **Completate:** 174 / 3.359 (**5,18%**)
- **Failed:** 7
- **Skipped:** 0
- **Not found:** 0
- **Pending DB:** 3.177
- **Processing:** 1
- **In coda SISTER (`sister_remote_state = pending`):** 1

Distribuzione richieste per stato:

| Status | Codice errore | Conteggio |
|---|---:|---:|
| pending | — | 3.177 |
| completed | — | 174 |
| failed | `flow_failed` | 6 |
| failed | `retry_exhausted` | 1 |
| processing | — | 1 |

Distribuzione `sister_remote_state`:

| Remote state | Conteggio |
|---|---:|
| `none` | 3.184 |
| `downloaded` | 174 |
| `pending` | 1 |

## Velocità e stima completamento

- **Completate nell'ultima ora:** 68
- **Velocità corrente:** circa **68 richieste/ora** (**1,13 richieste/minuto**)
- **Richieste ancora da lavorare** (`pending + processing`): 3.178
- **Stima ore rimanenti alla velocità corrente:** circa **46,74 ore**
- **ETA indicativa:** circa 1 giorno e 23 ore dopo le 06:00 CEST del 24 agosto 2026, quindi intorno al **26 agosto 2026 ore 04:45 CEST**, se la velocità resta costante e senza ulteriori retry/blocchi.

Ultime 10 richieste completate:

| Riga | Comune | Foglio | Particella | Processed at UTC |
|---:|---|---:|---:|---|
| 181 | Marrubiu | 12 | 707 | 2026-08-24 03:59:35.892489+00 |
| 180 | Marrubiu | 12 | 705 | 2026-08-24 03:58:59.675464+00 |
| 179 | Marrubiu | 12 | 702 | 2026-08-24 03:58:47.42391+00 |
| 178 | Marrubiu | 12 | 695 | 2026-08-24 03:58:35.249605+00 |
| 176 | Marrubiu | 12 | 687 | 2026-08-24 03:41:22.832621+00 |
| 175 | Marrubiu | 12 | 673 | 2026-08-24 03:41:10.934031+00 |
| 174 | Marrubiu | 12 | 664 | 2026-08-24 03:39:49.262675+00 |
| 173 | Marrubiu | 12 | 657 | 2026-08-24 03:39:19.587885+00 |
| 172 | Marrubiu | 12 | 642 | 2026-08-24 03:39:07.736692+00 |
| 171 | Marrubiu | 12 | 637 | 2026-08-24 03:38:38.306555+00 |

## Worker

- **Container worker:** `gaia-elaborazioni-worker-visure`
- **Stato container:** `Up 7 hours`
- Il worker risulta quindi attivo al momento del controllo.

## Dettaglio failed

Totale failed: **7**.

| Riga | Comune | Foglio | Particella | Codice errore | Messaggio | Processed at UTC |
|---:|---|---:|---:|---|---|---|
| 41 | Marrubiu | 6 | 971 | `flow_failed` | Automatic CAPTCHA exhausted; manual CAPTCHA response missing | 2026-08-23 16:44:59.812916+00 |
| 65 | Marrubiu | 8 | 427 | `flow_failed` | Automatic CAPTCHA exhausted; manual CAPTCHA response missing | 2026-08-23 17:21:08.891149+00 |
| 82 | Marrubiu | 8 | 519 | `flow_failed` | Automatic CAPTCHA exhausted; manual CAPTCHA response missing | 2026-08-23 17:56:01.59201+00 |
| 87 | Marrubiu | 8 | 541 | `flow_failed` | Automatic CAPTCHA exhausted; manual CAPTCHA response missing | 2026-08-23 18:21:13.528337+00 |
| 99 | Marrubiu | 8 | 571 | `retry_exhausted` | Numero massimo di tentativi SISTER raggiunto (50) | 2026-08-24 02:24:28.991383+00 |
| 104 | Marrubiu | 12 | 221 | `flow_failed` | Automatic CAPTCHA exhausted; manual CAPTCHA response missing | 2026-08-24 02:42:15.773831+00 |
| 177 | Marrubiu | 12 | 691 | `flow_failed` | Automatic CAPTCHA exhausted; manual CAPTCHA response missing | 2026-08-24 03:58:22.342292+00 |

Cause aggregate:

- **6** richieste fallite per esaurimento automatico del CAPTCHA senza risposta manuale (`flow_failed`).
- **1** richiesta fallita per esaurimento del numero massimo di tentativi SISTER (`retry_exhausted`, 50 tentativi).

## Richieste in coda SISTER (`queued_sister`)

- `sister_remote_state = pending`: **1** richiesta.
- `sister_remote_state = downloaded`: **174** richieste.
- `sister_remote_state = none`: **3.184** richieste.

Interpretazione operativa: al momento del controllo c'è **1 richiesta ancora in attesa di essere ripresa/scaricata da SISTER**; la gran parte delle richieste non ha ancora uno stato remoto SISTER valorizzato perché è ancora pending/da processare lato batch.

## Note operative

- Il batch è ancora in lavorazione e sta procedendo su **Marrubiu, foglio 12**.
- I log recenti mostrano completamento PDF riuscito per la riga 181 / particella 707 alle `03:59:35 UTC`, con persistenza del risultato `status=completed`.
- Subito dopo il worker ha iniziato la riga 182 / particella 710, riutilizzando la sessione SISTER esistente.
- Nei log finali del campione si osserva un CAPTCHA rifiutato al primo tentativo per la richiesta corrente, seguito dall'avvio del secondo tentativo. Questo è coerente con le cause di alcuni failed già registrati (`flow_failed` per esaurimento CAPTCHA), ma il worker risulta ancora attivo.
- Non emergono dal controllo segnali di container fermo; il principale fattore operativo da monitorare resta l'affidabilità del CAPTCHA/SISTER e l'eventuale accumulo di failed per retry esauriti.
