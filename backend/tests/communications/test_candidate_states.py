"""List state queries stay bounded as the page grows; canonical state values are retained."""

from datetime import timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy import event

from app.modules.communications import candidate_states, models, ruolo_source
from app.modules.ruolo.notice_register_models import NoticeNotification, NoticePosition

from .conftest import create


def test_empty_page_does_not_query_the_accounting_detail(api):
    with api.session() as db:
        assert candidate_states.page_states(db, []) == ({}, {}, {})
        assert candidate_states.item_states(SimpleNamespace(avviso_ids_json=[]), {}, {}) == (
            "da_verificare",
            "da_verificare",
        )


def test_state_queries_are_bounded_for_25_candidates_and_do_not_load_full_detail(api, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("List must not load per-notice details, payments or notes")

    monkeypatch.setattr(ruolo_source.repo, "get_tributi_avviso", forbidden)
    statements = []

    def count(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(api.engine, "before_cursor_execute", count)
    try:
        with api.session() as db:
            source = ruolo_source.source_item(db, api.source_id)
            items = [
                SimpleNamespace(id=uuid4(), avviso_ids_json=source.avviso_ids_json)
                for _ in range(25)
            ]
            for size in (1, 25):
                statements.clear()
                payment, notifications, messages = candidate_states.page_states(db, items[:size])
                assert len(statements) <= 8
                assert messages == {}
                assert candidate_states.item_states(items[0], payment, notifications) == (
                    "unpaid",
                    "nessuna_evidenza",
                )
    finally:
        event.remove(api.engine, "before_cursor_execute", count)


def test_multiple_positions_notifications_and_latest_message_are_deterministic(api):
    first, second = create(api), create(api)
    with api.session() as db:
        source = ruolo_source.source_item(db, api.source_id)
        older = db.get(models.CommunicationMessage, UUID(first["id"]))
        newer = db.get(models.CommunicationMessage, UUID(second["id"]))
        older.created_at = newer.created_at - timedelta(seconds=1)
        older.state, newer.state = "cancelled", "draft"
        document_id = newer.document_id
        db.get(NoticeNotification, document_id).state = "invio_in_corso"
        db.flush()
        payment, notifications, messages = candidate_states.page_states(db, [source])
        assert messages[source.id].id == newer.id
        assert candidate_states.item_states(source, payment, notifications) == (
            "unpaid",
            "invio_in_corso, nessuna_evidenza",
        )
        missing = uuid4()
        other = uuid4()
        mixed = SimpleNamespace(avviso_ids_json=[*source.avviso_ids_json, str(missing), str(other)])
        payment[other] = "paid"
        assert candidate_states.item_states(mixed, payment, notifications)[0] == (
            "da_verificare, paid, unpaid"
        )
        assert db.query(NoticePosition).count() == 2
