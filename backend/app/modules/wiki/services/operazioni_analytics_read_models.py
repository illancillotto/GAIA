from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser


@dataclass(frozen=True)
class OperazioniAnalyticsReadModelBundle:
    summary: dict[str, object]
    top_fuel: dict[str, object]
    top_km_operators: dict[str, object]
    work_hours_by_team: dict[str, object]


def get_operazioni_analytics_summary_read_model(db: Session, current_user: ApplicationUser) -> dict[str, object]:
    from app.modules.operazioni.routes.analytics import analytics_summary

    return analytics_summary(current_user=current_user, db=db, from_date=None, to_date=None).model_dump(mode="json")


def get_operazioni_analytics_top_fuel_read_model(db: Session, current_user: ApplicationUser) -> dict[str, object]:
    from app.modules.operazioni.routes.analytics import fuel_analytics

    return fuel_analytics(current_user=current_user, db=db, from_date=None, to_date=None, granularity="month").model_dump(
        mode="json"
    )


def get_operazioni_analytics_top_km_operators_read_model(db: Session, current_user: ApplicationUser) -> dict[str, object]:
    from app.modules.operazioni.routes.analytics import km_analytics

    return km_analytics(current_user=current_user, db=db, from_date=None, to_date=None, granularity="month").model_dump(
        mode="json"
    )


def get_operazioni_analytics_work_hours_by_team_read_model(db: Session, current_user: ApplicationUser) -> dict[str, object]:
    from app.modules.operazioni.routes.analytics import work_hours_analytics

    return work_hours_analytics(
        current_user=current_user, db=db, from_date=None, to_date=None, granularity="month"
    ).model_dump(mode="json")


def build_operazioni_analytics_bundle(db: Session, current_user: ApplicationUser) -> OperazioniAnalyticsReadModelBundle:
    return OperazioniAnalyticsReadModelBundle(
        summary=get_operazioni_analytics_summary_read_model(db, current_user),
        top_fuel=get_operazioni_analytics_top_fuel_read_model(db, current_user),
        top_km_operators=get_operazioni_analytics_top_km_operators_read_model(db, current_user),
        work_hours_by_team=get_operazioni_analytics_work_hours_by_team_read_model(db, current_user),
    )
