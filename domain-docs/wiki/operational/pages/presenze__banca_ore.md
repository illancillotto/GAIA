# Pagina Banca Ore Presenze

## Scopo

La pagina `/presenze/banca-ore` aiuta HR a controllare il saldo banca ore importato da Presenze, applicare rettifiche manuali e usare una proposta di liquidazione guidata.

## Cosa puo fare l'operatore

- leggere saldo importato, saldo effettivo e liquidato
- aprire il dettaglio di un collaboratore
- verificare snapshot mensili Presenze e workflow rettifiche
- capire se una quota e:
  - liquidabile
  - da mantenere in banca ore
  - da revisione HR
- precompilare una liquidazione con il pulsante `Proponi liquidazione`

## Regole chiave

- la quota candidata nasce dallo straordinario del periodo classificato dal motore CCNL
- la quota proposta non puo superare il saldo banca ore disponibile
- se il profilo contrattuale e mancante, o derivato quando la policy non lo consente, la quota candidata passa a revisione HR
- una quota puo restare in banca ore anche quando esiste saldo disponibile, se il periodo non offre abbastanza straordinario candidabile
- la policy che governa questi passaggi si configura da `/presenze/configurazione`
- nella configurazione e disponibile anche uno storico revisioni della policy, utile per ricostruire chi ha cambiato i criteri di proposta

## Dati utili

- collaboratore o matricola
- intervallo di riferimento
- profilo contrattuale (`operaio`, `impiegato`, altro)
- motivazione della liquidazione o della rettifica

## Lettura della guida liquidazione

- `Liquidabile`: quota che GAIA puo proporre subito nel form
- `Resta in banca ore`: saldo non coperto dalla quota straordinario candidabile
- `Da revisione HR`: quota che richiede conferma umana prima di essere liquidata

## Prossimi passi

Indica collaboratore e periodo: posso aiutarti a leggere il saldo, capire la proposta o verificare perche una quota e finita in revisione HR.
