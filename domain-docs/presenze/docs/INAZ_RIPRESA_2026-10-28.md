# Ripresa sincronizzazione INAZ — 28 ottobre 2026

## Intervento in produzione

Su richiesta dell'utente sono state riabilitate la credenziale INAZ e la
sincronizzazione immediata INAZ → GAIA. Non sono stati modificati codice
runtime, password, mapping identità o configurazione GATE.

La pianificazione automatica era già abilitata, alle 06:00, 12:00 e 18:00
Europe/Rome. Il blocco dipendeva dalla credenziale 1, disabilitata dopo un
errore di login del 21 ottobre: il portale aveva ripresentato la pagina di
accesso. L'ultimo successo precedente risaliva al 21 ottobre alle 13:41 locali.
Questa evidenza non permette di stabilire la causa originaria del rifiuto del
portale. Worker e scheduler erano operativi.

Il 28 ottobre `test_credential`, eseguito con il proprietario effettivo della
credenziale, ha verificato il login e riattivato la credenziale tramite i
servizi esistenti. `trigger_auto_sync_job` ha poi accodato quattro shard per il
periodo 1–31 ottobre, con 49 codici configurati per shard. Non sono stati
eseguiti aggiornamenti SQL manuali, deploy o riavvii.

L'intervento è iniziato alle 09:53 locali (08:53 UTC). L'ultimo job è terminato
alle **11:43:52 locali (10:43:52 UTC)**. Il monitoraggio ha atteso anche tutti
i retry automatici discendenti prima di dichiarare conclusa la campagna.

## Esito verificato

| Controllo | Risultato |
| --- | --- |
| Job iniziali e retry | 9 complessivi, tutti `completed` |
| Codici configurati | 196 |
| Collaboratori restituiti da INAZ per ottobre e acquisiti | 184 |
| Codici configurati non restituiti per il periodo | 12 |
| Collaboratori con errori iniziali | 21, tutti recuperati |
| Errori noti rimasti senza recupero | 0 |
| Giornaliere ottobre negli artefatti acquisiti | 5.704 |
| Giornaliere ottobre nel database | 5.704 |
| Righe mancanti rispetto agli artefatti | 0 |
| Differenze fra `raw_payload_json` salvato e artefatti | 0 |
| Credenziale al termine | Attiva, zero fallimenti consecutivi, nessun ultimo errore |
| Pianificazione automatica al termine | Abilitata |

Il confronto read-only ha utilizzato gli artefatti dei quattro job iniziali e
dei relativi discendenti, conservando l'ultimo payload acquisito per ciascuna
giornata nel namespace INAZ. Non ha creato né modificato associazioni con gli
utenti GAIA. Il controllo ha verificato l'univocità delle matricole INAZ
presenti prima del confronto e non ha esposto nominativi o credenziali.

5.692 giornaliere hanno un `updated_at` successivo all'avvio; altre 12 hanno
mantenuto il timestamp precedente, ma il payload salvato coincide esattamente
con quello riacquisito. Il timestamp non rappresenta quindi da solo il numero
di righe elaborate.

`presenze_daily_records.source_job_id` viene impostato alla creazione della
riga e non riassegnato quando la riga esistente è aggiornata. Per questa
campagna le giornaliere conservano gli import job originari: una selezione
limitata agli `import_job_id` appena creati restituisce zero righe e non è una
verifica valida della riuscita dell'aggiornamento. L'esito sopra deriva dal
confronto completo con gli artefatti, non da quel filtro né dai soli contatori
dei job.

## Integrità identità

L'audit prima e dopo la campagna rileva 196 collaboratori, tutti attivi e
mappati mediante la FK canonica
`presenze_collaborators.application_user_id → application_users.id`.
Sono pari a zero: collaboratori non mappati, identità duplicate, riferimenti
orfani, divergenze del mapping su giornaliere e riepiloghi eventi, collaboratori
mappati senza un unico `WCOperator` canonico. Nessun mapping è stato cambiato.

## Segnalazioni residue

I 12 codici non restituiti dal portale per ottobre restano distinti dai 21
errori recuperati. La campagna non dimostra la ragione della loro assenza dal
periodo e non permette di dichiarare aggiornati tutti i 196 collaboratori
configurati.

L'indicatore aggregato prodotto da `build_inaz_sync_status(month="2026-10")`
rimane `degraded`, con `error_code=inaz_sync_partial`. La logica attuale richiede
che ogni job della coorte sia completato senza contatori di errore. I job
iniziali conservano gli errori storici anche quando i discendenti acquisiscono
con successo i collaboratori interessati; l'indicatore non riconcilia tali
recuperi. Al controllo finale `last_success_at` e `data_updated_at` indicano
10:00:51 UTC, mentre l'ultima scrittura dati della campagna è delle 10:43:51
UTC. Questi metadati non descrivono quindi l'istante finale di questa campagna.
Non sono stati azzerati contatori storici per modificare l'indicatore.

## Evidenze operative

Gli script di intervento, monitoraggio e audit sono conservati nell'area
operativa protetta `/opt/gaia/releases/inaz-reactivation-20261028/`; le
verifiche locali sono in `/tmp/gaia-inaz-reactivation-20261028/`. Non rieseguire
lo script di riattivazione: accoderebbe una nuova sincronizzazione.

Job radice, utili per ricostruire la campagna tramite
`params_json.parent_sync_job_id`:

- `51c64612-1e67-4975-88d4-df7b33ed8a17`
- `f6c6b429-9e16-48c0-97d6-6cbef5ea4102`
- `78056c6a-e6f1-40d7-84f4-a63f6249c7a5`
- `3a0ad168-ea8d-4023-9dd5-d42050563afd`

Non essendoci modifiche runtime, non si applicano nuovi obiettivi di coverage
o complessità a questo intervento operativo. La verifica pertinente è il
riscontro end-to-end della campagna e dell'integrità dei dati persistiti.
