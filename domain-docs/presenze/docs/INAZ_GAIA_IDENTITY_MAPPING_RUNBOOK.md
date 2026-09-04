# Runbook mapping identita INAZ - GAIA

## Scopo

Questo runbook governa la relazione fra i collaboratori acquisiti da INAZ e
gli utenti canonici GAIA. Si applica dopo ogni prima acquisizione di un
collaboratore, durante gli audit periodici e negli incidenti in cui GATE non
mostra Giornaliere attese.

Obiettivo operativo: ogni riga di `presenze_collaborators`, attiva o storica,
deve avere un `application_user_id` valido e univoco. Un utente GAIA inattivo
resta utilizzabile come identita senza acquisire login. Un collaboratore non
mappato non deve ottenere visibilita per fallback: resta escluso dagli snapshot
autorizzati finche il mapping non viene attestato e applicato.

## Contratto identita

```text
gaia_user_id (contratti esterni)
  = application_users.id (identita canonica GAIA)
  = presenze_collaborators.application_user_id (foreign key interna)
  = presenze_daily_records.application_user_id
  = presenze_event_summaries.application_user_id
```

Gli identificativi seguenti sono descrittivi o appartengono ad altri
namespace e non provano il mapping:

- `presenze_collaborators.id`: UUID tecnico del collaboratore Presenze;
- `employee_code`: matricola INAZ;
- nome, username, email e codice fiscale;
- ID locali GATE o vecchi ID `wc_operator`.

Non usare mai questi valori per matching automatico, fallback autorizzativo o
uguaglianze numeriche con `application_users.id`. In caso di assenza,
duplicazione o conflitto, il comportamento corretto e fail-closed.

## Responsabilita e attestazione

Il mapping puo essere applicato solo quando una fonte aziendale autorevole o
un responsabile HR/amministratore autorizzato attesta esplicitamente la coppia:

```text
gaia_user_id -> presenze_collaborator_id
```

La revisione puo usare nome, cognome, matricola e altri dati anagrafici per
proporre o valutare una coppia, ma tali dati non diventano chiavi di
correlazione. L'attestazione finale deve indicare direttamente entrambi gli ID
ed essere conservata insieme al motivo dell'intervento. Se la fonte non espone
entrambi gli ID, non esiste un mapping automatico conforme: si puo produrre una
lista di candidati, ma una decisione umana esplicita deve precedere il manifest.

## Bootstrap una tantum da nome e cognome

Quando il backlog manuale e elevato, e ammessa un'analisi read-only per ridurre
il numero di righe da esaminare. Questa analisi non e un fallback runtime e non
modifica visibilita, snapshot o database.

Ordine dei criteri:

1. `EXACT_NORMALIZED`: nome INAZ uguale a `application_users.full_name` oppure
   a nome e cognome del `WCOperator` canonico, accettando l'ordine inverso;
2. `TOKEN_REORDER`: stessi token anagrafici in ordine diverso;
3. `TOKEN_SUBSET`: nome e cognome coincidono e una fonte contiene secondi nomi
   aggiuntivi;
4. `AMBIGUOUS_NAME`: piu `gaia_user_id` distinti corrispondono alla stessa
   persona nominale;
5. `NO_CANDIDATE`: nessuna corrispondenza strutturata.

Un candidato e revisionabile soltanto se il `gaia_user_id` non e gia associato
ad altro collaboratore, esiste un solo `WCOperator` canonico e
`personnel_area` vale `AGRARIO` o `IMPIANTI`. Il file di lavoro deve contenere
almeno:

- `presenze_collaborator_id` e `candidate_gaia_user_id`;
- `match_basis` e stato `REVIEW_REQUIRED`;
- nomi delle due fonti per la revisione;
- `personnel_area`;
- campi vuoti `decision` e `review_note`;
- metadato `auto_apply=false`.

