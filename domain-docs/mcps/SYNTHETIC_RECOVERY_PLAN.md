# Recupero selettivo MCP — 2026-10-01

## Obiettivo e perimetro

Recuperare le responsabilita utili dei checkout storici, non integrarli in blocco.
Protocollo nuovo `gaia-synthetic-comparison-v1`: non e il freeze v1/v2/v4 della tesi
e non modifica query, hash, approvazioni o artifact storici. Solo dati prodotti dal
generatore sintetico verificato; nessun corpus Docs, documento reale, SQL operativo,
Ollama, Granite o nuovo orchestratore.

## Requisiti implementati e progress

- [x] Harness riproducibile: condizioni Static/MCP abbinate per caso/ripetizione,
  ordine seeded, manifest che lega dataset, casi/oracle, budget e hash del codice.
- [x] Journal JSONL append-only, flush/fsync, lock esclusivo non bloccante,
  resume delle condizioni concluse, retry limitati dei soli errori di esecuzione.
  Risposte errate non vengono ritentate per migliorare il risultato. Configurazione
  diversa, JSON corrotto o ultima riga incompleta fermano il resume; nessuna
  riparazione/cancellazione automatica. Lock POSIX: ambiente Linux GAIA.
- [x] Scoring di identita, fatti/campi, citazioni e assenza verificata. JSON invalido,
  UUID non stringa, duplicati, campi inventati e citazioni errate non passano.
- [x] Baseline lexical Static RAG: FTS5 in memoria sui record delle dieci tabelle
  sintetiche, costruito indipendentemente dal ground truth; nessun accesso a Docs.
- [x] Stesso `gpt-reserve`, temperatura zero, domanda/contratto, dataset e limite
  evidenze per entrambe le condizioni. Static non espone tool al modello; MCP usa
  `WikiMCPAgent` e il client HTTP/SDK esistenti, non un altro orchestratore.
- [x] Catalogo esclusivamente `data__*`; verifica dataset remoto prima di inoltrare
  risultati al modello. Il client reale resta `docs_url=None`.
- [x] Trace dei messaggi effettivamente passati al modello, evidenze nel contesto,
  token stimati, chiamate, latenza e scoring. Errori solo per tipo, senza testo
  potenzialmente sensibile/credenziali. Correlation UUID derivato da manifest/item.
- [x] Preview `/wiki/mcp`: autenticazione GAIA, solo due preset sintetici,
  provenance e stati caricamento/assenza/errore; niente testo libero/upload/API legacy.
- [x] Server/auth/orchestratori vecchi conservati come riferimenti, non duplicati.
- [x] Freeze v1/v2 e cinque pending change retrieval-only mainline preservati.

## Contratto e limiti delle metriche

Il modello riceve la domanda sintetica generata e il contratto JSON:
`status: found|absent`, `records`, `citations: [{entity, record_id}]`.
L'oracle `expected` resta locale nel manifest, usato solo dallo scorer. I record
richiesti devono avere esattamente i campi previsti e i relativi valori; citazioni
uniche, note dalle evidenze e corrispondenti ai record della risposta. `absent`
richiede evidenze senza errori e ricerca terminale riuscita a zero risultati,
non troncata e senza cursore, sull'entita richiesta o sul suo parent diretto.
Un avviso trovato seguito da zero pagamenti puo quindi provare l'assenza dei
pagamenti. Per evidenze Static senza tool riconosciuto tutti i risultati devono
essere vuoti. Errore, permesso negato, nessuna ricerca, entita non pertinente o
record inventati non provano l'assenza. Lo scorer verifica il contratto strutturato,
non dimostra da solo la correttezza semantica dei filtri scelti dal modello.

La verifica citazioni non dimostra entailment semantico di prosa libera. Il
protocollo misura correttezza strutturata dei fatti richiesti, non qualita generale
delle risposte italiane. Source-routing accuracy non viene presentata come risultato
scientifico: con una sola fonte Data sarebbe una metrica banale.

Static fa una ricerca lessicale, massimo 50 record poi limite token, dando priorita
a UUID/identificativi nella domanda. Non espande automaticamente relazioni. MCP puo
fare fino a 8 chiamate; entrambi hanno 6000 token stimati di evidenze. Questo non
limita i token totali API/generazione. Static e un baseline dichiarato, non il miglior
RAG possibile: il multi-hop e un limite noto del retriever, non una prova universale
di superiorita MCP. Il corpus Static richiede tutti e tre gli scope sintetici.
Il runner locale usa un principal sperimentale sintetico; la preview passa invece
per il gateway e i permessi reali dell'utente GAIA, senza ampliamenti.

