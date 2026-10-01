"""Authenticated GAIA gateway and optional Wiki MCP agent entry point."""

import os
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.services.permission_resolver import can_access_section

from .agent import WikiMCPAgent
from .auth import effective_scopes, issue_token, validate_secret
from .client import WikiMCPClient
from .context import CallContext

router = APIRouter(prefix="/mcp", tags=["Wiki MCP"])
MODEL = "gpt-reserve"


class Correlation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID | None = None
    experiment_run_id: UUID | None = None


class AgentQuestion(Correlation):
    question: str = Field(min_length=1, max_length=2000)


def signing_secret() -> str:
    secret = os.environ.get("GAIA_MCP_SIGNING_SECRET", "")
    try:
        validate_secret(secret)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="MCP signing is not configured") from exc
    return secret


def user_context(db, user, correlation: Correlation) -> CallContext:
    return CallContext(
        principal=f"gaia:{user.id}",
        scopes=effective_scopes(db, user, can_access_section) - {"docs.read"},
        conversation_id=str(correlation.conversation_id) if correlation.conversation_id else None,
        experiment_run_id=str(correlation.experiment_run_id)
        if correlation.experiment_run_id
        else None,
    )


def source_client() -> WikiMCPClient:
    return WikiMCPClient(
        None,
        os.environ.get("GAIA_MCP_DATA_URL", "http://127.0.0.1:8768/data/"),
        signing_secret(),
    )


def model_client():
    from openai import AsyncOpenAI

    url = os.environ.get("GAIA_MCP_MODEL_BASE_URL") or os.environ.get("CODEX_LB_URL", "")
    key = os.environ.get("GAIA_MCP_MODEL_API_KEY") or os.environ.get("CODEX_LB_API_KEY", "")
    if not all((url, key, os.environ.get("GAIA_MCP_MODEL", MODEL) == MODEL)):
        raise HTTPException(status_code=503, detail="MCP codex-lb provider is not configured")
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=503, detail="Invalid MCP provider URL")
    if any((parsed.username, parsed.password, parsed.query, parsed.fragment)):
        raise HTTPException(status_code=503, detail="Invalid MCP provider URL")
    return AsyncOpenAI(base_url=url, api_key=key, timeout=60, max_retries=0)


@router.post("/token")
def token(
    correlation: Correlation,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
):
    context = user_context(db, user, correlation)
    return {
        "access_token": issue_token(signing_secret(), context),
        "token_type": "Bearer",
        "expires_in": 60,
        "scopes": sorted(context.scopes),
    }


@router.get("/tools")
async def tools(
    db: Session = Depends(get_db), user: ApplicationUser = Depends(require_active_user)
):
    context = user_context(db, user, Correlation())
    try:
        return {"tools": await source_client().list_tools(context)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="MCP sources unavailable") from exc


@router.post("/chat")
async def chat(
    payload: AgentQuestion,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
):
    context = user_context(db, user, payload)
    try:
        async with model_client() as client:
            agent = WikiMCPAgent(source_client(), client, MODEL)
            return await agent.answer(payload.question, context)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="MCP agent unavailable") from exc
