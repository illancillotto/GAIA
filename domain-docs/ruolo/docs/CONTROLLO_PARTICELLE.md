# Controllo particelle e recupero posizioni

## Ambito

Il controllo riusa `/ruolo/particelle`, senza una seconda pagina o un secondo
servizio. L'universo storico comprende le particelle importate per il periodo
2020–2025; l'annualita corrente concordata e **2025**. La consultazione annuale
precedente resta disponibile con `?vista=annuale`; i vecchi URL con filtri
annuali continuano ad aprire quella vista.

Le altre viste comprendono storico, particelle non rilevate nel 2025, avvisi
con CF anomalo, pratiche aperte, pratiche con visure, immobili recuperati,
proposte e pratiche concluse/escluse. Le ultime due viste di approfondimento
elencano le pratiche: gli immobili e gli esiti delle visure sono nel dettaglio.

## Fonti e significato delle annualita

La fonte del controllo e il dettaglio gia acquisito nelle tabelle
`ruolo_particelle -> ruolo_partite -> ruolo_avvisi`, con i relativi
`ruolo_import_jobs`. Non si interrogano direttamente inCASS o Capacitas
durante l'analisi, ne si assume che gli archivi importati siano completi.

1. **Aggiorna analisi** costruisce un indice persistente e le firme delle fonti.
2. Un operatore autorizzato puo attestare la completezza di un'annualita,
   indicando fonte/versione e motivazione, dopo la verifica dell'intero ruolo
   e del dettaglio particelle. Import mancanti, non completati, con errori o
   record saltati impediscono l'attestazione.
3. Una presenza importata e `present`; una mancata presenza e `absent` soltanto
   con identificativo completo e attestazione valida per la firma corrente.
   Altrimenti e `not_verifiable`.
4. Una variazione delle firme invalida l'attestazione: aggiornare l'analisi e
   ripetere la verifica di completezza. Non equiparare mai assenza a omissione.

La vista “Non rilevate nel 2025” include anche casi non verificabili, chiaramente
distinti dalle assenze certificate. La matrice mostra prima/ultima presenza,
avvisi e intestatari per annualita. Un CF anomalo non esclude la particella
dall'universo storico. Sono censiti anche avvisi anomali privi di particelle.

Le chiavi conservano comune catastale, sezione disponibile, foglio, particella
e subalterno. I riferimenti originali restano nelle occorrenze. Le sezioni
derivano soltanto dagli hint gia esistenti nel parser Ruolo; gli identificativi
incompleti restano distinti per record sorgente. Non viene effettuato un merge
automatico fra riferimenti Ruolo e SISTER, che hanno namespace distinti.

## Istruttoria persistente

Aprire una pratica dalla particella o dall'avviso anomalo. Nel dettaglio:

- consultare la fotografia dei dati originali e lo storico annuale;
- registrare evidenze con fonte, riferimento documentale e data;
- per evidenze territoriali indicare anche versione, ambito ed esito;
- registrare abbinamenti proposti o confermati con CF, tipo soggetto, diritto,
  quota, periodo ed evidenza di supporto;
- mantenere separati stato pratica, richieste SISTER ed esiti dei singoli
  immobili acquisiti;
- preparare proposte e registrare conferma, esclusione motivata o approfondimento.

La validazione CF distingue mancante, incompleto, formalmente errato e
incoerente fra avviso e partita; comprende checksum e omocodia PF. La validita
formale non verifica l'identita. La conferma dell'abbinamento e una decisione
esplicita dell'operatore: non esiste conferma automatica per similitudine.

La pratica conserva una fotografia originale separata dalle evidenze acquisite
e dagli abbinamenti. Nessun comando modifica avvisi storici, anagrafiche o ruolo.
Trasferimenti, omonimie, quote e derivazioni catastali richiedono evidenze
documentali; una visura attuale non prova la titolarita nelle annualita pregresse.

## SISTER e immobili recuperati

Le richieste riusano `CatastoBatch`, `CatastoVisuraRequest`, documenti ed
estrazioni esistenti. **Prepara richiesta SISTER** crea un batch pending:
il collegamento **Apri elaborazione** porta al flusso esistente per avvio,
documenti e gestione errori. La ricerca per soggetto richiede un abbinamento
confermato PF/PNF; l'ambito effettivo della ricerca deve essere dichiarato.

`completed`, `failed`, `skipped` e `not_found` sono esiti della richiesta,
non dichiarazioni sull'esistenza catastale. Un errore tecnico, una richiesta
senza risultati o l'assenza nell'archivio locale non attestano una soppressione.

