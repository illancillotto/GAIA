from sqlalchemy.orm import Session

from app.modules.accessi.sync_org_charts import (
    WhiteOrgChartsSyncResult,
    sync_white_org_charts,
)
from app.modules.elaborazioni.bonifica_oristanese.apps.org_charts.client import (
    BonificaOrgChartRow,
)
from app.modules.organigramma.services.whitecompany_sync import sync_from_whitecompany


def sync_white_org_charts_to_canonical(
    *,
    db: Session,
    rows: list[BonificaOrgChartRow],
    user_id: int,
) -> WhiteOrgChartsSyncResult:
    sync_result = sync_white_org_charts(db=db, rows=rows)
    sync_from_whitecompany(db, user_id=user_id)
    return sync_result
