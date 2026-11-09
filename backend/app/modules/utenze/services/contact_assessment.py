"""Read-only assessment from explicit archived source types, without SMTP/DNS probes.

A domain name is never evidence that an address is PEC. The result describes
what GAIA's archived sources say, not ownership or current mailbox availability.
"""

from email_validator import EmailNotValidError

from app.modules.utenze.contact_schemas import normalize_address

SOURCE_CHANNELS = {"PEC": "pec", "EMAIL": "email"}


def assess(address, source_contacts):
    try:
        normalized = normalize_address(address)
    except (EmailNotValidError, ValueError):
        return {
            "address": address,
            "channel": "unclassified",
            "state": "review",
            "reason": "invalid_syntax",
            "source_count": 0,
        }
    matched = [
        row for row in source_contacts if str(row.get("email") or "").strip().lower() == normalized
    ]
    channels = {SOURCE_CHANNELS.get(str(row.get("type") or "").strip().upper()) for row in matched}
    if len(channels) != 1 or None in channels:
        return {
            "address": normalized,
            "channel": "unclassified",
            "state": "review",
            "reason": "missing_or_conflicting_type",
            "source_count": len(matched),
        }
    channel = channels.pop()
    state, reason = _source_state(matched)
    return {
        "address": normalized,
        "channel": channel,
        "state": state,
        "reason": reason,
        "source_count": len(matched),
    }


def _source_state(rows):
    if any(row.get("revocation_at") or row.get("active_code") == -2 for row in rows):
        return "revoked", "source_revocation"
    if not all(row.get("active_code") == 1 for row in rows):
        return "review", "source_not_active"
    return "active", "explicit_source_type"
