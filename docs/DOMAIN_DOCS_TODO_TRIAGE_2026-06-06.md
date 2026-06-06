# Domain Docs TODO Triage — 2026-06-06

## Scopo

Separare i TODO documentali che rappresentano lavoro operativo reale da:

- note storiche
- checklist di prompt/accettazione
- TODO locali a snippet o prove tecniche

Questo file non modifica il runtime. Serve solo come inventario di triage.

## TODO Operativi Reali

Questi TODO descrivono lavoro ancora aperto e dovrebbero vivere come backlog esplicito.

### CED

Fonte: `domain-docs/ced/docs/PROGRESS.md`

Motivo:
- è un vero piano di modulo ancora non implementato
- contiene task concreti su route, sidebar, home, permessi, redirect

Azioni consigliate:
- aprire un epic `CED module bootstrap`
- spezzare in ticket frontend shell, routing, permessi, alias legacy

### Wiki

Fonte: `domain-docs/wiki/docs/IMPLEMENTATION_PLAN_wiki.md`

TODO reali:
- pagina admin `/wiki/requests`
- streaming SSE `/wiki/chat/stream`

Motivo:
- sono feature di prodotto non ancora chiuse
- impattano superfici utente reali

### Operazioni

Fonte: `domain-docs/operazioni/docs/GAIA_OPERAZIONI_PROGRESS.md`

TODO reali:
- milestone hardening
- GPS residuali
- test workflow non completati

Motivo:
- sono blocchi di delivery e qualità ancora vivi

Nota:
- il documento mescola anche note di stato e storico; va tenuto come progress tracker, non come sorgente unica del backlog.

### Capacitas / Elaborazioni

Fonte: `domain-docs/elaborazioni/capacitas/docs/CAPACITAS_integration.md`

TODO reali:
- acquisizione massiva Terreni
- sezione frontend credenziali Capacitas
- endpoint/search residue
- refactor client per macro-moduli

Motivo:
- backlog funzionale/infrastrutturale ancora aperto

### Utenze / ANPR decessi

Fonte: `domain-docs/utenze/docs/ARCH_PDND_ANPR_DECESSI.md:332`

TODO reale:
- validazione pre go-live con chiamate note su ambiente test ANPR

Motivo:
- non è lavoro di codice generico, ma un gate di integrazione reale prima della produzione

### Ruolo

Fonte: `domain-docs/ruolo/docs/PROGRESS_ruolo.md`

TODO reale:
- import completo file Ruolo 2024 su dati reali

Motivo:
- attività operativa ancora da eseguire su dataset reale

## TODO Storici / Non Operativi

Questi TODO non vanno trattati come debito runtime immediato.

### Inline note di snippet o prototipi

Fonte: `domain-docs/catasto/docs/GAIA_CATASTO_GIS_FRONTEND_CODEX_v1.md:486`

Esempio:
- fetch eventuale geometrie selezionate per highlight

Classificazione:
- nota tecnica locale
- non backlog prioritario se il comportamento attuale è intenzionale

### Checklist di prompt / acceptance checklist

Fonti tipiche:
- `domain-docs/catasto/docs/GAIA_CATASTO_BACKEND_CODEX_v1.md`
- `domain-docs/catasto/docs/GAIA_CATASTO_CURSOR_PROMPT_v1.md`
- `domain-docs/utenze/docs/CURSOR_PROMPT_PDND_ANPR.md`
- `domain-docs/wiki/docs/PROMPT_CODEX_wiki.md`
- `domain-docs/operazioni/docs/PROMPT_SEGNALAZIONI_VIEWER.md`
- `domain-docs/riordino/docs/PROMPT_CODEX_riordino_fullstack_v2.md`

Classificazione:
- non backlog di prodotto
- sono checklist di esecuzione o criteri di accettazione contenuti in prompt storici

Azioni consigliate:
- non aprire ticket automaticamente
- archiviarli o marcarli come `prompt checklist` quando si fa pulizia documentale

### Stato generico “TODO” in documenti progressivi

Fonte: `domain-docs/operazioni/docs/GAIA_OPERAZIONI_PROGRESS.md:272`

Classificazione:
- metadato di milestone
- utile al lettore, ma non sufficiente da solo per creare ticket

## Regola di triage proposta

Quando compare un TODO in `domain-docs`, classificarlo così:

1. `operational_backlog`
   Usa questa classe se descrive una feature, migrazione, test, rollout o integrazione ancora da fare.

2. `integration_gate`
   Usa questa classe se è un controllo obbligatorio prima del go-live, come ANPR/PDND o verifiche provider.

3. `prompt_checklist`
   Usa questa classe per checklist contenute in prompt, documenti guida o acceptance criteria storici.

4. `local_note`
   Usa questa classe per note inline limitate a un frammento di esempio o prototipo.

## Esito

Backlog operativo reale identificato:
- CED bootstrap
- Wiki requests + SSE
- Operazioni hardening/GPS/test residuali
- Capacitas backlog residuo
- validazione ANPR pre go-live
- import Ruolo 2024 su dati reali

Da non trattare come debito runtime:
- checklist nei prompt
- TODO inline locali
- stati generici di milestone senza task atomico
