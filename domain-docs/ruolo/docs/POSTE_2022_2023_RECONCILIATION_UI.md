# Riconciliazione assistita Poste 2022-2023

La pagina `/ruolo/raccomandate` mostra una coda di revisione per la campagna
storica Poste 2022/2023, delimitata agli invii creati prima del
`2026-09-29T00:00:00+02:00`. La coda usa l'anteprima read-only del Registro e
non cambia alcuna associazione senza conferma individuale dell'operatore.

L'operatore seleziona il file Excel con il foglio `Dati`. Il browser legge le
righe operative e calcola lo SHA-256 del file; il contenuto completo non viene
caricato sul server. Per una coppia proposta la schermata mostra i dati Poste,
la riga cumulativa trovata per codice fiscale e i due avvisi annuali. La riga
deve essere unica e contenere entrambi i riferimenti C/D. L'endpoint
`POST /ruolo/tributi/raccomandate/{mail_id}/reference-check` verifica in
lettura che i riferimenti esistano in inCASS e concordino per soggetto e codice
fiscale con gli avvisi candidati.

Un segnaposto come `---` non e un riferimento annuale: la riga non costituisce
evidenza per associare la coppia. Nella ricerca "Matching manuale" ogni avviso
mostra separatamente lo stato del pagamento (pagato, parziale, non pagato,
eccedenza o da verificare) e l'eventuale rateizzazione/stato gestionale. I
badge derivano dallo stato di pagamento calcolato, dal workflow e dalla policy
di rateizzazione inCASS gia esposti dall'API; non sono modificabili dalla
modale e non dimostrano quali avvisi fossero contenuti nella busta Poste.

## Revisione di una sola annualita

Se il foglio riporta il riferimento di una sola annualita, non forzare
l'associazione cumulativa. Il caso puo essere proposto per un collegamento
singolo quando codice fiscale, soggetto e indirizzo della raccomandata
concordano con l'avviso; il riferimento annuale trova riscontro in inCASS;
l'altra annualita risulta gia saldata prima della data di spedizione; e non
esistono collegamenti concorrenti. Lo stato di pagamento successivo all'invio
e un indizio cronologico aggiuntivo, non una prova della composizione della
busta. L'operatore verifica l'invio e conferma soltanto l'avviso documentato.
Senza tale verifica il caso resta in revisione; non applicare il criterio in
batch e non inferire la notifica perfezionata dall'associazione.
La modale di matching manuale registra operatore e timestamp ma, per il
collegamento singolo, non conserva ancora hash e riga del foglio Excel: tali
elementi vanno verificati nella fonte operativa e non attribuiti all'audit
applicativo.

Solo dopo tale verifica e la spunta esplicita dell'operatore si puo associare
la coppia. Il `PATCH /association` ripete la verifica e controlla che gli
avvisi selezionati coincidano con i candidati salvati. Nel payload della
associazione manuale e nell'audit persistente del Registro restano hash del
file, foglio, numero di riga, riferimenti annuali, utente e timestamp.
L'hash e la riga sono dichiarati dal client: il server non riceve l'Excel e
non puo verificarne i byte. La verifica server-side riguarda i riferimenti
inCASS e la coppia di avvisi, non l'autenticita del foglio.

Il foglio non contiene un ID invio o tracking Poste: concordanza di nominativo
e codice fiscale non dimostra da sola il contenuto della busta. La conferma
richiede quindi una verifica operativa dell'invio. L'associazione crea le
posizioni cumulative nel Registro con stato notifica `da_verificare`; non
certifica la notifica perfezionata. I casi senza coppia univoca o senza
riscontro inCASS restano nella coda e non sono associati da questa schermata.

## Verifica e rilascio

Prima del rilascio: 45 test backend passati, 6 test PostgreSQL esclusi dalla
selezione mirata; coverage dei cinque file runtime backend modificati al 100%
statement e branch. I 25 test frontend mirati passano con 100% statement,
branch, funzioni e righe sui sei file runtime modificati. Typecheck, ESLint
mirato, Ruff e complexity ratchet contro `origin/main` passano senza finding.
Graphify aggiornato con i target `graphify-ruolo-code`, `graphify-frontend` e
`graphify-ruolo-docs`. Il rilascio applicativo non avvia il job Poste 9 e non
esegue riconciliazioni massive: ogni associazione resta una decisione
individuale. Al momento della verifica locale non sono state modificate le
151 associazioni presenti nell'audit del 2026-09-29.

