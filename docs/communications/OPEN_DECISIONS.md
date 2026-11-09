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
| NAS e firewall CED | IT/DBA | Grant verificati sul clone completo e ruolo ristretto applicato; NAS/firewall da collaudare prima dell'abilitazione dei trasporti |
| Altre annualità/moduli e CC/CCN/HTML | Product owner | Solo Ruolo2021, destinatario singolo, testo semplice |
| Formati PEC proprietari/CMS multipli | IT/provider | Non classificati automaticamente, EML conservati |
| Inbox preesistenti/voluminose o EML oltre32MiB | IT | Readonly, triage cursore senza eliminazione automatica |
| Rotazione delle credenziali mostrate durante la preparazione del rilascio | IT | Incidente segnalato; rotazione coordinata ancora necessaria, nessun valore riportato in documentazione |

Questi punti non impediscono il collaudo sintetico e non autorizzano credenziali,
atti, produzione o deployment.

L'autorizzazione successiva al rilascio CED del 4 novembre e le verifiche
operative sono registrate in
[DEPLOYMENT_REPORT_2026-11-04](DEPLOYMENT_REPORT_2026-11-04.md).
Non autorizzano l'attivazione dei trasporti o invii a recapiti reali.

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

## Anteprima del 4 novembre — pubblicata, recapiti ancora separati

La preview immediata è pubblicata e verificata su PDF reale. Il registro Utenze
classificato, la migrazione 20261104_1400 e il backfill non sono inclusi nella
patch: l'elenco PEC mostra ancora le 17 righe del campo aziende legacy.
Riacquisire e verificare il piano dati prima di applicarlo; 14 discordanti ai
colleghi e nessuna inferenza dal dominio. Configurazione provider e invii reali
rimangono soggetti al collaudo autorizzato. Dettagli in SOURCE_PREVIEW_2026-11-04.md.

## Aggiornamento 05/11/2026

Il rilascio del registro recapiti è concluso: non è più un blocco esterno.
Restano all'ufficio 14 soggetti discordanti e i recapiti da verificare, compresi
quattro valori invalidi in quarantena e una PEC revocata. I dati originali
restano invariati. Nessuna classificazione automatica dal solo dominio e
nessun collaudo con destinatari reali. Stato verificato: [CONTACT_RELEASE_2026-11-05](CONTACT_RELEASE_2026-11-05.md).
