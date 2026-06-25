# Presenze Phase C Decision

Ultimo aggiornamento: `2026-06-25`

## Decisione raccomandata

Per la `Fase C` adottare questa strategia:

1. introdurre `/presenze/...` come route pubblica primaria
2. mantenere `/inaz/...` come alias compatibile per almeno una release stabile
3. mantenere `module_inaz` invariato nella prima ondata
4. non rinominare subito tabelle e modelli `inaz_*`
5. rendere `Presenze*` canonico nel client e nell'API pubblica
6. decidere solo dopo se rimuovere davvero il legacy

## Motivazione

Questa strategia massimizza il valore e minimizza il rischio:

- il naming pubblico migliora subito
- i deep link esistenti non si rompono
- non si apre una migrazione DB ad alto costo senza ritorno immediato
- non si toccano i permessi in contemporanea al rename pubblico
- il rollback resta semplice

## Cosa diventa canonico

### Canonico subito

- route frontend e backend `/presenze/...`
- naming client `Presenze*`
- documentazione tecnica e operativa `Presenze`

### Legacy compatibile

- `/inaz/...`
- tipi alias `Inaz*`
- wrapper API `Inaz*`
- file/helper legacy rimasti come bridge

### Rinviato

- `module_inaz` -> `module_presenze`
- rename DB `inaz_*` -> `presenze_*`
- rimozione completa del legacy

## Cosa NON fare nella prima ondata

- non rinominare le tabelle Alembic/DB
- non cambiare capability e ACL insieme al rename route
- non rimuovere `/inaz` nello stesso rilascio in cui nasce `/presenze`
- non cambiare contemporaneamente dominio pubblico, storage e regole HR

## Sequenza esecutiva approvata

### Wave 1

- introdurre `/presenze` nel frontend
- introdurre `/presenze` nel backend
- mantenere `/inaz` come alias
- aggiornare link primari, docs e wiki routing

### Wave 2

- rendere `Presenze*` canonico nel client
- spostare nuovi sviluppi fuori dal naming `Inaz*`
- aggiungere check che impediscano nuovo legacy

### Wave 3

- misurare uso residuo di `/inaz`
- valutare se il rename di `module_inaz` serve davvero
- valutare se il rename DB serve davvero

### Wave 4

- solo se il valore lo giustifica:
  - deprecazione vera di `/inaz`
  - eventuale migrazione capability
  - eventuale migrazione DB

## Criteri per avviare Wave 1

- banca ore stabile
- casi CCNL principali coperti
- export HR mesi campione verificato
- perimetro test modulo sufficiente

## Criteri per NON procedere oltre Wave 2

Se una di queste condizioni resta vera, fermarsi:

- esistono integrazioni esterne dipendenti da `/inaz`
- i permessi sono ancora in assestamento
- il DB rename porta solo beneficio estetico
- il modulo non e ancora stabile lato HR

## Impatto stimato

### Wave 1 + Wave 2

- effort: `4-6` giorni netti
- rischio: `medio`

### Wave 3 + Wave 4

- effort aggiuntivo: `4-6` giorni netti o piu
- rischio: `medio-alto`

## Decisione finale

La Fase C va eseguita con:

- route/API pubbliche `Presenze`
- alias legacy `Inaz`
- nessun rename DB nella prima ondata
- nessun rename `module_inaz` nella prima ondata

Stato esecutivo al `2026-06-25`:

- `Wave 1` completata
- frontend canonico su `/presenze/...`
- backend compatibile su `/presenze/...` e `/me/presenze/...`
- `/inaz/...` e `/me/inaz/...` mantenuti come alias legacy
