from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass(slots=True, frozen=True)
class WikiConversationReviewSignals:
    denied_count: int = 0
    fallback_count: int = 0
    no_match_count: int = 0
    consecutive_no_match_count: int = 0
    avg_latency_ms: int = 0
    manual_flag: bool = False


@dataclass(slots=True, frozen=True)
class WikiConversationReviewAssessment:
    needs_review: bool
    review_reason: str | None
    review_score: int


@dataclass(slots=True, frozen=True)
class WikiConversationReviewConfig:
    fallback_heavy_threshold: int
    no_match_repeated_threshold: int
    high_latency_ms_threshold: int


def default_review_config() -> WikiConversationReviewConfig:
    return WikiConversationReviewConfig(
        fallback_heavy_threshold=settings.wiki_review_fallback_heavy_threshold,
        no_match_repeated_threshold=settings.wiki_review_no_match_repeated_threshold,
        high_latency_ms_threshold=settings.wiki_review_high_latency_ms_threshold,
    )


def assess_conversation_review(
    signals: WikiConversationReviewSignals,
    *,
    priority: str,
    status: str,
    review_config: WikiConversationReviewConfig | None = None,
) -> WikiConversationReviewAssessment:
    config = review_config or default_review_config()
    if status == "resolved":
        return WikiConversationReviewAssessment(needs_review=False, review_reason=None, review_score=0)

    review_reason: str | None = None
    if signals.manual_flag:
        review_reason = "manual_flag"
    elif signals.denied_count > 0:
        review_reason = "denied_present"
    elif signals.fallback_count >= config.fallback_heavy_threshold:
        review_reason = "fallback_heavy"
    elif signals.consecutive_no_match_count >= config.no_match_repeated_threshold:
        review_reason = "no_match_repeated"
    elif signals.avg_latency_ms >= config.high_latency_ms_threshold:
        review_reason = "high_latency"

    if review_reason is None:
        return WikiConversationReviewAssessment(needs_review=False, review_reason=None, review_score=0)

    priority_score = {"high": 300, "medium": 200, "low": 100}.get(priority, 200)
    reason_score = {
        "manual_flag": 90,
        "denied_present": 80,
        "fallback_heavy": 60,
        "no_match_repeated": 50,
        "high_latency": 40,
    }.get(review_reason, 0)
    score = priority_score + reason_score + signals.denied_count * 10 + signals.fallback_count * 5 + signals.no_match_count * 3
    return WikiConversationReviewAssessment(needs_review=True, review_reason=review_reason, review_score=score)
