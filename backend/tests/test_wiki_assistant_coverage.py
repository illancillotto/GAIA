"""Copertura funzionale del Wiki Assistant tramite domande ad hoc.

Simula l'utente finale che non conosce il sistema: per ogni modulo GAIA pone
domande realistiche (overview, consultazione, workflow, navigazione) e verifica
che il routing deterministico le tratti come richieste *interne e gestibili*,
agganciandole a una capability sensata invece di bloccarle o lasciarle cadere.

Tutte le asserzioni passano per il fast router deterministico, quindi non serve
né il database né il provider LLM: è una rete di regressione che garantisce che
l'assistente "copra" davvero ogni modulo lato utente.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.wiki.capabilities.registry_loader import select_capability
from app.modules.wiki.services.question_router import route_wiki_question_fast


# Capability che rappresentano una risposta utile per l'utente: documentazione,
# dati live interni, spiegazioni, overview e navigazione.
ANSWERABLE_CAPABILITIES = {
    "docs_supported",
    "internal_live_data",
    "internal_explanation",
    "module_overview",
    "platform_overview",
    "page_intro",
    "navigation_help",
    "greeting",
    "clarification_needed",
}

# Capability che bloccano la richiesta: una domanda di dominio legittima non
# dovrebbe mai finire qui.
BLOCKED_CAPABILITIES = {
    "unsupported_external_live",
    "unsupported_access_request",
    "unsupported_action_request",
    "out_of_scope",
}

_OPERATIONAL_DOCS_ROOT = (
    Path(__file__).resolve().parents[2] / "domain-docs" / "wiki" / "operational"
)


# Domande ad hoc realistiche, una batteria per modulo. Coprono consultazione,
# interpretazione dati, workflow e regole operative tipiche di ogni dominio.
MODULE_QUESTION_BANK: dict[str, tuple[str, ...]] = {
    "wiki": (
        "Come cerco un articolo nel wiki?",
        "Come apro una richiesta di supporto completa?",
        "Quali fonti ha usato questa risposta?",
    ),
    "accessi": (
        "Come funziona il flusso di richiesta accesso?",
        "Quali ruoli servono per una funzione degli accessi?",
        "Come leggo i permessi effettivi su una cartella condivisa?",
    ),
    "catasto": (
        "Come leggo una visura catastale?",
        "Come interpreto lo stato di una particella?",
        "Quali dati servono per cercare il proprietario di un terreno?",
    ),
    "ruolo": (
        "Come funziona il workflow della pratica di ruolo?",
        "Quali campi del ruolo sono obbligatori?",
        "Come interpreto lo stato di un avviso del ruolo?",
    ),
    "utenze": (
        "Come leggo la scheda di un'utenza?",
        "Come interpreto un'anomalia di routing delle visure utenze?",
        "Quali campi sono rilevanti nella scheda di un'utenza?",
    ),
    "riordino": (
        "Come leggo lo stato di una pratica di riordino?",
        "Quali passaggi prevede il workflow del riordino?",
        "Quale documentazione serve per far avanzare una pratica di riordino?",
    ),
    "operazioni": (
        "Come leggo una metrica operativa?",
        "Come interpreto un'anomalia nelle operazioni?",
        "Come funziona la gestione dei mezzi nelle operazioni?",
    ),
    "rete": (
        "Come leggo il riepilogo di rete?",
        "Come interpreto un alert di rete?",
        "Quali dati controllo su un dispositivo di rete?",
    ),
    "organigramma": (
        "Come leggo l'albero organizzativo dell'organigramma?",
        "Come capisco chi vede chi nell'organigramma?",
        "Come interpreto ruoli e collegamenti nell'organigramma?",
    ),
    "elaborazioni": (
        "Come leggo lo stato di un job delle elaborazioni?",
        "Come interpreto esiti e scarti nelle elaborazioni?",
        "Quali artefatti produce un'elaborazione?",
    ),
    "presenze": (
        "Come leggo la banca ore di un collaboratore nelle presenze?",
        "Come interpreto una giornata nelle presenze?",
        "Come funziona la liquidazione della banca ore nelle presenze?",
    ),
    "inventario": (
        "Come leggo una richiesta di magazzino nell'inventario?",
        "Quali dati identificano un bene nell'inventario?",
        "Come distinguo una richiesta archiviata nell'inventario?",
    ),
}


def _all_module_questions() -> list[tuple[str, str]]:
    return [
        (module_key, question)
        for module_key, questions in MODULE_QUESTION_BANK.items()
        for question in questions
    ]


@pytest.mark.parametrize("module_key,question", _all_module_questions())
def test_domain_questions_are_treated_as_answerable(module_key: str, question: str) -> None:
    # Una domanda di dominio legittima ha solo due esiti corretti:
    #  1. il fast router la classifica come capability gestibile (docs/live/logic/overview);
    #  2. il fast router torna None, deferendola al router semantico LLM + pipeline RAG.
    # L'unico esito errato è il blocco deterministico: l'assistente deve sempre
    # provare a rispondere a una richiesta interna, mai chiuderla a priori.
    route = route_wiki_question_fast(question)
    if route is None:
        # Deferita al percorso LLM/RAG: comportamento "LLM-first" desiderato.
        return
    assert route.capability not in BLOCKED_CAPABILITIES, (
        f"[{module_key}] domanda legittima bloccata come "
        f"{route.capability!r}: {question!r}"
    )
    assert route.capability in ANSWERABLE_CAPABILITIES, (
        f"[{module_key}] capability inattesa {route.capability!r}: {question!r}"
    )


@pytest.mark.parametrize("module_key", tuple(MODULE_QUESTION_BANK))
def test_module_overview_question_routes_to_overview(module_key: str) -> None:
    route = route_wiki_question_fast(f"Cosa fa il modulo {module_key}?")
    assert route is not None
    assert route.capability == "module_overview"
    assert route.module_hint == module_key

    capability = select_capability(
        task_type="module_overview",
        module_hint=route.module_hint,
        extracted_slots=route.extracted_slots,
    )
    assert capability is not None, f"Overview senza capability per '{module_key}'"
    doc_path = _OPERATIONAL_DOCS_ROOT / capability.docs_pages[0]
    assert doc_path.is_file(), f"Documento overview mancante: {doc_path}"


@pytest.mark.parametrize(
    "question",
    [
        "Cos'e GAIA?",
        "Che cos'e GAIA?",
        "Quali moduli ci sono?",
        "Che moduli ci sono?",
        "Come funziona GAIA?",
    ],
)
def test_platform_questions_route_to_platform_overview(question: str) -> None:
    route = route_wiki_question_fast(question)
    assert route is not None
    assert route.capability == "platform_overview"


@pytest.mark.parametrize(
    "question",
    [
        "Dove trovo le particelle del ruolo?",
        "Dove si trova la banca ore?",
        "Come apro le pratiche di riordino?",
        "Come raggiungo i contatori irrigui?",
    ],
)
def test_navigation_questions_route_to_navigation_help(question: str) -> None:
    route = route_wiki_question_fast(question)
    assert route is not None
    assert route.capability == "navigation_help"


@pytest.mark.parametrize("question", ["Ciao", "Salve", "Buongiorno", "Hello"])
def test_greetings_route_to_greeting(question: str) -> None:
    route = route_wiki_question_fast(question)
    assert route is not None
    assert route.capability == "greeting"


@pytest.mark.parametrize(
    "question,expected",
    [
        ("Crea una nuova pratica di riordino", "unsupported_action_request"),
        ("Elimina questa particella dal catasto", "unsupported_action_request"),
        ("Dammi accesso alla cartella condivisa HR", "unsupported_access_request"),
        ("Abilitami al modulo operazioni", "unsupported_access_request"),
        ("Dammi le ultime notizie di borsa", "unsupported_external_live"),
        ("Che meteo fa adesso a Oristano?", "unsupported_external_live"),
    ],
)
def test_out_of_scope_requests_are_blocked(question: str, expected: str) -> None:
    route = route_wiki_question_fast(question)
    assert route is not None
    assert route.capability == expected, f"{question!r} -> {route.capability!r}"


def test_every_module_has_a_question_bank() -> None:
    # Guard: se aggiungiamo un modulo canonico deve avere domande di copertura.
    from tests.test_wiki_module_coverage import CANONICAL_MODULES

    missing = [m for m in CANONICAL_MODULES if m not in MODULE_QUESTION_BANK]
    assert not missing, f"Moduli senza domande ad hoc di copertura: {missing}"