Il file candidati non deve avere lo schema del manifest `version=1`, in modo da
non poter essere passato accidentalmente al backfill. Il revisore autorizzato
marca ogni riga `APPROVE` o `REJECT`. Solo le righe approvate vengono convertite
nel manifest canonico; gli omonimi, i casi non idonei e quelli senza candidato
si risolvono singolarmente nella UI GAIA e restano fail-closed nel frattempo.

## Audit read-only

Eseguire il controllo dopo ogni sync che introduce nuovi collaboratori e, come
rete di sicurezza, almeno una volta al giorno. Nel primo risultato
`unmapped_total` e `active_unmapped` devono essere entrambi `0`.

```bash
docker compose exec -T postgres sh -lc \
  'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT
  count(*) AS collaborators_total,
  count(*) FILTER (WHERE application_user_id IS NULL) AS unmapped_total,
  count(*) FILTER (
    WHERE is_active AND application_user_id IS NULL
  ) AS active_unmapped
FROM presenze_collaborators;

SELECT
  id AS presenze_collaborator_id,
  company_code,
  employee_code,
  is_active,
  last_seen_at
FROM presenze_collaborators
WHERE application_user_id IS NULL
ORDER BY is_active DESC, company_code NULLS FIRST, employee_code, id;

SELECT application_user_id, count(*) AS mappings
FROM presenze_collaborators
WHERE application_user_id IS NOT NULL
GROUP BY application_user_id
HAVING count(*) > 1;

SELECT count(*) AS orphan_application_users
FROM presenze_collaborators AS c
LEFT JOIN application_users AS u ON u.id = c.application_user_id
WHERE c.application_user_id IS NOT NULL AND u.id IS NULL;

SELECT count(*) AS daily_mapping_mismatches
FROM presenze_daily_records AS d
JOIN presenze_collaborators AS c ON c.id = d.collaborator_id
WHERE d.application_user_id IS DISTINCT FROM c.application_user_id;

SELECT count(*) AS event_summary_mapping_mismatches
FROM presenze_event_summaries AS e
JOIN presenze_collaborators AS c ON c.id = e.collaborator_id
WHERE e.application_user_id IS DISTINCT FROM c.application_user_id;

SELECT count(*) AS active_mapped_without_one_operator
FROM (
  SELECT c.id
  FROM presenze_collaborators AS c
  LEFT JOIN wc_operator AS o ON o.gaia_user_id = c.application_user_id
  WHERE c.application_user_id IS NOT NULL
  GROUP BY c.id
  HAVING count(o.id) <> 1
) AS inconsistent_operators;

SELECT (
  NOT EXISTS (
    SELECT 1 FROM presenze_collaborators
    WHERE application_user_id IS NULL
  )
  AND NOT EXISTS (
    SELECT 1
    FROM presenze_collaborators
    WHERE application_user_id IS NOT NULL
    GROUP BY application_user_id
    HAVING count(*) > 1
  )
  AND NOT EXISTS (
    SELECT 1
    FROM presenze_collaborators AS c
    LEFT JOIN application_users AS u ON u.id = c.application_user_id
    WHERE c.application_user_id IS NOT NULL AND u.id IS NULL
  )
  AND NOT EXISTS (
    SELECT c.id
    FROM presenze_collaborators AS c
    LEFT JOIN wc_operator AS o ON o.gaia_user_id = c.application_user_id
    WHERE c.application_user_id IS NOT NULL
    GROUP BY c.id
    HAVING count(o.id) <> 1
  )
  AND NOT EXISTS (
    SELECT 1
    FROM presenze_daily_records AS d
    JOIN presenze_collaborators AS c ON c.id = d.collaborator_id
    WHERE d.application_user_id IS DISTINCT FROM c.application_user_id
  )
  AND NOT EXISTS (
    SELECT 1
    FROM presenze_event_summaries AS e
    JOIN presenze_collaborators AS c ON c.id = e.collaborator_id
    WHERE e.application_user_id IS DISTINCT FROM c.application_user_id
  )
) AS identity_mapping_ok \gset
\if :identity_mapping_ok
  \echo 'IDENTITY_MAPPING_OK'
\else
  \echo 'IDENTITY_MAPPING_FAILED'
  DO $gate$ BEGIN RAISE EXCEPTION 'IDENTITY_MAPPING_FAILED'; END $gate$;
\endif
SQL
```

