# Personale Reparto Impianti — profilo Tecnico/Turnista

## Stato

Applicato in produzione il **07/10/2026**, con autorizzazione esplicita
«si procedi»: gateway sul VPS `gate`, backend e servizi GAIA sul master.
Importati 29 profili dal 01/01/2026, corretti 14 operatori e la squadra in area
IMPIANTI, aggiunte 8 membership. Secondo dry-run: zero ulteriori modifiche.
Manifest, backup, log e pacchetto mirato restano privati e fuori da Git.
Le modifiche al frontend GAIA sono verificate localmente; la console GATE
rilasciata mostra il nuovo profilo e i dettagli. Il frontend GAIA in produzione
usa un checkout precedente e non è stato sovrascritto.

## Fonte e decorrenza

Fonte: `Elenco Personale Reparto Impianto 2026.pdf`, fornito dall'utente.
Responsabile attestato: Massimiliano Sanna. Decorrenza confermata: **01/01/2026**,
senza scadenza inventata. Il documento comprende 29 persone: 26 tecnici/turnisti,
1 capo reparto/tecnico e 2 capi reparto; 17 rapporti indeterminati, 3 determinati
e 9 avventizi. I nomi canonici rimangono quelli già presenti in GAIA; le
abbreviazioni e i refusi del PDF sono conservati solo nell'artefatto di revisione.
Non viene creato o modificato alcun mapping GAIA–INAZ.

## Profilo e calcolo della giornata

`tecnico_turnista`, etichetta **Tecnico/Turnista**, è un profilo distinto per gli
operai degli Impianti, limitato alle 26 persone attestate e alle date di validità.
La tabella GAIA `presenze_personnel_profiles` conserva mansione, rapporto di
lavoro, area, responsabile, validità e SHA256 del documento. Un'importazione
INAZ non sostituisce queste attestazioni.

- Giornate OPE riconosciute: calendario ordinario, **1° e 3° sabato del mese**.
  Il codice effettivo mantiene la durata prevista: OPE feriale 7 ore, OPESAB
  6h30 e varianti estive già supportate. Anche `OPESAC` segue il calendario
  del 1°/3° sabato e le **6h30** confermate dall’utente; il codice e il teorico
  INAZ importati rimangono conservati. Anche un codice OPE feriale su un
  sabato 2/4/5 non crea un teorico ordinario per questo profilo. Una rotazione
  individuale precedente non sostituisce questo calendario attestato.
- Giornate in turno confermate dall'utente: `TELEC_1`, `TELEC_2`, `TELEC_3`,
  `ADD_9`, `IRRSE`, `IRRSEA`. Il teorico è quello **INAZ della giornata**:
  attualmente TELEC 480 minuti, ADD/IRR 420 minuti. L'eccedenza operativa parte
  da quel teorico, senza creare uno straordinario dopo 7 ore in un turno da 8.
- `SMONTO` e `RIPTURN` senza timbrature: riposo, teorico zero.
- Codici nuovi non attestati non diventano automaticamente turni. Teorico INAZ
  mancante o invalido: calcolo bloccante, ordinario/extra non inventati.
- Revoche manuali esplicite sulle giornate di turno restano rispettate. Una
  vecchia assegnazione generica non rende turnista una giornata OPE del tecnico.
- Acquaiolo, Telecontrollo e operai di altri profili conservano le proprie regole.

Le maggiorazioni e il buono pasto usano i percorsi CCNL esistenti. La soglia del
buono rimane almeno 7 ore ordinarie effettive dal 26/08/2026: ferie, extra e ore
oltre un teorico più corto non diventano ore ordinarie per maturarlo. Trasferte
e buoni manuali mantengono la semantica esistente. Il rapporto avventizio resta
un dato HR distinto dal determinato; non viene attivato un motore paghe.

GATE mostra il profilo e, nel dettaglio giornaliero, mansione, rapporto e area.
GAIA pubblica gli stessi dati tramite il builder condiviso LAN/outbound. La
nuova tipologia `tecnico_turnista` è ammessa da schemi e controlli nei due
progetti; le assegnazioni da sole non attestano il codice di turno del tecnico.

## Importazione applicata

Dry-run e applicazione sul master GAIA:

- 29 identità canoniche esistenti verificate; zero cambiamenti del mapping;
- 29 profili datati inseriti;
- 14 operatori corretti da AGRARIO a IMPIANTI;
- squadra esistente Reparto Impianti corretta a IMPIANTI;
- 8 membri mancanti aggiunti con validità dal 01/01/2026;
- responsabilità di Sanna conservata e attestata anche nel profilo; la gestione
  squadra di Pau Marco esistente non viene eliminata.

Le 21 membership già esistenti restano conservate, comprese le loro validità.
Non si inventano dati di gennaio–giugno, attualmente assenti nelle giornaliere
lette; la decorrenza si applicherà anche a nuove importazioni di quei periodi.

## Verifiche

- GAIA: suite profili, regole operai/sabati, turni/CCNL, snapshot e contratti;
  100% statement e branch sugli 11 file backend modificati o nuovi.
