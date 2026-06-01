from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LogicExplanation:
    label: str
    source_key: str
    excerpt: str
    answer_template: str


CATALOG_PLATFORM_CORE_RULES: dict[str, LogicExplanation] = {
    "docs_only": LogicExplanation(
        label="Regola piattaforma: risposta documentale",
        source_key="platform.logic.response_mode.docs_only",
        excerpt="Il Wiki risponde usando solo documentazione indicizzata quando non servono tool live.",
        answer_template="La modalità `docs_only` usa esclusivamente documentazione indicizzata e non esegue tool live o logic dedicati.",
    ),
    "module_enablement": LogicExplanation(
        label="Regola piattaforma: abilitazione modulo",
        source_key="platform.logic.access.module_enablement",
        excerpt="Ogni tool live verifica che il modulo richiesto sia abilitato sull'account utente.",
        answer_template="Le interrogazioni live sono permesse solo se il modulo richiesto è abilitato per l'utente o se l'utente è super admin.",
    ),
    "section_permissions": LogicExplanation(
        label="Regola piattaforma: permessi sezione",
        source_key="platform.logic.access.section_permissions",
        excerpt="I tool protetti verificano anche le section permissions risolte lato backend.",
        answer_template="Quando un tool richiede una sezione protetta, il Wiki verifica le section permissions risolte lato backend prima di restituire dati o logiche.",
    ),
    "hybrid_docs_enrichment": LogicExplanation(
        label="Regola piattaforma: arricchimento ibrido",
        source_key="platform.logic.response_mode.hybrid",
        excerpt="Il Wiki può combinare tool live e documentazione solo se il tool ha trovato dati utili e la domanda richiede contesto.",
        answer_template="La modalità `hybrid` combina un risultato tool già riuscito con documentazione rilevante quando la domanda chiede spiegazione o contesto aggiuntivo.",
    ),
}
