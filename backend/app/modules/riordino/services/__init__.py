"""Service exports for Riordino."""

from app.modules.riordino.services.appeal_service import (
    create_appeal,
    list_appeals,
    resolve_appeal,
    update_appeal,
)
from app.modules.riordino.services.dashboard_service import get_summary
from app.modules.riordino.services.demo_seed_service import ensure_demo_practices
from app.modules.riordino.services.document_service import (
    get_document,
    list_documents,
    soft_delete_document,
    upload_document,
)
from app.modules.riordino.services.export_service import export_practice_dossier_zip, export_practice_summary_csv
from app.modules.riordino.services.gis_service import create_gis_link, list_gis_links, update_gis_link
from app.modules.riordino.services.issue_service import close_issue, create_issue, list_issues
from app.modules.riordino.services.link_service import (
    create_parcel,
    create_party,
    delete_parcel,
    delete_party,
    import_parcels_csv,
    list_parcels,
    list_parties,
)
from app.modules.riordino.services.notification_service import check_deadlines, list_notifications, mark_read
from app.modules.riordino.services.practice_service import (
    archive_practice,
    complete_practice,
    create_practice,
    delete_practice,
    get_practice_detail,
    list_practices,
    update_practice,
)
from app.modules.riordino.services.workflow_service import (
    advance_step,
    complete_phase,
    reopen_step,
    skip_step,
    start_phase,
)

__all__ = [
    "advance_step",
    "archive_practice",
    "check_deadlines",
    "close_issue",
    "complete_phase",
    "complete_practice",
    "create_appeal",
    "create_gis_link",
    "create_issue",
    "create_parcel",
    "create_party",
    "create_practice",
    "delete_parcel",
    "delete_party",
    "delete_practice",
    "ensure_demo_practices",
    "export_practice_dossier_zip",
    "export_practice_summary_csv",
    "get_document",
    "get_practice_detail",
    "get_summary",
    "list_appeals",
    "list_documents",
    "list_gis_links",
    "list_issues",
    "list_notifications",
    "list_parcels",
    "list_parties",
    "list_practices",
    "mark_read",
    "reopen_step",
    "resolve_appeal",
    "skip_step",
    "soft_delete_document",
    "start_phase",
    "import_parcels_csv",
    "update_appeal",
    "update_gis_link",
    "update_practice",
    "upload_document",
]