- GATE: 97 test del perimetro calendario/export/UI passati prima dell'ultimo
  controtest; 53 test finali dei servizi e 100% statement, branch, funzioni e
  righe sui 5 servizi modificati o nuovi. Test schema condiviso: 6 passati.
- GAIA frontend: 7 test, coverage del perimetro 100%; typecheck GAIA e GATE,
  Ruff ed ESLint mirati passati. I badge riconoscono la nuova tipologia.
- PostgreSQL reale isolato: migrazione idempotente, nuovo vincolo tipo turno,
  downgrade rifiutato se esistono assegnazioni tecnico_turnista.
- Importazione completa su PostgreSQL isolato: dry-run, apply e secondo
  dry-run con zero ulteriori modifiche; nessuna identità remappata.
- Ratchet complessità GAIA e GATE passati senza cambiare baseline o soglie.
- Mappe Graphify codice Presenze, frontend GAIA e GATE aggiornate.

## Rilascio e rollback

GATE va rilasciato esclusivamente sul **VPS `gate`**. I servizi GAIA autorevoli
sono sul server GAIA; non è un rilascio del gateway GATE legacy CED/LAN.
Il pacchetto mirato deriva dalle immagini runtime rilevate e contiene soltanto
file di questa responsabilità, preservando i rilasci concorrenti.

Prima dell'applicazione: verificare nuovamente immagini/hash, backup database
verificato e configurazioni Compose. Applicare prima il contratto GATE, poi
schema/dati e servizi GAIA coinvolti, quindi sincronizzare e verificare record
OPE, TELEC e ADD/IRR reali in GATE, oltre ai 29 profili e ai conteggi della squadra.
La migrazione locale è `20261007_1600` (parent `20261006_1200`); produzione è
ancora a `20261005_1500`. Un'eventuale applicazione mirata dello schema non deve
marcare eseguita la migrazione Ruolo intermedia né eseguire upgrade estranei.

Rollback: immagini e configurazioni precedenti, backup/manifest delle aree e
membership modificati; non cancellare comandi manuali o dati aggiunti dopo il
rilascio. L'eventuale downgrade del nuovo tipo richiede prima la riconciliazione
esplicita delle assegnazioni, come verificato dal test PostgreSQL.

## Verifica in produzione e limiti

I 29 profili e le identità del PDF sono coerenti. Preservate le 21 membership
esistenti, le supervisione precedenti e le assegnazioni di turno. Il confronto
dei valori manuali di 3.567 giornaliere ha lo stesso SHA256 prima/dopo; i
payload di 1.110 comandi GATE preesistenti sono invariati. La cache GATE
contiene le 3.567 giornaliere di tutte le 29 persone nei mesi luglio–ottobre;
12 campioni reali coincidono con GAIA anche per timbrature e conteggi turno.
Nei dati del PDF sono presenti casi OPE del 1°, 3° e 4° sabato, rispettivamente
390, 390 e 0 minuti attesi; il 2°/5° sabato è verificato dai test.
La variante OPESAC passa 121 test mirati con coverage statement/branch 100%
sul resolver modificato, Ruff e ratchet passati.

Backup mirato verificato: tutte le definizioni di schema e dati delle tabelle
Presenze, squadre, anagrafiche e sincronizzazione. Dump custom circa 309 MB,
lista pg_restore verificata e copia NAS con SHA256 coincidente. È un backup
per ripristino selettivo del perimetro; non è un dump completo dei dati GAIA.
Il backup completo da 68 GB è stato interrotto dopo questa verifica.

L’audit globale rileva 15 collaboratori senza WCOperator, 239 giornaliere e
53 riepiloghi con riferimenti incoerenti: il confronto diretto con il backup
prova che erano già presenti, tutti **fuori dall’elenco PDF**. Non sono stati
corretti in questo intervento. Nessun collaboratore senza mapping canonico,
nessun duplicato o riferimento anagrafico orfano; nel perimetro delle 29
persone tutti i controlli identitari sono a zero.

Schema applicato in modo mirato; Alembic resta a `20261005_1500`, senza
eseguire o marcare eseguita la migrazione Ruolo intermedia. Backend finale
`gaia-backend:personale-impianti-20261007-v2`; worker e sync conservano la loro
immagine e usano la copia dedicata del mount con i soli file Presenze aggiornati.
Configurazione, ambiente, porte e volumi verificati rispetto al runtime precedente.
Il registro canonico privato conserva anche le 29 aree aggiornate per il
controllo dopo un futuro restore, senza modificare le identità.

Invio outbound autorizzato riuscito: run
`a2858864-791f-400b-a05c-4ca5a12004fc`, concluso il 07/10/2026 alle
16:58:41 UTC. Consegnati 116 scope collaboratore/mese, 3.567 giornaliere e
711 anomalie; confronto finale della cache GATE passato. Health finale dei
servizi GAIA e del gateway VPS positivo, endpoint GATE HTTP 200.
