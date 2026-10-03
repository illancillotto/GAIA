"""GAIA authenticated gateway to synthetic inspection and local audit history."""

from urllib.parse import urljoin

import httpx2
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser

from .audit import AUDIT_SCOPE
from .auth import issue_token
from .routes import Correlation, source_client, user_context

router = APIRouter(prefix="/console", tags=["Wiki MCP console"])


@router.get("/{kind}")
async def inspect(
    kind: str,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0, le=100000),
    before: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
):
    from .inspection import ENTITY_SCOPES

    if kind not in {"catalog", "calls", *ENTITY_SCOPES}:
        raise HTTPException(status_code=404, detail="Unknown MCP inspection resource")
    context = user_context(db, user, Correlation())
    if user.role in {"admin", "super_admin"}:
        from dataclasses import replace

        context = replace(context, scopes=context.scopes | {AUDIT_SCOPE})
    try:
        source = source_client()
        url = urljoin(source.urls["data"], f"../inspect/{kind}")
        async with httpx2.AsyncClient(
            headers={"Authorization": f"Bearer {issue_token(source.secret, context)}"},
            timeout=30,
            follow_redirects=False,
        ) as client:
            response = await client.get(
                url, params={"limit": limit, "offset": offset, "before": before}
            )
        if response.status_code != 200:
            status = response.status_code if response.status_code in {403, 404} else 503
            raise HTTPException(status_code=status, detail="MCP inspection unavailable or denied")
        return response.json()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="MCP inspection unavailable") from exc
