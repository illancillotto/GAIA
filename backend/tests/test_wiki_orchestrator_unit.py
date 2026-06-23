from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse, WikiChatStreamChunk, WikiChunkSource
from app.modules.wiki.services.orchestrator import (
    WikiOrchestrationPlan,
    _build_orchestration_plan,
    _build_stream_meta,
    _chunk_answer,
    _execute_docs_plan,
    _execute_guardrail_plan,
    _execute_tool_plan,
    _serialize_stream_chunk,
    _yield_synthetic_stream,
    answer_with_orchestration,
    stream_with_orchestration,
)
from app.modules.wiki.services.semantic_router import WikiSemanticRoute


def _user() -> ApplicationUser:
    user = ApplicationUser()
    user.username = "tester"
    user.role = "admin"
    return user


def _conversation():
    return SimpleNamespace(id=uuid4())


def _response(answer: str = "Risposta", *, found: bool = True) -> WikiChatResponse:
    return WikiChatResponse(
        answer=answer,
        sources=[WikiChunkSource(source_file="docs/wiki.md", section_title="Intro", excerpt="...")] if found else [],
        found=found,
    )


def test_chunk_answer_and_serialize_stream_chunk_cover_helper_branches() -> None:
    assert _chunk_answer("") == [""]
    assert _chunk_answer("uno due tre", chunk_words=2) == ["uno due", "tre"]

    chunk = _serialize_stream_chunk("done", {"answer": "ok"})
    assert isinstance(chunk, WikiChatStreamChunk)
    assert chunk.event == "done"


def test_build_stream_meta_includes_stream_mode() -> None:
    response = _response()
    response.conversation_id = uuid4()

    payload = _build_stream_meta(response, stream_mode="synthetic")

    assert payload["stream_mode"] == "synthetic"
    assert payload["conversation_id"] == str(response.conversation_id)


def test_build_orchestration_plan_uses_preflight_guardrail_decision() -> None:
    conversation = _conversation()
    decision = SimpleNamespace(answer="Blocco", fallback_reason="unsupported_action_request")

    with (
        patch("app.modules.wiki.services.orchestrator.get_or_create_wiki_conversation", return_value=conversation),
        patch("app.modules.wiki.services.orchestrator.route_wiki_question_fast", return_value=None),
        patch("app.modules.wiki.services.orchestrator.route_wiki_question", return_value=None),
        patch("app.modules.wiki.services.orchestrator.classify_intent", return_value="docs_only"),
        patch("app.modules.wiki.services.orchestrator.preflight_capability_guardrail", return_value=decision),
    ):
        plan = _build_orchestration_plan(MagicMock(), _user(), "Aggiorna la pratica", None, None, None, "/operazioni/pratiche")

    assert plan.preflight_response is not None
    assert plan.preflight_response.found is False
    assert plan.preflight_reason == "unsupported_action_request"


def test_build_orchestration_plan_uses_widget_preflight_when_available() -> None:
    conversation = _conversation()
    route = WikiSemanticRoute(
        language="it",
        normalized_query="ciao",
        intent="docs_only",
        capability="greeting",
        module_hint=None,
        user_reply=None,
    )
    decision = SimpleNamespace(answer="Intro pagina", fallback_reason="page_intro", tool_name="page_intro", found=True)

    with (
        patch("app.modules.wiki.services.orchestrator.get_or_create_wiki_conversation", return_value=conversation),
        patch("app.modules.wiki.services.orchestrator.route_wiki_question_fast", return_value=route),
        patch("app.modules.wiki.services.orchestrator.preflight_capability_guardrail", return_value=None),
        patch("app.modules.wiki.services.orchestrator.build_widget_preflight_response", return_value=decision),
    ):
        plan = _build_orchestration_plan(MagicMock(), _user(), "ciao", None, None, "operazioni", "/operazioni/pratiche")

    assert plan.preflight_response is not None
    assert plan.preflight_response.found is True
    assert plan.preflight_tool_name == "page_intro"


def test_execute_guardrail_plan_raises_without_preflight_response() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="docs_only",
        normalized_question="ciao",
        matched_tool=None,
        preflight_response=None,
        preflight_reason=None,
        preflight_tool_name=None,
    )

    with pytest.raises(RuntimeError, match="Preflight plan richiesto"):
        _execute_guardrail_plan(
            MagicMock(),
            current_user=_user(),
            plan=plan,
            question="ciao",
            context_article=None,
            started_at=0.0,
            module_key=None,
            page_path=None,
        )


def test_execute_tool_plan_raises_without_matched_tool() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="live_data",
        normalized_question="domanda",
        matched_tool=None,
        preflight_response=None,
        preflight_reason=None,
        preflight_tool_name=None,
    )

    with pytest.raises(RuntimeError, match="Tool plan richiesto"):
        _execute_tool_plan(
            MagicMock(),
            current_user=_user(),
            plan=plan,
            question="domanda",
            context_article=None,
            started_at=0.0,
            module_key=None,
            page_path=None,
        )


