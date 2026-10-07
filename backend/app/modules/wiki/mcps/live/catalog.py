"""Explicit read-only GAIA API contracts, independent of the synthetic catalog."""

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Page(Empty):
    page: int = Field(1, ge=1, le=1000)
    page_size: int = Field(20, ge=1, le=50)


class Search(Empty):
    q: str = Field(min_length=2, max_length=120)
    limit: int = Field(12, ge=1, le=30)


class AssetSearch(Page):
    search: str | None = Field(None, min_length=1, max_length=120)


class Record(Empty):
    record_id: UUID


class RecordPage(Page):
    record_id: UUID


class Window(Empty):
    hours: int = Field(24, ge=1, le=72)


class ParcelSearch(Page):
    comune_codice: str | None = Field(None, min_length=1, max_length=10)
    foglio: str | None = Field(None, min_length=1, max_length=20)
    particella: str | None = Field(None, min_length=1, max_length=20)


@dataclass(frozen=True)
class ToolSpec:
    path: str
    module: str
    sections: tuple[str, ...]
    inputs: type[Empty]
    fields: frozenset[str]
    description: str


COMMON = frozenset({"items", "total", "page", "page_size", "id", "name", "status"})
ASSETS = COMMON | {
    "asset_code",
    "asset_type",
    "effective_status",
    "is_active",
    "assigned_org_unit_name",
    "current_custody",
    "holder_user_id",
    "taken_at",
    "returned_at",
    "created_at",
    "updated_at",
}
SELF = COMMON | {
    "presenze",
    "operazioni",
    "network",
    "daily_records",
    "work_date",
    "worked_minutes",
    "expected_minutes",
    "overtime_minutes",
    "activities",
    "reports",
    "cases",
    "vehicle_sessions",
    "assigned_devices",
    "vehicle_assignments",
    "count",
    "pending",
    "open",
    "period_start",
    "period_end",
    "ordinary_minutes",
    "extra_minutes",
    "ordinary_hours",
    "extra_hours",
    "worked_days",
    "anomaly_days",
    "activities_count",
    "activity_minutes",
    "reports_count",
    "assigned_cases_count",
    "open_cases_count",
    "closed_cases_count",
    "vehicle_sessions_count",
    "vehicle_km",
    "assigned_devices_count",
    "active_vehicle_assignments_count",
    "teo_minutes",
    "effective_extra_minutes",
    "validation_status",
    "operational_status",
}
NETWORK = COMMON | {
    "ip_address",
    "hostname",
    "vendor",
    "device_type",
    "last_seen_at",
    "started_at",
    "completed_at",
    "devices_count",
    "known_devices",
    "unknown_devices",
    "online",
    "offline",
    "total_devices",
    "scans",
    "network_range",
    "scan_type",
    "hosts_scanned",
    "active_hosts",
    "discovered_devices",
}

