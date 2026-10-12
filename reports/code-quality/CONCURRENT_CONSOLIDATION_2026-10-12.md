# GAIA — consolidamento selettivo dei 22 file concorrenti

## Perimetro e decisione

Verifica e commit locali autorizzati dall'utente, separati dalla campagna di
complessità. La campagna resta **PAUSED / INCOMPLETE**: nessuna nuova slice,
nessun refactoring correttivo, nessun push, deploy, backfill o accesso alla
produzione. I candidati esclusi della campagna non sono stati riammessi.

- Checkout: `/home/cbo/CursorProjects/GAIA`; branch: `main`.
- HEAD e merge-base con `main` all'inizio delle verifiche:
  `1012faddc6d05b50be2593b3dc7814c3437b6793`.
- Snapshot iniziale della precedente campagna:
  `55a1b1d35911451e018b662c2acc450bf5994ea2`; non è il nuovo merge-base dopo
  l'integrazione già autorizzata della campagna.
- Inventario iniziale: 22 file concorrenti, nessun file staged; 9 Elaborazioni,
  8 Presenze, 4 Ruolo, 1 audit storico.
- Risultato: **13 file originali ammessi e committati; 9 conservati fuori dai
  commit**. Questo documento è un ulteriore file di checkpoint.
- Tutti i 22 file mantengono i byte dell'inventario iniziale. La verifica non ha
  modificato codice, test, configurazione applicativa o documenti preesistenti.

## Commit ammessi

| Responsabilità | Commit | File originali |
| --- | --- | ---: |
| Audit storico dell'8 ottobre | `2564d62d9ec3408df7992664cb71c9729194376c` | 1 |
| Diagnostica INAZ e calendario individuale Presenze | `8de27a20f0121fb4936c87f1fa5dec3bfe68f4e7` | 8 |
| Colonne destinatario Poste, Ruolo | `bd9dba9672f7f95e1b17b048f7ae12e4d75406ea` | 4 |

Staging esplicito per dominio, confronto SHA256 dei blob staged con gli originali
archiviati e `git diff --cached --check` prima dei commit. Il generatore automatico
di documentazione è stato saltato mediante il flag supportato
`SKIP_DOCS_UPDATE=1`; ogni gruppo include la propria documentazione già presente.
Il commit di questo checkpoint è identificabile con `git log --` sul documento.

## Ownership e inventario

L'origine è il lavoro concorrente inventariato su `main`, non le branch dello
swarm. L'autorizzazione corrente riguarda la verifica e il consolidamento di
questi file; non attribuisce retroattivamente la loro autoria agli agenti della
campagna. L'agente di questa sessione è responsabile della verifica e dello
staging selettivo. I percorsi e gli hash completi sono nel manifest di handoff.

| File | Classificazione | Esito |
| --- | --- | --- |
| `backend/app/modules/presenze/services/gate_mobile_payloads.py` | AMMESSO | Commit Presenze |
| `backend/app/modules/presenze/services/operai_schedule_policy.py` | AMMESSO | Commit Presenze |
| `backend/app/modules/presenze/services/gate_inaz_details.py` | AMMESSO | Commit Presenze |
| `backend/app/modules/presenze/services/inaz_assigned_calendar.py` | AMMESSO | Commit Presenze |
| `backend/tests/test_gate_mobile_sync.py` | AMMESSO | Commit Presenze |
| `backend/tests/test_gate_inaz_details.py` | AMMESSO | Commit Presenze |
| `backend/tests/test_presenze_inaz_assigned_calendar.py` | AMMESSO | Commit Presenze |
| `domain-docs/presenze/docs/INAZ_CONTRACT_RULES_ALIGNMENT_2026-10-08.md` | AMMESSO | Commit Presenze; note operative storiche |
| `backend/app/modules/ruolo/tributi_repositories.py` | AMMESSO | Commit Ruolo |
| `backend/app/modules/ruolo/services/posta_online_recipient_columns.py` | AMMESSO | Commit Ruolo |
| `backend/tests/ruolo/test_posta_online_recipient_columns.py` | AMMESSO | Commit Ruolo |
| `domain-docs/ruolo/docs/POSTE_ADDRESS_MAPPING_REPAIR_2026-10-07.md` | AMMESSO | Commit Ruolo; note operative storiche |
| `reports/code-quality/COMPLEXITY_AUDIT_2026-10-08.md` | AMMESSO | Audit storico, non scansione corrente |
| `backend/app/modules/elaborazioni/domande_irrigue_autosync_scheduler.py` | PARZIALE | Non committato: gruppo non certificato |
| `backend/app/modules/elaborazioni/domande_irrigue_parallel.py` | PARZIALE | Non committato: gruppo non certificato |
| `backend/app/services/elaborazioni_capacitas_runtime.py` | PARZIALE | Non committato: coverage artificiosa |
| `backend/app/modules/elaborazioni/domande_irrigue_refresh.py` | PARZIALE | Non committato: dipendenza della stessa change |
| `backend/tests/test_domande_irrigue_autosync_scheduler.py` | PARZIALE | Non committato |
| `backend/tests/test_domande_irrigue_refresh.py` | PARZIALE | Non committato |
| `backend/tests/test_capacitas_runtime_refresh_contract.py` | RESPINTO | Metodo di copertura artificioso; file conservato |
| `config/capacitas/compose.conservative.yml` | PARZIALE | Non committato né applicato |
| `domain-docs/elaborazioni/docs/CAPACITAS_POLITE_SYNC_2026-10-07.md` | PARZIALE | Non committato con la change dipendente |