def test_execute_docs_plan_uses_recent_fallback_for_platform_scope() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="docs_only",
        normalized_question="gaia wiki",
        matched_tool=None,
        preflight_response=None,
        preflight_reason=None,
        preflight_tool_name=None,
    )
    first = _response("niente", found=False)
    second = _response("docs", found=True)

    with (
        patch("app.modules.wiki.services.orchestrator.answer_question", side_effect=[first, second]) as mocked_answer,
        patch("app.modules.wiki.services.orchestrator.has_platform_scope", return_value=True),
        patch("app.modules.wiki.services.orchestrator.postflight_docs_guardrail", return_value=None),
        patch("app.modules.wiki.services.orchestrator._persist_response_and_audit", side_effect=lambda *args, **kwargs: kwargs["response"]),
    ):
        response = _execute_docs_plan(
            MagicMock(),
            current_user=_user(),
            plan=plan,
            question="Che cos'è il wiki di GAIA?",
            context_article=None,
            started_at=0.0,
            module_key="wiki",
            page_path="/operazioni/pratiche",
        )

    assert response.answer == "docs"
    assert mocked_answer.call_count == 2
    assert mocked_answer.call_args_list[0].kwargs["operational_only"] is True
    assert mocked_answer.call_args_list[1].kwargs["allow_recent_fallback"] is True


def test_yield_synthetic_stream_emits_meta_delta_and_done() -> None:
    response = _response("uno due tre")
    response.conversation_id = uuid4()

    chunks = list(_yield_synthetic_stream(response))

    assert [chunk.event for chunk in chunks] == ["meta", "delta", "done"]


def test_stream_with_orchestration_uses_preflight_response() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="docs_only",
        normalized_question="ciao",
        matched_tool=None,
        preflight_response=_response("Intro"),
        preflight_reason="page_intro",
        preflight_tool_name="page_intro",
    )
    final_response = _response("Intro finale")
    final_response.conversation_id = uuid4()

    with (
        patch("app.modules.wiki.services.orchestrator._build_orchestration_plan", return_value=plan),
        patch("app.modules.wiki.services.orchestrator.answer_with_orchestration", return_value=final_response),
    ):
        chunks = list(stream_with_orchestration(MagicMock(), _user(), "ciao", page_path="/operazioni/pratiche"))

    assert [chunk.event for chunk in chunks] == ["meta", "delta", "done"]


def test_stream_with_orchestration_uses_tool_plan_shortcut() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="live_data",
        normalized_question="stato",
        matched_tool=object(),
        preflight_response=None,
        preflight_reason=None,
        preflight_tool_name=None,
    )
    final_response = _response("Tool finale")
    final_response.conversation_id = uuid4()

    with (
        patch("app.modules.wiki.services.orchestrator._build_orchestration_plan", return_value=plan),
        patch("app.modules.wiki.services.orchestrator.answer_with_orchestration", return_value=final_response),
    ):
        chunks = list(stream_with_orchestration(MagicMock(), _user(), "stato", page_path="/operazioni/pratiche"))

    assert [chunk.event for chunk in chunks] == ["meta", "delta", "done"]


def test_stream_with_orchestration_raises_when_wiki_is_unavailable() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="docs_only",
        normalized_question="domanda",
        matched_tool=None,
        preflight_response=None,
        preflight_reason=None,
        preflight_tool_name=None,
    )

    with (
        patch("app.modules.wiki.services.orchestrator._build_orchestration_plan", return_value=plan),
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=False),
        pytest.raises(RuntimeError, match="codex-lb"),
    ):
        list(stream_with_orchestration(MagicMock(), _user(), "domanda"))


def test_answer_with_orchestration_raises_when_wiki_is_unavailable() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="docs_only",
        normalized_question="domanda",
        matched_tool=None,
        preflight_response=None,
        preflight_reason=None,
        preflight_tool_name=None,
    )

    with (
        patch("app.modules.wiki.services.orchestrator._build_orchestration_plan", return_value=plan),
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=False),
        pytest.raises(RuntimeError, match="codex-lb"),
    ):
        answer_with_orchestration(MagicMock(), _user(), "domanda")


def test_stream_with_orchestration_falls_back_to_sync_answer_when_no_docs_found() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="docs_only",
        normalized_question="domanda",
        matched_tool=None,
        preflight_response=None,
        preflight_reason=None,
        preflight_tool_name=None,
    )
    prepared = SimpleNamespace(found=False, sources=[], chunks=[])
    final_response = _response("Fallback sync")
    final_response.conversation_id = uuid4()

    with (
        patch("app.modules.wiki.services.orchestrator._build_orchestration_plan", return_value=plan),
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.prepare_docs_answer", return_value=prepared),
        patch("app.modules.wiki.services.orchestrator.answer_with_orchestration", return_value=final_response),
    ):
        chunks = list(stream_with_orchestration(MagicMock(), _user(), "domanda", page_path="/operazioni/pratiche"))

    assert [chunk.event for chunk in chunks] == ["meta", "done"]


