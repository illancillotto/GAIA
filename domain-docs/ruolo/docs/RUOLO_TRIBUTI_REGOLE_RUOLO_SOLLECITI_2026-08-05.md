# Ruolo tributi - Regole ruolo e preview solleciti

Data: 2026-08-05

## Regola operativa

Le `Regole ruolo` governano quali annualita GAIA possono essere incluse nello stesso avviso di sollecito.
Quando l'operatore configura un range multi-annualita, per esempio `2024-2025`, la UI salva una regola annuale per ciascun anno, cosi ogni ruolo puo avere date proprie:

- scadenza pagamento bonario per annualita;
- decorrenza maggiorazione calcolata automaticamente dal giorno successivo alla scadenza bonaria;
- fallback/minimo interessi per annualita;
- percentuali e modalita interessi della regola.

Aggiornamento 2026-10-26: la regola salva anche `print_bollettino` (default
`true`), `payment_due_date` e `bollettino_version` (`v1` default, `v2` modello
Poste). La UI espone la versione in `Gestisci regole calcolo` e nel riepilogo.
Per avvisi multiannualita, basta una regola con bollettino disattivato per
escluderlo; versione, data avviso, causale ed esercizio provengono dalla regola
dell'anno piu recente. La scelta vale per preview e stampe successive e viene
copiata nello snapshot del batch; cambiare la regola non riscrive documenti
gia generati. Le regole esistenti restano v1 dopo la migration `20261026_0900`.
Misure e differenze dei layout sono in `RUOLO_TRIBUTI_TEMPLATE_GAIA_2026-07-23.md`
e `MANUALE_VERIFICA_BOLLETTINI_TD896.md`.

Aggiornamento 2026-10-27 (termine dalla notifica): `payment_deadline_mode`
sceglie tra `fixed_date` (default retrocompatibile) e `notification_60_days`.
Dal 2026-10-28 in `Regole ruolo` le date restano visibili per entrambe le
modalita e sono conservate anche passando al termine a 60 giorni. Con questa
modalita e bollettino abilitato, `payment_due_date` e obbligatoria: il backend
rifiuta il salvataggio senza data e blocca la generazione da regole o snapshot
storici senza data. Senza bollettino la data puo essere assente. Il fallback
legacy a 30 giorni resta limitato alla modalita a data fissa.
La modalita dell'anno piu recente prevale negli avvisi multiannualita e viene
copiata nello snapshot del batch. Il termine relativo e riportato nella prima
pagina e nei campi DOCX, senza calcolare una data di notifica dalla stampa.
I bollettini v1/v2 stampano la data fissa salvata seguita da ` - Rata Unica`
su entrambi i tagliandi. Solo nella modalita a 60 giorni compaiono il termine e
le avvertenze prima del portale, seguito dai contatti degli uffici e dalle
informazioni sul sito del Consorzio, e l'intimazione del Consorzio con triangolo
rosso prima dei due QR WhatsApp/Irrighiamo Insieme. Nel solo box importo della
prima pagina di un avviso del solo 2021 si stampa `scadenza il gg/mm/aaaa`
seguito da `e comunque entro 60 giorni dalla data di notifica`; senza data esplicita si
stampa solo il termine relativo. Non cambia la persistenza delle regole.
La nuova scelta riguarda il termine e i testi stampati: non cambia il motore
di calcolo degli interessi ne la scadenza bonaria. Richiede la migration
`20261027_1300`, successiva a `20261027_1100`; al termine di questo ciclo non
e applicata al server degli uffici. Verifiche e limiti in
[scadenza dalla notifica](RUOLO_SCADENZA_NOTIFICA_2026-10-27.md).

Aggiornamento 2026-10-26 (numero avviso): la regola salva `notice_number_source`
(`gaia` default, `incass`), migration `20261026_1600`. Con `incass` GAIA non
genera un nuovo numero: ogni avviso dell'anno della regola diventa un avviso a
se, con numero = numero avviso inCASS a 15 cifre, usato come codice cliente
TD 896, causale del bollettino e suffisso del file sul NAS; non viene
prenotato alcun progressivo GAIA. L'esercizio resta quello configurato nella
regola (per il 2021: `2021`). Gli avvisi di anni con regola `gaia` dello stesso
contribuente restano raggruppati in un unico avviso GAIA. Un avviso senza
numero inCASS valido blocca il batch con errore esplicito.

## Chi paga: avvisi di deceduti e vendite (2026-10-27)

