from __future__ import annotations

from app.modules.wiki.services.logic_catalog_common import LogicExplanation

CATALOG_OPERAZIONI_CASE_STATUS: dict[str, LogicExplanation] = {
    "open": LogicExplanation("Regola workflow Operazioni: case open", "operazioni.logic.case_status.open", "Il case e appena aperto e non ancora assegnato o preso in carico.", "Un case `open` e stato creato ma non e ancora stato assegnato o preso in carico operativamente."),
    "assigned": LogicExplanation("Regola workflow Operazioni: case assigned", "operazioni.logic.case_status.assigned", "Il case e stato assegnato a un utente o team.", "Un case `assigned` ha gia un assegnatario, ma non e ancora stato formalmente preso in carico."),
    "acknowledged": LogicExplanation("Regola workflow Operazioni: case acknowledged", "operazioni.logic.case_status.acknowledged", "Il case e stato riconosciuto dall'assegnatario e pronto alla lavorazione.", "Un case `acknowledged` e stato visto e accettato dall'assegnatario, ma non e ancora in esecuzione."),
    "in_progress": LogicExplanation("Regola workflow Operazioni: case in progress", "operazioni.logic.case_status.in_progress", "Il case e in lavorazione attiva.", "Un case `in_progress` e in lavorazione attiva e dovrebbe avere una presa in carico operativa gia registrata."),
    "resolved": LogicExplanation("Regola workflow Operazioni: case resolved", "operazioni.logic.case_status.resolved", "Il case e stato risolto ma non ancora chiuso definitivamente.", "Un case `resolved` ha una risoluzione registrata, ma non e ancora stato chiuso definitivamente."),
    "closed": LogicExplanation("Regola workflow Operazioni: case closed", "operazioni.logic.case_status.closed", "Il case e stato chiuso e non e piu nel ciclo operativo attivo.", "Un case `closed` e stato chiuso formalmente e non e piu nel ciclo operativo attivo."),
    "reopened": LogicExplanation("Regola workflow Operazioni: case reopened", "operazioni.logic.case_status.reopened", "Il case era chiuso o risolto ed e stato riaperto.", "Un case `reopened` era stato chiuso o risolto, ma e stato riattivato per ulteriori lavorazioni."),
}

CATALOG_OPERAZIONI_ASSIGNMENT_STATUS: dict[str, LogicExplanation] = {
    "open_operator": LogicExplanation("Regola workflow Operazioni: assegnazione mezzo attiva a operatore", "operazioni.logic.assignment_status.open_operator", "Assegnazione mezzo aperta verso un operatore applicativo.", "Un'assegnazione mezzo aperta verso un operatore indica che il mezzo e attualmente riservato a un utente specifico finché l'assegnazione non viene chiusa con `end_at`."),
    "open_team": LogicExplanation("Regola workflow Operazioni: assegnazione mezzo attiva a team", "operazioni.logic.assignment_status.open_team", "Assegnazione mezzo aperta verso un team operativo.", "Un'assegnazione mezzo aperta verso un team indica che il mezzo e nel perimetro operativo del team finché l'assegnazione non viene chiusa con `end_at`."),
    "closed_operator": LogicExplanation("Regola workflow Operazioni: assegnazione mezzo chiusa da operatore", "operazioni.logic.assignment_status.closed_operator", "Assegnazione mezzo verso operatore terminata.", "Un'assegnazione mezzo chiusa verso un operatore rappresenta uno storico: il mezzo era assegnato a quell'utente ma il periodo operativo si e concluso."),
    "closed_team": LogicExplanation("Regola workflow Operazioni: assegnazione mezzo chiusa da team", "operazioni.logic.assignment_status.closed_team", "Assegnazione mezzo verso team terminata.", "Un'assegnazione mezzo chiusa verso un team rappresenta uno storico: il mezzo era nel perimetro del team ma l'assegnazione e stata terminata."),
}

