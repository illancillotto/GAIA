from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BonificaAppDefinition:
    key: str
    label: str
    list_path: str
    detail_path_template: str | None = None
    columns_count: int = 3
    supports_date_range: bool = False


BONIFICA_APPS: dict[str, BonificaAppDefinition] = {
    "vehicles": BonificaAppDefinition(
        key="vehicles",
        label="Automezzi e attrezzature",
        list_path="/vehicles/datatable",
        detail_path_template="/vehicles/edit/{id}",
    ),
    "refuels": BonificaAppDefinition(
        key="refuels",
        label="Registro rifornimenti",
        list_path="/vehicles/refuel/datatable",
        detail_path_template="/vehicles/refuel/edit/{id}",
        columns_count=5,
        supports_date_range=True,
    ),
    "taken_charge": BonificaAppDefinition(
        key="taken_charge",
        label="Prese in carico automezzi",
        list_path="/vehicles/taken-charge/datatable",
        detail_path_template="/vehicles/taken-charge/edit/{id}",
        columns_count=7,
        supports_date_range=True,
    ),
    "users": BonificaAppDefinition(
        key="users",
        label="Utenti",
        list_path="/users/list",
        detail_path_template="/users/{id}",
        columns_count=5,
    ),
    "areas": BonificaAppDefinition(
        key="areas",
        label="Aree territoriali",
        list_path="/areas/datatable",
        detail_path_template="/areas/edit/{id}",
    ),
    "organizational_chart_areas": BonificaAppDefinition(
        key="organizational_chart_areas",
        label="Organigrammi aree",
        list_path="/areas/organizational-charts/list",
        detail_path_template="/areas/organizational-charts/edit/{id}",
    ),
    "organizational_chart_users": BonificaAppDefinition(
        key="organizational_chart_users",
        label="Organigrammi utenti",
        list_path="/users/organizational-charts/list",
        detail_path_template="/users/organizational-charts/edit/{id}",
    ),
    "report_types": BonificaAppDefinition(
        key="report_types",
        label="Tipologie segnalazione",
        list_path="/reports/types/datatable",
        detail_path_template="/reports/types/edit/{id}",
    ),
    "reports": BonificaAppDefinition(
        key="reports",
        label="Segnalazioni",
        list_path="/statistics/export-reports-datatable",
        columns_count=21,
        supports_date_range=True,
    ),
    "warehouse_requests": BonificaAppDefinition(
        key="warehouse_requests",
        label="Richieste magazzino",
        list_path="/warehouse-requests/datatable",
        columns_count=6,
        supports_date_range=True,
    ),
}


def get_bonifica_app(app_key: str) -> BonificaAppDefinition:
    try:
        return BONIFICA_APPS[app_key]
    except KeyError as exc:
        raise KeyError(f"Provider Bonifica Oristanese non configurato per entity `{app_key}`") from exc


def list_bonifica_apps() -> list[BonificaAppDefinition]:
    return list(BONIFICA_APPS.values())
