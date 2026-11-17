# Invio PEC/email dei solleciti2021

## Integrazione archivio — 17 novembre 2026, rilasciata sul CED

Email e PEC condividono il recupero degli accessi univoci per CF valido quando lo snapshot PDF è assente/null/vuoto. Il compositore indica la provenienza. Snapshot già presenti non vengono sostituiti; ambiguità o PIN non decifrabili mantengono l’omissione del blocco. Corpo congelato nella bozza, PDF e payload documentale invariati. [Contratto, test e gate](../../../docs/communications/ARCHIVE_PORTAL_ACCESS_2026-11-17.md).

Nuove sottoroute PEC ed Email della navigazione Solleciti. Generati e Posta Online
mantengono flussi e servizi esistenti. La nuova outbox non invia tramite il worker
browser Poste e non rigenera documenti.

L'identità è la riga batch definitiva e il documento Registro gaia_batch_item,
con numero riservato generated. Annualità esattamente [2021]. Eleggibilità
corrente riutilizzata dal Registro, inclusi saldo, storico inCASS, STEP e invii
non chiariti. Nessuna deduzione di consegna da sola accettazione SMTP.

Snapshot BYTEA: PDF mostrato e PDF MIME identici. Approvazione individuale legata
a hash/versione; rigenerazione della sorgente blocca invio prima del confine
sending. Prenotazione atomica del numero coordinata tramite trigger PostgreSQL
con ruolo_poste_dispatch_items; non aprire contemporaneamente campagne esterne
al portale Poste non registrate in GAIA.

Tentativi/evidenze nuovi nel namespace gaia_communications; nessuna modifica a
NoticeNotification o evidenze importate. Perfezionamento giuridico nel workflow
approvato dall'ufficio; email solo cortesia. Nessun reinvio di uncertain.

Documentazione autorevole: docs/communications (audit, API, operazioni,
collaudo, deployment/rollback). Nessun inventario/collaudo su dati di produzione
o caselle reali effettuato nel ciclo originario. Il controllo in sola lettura del 17 novembre è descritto nel report aggiornato sopra. Trasporto tuttora disabilitato.

## Verifica finale storica — 3 novembre 2026

La prova con get_tributi_avviso reale conferma che il default2021 resta in
gestione STEP e che un pagamento persistito dopo review blocca l'accodamento.
La configurazione interna usata nei test è esclusivamente sintetica: nessun
override tributario reale. Matrice completa in docs/communications/FINAL_REVIEW.md
e avanzamento in docs/communications/PROGRESS.md. Nessun deployment nel ciclo originario; il rilascio CED del 17 novembre è descritto sopra.

## Modelli ufficio — novembre 2026

Il catalogo Communications propone testi PEC/email con importo e termine del PDF 2021, bonifico, rateizzazione e accessi ICATASTO. Codice utenza/PIN provengono prioritariamente dallo snapshot del documento. Il ciclo successivo del 17 novembre rilascia sul CED il recupero dall’archivio univoco per CF valido, per il solo messaggio e senza cambiare il PDF; il conteggio 726 appartiene all’audit storico. Testi semplici modificabili e approvazione della versione distinta da quella del singolo messaggio. [Dettagli](../../../docs/communications/OFFICE_TEMPLATES_2026-11-07.md).

Dal 12 novembre l’amministratore può comporre anche layout a blocchi con logo
ufficiale, titoli, paragrafi, elenchi, link e pulsanti HTTPS. Le variabili si
inseriscono nei testi, le destinazioni dei link sono fisse. In composizione
l’anteprima messaggio e la modifica del layout si aprono su richiesta; il PDF
dell’avviso resta sotto i campi. Ogni modifica invalida l’approvazione e richiede
nuova verifica del PDF. Restano bloccanti i dati canonici obbligatori mancanti e
restano esclusi gli avvisi riconciliati con Poste.
[Contratto e verifiche](../../../docs/communications/RICH_TEMPLATES_2026-11-12.md).

## Blocchi ICATASTO condizionali — 17 novembre 2026

L'editor aggiunge paragrafo e pulsante ICATASTO con visibilità condizionata
alla presenza di entrambi i valori canonici `codice_utenza` e `pin_utenza`.
Se manca uno dei due, il blocco viene omesso da anteprima, bozza e MIME senza
bloccare la composizione per quei soli segnaposto. Le variabili richieste
altrove restano obbligatorie. Nessun recupero PIN o modifica del PDF.
La conversione esplicita dei modelli ufficio prepara una nuova versione da
revisionare e approvare; non cambia catalogo originale o modelli già approvati.
[Verifiche e stato reale del rilascio](../../../docs/communications/CONDITIONAL_TEMPLATES_2026-11-17.md).