`company_code` ed `employee_code` nell'elenco sono etichette operative per la
revisione; non devono essere confrontati con ID GAIA. Conservare nei report
condivisi solo gli identificativi necessari ed evitare dati anagrafici.

## Manifest canonico

Preparare un file fuori dal repository, con permessi restrittivi. Ogni riga
deve provenire dall'attestazione esplicita e contiene soltanto i campi ammessi:

```json
{
  "version": 1,
  "people": [
    {
      "gaia_user_id": 238,
      "personnel_area": "IMPIANTI",
      "presenze_collaborator_id": "13126cf8-32b6-4206-9910-58374f125681"
    }
  ]
}
```

`personnel_area` ammette solo `AGRARIO` o `IMPIANTI`. Non aggiungere nome,
username, email, matricola o altri campi: il parser li rifiuta. Un manifest non
deve contenere duplicati di `gaia_user_id` o `presenze_collaborator_id`.

## Dry-run obbligatorio

In un ambiente Python GAIA configurato:

```bash
python backend/scripts/backfill_presenze_canonical_identities.py \
  /tmp/gaia-inaz-identities.json \
  --changed-by-gaia-user-id 1 \
  --reason "Attestazione mapping INAZ-GAIA YYYY-MM-DD"
```

Nel deployment Compose copiare temporaneamente il manifest nel container:

```bash
docker compose cp /tmp/gaia-inaz-identities.json \
  backend:/tmp/gaia-inaz-identities.json

docker compose exec -T backend \
  python scripts/backfill_presenze_canonical_identities.py \
  /tmp/gaia-inaz-identities.json \
  --changed-by-gaia-user-id 1 \
  --reason "Attestazione mapping INAZ-GAIA YYYY-MM-DD"
```

Sostituire `1` con l'ID reale dell'amministratore autore. Il default e sempre
dry-run. Il report deve essere coerente con il manifest e non deve presentare
errori. Qualunque identita inesistente, relazione `WCOperator` non univoca o
mapping gia occupato interrompe l'intero batch prima delle scritture.

## Registro locale e controllo post-restore

Le coppie gia attestate devono restare disponibili in un registro locale
privato anche quando un restore sostituisce database e tabella audit. Nel
checkout operativo il percorso predefinito e
`secrets/presenze/canonical-identities.json`, ignorato da Git. Il registro usa
lo stesso schema `version=1` del manifest e non deve contenere nomi, username,
email o matricole.

Dopo ogni restore, prima di riattivare worker o sync Presenze, eseguire:

```bash
make audit-presenze-identities
```

Il target esegue un dry-run con `--require-unchanged`: exit code `0` significa
che tutte le coppie registrate e le aree canoniche coincidono; exit code `1` e
il marker `IDENTITY_MANIFEST_DRIFT` indicano che il restore ha perso o alterato
almeno un'attestazione. Il controllo non scrive il database e un suo fallimento
non autorizza il backfill automatico. Conservare il registro separatamente dai
dump e includere questo gate nella checklist di restore CED/NAS.

Caso omonimia noto: i due collaboratori SPANU SALVATORE sono persone distinte.
Il registro conserva esclusivamente le coppie attestate
`254 -> 1bf41d92-e6ed-4503-9e42-93f5cf43edf2` e
`255 -> 33e64c8a-59b3-47b0-a186-cdec316246de`; il nome non deve mai essere
usato per ricostruirle o invertirle.

