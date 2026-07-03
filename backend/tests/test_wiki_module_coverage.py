"""Copertura modulo per modulo del Wiki Assistant.

Questi test garantiscono che ogni modulo operativo di GAIA sia coperto end-to-end
dall'assistente: token riconosciuto, module hint, capability di overview e pagina
di documentazione operativa effettivamente presente su disco. Servono da rete di
sicurezza contro moduli che "spariscono" silenziosamente dal perimetro
dell'assistente (es. un nuovo modulo backend senza copertura wiki).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.wiki.capabilities.registry_loader import select_capability
from app.modules.wiki.services.context_hints import MODULE_HINTS
from app.modules.wiki.services.guardrails import extract_requested_module


# Perimetro canonico dei moduli operativi GAIA esposti all'utente finale.
# Ogni voce: chiave modulo canonica usata da capability registry e docs.
CANONICAL_MODULES: tuple[str, ...] = (
    "wiki",
    "accessi",
    "catasto",
    "ruolo",
    "utenze",
    "riordino",
    "operazioni",
    "rete",
    "organigramma",
    "elaborazioni",
    "presenze",
    "inventario",
)

# Radice dei documenti operativi indicizzati dal RAG.
_OPERATIONAL_DOCS_ROOT = (
    Path(__file__).resolve().parents[2] / "domain-docs" / "wiki" / "operational"
)


@pytest.mark.parametrize("module_key", CANONICAL_MODULES)
def test_module_has_context_hint(module_key: str) -> None:
    assert module_key in MODULE_HINTS, f"Modulo '{module_key}' senza MODULE_HINTS"
    hint = MODULE_HINTS[module_key]
    assert hint.get("label"), f"Modulo '{module_key}' senza label"
    assert hint.get("examples"), f"Modulo '{module_key}' senza esempi guida"


@pytest.mark.parametrize("module_key", CANONICAL_MODULES)
def test_module_overview_capability_resolves(module_key: str) -> None:
    capability = select_capability(
        task_type="module_overview",
        module_hint=module_key,
        extracted_slots={},
    )
    assert capability is not None, f"Nessuna capability overview per '{module_key}'"
    assert capability.module_key == module_key
    assert capability.docs_pages, f"Capability '{capability.name}' senza docs_pages"


@pytest.mark.parametrize("module_key", CANONICAL_MODULES)
def test_module_overview_docs_exist_on_disk(module_key: str) -> None:
    capability = select_capability(
        task_type="module_overview",
        module_hint=module_key,
        extracted_slots={},
    )
    assert capability is not None
    for relative_doc in capability.docs_pages:
        doc_path = _OPERATIONAL_DOCS_ROOT / relative_doc
        assert doc_path.is_file(), f"Documento mancante per '{module_key}': {doc_path}"
        assert doc_path.read_text(encoding="utf-8").strip(), f"Documento vuoto: {doc_path}"


@pytest.mark.parametrize("module_key", CANONICAL_MODULES)
def test_module_token_is_recognized(module_key: str) -> None:
    # Una domanda che nomina esplicitamente il modulo deve risolvere il module hint
    # canonico, così l'orchestrazione può agganciare capability e documentazione.
    question = f"Cosa fa il modulo {module_key}?"
    assert extract_requested_module(question) == module_key


def test_no_canonical_module_is_missing_from_hints() -> None:
    # Guard inverso: se aggiungiamo un modulo a MODULE_HINTS dovremmo valutarne la
    # copertura. Qui ci assicuriamo che ogni modulo canonico sia presente; gli alias
    # extra (network, inaz, inventory) restano ammessi come sinonimi.
    missing = [module for module in CANONICAL_MODULES if module not in MODULE_HINTS]
    assert not missing, f"Moduli canonici senza hint: {missing}"
