from app.schemas.sync import ParsedAclEntry, ParsedNasGroup, ParsedNasUser, ParsedShare


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
        member_list = [member for member in members.split(",") if member]
        groups.append(ParsedNasGroup(name=name, gid=gid, members=member_list))

    return groups


def parse_share_listing(raw_text: str) -> list[ParsedShare]:
    shares: list[ParsedShare] = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        shares.append(ParsedShare(name=stripped))

    return shares


def parse_acl_output(raw_text: str) -> list[ParsedAclEntry]:
    acl_entries: list[ParsedAclEntry] = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
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

        subject, permissions = payload.split(":", maxsplit=1)
        acl_entries.append(
            ParsedAclEntry(
                subject=subject.strip(),
                permissions=permissions.strip(),
                effect=effect,
            )
        )

    return acl_entries
