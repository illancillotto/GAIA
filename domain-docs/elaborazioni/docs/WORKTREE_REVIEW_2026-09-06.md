# Verifica modifiche residue del worktree

Ambito: Portal Health, logging scheduler, editor Festivita. Nessun deploy o
push in questa verifica; il rilascio SISTER precedente resta invariato.

## Correzioni

- Festivita: il riferimento all'elemento `article` usa `HTMLElement`, non
  l'inesistente `HTMLArticleElement`. Conservati editor evidenziato, focus,
  scroll e gestione delle tre categorie; test nuovo incluso nel commit.
- Portal Health: KPI credenziali operative e media delle esecuzioni uniche
  attribuite. Eventi senza credenziale o run ID non partecipano al calcolo.
  Calcolo estratto in `_credential_execution_totals`; presentazione dei due
  KPI separata in `CredentialExecutionKpis`, coerente con `DownloadKpi`.
- Scheduler: inizializzazione del logging in `main`. Non modifica frequenze,
  concorrenza o gestione dei job e non risolve i ritardi del loop condiviso.

## Evidenze

- Sei test backend passati; 100% statement e branch su telemetry_service,
  telemetry_schemas e platform_scheduler_runner.
- Sedici test frontend; coverage esplicita dei due componenti modificati.
- Typecheck globale, Ruff ed ESLint mirato verificati separatamente dai test.
- Metriche Portal Health backend: get_portal_health ciclomatica 15 -> 10,
  cognitiva 14 -> 9, LOC 64 -> 54; helper 6/5/9, sotto soglia. Estrazione
  caratterizzata, non rivendicata come riduzione della complessita aggregata.
- Ratchet contro baseline del merge-base `6d6278cb`: backend KPI e Festivita
  passano. Per il frontend Portal Health serve il corpus completo: la scansione
  ristretta genera un falso matching di spostamenti da file esclusi dal report.
  Il polling useEffect non e stato modificato rispetto al merge-base; il suo
  rilievo LOC 5 -> 6 deriva dalla baseline precedente, non dai nuovi KPI.
  Anche run_scheduler e invariato rispetto al merge-base: non attribuire alla
  singola aggiunta configure_logging i finding legacy della scansione ristretta.
- Baseline e report generati nel repository non modificati da questa verifica.
  Evidenze temporanee: `/tmp/external-fix-{before,after}.json`,
  `/tmp/external-fix-full-corpus-ratchet.json`,
  `/tmp/external-fix-{backend,frontend,typecheck,eslint}.log`.

## Separazione del lavoro

Commit indipendenti per Festivita, logging scheduler e KPI Portal Health.
Documentazione pregressa delle modularizzazioni e report generati restano
fuori dai commit funzionali: il report JSON residuo cambia perimetro e contiene
oltre 244 mila righe di diff, quindi richiede una decisione separata.
Il rimando della skill Graphify ad AGENTS.md e coerente con le regole correnti,
ma non e necessario per le tre correzioni funzionali.
