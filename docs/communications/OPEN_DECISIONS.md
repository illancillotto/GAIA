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
