# AutoSync SISTER: diagnosi e interventi del 28 settembre 2026

## Evidenze sul CED

Indagine in sola lettura alle 11:15-11:30 Europe/Rome. Nessun login aggiuntivo
verso SISTER e nessuna modifica di password, account o calendario.

Carlo: ultimo PDF osservato il 26/09 alle 07:32 locali, ultimo controllo
autenticazione riuscito alle 08:52. Marika: ultimo PDF l'08/09 alle 07:28,
ultimo controllo autenticazione riuscito alle 07:25. La telemetria conservata
permette di datare l'assenza di resa, non l'inizio certo della causa attuale.

Gli artifact `final-failed.html` delle ultime richieste dei due account
mostrano entrambi la pagina Uscita con:

> Utente non abilitato, per accedere ai servizi occorre essere registrati.

**Non e dimostrato un cambio password.** La diagnosi corretta e account non
abilitato ai servizi secondo la risposta del portale, da verificare con il
responsabile delle abilitazioni. `updated_at` GAIA risale al 3 settembre per
entrambi e non rappresenta un audit delle password sul portale esterno.

Nelle 24 ore della prima lettura: 505 PDF, 455 errori login (358 sui due
account senza resa), 1.232 poll su 28 richieste. I due account consumano circa
6,6 ore aggregate in login falliti; non sono ore di fermo del sistema.
Un successivo report su una finestra scorrevole leggermente diversa misura
circa 8,2-10,9 PDF per ora programmata sui quattro account produttivi.
Il settimo profilo non presenta attivita nel campione; il limite effettivo
e sei browser simultanei. La sospensione deve liberare il posto browser,
altrimenti un account senza resa continua a sottrarre capacita al pool.

### Submit non avanzato

Nel campione piu recente, l'artifact mostra:

> La sezione e obbligatoria per il comune specificato.

Il menu offre tre valori, A, B e C. Il recupero esistente seleziona
automaticamente soltanto un'unica opzione certa: qui il rifiuto di scegliere
arbitrariamente e corretto. La richiesta va arricchita con la sezione canonica
dal dato sorgente e poi rivalutata. Non estendere la diagnosi a tutti i 148
fallimenti di submit senza esaminare i rispettivi artifact. Il messaggio
`classification=current` dell'audit AdE non dimostra che il form sia valido.

## Modifiche preparate nel checkout

- Controllo autenticazione AutoSync prima del claim della visura: un login
  fallito non consuma tentativi delle richieste e non accoda nuovi submit.
- Stato del controllo persistito in `sister_portal_events` con tipo
  `authentication_gate`, motivo strutturato, durata e numero di errori
  consecutivi. Password e messaggi HTML non sono persistiti in questi eventi.
- Due prime attese da 180 secondi; dal terzo errore pausa di 15 minuti,
  poi 30 e massimo 60 minuti. Alla scadenza una prova di autenticazione;
  il successo azzera il contatore. I valori sono una policy iniziale da
  monitorare, non una modifica alle impostazioni delle credenziali.
- La sospensione termina il runner e rilascia browser e lease. Il refresh
  del pool/successivo ciclo worker rivaluta la scadenza senza aprire browser
  per gli account ancora sospesi.
- Oltre alla lease esistente, la prova usa un advisory lock transazionale
  PostgreSQL sullo username. Il controllo viene riletto dopo il lock;
  due runner non possono effettuare la prova contemporaneamente. Un errore
  di storage impedisce il claim: non si procede senza la protezione.
- La pagina con utente non abilitato riceve una diagnosi esplicita.
  Le altre categorie conservano i controlli di autenticazione esistenti.
- Poll remoto a 5 minuti nella prima ora, 10 nella seconda, 20 in seguito;
  ritorno a 5 minuti nell'ultima ora della deadline, senza oltrepassarla.
  Nessun rinnovo del primo invio, sostituzione di ID o reinvio remoto.
- I claim ordinano prima le richieste con primo invio piu vecchio, poi
  l'ordine di riga, conservando filtri di pinning, retry e lock esistenti.
- Le eccezioni previste di documento non pronto sono eventi `waiting`,
  senza essere classificate come guasto del portale.

Il controllo preventivo si applica a `perpetual_sync` e `ruolo_autosync`.
La policy di recupero remoto e condivisa anche dai batch manuali.
Le modifiche sono locali: questa attivita non esegue il deploy sul CED.

## Misure ripetibili

`scripts/sister_autosync_efficiency.py` produce JSON per account. Eseguire
con l'ambiente backend e `PYTHONPATH=backend`:

```sh
python scripts/sister_autosync_efficiency.py --user-id 1 --hours 24
```

Il comando imposta `SET TRANSACTION READ ONLY`. Filtra campagna, utente,
credenziali e intervallo, e non legge o stampa password. Espone:

- PDF unici per richiesta e PDF per ora programmata;
- tempo dentro e fuori fascia, con granularita di confine al minuto;
- durate osservate di login, lavoro di polling e cooldown, ritagliate alla
  fascia e unite per evitare doppio conteggio nella stessa categoria;
