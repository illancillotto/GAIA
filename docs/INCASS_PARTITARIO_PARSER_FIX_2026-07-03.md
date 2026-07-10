# Fix parser inCASS partitario - 2026-07-03

Riscrittura del parsing della modale partitario inCASS
(`backend/app/modules/elaborazioni/capacitas/apps/incass/parsers.py`) e procedura
di ripopolamento dei dati storici. Supera le verifiche documentate in
`INCASS_PARTITARIO_PARSING_VERIFICA_2026-07-01.md` e
`INCASS_PARTITARIO_MARRUBIU_VERIFICA.md`.

## Bug corretti (tutti verificati sulle fixture reali)

1. **Importi nella colonna sbagliata + manut spurio.** Le righe "domanda irrigua"
   con coltura del tipo `MAIS 1 I` / `MEDICA 1` (classe "1", flag irriguo "I")
   producevano `importo_manut_euro = "1"` (la classe scambiata per un importo) e
   l'importo reale finiva in `importo_ist_euro` (0985). L'importo singolo di quelle
   righe appartiene alla colonna **Irrig. (0668)**: verificato posizionalmente sul
   layout monospace e contabilmente (pau: somma particelle 50,73 + consumo contatore
   231,96 = 282,69 ≈ totale 0668 282,70). ~510 righe affette nelle sole fixture.
2. **Particelle fantasma da righe senza importi.** `40 28 9 1308 1 MAIS 1 I` veniva
   letta come `foglio=28 particella=9 sup_cata=1308`; ora produce correttamente
   `foglio=9 particella=1308 sup_cata=1` senza importi.
3. **Anno hardcoded nel filtro consumi.** `_looks_like_consumption_row` filtrava solo
   righe che iniziavano con `2025`; sostituito da una macchina a stati: da
   `Consumi da contatore:` fino a `Legenda`/nuova `Partita` non si parsa nulla,
   qualunque sia l'anno.
4. **Importo perso nel merge righe riepilogo+domanda.** L'importo Irrig. della riga
   domanda veniva scartato quando esisteva la riga riepilogo della stessa particella.
5. **Particella testuale persa.** `31 6 acque 650 2,37 1,69` (Marrubiu) veniva
   scartata; ora è emessa con `particella="acque"`.

## Nuova architettura del parser

La modale è testo monospace a **colonne a larghezza fissa** con header identico
byte-per-byte in tutte le fixture:

```
Dom. Dis. Fog. Part.  Sub Sup.Cata.  Sup.Irr. Colt.     Manut.   Irrig.     Ist.
```

- **Parse posizionale** (`_parse_particella_row_by_columns`): le righe raw (spaziatura
  preservata, estratte splittando su `<br>` senza collassare gli spazi) vengono lette
  assegnando ogni token alla colonna il cui bordo destro è più vicino al bordo destro
  del token (tolleranza 2 caratteri; scarto massimo osservato sulle modali reali: 1).
  Validazione rigorosa per tipo di colonna; qualunque violazione fa ricadere la riga
  sul fallback.
- **Fallback a token** (`_parse_particella_row_by_tokens`): per input già collassato
  (es. `info_text` storico a DB). Distingue gli importi (sempre con virgola decimale)
  dagli interi/classi coltura; gestisce anche le forme legacy prodotte dal vecchio
  parser (riga fusa a 10 token e riga riepilogo+domanda concatenata).
- **Due tipi di riga, non righe "spezzate"**: la riga *riepilogo* porta Manut.+Ist.
  (0648+0985), la riga *domanda irrigua* porta coltura e solo Irrig. (0668).
  L'assemblatore le fonde per particella (chiave: distretto+foglio+particella+sub+
  sup.cata.), gestendo più colture sulla stessa particella (es. ferraresi fog.16
  part.2: SOIA+SORGO+MAIS, ognuna con il proprio importo irriguo).

Invarianti verificate su tutte le 14 fixture reali (2.288 righe): le righe domanda
hanno sempre un solo importo, sempre in Irrig.; le righe riepilogo hanno sempre
Manut. e Ist. in coppia. Parse posizionale e fallback a token producono risultati
**identici** su tutte le fixture.

## Verifica contabile

