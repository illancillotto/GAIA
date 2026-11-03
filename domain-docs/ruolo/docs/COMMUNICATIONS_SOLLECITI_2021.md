# Invio PEC/email dei solleciti2021

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
o caselle reali effettuato. Trasporto disabilitato per default.

## Verifica finale

La prova con get_tributi_avviso reale conferma che il default2021 resta in
gestione STEP e che un pagamento persistito dopo review blocca l'accodamento.
La configurazione interna usata nei test è esclusivamente sintetica: nessun
override tributario reale. Matrice completa in docs/communications/FINAL_REVIEW.md
e avanzamento in docs/communications/PROGRESS.md. Nessun deployment.
