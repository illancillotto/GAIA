# Testate Ruolo dal sync inCASS — 2026-10-01

Aggiornamento 2026-10-05: ammessi anche riferimenti ordinari storici con
prefisso `1` oltre a `0`, verificati per CADONI nelle annualità 2016–2018.
La scansione completa dall'anagrafica e la riconciliazione del partitario sono
descritte in `domain-docs/elaborazioni/docs/CAPACITAS_FULL_RECOVERY_2026-10-05.md`.

## Bug verificato

Per ARDU CRISTIAN (`RDACST79D30G113S`) Capacitas restituisce l'avviso 2023
`020230024242890`. Il record era presente in `ana_payment_notices`, ma non in
`ruolo_avvisi`. Il sync scriveva solo il primo archivio; la scheda Ruolo consulta
il secondo. Il materializzatore batch richiede il partitario e salta gli avvisi
sincronizzati senza dettagli: una sincronizzazione recente non garantiva quindi
la presenza del ruolo nella scheda soggetto.

## Correzione runtime

`backend/app/modules/ruolo/services/incass_read_model.py` espone
`materialize_incass_notice_header`, richiamato dall'upsert degli avvisi in
`backend/app/services/elaborazioni_capacitas_incass.py`.

- Sono ammesse solo annualità ordinarie e riferimenti numerici di 15 cifre
  coerenti con l'anno. I codici speciali, incluso il Riordino fondiario, sono
  esclusi tramite il classificatore canonico Capacitas.
- Il soggetto deve esistere, non essere duplicato e avere un'identità canonica
  non ambigua. Il CF/PIVA sorgente deve appartenere alla persona o società
  canonica; CF e PIVA della società restano identificatori distinti.
- Il CNC usa la conversione già adottata dal materializzatore:
  `01.` seguito dal riferimento senza l'ultima cifra.
- Per la testata si copiano nominativo, indirizzo sorgente, codice utenza e
  importo carico noto. Un importo invalido o fuori capacità resta nullo.
- Non vengono create partite, particelle o ripartizioni per tributo. Non si
  deducono notifiche o associazioni Poste.
- Le testate esistenti non sono modificate. Un'identità in conflitto interrompe
  il sync del soggetto, con rollback, anziché assegnare l'avviso arbitrariamente.
- UUID deterministici e `ON CONFLICT DO NOTHING` rendono la creazione idempotente
  anche in concorrenza. Il servizio non esegue commit: vale la transazione del
  sync soggetto, comprensiva dell'avviso in Utenze.

## Provenienza e limiti

Il job annuale `incass_sync_headers_<anno>` registra
`source=ana_payment_notices`, `mode=incass_header_sync` e
`partitario_materialized=false`. Questi job identificano la provenienza delle
testate, non rappresentano una certificazione di importazione catastale completa
né un contatore del lotto operativo di sincronizzazione.

L'arricchimento delle partite rimane nel materializzatore canonico
`backend/scripts/materialize_ruolo_from_incass.py`. La testata parziale non
garantisce il dettaglio catastale o i totali per tributo. Il materializzatore
preesistente conserva i totali delle testate già esistenti: il completamento di
questi aggregati richiede una riconciliazione distinta e non viene simulato dal
presente fix.

## Recupero dei record già sincronizzati

Il fix è locale e non implica deploy o backfill della produzione. Dopo il deploy
il successivo sync dell'avviso crea la testata mancante; la policy che salta i
soggetti già aggiornati può però escludere proprio i casi storici da recuperare.

Per un recupero dedicato:

1. Esportare un manifest degli avvisi inCASS ordinari privi del CNC/anno nel
   read-model, limitando colonne e soggetti e senza caricare PDF/HTML.
2. Eseguire un dry-run con le medesime verifiche d'identità, separando i conflitti
   dai candidati materializzabili. Nessuna annualità deriva dal solo indirizzo.
3. Salvare backup e manifest prima di applicare il helper ai soli candidati
   validati, con transazioni delimitate e report degli errori.
4. Verificare per ARDU il CNC `01.02023002424289`, anno 2023 e soggetto canonico;
   verificare inoltre assenza di duplicati e invariabilità dei dati Riordino.

Non accodare nuovamente i lotti Capacitas già presenti solo per ottenere una
testata. Il deploy e il recupero storico non sono stati eseguiti in questa change.

## Esecuzione successiva autorizzata in produzione — 2026-10-01

Dopo esplicita autorizzazione dell'utente è stato distribuito il fix al backend
montato e al solo worker runtime, ricreato senza job Capacitas attivi. Non è stato
eseguito un deploy globale del working tree né un riavvio del backend.

Il perimetro operativo comprende 452 utenze canoniche delle 661 raccomandate
tributarie residue, non tutte le utenze GAIA. I precedenti sync leggeri
4358–4362 erano già conclusi. Il nuovo lotto completo 4363–4381 ha sincronizzato
le 452 utenze con dettagli e partitario, senza errori di esecuzione e senza
importazione mailing list/ricevute Poste.

Un backup consistente streaming precede le modifiche. Dopo un dry-run senza
errori, la riconciliazione scoped riusa parser e validazioni canonici e aggiorna
i campi annuali noti della sorgente: 534 testate aggiornate, 375 partite e 2.338
particelle aggiunte, 211 particelle preesistenti aggiornate. Nessuna riga viene
cancellata; gli ID, i collegamenti e i campi archivistici rimangono invariati.
Per questa operazione esplicitamente autorizzata gli aggregati delle testate
esistenti sono riconciliati, diversamente dal comportamento conservativo del
helper automatico e del CLI preesistente. Il registro Catasto non è modificato.

Il controllo indipendente finale trova tutte le 3.289 testate ordinarie attese,
nessuna testata mancante e nessun conflitto d'identità; 441 testate mancavano
prima dell'operazione. ARDU ha il ruolo 2023, importo 70,00 euro e una partita,
coerenti con l'avviso `020230024242890` e il partitario Capacitas.

Restano segnalazioni di qualità della sorgente: 76 avvisi senza partite
disponibili nel partitario e 256 differenze fra carico e somma dei tre tributi.
Non sono interpretate come importi equivalenti o risolte per approssimazione.
Le somme Ruolo derivano dai tributi del partitario; il carico inCASS resta nella
sorgente ed è confrontato nel report dedicato. Queste differenze non provano
né invalidano automaticamente il collegamento anagrafico di una raccomandata.

La riverifica read-only mantiene 747 associazioni e propone 18 raccomandate
(26 avvisi): 14 con riferimenti Excel e quattro con avviso univoco. Non sono
applicate nuove associazioni. Fingerprint di Poste e cinque tabelle del registro
notifiche risultano identici prima/dopo; 878 raccomandate Riordino restano escluse.

Evidenze locali: `Report_di_associazione/Sync_completo_ruoli_20261001` nella
cartella operativa del Desktop. Backup, manifest, job plan e audit per-avviso
sono persistenti sul CED in
`/runtime-data/poste-recovery-backup/ruoli-full-20261001`.
L'override worker è
`/opt/gaia/hotfixes/incass-ruolo-20261001/compose.override.yml`;
un successivo deploy deve includere i due file del fix per non reintrodurre
il problema. Nessun commit o push eseguito per l'operazione.
