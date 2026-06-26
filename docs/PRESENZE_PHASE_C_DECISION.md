# Presenze Phase C Decision

Ultimo aggiornamento: `2026-06-25`

## Esito

La `Fase C` del rename prodotto e runtime e da considerare `eseguita`.

Risultato raggiunto:

- namespace pubblico canonico: `presenze`
- naming applicativo canonico: `Presenze*`
- package backend canonico: `app.modules.presenze.*`
- route frontend legacy rimosse
- alias pubblici runtime legacy rimossi

## Decisione finale consolidata

Il rename `Inaz -> Presenze` e stato chiuso sul perimetro applicativo.

Non rientrano piu nella stessa change di prodotto:

- rename fisico delle tabelle legacy `inaz_*`
- riscrittura della migration history Alembic
- consolidamento definitivo del repository esterno `presenze-scraper`

Questi tre punti vanno trattati come iniziative separate di infrastruttura o storage, non come parte del rename funzionale del modulo.

## Cosa e canonico oggi

- route e navigazione: `presenze`
- chiave modulo runtime: `presenze`
- model/schema/client types: `Presenze*`
- documentazione operativa del modulo: `Presenze`

## Cosa resta legacy ma accettato

- nomi storici nelle migration Alembic gia versionate
- tabelle fisiche `inaz_*`
- path reali verso il repo esterno `/home/cbo/CursorProjects/presenze-scraper`
- memo storici o analisi di transizione che parlano del vecchio naming

## Guardrail

Da qui in avanti:

- nuovo codice runtime non deve reintrodurre `Inaz*`
- nuova documentazione operativa non deve usare `Inaz` come nome corrente del modulo
- eventuali rename del DB fisico o del repo esterno richiedono piano dedicato, verifica deploy e rollback esplicito

## Prossimo perimetro corretto

Se si vuole proseguire oltre il rename prodotto, i temi residui sono:

1. rinominare le tabelle `inaz_*` con migrazione dati e rollback
2. consolidare definitivamente il repository esterno `presenze-scraper` e tutti i mount/config associati
3. ripulire o archiviare i documenti storici che citano il naming precedente