## Lotto operativo autorizzato del 2026-09-30

Dopo la conferma del foglio Excel da parte dei colleghi e l'approvazione
esplicita del dry run, e stato applicato sul CED il lotto
`poste-name-address-excel-235-20260930`. Il confronto usa nome e cognome
completi normalizzati, indipendenti dall'ordine, e indirizzo con civico
concordante; soltanto le ambiguita vengono risolte con la riga Excel univoca
per codice fiscale e i riferimenti annuali verificati in inCASS. Il file
operativo ha SHA-256
`66637fa3be62d89f566a4ebb64a08fe5627cd604589d1dc109fb121ac04add6d`.
Questa esecuzione autorizzata e separata dalla conferma individuale della UI.

Il lotto comprende 19 collegamenti singoli da nome e indirizzo, 88 singoli
risolti con Excel e 128 coppie 2022/2023: 235 raccomandate e 363 avvisi
distinti. Le associazioni legacy passano da 152 a 387. Sono stati creati
128 documenti cumulativi e 256 posizioni nel Registro; notifica e recupero
restano `da_verificare`. Gli 8 invii con avvisi condivisi fra proposte restano
esclusi, insieme ai 1891 senza concordanza esatta di nominativo e indirizzo.

Per 32 coppie i candidati storici erano assenti o riferiti ad avvisi non piu
presenti. Il lotto ha ricalcolato i candidati dai dati attuali e verificato
separatamente annualita, soggetto, codice fiscale e riferimenti inCASS; la
provenienza registra tale percorso senza modificare i vecchi suggerimenti.
Il servizio GAIA esistente registra le associazioni con l'account operativo
`admin` (ID 1), la conferma esplicita del lotto e il riferimento al dry run.
Le 216 associazioni risolte con Excel conservano hash, foglio e numero di
riga, inclusi i collegamenti singoli; le coppie conservano anche l'audit del
Registro.

Prima del commit sono stati eseguiti una prova completa con rollback,
un nuovo controllo dei dati e un backup privato `0600` persistente:
`/opt/gaia/runtime-data/poste-recovery-backup/poste-name-address-excel-235-20260930-apply-backup.json`,
SHA-256 `97684847e9483d4dc75cec0244278b322a346191309e57b97ee262c1193835b7`.
La transazione e stata atomica. La verifica indipendente dopo il commit
conferma tutte le associazioni, le evidenze, le 128 coppie e gli stati
`da_verificare`; le altre 2051 righe e tutti i record preesistenti del Registro
sono invariati. L'esito persistente e nel file
`poste-name-address-excel-235-20260930-independent-verification.json` della
stessa directory di backup.

## Secondo lotto autorizzato del 2026-09-30

Il lotto `poste-residual-23-20260930`, approvato dopo l'analisi delle residue,
ha associato altre 23 raccomandate a 26 avvisi distinti: 20 collegamenti
singoli e 3 coppie. Il totale delle raccomandate associate passa da 387 a 410.
Tre proposte hanno comune, via e civico concordanti con una sigla provinciale
storica diversa; le altre 20 usano l'indirizzo originale conservato in
`raw_payload_json.raw.info`, mentre il campo indirizzo importato conteneva
il codice fiscale.

La stessa transazione ha corretto soltanto quei 20 indirizzi, con comune,
provincia, CAP e normalizzazioni coerenti. Per ogni correzione l'audit
dell'associazione conserva i valori precedenti e successivi, il percorso
della fonte, l'ID invio e l'hash dell'indirizzo originale. Il dato `raw` resta
immutato. I candidati sono stati ricalcolati sui dati correnti verificando
nome completo, comune, via e civico; per gli indirizzi ricostruiti concorda
anche il codice fiscale archiviato. Le 15 proposte con riscontro Excel
conservano hash, foglio e riga e ripetono il controllo dei riferimenti inCASS.
Le proposte singole senza riscontro Excel richiedono un unico avviso
compatibile. Riordino fondiario, target condivisi e casi ancora in revisione
restano esclusi.

