"""Report di stato per la dismissione del legacy Ruolo basato su DMP.

Uso:
    docker compose exec -T backend python scripts/report_ruolo_legacy_state.py
"""
from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal


QUERIES: list[tuple[str, str]] = [
    (
        "volumi_tabelle",
        """
        select 'ruolo_import_jobs' as tabella, count(*) as righe from ruolo_import_jobs
        union all select 'ruolo_avvisi', count(*) from ruolo_avvisi
        union all select 'ruolo_partite', count(*) from ruolo_partite
        union all select 'ruolo_particelle', count(*) from ruolo_particelle
        union all select 'ana_payment_notices', count(*) from ana_payment_notices
        order by tabella
        """,
    ),
    (
        "job_legacy_2025",
        """
        select
          id,
          anno_tributario,
          filename,
          status,
          records_imported,
          created_at
        from ruolo_import_jobs
        where anno_tributario = 2025
        order by created_at desc
        """,
    ),
    (
        "incass_2025_copertura",
        """
        with ruolo as (
          select distinct subject_id
          from ruolo_avvisi
          where anno_tributario = 2025 and subject_id is not null
        ),
        notices as (
          select distinct subject_id
          from ana_payment_notices
          where anno = '2025' and source_system = 'incass' and subject_id is not null
        )
        select
          (select count(*) from ruolo) as ruolo_subjects,
          (select count(*) from notices) as incass_subjects,
          (select count(*) from ruolo r join notices n using (subject_id)) as overlap_subjects
        """,
    ),
    (
        "incass_2025_partitario",
        """
        select
          count(*) as notices_2025,
          count(*) filter (
            where raw_detail_json is not null
          ) as notices_con_detail,
          count(*) filter (
            where raw_detail_json is not null
              and (raw_detail_json::jsonb ? 'partitario')
          ) as notices_con_partitario
        from ana_payment_notices
        where anno = '2025' and source_system = 'incass'
        """,
    ),
    (
        "incass_2025_senza_soggetto",
        """
        select count(*) as notices_senza_subject
        from ana_payment_notices
        where anno = '2025'
          and source_system = 'incass'
          and subject_id is null
        """,
    ),
]


def main() -> None:
    with SessionLocal() as db:
        for name, sql in QUERIES:
            print(f"--- {name} ---")
            rows = db.execute(text(sql)).fetchall()
            for row in rows:
                print(row)
            db.rollback()


if __name__ == "__main__":
    main()
