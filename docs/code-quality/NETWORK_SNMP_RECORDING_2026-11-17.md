# Batch registrazione metriche SNMP Network — 2026-11-17

Esito **NO_SAFE_CHANGE**, consegna **TEST_ONLY**. Il runtime
`backend/app/modules/network/sophos_snmp.py` rimane identico. Il candidato
estratto in `/tmp` avrebbe sostituito un Warning ciclomatico con un Warning
sui parametri; non viene contato come miglioramento.

## Candidato respinto

Separare la registrazione delle letture dalla gestione del firewall e della
transazione richiede db, firewall, host, definizioni OID e valori. L'helper
avrebbe cinque parametri, raggiungendo la soglia Warning. Il polling scenderebbe
sotto soglia, ma il saldo delle violation resterebbe zero.

| Metrica | Runtime originale/finale | Candidato esterno respinto |
| --- | ---: | ---: |
| Polling: cognitiva | 12 | 9 |
| Polling: ciclomatica | 11 | 9 |
| Polling: LOC | 40 | 23 |
| Polling: nesting | 2 | 1 |
| Cognitiva file | 70 | 70 |
| Ciclomatica file | 64 | 65 |
| Somma cyclomatic meno 1 | 53 | 53 |
| Callable | 11 | 12 |
| LOC file | 190 | 199 |
| Error | 1 | 1 |
| Warning | 1 | 1 |

Helper candidato cognitive/cyclomatic/LOC/nesting `3/3/26/2`, parametri 5:
nuovo Warning sui parametri. Il candidato non e stato applicato o certificato
come equivalente. Non si introducono contenitori artificiali per ridurre il
numero di parametri, ne si anticipano letture ORM per semplificare la firma.

## Caratterizzazione consegnata

Nuovo `backend/tests/test_network_snmp_recording.py`: 16 casi che esercitano il
polling e la registrazione originale, includendo add e flush delle metriche.

- Ordine delle definizioni OID e duplicati preservati, anche con valori
  restituiti in ordine diverso; definizioni senza lettura saltate prima dei
  getter opzionali e dell'accesso all'ID del firewall.
- ID del firewall letto per ogni metrica e valori[key] letto separatamente
  per conversione e raw_payload: il secondo valore puo differire dal primo.
- Un batch con valori non vuoti ma senza definizioni corrispondenti aggiorna
  comunque last_seen/status del firewall ed esegue il commit.
- Ogni metrica viene aggiunta e flushata prima della finalizzazione del
  firewall. Unico commit dopo tutti i record, last_seen/status e add firewall.
- Errori iniettati su lettura, upsert, ID, primo/secondo add e flush, setter
  firewall, add finale e commit: stato parziale e arresto al punto originale,
  senza nuovi rollback o retry.

## Verifiche

Artefatti `/tmp/gaia-network-snmp-recording-refactor-20261117/`.

- 164 test PASS, zero failure/error/skip: servizi Network, API, caratterizzazioni
  SNMP precedenti e 16 nuovi casi. Nessun test esistente modificato.
- Runtime full-file statement/branch 100%: 121/121 statement e 44/44 branch;
  zero esclusioni, righe mancanti o branch parziali.
- Cinque mutanti solo in memoria respinti dalla nuova caratterizzazione:
  deduplica impropria (1 failure), ID firewall letto una volta (3), valore
  grezzo letto una volta (1), commit per metrica (8), mancata finalizzazione
  del batch senza corrispondenze (1). Nessun errore di collection o skip.
- Ratchet mirato origin/main PASS; globale exit 2 per la stessa ambiguita
  preesistente Tributi useEffect[0]<callback>, dieci candidati. Merge-base
  `686e529ee011487e0764b9f91d023be063dbdf55`. Nessun PASS globale dichiarato.
- Report completo corrente identico al precedente per tutti i file, callable,
  violation e aggregati: 1.963 file, 22.637 callable, 1.897 Error, 2.949 Warning,
  zero parse/exception error. Nessuna riduzione conteggiata in questo turno.
- Ruff e format del nuovo test, lint-backend 251 file e diff-check PASS.
  Nessuna nuova failure applicativa; 98 warning JWT API preesistenti.
- Graphify Network via Make: nessuna variazione della topologia. Esito
  platform docs e controllo chunk/warning semantici nel checkpoint finale.
- Hash runtime, slice precedenti, baseline, eccezioni, test preesistenti e
  report condivisi preservati. Nessuna baseline sync/verify; nessuna modifica
  a soglie, scope, matcher o gate. Modifiche concorrenti preservate.

Comandi principali dalla root:

```bash
COVERAGE_FILE=/tmp/gaia-network-snmp-recording-refactor-20261117/.coverage DATABASE_URL=sqlite:////tmp/gaia-network-snmp-recording-refactor-20261117/test.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_services.py backend/tests/test_network_api.py backend/tests/test_network_sophos_snmp.py backend/tests/test_network_snmp_response.py backend/tests/test_network_snmp_recording.py --junitxml=/tmp/gaia-network-snmp-recording-refactor-20261117/tests.xml
COVERAGE_FILE=/tmp/gaia-network-snmp-recording-refactor-20261117/.coverage backend/.venv/bin/python -m coverage json --include='*/network/sophos_snmp.py' -o /tmp/gaia-network-snmp-recording-refactor-20261117/coverage.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-snmp-recording-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/sophos_snmp.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-patch-openai-base-url
make graphify-platform-docs
```

## Stato e prossima azione

HEAD iniziale `8f65d353c7ecbf9d055dcecd564b617c6278cf6e`. Singolo hotspot
esaminato; nessun commit/push/merge/deploy o secondo hotspot avviato.
Restano 23 slice migliorative dalla ripresa: −21 Error, −24 Warning,
−140 cognitiva aggregata. Questa consegna TEST_ONLY non incrementa quei numeri.

Restano il Warning del polling e l'Error parametri record_firewall_metric.
Prossima azione: review della caratterizzazione, poi selezione di un altro
hotspot dal report. Il goal generale di riduzione rimane attivo.
