# SISTER: navigazione e recupero sezioni, 3-5 ottobre 2026

## Perimetro e invarianti

Intervento sul batch perpetual `1b235a03-5d98-4bbc-8a7c-efa2bae0b842`.
Marika esclusa: nessuna modifica di account, password, abilitazioni o calendario.
Nessun commit o push. Nessuna modifica alla durata assoluta di recupero di 24 ore,
agli ID remoti, al proprietario delle richieste o al limite di 20 richieste aperte.

## Diagnosi verificata

- Tutti i 953 artifact dei fallimenti `Submit visura non avanzato` mostrano
  la sezione obbligatoria: Terralba 426, Arborea 275, Oristano 241, Sili 11.
- 659 hanno un collegamento catastale `matched` e una sezione canonica presente
  nel menu SISTER. Nella fotografia iniziale 478 superavano i controlli locali;
  altri 181 conservavano `session_recovery` da un tentativo precedente.
  Il controllo completo dei raccordi della campagna il 5 ottobre ammette 645
  candidati SQL: il dato canonico da solo non autorizza il retry.
- 294 non hanno una sezione canonica utilizzabile; 270 riguardano Arborea con
  collegamento confermato ma sezione vuota. Non scegliere una sezione per tentativi.
- 219 fallimenti login storici riguardano l'area visure; 217 artifact mostrano
  `Scelta province`, con form `/Visure/DataRichiesta.do` e select `listacom`,
  pur mantenendo `Informativa.do` nell'URL.
- 106 originali appartengono a credenziali disattivate (Carlo 45, Gabriele 61).
  Non riassegnarli ad altri account e non riattivare credenziali automaticamente.

## Correzioni

`sister_browser_reliability.is_visura_area_ready` riconosce il form province
soltanto se il select e visibile dentro il form visure effettivo. Un'informativa
senza quel form resta non pronta. La regressione Playwright percorre anche
la scelta del territorio e raggiunge il form catastale.

`recover_sister_sections` ammette anche il codice residuo `session_recovery`,
ma mantiene tutti i controlli su collegamento canonico, dati della particella,
artifact esplicito, tentativi, documento, claim ed evidenza remota. Gli altri
codici continuano a bloccare. Il recupero conserva richiesta, tentativi e diagnosi.

Il 5 ottobre quattro richieste di Annamaria, inviate il 2-3 ottobre e ancora
pending, sono state messe in revisione tramite la policy esistente. Le righe
sono state bloccate transazionalmente e verificate senza claim o documento;
ID, URL, stato remoto, primo invio, credenziale e tentativi sono rimasti invariati.
Nessun reinvio. Il planner ha successivamente rioccupato gli slot liberati.

## Rilascio e recupero operativo

Il 3 ottobre e stato ricreato soltanto `gaia-elaborazioni-worker-visure`, usando
un'immagine derivata dal runtime presente sul CED e modificando un solo file.
Ambiente, comando e mount sono stati confrontati prima del rilascio.
Immagine attiva: `sha256:2adb7bf3036f48a46373b7748d484c75bd62da199829da438d373760dda1cf6d`.
Il browser smoke dell'immagine e passato senza connessioni esterne.
Rollback disponibile nell'immagine `gaia-elaborazioni-worker-visure:sister-before-20261003`.
Il 5 ottobre il worker e healthy e l'hash del fix coincide con il checkout.

Task operativo temporaneo sul CED:
`/opt/gaia/runtime-data/sister-recovery-20261003/recover-sections.sh`.
Log: `/opt/gaia/runtime-data/sister-recovery-20261003/recovery.log`.
PID: `/opt/gaia/runtime-data/sister-recovery-20261003/recovery.pid`.

Il task ha lock esclusivo e timeout totale di 48 ore. Prima del canary applica
la scadenza esistente alle sole richieste pending, senza claim o documento,
escludendo quelle di Marika; la scadenza e la prenotazione del canary condividono
il lock del batch, per evitare che il planner sottragga lo slot appena liberato.
Il canary e `22878c81-cab6-4bc0-b263-4c3082e9b14b`, Oristano, sezione A.
Solo dopo un PDF con firma, dimensione e SHA-256 coerenti avvia recuperi fino a
20 per passaggio, sempre entro la capacita libera. Un fallimento del canary,
errore DB o timeout ferma il task; nessun ampliamento del calendario.

All'avvio del task il canary attende ancora capacita: il recupero non e dichiarato
completato. Il lunedi i profili correnti riprendono alle 15:00 Europe/Rome.
Una richiesta accodata fuori fascia non autorizza un accesso anticipato a SISTER.

## Verifiche

- 5 ottobre: 46 test navigazione/browser e 11 test recupero sezioni superati.
  Entrambi i runtime al 100% statement e branch.
- 3 ottobre: 14 test su PostGIS effimero, inclusi i tre casi di concorrenza
  del refill, superati; recupero sezioni al 100% statement e branch.
- Ruff sul perimetro modificato e ratchet rispetto a `HEAD@fccd06b0`: verdi.
  Metriche cognitive/ciclomatiche/LOC invariate: readiness `13/11/10`,
  eleggibilita sezioni `16/13/25`. Baseline non modificata.
- Il confronto con `origin/main` segnala la violation preesistente di
  `_is_non_blocking_init_portale_error`, non modificata da questa change.
- Suite worker completa non verde: 23 `NameError` in
  `test_worker_reliability.py`, gia presenti nei file invariati di HEAD.
  La prima esecuzione richiedeva inoltre il PYTHONPATH della root per il report
  `scripts.sister_autosync_efficiency`; il rerun rende visibili i NameError.
- Lint globale: il 3 ottobre era bloccato dal formatter di
  `backend/tests/test_wiki_data_mcp.py`; il rerun del 5 ottobre e bloccato da
  `backend/app/modules/presenze/services/shift_ccnl.py`. Entrambi sono estranei
  al perimetro. Nessuna correzione o baseline assorbita per nasconderli.

## Limiti aperti

Serve completare il dato sorgente delle sezioni mancanti e verificare manualmente
gli originali scaduti o legati a credenziali disattivate. Il 5 ottobre anche
Annamaria mostra `account_not_enabled`: e un problema di abilitazione sul portale,
non una password da ruotare o un controllo da aggirare. Nessun account modificato.

Riferimenti: [runbook](SISTER_debug_runbook.md),
[policy AutoSync](SISTER_AUTOSYNC_RELIABILITY_2026-09-28.md).
