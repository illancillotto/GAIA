# STEP: Piano Di Implementazione Import

## Stato Al 2026-09-21

Documento preparatorio richiesto dall'operatore. **Import STEP operativo non è
ancora attivo**: non abbiamo ancora report campione, dizionario degli stati o
contratto API. È stato aggiunto il primo blocco sicuro di implementazione:
`notice_import_step.py` legge CSV/XLSX solo con mapping esplicito e produce
osservazioni immutabili di staging, senza matching, affidamento o modifica dei
dati operativi.

Come per [Poste](POSTE_INVIO_AUTOMATICO.md), separiamo acquisizione del contratto,
implementazione e attivazione. Il parser introdotto non inventa colonne o stati:
richiede il mapping approvato dall'operatore e conserva l'originale di ogni riga.
Il sito pubblico indicato, <https://www.stepservizi.net/new>, non identifica
necessariamente il portale riservato, il servizio contrattuale o un'API.

Obiettivo: importare fatti documentati sul recupero crediti, collegarli al
registro avvisi e mantenere una storia verificabile. Non affidare nuove pratiche
a STEP, non notificare avvisi e non registrare automaticamente incassi.

## Regole Di Dominio

- Importare tutto lo storico 2022/2023, inclusi notificati e affidati. I filtri
  di generazione non sono filtri di importazione.
- Notifica, affidamento STEP, invio e pagamento sono fatti indipendenti. La
  stima operativa del 90% di affidamenti dopo notifica non autorizza deduzioni.
- Una riga assente dal report non prova il mancato affidamento, neppure se il
  file si presenta come elenco completo: possono esserci filtri, altre pratiche,
  account, tributi o intervalli non coperti.
- Nessun collegamento automatico tramite solo nome, codice fiscale, importo o
  annualita. Questi dati possono proporre candidati, non stabilire identita.
- Pratica STEP, documento storico, posizione annuale, avviso GAIA e tracking
  Poste restano identificatori distinti. Conservare namespace e provenienza.
- Originali ed eventi importati sono immutabili. Rettifiche, collegamenti e
  decisioni dell'operatore producono nuove revisioni con motivazione e audit.

## Acquisizione Del Contratto

Prima tranche: export manuale autorizzato, senza connettore. Servono report
campione con casi attivi, revocati, chiusi, pagamenti parziali, piu annualita,
piu pratiche per posizione e pratiche senza riferimento avviso.

Per ogni campione annotare localmente ente/account, servizio, filtri, data di
estrazione e data di aggiornamento dichiarata da STEP. Richiedere il dizionario
ufficiale di colonne, identificatori, causali, stati e date. Verificare se il
report e una fotografia o un insieme di variazioni/eventi.

Solo in una fase successiva, per il download automatico:

1. Verificare disponibilita di API ufficiali e autorizzazioni contrattuali.
2. Concordare account, ambiente e sole operazioni di lettura consentite.
3. Osservare login, elenco pratiche, dettaglio, richiesta export, stato job e
   download. Sono operazioni da verificare, non endpoint gia conosciuti.
4. Registrare metodo, host/path verificati, paginazione, limiti, scadenza link,
   codici risposta, MIME, schema dati e gestione autenticazione interattiva.
5. Distinguere POST di lettura da comandi remoti. Non ripetere richieste di
   export su timeout finche non sono noti effetti e modalita di riconciliazione.
6. Non osservare o eseguire affidamenti, revoche, chiusure o altre scritture
   operative per scoprire il contratto. Non aggirare MFA/OTP.

HAR e report originali vanno conservati fuori dal repository in storage privato
con accessi autorizzati e retention definita. Non registrare cookie, token,
credenziali, query identificative o dati personali nei log diagnostici.
L'inventario HAR Poste ha una allowlist specifica e **non supporta STEP**:
non riutilizzarlo ampliando gli host senza un contratto e test dedicati.

## Contratto Dati Da Validare

Questi sono requisiti interni, non nomi di colonne STEP gia osservati.