Il preflight completo con rollback e passato prima del commit atomico.
Il backup persistente privato `0600` e
`/opt/gaia/runtime-data/poste-recovery-backup/poste-residual-23-20260930-apply-backup.json`,
SHA-256 `0d508ed1680e6299c5e4e0e31449d44d3ee1f112fe471319d0d34ff4895bd655`.
La verifica indipendente conferma associazioni, 20 correzioni, 15 evidenze
Excel e 3 nuovi documenti cumulativi con 6 posizioni; notifica e recupero
restano `da_verificare`. Le altre 2263 righe, i record preesistenti del
Registro e i dati degli avvisi importati sono invariati. L'esito e in
`poste-residual-23-20260930-independent-verification.json` nella stessa
directory di backup.

## Terzo lotto autorizzato del 2026-10-01

L'utente ha approvato l'associazione dei 313 casi con nome completo,
indirizzo, comune e civico Poste concordanti con l'Excel operativo, pur
conservando l'indirizzo storico discordante del Ruolo. Il controllo aggiuntivo
dei suggerimenti storici ha escluso un caso che riportava avvisi ancora
presenti riferiti a un'altra identita. Il lotto effettivamente applicato,
`poste-excel-address-312-20261001`, comprende quindi 312 raccomandate e
479 avvisi distinti: 145 collegamenti singoli e 167 coppie 2022/2023.
Il totale delle raccomandate associate passa da 410 a 722.

Tutte le 312 associazioni conservano hash dell'Excel, foglio `Dati`, riga e
riferimenti annuali. I riferimenti sono stati ricontrollati su inCASS per
annualita, soggetto e codice fiscale; i target non risultavano gia collegati
o condivisi nel lotto. I suggerimenti storici sono rimasti invariati e ogni
loro esito e registrato nella provenienza: selezionato e riverificato,
avviso non piu presente oppure stessa identita con annualita non riportata
nel foglio operativo confermato. I suggerimenti validi su altra identita
non sono stati ignorati e il caso resta in revisione.

Per 31 raccomandate il vero indirizzo Poste e stato verificato dal dato
originale `raw_payload_json.raw.info`, senza correggere i campi memorizzati
in questo lotto. Tutti gli indirizzi Poste, i payload originali e i dati
storici degli avvisi Ruolo sono preservati. Riordino fondiario resta escluso.

Il primo tentativo di preflight si e interrotto prima delle modifiche durante
una lettura troppo ampia degli avvisi. La transazione non ha effettuato
commit e il totale delle associazioni e rimasto 410. Il successivo preflight
ha limitato la materializzazione ORM al perimetro annuale e confrontato
l'intera tabella avvisi tramite fingerprint SQL, completando la prova delle
312 associazioni con rollback. L'applicazione ha ripetuto le verifiche sotto
lock e ha effettuato un unico commit atomico con l'account operativo `admin`.

Il backup persistente privato `0600` e
`/opt/gaia/runtime-data/poste-recovery-backup/poste-excel-address-312-20261001-apply-backup.json`,
SHA-256 `1bb044f1632b46e4485c48562e611a329c5ba96e659c66274330ae4b7c10072a`.
La verifica indipendente post-commit conferma le 312 associazioni, tutte le
evidenze Excel, i 167 nuovi documenti cumulativi e le 334 posizioni. Notifica
e recupero restano `da_verificare`. Le altre 1974 righe Poste e tutti i record
preesistenti del Registro sono invariati; il fingerprint dell'intera tabella
Ruolo e il confronto degli avvisi selezionati confermano l'assenza di
modifiche ai dati importati. L'esito persistente e
`poste-excel-address-312-20261001-independent-verification.json` nella stessa
directory di backup.

Lo snapshot read-only post-applicazione del 2026-10-01 conferma 2286
raccomandate complessive, 722 associate e 1564 residue: 878 del Riordino
fondiario e 686 tributarie ancora da revisionare. Tutti i report disponibili
sono archiviati nella cartella locale
`/home/cbo/Desktop/Avvisi non pagati 2022-2023/Report_di_associazione`.
Il prospetto corrente e `REPORT_FINALE_20261001.xlsx`; lo storico conserva
gli esiti delle analisi precedenti, che non vanno interpretati come totali
attuali.

## Quarto lotto autorizzato del 2026-10-01

