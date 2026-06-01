from __future__ import annotations

from datetime import UTC, datetime, date

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_user import ApplicationUser
from app.modules.wiki.models import WikiConversationGovernanceConfig


def _utc_now() -> datetime:
    return datetime.now(UTC)


def get_or_create_wiki_conversation_governance_config(db: Session) -> WikiConversationGovernanceConfig:
    config = db.get(WikiConversationGovernanceConfig, 1)
    if config is not None:
        return config
    config = WikiConversationGovernanceConfig(
        id=1,
        fallback_heavy_threshold=settings.wiki_review_fallback_heavy_threshold,
        no_match_repeated_threshold=settings.wiki_review_no_match_repeated_threshold,
        high_latency_ms_threshold=settings.wiki_review_high_latency_ms_threshold,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def update_wiki_conversation_governance_config(
    db: Session,
    *,
    current_user: ApplicationUser | None,
    fallback_heavy_threshold: int | None = None,
    no_match_repeated_threshold: int | None = None,
    high_latency_ms_threshold: int | None = None,
    data_complete_from: date | None = None,
    last_backfill_at: datetime | None = None,
    updated_by: str | None = None,
) -> WikiConversationGovernanceConfig:
    config = get_or_create_wiki_conversation_governance_config(db)
    if fallback_heavy_threshold is not None:
        config.fallback_heavy_threshold = fallback_heavy_threshold
    if no_match_repeated_threshold is not None:
        config.no_match_repeated_threshold = no_match_repeated_threshold
    if high_latency_ms_threshold is not None:
        config.high_latency_ms_threshold = high_latency_ms_threshold
    if data_complete_from is not None:
        config.data_complete_from = data_complete_from
    if last_backfill_at is not None:
        config.last_backfill_at = last_backfill_at
    config.updated_by = updated_by or (current_user.username if current_user is not None else "system")
    config.updated_at = _utc_now()
    db.commit()
    db.refresh(config)
    return config
