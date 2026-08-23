# GAIA/SISTER — Demanio_R9 analisi 21 failed

Data: 2026-08-23 12:00 CEST circa
Target: `serverCed` / batch `Demanio_R9` (`e3862317-8fa4-46fd-8c2b-23da253c40ef`)
Scope: sola lettura su DB PostgreSQL e output monitor.

## Stato batch verificato

```text
status: failed
total_items: 3359
completed_items: 3338
failed_items: 21
skipped_items: 0
current_operation: Batch terminato
completed_at: 2026-08-23 09:53:45 UTC
```

Distribuzione richieste:

```text
completed: 3338
failed: 21
```

## Breakdown dei 21 failed

```text
16 failed / attempts=2 / flow_failed / Fallita
   error_message: Automatic CAPTCHA exhausted; manual CAPTCHA response missing

5 failed / attempts=5 / retry_exhausted / Retry SISTER esauriti
   error_message: Numero massimo di tentativi SISTER raggiunto (5)
```

## Interpretazione

### 16 CAPTCHA/manual timeout

Queste richieste sono finite failed perché il worker è arrivato a CAPTCHA manuale ma non ha ricevuto una soluzione entro la finestra prevista.

Esempio: riga 186 con immagine CAPTCHA salvata in container:

```text
/data/catasto/captcha/e3862317-8fa4-46fd-8c2b-23da253c40ef/abc51738-3384-405e-92e1-0e41823ca24f_manual_1.png
```

La patch applicata evita il fallimento immediato se il CAPTCHA inserito è sbagliato e SISTER ne genera uno nuovo; però se non arriva nessun input manuale prima del timeout, la richiesta finisce ancora `failed`.

### 5 retry exhausted

Queste richieste sono arrivate al limite massimo di 5 tentativi SISTER. Non sono classificate come CAPTCHA manuale mancante, ma come esaurimento retry del worker/portale.

Righe campione viste:

```text
290, 302, 966, 1977, 3268
```

## Conclusione

Il recupero ha funzionato sul grosso del batch:

```text
prima del recupero: 3076 completed, 171 failed, 112 skipped
dopo recupero:      3338 completed, 21 failed, 0 skipped
```

Sono stati quindi recuperati/completati ulteriori 262 PDF.

Restano 21 richieste recuperabili da valutare con reset mirato:

- 16 da CAPTCHA manuale non compilato in tempo;
- 5 da retry esaurito.

## Prossima azione consigliata

Non rilanciare tutto il batch indiscriminatamente. Fare invece:

1. reset mirato delle 16 righe CAPTCHA manual timeout a `pending`;
2. valutare separatamente le 5 `retry_exhausted` e resettarle solo se i log confermano errore transitorio SISTER/worker;
3. riprendere con monitor CAPTCHA manuale attivo e risposta rapida alle immagini.

Nessuna modifica DB o restart è stata eseguita durante questa analisi.