## Matrice funzionalita → comportamento → test

Test backend in `backend/tests/test_wiki_mcp_experiment.py`.

| Funzionalita | Comportamento atteso | Test |
| --- | --- | --- |
| Dataset/casi/renderer | Solo sintetico, oracle indipendente, scope obbligatori | `test_generated_cases_and_static_corpus_are_dataset_only` |
| Configurazione | Limiti ripetizioni/retry/chiamate/token validati | `test_invalid_experiment_limits` |
| Manifest/schedule | Seed/pairing, identita dataset/budget, casi unici | `test_schedule_reproducibility_and_manifest_binding` |
| Scoring formato | Risposte fuori contratto rigettate | `test_malformed_answer_is_not_scored_as_success` |
| Fatti/citazioni/assenza | Rigetta invenzioni, duplicati, assenza non verificata | `test_facts_citations_duplicates_and_no_answer_scoring` |
| Persistenza | Append/resume, lock, mismatch/corruzione fail-closed | `test_journal_append_resume_lock_and_corruption` |
| Privacy | Docs bloccato prima delle chiamate, dataset diverso prima del modello | `test_verified_sources_reject_docs_before_invocation_and_wrong_dataset` |
| Agent/trace | Tool calling corrente, Static senza tool, contratto condiviso | `test_existing_agent_trace_and_static_contract` |
| Retry/interruzioni | Resume senza ripetere successi, errori redatti, tentativi limitati | `test_paired_runner_retry_resume_and_exhaustion` |
| CLI | Piano offline, opt-in live, cleanup, no input Docs | `test_cli_plan_live_and_cleanup` |
| HTTP/SDK | Namespace effettivo, bearer, chiamata reale, zero Docs | `test_comparison_uses_real_sdk_catalog_and_http_tools_without_docs` |
| Paginazione multi-hop | Lookup avviso e tre pagine con cursor reale e provenance distinta | `test_agent_multiple_payments_follows_real_cursors` |
| Assenza multi-hop | Parent positivo ammesso, terminale pertinente e completo, citazioni rigorose | `test_no_payments_scoring_requires_terminal_entity` |
| Budget e permessi | Diniego/esaurimento non diventano assenza verificata | `test_agent_denial_and_exhaustion_do_not_become_valid_absence` |
| Citazione corrotta dal modello | UUID assemblato da due record o citazione duplicata respinti; risposta grezza preservata | `test_model_payment_citation_corruption_is_preserved_and_rejected` (due parametri) |
| UI | Preset-only, auth, provenance, assenza/errori/reset | `frontend/tests/unit/wiki-mcp-preview.test.tsx` |
| Browser | Pagina Next reale, preset, successo e 503 | `frontend/tests/e2e/wiki-mcp-preview.spec.ts` (API simulate) |
| Browser live | Login GAIA reale, gateway, MCP HTTP e modello; UUID e assenza verificati | stesso file, test opt-in `live synthetic login to gateway to MCP to model` |

## Validazione e residui

- [x] MCP coverage statement/branch 100%; preview coverage 100%.
- [x] Regressioni Wiki backend/frontend e browser Chromium con API simulate.
- [x] Pilot live: modello e HTTP/SDK/bearer reali, soltanto sintetico.
- [x] Pilot diagnostico ampliato a tre seed, avvisi non iniziali, paginazione e zero pagamenti.
- [x] Browser con login/auth reali su backend isolato sintetico e provider reale.
- [x] Ruff/format e ratchet mirato senza nuovi errori, baseline invariata.
- [x] Graphify codice Wiki/frontend tramite Make, nessuna estrazione docs remota.
- [x] Gate globali eseguiti; failure concorrenti registrate senza fix fuori scope.
- [ ] Gate globale verde: problemi esterni al recupero, vedi report.
- [ ] Campione tesi definitivo, approvazione umana e freeze del nuovo protocollo.
- [ ] Disegno statistico, campione piu ampio e baseline RAG piu forte se richiesta.
- [ ] Eventuale review/commit separato dei cinque pending change retrieval-only.

Questo recupero non certifica come completati i gate dei checkout esterni. Nessun
commit, push, merge o deploy incluso nelle verifiche successive. Evidenze storiche:
`SYNTHETIC_RECOVERY_REPORT.md`; stato corrente e residui:
`POST_COMMIT_VALIDATION_2026-10-01.md`.