Cache, SQLite di test, coverage nativa e output Graphify sono GENERATI: non
versionati. Non è stato eliminato o sovrascritto alcun lavoro concorrente.

## Test e coverage

Esecuzioni seriali GAIA, ciascuna una sola volta, con il virtualenv esistente:
runner esterno `verify_domain.py ELABORAZIONI|PRESENZE|RUOLO`. Ambiente sintetico,
caricamento dotenv disabilitato e database SQLite privati sul disco delle
evidenze. Comandi, lista completa dei test, log, exit code, JUnit, coverage JSON
e dati nativi sono archiviati. Nessuna installazione di dipendenze.

| Gruppo | Test PASS | Skip | Failure/error | Coverage numerica | Ammissione |
| --- | ---: | ---: | ---: | --- | --- |
| Presenze | 421 | 0 | 0 | 100% statement/branch, quattro file completi | Sì |
| Ruolo | 710 | 392 | 0 | 100% statement/branch nel perimetro configurato | Sì, con limiti sotto |
| Elaborazioni | 126 | 0 | 0 | 100% riportato, ma un ramo è fabbricato dal test | No |

| Runtime ammesso | Statement coperti/totali | Branch coperti/totali | Righe escluse |
| --- | ---: | ---: | ---: |
| `gate_mobile_payloads.py` | 133/133 | 40/40 | 0 |
| `operai_schedule_policy.py` | 42/42 | 12/12 | 0 |
| `gate_inaz_details.py` | 10/10 | 0/0 | 0 |
| `inaz_assigned_calendar.py` | 7/7 | 2/2 | 0 |
| `tributi_repositories.py` | 1861/1861 | 722/722 | 2, preesistenti |
| `posta_online_recipient_columns.py` | 12/12 | 4/4 | 0 |

Le due righe Ruolo escluse sono la guardia `tributi_item is None` e il suo corpo,
oggi alle righe 3362/3363: la direttiva motivata `pragma: no cover - guarded by
caller and DB FK.` e il corpo sono identici allo snapshot iniziale, alle righe
3361/3362. Non sono nuove esclusioni e **non sono dichiarate verificate**.

I 392 skip Ruolo richiedono PostgreSQL, soprattutto per concorrenza e row lock;
`GAIA_TEST_POSTGRES_URL` non è configurato nell'ambiente sintetico. Restano
**non verificati**, non PASS. I 449 skip della precedente certificazione backend
della campagna restano distinti e non verificati; non sommare i conteggi come se
rappresentassero test indipendenti. Suite completa backend, frontend, worker,
build ed E2E non sono state ripetute. I certificati R60/R61/R62 non sono una prova
delle successive modifiche concorrenti.

Warnings conservati: chiave JWT sintetica corta e `coverage --include` ignorato
in raccolta perché la configurazione esistente imposta `source=app`. I report
per-file verificano comunque tutti i file runtime toccati, non soltanto le righe
modificate. Nessuna configurazione coverage o filtro warning è stato cambiato.

## Blocco Elaborazioni

`test_incass_empty_attempt_sequence_and_non_dict_resume_state` sostituisce
`runtime.range` con una funzione che restituisce `[]`. Questo fabbrica l'uscita
per esaurimento del ciclo retry, invece di caratterizzare un comportamento
raggiungibile del worker. Il `range(1, len(delays) + 2)` reale è sempre non vuoto;
il retry può continuare solo prima dell'ultimo tentativo, che termina con
`return`, come i percorsi successo, job assente ed errore credenziali.

Il 100% numerico dipende quindi da una sostituzione della primitiva del linguaggio,
non dal solo mock di un confine esterno. Non viene usato per ammettere la change.
Il medesimo test contiene anche una verifica legittima dello stato di resume non
dict: conservarla nella futura soluzione. Tutti i nove file rimangono nel working
tree e nell'archivio immutabile. Nessuna riparazione o nuova slice è stata avviata.

## Stile, ratchet e metriche

