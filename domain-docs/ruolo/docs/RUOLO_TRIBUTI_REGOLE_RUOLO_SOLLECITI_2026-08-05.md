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
