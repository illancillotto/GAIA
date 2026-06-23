from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.models.application_user import ApplicationUser
from app.modules.wiki.capabilities.registry_schema import CapabilityDefinition
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


def test_build_orchestration_plan_uses_operational_preflight_when_available() -> None:
    conversation = _conversation()
    decision = SimpleNamespace(
        answer="Servono comune, foglio e particella",
        fallback_reason="owner_lookup_clarification",
        tool_name="owner_lookup_clarification",
        found=True,
    )

    with (
        patch("app.modules.wiki.services.orchestrator.get_or_create_wiki_conversation", return_value=conversation),
        patch("app.modules.wiki.services.orchestrator.route_wiki_question_fast", return_value=None),
        patch("app.modules.wiki.services.orchestrator.route_wiki_question", return_value=None),
        patch("app.modules.wiki.services.orchestrator.classify_intent", return_value="docs_only"),
        patch("app.modules.wiki.services.orchestrator.preflight_capability_guardrail", return_value=None),
        patch("app.modules.wiki.services.orchestrator.build_operational_preflight_response", return_value=decision),
    ):
        plan = _build_orchestration_plan(
            MagicMock(),
            _user(),
            "mi serve trovare un proprietario di un terreno",
            None,
            None,
            None,
            "/wiki",
        )

    assert plan.preflight_response is not None
    assert plan.preflight_response.found is True
    assert plan.preflight_tool_name == "owner_lookup_clarification"


def test_build_orchestration_plan_uses_capability_registry_for_missing_parameters() -> None:
    conversation = _conversation()
    route = WikiSemanticRoute(
        language="it",
        normalized_query="trova proprietario terreno",
        intent="live_data",
        capability="internal_live_data",
        module_hint="catasto",
        user_reply=None,
        task_type="owner_lookup",
        extracted_slots={"comune": None, "foglio": None, "particella": None},
    )

    with (
        patch("app.modules.wiki.services.orchestrator.get_or_create_wiki_conversation", return_value=conversation),
        patch("app.modules.wiki.services.orchestrator.route_wiki_question_fast", return_value=route),
    ):
        plan = _build_orchestration_plan(
            MagicMock(),
            _user(),
            "mi serve trovare un proprietario di un terreno",
            None,
            None,
            None,
            "/wiki",
        )

    assert plan.selected_capability is not None
    assert plan.selected_capability.name == "catasto.owner_lookup"
    assert plan.preflight_response is not None
    assert plan.preflight_reason == "missing_parameters"
    assert "comune, foglio e particella" in plan.preflight_response.answer


def test_build_orchestration_plan_uses_capability_tool_name_when_available() -> None:
    conversation = _conversation()
    route = WikiSemanticRoute(
        language="it",
        normalized_query="particella 11111111-1111-1111-1111-111111111111",
        intent="live_data",
        capability="internal_live_data",
        module_hint="catasto",
        user_reply=None,
        task_type="entity_lookup",
        extracted_slots={"uuid": "11111111-1111-1111-1111-111111111111"},
    )
    fake_tool = object()

    with (
        patch("app.modules.wiki.services.orchestrator.get_or_create_wiki_conversation", return_value=conversation),
        patch("app.modules.wiki.services.orchestrator.route_wiki_question_fast", return_value=route),
        patch("app.modules.wiki.services.orchestrator.find_matching_tool", return_value=None),
        patch("app.modules.wiki.services.orchestrator.find_tool_by_name", return_value=fake_tool),
    ):
        plan = _build_orchestration_plan(
            MagicMock(),
            _user(),
            "mostrami la particella 11111111-1111-1111-1111-111111111111",
            None,
            None,
            None,
            "/wiki",
        )

    assert plan.selected_capability is not None
    assert plan.selected_capability.name == "catasto.particella_lookup"
    assert plan.matched_tool is fake_tool


def test_execute_guardrail_plan_raises_without_preflight_response() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="docs_only",
        normalized_question="ciao",
        matched_tool=None,
        selected_capability=None,
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


def test_execute_guardrail_plan_prefers_docs_guided_answer_when_context_article_exists() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="docs_only",
        normalized_question="mi serve trovare un proprietario di un terreno cosa devo fare",
        matched_tool=None,
        selected_capability=CapabilityDefinition(
            name="catasto.owner_lookup",
            task_type="owner_lookup",
            module_key="catasto",
            docs_pages=("capabilities/catasto.owner_lookup.md",),
        ),
        preflight_response=WikiChatResponse(
            answer="Servono comune, foglio e particella.",
            sources=[],
            found=True,
        ),
        preflight_reason="missing_parameters",
        preflight_tool_name="catasto.owner_lookup",
    )
    docs_response = _response("Risposta guidata dai documenti operativi")

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response) as mocked_answer,
        patch("app.modules.wiki.services.orchestrator._persist_response_and_audit", side_effect=lambda *args, **kwargs: kwargs["response"]),
    ):
        response = _execute_guardrail_plan(
            MagicMock(),
            current_user=_user(),
            plan=plan,
            question="mi serve trovare un proprietario di un terreno cosa devo fare?",
            context_article=None,
            started_at=0.0,
            module_key="catasto",
            page_path="/catasto/particelle",
        )

    assert response.answer == "Risposta guidata dai documenti operativi"
    assert response.sources[0].source_file == "docs/wiki.md"
    assert mocked_answer.call_args.args[2] == "domain-docs/wiki/operational/capabilities/catasto.owner_lookup.md"