**Limite attuale:** il parser SISTER restituisce un solo riferimento catastale
principale. Il pulsante di acquisizione registra quel riferimento e gli
intestatari estratti, non tutti gli immobili del documento. Per gli altri
immobili occorre consultare il documento completo; la ricerca non viene
dichiarata esaustiva. Il confronto Ruolo di un immobile recuperato e manuale
con evidenza `role_check`, non un matching automatico fra i due namespace.

## Proposte e salvaguardie

Le proposte sono deduplicate per riferimento, annualita, CF verificato,
diritto, quota, componente tributaria e tipo. Una proposta di inserimento per
una particella gia presente nell'annualita richiesta viene rifiutata; restano
possibili rettifica e approfondimento storico. L'inserimento e limitato al
2025; le annualita pregresse usano `historical_review` separatamente.

La conferma richiede fonti non cambiate, evidenze aggiornate della particella,
esistenza catastale documentata, verifica territoriale positiva e regola
tributaria dichiarata. Per annualita pregresse e richiesta anche evidenza di
titolarita nel periodo. Non e previsto un inserimento automatico nel ruolo.

**La conferma alimenta soltanto la coda istruttoria GAIA**
(`destination=gaia_review_queue`): non e ancora collegata al processo reale di
formazione del ruolo. Il contratto di destinazione deve essere concordato prima
di realizzare tale collegamento.

## Persistenza, permessi e concorrenza

La revisione Alembic `20261006_1200` aggiunge indice, stato delle fonti,
pratiche, proposte e audit nello stesso database GAIA. Applicarla tramite il
normale processo di deployment prima di utilizzare le nuove viste.

La consultazione richiede modulo `ruolo` e sezione `ruolo.avvisi`; tutte le
azioni istruttorie richiedono `ruolo.tributi.manage_status`. Preparare richieste
richiede inoltre modulo `elaborazioni`. Al momento verifica e conferma
condividono il permesso esistente: eventuale separazione dei ruoli va definita.

Ogni comando registra operatore, azione, motivazione e payload. `command_id`
assicura replay idempotente; il riuso della chiave con dati differenti e
rifiutato. Gli aggiornamenti richiedono `expected_version`, lock della pratica
e controllo ottimistico; analisi/certificazioni usano advisory lock transazionale
PostgreSQL. Vincoli univoci proteggono origini delle pratiche e proposte.

## Decisioni ancora necessarie

- Fonti territoriali autorevoli/versionate per perimetro consortile e centri
  abitati. In loro assenza lo stato resta `verification_required`, senza
  inferenze basate sul solo comune.
- Regole di assoggettamento, componenti tributarie, periodi rilevanti e requisiti
  per recuperi pregressi: non sono inventati dal software.
- Collegamento effettivo al processo di formazione del ruolo.
- Estrazione completa delle visure per soggetto e riconciliazione documentata
  dei riferimenti Ruolo/SISTER.
- Eventuali permessi distinti per verifica e approvazione.

## Verifiche del ciclo

Test mirati: 43 casi backend e 27 frontend; coverage statement/branch al 100%
dei nuovi runtime e dei file runtime modificati nel ciclo, inclusa la pagina
Particelle esistente. Verificati Ruff, ESLint e typecheck. La migration ha
roundtrip/schema test in SQLite e generazione SQL nel contesto Alembic
PostgreSQL reale; non e stata applicata al database operativo. I test di lock
PostgreSQL simulano il dialect: non costituiscono un test concorrente su un
server PostgreSQL. Nessuna verifica live SISTER o collaudo browser operativo.

Gate del ciclo: `make lint-backend BASE_REF=HEAD`, ESLint sui sei runtime
frontend e `npm run typecheck`; pytest sul modulo `test_parcel_control.py` con
coverage full-file dei runtime del ciclo e Vitest sui tre file
`parcel-control*.test.*` con include esplicito anche della pagina annuale.
Ratchet autorevole tramite scan completo contro baseline del merge-base
`HEAD` e, come controllo aggiuntivo, `origin/main`; nessuna modifica a soglie,
esclusioni o baseline. I report temporanei vivono in `/tmp/gaia-control-*`.
La scansione parziale non e autorevole per il matching inter-file: puo scambiare
funzioni nuove per simboli di sorgenti non incluse nello scan.

Metriche dei 14 runtime nuovi: 120 callable, 27 warning e **zero error-level**;
ratchet completo senza finding nel ciclo. I runtime legacy toccati non
introducono regressioni. Baseline invariata per non includere modifiche
concorrenti estranee; nessun refactoring hotspot o riduzione dichiarata.
Graphify Ruolo codice/docs, frontend e backend aggiornati attraverso i target
dedicati; gli artefatti generati non entrano nel commit.
