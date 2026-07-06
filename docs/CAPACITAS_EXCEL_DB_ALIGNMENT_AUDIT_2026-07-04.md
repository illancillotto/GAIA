# Audit allineamento Excel Capacitas vs database GAIA

Data audit: 2026-07-04.

## Provenienza input

File analizzato durante l'audit locale:

```text
ct0902026_grid (3).xlsx
```

Artifact locali generati durante l'audit locale:

```text
/tmp/gaia_capacitas_audit/audit_summary.json
/tmp/gaia_capacitas_audit/audit_surface_semantics.json
/tmp/gaia_capacitas_audit/sample_excel_rows_missing_in_cat_utenze_2025.csv
/tmp/gaia_capacitas_audit/sample_cat_utenze_rows_missing_in_excel.csv
/tmp/gaia_capacitas_audit/sample_ruolo_rows_missing_in_excel_by_cat_key.csv
/tmp/gaia_capacitas_audit/sample_ruolo_rows_missing_in_cat_utenze_by_cat_key.csv
/tmp/gaia_capacitas_audit/sample_cf_mismatch_common_utenza_key.csv
/tmp/gaia_capacitas_audit/sample_sup_cat_mismatch_common_utenza_key.csv
/tmp/gaia_capacitas_audit/sample_sup_irr_mismatch_common_utenza_key.csv
```

Nota di riproducibilita:

- i path locali sopra non sono artefatti versionati del repository;
- i numeri riportati in questo documento valgono per lo snapshot Excel usato il 2026-07-04 e per il database GAIA disponibile nella stessa data;
- per ri-eseguire l'audit serve esplicitare in un runbook o script dedicato: query SQL usate, normalizzazioni chiave e sorgente Excel di input.

## Sintesi

Il file Excel Capacitas `ct0902026` non e allineato 1:1 al database GAIA attuale.
Il DB contiene una base `cat_utenze_irrigue` solo per `anno_campagna=2025`, con
`91.977` righe, mentre l'Excel contiene `186.017` righe. Il file Excel e quindi un
export Capacitas piu ampio/recente rispetto alla base di calcolo 2025 caricata in
GAIA.

Il ripopolamento ruolo 2025 da inCASS post-fix risulta invece coerente sui controlli
specifici del parser:

- nessuna particella fantasma con foglio `2024/2025/2026`;
- `96.926/99.848` righe ruolo 2025 hanno match catastale `matched`;
- `importo_irrig` e `importo_ist` sono valorizzati dopo il fix;
- il totale manut non mostra piu il gonfiamento patologico pre-fix.

Restano differenze di perimetro tra ruolo 2025, base Capacitas DB 2025 ed export
Capacitas 2026. Queste differenze non vanno trattate come errore parser, ma come
disallineamento dati/snapshot da governare.

## Dataset

### Excel Capacitas

| Metrica | Valore |
| --- | ---: |
| Righe totali | 186.017 |
| Righe con chiave foglio/particella valida | 185.990 |
| Chiavi catastali distinte | 143.817 |
| Chiavi utenza distinte | 155.164 |
| Righe senza foglio | 5 |
| Righe senza codice fiscale | 16.002 |
| Somma `SUP. CATASTALE` mq | 937.335.439 |
| Somma `SUP. IRRIGATA` mq | 184.601.347 |

Distribuzione flag Excel:

| Campo | Distribuzione |
| --- | --- |
| `MANUTENZIONE` | `1`: 157.103, `0`: 28.884, `2`: 29, `3`: 1 |
| `DOMANDA > 0` | 28.884 righe |

### Database GAIA

| Tabella | Perimetro | Righe |
| --- | --- | ---: |
| `cat_utenze_irrigue` | `anno_campagna=2025` | 91.977 |
| `cat_particelle` current | `is_current=true` | 287.387 |
| `ruolo_particelle` | `anno_tributario=2025` | 99.848 |

`cat_utenze_irrigue` contiene un solo anno campagna (`2025`) e un solo batch, creato
il 2026-04-28.

## Excel vs `cat_particelle`

Confronto su chiave catastale normalizzata:

```text
codice catastale + foglio + particella + subalterno
```

