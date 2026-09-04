# Registro locale identita Presenze

`canonical-identities.json` e il registro privato locale delle coppie canoniche
gia attestate. Il file e ignorato da Git e contiene soltanto `gaia_user_id`,
`personnel_area` e `presenze_collaborator_id`: nome e matricola non sono chiavi
di mapping.

Le due attestazioni SPANU del 3 settembre 2026 sono distinte:

- `gaia_user_id=254` -> `presenze_collaborator_id=1bf41d92-e6ed-4503-9e42-93f5cf43edf2`;
- `gaia_user_id=255` -> `presenze_collaborator_id=33e64c8a-59b3-47b0-a186-cdec316246de`.

Entrambe hanno `personnel_area=AGRARIO` e risultano dall'audit locale con
`source=canonical_manifest`, motivo
`Attestazione esplicita residui GAIA-INAZ 2026-09-03`.

Eseguire dopo ogni restore e prima di riattivare i writer Presenze:

```bash
make audit-presenze-identities
```

Il comando e read-only e fallisce con `IDENTITY_MANIFEST_DRIFT` se il database
non coincide con il registro. Il fallimento non autorizza l'applicazione: prima
servono backup, dry-run e verifica delle attestazioni secondo il runbook.