## Backup e applicazione

Prima di modificare produzione creare un backup verificabile:

```bash
make backup-db-to-nas
```

Registrare percorso locale, manifest NAS e timestamp. Solo dopo il dry-run e
l'autorizzazione all'intervento applicare esattamente lo stesso file:

```bash
docker compose exec -T backend \
  python scripts/backfill_presenze_canonical_identities.py \
  /tmp/gaia-inaz-identities.json \
  --changed-by-gaia-user-id 1 \
  --reason "Attestazione mapping INAZ-GAIA YYYY-MM-DD" \
  --apply
```

L'applicazione e transazionale e aggiorna il collaboratore, le Giornaliere e i
riepiloghi eventi; scrive inoltre
`presenze_collaborator_mapping_audit` con `source=canonical_manifest`. In caso
di errore non correggere tabelle a mano e non applicare porzioni del manifest.

Rieseguire subito lo stesso comando senza `--apply`: il dry-run deve indicare
tutte le righe come `unchanged`. Verificare inoltre che il numero di record di
audit non sia aumentato oltre le variazioni effettivamente applicate.

## Verifica e sincronizzazione GATE

1. Rieseguire tutte le query di audit. `unmapped_total`, `active_unmapped`,
   duplicati, orfani, mapping privi di un solo `WCOperator` canonico e mismatch
   devono essere `0`; il comando deve terminare con `IDENTITY_MAPPING_OK` ed
   exit code `0`.
2. Verificare che le righe audit abbiano autore, motivo, `source` e timestamp
   corretti.
3. Attendere il ciclo automatico `gate-mobile-sync` (intervallo standard 300
   secondi) oppure, se autorizzati, avviare il run amministrativo
   `POST /operazioni/mobile-gateway-sync/run`.
4. Verificare `GET /operazioni/mobile-gateway-sync/status`: l'ultimo run deve
   essere concluso senza errore e deve includere gli snapshot richiesti.
5. Sugli endpoint effettivi GATE verificare che membership, Giornaliere e
   anomalie espongano lo stesso `gaia_user_id` per la persona attestata.
6. Verificare un caso negativo: un collaboratore senza mapping o con identita
   incoerente non deve comparire nelle righe autorizzate.

Il sync non crea il mapping e non risolve autonomamente gli unmapped: pubblica
solo lo stato canonico gia persistito in GAIA. Attendere un nuovo ciclo serve
soltanto dopo che il backfill e stato applicato e verificato.

## Prevenzione

- Eseguire l'audit immediatamente dopo ogni prima acquisizione INAZ e bloccare
  la chiusura operativa del job se `unmapped_total > 0`.
- Eseguire lo stesso audit giornalmente e generare un allarme sul primo valore
  diverso da zero; non aspettare una segnalazione GATE.
- Richiedere il mapping canonico come parte dell'onboarding: creazione utente
  GAIA, assegnazione `personnel_area`, attestazione del collaborator UUID,
  dry-run, applicazione e verifica.
- Non rendere `application_user_id` obbligatorio nel DB finche l'acquisizione
  INAZ non dispone della coppia canonica: bloccherebbe l'import senza poter
  risolvere correttamente l'identita. Il controllo resta fail-closed e
  operativo.
- Non considerare risolto un incidente con un manifest parziale se esistono
  ancora collaboratori INAZ, attivi o storici, non mappati.

## Recovery

Per una coppia attestata in modo errato non eseguire `UPDATE` manuali e non
usare il manifest di backfill per forzare un remap: il servizio lo rifiuta. Usare
il flusso amministrativo auditato di mapping singolo solo dopo una nuova
attestazione; se coinvolge uno scambio o piu identita, fermarsi e pianificare
una procedura atomica dedicata con test. Il restore completo del backup e una
misura di emergenza e segue `make restore-db-from-nas`, dopo avere fermato i
writer e verificato il manifest del dump.