Il lotto `poste-excel-name-19-20261001` associa altre 19 raccomandate a
32 avvisi distinti: 6 collegamenti singoli e 13 coppie. L'utente ha approvato
esplicitamente anche le 14 differenze del nominativo storico Ruolo, composto
da parole aggiunte o mancanti rispetto al nome completo concordante fra
Poste ed Excel. Le altre 5 raccomandate hanno nome Ruolo esatto e una
differenza della strada storica corroborata dall'indirizzo Excel. Non si
tratta di accettare automaticamente una somiglianza fuzzy.

Il dry run ha confrontato tutte le 686 residue tributarie con le righe
operative Excel, verificando nome completo, indirizzo, comune e civico.
I 32 riferimenti annuali sono stati ricontrollati in inCASS per anno,
soggetto e codice fiscale, selezionando gli avvisi canonici dello stesso
contribuente. I 34 suggerimenti storici del lotto sono stati controllati
anche sul database corrente, senza limitarsi allo snapshot annuale:
nessun suggerimento valido conflittuale. Nessun target risulta gia
associato o condiviso nel lotto proposto.

Il preflight completo con rollback e stato seguito da nuova validazione
sotto lock, backup privato persistente e commit atomico con il servizio
GAIA esistente e l'account operativo `admin`. Ogni associazione conserva
hash, foglio e riga dell'Excel, riferimenti annuali, autorizzazione ed esiti
dei suggerimenti storici. Tutti i nomi e gli indirizzi storici Ruolo restano
invariati; anche gli indirizzi Poste e i payload originali sono preservati.

Il backup persistente privato `0600` e
`/opt/gaia/runtime-data/poste-recovery-backup/poste-excel-name-19-20261001-apply-backup.json`,
SHA-256 `b90e1e0750085de4743620bbb9d3ac2e7819e9865a2a7b76281ef6cf70cecaae`.
La verifica indipendente post-commit conferma le 19 associazioni, tutte le
evidenze Excel, i 13 nuovi documenti cumulativi e le 26 posizioni. Notifica
e recupero restano `da_verificare`. Le altre 2267 righe Poste, inclusi tutti
i casi del Riordino fondiario, il Registro preesistente e l'intera tabella
degli avvisi Ruolo sono invariati. L'esito persistente e
`poste-excel-name-19-20261001-independent-verification.json` nella stessa
directory di backup.

Lo snapshot read-only post-applicazione del 2026-10-01T11:21:01.923493+00:00
conferma 2286 raccomandate complessive, 741 associate e 1545 residue:
878 Riordino fondiario escluse e 667 tributarie ancora da revisionare.
Nella cartella locale `Report_di_associazione` il prospetto corrente e
`REPORT_FINALE_20261001_LOTTO19.xlsx`, con evidenze in `Lotto_19_20261001`.
Le analisi delle 686 residue e il prospetto dei 19 prima dell'approvazione
restano disponibili come storico; i loro conteggi non sono lo stato attuale.

## Collegamento singolo senza civico del 2026-10-01

Il lotto `poste-missing-civic-1-20261001` associa una raccomandata a un
avviso, dopo l'approvazione esplicita dell'assenza del civico in entrambe
le fonti Poste ed Excel. Concordano nome completo Poste/Excel/Ruolo,
indirizzo Poste/Excel, comune e codice fiscale archiviato nel dato Poste.
Il riferimento annuale e stato verificato in inCASS per anno, soggetto e
codice fiscale. Il target e unico, libero e non condiviso; non sono presenti
suggerimenti storici conflittuali. La fonte originale `raw.info` e l'ID
invio in `raw.source.idInvio` sono stati riverificati sul CED.

L'assenza del civico non e stata trasformata in un valore presunto. Tutti
i nomi e gli indirizzi storici, compresi i campi Poste memorizzati, restano
invariati. Il servizio GAIA esistente ha registrato il collegamento con
l'account operativo `admin`, l'autorizzazione della specifica eccezione,
hash dell'Excel, foglio `Dati`, riga e riferimenti annuali.

Il preflight completo con rollback e stato seguito da nuova validazione
sotto lock, backup privato persistente e commit atomico. Il backup `0600` e
`/opt/gaia/runtime-data/poste-recovery-backup/poste-missing-civic-1-20261001-apply-backup.json`,
SHA-256 `acf802606be11037c463b893aee0b37a9096a39c6746dfb807edaab4bc2c6387`.
La verifica indipendente post-commit conferma il collegamento e l'evidenza
Excel, l'assenza di modifiche agli avvisi Ruolo e al Registro preesistente
e le altre 2285 righe Poste inalterate. Non e stato creato alcun documento
cumulativo e non e stata dedotta una notifica perfezionata. L'esito
persistente e `poste-missing-civic-1-20261001-independent-verification.json`
nella stessa directory di backup.

