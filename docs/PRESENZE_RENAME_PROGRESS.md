# Presenze Rename Progress

Ultimo aggiornamento: `2026-06-25`

## Obiettivo

Sostituire progressivamente il termine `Inaz` con un naming di dominio coerente per il prodotto.

Nome target lato utente:

- `Presenze` come nome funzionale del dominio
- `Giornaliere` come etichetta operativa dove il contesto e la pagina sono centrati sul cartellino giornaliero

Vincolo attuale:

- il namespace tecnico `inaz` resta attivo in route, API, tipi, modelli e tabelle finche non viene eseguita la fase tecnica successiva

## Stato generale

Stato programma: `in corso`

Fase corrente: `Fase B - preparazione refactor tecnico compatibile`

Completamento stimato Fase A: `100%`

## Completato

- Sidebar piattaforma:
  - modulo `/inaz` esposto come `Giornaliere`
- Titoli, breadcrumb e label principali del modulo:
  - dashboard
  - giornaliere
  - banca ore
  - export
  - sync
  - anomalie
  - collaboratori
  - dettaglio collaboratore
  - configurazione
  - festivita
  - recuperi
  - organigramma
- Testi operativi principali:
  - badge modulo
  - CTA di navigazione
  - messaggi di empty state principali
  - parte dei messaggi di errore e conferma
- Sezione utenti GAIA:
  - modulo `Inaz` rinominato in `Giornaliere` nelle label utente
- Cruscotto operatori:
  - riepilogo e metriche esposte come `giornaliere`
- Wiki context hints:
  - dominio `/inaz` etichettato come `Giornaliere`
  - pagina banca ore etichettata come `Banca ore`
- Bootstrap sezioni backend:
  - label sezione aggiornate da `Inaz - ...` a `Giornaliere - ...`
- Graphify:
  - aggiornato con `make graphify-inaz-code`

## In corso

- Preparazione del backlog tecnico per gli alias `Presenze`
- Separazione tra naming utente e naming tecnico legacy
- Layer frontend compatibile avviato:
  - alias `Presenze*` in `frontend/src/types/api.ts`
  - wrapper `Presenze` in `frontend/src/lib/api.ts`
- Prime adozioni applicative completate:
  - dashboard modulo
  - export modulo
  - sync modulo
  - collaboratori modulo
  - festivita modulo
  - settings modulo
  - anomalie modulo
  - recuperi modulo
  - banca ore modulo
  - giornaliere modulo
  - dettaglio collaboratore modulo
  - configurazione modulo

## Residuo noto della Fase A

- la Fase A e considerata chiusa sul perimetro utente principale
- il nome tecnico `inaz` resta intenzionalmente presente in:
  - cartella `frontend/src/app/inaz`
  - route `/inaz/...`
  - `module_inaz`
  - tipi `Inaz*`
  - modelli e tabelle `inaz_*`

## Verifiche eseguite

- smoke test frontend locale: `18/18` verdi
- ricerca mirata delle etichette utente residue con `rg`
- controllo mirato: nel perimetro principale non risultano piu titoli o breadcrumb utente con `Inaz`
- review finale del perimetro Fase A completata prima del commit dedicato
- smoke test frontend rieseguiti dopo l'introduzione del layer compatibile `Presenze`
- smoke test frontend rieseguiti dopo la prima adozione reale dei wrapper `Presenze`

## Decisioni prese

- non cambiare nella Fase A route, tipi o storage
- usare `Giornaliere` nelle superfici operative del modulo
- usare `Presenze` come termine di dominio nei documenti di refactor e nella futura fase tecnica

## Prossimo passo

Aprire la Fase B:

- introdurre naming tecnico compatibile `Presenze`
- mantenere compatibilita con il namespace pubblico legacy `inaz`
