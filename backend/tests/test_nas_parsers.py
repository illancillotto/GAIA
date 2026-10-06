from app.schemas.sync import ParsedAclEntry
from app.services.nas_parsers import (
    _is_human_user,
    _normalize_share_name,
    parse_acl_output,
    parse_group_output,
    parse_passwd_output,
    parse_share_listing,
)


def test_nas_parsers_reject_malformed_and_internal_values() -> None:
    assert parse_passwd_output("\n# comment\nshort\nuser:x:not-a-uid:1::/home/user:x\n") == []
    assert parse_passwd_output("user:x:1001:1::/home/user:x")[0].full_name is None
    assert parse_group_output("\n# comment\nshort\nname:x:not-a-gid:a,b\nname:x:2000:a,,b\n")[
        0
    ].members == [
        "a",
        "b",
    ]

    assert _is_human_user("999", "/home/user") is False
    assert _is_human_user("1000", "/tmp/user") is False
    assert _is_human_user("1000", "/home/user") is True
    assert _normalize_share_name("  ") is None
    assert _normalize_share_name("/volume1") is None
    assert _normalize_share_name("/volume1/") is None
    assert _normalize_share_name("/volume1/@eaDir") is None
    assert _normalize_share_name("folder/#recycle") is None

    assert parse_share_listing("\n# comment\n/volume1\n") == []
    assert parse_acl_output(
        "\n# comment\nunknown: value\nallow: missing-colon\nuser:foo:read\n"
    ) == [ParsedAclEntry(subject="user:foo", permissions="read", effect="allow")]


def test_parse_passwd_output_extracts_users() -> None:
    raw = "mrossi:x:1001:100:Mario Rossi:/var/services/homes/mrossi:/sbin/nologin\n"
    users = parse_passwd_output(raw)

    assert len(users) == 1
    assert users[0].username == "mrossi"
    assert users[0].source_uid == "1001"
    assert users[0].full_name == "Mario Rossi"


def test_parse_passwd_output_skips_system_users() -> None:
    raw = (
        "anonymous:x:21:21::/nonexist:/usr/bin/nologin\n"
        "mrossi:x:1001:100:Mario Rossi:/var/services/homes/mrossi:/sbin/nologin\n"
    )

    users = parse_passwd_output(raw)

    assert [user.username for user in users] == ["mrossi"]


def test_parse_group_output_extracts_members() -> None:
    raw = "amministrazione:x:2001:mrossi,lbianchi\n"
    groups = parse_group_output(raw)

    assert len(groups) == 1
    assert groups[0].name == "amministrazione"
    assert groups[0].members == ["mrossi", "lbianchi"]


def test_parse_group_output_skips_synology_metadata_line() -> None:
    raw = "#$_@GID__INDEX@_$65539$\nadministrators:x:101:admin,svc_naap\n"

    groups = parse_group_output(raw)

    assert len(groups) == 1
    assert groups[0].name == "administrators"


def test_parse_share_listing_extracts_share_names() -> None:
    shares = parse_share_listing("contabilita\nhr\n")

    assert [share.name for share in shares] == ["contabilita", "hr"]


def test_parse_share_listing_skips_synology_internal_paths_and_keeps_spaces() -> None:
    shares = parse_share_listing("@appconf\n'Settore Affari Legali'\nEmailSaver\n")

    assert [share.name for share in shares] == ["Settore Affari Legali", "EmailSaver"]


def test_parse_share_listing_accepts_nested_absolute_paths() -> None:
    shares = parse_share_listing(
        "/volume1/Settore Catasto\n"
        "/volume1/Settore Catasto/Elaborazioni\n"
        "/volume1/@eaDir\n"
        "/volume1/Settore Catasto/#recycle\n"
    )

    assert [share.name for share in shares] == [
        "Settore Catasto",
        "Settore Catasto/Elaborazioni",
    ]


def test_parse_acl_output_extracts_allow_and_deny_entries() -> None:
    raw = "allow: group:amministrazione:read,write\ndeny: user:ospite:read\n"
    acl_entries = parse_acl_output(raw)

    assert len(acl_entries) == 2
    assert acl_entries[0].effect == "allow"
    assert acl_entries[0].subject == "group:amministrazione"
    assert acl_entries[0].permissions == "read,write"
    assert acl_entries[1].effect == "deny"
    assert acl_entries[1].subject == "user:ospite"
    assert acl_entries[1].permissions == "read"


def test_parse_acl_output_extracts_synology_acl_entries() -> None:
    raw = (
        "ACL version: 1\n"
        "Archive: has_ACL,is_support_ACL\n"
        "Owner: [root(user)]\n"
        "---------------------\n"
        "\t [0] group:administrators:allow:rwxpdDaARWc--:fd-- (level:0)\n"
        "\t [1] user:svc_naap:allow:rwxpdDaARWc--:fd-- (level:0)\n"
    )

    acl_entries = parse_acl_output(raw)

    assert len(acl_entries) == 2
    assert acl_entries[0].subject == "group:administrators"
    assert acl_entries[0].effect == "allow"
    assert acl_entries[0].permissions == "rwxpdDaARWc--"
    assert acl_entries[1].subject == "user:svc_naap"