Lo snapshot read-only post-applicazione del 2026-10-01T13:26:58.05731+00:00
conferma 2286 raccomandate complessive, 742 associate e 1544 residue:
878 Riordino fondiario escluse e 666 tributarie ancora da revisionare.
Il report corrente nella cartella locale `Report_di_associazione` e
`REPORT_FINALE_20261001_LOTTO1.xlsx`, con evidenze in `Lotto_1_20261001`.
Gli approfondimenti delle 667 residue e il relativo candidato restano
conservati come evidenza della fase precedente all'approvazione.

## Lotto regex e riferimenti Excel del 2026-10-01

Il lotto `poste-regex-excel-5-20261001` associa cinque raccomandate a dieci
avvisi, tutti in coppia 2022/2023, dopo la richiesta esplicita dell'utente
di riconoscere le varianti di indirizzo come SALIS e di utilizzare l'Excel
per la selezione delle annualita. I destinatari sono SALIS OTTAVIO,
SOCIETA' AGRICOLA QUERCUS SRL, WILLIAM DUE SRL, UNITRADE SRL e
FONDIARIA ESTATE SRL.

Le regex normalizzano abbreviazioni stradali e punteggiatura societaria,
preservando comune, civici, suffissi e chilometrica. L'alias tra STRADA
VICINALE SAN SIMEONE e CASE SPARSE SAN SIMEONE SNC e limitato a
SANTA GIUSTA e alle varianti senza civico numerico autorizzate dall'utente.
Ogni riferimento annuale Excel e verificato in inCASS per anno, CF e
soggetto canonico. I suggerimenti storici sono riverificati live; nessun
target selezionato e gia collegato o condiviso nel perimetro esaminato.

Il confronto regex read-only individua 28 raccomandate e 54 avvisi
candidati. Restano esclusi 23 invii: 18 senza riga Excel unica corroborata,
due con target condiviso e tre con avvisi gia associati. Le righe Dati
3605 e 4459 contengono rispettivamente SALIS e WILLIAM DUE: i precedenti
prospetti che indicavano assenza di riga esatta per questi destinatari
sono superati dalla verifica diretta per CF e denominazione normalizzata.
WILLIAM DUE ha indirizzo e comune Excel assenti, ma Poste e Ruolo
concordano dopo l'espansione SS in STRADA STATALE.

Il preflight completo con rollback precede una nuova validazione sotto
lock, backup persistente privato e commit atomico. Il backup e
`/opt/gaia/runtime-data/poste-recovery-backup/poste-regex-excel-5-20261001-apply-backup.json`,
SHA-256 `63c937420e3b2480db7da06db01045dedf0e86d969a2b75ae0c79b171471c0cb`.
La verifica indipendente conferma le dieci posizioni, le evidenze Excel,
l'intera tabella avvisi invariata, il Registro preesistente invariato e
le altre 2281 righe Poste inalterate. Gli indirizzi storici e i payload
originali restano invariati; notifica e recupero restano `da_verificare`.

Lo snapshot successivo del 2026-10-01T15:11:29.091652+00:00 conferma
2286 raccomandate, 747 associate, 661 residue tributarie e 878 Riordino
fondiario escluse. Il report corrente e
`Report_di_associazione/REPORT_FINALE_20261001_LOTTO_REGEX5.xlsx/json`;
manifest, confronti ed esiti sono in `Regex_indirizzi_20261001`.

WILLIAM DUE ha gia la sede STRADA STATALE 126 KM 113 500, TERRALBA,
sia negli avvisi storici sia nelle Utenze. La verifica diretta Capacitas
non e possibile: la sola credenziale configurata, ID 1, e disattivata.
Non e stata riattivata e nessun job massivo e stato avviato. La presenza
del dato non dimostra aggiornamento rispetto a Capacitas corrente.
Il job REGISTRY esistente importa documenti NAS, non indirizzi Capacitas;
il job storico Capacitas supporta solo persone e non va usato per aziende.
