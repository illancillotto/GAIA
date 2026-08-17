# GAIA Docs MCP — corpus policy

## Obiettivo

Definire in modo riproducibile quali documenti costituiscono la fonte documentale GAIA nell'esperimento.

## Principio

Non indicizzare automaticamente tutto il repository.

Il corpus deve rappresentare la **conoscenza interna utile a operatori e processi GAIA**, non l'intero patrimonio di sviluppo software.

## Include preferenziale

### Documentazione di piattaforma

Valutare:
- `docs/ARCHITECTURE.md`;
- `docs/PRD.md`;
- documenti di sicurezza e runbook pertinenti;
- documentazione GIS solo se entra nei casi sperimentali.

### Documentazione per dominio

Priorità:
- Catasto;
- Utenze;
- Ruolo;
- Wiki;
- eventuali domini approvati nel ground truth.

Tipologie:
- PRD correnti;
- architecture;
- procedure;
- runbook;
- specifiche funzionali;
- workflow;
- documentazione operativa.

### Operational Wiki

`domain-docs/wiki/operational/` può essere incluso solo se:
- il contenuto viene congelato prima degli esperimenti;
- non contiene risposte create appositamente dopo aver visto il ground truth;
- è versionato nel manifest.

## Esclude di default

- `PROMPT_CODEX*`;
- prompt Claude/Cursor;
- execution prompt puramente di sviluppo;
- `CODE_SIZE_ANALYSIS*`;
- piani di refactoring non operativi;
- coverage plan;
- `progress/*.md` salvo motivazione;
- documenti `archive/`;
- output Graphify;
- codice sorgente `.py`, `.ts`, `.tsx`;
- file generati;
- secret/config reali;
- dump;
- dati personali.

## Freschezza

Per documenti duplicati o storici:
1. individuare la fonte corrente;
2. marcare gli altri come `historical`;
3. escluderli dal corpus principale salvo casi storici espliciti.

## Manifest

Formato suggerito:
```csv
path,sha256,domain,category,status,included,reason
```

Status:
- `current`
- `historical`
- `deprecated`
- `uncertain`

## Freeze sperimentale

Prima del ground truth definitivo produrre:
- `corpus_manifest.csv`;
- `corpus_version.json`;
- hash complessivo.

Qualunque modifica successiva deve produrre una nuova versione.

## Leakage

Non aggiungere documenti costruiti direttamente dalle risposte del ground truth dopo l'inizio della valutazione.
