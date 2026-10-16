"""Seeding shortcut shared by the worker request repository/reliability tests."""

from test_worker import _seed_batch

from app.models.catasto import CatastoVisuraRequestStatus


def seed_requests(session_factory, *statuses: CatastoVisuraRequestStatus):
    """Seed one batch holding one visura request per status, in the given order."""
    return _seed_batch(session_factory, request_statuses=[status.value for status in statuses])