TOOLS = {
    "search_gaia": ToolSpec(
        "/api/search",
        "",
        ("utenze.subjects", "catasto.dashboard", "ruolo.avvisi"),
        Search,
        COMMON | {"module", "type", "title", "subtitle", "href", "score", "modules"},
        "Search authorized Utenze, Catasto and Ruolo records; requires all three sections and modules.",
    ),
    "get_subject": ToolSpec(
        "/utenze/subjects/{record_id}",
        "utenze",
        ("utenze.subjects",),
        Record,
        COMMON
        | {
            "subject_type",
            "display_name",
            "first_name",
            "last_name",
            "company_name",
            "municipality",
            "irrigation_accounts",
            "person",
            "company",
            "nome",
            "cognome",
            "ragione_sociale",
        },
        "Read an authorized subject by the UUID returned by GAIA search.",
    ),
    "get_role_notice": ToolSpec(
        "/ruolo/avvisi/{record_id}",
        "ruolo",
        ("ruolo.avvisi",),
        Record,
        COMMON
        | {
            "anno",
            "codice_avviso",
            "importo_totale",
            "importo_pagato",
            "residuo",
            "payments",
            "amount",
            "paid_at",
            "lines",
            "tributo",
            "importo",
            "codice_cnc",
            "anno_tributario",
            "importo_totale_0648",
            "importo_totale_0985",
            "importo_totale_0668",
            "importo_totale_euro",
        },
        "Read an authorized role notice by its UUID; no accounting changes.",
    ),
    "search_assets": ToolSpec(
        "/api/dotazioni/assets",
        "dotazioni",
        ("dotazioni.view",),
        AssetSearch,
        ASSETS,
        "Search assets, assigned units and current custody; paged, read-only.",
    ),
    "get_asset": ToolSpec(
        "/api/dotazioni/assets/{record_id}",
        "dotazioni",
        ("dotazioni.view",),
        Record,
        ASSETS,
        "Read an asset by UUID; no custody or assignment changes.",
    ),
    "get_asset_custody": ToolSpec(
        "/api/dotazioni/assets/{record_id}/custody",
        "dotazioni",
        ("dotazioni.view",),
        Record,
        ASSETS,
        "Read current custody of an authorized asset.",
    ),
    "get_asset_history": ToolSpec(
        "/api/dotazioni/assets/{record_id}/events",
        "dotazioni",
        ("dotazioni.history",),
        RecordPage,
        ASSETS | {"action", "actor_user_id"},
        "Read asset event metadata; free-form notes are excluded.",
    ),
    "get_my_summary": ToolSpec(
        "/me/summary",
        "",
        (),
        Empty,
        SELF,
        "Read only the authenticated user's self-service summary.",
    ),
    "get_my_presenze": ToolSpec(
        "/me/presenze/daily-records",
        "presenze",
        (),
        Page,
        SELF,
        "Read the authenticated user's daily records; medical reasons and other users are excluded.",
    ),
    "get_my_reports": ToolSpec(
        "/me/operazioni/reports",
        "operazioni",
        (),
        Page,
        SELF | {"report_number", "category_name", "severity_name", "created_at", "updated_at"},
        "Read the authenticated user's report metadata; no report bodies or attachments.",
    ),
    "get_operations_summary": ToolSpec(
        "/operazioni/dashboard/summary",
        "operazioni",
        ("operazioni.dashboard",),
        Empty,
        SELF
        | {
            "vehicles",
            "available",
            "in_use",
            "maintenance",
            "today_total",
            "in_progress",
            "submitted",
            "storage",
            "percentage_used",
            "alert_level",
        },
        "Read the existing authorized operations dashboard summary.",
    ),
    "list_org_units": ToolSpec(
        "/organigramma/units",
        "organigramma",
        ("organigramma.read",),
        Empty,
        COMMON | {"nome", "tipo", "parent_id", "is_active"},
        "Read organizational units respecting GAIA visibility; no assignments changed.",
    ),
    "list_network_devices": ToolSpec(
        "/network/devices",
        "rete",
        ("rete.devices",),
        AssetSearch,
        NETWORK,
        "Read already discovered devices; never launch scans or access firewall credentials.",
    ),
    "list_network_scans": ToolSpec(
        "/network/scans",
        "rete",
        ("rete.scan",),
        Empty,
        NETWORK,
        "Read metadata of existing scans; cannot start scans.",
    ),
    "get_portal_health": ToolSpec(
        "/elaborazioni/portal-health",
        "catasto",
        ("catasto.dashboard",),
        Window,
        COMMON
        | {
            "events",
            "executions",
            "successes",
            "errors",
            "retries",
            "cooldowns",
            "success_rate",
            "average_duration_ms",
            "p95_duration_ms",
            "totals",
            "window_hours",
        },
        "Read current user's SISTER portal health; credentials and raw errors are excluded.",
    ),
    "get_processing_request": ToolSpec(
        "/elaborazioni/requests/{record_id}",
        "catasto",
        ("catasto.dashboard",),
        Record,
        COMMON
        | {
            "batch_id",
            "attempts",
            "last_error_code",
            "retry_not_before",
            "created_at",
            "updated_at",
            "processed_at",
        },
        "Read an authenticated user's processing request status; no artifacts, captcha, credentials or raw errors.",
    ),
    "search_parcels": ToolSpec(
        "/catasto/parcels",
        "ruolo",
        ("ruolo.avvisi",),
        ParcelSearch,
        COMMON
        | {
            "comune_codice",
            "comune_nome",
            "foglio",
            "particella",
            "subalterno",
            "sup_catastale_are",
            "sup_catastale_ha",
            "valid_from",
            "valid_to",
        },
        "Read paged cadastral parcel metadata through the existing Ruolo-authorized API; no documents or synchronization.",
    ),
}

BLOCKED_INTEGRATIONS = {
    "nas_documents": "Requires approved shares, canonical GAIA/NAS identity and live per-document ACL verification.",
    "trasparenza": "Requires an approved source URL, catalog and document distribution policy.",
    "processing_batches": "Existing batch GET routes synchronize counters; requires a separate pure read contract.",
}