CATALOG_OPERAZIONI_MAINTENANCE_STATUS: dict[str, LogicExplanation] = {
    "planned": LogicExplanation("Regola workflow Operazioni: manutenzione pianificata", "operazioni.logic.maintenance_status.planned", "Intervento manutentivo aperto o pianificato ma non ancora completato.", "Una manutenzione `planned` rappresenta un intervento aperto o programmato: il mezzo e nel ciclo di manutenzione ma il completamento non e ancora stato registrato."),
    "completed": LogicExplanation("Regola workflow Operazioni: manutenzione completata", "operazioni.logic.maintenance_status.completed", "Intervento manutentivo concluso con data di completamento registrata.", "Una manutenzione `completed` rappresenta un intervento chiuso: esiste una data di completamento e l'intervento e uscito dal ciclo manutentivo attivo."),
}

CATALOG_OPERAZIONI_USAGE_SESSION_STATUS: dict[str, LogicExplanation] = {
    "open": LogicExplanation("Regola workflow Operazioni: sessione d'uso aperta", "operazioni.logic.usage_session_status.open", "Sessione d'uso avviata e non ancora chiusa.", "Una sessione `open` rappresenta un utilizzo del mezzo ancora in corso: l'uscita e stata registrata ma non esiste ancora una chiusura con odometro finale."),
    "closed": LogicExplanation("Regola workflow Operazioni: sessione d'uso chiusa", "operazioni.logic.usage_session_status.closed", "Sessione d'uso chiusa con odometro finale registrato.", "Una sessione `closed` rappresenta un utilizzo concluso: esiste una chiusura con odometro finale e il mezzo e uscito dalla sessione attiva."),
    "validated": LogicExplanation("Regola workflow Operazioni: sessione d'uso validata", "operazioni.logic.usage_session_status.validated", "Sessione d'uso chiusa e validata da un utente applicativo.", "Una sessione `validated` rappresenta un utilizzo chiuso e verificato: oltre alla chiusura operativa esiste anche una validazione applicativa."),
}

CATALOG_OPERAZIONI_ACTIVITY_STATUS: dict[str, LogicExplanation] = {
    "draft": LogicExplanation("Regola workflow Operazioni: attività in bozza", "operazioni.logic.activity_status.draft", "Attività fermata o salvata senza invio al ciclo di review.", "Un'attività `draft` è stata salvata senza completare l'invio al ciclo di review: resta modificabile e non è ancora entrata nella verifica applicativa."),
    "in_progress": LogicExplanation("Regola workflow Operazioni: attività in corso", "operazioni.logic.activity_status.in_progress", "Attività avviata dall'operatore e non ancora fermata.", "Un'attività `in_progress` è stata avviata ma non ancora chiusa: il lavoro operativo è ancora in corso e non esiste ancora un esito finale o una review."),
    "submitted": LogicExplanation("Regola workflow Operazioni: attività inviata", "operazioni.logic.activity_status.submitted", "Attività fermata e inviata per la review.", "Un'attività `submitted` è stata chiusa dall'operatore e inviata al ciclo di review: ha terminato l'esecuzione ma non ha ancora un esito approvativo."),
    "under_review": LogicExplanation("Regola workflow Operazioni: attività in review", "operazioni.logic.activity_status.under_review", "Attività già passata da una review ma ancora in verifica o integrazione.", "Un'attività `under_review` è nel ciclo di verifica: esiste una review o una richiesta di integrazione, ma il processo non è ancora chiuso con approvazione o rigetto."),
    "approved": LogicExplanation("Regola workflow Operazioni: attività approvata", "operazioni.logic.activity_status.approved", "Attività chiusa con esito review approvato.", "Un'attività `approved` ha completato il ciclo operativo e la review ha registrato un esito positivo."),
    "rejected": LogicExplanation("Regola workflow Operazioni: attività respinta", "operazioni.logic.activity_status.rejected", "Attività chiusa con esito review negativo.", "Un'attività `rejected` ha ricevuto un esito di review negativo: il contenuto è stato ritenuto non approvabile nello stato corrente."),
}