- `BASE_REF=main make style-ratchet QUALITY_PYTHON=backend/.venv/bin/python`:
  PASS su 17 file Python, inclusi i controlli format dei nove file Python nuovi.
- `make complexity-ratchet BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python`:
  PASS, **zero finding**, eseguito prima dei commit, quando `main` e merge-base
  erano entrambi `1012faddc6d05b50be2593b3dc7814c3437b6793`.
- Nessun confronto contro `main` avanzata dai nuovi commit è stato usato per
  nascondere la change. I byte degli input sono rimasti identici dopo i gate.
- `git diff --check` e i diff staged: PASS.
- Baseline, soglie, matcher, eccezioni, ignore e policy coverage: invariati.
  Nessuna esecuzione di `complexity-baseline` o `baseline-repair`.
- Il FAIL/ambiguità integrale storico resta separato dal ratchet di questa change;
  non è stato risolto o assorbito.

Misure AST prima/dopo contro gli input iniziali, in `runtime-metrics.json`:

| Runtime/callable ammesso | Prima | Dopo | Nota |
| --- | --- | --- | --- |
| `gate_mobile_payloads.py`, LOC effettive | 351 | 352 | Contratto diagnostico aggiuntivo |
| `operai_schedule_policy.py`, LOC effettive | 75 | 79 | Calendario attestato |
| `has_individual_saturday`, cognitive/cyclomatic | 3/4 | 5/6 | Sotto soglia, non una riduzione dichiarata |
| `tributi_repositories.py`, LOC effettive | 3692 | 3693 | Correzione parser locale |
| `_parse_posta_online_detail_html`, cognitive/cyclomatic | 28/23 | 26/22 | Helper nuovo, nessuna regressione ratchet |
| `gate_inaz_details.py`, LOC effettive | Nuovo | 48 | Proiezione diagnostica |
| `inaz_assigned_calendar.py`, LOC effettive | Nuovo | 12 | Calendario individuale |
| `posta_online_recipient_columns.py`, LOC effettive | Nuovo | 14 | Discriminazione colonne |

Questa è manutenzione funzionale concorrente consolidata, **non** una nuova
wave di complessità, né una rivendicazione di riduzione globale del debito.

## Graphify

Target dedicati `graphify-presenze-code` e `graphify-ruolo-code`: exit 0,
ricontrollo AST senza variazioni di topologia rispetto ai grafi locali presenti.
Patch locale `graphify-patch-openai-base-url` già applicata e verificata.

- Presenze docs: target dedicato, `gpt-reserve` imposto dopo il loader locale
  che configurava `gpt-5.5`; 33 cache hit, sei file riestratti, `chunk 1/1 done`,
  nessun warning di chunk falliti. 1198 nodi, 2229 archi, 77 comunità;
  3945 token input / 3491 output, costo stimato dal tool $0.0072.
- Ruolo docs: target dedicato, stesso modello; 31 cache hit, zero miss, nessuna
  richiesta semantica necessaria e nessun warning di chunk falliti. 1312 nodi,
  2913 archi, 70 comunità. Nessun `chunk done` atteso per una scansione interamente
  servita dalla cache.
- Nessuna estrazione dalla root grezza. Grafi non committati; snapshot e checksum
  conservati nell'handoff. Non sono prove della complessità o dei test.

## Evidenze durevoli e handoff

Archivio privato:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-concurrent-consolidation-20261012`.
Manifest congelato: `HANDOFF_MANIFEST_v1.json`.
SHA256: `895b498216495684646aaab9029e230b0e2e17e1682dd6321a5e980116dedb65`.

Il manifest contiene i 22 originali content-addressed, classificazione,
commit, input dei test, hash dei log/coverage/JUnit/script, checksum della policy
invariata e copie dei quattro grafi. Cache e SQLite di test non sono oggetto di
commit o di conservazione documentale obbligatoria. Gli archivi precedenti di
pausa e integrazione restano intatti. Il report storico dell'8 ottobre è
versionato byte-identico, SHA256
`ca7e10237398594a3452fd20106472881e4d6240a2746c8b354534d7783a2484`;
non si dichiarano presenti i precedenti report AST temporanei ora assenti.

Un primo tentativo del solo helper di staging ha fallito prima di fare `git add`
per un'etichetta `AUDIT` diversa da `AUDIT_HISTORICAL`; ricevuta conservata in
`audit-commit.log`. Correzione limitata allo script esterno, nessuna failure
applicativa riparata e nessun retry delle suite.

La ricevuta successiva `FINAL_CHECKPOINT_RECEIPT.json`, esterna al repository,
registra il commit di questo documento e il controllo finale dei residui.
Prossimo passo, **non automatico**: decisione separata sul ramo retry e sul test
artificioso Elaborazioni, quindi gate pertinenti prima di ammettere il gruppo.
Nessuna ripresa della campagna è autorizzata da questo checkpoint.