| Metrica | Valore |
| --- | ---: |
| Righe Excel con particella presente in `cat_particelle` current | 139.910 |
| Righe Excel non presenti in `cat_particelle` current | 46.080 |
| Chiavi catastali Excel distinte presenti in `cat_particelle` current | 105.162 |
| Chiavi catastali Excel distinte mancanti in `cat_particelle` current | 38.655 |

Interpretazione: il catasto corrente GAIA non copre tutto l'export Capacitas 2026.
Questo e un disallineamento del registro catastale/current rispetto al nuovo export,
non un effetto del parser inCASS.

## Excel vs `cat_utenze_irrigue`

Confronto su chiave utenza normalizzata:

```text
COM + FRA + CCO + foglio + particella + subalterno
```

| Metrica | Valore |
| --- | ---: |
| Righe Excel con chiave utenza presente in DB | 113.566 |
| Righe Excel senza chiave utenza in DB | 72.424 |
| Righe DB con chiave utenza presente in Excel | 88.848 |
| Righe DB senza chiave utenza in Excel | 3.129 |
| Chiavi utenza Excel distinte presenti in DB | 88.138 |
| Chiavi utenza Excel distinte mancanti in DB | 67.026 |
| Chiavi utenza DB distinte mancanti in Excel | 3.110 |

Top comuni delle righe Excel mancanti in `cat_utenze_irrigue`:

| Comune | Righe mancanti |
| --- | ---: |
| CABRAS | 19.588 |
| RIOLA SARDO | 7.808 |
| SAN VERO MILIS | 7.111 |
| TERRALBA | 4.177 |
| NURACHI | 3.316 |
| SANTA GIUSTA | 2.968 |
| MARRUBIU | 2.199 |
| ORISTANO | 2.184 |
| ARBOREA | 2.143 |
| TRAMATZA | 2.007 |

Interpretazione: il DB 2025 non contiene una parte rilevante del nuovo export
Capacitas, in particolare su Cabras/Riola/San Vero Milis. Per ottenere allineamento
serve importare o sincronizzare questo export 2026 in una tabella/staging dedicata,
oppure aggiornare `cat_utenze_irrigue` con un batch 2026.

## Qualita sui record comuni

Sulle `88.138` chiavi utenza comuni tra Excel e `cat_utenze_irrigue`:

| Controllo | Esito |
| --- | ---: |
| CF non vuoti discordanti | 399 |
| Nominativi non vuoti discordanti | 432 |
| Superficie catastale discordante | 1.529 |
| Superficie irrigata/irrigabile discordante | 87.528 |

La discordanza `SUP. IRRIGATA` non va letta in blocco come errore: per la maggior
parte delle righe con `MANUTENZIONE > 0`, l'Excel ha `SUP. IRRIGATA = 0`, mentre il
DB 2025 conserva `sup_irrigabile_mq` valorizzata.

Controllo ristretto alle righe Excel con `DOMANDA > 0` o `SUP. IRRIGATA > 0`:

| Metrica | Valore |
| --- | ---: |
| Righe comuni con domanda/sup irrigata positiva | 572 |
| Superficie catastale allineata | 568 |
| Superficie catastale discordante | 4 |
| Superficie irrigata allineata | 490 |
| Superficie irrigata discordante | 82 |
| Somma Excel `SUP. IRRIGATA` mq | 1.545.101 |
| Somma DB `sup_irrigabile_mq` mq | 1.789.824 |

Quindi la superficie catastale e sostanzialmente allineata sulle chiavi comuni; la
superficie irrigata richiede una regola di confronto diversa per righe di sola
manutenzione e un controllo puntuale sulle 82 righe irrigue divergenti.

## Ruolo 2025 post-fix vs Capacitas

Confronto ruolo su chiave:

```text
comune normalizzato + foglio + particella + subalterno
```