| Gruppo | Informazioni richieste |
| --- | --- |
| Provenienza | Ente/account, servizio, file, SHA-256, foglio/riga, versione parser |
| Report | Filtri, copertura, tipo snapshot/eventi, data estrazione e aggiornamento fonte |
| Identita pratica | Identificatore stabile, namespace e eventuale identificatore evento/revisione |
| Identita posizione | Riferimento avviso originario, annualita e tributo, identificatore posizione STEP se presente |
| Soggetto | CF/P.IVA e denominazione originali, senza usarli come chiave certa |
| Stato | Codice/descrizione originali, causale, decorrenza e prova dell'evento |
| Importi | Carico, riscosso, residuo, interessi e spese distinti, valuta e precisione |
| Evidenze | Riferimenti a distinta, provvedimento, report o ricevuta verificabili |

Preservare stringhe e zeri iniziali degli identificatori. Importi con Decimal;
niente conversioni permissive che trasformino valori mancanti in zero. Date
ambigue, future o malformate richiedono anomalie e originale conservato.
La correzione Excel gia approvata `29/06/204 -> 29/06/2024` e specifica di quella
fonte: non applicarla genericamente ai futuri report STEP.

Una riga multiannualita non va duplicata attribuendo l'intero importo a ogni
anno. Conservare il totale pratica separato dai dettagli; una ripartizione non
documentata resta sconosciuta. Un report contabile STEP non crea pagamenti GAIA:
gli incassi richiedono una riconciliazione contabile separata, anche per evitare
doppioni con import bancari o inCASS.

## Modello E Riuso

Nel registro esiste gia `NoticeRecovery`, una valutazione corrente per
`NoticePosition`, con stato, pratica, data verifica, prova e importo opzionale.
Non e un archivio analitico di pratiche: **non sovrascriverlo a ogni riga** di un
report con piu pratiche sulla stessa posizione.

L'implementazione dovra aggiungere, con migration revisionata:

- Pratiche STEP identificate nel namespace ente/account/servizio verificato.
- Osservazioni/eventi immutabili collegati a report e righe originali.
- Collegamenti pratica-posizione molti-a-molti, con stato di revisione, versione,
  motivazione e operatore. Se manca `avviso_id`, mantenere l'anomalia.
- Proiezione della valutazione corrente nel registro, riconducibile a tutte le
  pratiche collegate. Un solo affidamento attivo impedisce il via libera.

Riutilizzare il workflow di staging, digest, anteprima, conferma e audit di
`notice_import.py` e le superfici UI delle importazioni/anomalie. Non chiamare
direttamente `notice_import_register.publish_row`: oggi pubblica documenti
storici, mentre una pratica STEP non e necessariamente un nuovo avviso.
Occorre un publisher STEP dedicato e un'estensione esplicita dei contratti API.

## Import E Riconciliazione

1. **Staging:** validare formato reale e limiti file/righe/decompressione;
   conservare snapshot server immutabile e metadati di provenienza. Non eseguire
   macro/formule, link esterni o contenuti incorporati nel foglio.
2. **Anteprima:** conteggi di nuovi eventi, duplicati, aggiornamenti, conflitti,
   anomalie, pratiche prive di collegamento e potenziali blocchi di generazione.
   Nessuna modifica al registro definitivo.
3. **Matching:** consentire collegamenti certi solo per identificatori
   documentati e corrispondenza univoca. Gli altri casi vanno in anomalie con
   ricerca manuale degli avvisi e confronto di anno/riferimento/soggetto.
4. **Conferma:** permessi server, digest e revisione attesi, ricalcolo conflitti
   dentro la transazione, lock/versioni e unicita DB. Doppio click e due
   operatori non devono pubblicare due volte gli stessi eventi.
5. **Applicazione:** persistere osservazioni, collegamenti approvati ed audit;
   aggiornare la proiezione STEP solo secondo mapping di stati validato.
6. **Rettifica:** mantenere originale e decisione precedente; rettificare il
   collegamento con motivazione e riaprire la verifica delle posizioni coinvolte.
   Annullare un import locale non significa revocare la pratica su STEP.

Deduplica file tramite contenuto e provenienza; deduplica logica tramite chiavi
fonte stabili, revisione/evento e fingerprint normalizzato. Nome file, numero
riga e timestamp di download non sono chiavi di pratica. Se STEP non offre
identita/revisioni affidabili, trattare i report come osservazioni confrontabili
manualmente, senza promettere deduplica automatica degli eventi.

Un report piu recente puo contenere eventi vecchi. Non usare il momento di
importazione come ordine di verita. Payload discordanti con la stessa chiave,
date fuori ordine o stati incompatibili producono conflitti visibili, senza
last-write-wins e senza cancellazione dello storico.

