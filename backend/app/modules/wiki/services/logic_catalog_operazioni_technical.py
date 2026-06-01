from __future__ import annotations

from app.modules.wiki.services.logic_catalog_common import LogicExplanation

CATALOG_OPERAZIONI_STORAGE_ALERTS: dict[str, LogicExplanation] = {
    "quota_usage": LogicExplanation(
        label="Regola tecnica Operazioni: quota storage",
        source_key="operazioni.logic.storage.quota_usage",
        excerpt="La quota storage misura bytes usati rispetto alla quota configurata.",
        answer_template=(
            "La quota storage Operazioni confronta i byte usati con la quota configurata lato backend; "
            "la percentuale e il rapporto tra `total_bytes_used` e `quota_bytes` nell'ultima metrica disponibile."
        ),
    ),
    "warning": LogicExplanation(
        label="Regola tecnica Operazioni: storage warning",
        source_key="operazioni.logic.storage.warning",
        excerpt="Alert warning quando la percentuale usata supera la soglia intermedia configurata.",
        answer_template=(
            "Un alert storage `warning` indica che l'uso spazio ha superato una soglia intermedia di attenzione; "
            "serve come segnale operativo per intervenire prima di una saturazione critica."
        ),
    ),
    "critical": LogicExplanation(
        label="Regola tecnica Operazioni: storage critical",
        source_key="operazioni.logic.storage.critical",
        excerpt="Alert critical quando la percentuale usata supera la soglia alta configurata.",
        answer_template=(
            "Un alert storage `critical` indica che l'uso spazio ha superato la soglia alta configurata; "
            "il sistema richiede intervento rapido per evitare impatti su allegati, import o processi operativi."
        ),
    ),
}

CATALOG_OPERAZIONI_MOBILE_SYNC: dict[str, LogicExplanation] = {
    "handshake": LogicExplanation(
        label="Regola tecnica Operazioni: mobile connector handshake",
        source_key="operazioni.logic.mobile_sync.handshake",
        excerpt="L'handshake espone capacità e autenticazione del connettore mobile.",
        answer_template=(
            "L'handshake mobile sync conferma che il connettore e autenticato e dichiara le capability disponibili, "
            "come lettura cataloghi/workset e invio field report o activity events."
        ),
    ),
    "catalogs": LogicExplanation(
        label="Regola tecnica Operazioni: mobile catalogs",
        source_key="operazioni.logic.mobile_sync.catalogs",
        excerpt="I cataloghi mobile espongono anagrafiche operative sincronizzate da GAIA.",
        answer_template=(
            "I cataloghi mobile sync esportano verso il client mobile le anagrafiche operative curate da GAIA, "
            "come tipi attività, severità report, veicoli e contatori assegnabili."
        ),
    ),
    "worksets": LogicExplanation(
        label="Regola tecnica Operazioni: mobile worksets",
        source_key="operazioni.logic.mobile_sync.worksets",
        excerpt="I workset mobile sono i payload operativi calcolati per operatore.",
        answer_template=(
            "I workset mobile aggregano il contesto operativo per operatore: attività assegnate, attività aperte, "
            "team, veicoli disponibili e contatori associati."
        ),
    ),
    "writeback": LogicExplanation(
        label="Regola tecnica Operazioni: mobile writeback",
        source_key="operazioni.logic.mobile_sync.writeback",
        excerpt="Il writeback mobile riceve eventi idempotenti come field report e activity start/stop.",
        answer_template=(
            "Il writeback mobile sync riceve eventi applicativi idempotenti dal client, come field report, "
            "activity start/stop e richieste fault TETI, mantenendo coerenza tramite chiavi di idempotenza."
        ),
    ),
}

CATALOG_OPERAZIONI_AUTODOC_SYNC_STATUS: dict[str, LogicExplanation] = {
    "queued": LogicExplanation("Regola workflow Operazioni: job AUTODOC in coda", "operazioni.logic.autodoc_sync_status.queued", "Job AUTODOC creato ma non ancora preso in esecuzione dal worker.", "Uno stato `queued` indica che il job AUTODOC è stato accodato correttamente ma non è ancora stato preso in esecuzione dal worker dedicato."),
    "running": LogicExplanation("Regola workflow Operazioni: job AUTODOC in esecuzione", "operazioni.logic.autodoc_sync_status.running", "Job AUTODOC in lavorazione sul worker browser dedicato.", "Uno stato `running` indica che il worker AUTODOC sta eseguendo la sincronizzazione dei mezzi selezionati."),
    "completed": LogicExplanation("Regola workflow Operazioni: job AUTODOC completato", "operazioni.logic.autodoc_sync_status.completed", "Job AUTODOC chiuso con esecuzione completata.", "Uno stato `completed` indica che il job AUTODOC ha terminato il ciclo di sincronizzazione e ha prodotto un esito finale senza rimanere aperto."),
    "failed": LogicExplanation("Regola workflow Operazioni: job AUTODOC fallito", "operazioni.logic.autodoc_sync_status.failed", "Job AUTODOC interrotto con errore o timeout.", "Uno stato `failed` indica che il job AUTODOC non ha completato correttamente la sincronizzazione: tipicamente per errore operativo, timeout o problema sul worker/browser."),
}
