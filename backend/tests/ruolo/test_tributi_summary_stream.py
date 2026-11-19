from types import SimpleNamespace
from uuid import UUID

from sqlalchemy import event

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloTributiRegisteredMail
from app.modules.utenze.models import AnagraficaPaymentNotice

from .test_tributi_api import TestingSessionLocal, seed_avviso
from .test_tributi_api import setup_database as setup_database


def test_summary_stream_visits_each_notice_once_and_keeps_channel_precedence(monkeypatch):
    notices = [
        (2024, UUID(seed_avviso(anno=2024, tax_code="T2", amount=10.02))),
        (2022, UUID(seed_avviso(anno=2022, tax_code="T1", amount=19.99))),
        (2023, UUID(seed_avviso(anno=2023, tax_code="T1", amount=15.55))),
        (2022, UUID(seed_avviso(anno=2022, tax_code="T2", amount=21.11))),
    ]
    with TestingSessionLocal() as db:
        for year, avviso_id in notices[:2]:
            db.add(
                RuoloTributiRegisteredMail(
                    avviso_id=avviso_id, source_shipment_id=str(year), match_status="matched"
                )
            )
        db.add(
            AnagraficaPaymentNotice(
                source_system="incass",
                source_notice_id="PEC",
                anno="2022",
                codice_fiscale="T1",
                detail_url="/fixture",
                raw_detail_json={
                    "mailing_list": {
                        "shipments": [{"external_id": "recorded", "status_label": "Accettazione"}]
                    },
                    "partitario": {"shipments": ["unrelated"]},
                },
            )
        )
        db.commit()
        query_count = 0
        visited = []
        original = repo._precompute_tributi_effective_cores

        def observe(db, *, rows):
            visited.extend(row[0].id for row in rows)
            return original(db, rows=rows)

        def count_base_scan(_conn, _cursor, statement, _params, _context, _many):
            nonlocal query_count
            if "derived_payment_status" in statement and "count(*)" not in statement[:40]:
                query_count += 1

        monkeypatch.setattr(repo, "EFFECTIVE_FILTER_SCAN_CHUNK_SIZE", 2)
        monkeypatch.setattr(repo, "_precompute_tributi_effective_cores", observe)
        event.listen(db.get_bind(), "before_cursor_execute", count_base_scan)
        try:
            summary = repo.get_tributi_summary(db)
        finally:
            event.remove(db.get_bind(), "before_cursor_execute", count_base_scan)
        assert query_count == 1
        assert visited == [avviso_id for _, avviso_id in sorted(notices)]
        assert summary == {
            "to_send_count": 2,
            "sent_count": 2,
            "pec_count": 1,
            "raccomandata_count": 1,
            "total_count": 4,
            "total_amount": 66.67,
            "pec_amount": 19.99,
            "raccomandata_amount": 10.02,
            "raccomandata_source_available": True,
            "summary_partial": False,
            "summary_scan_limit": None,
            "summary_scanned_count": 4,
        }

        visited.clear()
        monkeypatch.setattr(repo, "SUMMARY_EFFECTIVE_FILTER_SCAN_LIMIT", 3)
        original_query, _, _ = repo._base_tributi_query()
        expected_sample = [
            row[0].id for row in db.execute(original_query.order_by(None).offset(0).limit(3))
        ]
        partial = repo.get_tributi_summary(db, open_only=True)
        assert visited == expected_sample
        assert partial["summary_scanned_count"] == partial["summary_scan_limit"] == 3
        assert partial["summary_partial"] is True


def test_incass_lookup_bounds_bind_count_for_large_reminder_batches(monkeypatch):
    rows = [
        (
            SimpleNamespace(
                id=UUID(int=i),
                codice_cnc=f"C{i}",
                anno_tributario=2024,
                codice_fiscale_raw=f"KEY{i}",
            ),
            None,
        )
        for i in range(1, 6)
    ]
    with TestingSessionLocal() as db:
        for i in range(1, 6):
            db.add(
                AnagraficaPaymentNotice(
                    source_system="incass",
                    source_notice_id=f"N{i}",
                    anno="2024",
                    codice_fiscale=f"KEY{i}",
                    detail_url="/fixture",
                )
            )
        db.commit()
        batches = []

        def record(_conn, _cursor, statement, parameters, _context, _many):
            if "requested_notices" in statement:
                batches.append(len(parameters))

        monkeypatch.setattr(repo, "EFFECTIVE_FILTER_SCAN_CHUNK_SIZE", 2)
        event.listen(db.get_bind(), "before_cursor_execute", record)
        try:
            notices = repo._batch_load_incass_notice_links(db, rows=rows)
        finally:
            event.remove(db.get_bind(), "before_cursor_execute", record)
        assert [notices[UUID(int=i)]["source_notice_id"] for i in range(1, 6)] == [
            "N1",
            "N2",
            "N3",
            "N4",
            "N5",
        ]
        assert len(batches) == 3
        assert batches[0] == batches[1] == batches[2] + 2
