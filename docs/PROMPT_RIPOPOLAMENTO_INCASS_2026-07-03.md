# Prompt — Commit fix parser incass + ripopolamento ruolo_particelle da inCASS

> Prompt operativo autosufficiente. Obiettivo: mettere in salvo (commit) il fix del
> parser partitario inCASS già completato e verificato, poi rieseguire la
> materializzazione dei dati ruolo 2025 dal raw salvato a DB e verificare il risultato.
> Data: 2026-07-03. Repo: GAIA, branch: `main`. Contesto completo in
> `docs/INCASS_PARTITARIO_PARSER_FIX_2026-07-03.md` (leggilo prima di iniziare).

## Contesto in 5 righe

Il parser della modale partitario inCASS è stato riscritto (parse posizionale a
colonne fisse + fallback a token). I dati oggi in `ruolo_particelle` per l'anno 2025
sono stati materializzati con il parser vecchio e sono corrotti: importi 0668
assegnati alla colonna sbagliata, `importo_manut=1` spurio, particelle fantasma,
manut gonfiato (~1,92 M€ su un campione di 400 avvisi). Il raw della modale è salvato
in `ana_payment_notices.raw_detail_json.partitario.raw_html` per tutti i 12.348
avvisi incass 2025: si ripopola da lì.

## Vincoli sul working tree (IMPORTANTE)

Nel working tree ci sono modifiche di più flussi di lavoro. Devi committare SOLO i
file del fix parser (elenco esatto in STEP 1). NON toccare e NON committare:
`backend/app/modules/presenze/*`, `frontend/*`, `backend/gaia_compute.py`,
`backend/gen_export.py`, `backend/instrument.py`, `tsconfig.tsbuildinfo`, i file
`docs/INCASS_TOP20_*` e `docs/INCASS_PARTITARIO_*VERIFICA*.md` (audit di un flusso
parallelo: lasciali untracked). Non fare `git add -A` per nessun motivo.

## STEP 0 — Pre-flight

1. Verifica i test del parser (devono essere tutti verdi, 26 locali):
   ```bash
   cd backend && python3 -m pytest tests/test_incass_parsers.py tests/elaborazioni/ -q
   docker compose exec -T backend python -m pytest tests/test_incass_parsers.py tests/elaborazioni/ tests/ruolo/ -q
   ```
   Se qualcosa è rosso FERMATI e riporta l'errore: non procedere al ripopolamento.
2. Verifica che il backend docker sia healthy (`docker compose ps`).

## STEP 1 — Commit del fix (mettere in salvo prima di toccare il DB)

Commit singolo con ESATTAMENTE questi path:

```
backend/app/modules/elaborazioni/capacitas/apps/incass/parsers.py
backend/tests/test_incass_parsers.py
backend/tests/elaborazioni/
backend/tests/fixtures/
backend/scripts/materialize_ruolo_from_incass.py
domain-docs/elaborazioni/capacitas/docs/CAPACITAS_integration.md
docs/INCASS_PARTITARIO_PARSER_FIX_2026-07-03.md
```

Messaggio suggerito (stile dello storico, inglese, imperativo):
`Fix incass partitario parser with fixed-width column parsing`
con body che cita: colonna Irrig./0668 corretta, particelle fantasma eliminate,
filtro consumi indipendente dall'anno, flag `--reparse-partitario`.
NON pushare senza conferma dell'utente.

## STEP 2 — Backup DB