def test_execute_guardrail_plan_keeps_static_preflight_when_docs_answer_is_not_found() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="docs_only",
        normalized_question="come funziona il modulo catasto",
        matched_tool=None,
        selected_capability=CapabilityDefinition(
            name="common.module_overview",
            task_type="module_overview",
            module_key=None,
            docs_pages=("modules/module_overview.md",),
        ),
        preflight_response=WikiChatResponse(
            answer="Intro statica",
            sources=[],
            found=True,
        ),
        preflight_reason="module_overview",
        preflight_tool_name="module_overview",
    )

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=_response("niente", found=False)),
        patch("app.modules.wiki.services.orchestrator._persist_response_and_audit", side_effect=lambda *args, **kwargs: kwargs["response"]),
    ):
        response = _execute_guardrail_plan(
            MagicMock(),
            current_user=_user(),
            plan=plan,
            question="Come funziona il modulo catasto?",
            context_article=None,
            started_at=0.0,
            module_key="catasto",
            page_path="/catasto/particelle",
        )

    assert response.answer == "Intro statica"
    assert response.sources == []


def test_execute_tool_plan_raises_without_matched_tool() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="live_data",
        normalized_question="domanda",
        matched_tool=None,
        selected_capability=None,
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
        selected_capability=None,
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


def test_execute_docs_plan_prefers_capability_context_article() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="docs_only",
        normalized_question="come funziona il modulo catasto",
        matched_tool=None,
        selected_capability=CapabilityDefinition(
            name="common.module_overview",
            task_type="module_overview",
            module_key=None,
            docs_pages=("modules/module_overview.md",),
        ),
        preflight_response=None,
        preflight_reason=None,
        preflight_tool_name=None,
    )
    docs_response = _response("docs operativi")

    with (
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response) as mocked_answer,
        patch("app.modules.wiki.services.orchestrator.postflight_docs_guardrail", return_value=None),
        patch("app.modules.wiki.services.orchestrator._persist_response_and_audit", side_effect=lambda *args, **kwargs: kwargs["response"]),
    ):
        response = _execute_docs_plan(
            MagicMock(),
            current_user=_user(),
            plan=plan,
            question="Come funziona il modulo catasto?",
            context_article=None,
            started_at=0.0,
            module_key="catasto",
            page_path="/catasto/particelle",
        )

    assert response.answer == "docs operativi"
    assert mocked_answer.call_args.args[2] == "domain-docs/wiki/operational/modules/module_overview.md"


def test_execute_docs_plan_falls_back_from_capability_context_to_general_retrieval() -> None:
    plan = WikiOrchestrationPlan(
        conversation=_conversation(),
        intent="docs_only",
        normalized_question="spiegami il workflow accessi",
        matched_tool=None,
        selected_capability=CapabilityDefinition(
            name="common.workflow_explanation",
            task_type="workflow_explanation",
            module_key=None,
            docs_pages=("workflows/workflow_explanation.md",),
        ),
        preflight_response=None,
        preflight_reason=None,
        preflight_tool_name=None,
    )
    first = _response("niente", found=False)
    second = _response("docs generali", found=True)

    with (
        patch("app.modules.wiki.services.orchestrator.answer_question", side_effect=[first, second]) as mocked_answer,
        patch("app.modules.wiki.services.orchestrator.postflight_docs_guardrail", return_value=None),
        patch("app.modules.wiki.services.orchestrator._persist_response_and_audit", side_effect=lambda *args, **kwargs: kwargs["response"]),
    ):
        response = _execute_docs_plan(
            MagicMock(),
            current_user=_user(),
            plan=plan,
            question="Spiegami il workflow accessi",
            context_article=None,
            started_at=0.0,
            module_key="accessi",
            page_path="/nas-control/shares",
        )

    assert response.answer == "docs generali"
    assert mocked_answer.call_count == 2
    assert mocked_answer.call_args_list[0].args[2] == "domain-docs/wiki/operational/workflows/workflow_explanation.md"
    assert mocked_answer.call_args_list[1].args[2] is None


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
        selected_capability=None,
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
        selected_capability=None,
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
        selected_capability=None,
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
        selected_capability=None,
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
        selected_capability=None,
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
        selected_capability=None,
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
        selected_capability=None,
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
        selected_capability=None,
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