## Stati E Generazione 2022/2023

| Evidenza verificata | Valutazione corrente / effetto |
| --- | --- |
| Nessun riscontro o stato sconosciuto | `da_verificare`; blocca |
| Affidamento attivo su almeno una pratica | `affidato`; blocca |
| Mancato affidamento esplicitamente verificato su tutto il perimetro | `non_affidato_verificato`; solo il blocco STEP puo essere rimosso |
| Revoca provata, nessun'altra pratica attiva o incerta | `revocato`; restano tutti gli altri controlli |
| Pratica chiusa | `chiuso`; resta bloccata nel gate attuale, non equivale a insoluto nuovamente esigibile |
| Stati discordanti, copertura incompleta o collegamento dubbio | Revisione obbligatoria; nessun nuovo via libera |

Notifica perfezionata, saldo non esigibile, storico non verificato, invii
irrisolti e anomalie continuano a bloccare indipendentemente da STEP.
L'import non puo trasformare una notifica gia perfezionata in assenza di notifica.
La scadenza di una verifica e l'eventuale liberazione di pratiche chiuse richiedono
una decisione di dominio separata, non una scelta implicita del parser.

Un import tardivo puo invalidare una bozza o una conferma non ancora utilizzata.
Il publisher STEP deve aderire al protocollo concorrente della generazione,
inclusi nuovi orfani, ricollocazioni e cambi di stato. Il collegamento manuale
deve invalidare sia il vecchio sia il nuovo perimetro. Un invio gia avvenuto non
si annulla con rollback: va segnalato come evento da gestire e conservato in audit.

## UI Prevista

Nel registro, sezione Importazioni con origine STEP: file, copertura del report,
data fonte, esito e anteprima prima della conferma. Nel dettaglio avviso,
pratiche collegate con eventi, provenienza e valutazione corrente separati.
In Anomalie, pratiche/posizioni senza `avviso_id`, candidati e comando esplicito
di collegamento; in Conflitti, confronto originale/nuova osservazione/decisione.

Utenti in sola lettura possono consultare, non importare o risolvere anomalie.
Attore e permessi derivano dalla sessione server; le rettifiche richiedono
motivazione e versione, non un `actor_id` liberamente scelto nel browser.
Non mostrare pulsanti di download automatico o import operativo prima che
adapter, contratto, autorizzazioni e test siano pronti.

## Ordine Di Implementazione

1. Acquisire campioni e dizionario, approvare il mapping senza effetti operativi.
2. Implementare parser offline versionato e fixture anonimizzate; preview soltanto.
3. Introdurre archivio pratiche/eventi, publisher transazionale e deduplica DB.
4. Integrare anomalie, collegamenti, conflitti, rettifiche e proiezione STEP.
5. Collegare invalidazione e protocollo di conferma generazione; test PostgreSQL.
6. Collaudare UI e import pilota in ambiente isolato, poi decidere l'attivazione.
7. Solo successivamente implementare download automatico con account autorizzato,
   credenziali gestite dalla piattaforma, osservabilita e nessuna scrittura remota.

## Criteri Di Accettazione

- Campioni coprono piu pratiche/annualita, dati mancanti, importi, date, stati
  ignoti, report filtrati, vecchi e fuori ordine; originali sempre ricostruibili.
- Reimport dello stesso file e file rinominato/riordinato non duplicano fatti;
  cambi reali non vengono scartati come duplicati.
- Assenza nel report non libera STEP; notifica non assegna STEP; riscosso STEP
  non crea incasso GAIA; chiusura/revoca parziale non libera altre pratiche.
- Concorrenza reale PostgreSQL: doppia conferma, import/collegamento/rettifica
  simultanei e import contro conferma lotto; rollback condiviso senza mezzi stati.
- API: autenticazione, permessi, versioni/digest obsoleti, limiti, paginazione,
  errori e isolamento dei dati. UI desktop/mobile e sola lettura.
- Coverage full-file runtime 100%, lint e quality ratchet contro merge-base,
  Graphify aggiornato. Nessun accesso reale a STEP necessario nei test automatici.

Il rilascio resta subordinato ai campioni, alla revisione del mapping e al
protocollo di generazione/conferma; questo documento non attiva alcuna integrazione.
