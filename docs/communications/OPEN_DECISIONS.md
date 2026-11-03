# Decisioni esterne e limiti

| Decisione/verifica | Responsabile | Comportamento in attesa |
| --- | --- | --- |
| Autorizzazione caselle/provider e recapiti collaudo | Ente/IT | Trasporto false, nessun invio reale |
| Contratto/auth/MFA/password applicativa/rinnovo OAuth2 | IT/provider | Parametri configurabili; guide pubbliche consultate, account reale non collaudato |
| Testi e uso recapito PEC per procedimento | Ufficio competente | Due seed draft, email solo cortesia, conferma individuale |
| CA/pin PEC e rotazione firmatari | IT/responsabile | Senza trust, nessuna classificazione certificata |
| Perfezionamento giuridico | Responsabile procedimento | Solo evidenze tecniche; NoticeNotification immutato |
| Conservazione, archivio a norma, backup/restore | Ente/documentale | Nessun termine inventato o cancellazione automatica |
| Reinvio dopo incerto/esito trasmesso | Ufficio/provider | Nessun comando di reinvio o retry incerto |
| Bozze/invii portale Poste esterni al DB | Operatore | Coordinamento manuale necessario |
| Fonte recapiti PF PEC/PG email non presente nello schema | Anagrafica/ufficio | Nessuna inferenza, inserimento e verifica espliciti |
| Grants, NAS, firewall e restore CED | IT/DBA | Esempi preparati, non applicati alla produzione |
| Altre annualità/moduli e CC/CCN/HTML | Product owner | Solo Ruolo2021, destinatario singolo, testo semplice |
| Formati PEC proprietari/CMS multipli | IT/provider | Non classificati automaticamente, EML conservati |
| Inbox preesistenti/voluminose o EML oltre32MiB | IT | Readonly, triage cursore senza eliminazione automatica |

Questi punti non impediscono il collaudo sintetico e non autorizzano credenziali,
atti, produzione o deployment.

## Baseline del branch — risolto

Il precedente blocco di sincronizzazione è risolto nel commit d826c904 tramite
la procedura per runtime già committato, verificata in worktree isolato e nel
checkout canonico. Nessun refactoring Poste o nuova esclusione; ratchet main
sempre autorevole e verde. Evidenze in BASELINE_REPAIR.md.

## Configurazione di dominio

La prova con il repository contabile reale conferma che il default2021 è
external_recovery/STEP. Un avviso non diventa eleggibile perché compare nella
tabella Communications: occorre la configurazione di gestione canonica e la
revisione delle posizioni prevista dal Ruolo. Nessuna configurazione tributaria
reale è stata modificata o automaticamente aggirata.

Il collaudo NAS deve includere la policy host-key del connector condiviso e
il download in memoria prima del limite PDF: debito preesistente descritto in
SECURITY/FINAL_REVIEW, non dichiarato risolto dai test sintetici.


## Gate finale — regressione generale residua

La suite PG collettiva attivata nella verifica finale incontra un errore di
setup GeoAlchemy/GeometryCompat, riprodotto anche sul commit9676aaa7 prima di
Communications. Non è stato modificato il modello Catasto condiviso: il fix e
la stabilizzazione della composizione dei fixture richiedono un ciclo dedicato.
Restano inoltre prove legacy con requisiti PostGIS/schema migrato e dipendenze
GIS mancanti. Il gate complessivo è FAIL; il dettaglio delle corse isolate e
la distinzione rispetto al100% del runtime Communications sono in FINAL_REVIEW.