- attesa remota osservata fra evento polling `waiting` e successivo avvio
  o download della richiesta. Senza nuovi eventi affidabili il valore e
  `null`, non zero.

Le categorie possono sovrapporsi e non vanno sommate. La configurazione
usata e quella corrente: cambi storici delle fasce o dell'abilitazione non
sono ricostruibili. La disponibilita da calendario non equivale a disponibilita
da lease: il report segnala esplicitamente l'occupazione lease come ignota.
Un username duplicato nei profili e rifiutato per non gonfiare il denominatore.
I vecchi cooldown possono avere attribuzione incompleta; il nuovo evento
di autenticazione registra invece direttamente la credenziale interessata.

## Domenica / lunedi

La domenica `00:00-00:00` significa tutto il giorno, ma non crea una coda
notturna sul lunedi. Il lunedi `15:00-07:30` inizia alle 15:00. Pertanto
esiste realmente un intervallo di 15 ore tra fine domenica e ripresa.

Soluzione proposta, subordinata alla compatibilita con l'uso umano: aggiungere
al lunedi la fascia `00:00-07:30` nei soli profili AutoSync autorizzati,
conservando `15:00-07:30`. Non modificare la semantica globale dei calendari
o le fasce delle elaborazioni manuali. Conferma sull'uso umano richiesta;
configurazione di produzione lasciata invariata in attesa della risposta.

I quattro recuperi presenti nella fotografia hanno ancora la richiesta remota
originale. Il piu vecchio scade il 28/09 alle 16:17 locali: la deadline rimane
assoluta e non viene estesa per compensare le fasce.

## Verifica e rollout

Test mirati: persistenza della sospensione tra istanze, mancato consumo delle
richieste, singola prova e reset del contatore, rilascio dello slot, scadenza
del polling, priorita della richiesta originale, classificazione delle attese,
unione degli intervalli e accesso read-only del report.

Il lock e stato verificato anche su PostgreSQL del CED, con chiave casuale
di verifica: prima transazione ammessa, seconda respinta, ammissione dopo
rollback della prima. Nessuna riga modificata o account reale bloccato.

Prima della distribuzione verificare coverage e quality ratchet, poi osservare
una fascia completa: assenza di tentativi visura durante sospensione,
ripresa dopo la prova, slot liberati, nessun doppio invio e PDF/ora programmata.
Le failure legacy e le modifiche concorrenti nel working tree devono restare
visibili nei risultati dei gate, senza assorbirle nella baseline.

### Esito delle verifiche locali

- Suite worker eseguita con `make test-worker`, isolamento per file: superata.
- Coverage finale statement e branch: 100% su `worker.py`,
  `browser_session.py`, `sister_auth_gate.py`, `sister_observability.py`,
  `sister_recovery_policy.py`, `sister_worker_reliability.py` e sul report
  `scripts/sister_autosync_efficiency.py`. I rerun mirati completano la
  copertura delle modifiche successive al primo passaggio della suite.
- Ruff sul runtime interessato e formatter sui file nuovi: superati.
- `git diff --check`: superato.
- Quality ratchet contro `origin/main`, merge-base
  `c42bea845fa0de39f8bd9d8f067747a32e237b5b`: **non superato**.
  Oltre alle differenze gia presenti rispetto alla baseline, questa modifica
  portava `sister_worker_reliability.py` da 797 a 800 LOC metriche.
  Il follow-up autorizzato elimina il flag derivato duplicato di `_ClaimScan`:
  file a 798 LOC, ratchet di questo file superato, priorita CAPTCHA e minimo
  retry invariati anche con ritardo zero. Il ratchet dei sei runtime SISTER
  passa da 15 a 14 rilievi: resta non superato, incluso il classificatore
  login che aggiunge 2 LOC. La baseline non e stata modificata; la rimozione
  del singolo blocco file-level non rende pronta al rilascio l'intera change.

Commit richiesto dopo la verifica del contenuto staged in un checkout
temporaneo, separato dalle modifiche concorrenti Poste/Accessi/Ruolo.
Verifica finale del contenuto da committare: `make test-worker` supera
676 test in 46 file isolati; i sei runtime worker modificati sono al 100%
statement e branch. Il report supera anche 6 test dedicati con coverage
100%. Il totale worker resta al 99% per file esterni a questa modifica:
non viene dichiarata coverage globale del repository al 100%.
I test del checkout isolato usano `DATABASE_URL=sqlite://` e una chiave JWT
fittizia: non dipendono dai segreti locali. Nessun deploy; calendari invariati.
Il commit conserva esplicitamente il blocco del ratchet complessivo e non
costituisce approvazione al rilascio.

Riferimenti: [analisi iniziale](SISTER_AUTOSYNC_EFFICIENCY_ANALYSIS_2026-09-25.md),
[campagna continua](CATASTO_CONTINUOUS_SYNC.md),
[runbook](SISTER_debug_runbook.md).
