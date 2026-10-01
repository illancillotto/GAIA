"""Fixed application queries and semantic source catalog."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Query:
    entity: str
    scope: str
    select: str
    filters: dict[str, str]
    parent: tuple[str, str] | None = None
    singleton: bool = False


SUBJECTS = "SELECT t.* FROM subjects t WHERE 1=1"
ACCOUNTS = "SELECT t.*, d.code AS district_code FROM irrigation_accounts t JOIN districts d ON d.id=t.district_id WHERE 1=1"
PARCELS = "SELECT t.*, d.code AS district_code FROM parcels t JOIN districts d ON d.id=t.district_id WHERE 1=1"
NOTICES = "SELECT t.* FROM role_notices t WHERE 1=1"
ACCOUNT_FILTERS = {
    "account_code": "t.account_code=:account_code",
    "campaign_year": "t.campaign_year=:campaign_year",
    "district_code": "d.code=:district_code",
    "status": "t.status=:status",
    "subject_id": "EXISTS (SELECT 1 FROM subject_accounts s WHERE s.account_id=t.id AND s.subject_id=:subject_id)",
}
PARCEL_FILTERS = {
    name: f"t.{name}=:{name}" for name in ("municipality_code", "sheet", "parcel_number", "crop")
}
PARCEL_FILTERS["district_code"] = "d.code=:district_code"
NOTICE_FILTERS = {
    name: f"t.{name}=:{name}"
    for name in ("subject_id", "tax_year", "status", "account_code", "notice_code")
}
QUERIES = {
    "search_subjects": Query(
        "subjects",
        "utenze.read",
        SUBJECTS,
        {
            "query": "(instr(lower(t.display_name), lower(:query))>0 OR instr(lower(t.synthetic_identifier), lower(:query))>0)",
            "subject_type": "t.subject_type=:subject_type",
        },
    ),
    "get_subject": Query(
        "subjects", "utenze.read", SUBJECTS, {"subject_id": "t.id=:subject_id"}, singleton=True
    ),
    "search_irrigation_accounts": Query(
        "irrigation_accounts", "catasto.read", ACCOUNTS, ACCOUNT_FILTERS
    ),
    "get_irrigation_account": Query(
        "irrigation_accounts",
        "catasto.read",
        ACCOUNTS,
        {"account_id": "t.id=:account_id"},
        singleton=True,
    ),
    "search_parcels": Query("parcels", "catasto.read", PARCELS, PARCEL_FILTERS),
    "get_parcel": Query(
        "parcels", "catasto.read", PARCELS, {"parcel_id": "t.id=:parcel_id"}, singleton=True
    ),
    "get_accounts_by_parcel": Query(
        "irrigation_accounts",
        "catasto.read",
        ACCOUNTS,
        {
            "parcel_id": "EXISTS (SELECT 1 FROM account_parcels ap WHERE ap.account_id=t.id AND ap.parcel_id=:parcel_id AND ap.valid_from_year<=:year AND ap.valid_to_year>=:year)",
            "year": ":year IS NOT NULL",
        },
        ("parcels", "parcel_id"),
    ),
    "get_parcels_by_account": Query(
        "parcels",
        "catasto.read",
        PARCELS,
        {
            "account_id": "EXISTS (SELECT 1 FROM account_parcels ap WHERE ap.parcel_id=t.id AND ap.account_id=:account_id AND ap.valid_from_year<=:year AND ap.valid_to_year>=:year)",
            "year": ":year IS NOT NULL",
        },
        ("irrigation_accounts", "account_id"),
    ),
    "search_role_notices": Query("role_notices", "ruolo.read", NOTICES, NOTICE_FILTERS),
    "get_role_notice": Query(
        "role_notices", "ruolo.read", NOTICES, {"notice_id": "t.id=:notice_id"}, singleton=True
    ),
    "get_payments_by_notice": Query(
        "payments",
        "ruolo.read",
        "SELECT t.* FROM payments t WHERE 1=1",
        {"notice_id": "t.notice_id=:notice_id"},
        ("role_notices", "notice_id"),
    ),
    "get_role_lines_by_notice": Query(
        "role_lines",
        "ruolo.read",
        "SELECT t.* FROM role_lines t WHERE 1=1",
        {"notice_id": "t.notice_id=:notice_id"},
        ("role_notices", "notice_id"),
    ),
}