Su 28 partite con totali dichiarati in testa: 26 riconciliano al centesimo sia su
0648 (somma Manut.) sia su 0985 (somma Ist.). Le eccezioni sono i contributi minimi
forfettari (serra: 30/20 euro) e arrotondamenti di 6-10 centesimi del documento
sorgente. Il totale 0668 di partita NON riconcilia con le particelle per costruzione
(include l'imposta da consumo contatore e il minimo forfettario di 70 euro).

## Test

- `backend/tests/test_incass_parsers.py`: 21 test (sintetici = percorso fallback,
  fixture reali = percorso posizionale, guard-clause unit test).
- `backend/tests/elaborazioni/capacitas/test_incass_partitario_parsing.py`: 5 test
  di caratterizzazione aggiornati al comportamento corretto (prima codificavano i
  bug: `manut=5.42`/`44.82` su righe Irrig., "acque" scartata, riconciliazione 0668
  contro il minimo forfettario).
- Copertura: il flusso partitario di `parsers.py` è coperto al 100%; il file nel suo
  complesso è al 78% (le parti scoperte sono ricerca avvisi, dettaglio/PDF e
  `_derive_payment_status`, non toccate da questo fix; `client.py` è a 0% perché
  client HTTP asincrono senza test).

## Ripopolamento dei dati storici (DA ESEGUIRE)

Tutti i 12.348 avvisi incass 2025 hanno `raw_detail_json.partitario.raw_html`
popolato. Impatto misurato su un campione di 400 avvisi reali riparsati:
**400/400 cambiano**, 136 righe con manut spurio "1", totale 0648 salvato gonfiato
di ~1,92 M€ (il parser deployato scambiava superfici in mq per importi), 0668 quasi
tutto assente.

`materialize_ruolo_from_incass.py` ha ora il flag `--reparse-partitario` (forza il
re-parse dal raw ignorando le partite già materializzate nel payload) e preferisce
`raw_html`/`info_html` a `info_text`:

Aggiornamento 2026-07-09: il re-parse corretto non basta se la materializzazione
riconverte i valori già normalizzati dal parser. `_to_decimal()` nel materializzatore
deve trattare il punto come separatore decimale quando non è presente la virgola
italiana; altrimenti `18.4994` viene risalvato come `184994`.

```bash
# dry-run
docker compose exec backend python scripts/materialize_ruolo_from_incass.py \
  --from-year 2025 --to-year 2025 --replace-year --reparse-partitario

# esecuzione reale (valutare backup DB prima: --replace-year svuota l'anno)
docker compose exec backend python scripts/materialize_ruolo_from_incass.py \
  --from-year 2025 --to-year 2025 --replace-year --reparse-partitario --apply
```

Verifica minima post-run sulle superfici:

```sql
WITH base AS (
  SELECT sup_irrigata_ha::numeric irr, sup_catastale_are::numeric are
  FROM ruolo_particelle
  WHERE anno_tributario = 2025 AND sup_irrigata_ha IS NOT NULL
)
SELECT count(*) AS rows,
       count(*) FILTER (WHERE irr > 1000) AS over_1000,
       count(*) FILTER (WHERE are > 0 AND abs(irr - are) < 0.0001) AS eq_are,
       percentile_disc(0.5) WITHIN GROUP (ORDER BY irr) AS p50,
       percentile_disc(0.9) WITHIN GROUP (ORDER BY irr) AS p90,
       max(irr) AS max_irr
FROM base;
```

Esito atteso dopo il fix 2026-07-09: `rows=19456`, `over_1000=0`, `eq_are=0`,
`p50=0.1000`, `p90=1.0000`, `max_irr=49.7000`.

Dopo il ripopolamento confrontare i totali per comune con
`INCASS_TOP20_TOTALI_PER_COMUNE_2026-07-01.csv` (attesi scostamenti coerenti con il
fix: 0648/0985 per-particella corretti, 0668 ora valorizzato).

Nota: le `partite` materializzate dentro `raw_detail_json` restano quelle vecchie
(lo script non riscrive il payload sorgente); la fonte di verità per il re-parse è
`raw_html`. `backfill_ruolo_particelle_from_incass.py` legge ancora le partite
salvate nel payload: non usarlo per il ripopolamento, usare materialize.
