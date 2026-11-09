# SISTER: verifica operativa del 27 ottobre 2026

## Esito

Verifica CED in sola lettura fra le 10:45 e le 10:47 UTC (11:45-11:47 italiane).
Il worker `gaia-elaborazioni-worker-visure` e healthy, con heartbeat aggiornato
(eta 5,7 secondi al campionamento), lease credenziale valida e richieste reali
in avanzamento. Non e stato riavviato e non sono state accodate visure di prova.

Alle 10:45 UTC nelle ultime 24 ore risultano 190 richieste `completed` e
14 `failed`. Durante l'audit i successi nell'ora corrente passano da 24 a 25:
la verifica comprende quindi un nuovo completamento, non solo lo stato del
processo. Il batch perpetual `92a8816d-114a-4f9b-8ad2-fe25f46f0979` e in corso,
con 17.248 elementi totali, 16.151 completati e 1.078 falliti al primo
campionamento. Questi ultimi sono cumulativi del batch, non tutti di oggi.

## Errori e limiti osservati

- Dodici fallimenti nelle ultime 24 ore riguardano CAPTCHA non risolti o
  rifiutati dal portale. I log dell'ultimo caso mostrano tentativi esauriti;
  il fallback esterno non e configurato e quello manuale e disabilitato.
- Due richieste hanno codice `sister_recovery_review_required`: restano in
  revisione, senza conversione automatica in successo o ripetizione arbitraria.
- Restano richieste pendenti; tre batch manuali sono `pending` con operazione
  `Awaiting start`, mentre il batch perpetual continua. La verifica non li
  avvia e non modifica la priorita o l'ownership delle richieste.

I vecchi connection test falliti del 1-2 ottobre non descrivono l'autenticazione
corrente: il worker riusa una sessione valida e completa richieste durante il
controllo. Non e stata diagnosticata un'indisponibilita generale del portale.
I 14 errori restano problemi reali delle singole richieste, quindi la salute
Docker non va presentata come assenza di errori applicativi.

## Metodo e riferimenti

Controllati stato Docker, heartbeat, lease, aggregati delle richieste per stato,
ultimi batch, codici errore e log recenti. Le query non estraggono password,
contenuti delle visure o dati anagrafici. Nessun nuovo codice runtime o test
artificiale introdotto per questa verifica.

Per il flusso operativo vedere [SISTER_debug_runbook.md](SISTER_debug_runbook.md).
La supervisione dei blocchi descritta in
[SISTER_WORKER_STALL_FIX_2026-10-06.md](SISTER_WORKER_STALL_FIX_2026-10-06.md)
resta un intervento distinto: questa verifica non dichiara distribuito quel fix.
