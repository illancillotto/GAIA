# Ruolo tributi - Regole ruolo e preview solleciti

Data: 2026-08-05

## Regola operativa

Le `Regole ruolo` governano quali annualita GAIA possono essere incluse nello stesso avviso di sollecito.
Quando l'operatore configura un range multi-annualita, per esempio `2024-2025`, la UI salva una regola annuale per ciascun anno, cosi ogni ruolo puo avere date proprie:

- scadenza pagamento bonario per annualita;
- decorrenza maggiorazione calcolata automaticamente dal giorno successivo alla scadenza bonaria;
- fallback/minimo interessi per annualita;
- percentuali e modalita interessi della regola.

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