Tabella `ruolo_tributi_payer_assignments` (migration `20261027_0900`): per
ogni avviso al massimo un pagatore attivo diverso dall'intestatario, con
motivo `decesso` (erede), `vendita` (acquirente/voltura) o `ufficio`
(indicazione dell'ufficio) e nota. Sostituire o rimuovere il pagatore
annulla la riga precedente (`voided_at`), che resta come storico.

- Il pagatore deve esistere in anagrafica (persona o societa, cercato per CF
  o partita IVA): se manca, va inserito prima da Utenze. Non puo coincidere
  con l'intestatario.
- API: `GET|PUT|DELETE /ruolo/tributi/avvisi/{id}/payer`; le modifiche
  richiedono `ruolo.tributi.manage_status`. In UI e la card "Chi paga" nel
  dettaglio dell'avviso in `/ruolo/tributi`.
- Solleciti: la selezione resta per intestatario (CF dell'avviso). Ogni
  avviso con pagatore diventa un sollecito a parte intestato al pagatore
  (nome, CF, indirizzo dell'anagrafica, cartella NAS del pagatore); gli
  avvisi dello stesso intestatario senza pagatore restano raggruppati. Nella
  tabella del sollecito, sotto il numero avviso, compare "intestato a
  <intestatario>" e, per decesso/vendita, "dovuto come erede/acquirente".
  Con la regola `incass` il numero resta quello inCASS.
- L'idoneita registro non segnala `destinatario_discordante` se il documento
  e intestato al pagatore attivo.
- Caricamento iniziale: `python -m app.scripts.import_payer_assignments
  file.csv [--apply]`, CSV `avviso_id;avviso;cf_pagatore;motivo;note`
  separato da `;`. Senza `--apply` e una prova; i pagatori non in anagrafica
  sono segnalati e saltati, quelli gia collegati non vengono duplicati.

Gli avvisi da non sollecitare (annullati, esubero, caricati ad altri) si
gestiscono con lo stato operativo esistente, non con questa tabella.

## Tasso interessi

Dal 2026-08-06 il tasso interessi effettivo della Regola ruolo e:

```text
Euribor medio 6 mesi + tasso da delibera
```

La modal `Regole ruolo` espone quindi due campi separati:

- `% Euribor medio 6 mesi`;
- `% tasso da delibera`.

Il campo Euribor puo essere compilato manualmente oppure recuperato con `Recupera da BCE`.
Il recupero automatico usa il Data Portal BCE, serie Euribor 6-month, filtrata sull'anno iniziale della policy.
GAIA salva sulla policy anche:

- URL sorgente BCE;
- periodo di riferimento;
- timestamp di recupero.

Questi metadati alimentano il link `verifica dato BCE`, cosi l'operatore puo ricontrollare la fonte del valore usato nel calcolo.

Le regole annuali generate dallo stesso nome base restano pero un unico gruppo logico. Esempio:

- `Ruoli 2024 e 2025 2024`
- `Ruoli 2024 e 2025 2025`

Queste due policy devono essere trattate come lo stesso gruppo di sollecito.

## Comportamento atteso in `/ruolo/tributi`

La lista tributi continua a mostrare una riga per avviso/annualita contabile. Se la stessa utenza ha un ruolo 2024 e un ruolo 2025, la lista puo quindi mostrare due righe.

Il pulsante `Avviso sollecito`, invece, deve produrre una preview unica quando:

- il CF/P.IVA e lo stesso;
- le annualita sono coperte da Regole ruolo attive dello stesso gruppo logico;
- gli avvisi hanno saldo aperto e annualita gestita internamente da GAIA/Consorzio.

Cliccando dal 2024 o dal 2025 il risultato deve essere equivalente:

- `years_json`: `[2024, 2025]`;
- `avviso_ids_json`: stessi avvisi;
- `notice_number`: identico;
- PDF preview con entrambe le annualita nello stesso avviso.

## Ripresa avvisi 2021 — 2026-10-21

I gestori annualita possono avere range attivi sovrapposti. Per attribuire
un avviso prevale il gestore con anno iniziale piu recente, poi anno finale
piu vicino (i limiti aperti vengono dopo quelli definiti). A parita di range
prevale la modifica piu recente, quindi l'ID decrescente per stabilita.
I filtri per gestore continuano a selezionare il suo intero range.

Per riprendere gli avvisi 2021 non notificati nella precedente tornata:

1. In `Gestisci regole`, creare `Avvisi 2021`, chiave `avvisi_2021`, anno da
   e anno a `2021`, policy `internal_gaia`, regola attiva. Il range STEP
   `2018-2021` puo restare attivo e invariato.
2. In `Regole ruolo`, configurare il 2021 con `Solo avvisi non notificati`,
   date e importi deliberati. Questa opzione esclude gli avvisi con ricevuta
   PEC di consegna o data documentata di ricezione della raccomandata.
   Un semplice stato di invio o accettazione PEC non prova la notifica.
3. Selezionare il periodo `Avvisi 2021` e il solo anno `2021` nel wizard,
   oppure usare la preview rapida dalla singola posizione.

Il wizard e il backend supportano annualita dal 2021; la generazione richiede
comunque saldo aperto e gestione `internal_gaia`. La sola sovrapposizione
non abilita gli avvisi affidati a un gestore esterno. Le regole di calcolo
mantengono la propria validazione dei range, distinta dai gestori annualita.

### Contratto API e persistenza

`POST /ruolo/tributi/year-managers` e `PUT /ruolo/tributi/year-managers/{id}`
accettano i range sovrapposti con lo schema esistente. Restano `422` per
range invertiti o chiavi non valide, `404` per modifica/cancellazione di ID
inesistenti, `401` senza autenticazione e `403` senza permesso di gestione.
Le mutazioni richiedono `ruolo.tributi.manage_status`; la creazione registra
`updated_by`. Una modifica non valida viene annullata senza alterare il gestore
persistito. Disattivare o cancellare la regola 2021 ripristina la precedenza STEP.
Nessuna nuova tabella, colonna, migration o modifica ai payload REST.

## Numero avviso

La preview rapida usa `filters.preview_only=true` e `filters.policy_group=true`.
Per evitare numeri diversi sullo stesso avviso logico, il backend riusa il `notice_number` gia generato per una preview con la stessa identita:

- CF/P.IVA normalizzato;
- insieme annualita;
- insieme avvisi inclusi;
- anno emissione.

Le generazioni definitive non sono vincolate da questa regola di riuso preview: il progressivo ufficiale continua a essere calcolato sul flusso persistente.

## Rateizzazioni inCASS

Gli importi e il saldo operativo possono derivare da inCASS, inclusi i casi rateizzati o parzialmente pagati.
Questo non deve cancellare il collegamento alla Regola ruolo: `calculation_policy_id` e `calculation_policy_name` restano quelli della policy annuale GAIA, cosi `reminder_enabled` resta vero quando l'annualita e coperta da regola attiva.
