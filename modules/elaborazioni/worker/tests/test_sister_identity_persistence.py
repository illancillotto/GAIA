from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from browser_test_support import ScriptedLocator, ScriptedPage, make_session

import sister_pdf_recovery
from app.models.catasto import CatastoVisuraRequest
from sister_browser_reliability import SisterSessionState
from sister_exceptions import SisterInvalidDocumentError
from sister_request_rows import SisterRequestCorrelation
from sister_submission_identity import IDENTITY_FIELDS, REQUESTS_LINKS
from sister_worker_types import SisterRemoteStateUpdate
from visura_flow import VisuraFlowCallbacks, _prepare_request

LIST = "https://sister3.agenziaentrate.gov.it/Servizi/ConsultazioneRichieste.do?metodo=lista&numConv=1050380&apertura=T"


@pytest.fixture
def worker_db(tmp_path, monkeypatch):
    # Load repository fixtures after the real browser module: test_worker has
    # lightweight fallback modules intended only for its isolated unit tests.
    import test_worker as worker_test_support

    yield from worker_test_support.worker_db.__wrapped__(tmp_path, monkeypatch)


@pytest.mark.parametrize("claim", ["current", "stale", "released"])
@pytest.mark.parametrize("mode", ["immobile", "soggetto"])
def test_dom_identity_is_durable_before_download_failure_and_respects_claim(
    worker_db, monkeypatch, tmp_path, claim, mode
):
    from test_worker import _seed_batch

    worker, session_factory, _ = worker_db
    _, _, ids = _seed_batch(session_factory, request_statuses=["processing"])
    token, credential = uuid4(), uuid4()
    first_submitted = datetime.now(UTC) - timedelta(hours=2)
    with session_factory() as db:
        request = db.get(CatastoVisuraRequest, ids[0])
        request.execution_token = token
        request.status = "pending" if claim == "released" else "processing"
        request.sister_first_submitted_at = first_submitted
        request.sister_remote_state = "pending"
        request.sister_credential_id = credential
        request.sister_remote_request_url = LIST
        request.attempts = 1
        db.commit()
    repository = worker._request_repository()
    session = make_session(
        ScriptedPage(url="https://sister3.agenziaentrate.gov.it/Visure/CheckRichiesta.do")
    )
    session.page.locators[IDENTITY_FIELDS] = ScriptedLocator(
        payload=[
            {
                "value": "2074281792",
                "action": "/Visure/ConsultazioneRichieste.do",
                "method": "post",
            }
        ]
    )
    session.page.locators[REQUESTS_LINKS] = ScriptedLocator(payload=[LIST])
    session._session_state = SisterSessionState(
        convention_id="1050380",
        correlation=SisterRequestCorrelation(str(ids[0]), frozenset(), ()),
    )
    callbacks = VisuraFlowCallbacks(
        update_remote_state=lambda remote_id, url, state: repository.set_remote_state(
            ids[0],
            uuid4() if claim == "stale" else token,
            SisterRemoteStateUpdate(remote_id, url, state, credential),
        ),
    )

    def assert_unarmed(_request):
        # Late responses from a previous request must stay unarmed while forms open.
        assert session._session_state.submission_callback is None

    session.open_visura_form = AsyncMock()
    session.fill_visura_form = AsyncMock(side_effect=assert_unarmed)
    session.open_subject_form = AsyncMock()
    session.fill_subject_form = AsyncMock(side_effect=assert_unarmed)
    session.search_subject_and_open_visura = AsyncMock(return_value=None)
    session.prepare_captcha_or_download = AsyncMock(return_value="download")
    monkeypatch.setattr(
        sister_pdf_recovery,
        "download_valid_pdf",
        AsyncMock(side_effect=SisterInvalidDocumentError("interrupted download")),
    )
    with pytest.raises(SisterInvalidDocumentError, match="interrupted"):
        asyncio.run(
            _prepare_request(
                session,
                SimpleNamespace(id=ids[0], search_mode=mode),
                tmp_path / "out.pdf",
                callbacks,
            )
        )
    with session_factory() as db:
        request = db.get(CatastoVisuraRequest, ids[0])
        assert request.sister_remote_request_id == ("2074281792" if claim == "current" else None)
        assert request.sister_first_submitted_at == first_submitted.replace(tzinfo=None)
        assert request.sister_credential_id == credential
        assert request.execution_token == token
        assert request.attempts == 1
        assert request.document_id is None
        if claim == "current":
            resumed = make_session()
            asyncio.run(resumed.begin_request_correlation(request))
            assert resumed.get_request_correlation().remote_id == "2074281792"
