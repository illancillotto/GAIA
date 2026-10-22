import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloTributiYearManager

from .test_tributi_notice_registry_postgres import (
    postgres_session_factory as postgres_session_factory,
)

pytestmark = pytest.mark.postgres


def test_year_manager_overlap_persists_and_orders_null_bounds_on_postgres(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory() as db:
        RuoloTributiYearManager.__table__.create(db.get_bind())
        repo.list_year_managers(db)
        manager = repo.upsert_year_manager(
            db,
            manager_key="avvisi_2021",
            manager_label="Avvisi 2021",
            year_from=2021,
            year_to=2021,
            calculation_policy="internal_gaia",
            is_active=True,
            notes=None,
            updated_by=None,
        )
        manager_id = manager.id
        db.commit()
    with postgres_session_factory() as db:
        assert repo.get_year_manager_for_year(db, 2017)["manager_key"] == "agenzia_entrate"
        assert repo.get_year_manager_for_year(db, 2020)["manager_key"] == "step"
        assert repo.get_year_manager_for_year(db, 2021)["manager_key"] == "avvisi_2021"
        assert repo.get_year_manager_for_year(db, 2022)["manager_key"] == "gaia"
        assert repo.delete_year_manager(db, manager_id) is True
        db.commit()
    with postgres_session_factory() as db:
        assert repo.get_year_manager_for_year(db, 2021)["manager_key"] == "step"
