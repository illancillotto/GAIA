from app.modules.wiki.schemas import WikiChatResponse, WikiChunkSource
from app.modules.wiki.services.response_composer import build_hybrid_response


def test_build_hybrid_response_merges_tool_and_docs() -> None:
    tool_response = WikiChatResponse(
        answer="Dati live ruolo: 3 avvisi collegati.",
        sources=[],
        found=True,
        mode="live_data",
    )
    docs_response = WikiChatResponse(
        answer="La documentazione spiega cosa significa collegato.",
        sources=[WikiChunkSource(source_file="RUOLO.md", section_title="Link", excerpt="...")],
        found=True,
    )

    response = build_hybrid_response(tool_response=tool_response, docs_response=docs_response)

    assert response.mode == "hybrid"
    assert response.found is True
    assert "Dati live ruolo" in response.answer
    assert "Contesto documentale" in response.answer
    assert response.sources[0].source_file == "RUOLO.md"
    assert any(evidence.type == "docs" for evidence in response.evidences)
