from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.ruolo.models import RuoloTributiReminderBatch
from app.modules.ruolo.notice_register_models import (
    NoticeAudit,
    NoticeDocument,
    NoticeNotification,
    NoticePosition,
)
from app.modules.ruolo.services import notice_generation as service

from .test_notice_import import api_engine as api_engine
from .test_notice_register import _avviso
from .test_notice_register_api import api as api


def record(avviso):
    return SimpleNamespace(
        id=uuid4(),
        avviso_id=avviso.id,
        generated_by=1,
        status="generated",
        payload_json={"notice_number": "GAIA-001"},
        generated_document_path="/test/document.docx",
    )


def test_generated_reminder_is_registered_idempotently_without_notification(api):
    with api.session() as db:
        avviso = _avviso(db)
        reminder = record(avviso)
        assert service.register_reminder(db, reminder) is reminder
        document = db.scalar(select(NoticeDocument))
        assert document.source_system == "gaia_reminder"
        assert document.document_number == "GAIA-001"
        assert db.get(NoticeNotification, document.id).state == "nessuna_evidenza"
        assert db.scalar(select(NoticePosition)).avviso_id == avviso.id
        assert db.scalar(select(NoticeAudit)).actor_id == 1
        assert service.register_reminder(db, reminder) is reminder
        assert len(list(db.scalars(select(NoticeDocument)))) == 1


def test_generation_requires_actor_and_complete_scope(api):
    with api.session() as db:
        avviso = _avviso(db)
        reminder = record(avviso)
        reminder.generated_by = None
        with pytest.raises(ValueError, match="Operatore"):
            service.register_reminder(db, reminder)
        reminder.generated_by = 1
        reminder.avviso_id = uuid4()
        with pytest.raises(ValueError, match="Posizioni GAIA incomplete"):
            service.register_reminder(db, reminder)
        with pytest.raises(ValueError, match="Posizioni GAIA incomplete"):
            service._publish(db, "gaia_reminder", reminder, [avviso.id, uuid4()], 1)
        reminder.avviso_id, reminder.payload_json = avviso.id, None
        service.register_reminder(db, reminder)
        assert db.scalar(select(NoticeDocument.document_number)) == str(reminder.id)


def test_preview_and_failed_batch_are_not_published(api, monkeypatch):
    with api.session() as db:
        avviso = _avviso(db)
        item = record(avviso)
        item.status = "generated"
        service.register_batch_item(db, item, preview_only=True)
        item.status = "failed"
        service.register_batch_item(db, item, preview_only=False)
        assert db.scalar(select(NoticeDocument)) is None
        item.status, item.batch_id, item.avviso_ids_json = "generated", uuid4(), [str(avviso.id)]
        original_get = db.get
        monkeypatch.setattr(
            db,
            "get",
            lambda model, key: (
                SimpleNamespace(generated_by=1)
                if model is RuoloTributiReminderBatch
                else original_get(model, key)
            ),
        )
        service.register_batch_item(db, item, preview_only=False)
        assert db.scalar(select(NoticeDocument.source_system)) == "gaia_batch_item"
