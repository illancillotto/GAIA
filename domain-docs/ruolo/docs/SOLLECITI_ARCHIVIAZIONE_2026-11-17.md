# Archiviazione operativa dei solleciti verificati — 17 novembre 2026

## Comportamento

Un item con `status=archived` resta nei lotti storici e conserva documento,
numero, collegamenti e importi. Non compare nel workspace operativo e non è
preparabile su Poste: i controlli esistenti accettano soltanto item `generated`.
Non cambia il credito sottostante, né lo stato contabile dell'avviso Ruolo.

Il filtro viene applicato **dopo** la scelta dell'ultima copia per numero avviso
o riferimento di consegna agli eredi. Archiviare l'ultima copia non ripropone
un vecchio PDF. Una successiva nuova copia valida resta visibile; consegne agli
eredi con riferimenti diversi rimangono indipendenti. I documenti privi di numero
continuano a essere distinti per ID.

Non è introdotta un'archiviazione automatica per età, annualità, importo ridotto
o identificativo fiscale invalido. La decisione richiede evidenze sul singolo
documento. Nessun nuovo endpoint, permesso, schema o comando di spedizione.

## Verifica e bonifica autorizzata

Audit in produzione dei 18 documenti segnalati dall'utente e di un ulteriore
documento emerso dalla ricerca finale dello stesso destinatario, in transazione
`REPEATABLE READ READ ONLY`, con confronto per numero avviso esatto e ID Ruolo:

- 16 PDF riportano lo stesso destinatario, ma le rispettive posizioni Ruolo e
  inCASS hanno nominativi diversi. Condividono l'identificativo invalido `C` e
  un collegamento anagrafico incoerente. Questi PDF sono errati; i debiti delle
  singole posizioni restano conservati e richiedono riconciliazione distinta.
- Un PDF conserva un residuo superato: la fonte inCASS importata e il motore
  Tributi riportano ora `paid` e residuo zero.
- Due documenti hanno ancora residuo positivo e non sono rimossi. Una precedente
  bozza Poste annullata non dimostra da sola che il documento vada eliminato.

Il caso aggiuntivo ha anche una copia successiva con destinatario corretto,
separata nel workspace: viene conservata integralmente. L'archiviazione riguarda
soltanto il vecchio item con intestazione errata, identificato tramite UUID;
non tutte le copie che condividono quel numero avviso.

L'audit consulta i dati sorgente già importati in GAIA, con le rispettive date
di sincronizzazione; non costituisce una nuova lettura del portale Capacitas
o una verifica legale di notifica. Nessun abbinamento per omonimia, nessuna
correzione automatica del codice fiscale o dei collegamenti anagrafici.

L'operazione privata conserva un manifest completo prima della modifica e una
motivazione in `error_detail` e `payload_json.operational_archive`. Prima della
scrittura verifica nuovamente identità, residui, assenza di lavorazioni Poste
attive e integrità degli item. La prova con rollback precede il commit atomico
dei primi 16 item e quello dell'ulteriore item verificato. Totale archiviati: 17.
PDF, contabilità, anagrafiche, registro e spedizioni rimangono
conservati. Nessuna bozza o spedizione viene creata.

Evidenze nominative e manifest di ripristino restano nell'area privata CED:
`/opt/gaia/runtime-data/ruolo/audits/solleciti-18-20261117/`.
Release backend circoscritta:
`/opt/gaia/releases/solleciti-archive-20261117/`.

## Validazione

- 35 test PASS, inclusi ranking e archiviazione su PostgreSQL isolato, generazione
  concorrente, controlli API e preparazione dal percorso precedente.
- Coverage del runtime modificato: 56/56 statement e 10/10 branch, 100%.
- Ruff, formattazione del nuovo test e `make lint-backend` PASS.
- Ciclomatica aggregata 38 e cognitiva aggregata 32 invariate; nessuna violation.
  Il file passa da 152 a 157 LOC effettive per il filtro SQL e la sua descrizione.
- Il ratchet completo contro il merge-base `origin/main` termina con exit 2 per
  l'ambiguità estranea `useEffect[0]<callback>` in Tributi frontend, dieci candidati.
  Nessun finding sul runtime modificato. La scansione ristretta perde il contesto
  dei simboli omonimi e produce abbinamenti impropri: non è usata come gate.
  Baseline, soglie ed esclusioni restano invariate; nessun PASS globale dichiarato.
- Il grafo codice Ruolo è aggiornato con il target Make dedicato. Le evidenze
  finali di attivazione e verifica dati sono nella directory privata di release.

## Esito produzione

Attivata il 17 novembre alle 12:18 CET l'immagine backend
`sha256:6fa84f4e132d7f15f1a9c789cd57cc274412fe3bf78ba31650fff55a41d51fd8`.
Confrontati tutti i 1.006 sorgenti Python dell'immagine precedente: cambia
soltanto `services/solleciti_workspace.py`. Configurazione effettiva conservata,
backend healthy e altri 36 container invariati. Ripristino disponibile nella
directory di release; nessun commit o push di questa modifica.

Verifica HTTP autenticata in sola lettura e verifica dati successive alla
bonifica: i documenti archiviati non sono più operativi, i due mantenuti restano
visibili. Autenticazione preservata (401 senza token), healthcheck 200.
I manifest privati distinguono la verifica dei primi 18 documenti dalla
successiva estensione e conservano la fotografia della copia corretta mantenuta.
La sincronizzazione dei dati sorgente resta distinta
dalla data di generazione dei PDF.
