import re

from app.schemas.sync import ParsedAclEntry, ParsedNasGroup, ParsedNasUser, ParsedShare


ACL_ENTRY_PATTERN = re.compile(
    r"^\[\d+\]\s+"
    r"(?P<subject_type>user|group):"
    r"(?P<subject_name>[^:]+):"
    r"(?P<effect>allow|deny):"
    r"(?P<permissions>[^:]+)"
)


def parse_passwd_output(raw_text: str) -> list[ParsedNasUser]:
    users: list[ParsedNasUser] = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        parts = stripped.split(":")
        if len(parts) < 7:
            continue

        username, _, uid, _, gecos, home_directory, _ = parts[:7]
        if not _is_human_user(uid, home_directory):
            continue
        users.append(
            ParsedNasUser(
                username=username,
                source_uid=uid,
                full_name=gecos or None,
                home_directory=home_directory or None,
            )
        )

    return users


def parse_group_output(raw_text: str) -> list[ParsedNasGroup]:
    groups: list[ParsedNasGroup] = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        parts = stripped.split(":")
        if len(parts) < 4:
            continue

        name, _, gid, members = parts[:4]
        if not gid.isdigit():
            continue
        member_list = [member for member in members.split(",") if member]
        groups.append(ParsedNasGroup(name=name, gid=gid, members=member_list))

    return groups


def parse_share_listing(raw_text: str) -> list[ParsedShare]:
    shares: list[ParsedShare] = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        share_name = _normalize_share_name(stripped)
        if share_name is None:
            continue
        shares.append(ParsedShare(name=share_name))

    return shares


def parse_acl_output(raw_text: str) -> list[ParsedAclEntry]:
    acl_entries: list[ParsedAclEntry] = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        synology_match = ACL_ENTRY_PATTERN.match(stripped)
        if synology_match:
            acl_entries.append(
                ParsedAclEntry(
                    subject=(
                        f"{synology_match.group('subject_type')}:"
                        f"{synology_match.group('subject_name').strip()}"
                    ),
                    permissions=synology_match.group("permissions").strip(),
                    effect=synology_match.group("effect").strip(),
                )
            )
            continue

        if not stripped.lower().startswith(("allow:", "deny:", "user:", "group:")):
            continue

        effect = "allow"
        payload = stripped
        lowered = stripped.lower()

        if lowered.startswith("deny:"):
            effect = "deny"
            payload = stripped.split(":", maxsplit=1)[1].strip()
        elif lowered.startswith("allow:"):
            payload = stripped.split(":", maxsplit=1)[1].strip()

        if ":" not in payload:
            continue

        subject, permissions = payload.rsplit(":", maxsplit=1)
        acl_entries.append(
            ParsedAclEntry(
                subject=subject.strip(),
                permissions=permissions.strip(),
                effect=effect,
            )
        )

    return acl_entries


def _is_human_user(uid: str, home_directory: str) -> bool:
    if not uid.isdigit():
        return False
    if int(uid) < 1000:
        return False
    return home_directory.startswith("/var/services/homes/") or home_directory.startswith("/home/")


def _normalize_share_name(raw_name: str) -> str | None:
    normalized = raw_name.strip()
    if not normalized:
        return None
    if normalized.startswith("'") and normalized.endswith("'") and len(normalized) >= 2:
        normalized = normalized[1:-1]
    normalized = normalized.rstrip("/")
    if normalized == "/volume1":
        return None
    if normalized.startswith("/volume1/"):
        normalized = normalized.removeprefix("/volume1/")
    if not normalized:
        return None
    if normalized.startswith("@") or normalized.startswith("#"):
        return None
    if any(segment.startswith("@") or segment.startswith("#") for segment in normalized.split("/")):
        return None
    return normalized