| Metrica | Valore |
| --- | ---: |
| Righe ruolo 2025 | 99.848 |
| Chiavi catastali ruolo distinte | 85.614 |
| Righe ruolo con chiave presente in Excel | 92.874 |
| Righe ruolo con chiave mancante in Excel | 6.974 |
| Righe ruolo con chiave+CF presente in Excel | 87.977 |
| Righe ruolo con chiave+CF mancante in Excel | 11.871 |
| Righe ruolo con chiave presente in `cat_utenze_irrigue` | 93.916 |
| Righe ruolo con chiave mancante in `cat_utenze_irrigue` | 5.932 |
| Righe ruolo con chiave+CF presente in `cat_utenze_irrigue` | 85.373 |
| Righe ruolo con chiave+CF mancante in `cat_utenze_irrigue` | 14.475 |

Top comuni delle righe ruolo non trovate nell'Excel:

| Comune | Righe ruolo mancanti in Excel |
| --- | ---: |
| ORISTANO | 3.237 |
| SAN VERO MILIS | 1.208 |
| OLLASTRA | 1.166 |
| MARRUBIU | 591 |
| URAS | 112 |

Nota: `OLLASTRA` compare tra le righe ruolo ma non emerge nel perimetro principale
dell'Excel. Questo va trattato come differenza di perimetro territoriale/export.

Tra le righe ruolo mancanti nell'Excel, `6.210/6.974` risultano comunque
`cat_particella_match_status = matched`; quindi non sono particelle spurie prodotte
dal parser, ma particelle presenti/risolte nel catasto GAIA che non compaiono in
questo export Capacitas.

## Validazione fix import ruolo da inCASS

Controlli specifici sul ripopolamento 2025:

| Controllo | Esito |
| --- | ---: |
| Righe ruolo 2025 | 99.848 |
| Match catastale `matched` | 96.926 |
| Righe non matched | 2.922 |
| Fogli fantasma `2024/2025/2026` | 0 |
| Righe con `importo_manut = 1` | 646 |
| Totale manut | 109.696.874 |
| Totale irrig | 51.104.969 |
| Totale ist | 79.251.072 |

Esito: le fix del parser partitario inCASS hanno generato un dataset ruolo coerente
rispetto agli errori noti che si volevano eliminare. In particolare:

- i blocchi consumi non generano piu particelle con foglio anno;
- la colonna `0668` ora confluisce in `importo_irrig`;
- la colonna `0985` confluisce in `importo_ist`;
- il gonfiamento pre-fix della manutenzione e rientrato.

Le righe residue con `importo_manut = 1` sono 646 su 99.848 e non rappresentano piu
l'anomalia massiva pre-fix.

## Conclusione

I dati non sono completamente allineati:

1. L'Excel Capacitas 2026 contiene circa il doppio delle righe della base
   `cat_utenze_irrigue` 2025 oggi presente in GAIA.
2. Il registro `cat_particelle` current non copre 38.655 chiavi catastali distinte
   presenti nell'Excel.
3. Sulle chiavi utenza comuni, CF/nominativi sono quasi sempre coerenti, ma ci sono
   399 CF e 432 nominativi discordanti da ispezionare.
4. La superficie catastale e quasi allineata sulle chiavi comuni; la superficie
   irrigata ha semantiche diverse tra export Excel e DB, e va confrontata solo sulle
   righe con domanda/superficie irrigata positiva.
5. Il ruolo 2025 post-fix e tecnicamente coerente: le anomalie del parser inCASS
   risultano corrette, ma il confronto con l'Excel evidenzia differenze di perimetro
   tra snapshot 2025/2026 e tra fonti Capacitas/catasto/ruolo.

## Prossimi passi consigliati

1. Importare il file Excel in una tabella staging dedicata, senza sovrascrivere
   `cat_utenze_irrigue`, e versionarlo come snapshot Capacitas 2026.
2. Decidere la chiave canonica di confronto per le particelle Capacitas: consigliata
   `CODICE + FOGLIO + PARTIC + SUB`, con mapping comune solo come fallback.
3. Aggiornare o arricchire `cat_particelle` current con le 38.655 chiavi Excel
   mancanti, marcando la fonte come `capacitas_2026`.
4. Analizzare i CSV campione degli scostamenti CF/nominativo/superfici prima di
   promuovere il nuovo snapshot a base di calcolo.
5. Tenere separato il giudizio sul parser inCASS dal giudizio di allineamento
   Capacitas 2026: il parser risulta corretto sui controlli noti, mentre il DB va
   aggiornato per allinearsi al nuovo export.
