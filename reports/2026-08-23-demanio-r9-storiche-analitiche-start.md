# GAIA/SISTER — Demanio_R9 copia sintetiche e avvio storiche analitiche

Data: 2026-08-23
Server: `serverCed`
Batch origine: `Demanio_R9` (`e3862317-8fa4-46fd-8c2b-23da253c40ef`)
Nuovo batch: `Demanio_R9_storiche_analitiche_20260823` (`398cb756-dc10-4351-844f-c4a9f4a2e0d6`)

## Richiesta

Ale ha chiesto:

1. copiare tutte le visure già scaricate in una cartella nel Desktop;
2. avviare lo scaricamento di tutte le visure **storiche analitiche**.

## Copia visure già scaricate

Cartella locale creata:

```text
/home/cbo/Desktop/Demanio_R9_visure_sintetiche_attualita_2026-08-23
```

Esito copia:

```text
copied_pdfs=3359
size=68M
```

Queste sono le visure già completate del batch origine. Il DB live indicava:

```text
docs=3359
requests=3359
SUM(file_size)=63774321 bytes
```

## Verifica tipo delle visure origine

Prima dell'avvio del nuovo batch è stato verificato che il batch origine contiene:

```text
tipo_visura = Sintetica
request_type = <null> / default worker ATTUALITA
purpose = visura_pdf
count = 3359
```

Quindi le visure già scaricate sono **sintetiche di attualità**, non storiche analitiche.

## Nuovo batch storiche analitiche

È stato creato un nuovo batch clonando le 3359 richieste completate dal batch origine e impostando:

```text
tipo_visura = Analitica
request_type = STORICA
purpose = visura_pdf
status iniziale richieste = pending
```

Il batch è stato avviato in stato `processing` con la stessa credenziale SISTER già usata dal batch origine:

```text
batch_id = 398cb756-dc10-4351-844f-c4a9f4a2e0d6
name = Demanio_R9_storiche_analitiche_20260823
status = processing
total_items = 3359
credential_id = 62a686a7-cdb4-4ab6-a6b8-74fca19a88d8
```

## Verifica pickup worker

Il worker `gaia-elaborazioni-worker-visure` ha preso in carico il batch:

```text
Batch 398cb756-dc10-4351-844f-c4a9f4a2e0d6 prelevato dalla coda di lavorazione
Batch 398cb756-dc10-4351-844f-c4a9f4a2e0d6 preso in carico per utente 1
```

Nel log della prima richiesta il worker ha compilato la form con:

```text
tipo=Analitica
```

## Stato iniziale verificato

Dopo l'avvio, il DB live indicava:

```text
status = processing
total_items = 3359
completed_items = 3
failed_items = 0
skipped_items = 0
current_operation = Lavorazione Marrubiu Fg.6 Part.836
```

Distribuzione richieste:

```text
Analitica | STORICA | completed  | 3
Analitica | STORICA | pending    | 3355
Analitica | STORICA | processing | 1
```

Documenti già prodotti dal nuovo batch:

```text
Analitica | STORICA | docs=3
```

## Stato

- Copia sintetiche attualità su Desktop: **completata**.
- Batch storiche analitiche: **avviato e in lavorazione**.
- Primo pickup worker e primi PDF storici analitici: **verificati da DB e log**.

## Attenzioni

- Il batch è lungo (`3359` richieste) e continuerà a lavorare sul server.
- Se compaiono CAPTCHA manuali o retry SISTER, andranno gestiti come nel recupero precedente.
- Non è stato eseguito push Git; questa è un'operazione runtime/DB, non una modifica codice.
