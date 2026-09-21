"""Commit fence primitives. No confirmation/export endpoint uses these yet.

Use a dedicated READ COMMITTED connection, never an ORM identity map or a
transaction that also changes dependencies. A token is not an eligibility check.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.engine import Connection

from app.modules.ruolo.notice_revision_models import NoticeGenerationRevision

DEPENDENCY_TABLES = frozenset(
    {
        "ana_subjects",
        "ana_persons",
        "ana_companies",
        "ana_payment_notices",
        "ruolo_avvisi",
        "ruolo_partite",
        "ruolo_particelle",
        "ruolo_tributi_payments",
        "ruolo_tributi_avviso_status",
        "ruolo_tributi_special_notices",
        "ruolo_tributi_special_allocations",
        "ruolo_tributi_year_managers",
        "ruolo_tributi_calculation_policies",
        "ruolo_tributi_templates",
        "ruolo_tributi_registered_mails",
        "ruolo_notice_documents",
        "ruolo_notice_positions",
        "ruolo_notice_attempts",
        "ruolo_notice_evidence",
        "ruolo_notice_notifications",
        "ruolo_notice_recoveries",
        "ruolo_notice_import_batches",
        "ruolo_notice_import_rows",
    }
)


class RevisionProtocolUnavailable(RuntimeError):
    """The database cannot provide the required commit fence."""


class GenerationRevisionChanged(ValueError):
    """A dependency committed since the caller captured its token."""


@dataclass(frozen=True)
class GenerationRevision:
    epoch: UUID
    revision: int


def _require_protocol(connection: Connection) -> None:
    if connection.dialect.name != "postgresql":
        raise RevisionProtocolUnavailable("Il protocollo richiede PostgreSQL")
    if (
        getattr(connection.connection.dbapi_connection, "autocommit", True)
        or connection.get_isolation_level() != "READ COMMITTED"
    ):
        raise RevisionProtocolUnavailable("Richiesta transazione READ COMMITTED, senza autocommit")
    rows = connection.execute(
        text("""
            SELECT c.relname, t.tgname, t.tgtype, t.tgdeferrable, t.tginitdeferred,
                   t.tgenabled, p.proname
            FROM pg_trigger t
            JOIN pg_class c ON c.oid = t.tgrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_proc p ON p.oid = t.tgfoid AND p.pronamespace = n.oid
            WHERE n.nspname = current_schema() AND NOT t.tgisinternal
              AND t.tgname IN ('gaia_notice_revision_row', 'gaia_notice_revision_truncate')
        """)
    )
    installed = {tuple(row) for row in rows}
    expected = {
        (table, name, kind, deferred, deferred, "A", "gaia_notice_revision_bump")
        for table in DEPENDENCY_TABLES
        for name, kind, deferred in (
            ("gaia_notice_revision_row", 29, True),
            ("gaia_notice_revision_truncate", 32, False),
        )
    }
    if not expected.issubset(installed):
        raise RevisionProtocolUnavailable(
            "Trigger di revisione assenti, disabilitati o incompatibili"
        )


def read_revision(connection: Connection) -> GenerationRevision:
    """Capture before reading inputs; no lock is retained during rendering."""
    _require_protocol(connection)
    return _read(connection, lock=False)


def lock_revision(connection: Connection, expected: GenerationRevision) -> GenerationRevision:
    """Hold the commit fence until transaction end; never render or do network I/O here."""
    _require_protocol(connection)
    current = _read(connection, lock=True)
    if current != expected:
        raise GenerationRevisionChanged("Dati modificati: rigenerare la bozza")
    return current


def _read(connection: Connection, *, lock: bool) -> GenerationRevision:
    table = NoticeGenerationRevision.__table__
    query = select(table.c.epoch, table.c.revision).where(table.c.id == 1)
    if lock:
        query = query.with_for_update()
    row = connection.execute(query).one_or_none()
    if row is None:
        raise RevisionProtocolUnavailable("Revisione non inizializzata dalla migration")
    return GenerationRevision(row.epoch, row.revision)
