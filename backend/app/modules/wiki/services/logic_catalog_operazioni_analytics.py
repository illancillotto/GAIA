from __future__ import annotations

from app.modules.wiki.services.logic_catalog_common import LogicExplanation

CATALOG_OPERAZIONI_ANALYTICS_METRICS: dict[str, LogicExplanation] = {
    "total_km": LogicExplanation(
        label="Regola metrica Operazioni Analytics: km totali",
        source_key="operazioni.logic.analytics.total_km",
        excerpt="Somma dei km dalle sessioni chiuse nel periodo selezionato.",
        answer_template=(
            "Il totale km di Operazioni Analytics somma i chilometri delle sessioni d'uso chiuse nel periodo selezionato, "
            "preferendo `route_distance_km` e usando come fallback la differenza odometro."
        ),
    ),
    "total_liters": LogicExplanation(
        label="Regola metrica Operazioni Analytics: litri totali",
        source_key="operazioni.logic.analytics.total_liters",
        excerpt="Somma dei litri registrati nei fuel log del periodo.",
        answer_template=(
            "I litri totali di Operazioni Analytics sommano i rifornimenti registrati nei fuel log del periodo selezionato."
        ),
    ),
    "total_work_hours": LogicExplanation(
        label="Regola metrica Operazioni Analytics: ore lavoro",
        source_key="operazioni.logic.analytics.total_work_hours",
        excerpt="Ore lavoro calcolate preferendo attività operatori e usando le sessioni veicolo come fallback.",
        answer_template=(
            "Le ore lavoro di Operazioni Analytics usano prima le attività operatori in stato `submitted`, `under_review` o `approved`; "
            "se non ci sono attività nel periodo, il sistema usa la durata delle sessioni veicolo chiuse come proxy."
        ),
    ),
    "active_sessions": LogicExplanation(
        label="Regola metrica Operazioni Analytics: sessioni attive",
        source_key="operazioni.logic.analytics.active_sessions",
        excerpt="Conteggio delle sessioni d'uso aperte al momento della query.",
        answer_template=(
            "Le sessioni attive di Operazioni Analytics contano le sessioni veicolo ancora in stato `open` al momento della richiesta."
        ),
    ),
    "anomaly_count": LogicExplanation(
        label="Regola metrica Operazioni Analytics: anomalie",
        source_key="operazioni.logic.analytics.anomaly_count",
        excerpt="Proxy anomaly count basato su refuel non abbinati e sessioni orfane aperte oltre soglia.",
        answer_template=(
            "Il conteggio anomalie di Operazioni Analytics usa un proxy operativo: refuel non abbinati nel periodo più sessioni aperte oltre soglia temporale."
        ),
    ),
    "top_operators_km": LogicExplanation(
        label="Regola metrica Operazioni Analytics: top operatori km",
        source_key="operazioni.logic.analytics.top_operators_km",
        excerpt="Classifica operatori costruita sommando i km delle sessioni chiuse e preferendo l'actual driver.",
        answer_template=(
            "La classifica top operatori km nelle analytics Operazioni somma i chilometri delle sessioni chiuse per operatore, "
            "preferendo `actual_driver_user_id` e usando `operator_name` come fallback sui record legacy."
        ),
    ),
    "work_hours_by_team": LogicExplanation(
        label="Regola metrica Operazioni Analytics: ore per team",
        source_key="operazioni.logic.analytics.work_hours_by_team",
        excerpt="Aggregazione ore attività per team sulle attività inviate, in review o approvate.",
        answer_template=(
            "Le ore per team nelle analytics Operazioni aggregano le attività in stato `submitted`, `under_review` o `approved`, "
            "sommando la durata per `team_id` e contando gli operatori distinti coinvolti."
        ),
    ),
}

CATALOG_OPERAZIONI_ANALYTICS_ANOMALY: dict[str, LogicExplanation] = {
    "orphan_session": LogicExplanation("Regola analytics Operazioni: sessione orfana", "operazioni.logic.analytics_anomaly.orphan_session", "Sessione d'uso rimasta aperta oltre la soglia temporale prevista.", "L'anomalia `orphan_session` segnala una sessione d'uso ancora aperta oltre la soglia prevista; in pratica manca la chiusura operativa della sessione."),
    "driver_mismatch": LogicExplanation("Regola analytics Operazioni: driver mismatch", "operazioni.logic.analytics_anomaly.driver_mismatch", "Guidatore effettivo diverso dall'operatore assegnato al mezzo nel periodo.", "L'anomalia `driver_mismatch` segnala che il guidatore registrato nella sessione non coincide con l'operatore assegnato al mezzo in quel momento."),
    "excessive_fuel": LogicExplanation("Regola analytics Operazioni: excessive fuel", "operazioni.logic.analytics_anomaly.excessive_fuel", "Rifornimento con volume oltre la soglia configurata.", "L'anomalia `excessive_fuel` segnala un rifornimento con litri superiori alla soglia analytics; serve come alert operativo e non implica da sola errore certo."),
    "unmatched_refuel": LogicExplanation("Regola analytics Operazioni: unmatched refuel", "operazioni.logic.analytics_anomaly.unmatched_refuel", "Evento WC rifornimento non abbinato a log interno.", "L'anomalia `unmatched_refuel` segnala un evento rifornimento proveniente da WC che non trova un fuel log interno corrispondente."),
    "hours_discrepancy": LogicExplanation("Regola analytics Operazioni: hours discrepancy", "operazioni.logic.analytics_anomaly.hours_discrepancy", "Scarto rilevante tra ore dichiarate e ore calcolate.", "L'anomalia `hours_discrepancy` segnala uno scarto significativo tra durata dichiarata e durata calcolata per l'attività."),
    "inactive_vehicle": LogicExplanation("Regola analytics Operazioni: inactive vehicle", "operazioni.logic.analytics_anomaly.inactive_vehicle", "Evento operativo registrato su mezzo dismesso o inattivo.", "L'anomalia `inactive_vehicle` segnala che una sessione o un rifornimento è stato registrato su un mezzo non più attivo."),
    "inactive_operator": LogicExplanation("Regola analytics Operazioni: inactive operator", "operazioni.logic.analytics_anomaly.inactive_operator", "Evento operativo registrato da operatore non più attivo.", "L'anomalia `inactive_operator` segnala che una sessione o un rifornimento è riferito a un operatore disattivato o non più valido."),
    "orphan_fuel_card": LogicExplanation("Regola analytics Operazioni: orphan fuel card", "operazioni.logic.analytics_anomaly.orphan_fuel_card", "Tessera carburante con assegnazione aperta ma operatore non valido o non mappato.", "L'anomalia `orphan_fuel_card` segnala una tessera carburante ancora aperta su un operatore disabilitato o non collegato a un utente GAIA."),
}
