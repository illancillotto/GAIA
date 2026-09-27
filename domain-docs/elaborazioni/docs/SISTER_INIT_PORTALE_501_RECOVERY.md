# SISTER initPortale HTTP 501

Il `501` restituito da `/portale-rest/rs/initPortale` e un errore HTTP reale,
ma non implica sempre che il login SISTER sia fallito. Il worker distingue i
seguenti casi:

- Se la pagina e la Home dei Servizi e mostra `Consultazioni e Certificazioni`,
  il `501` e non bloccante: il worker continua senza refresh.
- Se il `501` interrompe il login e la pagina non segnala sessione bloccata o
  credenziali rifiutate, il worker aggiorna **una sola volta** la pagina. Prosegue
  solo se dopo il refresh la Home o l'informativa privacy sono pronte e l'area
  visure si apre correttamente.
- Se il `501` arriva sulla pagina `Utente bloccato / gia' in sessione`, non
  viene fatto refresh: il worker usa il recupero sessione gia' esistente
  (chiusura sessione, attesa e un solo nuovo login). Un secondo blocco fallisce
  come `SISTER_SESSION_LOCKED`, senza ulteriori recovery.
- Se il refresh scade o la pagina resta non pronta, resta valido l'errore
  originale e il normale cooldown/retry del worker decide quando riprovare.
  Non viene inviata alcuna visura durante il recupero del login.

La prova controllata del 2026-09-27 ha osservato 15 login con `501` non
bloccante; un refresh sulla Home ha mantenuto accessibile l'area visure. Non e
stata ancora osservata dal probe una sessione bloccante recuperata dal refresh.
La regola di recupero e quindi prudenziale e limitata a un solo tentativo.