CATALOG_OPERAZIONI_ACTIVITY_APPROVAL_DECISION: dict[str, LogicExplanation] = {
    "approved": LogicExplanation("Regola workflow Operazioni: approvazione attività positiva", "operazioni.logic.activity_approval.approved", "La review ha chiuso l'attività con esito positivo.", "Una decisione `approved` indica che la review ha validato l'attività: il contenuto è stato accettato e il workflow si chiude con esito positivo."),
    "rejected": LogicExplanation("Regola workflow Operazioni: approvazione attività negativa", "operazioni.logic.activity_approval.rejected", "La review ha respinto l'attività nello stato corrente.", "Una decisione `rejected` indica che la review ha respinto l'attività: il contenuto non è stato ritenuto approvabile e richiede correzione o rifacimento."),
    "needs_integration": LogicExplanation("Regola workflow Operazioni: attività da integrare", "operazioni.logic.activity_approval.needs_integration", "La review non approva ancora l'attività e richiede integrazioni.", "Una decisione `needs_integration` indica che la review ha rilevato elementi mancanti o non chiari: l'attività resta nel ciclo di verifica e richiede integrazioni prima della chiusura."),
}

CATALOG_OPERAZIONI_FUEL_LOG_STATUS: dict[str, LogicExplanation] = {
    "linked": LogicExplanation("Regola workflow Operazioni: fuel log collegato", "operazioni.logic.fuel_log_status.linked", "Fuel log collegato a una sessione d'uso del mezzo.", "Un fuel log collegato indica che il rifornimento e gia stato associato a una sessione d'uso, quindi il contesto operativo del rifornimento e stato risolto."),
    "standalone": LogicExplanation("Regola workflow Operazioni: fuel log standalone", "operazioni.logic.fuel_log_status.standalone", "Fuel log registrato senza collegamento a una sessione d'uso.", "Un fuel log standalone indica che il rifornimento e stato registrato sul mezzo ma non e agganciato a una sessione d'uso specifica."),
    "incomplete": LogicExplanation("Regola workflow Operazioni: fuel log incompleto", "operazioni.logic.fuel_log_status.incomplete", "Fuel log con dati essenziali mancanti come costo, stazione o odometro.", "Un fuel log incompleto ha il rifornimento registrato ma presenta dati operativi mancanti; serve per audit ma riduce la qualita dell'analisi."),
}

CATALOG_OPERAZIONI_UNRESOLVED_TRANSACTION_REASON: dict[str, LogicExplanation] = {
    "no_card_operator": LogicExplanation("Regola import flotte: tessera senza operatore", "operazioni.logic.unresolved_transaction.no_card_operator", "La tessera carburante non ha un operatore associato al momento del match.", "La riga resta non risolta perché la tessera carburante non ha un operatore affidabile associato; senza questo passaggio il sistema non può risalire al contesto operativo."),
    "no_vehicle": LogicExplanation("Regola import flotte: mezzo non risolto", "operazioni.logic.unresolved_transaction.no_vehicle", "L'operatore o la tessera non portano a un mezzo univoco utilizzabile.", "La riga resta non risolta perché il processo di match non ha trovato un mezzo univoco; serve assegnazione manuale o completamento anagrafica mezzo."),
    "invalid_date": LogicExplanation("Regola import flotte: data non valida", "operazioni.logic.unresolved_transaction.invalid_date", "La riga contiene una data di rifornimento non interpretabile.", "La riga resta non risolta perché la data del rifornimento non è valida o non è interpretabile dal parser del processo di import."),
    "duplicate_pending": LogicExplanation("Regola import flotte: duplicato pendente", "operazioni.logic.unresolved_transaction.duplicate_pending", "La riga corrisponde a un unresolved già pendente nel sistema.", "La riga è trattata come duplicato pendente: il sistema ha già una transazione non risolta equivalente e ne evita la duplicazione."),
}