def test_stream_with_orchestration_uses_recent_fallback_when_platform_scope_has_no_docs() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="docs_only",
        normalized_question="gaia wiki",
        matched_tool=None,
        preflight_response=None,
        preflight_reason=None,
        preflight_tool_name=None,
    )
    first_prepared = SimpleNamespace(found=False, sources=[], chunks=[])
    second_prepared = SimpleNamespace(
        found=True,
        sources=[WikiChunkSource(source_file="docs/wiki.md", section_title="Intro", excerpt="...")],
        chunks=[],
    )

    with (
        patch("app.modules.wiki.services.orchestrator._build_orchestration_plan", return_value=plan),
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.prepare_docs_answer", side_effect=[first_prepared, second_prepared]) as mocked_prepare,
        patch("app.modules.wiki.services.orchestrator.has_platform_scope", return_value=True),
        patch("app.modules.wiki.services.orchestrator.stream_answer_from_prepared", return_value=iter(["uno"])),
        patch("app.modules.wiki.services.orchestrator.build_docs_response_from_prepared", return_value=_response("uno")),
        patch("app.modules.wiki.services.orchestrator.postflight_docs_guardrail", return_value=None),
        patch("app.modules.wiki.services.orchestrator._persist_response_and_audit", side_effect=lambda *args, **kwargs: kwargs["response"]),
    ):
        chunks = list(stream_with_orchestration(MagicMock(), _user(), "Che cos'è il wiki di GAIA?", page_path="/operazioni/pratiche"))

    assert [chunk.event for chunk in chunks] == ["meta", "delta", "done"]
    assert mocked_prepare.call_count == 2
    assert mocked_prepare.call_args_list[1].kwargs["allow_recent_fallback"] is True


def test_stream_with_orchestration_streams_provider_response() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="docs_only",
        normalized_question="domanda",
        matched_tool=None,
        preflight_response=None,
        preflight_reason=None,
        preflight_tool_name=None,
    )
    prepared = SimpleNamespace(
        found=True,
        sources=[WikiChunkSource(source_file="docs/wiki.md", section_title="Intro", excerpt="...")],
        chunks=[],
    )

    with (
        patch("app.modules.wiki.services.orchestrator._build_orchestration_plan", return_value=plan),
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.prepare_docs_answer", return_value=prepared),
        patch("app.modules.wiki.services.orchestrator.stream_answer_from_prepared", return_value=iter(["uno", " due"])),
        patch("app.modules.wiki.services.orchestrator.build_docs_response_from_prepared", return_value=_response("uno due")),
        patch("app.modules.wiki.services.orchestrator.postflight_docs_guardrail", return_value=None),
        patch("app.modules.wiki.services.orchestrator._persist_response_and_audit", side_effect=lambda *args, **kwargs: kwargs["response"]),
    ):
        chunks = list(stream_with_orchestration(MagicMock(), _user(), "domanda", page_path="/operazioni/pratiche"))

    assert [chunk.event for chunk in chunks] == ["meta", "delta", "delta", "done"]


def test_stream_with_orchestration_uses_sync_answer_when_stream_is_empty_and_applies_postflight() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="docs_only",
        normalized_question="domanda",
        matched_tool=None,
        preflight_response=None,
        preflight_reason=None,
        preflight_tool_name=None,
    )
    prepared = SimpleNamespace(
        found=True,
        sources=[WikiChunkSource(source_file="docs/wiki.md", section_title="Intro", excerpt="...")],
        chunks=[],
    )
    docs_response = _response("Risposta docs")
    guardrail = SimpleNamespace(answer="Fuori scope", fallback_reason="question_out_of_scope")

    with (
        patch("app.modules.wiki.services.orchestrator._build_orchestration_plan", return_value=plan),
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.prepare_docs_answer", return_value=prepared),
        patch("app.modules.wiki.services.orchestrator.stream_answer_from_prepared", return_value=iter(())),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response),
        patch("app.modules.wiki.services.orchestrator.postflight_docs_guardrail", return_value=guardrail),
        patch("app.modules.wiki.services.orchestrator._persist_response_and_audit", side_effect=lambda *args, **kwargs: kwargs["response"]),
    ):
        chunks = list(stream_with_orchestration(MagicMock(), _user(), "domanda", page_path="/operazioni/pratiche"))

    assert chunks[-1].data["answer"] == "Fuori scope"