Prima del ripopolamento (usa `--replace-year`, che svuota l'anno):

```bash
make backup-db-to-nas
```

Se il target fallisce (NAS non raggiungibile), fai un dump locale mirato e
riportalo nel resoconto:

```bash
docker compose exec -T backend sh -c 'pg_dump "$DATABASE_URL" -t ruolo_avvisi -t ruolo_partite -t ruolo_particelle -t ruolo_import_jobs' > /tmp/ruolo_backup_2026-07-03.sql
```

(adatta il nome della variabile d'ambiente del DB se diverso: verificalo con
`docker compose exec backend env | grep -i database`).

## STEP 3 — Fotografia PRIMA (baseline)

Salva questi numeri per il confronto (esegui via `docker compose exec -T backend python`
con SQLAlchemy, oppure psql):

```sql
SELECT count(*) AS particelle,
       count(*) FILTER (WHERE importo_manut = 1) AS manut_uguale_1,
       round(sum(importo_manut)::numeric, 2) AS tot_manut,
       round(sum(importo_irrig)::numeric, 2) AS tot_irrig,
       round(sum(importo_ist)::numeric, 2)  AS tot_ist
FROM ruolo_particelle WHERE anno_tributario = 2025;

SELECT count(*) AS avvisi FROM ruolo_avvisi WHERE anno_tributario = 2025;
SELECT count(*) AS partite FROM ruolo_partite rp
  JOIN ruolo_avvisi ra ON rp.avviso_id = ra.id WHERE ra.anno_tributario = 2025;
```

## STEP 4 — Dry-run

```bash
docker compose exec -T backend python scripts/materialize_ruolo_from_incass.py \
  --from-year 2025 --to-year 2025 --replace-year --reparse-partitario
```

Controlla le statistiche stampate: `notices_total` atteso 12348,
`notices_without_partite` deve essere basso (poche decine al massimo — se è alto
il re-parse sta fallendo: FERMATI e indaga). Nessuna scrittura avviene senza `--apply`.

## STEP 5 — Esecuzione reale

```bash
docker compose exec -T backend python scripts/materialize_ruolo_from_incass.py \
  --from-year 2025 --to-year 2025 --replace-year --reparse-partitario --apply
```

Nota: il linking catastale per ~50k+ particelle può richiedere parecchi minuti;
non interrompere. Se serve rilanciare dopo un'interruzione: prima
`--purge-only --replace-year --apply`, poi `--rebuild-only --reparse-partitario --apply`.

## STEP 6 — Verifiche DOPO

1. Riesegui le query dello STEP 3 e confronta. Attese rispetto alla baseline:
   - `manut_uguale_1` ≈ 0 (prima erano migliaia);
   - `tot_manut` in FORTE calo (nel campione da 400 avvisi il calo era ~1,92 M€;
     proiettato sull'intero anno sarà molto di più);
   - `tot_irrig` passa da ~0 a un valore significativo (0668 ora valorizzato);
   - `tot_ist` in aumento moderato;
   - conteggio particelle in calo (le righe riepilogo+domanda ora sono fuse e
     le particelle fantasma sparite): un calo del 10-15% è coerente col campione.
2. Nessuna particella fantasma da blocchi consumi:
   ```sql
   SELECT count(*) FROM ruolo_particelle
   WHERE anno_tributario = 2025 AND foglio IN ('2024','2025','2026');
   ```
   Atteso: 0.
3. Riconciliazione per avviso (campione): per 10 avvisi con 0648 valorizzato,
   somma `importo_manut` delle particelle ≈ `importo_totale_0648` dell'avviso
   (tolleranza 0,50 €; scarta gli avvisi da contributo minimo forfettario, dove la
   somma sarà inferiore al totale).
4. Totali per comune: genera la tabella per comune 2025
   (`SELECT rp2.comune_nome, sum(p.importo_manut), sum(p.importo_irrig), sum(p.importo_ist) ...`
   via join `ruolo_particelle -> ruolo_partite -> ruolo_avvisi`) e confrontala con
   `docs/INCASS_TOP20_TOTALI_PER_COMUNE_2026-07-01.csv`: gli scostamenti devono
   essere coerenti col fix (manut in calo, irrig da zero a valorizzato). Scostamenti
   in AUMENTO su manut sono un red flag: FERMATI e riporta.
5. Smoke test API: `GET /ruolo` stats 2025 risponde e i totali non sono nulli
   (usa le route del modulo ruolo, vedi `backend/app/modules/ruolo/routes/query_routes.py`).

## STEP 7 — Resoconto

Scrivi `docs/INCASS_RIPOPOLAMENTO_2025_ESITO_2026-07-03.md` con: numeri prima/dopo
(tabella), esito delle 5 verifiche, durata dell'esecuzione, eventuali anomalie
residue con esempi concreti (avviso + particella). Aggiorna la nota di stato in
`docs/PROMPT_REFACTOR_RUOLO_2026-07-03.md` (FASE 0 → ripopolamento ESEGUITO).
Committa resoconto + aggiornamento prompt in un secondo commit.

## Criteri di accettazione

1. Commit del fix creato con SOLO i file elencati (verifica con `git show --stat`).
2. Backup disponibile prima dell'apply.
3. Materializzazione completata senza errori; `notices_without_partite` trascurabile.
4. `manut_uguale_1` = 0 (o giustificato caso per caso), foglio-anno = 0,
   riconciliazione campione ok, confronto per comune coerente.
5. Resoconto scritto e committato. Nessun file estraneo toccato o committato.
