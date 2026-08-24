# GAIA/SISTER — Deploy Agent CAPTCHA server-side e monitor Demanio_R9

Data: 2026-08-22

## Esito sintetico

- Commit locale: `553677b7 fix: run SISTER captcha through server agent`
- Deploy su `serverCed`: completato per backend, frontend e `elaborazioni-worker-visure`.
- Batch: `Demanio_R9` (`e3862317-8fa4-46fd-8c2b-23da253c40ef`) rilanciato.
- Monitor automatico: attivo ogni 15 minuti, job `e89baebd6156`.

## Verifiche deploy

Servizi verificati su `serverCed`:

```text
gaia-backend: healthy
gaia-frontend: healthy
gaia-elaborazioni-worker-visure: up
```

Build/deploy eseguito con:

```text
docker compose up -d --build backend frontend elaborazioni-worker-visure
docker compose up -d --build elaborazioni-worker-visure
```

## Correzione post-monitor

Durante il primo run post-deploy il monitor ha intercettato un errore reale: `Visure/SelezioneConvenzione.do` era ancora classificata `not ready` per via dell'ordine dei check in `is_visura_area_ready`.

Azioni:

- worker fermato subito;
- batch messo in pausa;
- test RED aggiunto su `Visure/SelezioneConvenzione.do`;
- fix applicato ordinando prima i ready-state specifici `/Visure/...`;
- test GREEN:

```text
28 passed, llm_captcha_solver.py 100%
55 passed
```

- commit amend: `553677b7`;
- worker ricostruito e rilanciato.

## Stato batch dopo rilancio finale

Ultima verifica DB su `serverCed`:

```text
processing	3359	60	0	0	Completata riga 62
awaiting_captcha	1
completed	60
pending	3295
processing	3
```

Interpretazione:

- batch in lavorazione;
- PDF completati: 60 / 3359;
- failed: 0;
- skipped: 0;
- 3 richieste in processing;
- 1 richiesta in attesa CAPTCHA/gestione Agent nel flusso.

## Evidenza CAPTCHA Agent

Log worker osservati dopo fix:

```text
LLM CAPTCHA solver raw='...' normalized='...'
Invio candidato CAPTCHA con N caratteri
CAPTCHA accettato da SISTER
Richiesta ... CAPTCHA Agent (...) terminale status=completed
Richiesta ... completata con status=completed errore=None
```

Quindi Agent server-side nel container sta risolvendo CAPTCHA e SISTER li sta accettando.

## Monitor automatico

Creato script:

```text
/home/cbo/.hermes/scripts/gaia_sister_demanio_r9_watch.sh
```

Cron Hermes:

```text
job_id: e89baebd6156
schedule: every 15m
mode: no_agent
```

Il monitor resta silenzioso se il batch è `processing` con `failed=0` e `skipped=0`. Invia alert in chat se il batch esce da `processing` o se compaiono failed/skipped.

## Note

- I 10 failed generati dal primo run post-deploy sono stati reset a pending dopo aver corretto il ready-state, perché erano introdotti dal bug appena diagnosticato e non erano fallimenti definitivi SISTER.
- Nessun token/password/connection string è riportato nel report.
