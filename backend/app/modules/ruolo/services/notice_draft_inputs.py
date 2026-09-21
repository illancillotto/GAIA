"""Capture input revisions before generation reads, never after rendering.

An untracked generation still produces a private draft, but cannot acquire a
valid basis retroactively. This module does not authorize confirmation/export.
"""

from datetime import date
from functools import wraps

from sqlalchemy import inspect

from app.modules.ruolo.services.notice_revision import (
    RevisionProtocolUnavailable,
    read_revision,
)

_INPUT_KEY = "gaia_notice_input_capture"


def _capture(db, avviso):
    if db.new or db.dirty or db.deleted:
        return None
    if avviso is not None and getattr(inspect(avviso, raiseerr=False), "session", None) is not db:
        return None
    try:
        revision = read_revision(db.connection())
    except RevisionProtocolUnavailable:
        return None
    # Caller-loaded entities and the policy cache predate the revision read.
    db.expire_all()
    db.info.pop("ruolo_tributi_has_active_calculation_policies", None)
    return (
        db.get_transaction(),
        {
            "version": 1,
            "epoch": str(revision.epoch),
            "revision": revision.revision,
            "calculation_date": date.today().isoformat(),
        },
    )


def capture_inputs(generate):
    @wraps(generate)
    def captured(db, *args, **kwargs):
        previous = db.info.pop(_INPUT_KEY, None)
        try:
            with db.no_autoflush:
                db.info[_INPUT_KEY] = _capture(db, kwargs.get("avviso"))
            return generate(db, *args, **kwargs)
        finally:
            db.info.pop(_INPUT_KEY, None)
            if previous is not None:
                db.info[_INPUT_KEY] = previous

    return captured


def basis_for(db) -> dict | None:
    capture = db.info.get(_INPUT_KEY)
    if capture is None:
        return None
    transaction, basis = capture
    if (
        transaction is not db.get_transaction()
        or basis["calculation_date"] != date.today().isoformat()
    ):
        return None
    return dict(basis)
