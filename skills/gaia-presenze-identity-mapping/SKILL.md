---
name: gaia-presenze-identity-mapping
description: Verifica e riconcilia il mapping canonico tra utenti GAIA e collaboratori INAZ/Presenze, inclusi audit degli unmapped, manifest, backfill e controlli GATE fail-closed.
metadata:
  short-description: Gestisce identita GAIA-INAZ canoniche
---

# GAIA Presenze Identity Mapping

Usa questa skill per audit, incidenti e riconciliazioni che coinvolgono
`application_users`, collaboratori INAZ/Presenze o snapshot GATE.

## Prima di agire

1. Lavora dalla root del checkout GAIA e leggi `AGENTS.md`.
2. Leggi integralmente
   `domain-docs/presenze/docs/INAZ_GAIA_IDENTITY_MAPPING_RUNBOOK.md`.
3. Verifica branch, SHA e working tree; non alterare modifiche non correlate.
4. Distingui l'audit read-only dall'applicazione. Backup, `--apply`, sync e
   verifiche su produzione richiedono autorizzazione esplicita nel task
   corrente.

## Invarianti

- GAIA e l'anagrafica autorevole. L'identita canonica e
  `gaia_user_id = application_users.id`.
- La relazione Presenze e
  `presenze_collaborators.application_user_id -> application_users.id`.
- `presenze_collaborators.id`, `employee_code`, ID INAZ e ID GATE appartengono
  a namespace distinti.
- Non applicare mapping ottenuti direttamente da nome, username, email,
  matricola, codice fiscale o uguaglianza numerica tra namespace. Nome e
  cognome possono generare soltanto un artefatto separato `REVIEW_REQUIRED`,
  mai un manifest canonico o un fallback autorizzativo.
- Usa soltanto una coppia `gaia_user_id -> presenze_collaborator_id` attestata
  esplicitamente da una fonte o da un responsabile autorizzato. Se manca,
  chiedi l'attestazione e fermati sulla persona interessata.
- Identita assenti, duplicate, conflittuali o incoerenti restano fail-closed.
- Ogni collaboratore INAZ, attivo o storico, deve avere `application_user_id`;
  i conteggi totale e attivo degli unmapped sono gate e devono terminare a
  zero. Un account GAIA inattivo resta un'identita valida senza acquisire login.

## Workflow

1. Esegui le query del runbook e registra almeno: attivi totali, attivi non
   mappati, duplicati, riferimenti orfani e divergenze su giornaliere/riepiloghi.
2. Per un bootstrap una tantum puoi generare candidati da nome/cognome seguendo
   il runbook: separa match esatti, varianti di token, omonimi e assenti; marca
   sempre `auto_apply=false` e non modificare il database.
3. Acquisisci una decisione esplicita `APPROVE` o `REJECT` per ogni candidato.
   Gli omonimi e i casi senza candidato si risolvono singolarmente in GAIA.
4. Solo le coppie approvate costituiscono l'attestazione. Crea da queste un
   manifest `version=1` contenente esclusivamente `gaia_user_id`,
   `personnel_area` e `presenze_collaborator_id`.
5. Esegui sempre il dry-run con
   `backend/scripts/backfill_presenze_canonical_identities.py`; non proseguire
   se una riga fallisce o il report non coincide con il perimetro attestato.
6. Prima dell'applicazione in produzione crea e verifica il backup previsto
   dal runbook. Applica lo stesso manifest con autore e motivo audit espliciti.
7. Riesegui il manifest in dry-run per verificare l'idempotenza: tutte le righe
   devono risultare `unchanged`.
8. Riesegui l'audit completo. Non dichiarare risolto il problema finche tutti
   gli unmapped e tutte le incoerenze non sono zero.
9. Quando richiesto, esegui la sync GAIA -> GATE e verifica che membership e
   snapshot Presenze espongano lo stesso `gaia_user_id`; verifica anche un caso
   negativo fail-closed.

## Stop condition

Fermati senza scritture se un candidato non e stato approvato esplicitamente,
se una persona ha piu candidati, se un ID e gia assegnato altrove, se manca il
`WCOperator` canonico, se il dry-run non e spiegabile o se il backup non e
verificato.

## Output minimo

Riporta ambiente e timestamp, origine dell'attestazione, manifest usato senza
dati anagrafici superflui, report dry-run/apply, conteggi di integrita prima e
dopo, audit generato, esito sync GATE e ogni identita rimasta fail-closed.
