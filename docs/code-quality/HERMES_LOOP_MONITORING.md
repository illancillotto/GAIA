# Hermes Loop - solo monitoraggio

## Perche non usarlo per il refactoring

`/loop` esegue turni a intervallo. La riduzione della complessita e invece un
workflow causale con verifiche, decisioni e una definition of done: usare
`/goal` evita che un timer inizi un secondo refactoring mentre il primo e ancora
da revisionare.

## Uso ammesso

Usare `/loop` per controllare uno stato esterno dopo che il codice e gia stato
preparato, per esempio una CI o una review. Esempio, solo quando la CI e
operativa e il branch e stato pubblicato intenzionalmente:

```text
/loop 5m Controlla lo stato delle verifiche della pull request GAIA corrente. Non modificare codice, workflow, branch, baseline o impostazioni GitHub. Riporta solo cambiamenti di stato e failure con link/evidenza. Termina con LOOP_COMPLETE quando tutte le verifiche richieste sono concluse con esito definitivo. --times 12 --until tutte le verifiche richieste della pull request hanno un esito definitivo
```

Comandi di controllo:

```text
/loop status
/loop pause
/loop resume
/loop stop
```

Non usare un loop per:

- scegliere autonomamente hotspot successivi;
- rigenerare baseline;
- correggere in serie failure diverse;
- fare commit o push periodici;
- aspettare una CI non disponibile per billing o configurazione.

Se l'obiettivo e lavorare fino a un risultato tecnico, usare `/goal`. Se
l'obiettivo e osservare periodicamente uno stato esterno, usare `/loop`.
