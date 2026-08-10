# Ruolo/Capacitas live audit - sintesi sanificata

Data audit: `2026-08-06` / `2026-08-07`

## Scopo

Questa nota conserva le conclusioni operative dei report locali generati in `reports/`, senza includere dati personali, codici fiscali, nominativi, path locali o CSV raw.

Audit coperti:

- copertura ruoli salvati per anagrafiche attive;
- controverifica live Capacitas inCASS su anagrafiche verificabili;
- ricostruzione codici ruolo speciali;
- confronto Ruolo 2024 file operativo vs read-model GAIA;
- sync selettiva dei 118 avvisi 2024 mancanti nel read-model.

## Copertura ruoli salvati

Perimetro:

- anagrafiche attive: `37.393`;
- anagrafiche con identificativo fiscale primario: `33.125`;
- annualita ruolo disponibili nel read-model GAIA al momento dell'audit: `2011-2017`, `2019-2025`.

Esito sintetico:

| Indicatore | Conteggio |
|---|---:|
| Con ruolo in tutte le annualita disponibili | 4.229 |
| Con ruoli parziali | 8.419 |
| Senza ruoli in nessuna annualita | 20.477 |
| Senza identificativo fiscale | 4.268 |

Interpretazione:

- L'audit misura copertura DB, non morosita o errore operativo.
- Un soggetto senza ruolo in un anno puo semplicemente non essere contribuente in quell'annualita.
- La copertura e utile per priorizzare controlli di materializzazione e link `subject_id`.

## Controverifica live Capacitas

La verifica live e stata eseguita in sola lettura su Capacitas inCASS, senza sincronizzazioni e senza modifiche DB.

| Indicatore | Conteggio |
|---|---:|
| Anagrafiche attive input | 37.393 |
| Verificabili live con identificativo | 33.125 |
| Processate live | 33.125 |
| Presenti live in Capacitas | 19.583 |
| Non trovate live in Capacitas | 13.542 |
| Errori | 0 |

Codici rilevati live:

- annualita ordinarie `2011-2025`, inclusa `2018` non presente nel read-model locale coperto dall'audit;
- codici speciali `2525`, `2626`, `7700`, `7890`;
- anticipi tributi `99xx`.

## Diff annualita ordinarie

La ricostruzione ha individuato:

| Indicatore | Conteggio |
|---|---:|
| Soggetti con anni ordinari live mancanti in GAIA | 16.672 |
| Righe soggetto-anno candidate | 53.096 |
| Soggetti con mancanti su anni gia coperti localmente | 9.073 |
| Righe candidate su anni gia coperti localmente | 40.997 |
| Soggetti con anni live non coperti dal dataset locale | 12.099 |

Nota operativa:

- `2018` emerge come annualita live non coperta dal dataset locale in quel momento.
- Le righe candidate richiedono verifica prima di qualunque backfill: non tutti i gap sono automaticamente errori.

## Codici speciali Capacitas

Classificazione operativa confermata:

| Codice | Gestione |
|---|---|
| `2525` | Avviso accorpato emesso nel 2025, fuori dal calcolo ordinario |
| `2626` | Avviso accorpato emesso nel 2026, fuori dal calcolo ordinario |
| `7700` | Violazione di regolamento, avviso speciale |
| `7890` | Agenzia delle Entrate, avviso speciale |
| `99xx` | Anticipo tributi conduttore/affittuario, da gestire come movimento speciale |

La policy applicativa conseguente e documentata in `RUOLO_TRIBUTI_RUOLI_SPECIALI_CAPACITAS_2026-08-10.md` e implementa i codici speciali come `audit_only`, quindi non impattano saldo, morosita e annualita ordinaria.

## Partitario codici speciali

Campione live read-only su codici `2525`, `2626` e `99xx`:

| Controllo | Esito |
|---|---:|
| Avvisi campione | 12 |
| Modali con partite parsate | 0 |
| Modali vuote | 12 |
| Excel scaricati correttamente | 12 |
| Excel con righe dati effettive | 0 |

Conclusione:

- Per il campione verificato, gli endpoint di dettaglio/Excel partitario esposti da inCASS non forniscono righe utili per ricostruire particelle/proprietari dei codici speciali.
- La ricostruzione richiede una fonte alternativa Capacitas o un export back-office diverso.

## Ruolo 2024 e sync 118 avvisi

Confronto file operativo Ruolo 2024 vs read-model GAIA:

| Indicatore | Conteggio |
|---|---:|
| Righe file operativo | 2.681 |
| Avvisi GAIA 2024 totali prima del controllo selettivo | 11.678 |
| Righe file con CF + numero ruolo trovati | 2.681 |
| CF mancanti nel ruolo GAIA 2024 | 0 |
| CF presenti con numero ruolo non corrispondente | 0 |

Una controverifica live su `118` record mancanti dal read-model ha confermato che tutti risultavano presenti in Capacitas inCASS.

Sync selettiva successiva:

| Controllo | Esito |
|---|---:|
| Job manuali eseguiti | 12 |
| Job riusciti | 12 |
| Job falliti | 0 |
| Avvisi materializzati | 118 |
| Partite create | 161 |
| Particelle create | 1.147 |
| Errori materializzazione | 0 |

## Decisioni e follow-up

- Non versionare i CSV/JSON raw dell'audit: contengono dati personali e output live.
- Conservare in repository solo sintesi sanificate come questa nota.
- Per ulteriori backfill ordinari, produrre sempre prima una lista candidate sanificata e una verifica read-only.
- Per codici speciali, continuare a trattare `2525`, `2626`, `7700`, `7890` e `99xx` come superfici audit-only finche non esiste una fonte affidabile per partite/particelle.
