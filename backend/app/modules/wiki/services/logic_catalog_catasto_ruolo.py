from __future__ import annotations

from app.modules.wiki.services.logic_catalog_common import LogicExplanation

CATALOG_CAT_METRICS: dict[str, LogicExplanation] = {
    "anomalie": LogicExplanation(
        label="Regola metrica Catasto: anomalie aperte",
        source_key="catasto.logic.metric.anomalie",
        excerpt="Conteggio delle anomalie aperte aggregate nel dashboard Catasto.",
        answer_template=(
            "L'indicatore anomalie Catasto rappresenta il numero di anomalie aperte "
            "nell'aggregato backend del dashboard Catasto. Non e una stima frontend e segue "
            "le regole di validazione e import del modulo Catasto."
        ),
    ),
    "particelle": LogicExplanation(
        label="Regola metrica Catasto: particelle correnti",
        source_key="catasto.logic.metric.particelle",
        excerpt="Conteggio delle particelle correnti presenti nell'anno campagna selezionato.",
        answer_template=(
            "L'indicatore particelle correnti conta le particelle considerate correnti "
            "nell'anno campagna attivo del dashboard Catasto."
        ),
    ),
    "importi": LogicExplanation(
        label="Regola metrica Catasto: importi complessivi",
        source_key="catasto.logic.metric.importi",
        excerpt="Somma importi lato backend sugli aggregati utenze/ruolo del dashboard Catasto.",
        answer_template=(
            "L'indicatore importi complessivi usa la somma backend degli importi associati "
            "alle utenze ruolo del perimetro Catasto selezionato."
        ),
    ),
    "copertura": LogicExplanation(
        label="Regola metrica Catasto: copertura dati",
        source_key="catasto.logic.metric.copertura",
        excerpt="Copertura espressa come presenza di geometria, distretto e collegamento al ruolo.",
        answer_template=(
            "La copertura dati Catasto misura l'avanzamento dei collegamenti chiave: "
            "geometria GIS, associazione a distretto e collegamento al ruolo."
        ),
    ),
}


CATALOG_RUOLO_METRICS: dict[str, LogicExplanation] = {
    "avvisi_collegati": LogicExplanation(
        label="Regola metrica Ruolo: avvisi collegati",
        source_key="ruolo.logic.metric.avvisi_collegati",
        excerpt="Conteggio degli avvisi che hanno un soggetto anagrafico associato.",
        answer_template=(
            "Gli avvisi collegati sono gli avvisi Ruolo che hanno `subject_id` valorizzato "
            "e quindi un legame risolto verso un soggetto dell'anagrafica."
        ),
    ),
    "avvisi_non_collegati": LogicExplanation(
        label="Regola metrica Ruolo: avvisi non collegati",
        source_key="ruolo.logic.metric.avvisi_non_collegati",
        excerpt="Conteggio degli avvisi Ruolo ancora privi di collegamento anagrafico.",
        answer_template=(
            "Gli avvisi non collegati sono gli avvisi Ruolo senza `subject_id`; in pratica "
            "non e stato ancora risolto un collegamento affidabile verso l'anagrafica."
        ),
    ),
    "totale_importi": LogicExplanation(
        label="Regola metrica Ruolo: totale importi",
        source_key="ruolo.logic.metric.totale_importi",
        excerpt="Somma backend dei totali Ruolo per anno tributario e aggregato dashboard.",
        answer_template=(
            "Il totale importi Ruolo e calcolato lato backend sommando gli importi aggregati "
            "degli avvisi del perimetro selezionato, distinti per i codici 0648, 0985 e 0668."
        ),
    ),
}
